"""V402 · Bajas múltiples y unificación de nombres en Metas y tiendas.

Mantiene operaciones y usuarios históricos sin modificar. Alias persistente
por tienda y auditoría, permisos de administrador/superadministrador.
"""
from __future__ import annotations

from datetime import datetime
import re

from fastapi import HTTPException, Request
from v400_missing_productivity_center_pdf import norm


def normalize_key(raw):
    key = norm(raw)
    if not key or len(key) > 220:
        raise HTTPException(400, "Nombre de colaborador inválido")
    return key


def install(m):
    if getattr(m, "_V402_COLLABORATOR_ADMIN", False):
        return
    with m.db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS operation_collaborator_aliases(
            store TEXT NOT NULL, alias_key TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            changed_at TEXT NOT NULL, changed_by TEXT NOT NULL,
            PRIMARY KEY(store,alias_key)
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS operation_collaborator_admin_audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT NOT NULL, name_key TEXT NOT NULL,
            action TEXT NOT NULL, target_key TEXT DEFAULT '',
            changed_at TEXT NOT NULL, changed_by TEXT NOT NULL
        )""")

    def authorized(request):
        return m.require_user(request, ("superadmin", "admin"))

    def list_data(store):
        scope = str(store or "Compañía").strip()
        query = """SELECT c.store,c.name_key,c.name,c.active,c.first_seen,
                          c.last_seen,c.last_activity,c.updated_at,c.updated_by
                   FROM operation_collaborators AS c
                   LEFT JOIN operation_collaborator_aliases AS a
                     ON a.store=c.store AND a.alias_key=c.name_key
                   WHERE a.alias_key IS NULL"""
        params=[]
        if scope and scope != "Compañía":
            query += " AND c.store=?"
            params.append(scope)
        query += " ORDER BY c.store,c.name"
        with m.db() as con:
            rows = [dict(x) for x in con.execute(query,params).fetchall()]
            aliases = [dict(x) for x in con.execute(
                "SELECT a.store,a.alias_key,a.canonical_key,c.name "
                "FROM operation_collaborator_aliases a "
                "LEFT JOIN operation_collaborators c "
                "ON c.store=a.store AND c.name_key=a.alias_key"
            ).fetchall()]
            recent = [dict(x) for x in con.execute(
                "SELECT store,name_key,action,target_key,changed_at,changed_by "
                "FROM operation_collaborator_admin_audit ORDER BY id DESC LIMIT 40"
            ).fetchall()]
        by_target={}
        for alias in aliases:
            by_target.setdefault((alias["store"],alias["canonical_key"]), []).append(
                alias.get("name") or alias["alias_key"])
        for item in rows:
            item["aliases"]=sorted(by_target.get((item["store"],item["name_key"]), []))
        return {
            "rows":rows, "history":recent,
            "count_active":sum(bool(r["active"]) for r in rows),
            "count_inactive":sum(not bool(r["active"]) for r in rows),
            "count_aliases":len(aliases),
            "store":scope, "editable":True,
        }

    @m.app.get("/api/operations/collaborator-admin-v402")
    def collaborator_admin(request:Request,store:str="Compañía"):
        authorized(request)
        return list_data(store)

    @m.app.post("/api/operations/collaborator-admin-v402/status")
    async def batch_status(request:Request):
        actor=authorized(request)
        body=await request.json()
        items=body.get("items")
        active=body.get("active")
        if type(active) is not bool or not isinstance(items,list) or not 1<=len(items)<=200:
            raise HTTPException(400,"Selecciona de 1 a 200 colaboradores y un estatus válido")
        parsed=[]
        for item in items:
            if not isinstance(item,dict):
                raise HTTPException(400,"Colaborador inválido")
            store=str(item.get("store") or "").strip()
            if not store or len(store)>120:
                raise HTTPException(400,"Tienda inválida")
            parsed.append((store,normalize_key(item.get("name_key"))))
        if len(set(parsed))!=len(parsed):
            raise HTTPException(400,"No selecciones colaboradores repetidos")
        now=datetime.now().isoformat(timespec="seconds")
        with m.db() as con:
            for store,key in parsed:
                target=con.execute(
                    "SELECT active FROM operation_collaborators "
                    "WHERE store=? AND name_key=?",(store,key)).fetchone()
                alias=con.execute(
                    "SELECT 1 FROM operation_collaborator_aliases "
                    "WHERE store=? AND alias_key=?",(store,key)).fetchone()
                if target is None or alias is not None:
                    raise HTTPException(409,"La selección cambió. Actualiza la lista.")
            changed=0
            for store,key in parsed:
                cursor=con.execute(
                    "UPDATE operation_collaborators SET active=?, updated_at=?,updated_by=? "
                    "WHERE store=? AND name_key=? AND active<>?",
                    (int(active),now,actor["username"],store,key,int(active)))
                if cursor.rowcount:
                    changed+=1
                    con.execute(
                        "INSERT INTO operation_collaborator_admin_audit "
                        "(store,name_key,action,changed_at,changed_by) VALUES(?,?,?,?,?)",
                        (store,key,"Reactivado" if active else "Baja",now,actor["username"])
                    )
        return {"ok":True,"changed":changed,"selected":len(parsed),
                "message":f"{changed} colaborador(es) actualizado(s). Histórico conservado."}

    @m.app.post("/api/operations/collaborator-admin-v402/merge")
    async def merge_names(request:Request):
        actor=authorized(request)
        body=await request.json()
        store=str(body.get("store") or "").strip()
        target=normalize_key(body.get("canonical_key"))
        names=body.get("alias_keys")
        if not store or len(store)>120 or not isinstance(names,list) or not 1<=len(names)<=100:
            raise HTTPException(400,"Selecciona un nombre principal y otros nombres de la misma tienda")
        aliases=[normalize_key(x) for x in names]
        if len(aliases)!=len(set(aliases)) or target in aliases:
            raise HTTPException(400,"No se puede fusionar un nombre consigo mismo")
        now=datetime.now().isoformat(timespec="seconds")
        with m.db() as con:
            all_keys=[target,*aliases]
            ph=",".join("?" for _ in all_keys)
            found=[dict(r) for r in con.execute(
                f"SELECT store,name_key,name,active,first_seen,last_seen,last_activity "
                f"FROM operation_collaborators WHERE store=? AND name_key IN ({ph})",
                (store,*all_keys)
            ).fetchall()]
            bykey={x["name_key"]:x for x in found}
            if len(found)!=len(all_keys):
                raise HTTPException(409,"Alguno de los nombres ya no existe en el padrón")
            # Nunca asociar a una cuenta en otra tienda o introducir un ciclo.
            existing=con.execute(
                f"SELECT alias_key FROM operation_collaborator_aliases "
                f"WHERE store=? AND alias_key IN ({ph})",(store,*all_keys)
            ).fetchall()
            if existing:
                raise HTTPException(409,"Uno de los nombres ya está unificado. Actualiza la lista.")
            records=list(bykey.values())
            starts=[str(r["first_seen"]) for r in records if r["first_seen"]]
            ends=[str(r["last_seen"]) for r in records if r["last_seen"]]
            last=max(records,key=lambda r:str(r["last_seen"] or ""))
            # El nombre principal y su estatus activo/baja no se alteran.
            con.execute(
                "UPDATE operation_collaborators SET first_seen=?,last_seen=?,"
                "last_activity=?,updated_at=?,updated_by=? WHERE store=? AND name_key=?",
                (min(starts) if starts else "",max(ends) if ends else "",
                 last["last_activity"] or "",now,actor["username"],store,target)
            )
            for alias in aliases:
                # Si otros nombres ya apuntaban al alias, reorientarlos
                # al principal para mantener un único destino y sin ciclos.
                con.execute(
                    "UPDATE operation_collaborator_aliases SET canonical_key=?,"
                    "changed_at=?,changed_by=? WHERE store=? AND canonical_key=?",
                    (target,now,actor["username"],store,alias)
                )
                con.execute(
                    "INSERT INTO operation_collaborator_aliases "
                    "(store,alias_key,canonical_key,changed_at,changed_by) "
                    "VALUES(?,?,?,?,?)",(store,alias,target,now,actor["username"])
                )
                con.execute(
                    "UPDATE operation_collaborators SET active=0,updated_at=?,updated_by=? "
                    "WHERE store=? AND name_key=?",
                    (now,actor["username"],store,alias)
                )
                con.execute(
                    "INSERT INTO operation_collaborator_admin_audit "
                    "(store,name_key,action,target_key,changed_at,changed_by) "
                    "VALUES(?,?,?,?,?,?)",
                    (store,alias,"Unificado",target,now,actor["username"])
                )
        return {"ok":True,"merged":len(aliases),
                "name":bykey[target]["name"],
                "message":f"{len(aliases)} variante(s) unificada(s). Sin modificar piezas ni capturas."}

    m._V402_COLLABORATOR_ADMIN=True
    print("[V402] Padrón: bajas múltiples y unificación auditada por tienda.",flush=True)
