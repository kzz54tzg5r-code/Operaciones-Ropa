"""V405 · Opción 4: Bitácora de accesos exclusiva del Super Administrador.

Registro persistente, sólo desde despliegue. No modifica credenciales.
IP anonimizada y navegador simplificado. Exportaciones y filtros protegidos.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta, time, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
import ipaddress
import re

from fastapi import HTTPException, Request
from fastapi.responses import Response

MX = ZoneInfo("America/Mexico_City")
EVENTS = {"login_success", "login_failed", "logout", "password_reset", "session_observed"}
LABELS = {
    "login_success":"Ingreso exitoso", "login_failed":"Intento fallido",
    "logout":"Cierre de sesión", "password_reset":"Contraseña restablecida",
    "session_observed":"Sesión vigente detectada",
}


def _mask_ip(request):
    """No guardar direcciones IP completas; no confiar en X-Forwarded-For."""
    raw=str(getattr(getattr(request,"client",None),"host","") or "")
    try:
        ip=ipaddress.ip_address(raw)
        if ip.version==4:
            return ".".join(raw.split(".")[:3]) + ".×"
        return ip.exploded.split(":")[0]+":…"
    except (ValueError,AttributeError):
        return "No disponible"


def _device(request):
    ua=str(request.headers.get("user-agent","") or "").lower()[:512]
    system=("Windows" if "windows" in ua else "Android" if "android" in ua
         else "iOS" if ("iphone" in ua or "ipad" in ua) else "macOS" if "mac os" in ua
         else "Linux" if "linux" in ua else "No identificado")
    browser=("Edge" if "edg/" in ua else "Chrome" if "chrome/" in ua
             else "Firefox" if "firefox/" in ua else "Safari" if "safari/" in ua
             else "Otro navegador")
    return system+" / "+browser


def init_db(m):
    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS user_access_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            user_id INTEGER,
            username TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            store TEXT NOT NULL DEFAULT '',
            event TEXT NOT NULL,
            device TEXT NOT NULL DEFAULT '',
            ip_mask TEXT NOT NULL DEFAULT ''
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_access_at ON user_access_events(occurred_at DESC)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_access_user_at ON user_access_events(username,occurred_at DESC)")


def record_event(m, request, event, username="", user=None):
    """Fallo de auditoría no bloquea login/logout ni guarda contraseñas."""
    if event not in EVENTS:
        return
    try:
        row=user or {}
        name=str(row["username"] if row else username or "").strip()[:120] or "No especificado"
        now=datetime.now(timezone.utc).isoformat(timespec="seconds")
        with m.db() as con:
            con.execute(
                "INSERT INTO user_access_events "
                "(occurred_at,user_id,username,role,store,event,device,ip_mask) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (now,row["id"] if row else None,name,
                 str(row["role"] if row else ""),str(row["store"] if row else ""),
                 event,_device(request),_mask_ip(request))
            )
        return True
    except Exception as exc:
        # No registrar usuarios, contraseñas ni IP en errores; informar clase.
        print("[V408] Auditoría no disponible: "+type(exc).__name__,flush=True)
        return False


def _window(period, reference):
    local=datetime.now(MX).date()
    if reference:
        try:
            local=date.fromisoformat(str(reference)[:10])
        except ValueError as exc:
            raise HTTPException(400,"Fecha inválida") from exc
    if period=="day":
        first=last=local
    elif period=="week":
        first=local-timedelta(days=local.weekday())
        last=first+timedelta(days=6)
    elif period=="month":
        first=local.replace(day=1)
        new=first.replace(year=first.year+1,month=1) if first.month==12 else first.replace(month=first.month+1)
        last=new-timedelta(days=1)
    else:
        raise HTTPException(400,"Periodo no válido")
    a=datetime.combine(first,time.min,MX).astimezone(timezone.utc)
    b=datetime.combine(last+timedelta(days=1),time.min,MX).astimezone(timezone.utc)
    return a.isoformat(timespec="seconds"),b.isoformat(timespec="seconds"),first.isoformat(),last.isoformat()


def _params(request, period, reference, username, role, store, page, page_size):
    if page<1 or page>100000 or page_size<1 or page_size>100:
        raise HTTPException(400,"Paginación inválida")
    first,last,d1,d2=_window(period,reference)
    conditions=["occurred_at>=?","occurred_at<?"]
    values=[first,last]
    for name,val in (("username",username),("role",role),("store",store)):
        if val and val!="all":
            if len(str(val))>120:
                raise HTTPException(400,"Filtro inválido")
            conditions.append(name+"=?")
            values.append(val)
    return " AND ".join(conditions),values,d1,d2


def query(m, period="day", reference="", username="", role="", store="", page=1,page_size=20):
    where,values,d1,d2=_params(None,period,reference,username,role,store,page,page_size)
    with m.db() as con:
        counts=con.execute(
            "SELECT COUNT(*) total, "
            "SUM(CASE WHEN event='login_success' THEN 1 ELSE 0 END) successful, "
            "SUM(CASE WHEN event='login_failed' THEN 1 ELSE 0 END) failed, "
            "SUM(CASE WHEN event='logout' THEN 1 ELSE 0 END) closed, "
            "SUM(CASE WHEN event='password_reset' THEN 1 ELSE 0 END) resets, "
            "COUNT(DISTINCT CASE WHEN event IN ('login_success','session_observed') THEN user_id END) unique_users, "
            "SUM(CASE WHEN event='session_observed' THEN 1 ELSE 0 END) observed "
            "FROM user_access_events WHERE "+where,values).fetchone()
        total=int(counts["total"] or 0)
        rows=[dict(x) for x in con.execute(
            "SELECT occurred_at,username,role,store,event,device,ip_mask "
            "FROM user_access_events WHERE "+where+" ORDER BY occurred_at DESC,id DESC LIMIT ? OFFSET ?",
            [*values,page_size,(page-1)*page_size]).fetchall()]
        recent=[dict(x) for x in con.execute(
            "SELECT username,role,store,MAX(occurred_at) latest,"
            "SUM(CASE WHEN event='login_success' THEN 1 ELSE 0 END) accesses,"
            "SUM(CASE WHEN event='session_observed' THEN 1 ELSE 0 END) observed "
            "FROM user_access_events WHERE "+where+" "
            "AND event IN ('login_success','session_observed') "
            "GROUP BY username,role,store ORDER BY latest DESC LIMIT 12",values).fetchall()]
        top=[dict(x) for x in con.execute(
            "SELECT username,COUNT(*) accesses FROM user_access_events WHERE "+where+
            " AND event='login_success' GROUP BY username ORDER BY accesses DESC,username LIMIT 8",
            values).fetchall()]
        alerts=[dict(x) for x in con.execute(
            "SELECT occurred_at,username,event,device FROM user_access_events WHERE "+
            where+" AND event IN ('login_failed','password_reset','logout') "
            "ORDER BY occurred_at DESC,id DESC LIMIT 6",values).fetchall()]
        active=[dict(x) for x in con.execute(
            "SELECT DISTINCT role,store FROM users WHERE active=1 ORDER BY role,store").fetchall()]
        users=[x[0] for x in con.execute("SELECT username FROM users ORDER BY username").fetchall()]
    return {
        "period":period,"from":d1,"to":d2,"total":total,
        "successful":int(counts["successful"] or 0),
        "failed":int(counts["failed"] or 0),
        "closed":int(counts["closed"] or 0),
        "resets":int(counts["resets"] or 0),
        "observed":int(counts["observed"] or 0),
        "unique_users":int(counts["unique_users"] or 0),
        "recent":recent,"top":top,"alerts":alerts,
        "rows":rows,"page":page,"page_size":page_size,"pages":max(1,(total+page_size-1)//page_size),
        "filters":{"users":users,"roles":sorted({r["role"] for r in active if r["role"]}),
                   "stores":sorted({r["store"] for r in active if r["store"]})},
        "tracking_since":(
            "Los inicios de sesión anteriores a la activación de la bitácora no se pueden recuperar. "
            "Una sesión ya abierta se registra como 'Sesión vigente detectada', "
            "sin contarse como nuevo ingreso."
        ),
    }


def install(m):
    if getattr(m,"_V405_USER_ACCESS",False): return
    init_db(m)

    def owner(request):
        m.require_real_superadmin(request)
        u=m.current_user(request)
        if not u or u.get("role")!="superadmin":
            raise HTTPException(403,"Abre la vista Super Administrador para consultar los accesos")

    @m.app.post("/api/access/session-observed-v408")
    def observe_authenticated_session(request: Request):
        """Anotar una sesión preexistente una sola vez, sin falsificar login."""
        row=m._session_user_row(request)
        if row is None:
            raise HTTPException(401,"Sesión requerida")
        if request.session.get("v408_audit_seen"):
            return {"ok":True,"recorded":False}
        saved=record_event(m,request,"session_observed",user=dict(row))
        if saved:
            # SessionMiddleware firma esta marca en la cookie del usuario.
            # Evita registros duplicados entre pestañas y recargas.
            request.session["v408_audit_seen"]=True
        return {"ok":bool(saved),"recorded":bool(saved)}

    @m.app.get("/api/admin/access-history-v405")
    def history(request:Request,period:str="day",reference:str="",
                username:str="",role:str="",store:str="",page:int=1,page_size:int=20):
        owner(request)
        return query(m,period,reference,username,role,store,page,page_size)

    @m.app.get("/api/admin/access-history-v405/export")
    def export(request:Request,format:str="xlsx",period:str="day",reference:str="",
               username:str="",role:str="",store:str=""):
        owner(request)
        if format not in ("xlsx","pdf"): raise HTTPException(400,"Formato inválido")
        where,values,d1,d2=_params(request,period,reference,username,role,store,1,20)
        with m.db() as con:
            rows=[dict(x) for x in con.execute(
                "SELECT occurred_at,username,role,store,event,device,ip_mask "
                "FROM user_access_events WHERE "+where+
                " ORDER BY occurred_at DESC,id DESC LIMIT 10000",values).fetchall()]
        data=[{
            "Fecha (UTC)":r["occurred_at"],"Usuario":r["username"],
            "Rol":r["role"],"Tienda":r["store"],"Tipo de acceso":LABELS.get(r["event"],r["event"]),
            "Dispositivo":r["device"],"IP anonimizada":r["ip_mask"]
        } for r in rows]
        stem="historial_accesos_"+d1+"_"+d2
        if format=="xlsx":
            with BytesIO() as stream:
                with m.pd.ExcelWriter(stream,engine="openpyxl") as writer:
                    m.pd.DataFrame(data,columns=[
                        "Fecha (UTC)","Usuario","Rol","Tienda","Tipo de acceso",
                        "Dispositivo","IP anonimizada"
                    ]).to_excel(writer,sheet_name="Historial de accesos",index=False)
                out=stream.getvalue()
            return Response(out,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            headers={"Content-Disposition":f'attachment; filename="{stem}.xlsx"',"Cache-Control":"no-store"})
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import landscape,letter
        from reportlab.lib import colors
        stream=BytesIO()
        c=canvas.Canvas(stream,pagesize=landscape(letter))
        W,H=landscape(letter)
        y=H-35
        def begin():
            nonlocal y
            c.setFillColor(colors.HexColor("#183F78"));c.rect(0,H-82,W,82,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont("Helvetica-Bold",17)
            c.drawString(28,H-49,"Historial de ingresos · Operaciones Ropa")
            c.setFont("Helvetica",9);c.drawString(28,H-68,f"Periodo: {d1} a {d2} · Sólo Super Administrador")
            y=H-103
            c.setFillColor(colors.HexColor("#164D87"));c.rect(24,y-23,W-48,23,fill=1,stroke=0)
            c.setFillColor(colors.white);c.setFont("Helvetica-Bold",8)
            for x,title in ((30,"Fecha (UTC)"),(170,"Usuario"),(305,"Rol"),(410,"Tienda"),(515,"Evento"),(647,"Dispositivo")):
                c.drawString(x,y-15,title)
            y-=23
        begin()
        def fit(t,w=18):
            s=str(t or "—");return s if len(s)<=w else s[:w-1]+"…"
        for i,r in enumerate(data):
            if y<39:
                c.showPage();begin()
            c.setFillColor(colors.white if i%2==0 else colors.HexColor("#ECF3FC"))
            c.rect(24,y-21,W-48,21,fill=1,stroke=0)
            c.setFillColor(colors.HexColor("#173B73"));c.setFont("Helvetica",8)
            for x,val,w in (
                (30,r["Fecha (UTC)"],25),(170,r["Usuario"],23),(305,r["Rol"],17),
                (410,r["Tienda"],15),(515,r["Tipo de acceso"],21),(647,r["Dispositivo"],24)
            ):
                c.drawString(x,y-14,fit(val,w))
            y-=21
        c.save()
        return Response(stream.getvalue(),media_type="application/pdf",
                        headers={"Content-Disposition":f'attachment; filename="{stem}.pdf"',"Cache-Control":"no-store"})
    m._V405_USER_ACCESS=True
    print("[V405] Historial de accesos: almacenamiento y consulta solo propietario.",flush=True)
