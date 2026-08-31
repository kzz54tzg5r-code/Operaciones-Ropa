
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import List
from datetime import datetime
from urllib.parse import urlparse
import hashlib, hmac, json, math, os, secrets, sqlite3, unicodedata, shutil, socket, asyncio, subprocess, sys, io, threading, re

# Compatibilidad Windows para este equipo:
# platform.machine() se bloquea por WMI; fijamos arquitectura antes de importar pandas.
import platform
if os.name == "nt":
    platform.machine = lambda: "AMD64"

import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas as pdfcanvas
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Persistencia compartida entre versiones locales.
# Puede sobreescribirse con OPERACIONES_ROPA_DATA en hosting.
if not os.environ.get("OPERACIONES_ROPA_DATA"):
    os.environ["OPERACIONES_ROPA_DATA"] = str(Path.home() / "OperacionesRopaData")

from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from commercial.storage import (
    load_manifest, load_snapshots, save_snapshot, save_pdf_upload,
    save_capacity_upload, save_sales_upload, resolve_entry_path, update_entry,
)
from commercial.parsers import extract_pdf_snapshot, read_capacity_file, read_sales_file

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"

PROJECT_STORES = (
    "Iztapalapa", "Vallejo", "Ecatepec", "Toluca", "Arco Norte",
    "Ixtapaluca", "Querétaro", "Centro", "Olivar", "León", "Puebla",
    "Puebla Sur", "Aguascalientes", "Veracruz", "Naucalpan", "Miravalle",
    "Atemajac",
)
PROJECT_STORE_SET = set(PROJECT_STORES)

DATA_ROOT = Path(os.environ.get("OPERACIONES_ROPA_DATA", ROOT / "data"))
DATA_ROOT.mkdir(parents=True, exist_ok=True)
DB = DATA_ROOT / "operaciones_ropa_users.sqlite3"
OPS_FILE = DATA_ROOT / "operaciones_ropa_operativo.json"
OPERATIONS_PARSER_VERSION = 40

# Cache de respuestas compactas para evitar recalcular el mismo reporte en cada clic.
_OPS_RESPONSE_CACHE = {}

SALES_PDF_FILE = DATA_ROOT / "ventas_pdf_procesadas.json"
LEGACY_DB = ROOT / "data" / "config" / "ps_operaciones.db"
STAGING_DIR = DATA_ROOT / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

def _cleanup_old_staging_files():
    """Elimina staging antiguo sin bloquear el inicio de la aplicación."""
    try:
        import time as _time
        now=_time.time()
        for _p in STAGING_DIR.glob("legacy_*.xlsx"):
            try:
                if now-_p.stat().st_mtime > 300:
                    _p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass

_cleanup_old_staging_files()


def _parse_operations_external(stage_path: Path, token: str) -> dict:
    """Procesa el Excel en un proceso Python separado.

    Esto evita que openpyxl/pandas bloqueen el proceso principal de FastAPI
    mientras se valida un archivo grande.
    """
    output_path = STAGING_DIR / f"{token}.worker.json"
    cmd = [sys.executable, str(ROOT / "operations_parse_worker.py"), str(stage_path), str(output_path)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=900,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("La validación excedió 15 minutos y fue cancelada.")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "Error desconocido").strip()
        raise RuntimeError(err[-4000:])
    if not output_path.exists():
        raise RuntimeError("El proceso de validación terminó sin generar resultados.")
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    finally:
        output_path.unlink(missing_ok=True)


def migrate_packaged_data_to_shared():
    """Migra una sola vez los datos incluidos en la versión anterior al directorio compartido.

    Nunca sobreescribe información ya persistida en el directorio compartido.
    """
    packaged=ROOT / "data"
    try:
        if DATA_ROOT.resolve()==packaged.resolve():
            return
    except Exception:
        pass
    if not packaged.exists():
        return
    for filename in ("operaciones_ropa_users.sqlite3","operaciones_ropa_operativo.json","ventas_pdf_procesadas.json"):
        src=packaged/filename; dst=DATA_ROOT/filename
        if not src.exists() or dst.exists():
            continue
        if filename=="operaciones_ropa_operativo.json":
            try:
                seed=json.loads(src.read_text(encoding="utf-8"))
                if str(seed.get("source_file") or "").lower().startswith("_test"):
                    continue
            except Exception:
                pass
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    src_commercial=packaged/"commercial"; dst_commercial=DATA_ROOT/"commercial"
    if src_commercial.exists():
        dst_commercial.mkdir(parents=True,exist_ok=True)
        for src in src_commercial.rglob("*"):
            if not src.is_file():
                continue
            rel=src.relative_to(src_commercial); dst=dst_commercial/rel
            if not dst.exists():
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(src,dst)

migrate_packaged_data_to_shared()

app = FastAPI(title="Operaciones Ropa", version="37.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("OPERACIONES_ROPA_SESSION_SECRET", secrets.token_hex(32)),
    same_site="lax",
    https_only=os.environ.get("OPERACIONES_ROPA_HTTPS_ONLY", "0") == "1",
)

ROLES = ("superadmin", "admin", "director", "tienda")

DEFAULT_GOALS = {
    "productividad_diaria": 784.0,
    "conversion": 80.0,
    "recuperacion": 80.0,
    "acondicionado_ingresos": 85.0,
    "ubicado_ingresos": 80.0,
    "recorridos_lunes": 5.0,
    "recorridos_martes": 5.0,
    "recorridos_miercoles": 5.0,
    "recorridos_jueves": 8.0,
    "recorridos_viernes": 8.0,
    "recorridos_sabado": 8.0,
    "recorridos_domingo": 8.0,
    "recorridos_semanales": 47.0,
}

GOAL_LABELS = {
    "productividad_diaria": "Productividad diaria",
    "conversion": "Conversión",
    "recuperacion": "Recuperación",
    "acondicionado_ingresos": "Acondicionado / Ingresos",
    "ubicado_ingresos": "Ubicado / Ingresos",
    "recorridos_lunes": "Recorridos · Lunes",
    "recorridos_martes": "Recorridos · Martes",
    "recorridos_miercoles": "Recorridos · Miércoles",
    "recorridos_jueves": "Recorridos · Jueves",
    "recorridos_viernes": "Recorridos · Viernes",
    "recorridos_sabado": "Recorridos · Sábado",
    "recorridos_domingo": "Recorridos · Domingo",
    "recorridos_semanales": "Recorridos semanales",
}

ROLE_LABELS = {
    "superadmin":"Super Administrador · Propietario",
    "admin":"Administrador",
    "director":"Director / Consulta",
    "tienda":"Tienda",
}

class UploadAdapter(BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data); self.name = name
    def getvalue(self): return super().getvalue()

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            store TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS system_state(
            id INTEGER PRIMARY KEY CHECK(id=1),
            status TEXT NOT NULL DEFAULT 'active',
            updated_at TEXT NOT NULL,
            updated_by TEXT DEFAULT ''
        )""")
        con.execute("INSERT OR IGNORE INTO system_state(id,status,updated_at,updated_by) VALUES(1,'active',?,?)", (datetime.now().isoformat(timespec='seconds'),'system'))
        con.execute("""CREATE TABLE IF NOT EXISTS goals(
            key TEXT PRIMARY KEY,
            value REAL NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT DEFAULT ''
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS stores(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            project INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS store_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER,
            action TEXT NOT NULL,
            old_name TEXT DEFAULT '',
            new_name TEXT DEFAULT '',
            old_active INTEGER,
            new_active INTEGER,
            old_project INTEGER,
            new_project INTEGER,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS model_checklist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week TEXT NOT NULL,
            store TEXT NOT NULL,
            id_art TEXT NOT NULL,
            model TEXT DEFAULT '',
            section TEXT DEFAULT '',
            rubro TEXT DEFAULT '',
            en_ubicacion INTEGER,
            cenefa_correcta INTEGER,
            todas_tallas INTEGER,
            exhibido INTEGER,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            UNIQUE(week,store,id_art)
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS upload_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            period_detected TEXT DEFAULT '',
            valid_records INTEGER NOT NULL DEFAULT 0,
            rejected_records INTEGER NOT NULL DEFAULT 0,
            rejection_reason TEXT DEFAULT '',
            published INTEGER NOT NULL DEFAULT 0
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS goal_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            old_value REAL NOT NULL,
            new_value REAL NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL
        )""")
        now=datetime.now().isoformat(timespec='seconds')
        for key,value in DEFAULT_GOALS.items():
            con.execute("INSERT OR IGNORE INTO goals(key,value,updated_at,updated_by) VALUES(?,?,?,?)",
                        (key,float(value),now,'system'))
        for store_name in PROJECT_STORES:
            con.execute(
                "INSERT OR IGNORE INTO stores(name,active,created_at,updated_at,updated_by) VALUES(?,?,?,?,?)",
                (store_name,1,now,now,'system')
            )

def ensure_user_security_columns():
    """Migra la tabla users sin perder cuentas existentes."""
    with db() as con:
        cols={str(r["name"]) for r in con.execute("PRAGMA table_info(users)").fetchall()}
        if "must_change_password" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
        if "session_version" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1")
        if "updated_at" not in cols:
            con.execute("ALTER TABLE users ADD COLUMN updated_at TEXT DEFAULT ''")

init_db()
ensure_user_security_columns()

def ensure_store_project_columns():
    """Agrega la selección Proyecto sin perder la configuración existente."""
    with db() as con:
        cols={str(r["name"]) for r in con.execute("PRAGMA table_info(stores)").fetchall()}
        if "project" not in cols:
            con.execute("ALTER TABLE stores ADD COLUMN project INTEGER NOT NULL DEFAULT 0")
        hcols={str(r["name"]) for r in con.execute("PRAGMA table_info(store_history)").fetchall()}
        if "old_project" not in hcols:
            con.execute("ALTER TABLE store_history ADD COLUMN old_project INTEGER")
        if "new_project" not in hcols:
            con.execute("ALTER TABLE store_history ADD COLUMN new_project INTEGER")

ensure_store_project_columns()


def get_goals():
    values = DEFAULT_GOALS.copy()
    with db() as con:
        rows = con.execute("SELECT key,value FROM goals").fetchall()
    for row in rows:
        values[str(row["key"])] = float(row["value"])
    return values

def get_goal_history(limit: int = 100):
    with db() as con:
        rows = con.execute(
            "SELECT id,key,old_value,new_value,changed_at,changed_by "
            "FROM goal_history ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()
    return [dict(r) for r in rows]

def update_goals(values: dict, username: str):
    current = get_goals()
    changed=[]
    now=datetime.now().isoformat(timespec='seconds')
    with db() as con:
        for key, raw in values.items():
            if key not in DEFAULT_GOALS:
                continue
            try:
                new=float(raw)
            except Exception:
                raise HTTPException(400, f"Valor inválido para {key}")
            if new < 0:
                raise HTTPException(400, f"La meta {key} no puede ser negativa")
            old=float(current.get(key, DEFAULT_GOALS[key]))
            if abs(old-new) < 1e-9:
                continue
            con.execute(
                "INSERT INTO goal_history(key,old_value,new_value,changed_at,changed_by) VALUES(?,?,?,?,?)",
                (key,old,new,now,username)
            )
            con.execute(
                "INSERT INTO goals(key,value,updated_at,updated_by) VALUES(?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at,updated_by=excluded.updated_by",
                (key,new,now,username)
            )
            changed.append({"key":key,"old":old,"new":new})
    return changed


def get_project_stores(active_only: bool = True, project_only: bool = False):
    query="SELECT id,name,active,project,created_at,updated_at,updated_by FROM stores"
    clauses=[]
    params=[]
    if active_only:
        clauses.append("active=1")
    if project_only:
        clauses.append("project=1")
    if clauses:
        query+=" WHERE "+" AND ".join(clauses)
    query+=" ORDER BY name"
    with db() as con:
        rows=con.execute(query,params).fetchall()
    return [dict(r) for r in rows]

def store_names(active_only: bool = True):
    """Tiendas activas disponibles en el sistema."""
    return [str(r["name"]) for r in get_project_stores(active_only=active_only, project_only=False)]

def project_store_names(active_only: bool = True):
    """Tiendas seleccionadas explícitamente como Proyecto."""
    return [str(r["name"]) for r in get_project_stores(active_only=active_only, project_only=True)]

def get_store_history(limit: int = 200):
    with db() as con:
        rows=con.execute(
            "SELECT id,store_id,action,old_name,new_name,old_active,new_active,old_project,new_project,changed_at,changed_by "
            "FROM store_history ORDER BY id DESC LIMIT ?",(int(limit),)
        ).fetchall()
    return [dict(r) for r in rows]

def save_store_change(actor: str, store_id: int|None, action: str, old_name="", new_name="", old_active=None, new_active=None, old_project=None, new_project=None):
    with db() as con:
        con.execute(
            "INSERT INTO store_history(store_id,action,old_name,new_name,old_active,new_active,old_project,new_project,changed_at,changed_by) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (store_id,action,old_name,new_name,old_active,new_active,old_project,new_project,datetime.now().isoformat(timespec="seconds"),actor)
        )

def _store_name_exists(name: str, exclude_id: int|None=None):
    key=login_key(name)
    with db() as con:
        rows=con.execute("SELECT id,name FROM stores").fetchall()
    return any(login_key(r["name"])==key and (exclude_id is None or int(r["id"])!=int(exclude_id)) for r in rows)


def user_count():
    with db() as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]

def system_status():
    with db() as con:
        row=con.execute("SELECT status,updated_at,updated_by FROM system_state WHERE id=1").fetchone()
    return dict(row) if row else {"status":"active","updated_at":"","updated_by":""}

def set_system_status(status: str, username: str):
    with db() as con:
        con.execute("UPDATE system_state SET status=?,updated_at=?,updated_by=? WHERE id=1",
                    (status,datetime.now().isoformat(timespec='seconds'),username))

def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240000)
    return f"{salt}${digest.hex()}"

def verify_password(password: str, stored: str):
    stored=str(stored or "")
    if stored.startswith("$argon2"):
        try:
            PasswordHasher().verify(stored,password)
            return True
        except (VerifyMismatchError, InvalidHashError, Exception):
            return False
    try:
        salt, expected = stored.split("$",1)
        got = hash_password(password, salt).split("$",1)[1]
        return hmac.compare_digest(got, expected)
    except Exception:
        return False

def login_key(value: str):
    text=unicodedata.normalize("NFD",str(value or ""))
    text="".join(c for c in text if unicodedata.category(c)!="Mn")
    return " ".join(text.casefold().strip().split())

def migrate_legacy_owner():
    """Importa el propietario ya existente del proyecto anterior sin cambiar su contraseña."""
    if not LEGACY_DB.exists():
        return
    with db() as con:
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
    try:
        old=sqlite3.connect(LEGACY_DB)
        old.row_factory=sqlite3.Row
        rows=old.execute(
            "SELECT nomina,nombre,correo,password_hash,role,permiso,activo FROM usuarios WHERE activo=1"
        ).fetchall()
        old.close()
    except Exception:
        return
    for r in rows:
        role_raw=str(r["role"] or "").upper()
        permiso=str(r["permiso"] or "").lower()
        if role_raw=="OWNER" or "propietario" in permiso:
            username=str(r["nombre"] or r["nomina"] or "Propietario").strip()
            pwd=str(r["password_hash"] or "")
            if not pwd:
                continue
            with db() as con:
                con.execute(
                    "INSERT OR IGNORE INTO users(username,password_hash,role,store,active,created_at) VALUES(?,?,?,?,?,?)",
                    (username,pwd,"superadmin","",1,datetime.now().isoformat(timespec="seconds"))
                )
            break

def find_login_user(username: str):
    key=login_key(username)
    with db() as con:
        rows=con.execute("SELECT * FROM users WHERE active=1").fetchall()
    for row in rows:
        if login_key(row["username"])==key:
            return row

    # También acepta nómina, nombre o correo del usuario heredado.
    if LEGACY_DB.exists():
        try:
            old=sqlite3.connect(LEGACY_DB)
            old.row_factory=sqlite3.Row
            legacy=old.execute(
                "SELECT nomina,nombre,correo,password_hash,role,permiso,activo FROM usuarios WHERE activo=1"
            ).fetchall()
            old.close()
            for r in legacy:
                aliases=[r["nomina"],r["nombre"],r["correo"]]
                if any(login_key(a)==key for a in aliases if a):
                    # Asegurar que exista en la tabla web.
                    role_raw=str(r["role"] or "").upper()
                    permiso=str(r["permiso"] or "").lower()
                    role="superadmin" if (role_raw=="OWNER" or "propietario" in permiso) else "admin"
                    uname=str(r["nombre"] or r["nomina"] or username).strip()
                    with db() as con:
                        con.execute(
                            "INSERT OR IGNORE INTO users(username,password_hash,role,store,active,created_at) VALUES(?,?,?,?,?,?)",
                            (uname,str(r["password_hash"] or ""),role,"",1,datetime.now().isoformat(timespec="seconds"))
                        )
                        return con.execute("SELECT * FROM users WHERE username=? AND active=1",(uname,)).fetchone()
        except Exception:
            pass
    return None


def current_user(request: Request):
    uid=request.session.get("uid")
    if not uid:
        return None
    with db() as con:
        row=con.execute("SELECT * FROM users WHERE id=? AND active=1",(uid,)).fetchone()
    if not row:
        request.session.clear()
        return None
    expected=int(row["session_version"] or 1) if "session_version" in row.keys() else 1
    actual=int(request.session.get("sv") or 0)
    if actual!=expected:
        request.session.clear()
        return None
    return {
        "id":row["id"],"username":row["username"],"role":row["role"],"store":row["store"],
        "must_change_password":bool(row["must_change_password"]) if "must_change_password" in row.keys() else False,
    }

def require_user(request: Request, roles=None):
    u = current_user(request)
    if not u: raise HTTPException(401, "Sesión requerida")
    state=system_status().get("status","active")
    if state in ("suspended","deleted") and u.get("role")!="superadmin":
        raise HTTPException(423, "Operaciones Ropa está suspendido por el propietario")
    if roles and u["role"] not in roles: raise HTTPException(403, "No autorizado")
    return u

def effective_store(user, requested="Compañía"):
    if user["role"] == "tienda":
        return user.get("store") or ""
    return requested or "Compañía"

def _week_rows(week: str | None):
    snaps = list(load_snapshots().values())
    weeks = sorted({str(s.get("week") or "") for s in snaps if s.get("week")}, reverse=True)
    selected = week or (weeks[0] if weeks else "")
    rows = [s for s in snaps if str(s.get("week") or "") == selected] if selected else snaps
    return selected, weeks, rows

def _sum(rows,key): return float(sum(float(r.get(key) or 0) for r in rows))

def _section_group_web(value: str) -> str:
    key=normalize_col(value)
    if "dama" in key: return "Dama"
    if "caballero" in key: return "Caballero"
    if any(x in key for x in ("nina","niña","nino","niño","beba","bebe","bebé","infantil")): return "Infantil"
    return "Sin sección"

def _section_summary(rows):
    """Consolida participación a nivel compañía usando los porcentajes publicados por cada PDF.

    Inventario se calcula directamente con existencia. Piezas y utilidad se ponderan
    con el SUG7 total de cada fuente para obtener una sola participación compañía,
    evitando sumar porcentajes de tiendas entre sí.
    """
    acc={}
    total_company_vpd=sum(float(s.get("vpd") or 0) for s in rows)
    total_company_exist=sum(float(s.get("existence") or 0) for s in rows)

    # métricas absolutas desde las filas de sección ya normalizadas
    for snap in rows:
        for r in snap.get("sections",[]) or []:
            sec=str(r.get("Sección") or r.get("Sección detalle") or "Sin sección")
            if sec.lower().startswith("total"): continue
            d=acc.setdefault(sec,{"section":sec,"existence":0.0,"suggested":0.0,"capacity":0.0,"floor":0.0,"warehouse":0.0,
                                  "_pieces_num":0.0,"_utility_num":0.0,"_reported_weight":0.0})
            d["existence"]+=float(r.get("Existencia") or 0); d["suggested"]+=float(r.get("VPD") or 0)
            d["capacity"]+=float(r.get("Curva") or 0); d["floor"]+=float(r.get("Piso") or 0); d["warehouse"]+=float(r.get("Bodega") or 0)

    # participaciones reportadas por tienda; Infantil suma Niña/Niño/Beba/Bebé
    for snap in rows:
        weight=float(snap.get("vpd") or 0)
        grouped={}
        for r in ((snap.get("breakdowns") or {}).get("section") or []):
            sec=_section_group_web(r.get("label") or r.get("section") or "")
            g=grouped.setdefault(sec,{"pieces":0.0,"utility":0.0})
            g["pieces"]+=float(r.get("pieces_share") or 0)
            g["utility"]+=float(r.get("utility_share") or 0)
        for sec,shares in grouped.items():
            d=acc.setdefault(sec,{"section":sec,"existence":0.0,"suggested":0.0,"capacity":0.0,"floor":0.0,"warehouse":0.0,
                                  "_pieces_num":0.0,"_utility_num":0.0,"_reported_weight":0.0})
            if weight>0:
                d["_pieces_num"] += weight * shares["pieces"] / 100.0
                d["_utility_num"] += weight * shares["utility"] / 100.0
                d["_reported_weight"] += weight

    for d in acc.values():
        d["ddi"]=d["existence"]/d["suggested"] if d["suggested"] else 0
        d["occupancy"]=d["existence"]/d["capacity"]*100 if d["capacity"] else 0
        d["part_inventory"]=d["existence"]/total_company_exist*100 if total_company_exist else 0
        if total_company_vpd:
            d["part_pieces"]=d["_pieces_num"]/total_company_vpd*100 if d["_reported_weight"] else d["suggested"]/total_company_vpd*100
            d["utility"]=d["_utility_num"]/total_company_vpd*100 if d["_reported_weight"] else None
        else:
            d["part_pieces"],d["utility"]=0,None
        for k in ("_pieces_num","_utility_num","_reported_weight"): d.pop(k,None)
    order={"Dama":0,"Caballero":1,"Infantil":2,"Sin sección":9}
    return sorted(acc.values(),key=lambda x:(order.get(x["section"],8),x["section"]))

def _location_summary(rows):
    acc={}
    for snap in rows:
        for r in snap.get("locations",[]) or []:
            loc=str(r.get("Ubicación") or r.get("Ubicación detalle") or "Sin ubicación")
            if loc.lower().startswith("total"): continue
            d=acc.setdefault(loc,{"location":loc,"existence":0.0,"suggested":0.0,"capacity":0.0,"floor":0.0,"warehouse":0.0})
            d["existence"]+=float(r.get("Existencia") or 0); d["suggested"]+=float(r.get("VPD") or 0)
            d["capacity"]+=float(r.get("Curva") or 0); d["floor"]+=float(r.get("Piso") or 0); d["warehouse"]+=float(r.get("Bodega") or 0)
    for d in acc.values():
        d["ddi"]=d["existence"]/d["suggested"] if d["suggested"] else 0
        d["occupancy"]=d["existence"]/d["capacity"]*100 if d["capacity"] else 0
    return sorted(acc.values(),key=lambda x:-x["suggested"])

def _model_rows(rows, slow=False):
    """
    Ranking consolidado por modelo.

    - Lentos: usa exclusivamente el escenario real 'Baja rotación'.
    - Campeones: usa Sugerido/VPD como fuente principal y complementa candidatos
      con Utilidad/Baja rotación cuando un PDF no publicó tabla de Sugerido para
      Caballero o Infantil. Para evitar doble conteo entre escenarios se toma
      un único registro por tienda + ID_ART, conservando el VPD real disponible.
    """
    acc={}
    investment={}

    for snap in rows:
        for r in snap.get("model_rankings",[]) or []:
            if r.get("scenario")!="Inversión":
                continue
            ident=str(r.get("article_id") or "").strip()
            store=str(r.get("store") or snap.get("store") or "").strip()
            if ident:
                investment[(login_key(store),ident)]=max(
                    investment.get((login_key(store),ident),0.0),
                    float(r.get("investment") or 0)
                )

    # Candidatos por tienda/modelo para no sumar el mismo modelo varias veces
    # cuando aparece en distintas tablas del mismo PDF.
    store_model={}
    preferred={"Sugerido / VPD":3,"Utilidad":2,"Baja rotación":1}
    for snap in rows:
        snap_store=str(snap.get("store") or "")
        for r in snap.get("model_rankings",[]) or []:
            scenario=str(r.get("scenario") or "")
            if slow:
                if scenario!="Baja rotación":
                    continue
            else:
                if scenario not in preferred:
                    continue
            ident=str(r.get("article_id") or "").strip()
            if not ident:
                continue
            store=str(r.get("store") or snap_store).strip()
            key=(login_key(store),ident)
            candidate={
                "id_art":ident,
                "model":r.get("model") or ident,
                "brand":r.get("brand") or "",
                "section":_norm_section_name(r.get("world") or r.get("world_detail") or ""),
                "rubro":r.get("subcategory") or "",
                "suggested":float(r.get("vpd") or 0),
                "existence":float(r.get("existence") or (float(r.get("floor") or 0)+float(r.get("warehouse") or 0))),
                "floor":float(r.get("floor") or 0),
                "warehouse":float(r.get("warehouse") or 0),
                "utility":float(r.get("utility_share") or 0),
                "investment":investment.get(key,0.0),
                "_priority":preferred.get(scenario,1),
                "store":store,
            }
            current=store_model.get(key)
            if current is None:
                store_model[key]=candidate
            else:
                # Preferir la tabla Sugerido/VPD; si no, conservar el registro
                # que tenga mayor información real.
                score=(candidate["_priority"],candidate["suggested"],candidate["existence"])
                oldscore=(current["_priority"],current["suggested"],current["existence"])
                if score>oldscore:
                    store_model[key]=candidate

    for d0 in store_model.values():
        ident=d0["id_art"]
        d=acc.setdefault(ident,{
            "id_art":ident,"model":d0["model"],"brand":d0["brand"],
            "section":d0["section"],"rubro":d0["rubro"],
            "suggested":0.0,"existence":0.0,"floor":0.0,"warehouse":0.0,
            "investment":0.0,"utility":0.0,"stores":set()
        })
        d["suggested"]+=d0["suggested"]
        d["existence"]+=d0["existence"]
        d["floor"]+=d0["floor"]
        d["warehouse"]+=d0["warehouse"]
        d["investment"]+=d0["investment"]
        d["utility"]+=d0["utility"]
        if d0["store"]:
            d["stores"].add(d0["store"])

    vals=[]
    for ident,d in acc.items():
        d["ddi"]=d["existence"]/d["suggested"] if d["suggested"] else 0
        d["store_count"]=len(d.pop("stores"))
        vals.append(d)

    if slow:
        vals.sort(key=lambda x:(x["suggested"],-x["existence"],x["id_art"]))
        return vals[:20]

    vals.sort(key=lambda x:(-x["suggested"],-x["existence"],x["id_art"]))
    return vals[:50]

_OPS_DATA_CACHE={"stamp":None,"data":None}
_OPS_META_CACHE={"stamp":None,"data":None}
OPS_RECOVERY_CACHE_FILE = DATA_ROOT / "operaciones_recovery_fifo_cache.json"
OPS_META_CACHE_FILE = DATA_ROOT / "operaciones_meta_cache.json"

def load_ops():
    if not OPS_FILE.exists():
        _OPS_DATA_CACHE["stamp"]=None
        _OPS_DATA_CACHE["data"]={"rows":[],"uploaded_at":None}
        return _OPS_DATA_CACHE["data"]
    try:
        stamp=OPS_FILE.stat().st_mtime_ns
    except Exception:
        stamp=None
    if _OPS_DATA_CACHE.get("stamp")==stamp and isinstance(_OPS_DATA_CACHE.get("data"),dict):
        return _OPS_DATA_CACHE["data"]
    try:
        data=json.loads(OPS_FILE.read_text(encoding="utf-8"))
        _OPS_DATA_CACHE["stamp"]=stamp
        _OPS_DATA_CACHE["data"]=data
        return data
    except Exception:
        return {"rows":[],"uploaded_at":None}

def _ops_source_stamp():
    try:
        return OPS_FILE.stat().st_mtime_ns if OPS_FILE.exists() else 0
    except Exception:
        return 0


def _build_operations_meta(data: dict, stamp: int=0):
    rows=list(data.get("rows",[]) or [])
    embedded=data.get("meta_index") if isinstance(data.get("meta_index"),dict) else {}

    dates=list(embedded.get("available_dates") or [])
    weeks=list(embedded.get("available_weeks") or data.get("weeks") or [])
    months=list(embedded.get("available_months") or data.get("months") or [])
    stores=list(embedded.get("stores") or [])
    areas=list(embedded.get("areas") or [])
    activities=list(embedded.get("activities") or [])

    # Compatibilidad con archivos ya publicados antes de V38: sólo se recorre
    # la base una vez para construir este índice liviano y después se reutiliza.
    if not dates:
        dates=sorted({str(r.get("date")) for r in rows if r.get("date")})
    if not weeks:
        weeks=sorted({
            f"{int(r.get('year_iso'))}-W{int(r.get('week_iso')):02d}"
            for r in rows if r.get("year_iso") and r.get("week_iso")
        })
    if not months:
        months=sorted({str(r.get("month") or str(r.get("date") or "")[:7]) for r in rows if r.get("month") or r.get("date")})
    if not stores:
        stores=sorted({str(r.get("store") or "").strip() for r in rows if str(r.get("store") or "").strip()})
    if not areas:
        areas=sorted({str(r.get("area") or "").strip() for r in rows if str(r.get("area") or "").strip()})
    if not activities:
        activities=sorted({str(r.get("activity") or "").strip() for r in rows if str(r.get("activity") or "").strip()})

    return {
        "source_stamp":stamp,
        "available":bool(rows or data.get("commercial_daily")),
        "uploaded_at":data.get("uploaded_at"),
        "source_file":data.get("source_file","") or "",
        "operational_sheet":data.get("operational_sheet","") or "",
        "operational_sheets":data.get("operational_sheets",[]) or [],
        "monthly_sheets":data.get("monthly_sheets",[]) or [],
        "duplicate_rows_removed":int(data.get("duplicate_rows_removed") or 0),
        "available_dates":dates,
        "available_weeks":weeks,
        "available_months":months,
        "areas_available":areas,
        "activities_available":activities,
        "stores_detected":stores,
        "parser_version":int(data.get("parser_version") or 0),
        "valid_records":len(rows),
        "rejected_records":len(data.get("rejected_rows") or []),
    }


def load_operations_meta():
    stamp=_ops_source_stamp()
    if _OPS_META_CACHE.get("stamp")==stamp and isinstance(_OPS_META_CACHE.get("data"),dict):
        return _OPS_META_CACHE["data"]

    # Arranque rápido: leer primero el archivo de metadatos, que es pequeño.
    try:
        if OPS_META_CACHE_FILE.exists():
            cached=json.loads(OPS_META_CACHE_FILE.read_text(encoding="utf-8"))
            if int(cached.get("source_stamp") or 0)==int(stamp):
                _OPS_META_CACHE["stamp"]=stamp
                _OPS_META_CACHE["data"]=cached
                return cached
    except Exception:
        pass

    data=load_ops()
    meta=_build_operations_meta(data,stamp)
    _OPS_META_CACHE["stamp"]=stamp
    _OPS_META_CACHE["data"]=meta
    try:
        OPS_META_CACHE_FILE.write_text(_safe_json_dump(meta),encoding="utf-8")
    except Exception:
        pass
    return meta


def _clear_operations_caches(clear_meta_file: bool=False):
    _OPS_RESPONSE_CACHE.clear()
    _OPS_DATA_CACHE["stamp"]=None
    _OPS_DATA_CACHE["data"]=None
    _OPS_META_CACHE["stamp"]=None
    _OPS_META_CACHE["data"]=None
    if clear_meta_file:
        try: OPS_META_CACHE_FILE.unlink(missing_ok=True)
        except Exception: pass


def normalize_col(s):
    import unicodedata
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower().strip()
    return " ".join(s.replace("_"," ").split())

def _excel_engine_candidates(path: Path):
    return ["calamine", "openpyxl"] if path.suffix.lower()==".xlsx" else ["calamine", "xlrd"]

def _read_excel_sheets_robust(path: Path):
    last=None
    for engine in _excel_engine_candidates(path):
        try:
            return pd.read_excel(path,sheet_name=None,engine=engine)
        except Exception as exc:
            last=exc
    raise ValueError(f"No fue posible abrir el Excel ({path.suffix}). Detalle: {last}")

def _detect_header(raw: pd.DataFrame) -> int:
    keys=("actividad","numero de piezas","número de piezas","piezas","tienda","fecha","nombre","recorridos")
    best=(0,-1)
    for i,row in raw.head(25).iterrows():
        vals=[normalize_col(v) for v in row.tolist() if str(v)!="nan"]
        score=sum(any(k in v for k in keys) for v in vals)
        if score>best[1]: best=(int(i),score)
    return best[0]


def _safe_date_iso(value):
    dt=pd.to_datetime(value,errors="coerce")
    if pd.isna(dt) and value is not None:
        text=normalize_col(value)
        weekdays=("lunes","martes","miercoles","jueves","viernes","sabado","domingo")
        for wd in weekdays:
            text=re.sub(rf"^{wd},?\s*","",text)
        month_map={
            "enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06",
            "julio":"07","agosto":"08","septiembre":"09","setiembre":"09","octubre":"10",
            "noviembre":"11","diciembre":"12"
        }
        m=re.search(r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})\b",text)
        if m and m.group(2) in month_map:
            dt=pd.to_datetime(f"{m.group(3)}-{month_map[m.group(2)]}-{int(m.group(1)):02d}",errors="coerce")
    if pd.isna(dt):
        return "", None, None, ""
    iso=dt.isocalendar()
    return dt.date().isoformat(), int(iso.week), int(iso.year), dt.strftime("%Y-%m")

def _detect_operational_sheets(names):
    """Todas las hojas operativas cuyo nombre normalizado inicia con Resultados [de] productividad."""
    out=[]
    for name in names:
        key=normalize_col(name)
        if key.startswith("resultados productividad") or key.startswith("resultados de productividad"):
            out.append(name)
    return out

def _detect_operational_sheet(names):
    # Compatibilidad con llamadas antiguas.
    sheets=_detect_operational_sheets(names)
    return sheets[0] if sheets else None

def _monthly_sheet_name(name):
    key=normalize_col(name)
    months=("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre")
    return any(m in key for m in months) and ("26" in key or "2026" in key)

def _normalize_store_value(value):
    text=str(value or "").strip()
    if text.lower() in ("nan","none"):
        return ""
    try:
        from commercial.parsers import canon_store
        return canon_store(text)
    except Exception:
        return text


def _clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text=" ".join(str(value).split()).strip()
    return "" if normalize_col(text) in ("nan","none") else text


def _clean_occurrence(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value,(int,np.integer)):
        return str(int(value))
    if isinstance(value,(float,np.floating)) and math.isfinite(float(value)) and float(value).is_integer():
        return str(int(value))
    text=str(value).strip()
    if normalize_col(text) in ("nan","none"):
        return ""
    if re.fullmatch(r"\d+\.0+",text):
        return text.split(".",1)[0]
    return text


def _activity_class(value):
    original=" ".join(str(value or "").split()).strip()
    n=normalize_col(original)
    if "recoleccion" in n and "muerto" in n:
        return "Recolección de muertos"
    if "mantenimiento" in n and "mesa" in n:
        return "Mantenimiento Mesas"
    if "acondicion" in n or "habilitad" in n or n.startswith("habilitar"):
        return "Acondicionado"
    if n=="ubicado" or n.startswith("ubicar") or " ubicado" in f" {n}":
        return "Ubicado"
    return original


def _motive_class(value):
    original=" ".join(str(value or "").split()).strip()
    n=normalize_col(original)
    if "muerto" in n:
        return "Muertos"
    if "probador" in n or "aduana" in n:
        return "Probador"
    if "caja" in n:
        return "Cajas"
    if "sistema" in n or "devolucion" in n or re.search(r"(^|\s)dev($|\s)",n):
        return "Sistema/Devoluciones"
    return "Sin clasificar"


def _time_to_minutes(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value,datetime):
        return value.hour*60+value.minute+value.second/60
    if hasattr(value,"hour") and hasattr(value,"minute"):
        return value.hour*60+value.minute+getattr(value,"second",0)/60
    if isinstance(value,(float,int,np.floating,np.integer)) and 0 <= float(value) < 1:
        return float(value)*24*60
    text=str(value).strip()
    m=re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$",text)
    if not m:
        return None
    h,mi,se=int(m.group(1)),int(m.group(2)),int(m.group(3) or 0)
    if h>23 or mi>59 or se>59:
        return None
    return h*60+mi+se/60


def _duration_hours(start,end):
    a=_time_to_minutes(start); b=_time_to_minutes(end)
    if a is None or b is None:
        return None
    if b<a:
        b+=24*60
    hours=(b-a)/60
    return hours if 0 <= hours <= 24 else None



def _staff_lookup_from_template(path: Path, sheet_names):
    """Mapa de nómina y alias abreviados -> nombre completo usando la hoja Plantilla."""
    plantilla=next((s for s in sheet_names if normalize_col(s)=="plantilla"),None)
    by_nomina={}; by_store_alias={}
    if not plantilla:
        return {"by_nomina":by_nomina,"by_store_alias":by_store_alias}
    frame=None
    for engine in _excel_engine_candidates(path):
        try:
            frame=pd.read_excel(path,sheet_name=plantilla,engine=engine)
            break
        except Exception:
            pass
    if frame is None or frame.empty:
        return {"by_nomina":by_nomina,"by_store_alias":by_store_alias}
    frame.columns=[str(c).strip() for c in frame.columns]
    cols={normalize_col(c):c for c in frame.columns}
    c_store=cols.get("tienda"); c_name=cols.get("nombre"); c_nom=cols.get("nomina") or cols.get("nómina")
    if not c_name:
        return {"by_nomina":by_nomina,"by_store_alias":by_store_alias}
    for _,r in frame.iterrows():
        full=_clean_text(r.get(c_name)); store=_normalize_store_value(r.get(c_store)) if c_store else ""
        nom=_clean_occurrence(r.get(c_nom)) if c_nom else ""
        if not full: continue
        if nom: by_nomina[nom]=full
        nfull=normalize_col(full)
        tokens=[t for t in nfull.split() if len(t)>=3]
        aliases=set(tokens)
        if tokens:
            aliases.add(tokens[0])
            aliases.add(tokens[-1])
        # nombres compuestos frecuentes: 'del rosario', 'maria teresa', etc.
        for i in range(len(tokens)-1): aliases.add(tokens[i]+" "+tokens[i+1])
        for alias in aliases:
            by_store_alias.setdefault((normalize_col(store),alias),set()).add(full)
    return {"by_nomina":by_nomina,"by_store_alias":by_store_alias}


def _resolve_staff_name(raw_name, store, lookup):
    text=_clean_text(raw_name)
    if not text: return ""
    # Formato de Resultados productividad 2: "138550, Nombre Completo"
    cleaned=text.strip('"').strip()
    m=re.match(r"^\s*(\d+)\s*[,;\-]\s*(.+?)\s*$",cleaned)
    if m:
        nom=m.group(1); supplied=_clean_text(m.group(2))
        return lookup.get("by_nomina",{}).get(nom) or supplied
    if re.fullmatch(r"\d+",cleaned):
        return lookup.get("by_nomina",{}).get(cleaned) or cleaned
    key=normalize_col(cleaned); st=normalize_col(store)
    # Si ya parece nombre completo, conservarlo.
    if len(key.split())>=2:
        return cleaned
    candidates=[]
    for (kst,alias),names in lookup.get("by_store_alias",{}).items():
        if kst!=st: continue
        if alias==key or alias.startswith(key) or key.startswith(alias):
            candidates.extend(list(names))
    uniq=sorted(set(candidates))
    return uniq[0] if len(uniq)==1 else cleaned

def _dedupe_operational_rows(rows):
    """Elimina sólo filas completamente iguales a nivel operativo; occurrence por sí solo nunca deduplica piezas."""
    seen=set(); out=[]; removed=0
    for r in rows:
        key=(
            r.get("store",""),r.get("date",""),r.get("occurrence",""),
            normalize_col(r.get("activity_original",r.get("activity",""))),
            normalize_col(r.get("area","")),float(r.get("pieces") or 0),
            str(r.get("start_time") or ""),str(r.get("end_time") or ""),
            normalize_col(r.get("name","")),normalize_col(r.get("reason","")),
            normalize_col(r.get("table","")),float(r.get("recorridos") or 0),
        )
        if key in seen:
            removed+=1
            continue
        seen.add(key); out.append(r)
    return out,removed

def _read_operational_sheet(path: Path, sheet: str, staff_lookup=None):
    last_error=None
    df=None
    for engine in _excel_engine_candidates(path):
        try:
            df=pd.read_excel(path,sheet_name=sheet,engine=engine)
            break
        except Exception as exc:
            last_error=exc
    if df is None:
        raise ValueError(f"No se pudo abrir la hoja operativa '{sheet}': {last_error}")
    df.columns=[str(c).replace("\x00","").strip() for c in df.columns]

    normalized={normalize_col(c):c for c in df.columns}
    header_tokens=("fecha s","fecha","occurrence","ocurrencia","ocurrense","tienda","ubicacion","tabla","actividad realizada","area",
                   "numero de piezas","hora inicio","hora fin","nombre","nomina","motivo de ingreso","ingreso al area de acondicionado","recorridos")
    if sum(1 for t in header_tokens if normalize_col(t) in normalized) < 4:
        raw=None
        for engine in _excel_engine_candidates(path):
            try:
                raw=pd.read_excel(path,sheet_name=sheet,header=None,engine=engine)
                break
            except Exception:
                pass
        if raw is not None and not raw.empty:
            best_row=0; best_score=-1
            for i in range(min(25,len(raw))):
                vals=[normalize_col(v) for v in raw.iloc[i].tolist()]
                score=sum(any(tok==v or tok in v for tok in header_tokens) for v in vals if v)
                if score>best_score:
                    best_score=score; best_row=i
            if best_score>=4:
                headers=[]; seen={}
                for j,v in enumerate(raw.iloc[best_row].tolist()):
                    name=str(v).replace("\x00","").strip()
                    if not name or name.lower()=="nan": name=f"Columna {j+1}"
                    base=name; n=2
                    while name in seen:
                        name=f"{base} {n}"; n+=1
                    seen[name]=1; headers.append(name)
                df=raw.iloc[best_row+1:].copy(); df.columns=headers; df=df.dropna(how="all")

    rename={}
    for c in df.columns:
        cl=normalize_col(c)
        if cl in ("occurrence","ocurrencia","ocurrense"):
            rename[c]="Ocurrencia"
        elif cl in ("tienda","sucursal","ubicacion","ubicación"):
            rename[c]="Tienda"
        elif cl=="fecha":
            rename[c]="Fecha"
        elif cl in ("fecha s","fechas","fecha base"):
            rename[c]="Fecha s"
        elif cl=="tabla":
            rename[c]="Tabla"
        elif cl in ("actividad realizada","actividad"):
            rename[c]="Actividad Realizada"
        elif cl=="area":
            rename[c]="Área"
        elif cl in ("numero de piezas","piezas","pzas","cantidad"):
            rename[c]="Número de Piezas"
        elif cl in ("hora inicio","hora de inicio","inicio"):
            rename[c]="Hora Inicio"
        elif cl in ("hora fin","hora de fin","fin"):
            rename[c]="Hora Fin"
        elif cl in ("nombre","usuario","colaborador","nombre real","nombre colaborador","nomina") or cl.startswith("nomb"):
            if "Nombre" not in rename.values(): rename[c]="Nombre"
        elif cl in ("motivo de ingreso","motivo","ingreso al area de acondicionado","ingreso al area acondicionado"):
            rename[c]="Motivo de ingreso"
        elif cl in ("recorridos","recorrido","rec"):
            rename[c]="RECORRIDOS"
    df=df.rename(columns=rename)
    df=df.loc[:,~df.columns.duplicated()]

    original_columns=list(df.columns)
    required=["Fecha s","Fecha","Ocurrencia","Tienda","Tabla","Actividad Realizada","Área",
              "Número de Piezas","Hora Inicio","Hora Fin","Nombre","Motivo de ingreso","RECORRIDOS"]
    missing_columns=[c for c in required if c not in df.columns]
    for col in missing_columns: df[col]=np.nan

    rows=[]; rejected=[]; issues=[]
    for row_index,r in df.iterrows():
        act_original=_clean_text(r.get("Actividad Realizada"))
        activity=_activity_class(act_original)
        reason=_clean_text(r.get("Motivo de ingreso"))
        store=_normalize_store_value(r.get("Tienda"))
        occ=_clean_occurrence(r.get("Ocurrencia"))
        name=_resolve_staff_name(r.get("Nombre"),store,staff_lookup or {"by_nomina":{},"by_store_alias":{}})
        area=_clean_text(r.get("Área"))
        table=_clean_text(r.get("Tabla"))
        start_time=r.get("Hora Inicio"); end_time=r.get("Hora Fin")

        # Fecha principal: la columna Fecha de la captura; Fecha s es respaldo operativo.
        raw_date=r.get("Fecha")
        if raw_date is None or pd.isna(raw_date): raw_date=r.get("Fecha s")
        date_iso,week_iso,year_iso,month_key=_safe_date_iso(raw_date)

        pcs_raw=pd.to_numeric(r.get("Número de Piezas"),errors="coerce")
        has_identity=bool(act_original or reason or store or occ or name or table)
        if not has_identity: continue

        row_errors=[]
        if not store: row_errors.append("Tienda vacía")
        if not date_iso: row_errors.append("Fecha inválida")
        if pd.isna(pcs_raw): row_errors.append("Número de Piezas no numérico")
        if not act_original: row_errors.append("Actividad Realizada vacía")
        if row_errors:
            rejected.append({"sheet":sheet,"row":int(row_index)+2,"store":store,"occurrence":occ,
                             "activity":act_original,"reason":reason,"errors":row_errors})
            continue

        pcs=float(pcs_raw)
        if not math.isfinite(pcs):
            rejected.append({"sheet":sheet,"row":int(row_index)+2,"store":store,"occurrence":occ,
                             "activity":act_original,"reason":reason,"errors":["Número de Piezas no finito"]})
            continue

        is_recorrido_table="recorrido" in normalize_col(table)
        if not occ:
            issues.append({"sheet":sheet,"row":int(row_index)+2,"store":store,"activity":act_original,
                           "warning":"Ocurrencia vacía; la fila suma piezas pero no cuenta como recorrido."})

        is_recoleccion=(activity=="Recolección de muertos")
        is_ingreso=(normalize_col(act_original)=="ingreso")
        is_operational_input=is_recoleccion or is_ingreso
        motive=_motive_class(reason) if is_operational_input else "No aplica"
        muertos=pcs if is_operational_input and motive=="Muertos" else 0.0
        probador=pcs if is_operational_input and motive=="Probador" else 0.0
        cajas=pcs if is_operational_input and motive=="Cajas" else 0.0
        sistema_devoluciones=pcs if is_operational_input and motive=="Sistema/Devoluciones" else 0.0
        sin_clasificar=pcs if is_operational_input and motive=="Sin clasificar" else 0.0
        recolectadas=pcs if is_operational_input else 0.0
        acondicionado=pcs if activity=="Acondicionado" else 0.0
        ubicado=pcs if activity=="Ubicado" else 0.0
        duration=_duration_hours(start_time,end_time)
        recorridos_raw=pd.to_numeric(r.get("RECORRIDOS"),errors="coerce")
        has_recorridos_column=("RECORRIDOS" in original_columns)
        recorrido_key=f"{store}|{date_iso}|{occ}" if is_recorrido_table and occ else ""
        recorrido_count=float(recorridos_raw) if not pd.isna(recorridos_raw) else 0.0

        rows.append({
            "sheet":sheet,"occurrence":occ,"store":store,"date":date_iso,
            "week_iso":week_iso,"year_iso":year_iso,"month":month_key,
            "table":table,"activity":activity,"activity_original":act_original,
            "area":area,"pieces":pcs,"name":name,"reason":reason,"motive_class":motive,
            "start_time":"" if pd.isna(start_time) else str(start_time),
            "end_time":"" if pd.isna(end_time) else str(end_time),
            "hours_used":duration,"is_recorrido_table":bool(is_recorrido_table),"recorrido_key":recorrido_key,
            "has_recorridos_column":bool(has_recorridos_column),
            "muertos":muertos,"probador":probador,"cajas":cajas,
            "sistema_devoluciones":sistema_devoluciones,"sin_clasificar":sin_clasificar,
            "recolectadas":recolectadas,"acondicionado":acondicionado,"ubicado":ubicado,
            "recorridos":recorrido_count,
            "productividad":recolectadas+acondicionado+ubicado
        })
    return rows, original_columns, rejected, issues, missing_columns

def _num_series(series):
    return pd.to_numeric(series,errors="coerce").fillna(0)

def _parse_monthly_commercial(path: Path, sheet: str):
    raw=None; last=None
    for engine in _excel_engine_candidates(path):
        try:
            raw=pd.read_excel(path,sheet_name=sheet,header=None,engine=engine)
            break
        except Exception as exc:
            last=exc
    if raw is None:
        raise ValueError(f"No se pudo abrir {sheet}: {last}")
    if raw.shape[1] < 29 or raw.shape[0] < 3:
        return [], []

    data=raw.iloc[2:].copy().dropna(how="all")
    if data.empty:
        return [], []

    def col(i):
        if i < data.shape[1]:
            return data.iloc[:,i]
        return pd.Series([np.nan]*len(data),index=data.index)

    id_art=col(1).astype(str).replace("nan","")
    modelo=col(4).astype(str).replace("nan","")
    color=col(7).astype(str).replace("nan","")
    categoria=col(19).astype(str).replace("nan","")
    subcat=col(20).astype(str).replace("nan","")
    tienda=col(25).apply(_normalize_store_value)
    precio_men=_num_series(col(24))
    vta_pzs=_num_series(col(26))
    dev_pzs=_num_series(col(27))
    vta_imp=_num_series(col(28))
    costo=precio_men*dev_pzs
    costo=np.where(costo>0,costo,vta_imp)

    monthly=[]
    for pos in range(len(data)):
        vp=float(vta_pzs.iloc[pos]); dp=float(dev_pzs.iloc[pos]); vi=float(vta_imp.iloc[pos]); co=float(costo[pos])
        if vp==0 and dp==0 and vi==0:
            continue
        monthly.append({
            "month_source":sheet,"id_art":str(id_art.iloc[pos]),"model":str(modelo.iloc[pos]),
            "color":str(color.iloc[pos]),"category":str(categoria.iloc[pos]),
            "subcategory":str(subcat.iloc[pos]),"store":str(tienda.iloc[pos]),
            "vta_pzs":vp,"dev_pzs":dp,"vta_imp":vi,"costo_dev":co,
            "sold_validated":min(vp,dp),
        })

    daily=[]
    for j in range(29,raw.shape[1],3):
        if j+2>=raw.shape[1]:
            continue
        fecha=pd.to_datetime(raw.iloc[0,j],errors="coerce",dayfirst=True)
        if pd.isna(fecha):
            continue
        vp=_num_series(col(j)); dp=_num_series(col(j+1)); vi=_num_series(col(j+2))
        co=precio_men*dp
        co=np.where(co>0,co,vi)
        iso=fecha.isocalendar()
        for pos in range(len(data)):
            a=float(vp.iloc[pos]); b=float(dp.iloc[pos]); c=float(vi.iloc[pos]); cost=float(co[pos])
            if a==0 and b==0 and c==0:
                continue
            daily.append({
                "month_source":sheet,"date":fecha.date().isoformat(),
                "week_iso":int(iso.week),"year_iso":int(iso.year),
                "id_art":str(id_art.iloc[pos]),"model":str(modelo.iloc[pos]),
                "category":str(categoria.iloc[pos]),"subcategory":str(subcat.iloc[pos]),
                "store":str(tienda.iloc[pos]),"vta_pzs":a,"dev_pzs":b,
                "vta_imp":c,"costo_dev":cost,"sold_validated":min(a,b),
            })
    return monthly,daily


def _json_default(value):
    try:
        import numpy as _np
        if isinstance(value,_np.integer): return int(value)
        if isinstance(value,_np.floating):
            v=float(value)
            return None if math.isnan(v) or math.isinf(v) else v
        if isinstance(value,_np.bool_): return bool(value)
    except Exception:
        pass
    if isinstance(value,(datetime,pd.Timestamp)): return value.isoformat()
    try:
        if pd.isna(value): return None
    except Exception:
        pass
    return str(value)

def _safe_json_dump(data):
    return json.dumps(data,ensure_ascii=False,default=_json_default,allow_nan=False)



def _build_recovery_fifo_rows(daily_rows):
    """Precalcula recuperación FIFO por lote de devolución.

    Cada fila de salida representa devoluciones ocurridas en una fecha concreta.
    Las ventas sólo consumen devoluciones del mismo SKU/tienda/semana ISO y
    nunca una devolución futura. La cola termina al cerrar la semana ISO.
    """
    grouped={}
    for r in daily_rows or []:
        try:
            store=str(r.get("store") or "")
            year=int(r.get("year_iso") or 0)
            week=int(r.get("week_iso") or 0)
            art=str(r.get("id_art") or "").strip()
            color=str(r.get("color") or "").strip()
            date=str(r.get("date") or "")
            if not store or not year or not week or not art or not date:
                continue
            key=(store,year,week,art,color)
            day=grouped.setdefault(key,{}).setdefault(date,{
                "dev":0.0,"sales":0.0,"sales_value":0.0,"return_cost":0.0
            })
            day["dev"]+=max(float(r.get("dev_pzs") or 0),0.0)
            day["sales"]+=max(float(r.get("vta_pzs") or 0),0.0)
            day["sales_value"]+=max(float(r.get("vta_imp") or 0),0.0)
            day["return_cost"]+=max(float(r.get("costo_dev") or 0),0.0)
        except Exception:
            continue

    out=[]
    for key,by_date in grouped.items():
        week_sales=sum(x["sales"] for x in by_date.values())
        week_sales_value=sum(x["sales_value"] for x in by_date.values())
        unit_price=(week_sales_value/week_sales) if week_sales>0 else 0.0
        if not math.isfinite(unit_price) or unit_price<0:
            unit_price=0.0

        queue=[]
        lots=[]
        for date in sorted(by_date):
            d=by_date[date]
            if d["dev"]>0:
                value=(unit_price*d["dev"]) if unit_price>0 else d["return_cost"]
                lot={
                    "date":date,
                    "store":key[0],
                    "year_iso":key[1],
                    "week_iso":key[2],
                    "id_art":key[3],
                    "color":key[4],
                    "dev_pzs":d["dev"],
                    "vta_pzs":week_sales,
                    "converted_pieces":0.0,
                    "return_value":max(value,0.0),
                }
                queue.append(lot)
                lots.append(lot)

            available=max(d["sales"],0.0)
            while available>1e-9 and queue:
                lot=queue[0]
                assign=min(available,lot["dev_pzs"]-lot["converted_pieces"])
                if assign<=1e-9:
                    queue.pop(0)
                    continue
                lot["converted_pieces"]+=assign
                available-=assign
                if lot["converted_pieces"]>=lot["dev_pzs"]-1e-9:
                    queue.pop(0)

        for lot in lots:
            dev=max(float(lot["dev_pzs"]),0.0)
            rec=min(max(float(lot["converted_pieces"]),0.0),dev)
            value=max(float(lot["return_value"]),0.0)
            recovery_unit=(value/dev) if dev>0 else 0.0
            rec_value=min(rec*recovery_unit,value) if value>0 else 0.0
            lot.update({
                "converted_pieces":rec,
                "conversion_pct":rec/dev*100 if dev else 0.0,
                "recovered_value":rec_value,
                "recovery_pct":rec_value/value*100 if value else 0.0,
                "pending_pieces":max(dev-rec,0.0),
                "pending_value":max(value-rec_value,0.0),
            })
            out.append(lot)

    out.sort(key=lambda x:(x["date"],x["store"],x["id_art"],x.get("color","")))
    return out


def _get_recovery_fifo_rows(data):
    """Obtiene FIFO precalculado. Compatible con archivos ya cargados en V33."""
    rows=data.get("recovery_fifo")
    if isinstance(rows,list):
        return rows

    try:
        stamp=OPS_FILE.stat().st_mtime_ns if OPS_FILE.exists() else 0
    except Exception:
        stamp=0

    # Cache persistente derivado: permite arrancar V34 sin volver a cargar el Excel.
    try:
        if OPS_RECOVERY_CACHE_FILE.exists():
            cached=json.loads(OPS_RECOVERY_CACHE_FILE.read_text(encoding="utf-8"))
            if cached.get("source_stamp")==stamp and isinstance(cached.get("rows"),list):
                return cached["rows"]
    except Exception:
        pass

    rows=_build_recovery_fifo_rows(data.get("commercial_daily",[]))
    try:
        OPS_RECOVERY_CACHE_FILE.write_text(
            _safe_json_dump({"source_stamp":stamp,"rows":rows}),
            encoding="utf-8"
        )
    except Exception:
        pass
    return rows


def parse_operations_excel(path: Path, persist: bool=True):
    try:
        with pd.ExcelFile(path) as xls:
            names=list(xls.sheet_names)
    except Exception as exc:
        raise ValueError(f"No fue posible abrir el Excel: {exc}")

    operational_sheets=_detect_operational_sheets(names)
    monthly_sheets=[s for s in names if _monthly_sheet_name(s)]
    if not operational_sheets:
        raise ValueError(
            "El Excel abrió correctamente, pero no se encontró ninguna hoja cuyo nombre comience con "
            "'Resultados productividad' o 'Resultados de productividad'. Hojas detectadas: "+", ".join(names[:30])
        )

    staff_lookup=_staff_lookup_from_template(path,names)
    rows=[]; rejected_rows=[]; data_issues=[]; op_columns_by_sheet={}; missing_by_sheet={}; errors=[]
    for sheet in operational_sheets:
        try:
            r,cols,rej,issues,missing=_read_operational_sheet(path,sheet,staff_lookup=staff_lookup)
            rows.extend(r); rejected_rows.extend(rej); data_issues.extend(issues)
            op_columns_by_sheet[sheet]=cols; missing_by_sheet[sheet]=missing
            if "RECORRIDOS" in missing:
                data_issues.append({"sheet":sheet,"warning":"La hoja no contiene columna RECORRIDOS. Sus recorridos quedan en 0 hasta que el archivo la incluya."})
        except Exception as exc:
            errors.append(f"{sheet}: {exc}")

    if not rows:
        raise ValueError(
            "Se detectaron las hojas operativas, pero no contienen registros utilizables. "
            f"Hojas: {', '.join(operational_sheets)}. Errores: {' | '.join(errors) if errors else 'sin detalle'}"
        )

    # Deduplicación correcta: sólo filas completamente iguales. Nunca por occurrence solamente.
    rows,duplicate_rows_removed=_dedupe_operational_rows(rows)

    # Las hojas mensuales se conservan únicamente para conversión/recuperación comercial.
    # NO participan en Muertos, Probadores/Aduana, Cajas, Recolectadas, Acondicionado, Ubicado ni Recorridos.
    commercial=[]; daily=[]
    for sheet in monthly_sheets:
        try:
            co,di=_parse_monthly_commercial(path,sheet)
            commercial.extend(co); daily.extend(di)
        except Exception as exc:
            errors.append(f"{sheet}: {exc}")

    weeks=sorted({f"{int(r['year_iso'])}-W{int(r['week_iso']):02d}" for r in rows if r.get("year_iso") and r.get("week_iso")})
    daily_weeks=sorted({f"{int(r['year_iso'])}-W{int(r['week_iso']):02d}" for r in daily if r.get("year_iso") and r.get("week_iso")})
    months=sorted({r.get("month") for r in rows if r.get("month")})
    recovery_fifo=_build_recovery_fifo_rows(daily)
    meta_index={
        "available_dates":sorted({str(r.get("date")) for r in rows if r.get("date")}),
        "available_weeks":weeks,
        "available_months":months,
        "stores":sorted({str(r.get("store") or "").strip() for r in rows if str(r.get("store") or "").strip()}),
        "areas":sorted({str(r.get("area") or "").strip() for r in rows if str(r.get("area") or "").strip()}),
        "activities":sorted({str(r.get("activity") or "").strip() for r in rows if str(r.get("activity") or "").strip()}),
    }

    payload={
        "parser_version":OPERATIONS_PARSER_VERSION,
        "rows":rows,"commercial":commercial,"commercial_daily":daily,"recovery_fifo":recovery_fifo,
        "uploaded_at":datetime.now().isoformat(timespec="seconds"),"source_file":path.name,
        "sheets_all":names,"operational_sheet":operational_sheets[0],"operational_sheets":operational_sheets,
        "sheets_used":operational_sheets+monthly_sheets,"monthly_sheets":monthly_sheets,
        "op_columns":op_columns_by_sheet.get(operational_sheets[0],[]),"op_columns_by_sheet":op_columns_by_sheet,
        "missing_columns_by_sheet":missing_by_sheet,"weeks":weeks,"commercial_weeks":daily_weeks,"months":months,
        "meta_index":meta_index,
        "errors":errors,"rejected_rows":rejected_rows,"data_issues":data_issues,
        "duplicate_rows_removed":duplicate_rows_removed,
    }
    if persist:
        OPS_FILE.write_text(_safe_json_dump(payload),encoding="utf-8")
        _clear_operations_caches(clear_meta_file=True)
        try: OPS_RECOVERY_CACHE_FILE.unlink(missing_ok=True)
        except Exception: pass
        try:
            meta=_build_operations_meta(payload,_ops_source_stamp())
            OPS_META_CACHE_FILE.write_text(_safe_json_dump(meta),encoding="utf-8")
            _OPS_META_CACHE["stamp"]=_ops_source_stamp(); _OPS_META_CACHE["data"]=meta
        except Exception:
            pass
    return payload


@app.get("/health")
def health():
    return {"ok": True, "app": "Operaciones Ropa", "version": "V47"}

@app.get("/")
def index(): return FileResponse(WEB/"index.html")

@app.get("/api/bootstrap")
def bootstrap(request: Request):
    migrate_legacy_owner()
    return {"needs_owner":user_count()==0,"user":current_user(request),"roles":ROLE_LABELS,"system":system_status()}

@app.post("/api/bootstrap-owner")
async def bootstrap_owner(request: Request):
    if user_count()!=0: raise HTTPException(409,"El propietario ya fue configurado")
    body=await request.json(); username=str(body.get("username") or "").strip(); password=str(body.get("password") or "")
    if len(username)<3 or len(password)<8: raise HTTPException(400,"Usuario mínimo 3 caracteres y contraseña mínimo 8")
    with db() as con:
        con.execute("INSERT INTO users(username,password_hash,role,store,created_at) VALUES(?,?,?,?,?)",
                    (username,hash_password(password),"superadmin","",datetime.now().isoformat(timespec="seconds")))
    return {"ok":True}


def _local_recovery_allowed(request: Request):
    host=(request.client.host if request.client else "") or ""
    return host in ("127.0.0.1","::1","localhost","testclient")

@app.post("/api/recovery/reset-local")
async def recovery_reset_local(request: Request):
    if not _local_recovery_allowed(request):
        raise HTTPException(403,"La recuperación directa sólo está disponible desde la computadora del sistema")
    body=await request.json()
    username=str(body.get("username") or "").strip()
    new_password=str(body.get("new_password") or "")
    confirm=str(body.get("confirm_password") or "")
    if len(new_password)<8:
        raise HTTPException(400,"La nueva contraseña debe tener al menos 8 caracteres")
    if new_password!=confirm:
        raise HTTPException(400,"Las contraseñas no coinciden")

    migrate_legacy_owner()
    row=find_login_user(username)
    if not row:
        raise HTTPException(404,"No se encontró ese usuario, correo o nómina")
    if row["role"]!="superadmin":
        raise HTTPException(403,"Esta recuperación local es sólo para el propietario del sistema")

    new_hash=hash_password(new_password)
    with db() as con:
        con.execute("UPDATE users SET password_hash=? WHERE id=?",(new_hash,row["id"]))
    return {"ok":True,"message":"Contraseña actualizada. Ya puedes iniciar sesión.","username":row["username"]}

@app.post("/api/login")
async def login(request: Request):
    body=await request.json()
    username=str(body.get("username") or "").strip()
    password=str(body.get("password") or "")
    row=find_login_user(username)
    if not row or not verify_password(password,row["password_hash"]):
        raise HTTPException(401,"Usuario o contraseña incorrectos")
    state=system_status().get("status","active")
    if state in ("suspended","deleted") and row["role"]!="superadmin":
        raise HTTPException(423,"Operaciones Ropa está suspendido por el propietario")
    sv=int(row["session_version"] or 1) if "session_version" in row.keys() else 1
    request.session["uid"]=row["id"]
    request.session["sv"]=sv
    must=bool(row["must_change_password"]) if "must_change_password" in row.keys() else False
    return {
        "ok":True,
        "must_change_password":must,
        "user":{"id":row["id"],"username":row["username"],"role":row["role"],"store":row["store"],"must_change_password":must},
        "system":system_status()
    }

@app.post("/api/logout")
def logout(request: Request): request.session.clear(); return {"ok":True}

@app.get("/api/users")
def users(request: Request):
    actor=require_user(request,("superadmin","admin"))
    with db() as con:
        if actor["role"]=="admin":
            rows=con.execute(
                "SELECT id,username,role,store,active,created_at FROM users WHERE role<>'superadmin' ORDER BY role,username"
            ).fetchall()
        else:
            rows=con.execute(
                "SELECT id,username,role,store,active,created_at FROM users ORDER BY role,username"
            ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/users")
async def create_user(request: Request):
    actor=require_user(request,("superadmin","admin"))
    body=await request.json()
    role=str(body.get("role") or "tienda")
    username=" ".join(str(body.get("username") or "").split()).strip()
    password=str(body.get("password") or "")
    store=str(body.get("store") or "").strip()
    if role not in ROLES:
        raise HTTPException(400,"Rol inválido")
    if role=="superadmin":
        raise HTTPException(403,"No se puede crear otro Super Administrador")
    if role=="tienda" and not store:
        raise HTTPException(400,"Selecciona la tienda")
    if len(username)<3 or len(password)<8:
        raise HTTPException(400,"Usuario mínimo 3 caracteres y contraseña mínimo 8")
    now=datetime.now().isoformat(timespec="seconds")
    try:
        with db() as con:
            con.execute(
                "INSERT INTO users(username,password_hash,role,store,active,created_at,must_change_password,session_version,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (username,hash_password(password),role,store,1,now,1,1,now)
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409,"Ese usuario ya existe")
    return {"ok":True,"message":"Usuario creado correctamente","temporary_password":password}


def _target_user_for_actor(actor: dict, user_id: int):
    with db() as con:
        target=con.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    if not target:
        raise HTTPException(404,"Usuario no encontrado")
    if actor["role"]=="admin" and target["role"]=="superadmin":
        raise HTTPException(404,"Usuario no encontrado")
    return target

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    actor=require_user(request,("superadmin","admin"))
    target=_target_user_for_actor(actor,user_id)
    body=await request.json()
    username=" ".join(str(body.get("username",target["username"]) or "").split()).strip()
    role=str(body.get("role",target["role"]) or target["role"])
    store=str(body.get("store",target["store"]) or "").strip()
    active=1 if bool(body.get("active",bool(target["active"]))) else 0

    if target["role"]=="superadmin":
        raise HTTPException(403,"El Super Administrador no se edita desde esta pantalla")
    if role=="superadmin":
        raise HTTPException(403,"No se puede asignar el rol Super Administrador")
    if role=="tienda" and not store:
        raise HTTPException(400,"Selecciona la tienda")
    if len(username)<3:
        raise HTTPException(400,"Usuario mínimo 3 caracteres")
    try:
        with db() as con:
            con.execute(
                "UPDATE users SET username=?,role=?,store=?,active=?,updated_at=? WHERE id=?",
                (username,role,store,active,datetime.now().isoformat(timespec="seconds"),user_id)
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409,"Ese usuario ya existe")
    return {"ok":True,"message":"Usuario actualizado correctamente"}

@app.post("/api/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, request: Request):
    actor=require_user(request,("superadmin","admin"))
    target=_target_user_for_actor(actor,user_id)
    if target["role"]=="superadmin":
        raise HTTPException(403,"El Super Administrador usa “Cambiar mi contraseña”")
    body=await request.json()
    password=str(body.get("password") or "").strip()
    if not password:
        alphabet="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
        password="".join(secrets.choice(alphabet) for _ in range(12))
    if len(password)<8:
        raise HTTPException(400,"La contraseña temporal debe tener al menos 8 caracteres")
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute(
            "UPDATE users SET password_hash=?,must_change_password=1,session_version=COALESCE(session_version,1)+1,updated_at=? WHERE id=?",
            (hash_password(password),now,user_id)
        )
    return {
        "ok":True,
        "message":"Contraseña temporal generada. El usuario deberá cambiarla en el siguiente inicio.",
        "temporary_password":password
    }


@app.post("/api/me/change-password")
async def change_my_password(request: Request):
    actor=require_user(request)
    body=await request.json()
    current=str(body.get("current_password") or "")
    new=str(body.get("new_password") or "")
    confirm=str(body.get("confirm_password") or "")
    if len(new)<8:
        raise HTTPException(400,"La nueva contraseña debe tener al menos 8 caracteres")
    if new!=confirm:
        raise HTTPException(400,"Las contraseñas no coinciden")
    with db() as con:
        row=con.execute("SELECT * FROM users WHERE id=?",(actor["id"],)).fetchone()
    if not row or not verify_password(current,row["password_hash"]):
        raise HTTPException(401,"La contraseña actual no es correcta")
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute(
            "UPDATE users SET password_hash=?,must_change_password=0,session_version=COALESCE(session_version,1)+1,updated_at=? WHERE id=?",
            (hash_password(new),now,actor["id"])
        )
        row2=con.execute("SELECT session_version FROM users WHERE id=?",(actor["id"],)).fetchone()
    request.session["sv"]=int(row2["session_version"])
    return {"ok":True,"message":"Contraseña actualizada correctamente"}

@app.post("/api/me/complete-temporary-password")
async def complete_temporary_password(request: Request):
    actor=require_user(request)
    body=await request.json()
    new=str(body.get("new_password") or "")
    confirm=str(body.get("confirm_password") or "")
    if len(new)<8:
        raise HTTPException(400,"La nueva contraseña debe tener al menos 8 caracteres")
    if new!=confirm:
        raise HTTPException(400,"Las contraseñas no coinciden")
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute(
            "UPDATE users SET password_hash=?,must_change_password=0,session_version=COALESCE(session_version,1)+1,updated_at=? WHERE id=?",
            (hash_password(new),now,actor["id"])
        )
        row=con.execute("SELECT session_version FROM users WHERE id=?",(actor["id"],)).fetchone()
    request.session["sv"]=int(row["session_version"])
    return {"ok":True,"message":"Nueva contraseña guardada"}

@app.post("/api/users/{user_id}/status")
async def set_user_status(user_id: int, request: Request):
    actor=require_user(request,("superadmin","admin"))
    target=_target_user_for_actor(actor,user_id)
    if int(target["id"])==int(actor["id"]):
        raise HTTPException(400,"No puedes desactivar tu propio usuario")
    if target["role"]=="superadmin":
        raise HTTPException(403,"No puedes desactivar al Super Administrador")
    body=await request.json()
    active=1 if bool(body.get("active")) else 0
    with db() as con:
        con.execute("UPDATE users SET active=?,session_version=COALESCE(session_version,1)+1,updated_at=? WHERE id=?",(active,datetime.now().isoformat(timespec="seconds"),user_id))
    return {"ok":True,"message":"Estado actualizado"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, request: Request):
    actor=require_user(request,("superadmin","admin"))
    with db() as con:
        target=con.execute("SELECT id,username,role FROM users WHERE id=?",(user_id,)).fetchone()
        if not target: raise HTTPException(404,"Usuario no encontrado")
        if int(target["id"])==int(actor["id"]): raise HTTPException(400,"No puedes eliminar tu propio usuario")
        if target["role"]=="superadmin":
            if actor["role"]=="admin": raise HTTPException(404,"Usuario no encontrado")
            raise HTTPException(403,"El propietario del sistema no se puede eliminar")
        con.execute("DELETE FROM users WHERE id=?",(user_id,))
    return {"ok":True,"deleted":target["username"]}

@app.get("/api/system/status")
def get_system_status(request: Request):
    require_user(request,("superadmin",))
    return system_status()

@app.post("/api/system/action")
async def system_action(request: Request):
    u=require_user(request,("superadmin",)); body=await request.json()
    password=str(body.get("password") or ""); action=str(body.get("action") or "").lower(); confirmation=str(body.get("confirmation") or "")
    with db() as con: row=con.execute("SELECT password_hash FROM users WHERE id=?",(u["id"],)).fetchone()
    if not row or not verify_password(password,row["password_hash"]): raise HTTPException(401,"Contraseña del propietario incorrecta")
    if action=="suspend":
        set_system_status("suspended",u["username"]); return {"ok":True,"status":"suspended"}
    if action=="activate":
        set_system_status("active",u["username"]); return {"ok":True,"status":"active"}
    if action=="delete":
        if confirmation!="ELIMINAR SISTEMA": raise HTTPException(400,"Escribe exactamente ELIMINAR SISTEMA")
        with db() as con: con.execute("DELETE FROM users WHERE role<>'superadmin'")
        set_system_status("deleted",u["username"])
        return {"ok":True,"status":"deleted","note":"Sistema bloqueado y usuarios no propietarios eliminados. El servicio del hosting debe eliminarse desde el proveedor para borrar la URL."}
    raise HTTPException(400,"Acción inválida")


def _norm_section_name(value: str):
    key=login_key(value)
    if "dama" in key:
        return "Dama"
    if "caballero" in key:
        return "Caballero"
    if any(x in key for x in ("infantil","nino","nina","bebe","beba")):
        return "Infantil"
    return str(value or "Sin sección").strip() or "Sin sección"

def _snapshot_metric_for_section(snapshot: dict, section: str="Todas"):
    """Métrica de una tienda para toda la tienda o una sección del PDF."""
    if not section or section=="Todas":
        cap=float(snapshot.get("curve") or 0)
        ex=float(snapshot.get("existence") or 0)
        sug=float(snapshot.get("vpd") or 0)
        return {
            "store":snapshot.get("store",""),"suggested":sug,"existence":ex,
            "floor":float(snapshot.get("floor") or 0),"warehouse":float(snapshot.get("warehouse") or 0),
            "capacity":cap,"ddi":ex/sug if sug else 0.0,
            "occupancy":ex/cap*100 if cap else None,"available":True
        }
    want=login_key(section)
    section_rows=(snapshot.get("breakdowns") or {}).get("section") or []
    matches=[r for r in section_rows if login_key(_norm_section_name(r.get("label") or r.get("section") or ""))==want]
    if not matches:
        return {
            "store":snapshot.get("store",""),"suggested":None,"existence":None,"floor":None,
            "warehouse":None,"capacity":None,"ddi":None,"occupancy":None,"available":False
        }
    cap=sum(float(r.get("curve") or 0) for r in matches)
    ex=sum(float(r.get("existence") or 0) for r in matches)
    sug=sum(float(r.get("vpd") or 0) for r in matches)
    floor=sum(float(r.get("floor") or 0) for r in matches)
    wh=sum(float(r.get("warehouse") or 0) for r in matches)
    return {
        "store":snapshot.get("store",""),"suggested":sug,"existence":ex,"floor":floor,"warehouse":wh,
        "capacity":cap,"ddi":ex/sug if sug else 0.0,"occupancy":ex/cap*100 if cap else None,"available":True
    }

def _scope_snapshot(snapshot: dict, section: str="Todas"):
    """Crea una vista del snapshot limitada a sección sin modificar el original."""
    if not section or section=="Todas":
        return snapshot
    metric=_snapshot_metric_for_section(snapshot,section)
    if not metric.get("available"):
        return None
    out=dict(snapshot)
    out.update({
        "curve":metric["capacity"],"existence":metric["existence"],"floor":metric["floor"],
        "warehouse":metric["warehouse"],"vpd":metric["suggested"],"ddi":metric["ddi"]
    })
    wanted=login_key(section)
    breakdowns={}
    for key, values in (snapshot.get("breakdowns") or {}).items():
        if not isinstance(values,list):
            breakdowns[key]=values
            continue
        if key=="section":
            breakdowns[key]=[r for r in values if login_key(_norm_section_name(r.get("label") or r.get("section") or ""))==wanted]
        elif key=="rubro":
            breakdowns[key]=[r for r in values if login_key(_norm_section_name(r.get("section") or r.get("section_detail") or ""))==wanted]
        else:
            breakdowns[key]=values
    out["breakdowns"]=breakdowns
    out["model_rankings"]=[
        r for r in (snapshot.get("model_rankings") or [])
        if login_key(_norm_section_name(r.get("world") or r.get("world_detail") or ""))==wanted
    ]
    return out

def _capacity_unique_model_sets():
    """Modelos únicos por tienda/sección/subcategoría usando el Excel estructural cacheado."""
    result={}
    try:
        frame=_latest_capacity_frame()
        if frame.empty:
            return result
        for (store,section,rubro), grp in frame.groupby(["Tienda","Sección","Subcategoría"],dropna=False):
            ids=set()
            for col in ("ID_ART","Modelo"):
                if col in grp.columns:
                    ids.update(str(x).strip() for x in grp[col].dropna().tolist() if str(x).strip() not in ("","nan","None"))
            result[(login_key(store),login_key(section),login_key(rubro))]=ids
    except Exception as exc:
        print(f"[V44] No se pudo construir catálogo único: {type(exc).__name__}: {exc}")
        return {}
    return result





CAPACITY_NORMALIZED_DIR = DATA_ROOT / "capacity_normalized"
CAPACITY_NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

def _capacity_cache_path(entry_id: str) -> Path:
    safe=re.sub(r"[^0-9A-Za-z_-]+","_",str(entry_id or "capacity"))
    return CAPACITY_NORMALIZED_DIR / f"capacity_{safe}.pkl"

def _load_capacity_cache(entry: dict) -> pd.DataFrame:
    try:
        cache_rel=str(entry.get("cache_file") or "").strip()
        cache_path=(DATA_ROOT/cache_rel) if cache_rel else _capacity_cache_path(str(entry.get("id") or ""))
        if cache_path.exists() and cache_path.is_file():
            frame=pd.read_pickle(cache_path)
            if isinstance(frame,pd.DataFrame):
                return frame
    except Exception as exc:
        print(f"[V44] Cache capacidades no disponible: {type(exc).__name__}: {exc}")
    return pd.DataFrame()

_CAPACITY_FRAME_CACHE = {"path": "", "mtime": None, "frame": None}

def _latest_capacity_frame() -> pd.DataFrame:
    try:
        manifest=load_manifest()
        caps=[x for x in manifest.get("capacities",[]) if str(x.get("status") or "").lower()=="procesado"]
        if not caps:
            return pd.DataFrame()
        entry=sorted(caps,key=lambda x:str(x.get("uploaded_at") or x.get("created_at") or ""))[-1]
        path=resolve_entry_path(entry)
        mtime=path.stat().st_mtime if path.exists() else None
        cached=_CAPACITY_FRAME_CACHE.get("frame")
        if cached is not None and _CAPACITY_FRAME_CACHE.get("path")==str(path) and _CAPACITY_FRAME_CACHE.get("mtime")==mtime:
            return cached

        # V44: primero usa el catálogo normalizado persistente. Evita volver a leer
        # las ~196 mil filas del XLSX en cada reinicio/consulta.
        frame=_load_capacity_cache(entry)
        if frame.empty:
            frame=read_capacity_file(path)
            if isinstance(frame,pd.DataFrame) and not frame.empty:
                cache_path=_capacity_cache_path(str(entry.get("id") or ""))
                try:
                    frame.to_pickle(cache_path)
                    update_entry("capacities",str(entry.get("id") or ""),cache_file=str(cache_path.relative_to(DATA_ROOT)))
                except Exception as cache_exc:
                    print(f"[V44] No se pudo persistir cache capacidades: {cache_exc}")
        if isinstance(frame,pd.DataFrame):
            _CAPACITY_FRAME_CACHE.update({"path":str(path),"mtime":mtime,"frame":frame})
            return frame
        return pd.DataFrame()
    except Exception as exc:
        print(f"[V44] Error leyendo capacidad procesada: {type(exc).__name__}: {exc}")
        return pd.DataFrame()


def _scope_capacity(frame: pd.DataFrame, store: str="Compañía", section: str="Todas", catalog: str="Todos") -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    work=frame.copy()
    if store and store!="Compañía" and "Tienda" in work.columns:
        work=work[work["Tienda"].map(login_key)==login_key(store)]
    if section and section!="Todas" and "Sección" in work.columns:
        work=work[work["Sección"].map(login_key)==login_key(section)]
    if catalog and catalog not in ("Todos","Todas","") and "Tipo catálogo" in work.columns:
        work=work[work["Tipo catálogo"].map(login_key)==login_key(catalog)]
    return work.reset_index(drop=True)


def _first_non_empty(series: pd.Series, fallback: str="") -> str:
    for value in series.fillna("").astype(str):
        value=value.strip()
        if value and value.lower() not in ("nan","none"):
            return value
    return fallback


def _combine_labels(values, limit: int=3) -> str:
    items=[]
    for value in values:
        text=str(value or "").strip()
        if not text or text.lower() in ("nan","none") or text in items:
            continue
        items.append(text)
    if not items:
        return ""
    if len(items)<=limit:
        return " / ".join(items)
    return " / ".join(items[:limit])+f" +{len(items)-limit}"


def _aggregate_capacity_models(frame: pd.DataFrame, store: str="Compañía", section: str="Todas", catalog: str="Todos") -> pd.DataFrame:
    work=_scope_capacity(frame,store,section,catalog)
    if work.empty:
        return pd.DataFrame()
    grouped=[]
    for id_art, g in work.groupby("ID_ART", dropna=False):
        ids=set(str(x).strip() for x in g["ID_ART"].dropna().tolist() if str(x).strip())
        grouped.append({
            "id_art": _first_non_empty(g.get("ID_ART", pd.Series(dtype=str)), str(id_art)),
            "model": _first_non_empty(g.get("Modelo", pd.Series(dtype=str)), str(id_art)),
            "brand": _first_non_empty(g.get("Marca", pd.Series(dtype=str)), "Sin marca"),
            "section": _first_non_empty(g.get("Sección", pd.Series(dtype=str)), "Sin sección"),
            "rubro": _first_non_empty(g.get("Subcategoría", pd.Series(dtype=str)), _first_non_empty(g.get("Categoría", pd.Series(dtype=str)), "Sin rubro")),
            "store": _combine_labels(g.get("Tienda", pd.Series(dtype=str))),
            "location": _combine_labels(g.get("Ubicación detalle", g.get("Pasillo", pd.Series(dtype=str)))),
            "area": _combine_labels(g.get("Ubicación", pd.Series(dtype=str))),
            "exhibition": _combine_labels(g.get("Exhibición", pd.Series(dtype=str))),
            "exhibition_locations": _combine_labels(g.loc[g.get("Exhibición",pd.Series(index=g.index,dtype=str)).fillna('').astype(str).str.strip()!='', g.columns[g.columns.get_loc('Ubicación detalle')] if 'Ubicación detalle' in g.columns else 'Pasillo']) if ('Ubicación detalle' in g.columns or 'Pasillo' in g.columns) else "",
            "existence": float(pd.to_numeric(g.get("Existencia",0),errors="coerce").fillna(0).sum()),
            "floor": float(pd.to_numeric(g.get("Existencia piso",0),errors="coerce").fillna(0).sum()),
            "warehouse": float(pd.to_numeric(g.get("Existencia bodega",0),errors="coerce").fillna(0).sum()),
            "suggested": float(pd.to_numeric(g.get("VPD",0),errors="coerce").fillna(0).sum()),
            "ddi": float(pd.to_numeric(g.get("DDI",0),errors="coerce").fillna(0).replace([np.inf,-np.inf], np.nan).mean()) if len(g) else 0,
            "capacity": float(pd.to_numeric(g.get("Capacidad",0),errors="coerce").fillna(0).sum()),
            "sales_pzas": float(pd.to_numeric(g.get("Venta pzas", g.get("Venta pzas 30",0)),errors="coerce").fillna(0).sum()),
            "sales_pzas_30": float(pd.to_numeric(g.get("Venta pzas 30",0),errors="coerce").fillna(0).sum()),
            "sales_value_7": float(pd.to_numeric(g.get("Venta $ 7", g.get("Venta $",0)),errors="coerce").fillna(0).sum()),
            "sales_value_month": float(pd.to_numeric(g.get("Venta $ mes", g.get("Venta $",0)),errors="coerce").fillna(0).sum()),
            "sales_value": float(pd.to_numeric(g.get("Venta $ 7", g.get("Venta $",0)),errors="coerce").fillna(0).sum()),
            "catalog": _first_non_empty(g.get("Tipo catálogo", pd.Series(dtype=str)), ""),
            "ultima_cedis": pd.to_datetime(g.get("Última entrada CEDIS a tienda", pd.Series(dtype='datetime64[ns]')),errors='coerce').max(),
            "pzas_ult_cedis": float(pd.to_numeric(g.get("Pzas última entrada",0),errors='coerce').fillna(0).sum()),
            "stores_count": int(g.get("Tienda", pd.Series(dtype=str)).astype(str).str.strip().replace({'nan':''}).ne('').sum()),
        })
    out=pd.DataFrame(grouped)
    out["ddi"] = pd.to_numeric(out["ddi"],errors="coerce").fillna(0.0)
    out["occupancy"] = out.apply(lambda r: (r["existence"] / r["capacity"] * 100) if r["capacity"] else None, axis=1)
    out["ultima_cedis_fmt"] = out["ultima_cedis"].dt.strftime("%Y-%m-%d").fillna("")
    return out


def _capacity_model_rows(store: str="Compañía", section: str="Todas", mode: str="80_20", period: str="", catalog: str="Todos"):
    """Reportes de modelos desde el catálogo de capacidades.

    V44: agregación vectorizada. La versión anterior recorría grupo por grupo los
    ~17 mil ID_ART del Excel (195k+ filas), lo que podía tardar varios minutos y
    disparar el timeout del navegador. Aquí primero se agregan columnas numéricas
    con groupby nativo de pandas y sólo se construyen etiquetas de ubicación/
    exhibición para los modelos que realmente se van a devolver.
    """
    frame=_capacity_frame_for_period(period)
    if frame is None or frame.empty:
        return []
    work=_capacity_scope_v45(frame,store,section,catalog)
    if work.empty or "ID_ART" not in work.columns:
        return []

    work=work.copy()
    work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
    work=work[~work["__id"].isin(["","nan","None"])]
    if work.empty:
        return []

    # Columnas numéricas: convertir una sola vez y agregar con rutinas vectorizadas.
    num_sources={
        "existence":"Existencia",
        "floor":"Existencia piso",
        "warehouse":"Existencia bodega",
        "suggested":"VPD",
        "capacity":"Capacidad",
        "sales_pzas_7":"Venta pzas 7",
        "sales_pzas_month":"Venta pzas",
        "sales_pzas_30":"Venta pzas 30",
        "sales_value_7":"Venta $ 7",
        "sales_value_month":"Venta $ mes",
        "pzas_ult_cedis":"Pzas última entrada",
    }
    num_frame=pd.DataFrame(index=work.index)
    num_frame["__id"]=work["__id"]
    for dest,src in num_sources.items():
        if src in work.columns:
            num_frame[dest]=pd.to_numeric(work[src],errors="coerce").fillna(0.0)
        else:
            num_frame[dest]=0.0
    numeric=num_frame.groupby("__id",sort=False).sum(numeric_only=True)

    # DDI del archivo = Días de inventario SUG 7. No se suma; se conserva el
    # promedio de los registros que forman el modelo en el alcance seleccionado.
    if "DDI" in work.columns:
        ddi_src=pd.to_numeric(work["DDI"],errors="coerce").replace([np.inf,-np.inf],np.nan)
        ddi=ddi_src.groupby(work["__id"]).mean().rename("ddi")
        numeric=numeric.join(ddi,how="left")
    else:
        numeric["ddi"]=0.0
    numeric["ddi"]=pd.to_numeric(numeric["ddi"],errors="coerce").fillna(0.0)

    # Metadatos estables (primer valor real) sin iterar 17 mil grupos en Python.
    meta_cols={
        "model":"Modelo",
        "brand":"Marca",
        "section":"Sección",
        "rubro":"Subcategoría",
        "catalog":"Tipo catálogo",
    }
    meta_parts=[]
    for dest,src in meta_cols.items():
        if src in work.columns:
            s=work[src].fillna("").astype(str).str.strip().replace({"nan":"","None":""})
            tmp=pd.DataFrame({"__id":work["__id"],dest:s.replace("",pd.NA)})
            meta_parts.append(tmp.groupby("__id",sort=False)[dest].first())
    if meta_parts:
        meta=pd.concat(meta_parts,axis=1)
        numeric=numeric.join(meta,how="left")
    for col,default in (("model",""),("brand","Sin marca"),("section","Sin sección"),("rubro","Sin rubro"),("catalog","")):
        if col not in numeric.columns:
            numeric[col]=default
        numeric[col]=numeric[col].fillna(default).astype(str)
    numeric.loc[numeric["model"].str.strip()=="","model"]=numeric.index[numeric["model"].str.strip()==""]

    if "Última entrada CEDIS a tienda" in work.columns:
        dates=pd.to_datetime(work["Última entrada CEDIS a tienda"],errors="coerce")
        numeric=numeric.join(dates.groupby(work["__id"]).max().rename("ultima_cedis"),how="left")
    else:
        numeric["ultima_cedis"]=pd.NaT
    numeric["ultima_cedis_fmt"]=pd.to_datetime(numeric["ultima_cedis"],errors="coerce").dt.strftime("%Y-%m-%d").fillna("")

    models=numeric.reset_index().rename(columns={"__id":"id_art"})
    is_month=bool(re.fullmatch(r"\d{4}-\d{2}", str(period or "")))
    metric="sales_value_month" if is_month else "sales_value_7"
    if metric not in models.columns or float(pd.to_numeric(models.get(metric,0),errors="coerce").fillna(0).sum())<=0:
        metric="sales_value_7" if "sales_value_7" in models.columns else "sales_value_month"
    models[metric]=pd.to_numeric(models.get(metric,0),errors="coerce").fillna(0.0)
    models["sales_value"]=models[metric]
    pmetric="sales_pzas_month" if is_month else "sales_pzas_7"
    if pmetric not in models.columns:
        pmetric="sales_pzas_30" if "sales_pzas_30" in models.columns else "sales_pzas_month"
    models["sales_pzas"]=pd.to_numeric(models.get(pmetric,0),errors="coerce").fillna(0.0)

    mode=str(mode or "80_20").lower()
    if mode in ("80_20","8020","top","champions"):
        selected=models.sort_values([metric,"sales_pzas","existence"],ascending=[False,False,False]).reset_index(drop=True)
        total=float(selected[metric].sum())
        selected["cum_share"]=(selected[metric].cumsum()/total*100) if total>0 else 0.0
        if total>0:
            reached=np.flatnonzero(selected["cum_share"].to_numpy()>=80.0)
            last=int(reached[0]) if len(reached) else len(selected)-1
            selected=selected.iloc[:last+1].copy()
        else:
            selected=selected.head(50).copy()
    elif mode in ("slow","lentos"):
        selected=models[(pd.to_numeric(models["suggested"],errors="coerce").fillna(0)<=1) | (pd.to_numeric(models["sales_pzas_30"],errors="coerce").fillna(0)<=0)]
        selected=selected.sort_values(["existence","suggested","sales_pzas_30"],ascending=[False,True,True]).head(50).copy()
        selected["cum_share"]=0.0
    elif mode in ("suggested_zero","sin_venta","sug0"):
        selected=models[(pd.to_numeric(models["suggested"],errors="coerce").fillna(0)<=0) | (pd.to_numeric(models["sales_pzas_30"],errors="coerce").fillna(0)<=0)]
        selected=selected.sort_values(["existence","sales_pzas_30"],ascending=[False,True]).head(80).copy()
        selected["cum_share"]=0.0
    else:
        return []

    if selected.empty:
        return []
    selected=selected.reset_index(drop=True)
    selected["rank"]=np.arange(1,len(selected)+1)
    selected["occupancy"]=np.where(pd.to_numeric(selected.get("capacity",0),errors="coerce").fillna(0)>0,
        pd.to_numeric(selected.get("existence",0),errors="coerce").fillna(0)/pd.to_numeric(selected.get("capacity",0),errors="coerce").replace(0,np.nan)*100,np.nan)

    # Etiquetas de ubicación/exhibición sólo para el subconjunto devuelto.
    ids=set(selected["id_art"].astype(str))
    labels=work[work["__id"].isin(ids)].copy()
    label_map={}
    def compact_labels(src_col):
        if src_col not in labels.columns:
            return {}
        tmp=labels[["__id",src_col]].copy()
        tmp[src_col]=tmp[src_col].fillna("").astype(str).str.strip()
        tmp=tmp[~tmp[src_col].isin(["","nan","None"])].drop_duplicates()
        if tmp.empty:
            return {}
        return tmp.groupby("__id",sort=False)[src_col].agg(lambda s:_combine_labels(s,3)).to_dict()

    location_col="Ubicación detalle" if "Ubicación detalle" in labels.columns else ("Pasillo" if "Pasillo" in labels.columns else "")
    location_map=compact_labels(location_col) if location_col else {}
    exhibition_map=compact_labels("Exhibición")
    store_map=compact_labels("Tienda")

    rows=[]
    for r in selected.itertuples(index=False):
        rid=str(r.id_art)
        base={
            "id_art":rid,
            "model":str(getattr(r,"model",rid) or rid),
            "brand":str(getattr(r,"brand","Sin marca") or "Sin marca"),
            "section":str(getattr(r,"section","Sin sección") or "Sin sección"),
            "rubro":str(getattr(r,"rubro","Sin rubro") or "Sin rubro"),
            "location":location_map.get(rid,""),
            "exhibition":exhibition_map.get(rid,""),
            "store":store_map.get(rid,store if store!="Compañía" else "Compañía"),
            "rank":int(getattr(r,"rank",0) or 0),
            "suggested":float(getattr(r,"suggested",0) or 0),
            "existence":float(getattr(r,"existence",0) or 0),
            "capacity":float(getattr(r,"capacity",0) or 0),
            "occupancy":None if pd.isna(getattr(r,"occupancy",np.nan)) else float(getattr(r,"occupancy",0) or 0),
            "sales_pzas_30":float(getattr(r,"sales_pzas_30",0) or 0),
            "sales_pzas":float(getattr(r,"sales_pzas",0) or 0),
            "sales_value":float(getattr(r,"sales_value",0) or 0),
            "floor":float(getattr(r,"floor",0) or 0),
            "warehouse":float(getattr(r,"warehouse",0) or 0),
            "ddi":float(getattr(r,"ddi",0) or 0),
            "ultima_cedis":str(getattr(r,"ultima_cedis_fmt","") or ""),
            "pzas_ult_cedis":float(getattr(r,"pzas_ult_cedis",0) or 0),
            "cum_share":float(getattr(r,"cum_share",0) or 0),
        }
        rows.append(base)
    return rows



def _capacity_8020_summary(store: str="Compañía", section: str="Todas", catalog: str="Todos", period: str="", group_by: str="section"):
    frame=_capacity_frame_for_period(period)
    work=_capacity_scope_v45(frame,store,section,catalog)
    if work.empty or "ID_ART" not in work.columns:
        return {"models_80":0,"models_20":0,"total_models":0,"rows":[]}
    pcol,vcol=_capacity_period_columns(period)
    work=work.copy()
    work["__id"]=work["ID_ART"].fillna("").astype(str).str.strip()
    work=work[~work["__id"].isin(["","nan","None"])]
    if work.empty:return {"models_80":0,"models_20":0,"total_models":0,"rows":[]}
    # Área operativa corregida para V45.
    work["Área reporte"]=_capacity_area_report_series(work)
    # Agregación numérica a nivel modelo.
    agg=pd.DataFrame({"__id":work["__id"]})
    for dst,src in (("sales_pzas",pcol),("sales_value",vcol),("suggested","VPD"),("existence","Existencia"),("capacity","Capacidad")):
        agg[dst]=pd.to_numeric(work.get(src,0),errors="coerce").fillna(0.0)
    model=agg.groupby("__id",sort=False).sum(numeric_only=True)
    ddi_src=pd.to_numeric(work.get("DDI",0),errors="coerce").fillna(0.0)
    sug_src=pd.to_numeric(work.get("VPD",0),errors="coerce").fillna(0.0)
    weighted=(ddi_src*sug_src).groupby(work["__id"]).sum()
    weights=sug_src.groupby(work["__id"]).sum().replace(0,np.nan)
    model["ddi"]=(weighted/weights).fillna(ddi_src.groupby(work["__id"]).mean()).fillna(0.0)
    model=model.sort_values(["sales_value","sales_pzas","existence"],ascending=[False,False,False]).reset_index()
    total=float(model["sales_value"].sum())
    model["cum_share"]=model["sales_value"].cumsum()/total*100 if total>0 else 0.0
    model["segment"]="20"
    if total>0:
        hit=np.flatnonzero(model["cum_share"].to_numpy()>=80.0)
        last=int(hit[0]) if len(hit) else len(model)-1
        model.loc[:last,"segment"]="80"
    else:
        model.loc[:min(len(model)-1,49),"segment"]="80"

    # Dimensiones a nivel modelo. Se elige el valor de mayor venta; si no hay venta,
    # el de mayor existencia para evitar duplicar un mismo ID_ART en varios pasillos/tiendas.
    dim=work[["__id","Sección","Área reporte","Tipo catálogo",vcol,"Existencia"]].copy()
    dim["__sale"]=pd.to_numeric(dim[vcol],errors="coerce").fillna(0.0)
    dim["__exist"]=pd.to_numeric(dim["Existencia"],errors="coerce").fillna(0.0)
    dim=dim.sort_values(["__id","__sale","__exist"],ascending=[True,False,False]).drop_duplicates("__id")
    dim=dim.set_index("__id")
    model=model.set_index("__id").join(dim[["Sección","Área reporte","Tipo catálogo"]],how="left").reset_index()

    group_key={"section":"Sección","area":"Área reporte","catalog":"Tipo catálogo","general":None}.get(str(group_by or "section").lower(),"Sección")
    total_scope=float(model["sales_value"].sum())
    groups=[("General",model)] if group_key is None else list(model.groupby(group_key,dropna=False,sort=False))
    rows=[]
    for label,g in groups:
        label=str(label or "Sin clasificar")
        ex=float(g["existence"].sum());cap=float(g["capacity"].sum());sug=float(g["suggested"].sum())
        weights=g["suggested"].replace(0,np.nan)
        ddi=float((g["ddi"]*g["suggested"]).sum()/sug) if sug else float(g["ddi"].mean() if len(g) else 0)
        sv=float(g["sales_value"].sum())
        rows.append({"label":label,"models_80":int((g["segment"]=="80").sum()),"models_20":int((g["segment"]=="20").sum()),
            "models":int(len(g)),"sales_pzas":float(g["sales_pzas"].sum()),"sales_value":sv,"suggested":sug,"ddi":ddi,
            "capacity":cap,"occupancy":ex/cap*100 if cap else None,"participation":sv/total_scope*100 if total_scope else 0.0})
    rows.sort(key=lambda r:-float(r.get("participation") or 0))
    return {"models_80":int((model["segment"]=="80").sum()),"models_20":int((model["segment"]=="20").sum()),"total_models":int(len(model)),"rows":rows,
        "sales_value":float(model["sales_value"].sum()),"sales_pzas":float(model["sales_pzas"].sum()),"group_by":group_by}


@app.get("/api/model-8020-summary")
def model_8020_summary(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos", group_by: str="section"):
    u=require_user(request)
    store=effective_store(u,store)
    payload=_capacity_8020_summary(store,section,catalog,week or "",group_by)
    return {"week":week or "","store":store,"section":section,"catalog":catalog,**payload}


def parse_sales_pdf(path: str | Path, year: int | None=None, month: int | None=None) -> dict:
    path=Path(path)
    record={"file":path.name,"year":year,"month":month,"rows":0,"store":"","status":"Sin información útil"}
    try:
        text=""
        with pdfplumber.open(path) as pdf:
            pieces=[]
            for page in pdf.pages[:3]:
                pieces.append(page.extract_text() or "")
            text="\n".join(pieces)
        store=store_from_filename(path) or _store_from_pdf_text(text)
        record.update({"store":store,"status":"Procesado" if text.strip() else "PDF sin texto legible","rows":1 if text.strip() else 0})
    except Exception as exc:
        record.update({"status":f"Error: {type(exc).__name__}","error":str(exc)})
    return record


def save_sales_pdf_snapshot(entry_id: str, payload: dict):
    try:
        sales_dir=Path(os.environ.get("OPERACIONES_ROPA_DATA", str(Path.home()/"OperacionesRopaData")))/"commercial_data"/"sales_snapshots"
        sales_dir.mkdir(parents=True,exist_ok=True)
        target=sales_dir/f"{entry_id}.json"
        target.write_text(json.dumps(payload,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
    except Exception as exc:
        print(f"[V41] No se pudo guardar snapshot de ventas {entry_id}: {exc}")

def _capacity_location_detail(store: str="Compañía", section: str="Todas", catalog: str="Todos", period: str=""):
    """Detalle de ubicación operativo, vectorizado y basado en Excel capacidades."""
    try:
        frame=_capacity_frame_for_period(period)
        if frame.empty:
            return []
        work=_capacity_scope_v45(frame, store, section, catalog, add_area=True)
        if work.empty:
            return []
        work=work.copy()
        work["Grupo ubicación"]=work.get("Área reporte", _capacity_area_report_series(work)).fillna("").astype(str).str.strip()
        work["Pasillo real"]=_operational_location_series(work)
        work=work[work["Pasillo real"].fillna("").astype(str).str.strip().ne("")]
        if work.empty:
            return []
        pcol,vcol=_capacity_period_columns(period)
        group_cols=["Grupo ubicación","Pasillo real"] if store!="Compañía" else ["Tienda","Grupo ubicación","Pasillo real"]
        tmp=work[group_cols].copy()
        tmp["ID_ART"]=work.get("ID_ART",pd.Series("",index=work.index)).fillna("").astype(str).str.strip()
        for dst,src in (("capacity","Capacidad"),("floor","Existencia piso"),("warehouse","Existencia bodega"),("existence","Existencia"),("suggested","VPD"),("sales_pzas",pcol),("sales_value",vcol)):
            tmp[dst]=pd.to_numeric(work.get(src,0),errors="coerce").fillna(0.0)
        ddi=pd.to_numeric(work.get("DDI",0),errors="coerce").fillna(0.0)
        tmp["ddi_weighted"]=ddi*tmp["suggested"]
        sums=tmp.groupby(group_cols,dropna=False,sort=False)[["capacity","floor","warehouse","existence","suggested","sales_pzas","sales_value","ddi_weighted"]].sum()
        ids=tmp[tmp["ID_ART"].ne("")].groupby(group_cols,dropna=False,sort=False)["ID_ART"].nunique().rename("ids")
        agg=sums.join(ids,how="left").fillna({"ids":0}).reset_index()
        agg["ddi"]=np.where(agg["suggested"]>0,agg["ddi_weighted"]/agg["suggested"],0.0)
        agg["occupancy"]=np.where(agg["capacity"]>0,agg["existence"]/agg["capacity"]*100,np.nan)
        result=[]
        for r in agg.to_dict("records"):
            if store=="Compañía":
                st=r.get("Tienda","")
            else:
                st=store
            result.append({"store":str(st),"group":str(r.get("Grupo ubicación") or ""),"location":str(r.get("Pasillo real") or ""),
                "ids":int(r.get("ids") or 0),"capacity":float(r.get("capacity") or 0),"floor":float(r.get("floor") or 0),
                "warehouse":float(r.get("warehouse") or 0),"existence":float(r.get("existence") or 0),"suggested":float(r.get("suggested") or 0),
                "ddi":float(r.get("ddi") or 0),"occupancy":None if pd.isna(r.get("occupancy")) else float(r.get("occupancy")),
                "sales_pzas":float(r.get("sales_pzas") or 0),"sales_value":float(r.get("sales_value") or 0),
                "section":section if section!="Todas" else "Todas","catalog":catalog,"source":"Excel capacidades"})
        order={"Colgado":1,"Doblado":2,"Jeans":3,"Lencería":4}
        result.sort(key=lambda x:(order.get(x["group"],99),-float(x.get("suggested") or 0),str(x.get("store") or ""),x["location"]))
        return result
    except Exception as exc:
        print(f"[V47] No se pudo construir detalle por ubicación: {type(exc).__name__}: {exc}")
        return []



def _capacity_processed_entries():
    manifest=load_manifest()
    return [x for x in manifest.get("capacities",[]) if str(x.get("status") or "").lower()=="procesado"]


def _capacity_source_entry(period: str=""):
    caps=_capacity_processed_entries()
    if not caps:return None
    if period:
        matching=[]
        for e in caps:
            d=_capacity_report_date(e)
            iso=d.isocalendar(); wk=f"{iso.year}-W{iso.week:02d}"; mo=f"{d.year:04d}-{d.month:02d}"
            if period in (wk,mo):matching.append(e)
        if matching:
            return sorted(matching,key=lambda x:(_capacity_report_date(x),str(x.get("uploaded_at") or "")))[-1]
    return sorted(caps,key=lambda x:str(x.get("uploaded_at") or x.get("created_at") or ""))[-1]


def _capacity_report_date(entry: dict | None):
    if not entry:return datetime.now().date()
    raw=" ".join(str(entry.get(k) or "") for k in ("report_date","name","uploaded_at"))
    m=re.search(r"(?<!\d)(\d{1,2})[._-](\d{1,2})[._-](\d{2,4})(?!\d)",raw)
    if m:
        d,mo,y=map(int,m.groups()); y=y+2000 if y<100 else y
        try:return datetime(y,mo,d).date()
        except Exception:pass
    m=re.search(r"(?<!\d)(20\d{2})[._-](\d{1,2})[._-](\d{1,2})(?!\d)",raw)
    if m:
        y,mo,d=map(int,m.groups())
        try:return datetime(y,mo,d).date()
        except Exception:pass
    try:return datetime.fromisoformat(str(entry.get("uploaded_at") or "").replace("Z","+00:00")).date()
    except Exception:return datetime.now().date()


def _capacity_period_options(requested: str=""):
    weeks=[];months=[]
    for e in _capacity_processed_entries():
        d=_capacity_report_date(e); iso=d.isocalendar()
        weeks.append(f"{iso.year}-W{iso.week:02d}");months.append(f"{d.year:04d}-{d.month:02d}")
    weeks=sorted(set(weeks),reverse=True);months=sorted(set(months),reverse=True)
    values=weeks+months
    if not values:
        d=datetime.now().date();iso=d.isocalendar();values=[f"{iso.year}-W{iso.week:02d}",f"{d.year:04d}-{d.month:02d}"]
    if requested and requested not in values:values.insert(0,requested)
    return values


def _capacity_frame_for_period(period: str="") -> pd.DataFrame:
    entry=_capacity_source_entry(period)
    if not entry:return pd.DataFrame()
    try:
        path=resolve_entry_path(entry);mtime=path.stat().st_mtime if path.exists() else None
        cached=_CAPACITY_FRAME_CACHE.get("frame")
        if cached is not None and _CAPACITY_FRAME_CACHE.get("path")==str(path) and _CAPACITY_FRAME_CACHE.get("mtime")==mtime:return cached
        frame=_load_capacity_cache(entry)
        if frame.empty:
            frame=read_capacity_file(path)
            if isinstance(frame,pd.DataFrame) and not frame.empty:
                cache_path=_capacity_cache_path(str(entry.get("id") or ""))
                try:
                    frame.to_pickle(cache_path);update_entry("capacities",str(entry.get("id") or ""),cache_file=str(cache_path.relative_to(DATA_ROOT)))
                except Exception:pass
        if isinstance(frame,pd.DataFrame):
            frame=_normalize_capacity_store_aliases(frame)
            _CAPACITY_FRAME_CACHE.update({"path":str(path),"mtime":mtime,"frame":frame});return frame
    except Exception as exc:print(f"[V45] Error leyendo capacidad por periodo: {type(exc).__name__}: {exc}")
    return pd.DataFrame()


def _normalize_capacity_store_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    """Corrige alias del Excel aun cuando el catálogo cacheado provenga de V45."""
    if frame is None or frame.empty or "Tienda" not in frame.columns:
        return frame
    out=frame.copy()
    keys=out["Tienda"].fillna("").astype(str).map(login_key)
    # En el Excel de capacidades: Guadalajara = Atemajac y Guadalajara Miravalle = Miravalle.
    out.loc[keys==login_key("Guadalajara"),"Tienda"]="Atemajac"
    out.loc[keys.isin([login_key("Guadalajara Miravalle"),login_key("Miravalle Guadalajara")]),"Tienda"]="Miravalle"
    return out


def _capacity_period_columns(period: str=""):
    monthly=bool(re.fullmatch(r"\d{4}-\d{2}",str(period or "")))
    return ("Venta pzas","Venta $ mes") if monthly else ("Venta pzas 7","Venta $ 7")


def _capacity_area_report_series(frame: pd.DataFrame) -> pd.Series:
    """Área comercial operativa.

    La clasificación se apoya primero en PASILLO/ubicación real y después en la
    familia del producto. Las exhibiciones no se convierten en pasillos, pero sí
    conservan el área de mercancía para que sus piezas/venta formen parte del macro.
    """
    if frame is None or frame.empty:
        return pd.Series(dtype=str)
    sub=frame.get("Subcategoría",pd.Series("",index=frame.index)).fillna("").astype(str).str.upper()
    cat=frame.get("Categoría",pd.Series("",index=frame.index)).fillna("").astype(str).str.upper()
    aisle=frame.get("Pasillo",pd.Series("",index=frame.index)).fillna("").astype(str).str.upper()
    text=sub.str.cat(cat,sep=" ").str.cat(aisle,sep=" ")
    out=pd.Series("Doblado",index=frame.index,dtype="object")
    lenc=text.str.contains(r"LENCER|BRASIER|PANTIB|BOXER|BIKINI|INTERIOR",regex=True,na=False)
    jeans=text.str.contains(r"JEAN|MEZCLILLA|FERGINO|SURPRISE|SEVEN\s*ELEVEN|SEVEN ELEVEN",regex=True,na=False)
    colg=text.str.contains(r"R\.?\s*COLGAD[AO]|PASILLO\s*COLG|ROPA\s*COLG|RACK|CHAMARRA|ABRIGO|SACO|VESTIDO|BLUSA|CHALECO|ENSAMBLE|PONCHO|GABARDINA",regex=True,na=False)
    out.loc[colg]="Colgado"
    out.loc[jeans]="Jeans"
    out.loc[lenc]="Lencería"
    return out


def _operational_location_value(raw_value, area: str, store: str="") -> str:
    """Devuelve sólo una ubicación operativa válida.

    Reglas solicitadas:
    - Colgado: pasillos / R. COLGADA / ropa colgada.
    - Doblado: mesas operativas.
    - Jeans: Jeans, Jeans Mezclilla, Fergino, Surprise y Seven Eleven.
    - Lencería: ubicaciones de lencería.
    Cualquier otra etiqueta (cabecera, botadero, isla, rounder, pony, ofertas,
    exhibición, probador, etc.) se considera exhibición y no se publica como pasillo.
    """
    raw=str(raw_value or "").strip()
    if not raw or raw.lower() in ("nan","none"):
        return ""
    parts=[x.strip() for x in re.split(r"[,;/]+",raw) if x.strip()]
    exhibit_tokens=("CABECERA","BOTADERO","ISLA","ROUNDER","PONY","EXHIB","OFERTA","PROBADOR","PASTELERA","ARBOL","ÁRBOL","OUTLET")
    area_key=login_key(area)
    store_key=login_key(store)
    ixta_keywords=("CABALLEROS","CABALLERO","BLUSAS","BLUSA","VESTIDOS","VESTIDO","CHAMARRAS","CHAMARRA","ABRIGOS","ABRIGO","INFANTILES","INFANTIL","DAMA LICENCIA","INFANTILES LICENCIA","PALAZZOS","EJECUTIVA")
    for part in parts:
        key=login_key(part).upper()
        if any(tok in key for tok in exhibit_tokens):
            continue
        if area_key==login_key("Colgado"):
            if re.search(r"R\.?\s*COLGAD[AO]",key) or "PASILLO COLG" in key or "ROPA COLG" in key:
                return part
            if store_key==login_key("Ixtapaluca") and any(tok in key for tok in ixta_keywords):
                return part
        elif area_key==login_key("Doblado"):
            if "MESA" in key and not any(tok in key for tok in ("EXH","REDONDA","OFERTA")):
                return part
        elif area_key==login_key("Jeans"):
            if "BODEGA" in key:
                continue
            if any(tok in key for tok in ("JEANS","MEZCLILLA","FERGINO","SURPRISE","SEVEN ELEVEN","SEVEN JEANS")):
                return part
        elif area_key==login_key("Lencería"):
            if "LENCER" in key and not any(tok in key for tok in ("EXHIB","ARBOL","ÁRBOL")):
                return part
    return ""


def _operational_location_series(frame: pd.DataFrame) -> pd.Series:
    """Versión vectorizada: selecciona la primera ubicación operativa válida."""
    if frame is None or frame.empty:
        return pd.Series(dtype=str)
    areas=frame.get("Área reporte",_capacity_area_report_series(frame)).fillna("").astype(str)
    raw=frame.get("Pasillo",frame.get("Ubicación detalle",pd.Series("",index=frame.index))).fillna("").astype(str).str.strip()
    stores=frame.get("Tienda",pd.Series("",index=frame.index)).fillna("").astype(str)
    # Explota únicamente los componentes de ubicación. Es vectorizado y mucho más
    # rápido que recorrer ~196 mil filas con Python.
    parts=raw.str.split(r"[,;/]+",regex=True).explode().astype(str).str.strip()
    parts=parts[parts.ne("") & ~parts.str.lower().isin(["nan","none"])]
    if parts.empty:
        return pd.Series("",index=frame.index,dtype="object")
    pkey=parts.map(login_key).str.upper()
    area_exp=areas.reindex(parts.index).map(login_key)
    store_exp=stores.reindex(parts.index).map(login_key)
    exhibit=pkey.str.contains(r"CABECERA|BOTADERO|ISLA|ROUNDER|PONY|EXHIB|OFERTA|PROBADOR|PASTELERA|ARBOL|OUTLET",regex=True,na=False)
    colg=(area_exp==login_key("Colgado")) & (
        pkey.str.contains(r"R\.?\s*COLGAD[AO]|PASILLO\s*COLG|ROPA\s*COLG",regex=True,na=False)
    )
    ixta_kw=pkey.str.contains(r"CABALLEROS?|BLUSAS?|VESTIDOS?|CHAMARRAS?|ABRIGOS?|INFANTILES?|DAMA LICENCIA|INFANTILES LICENCIA|PALAZZOS|EJECUTIVA",regex=True,na=False)
    colg=colg | ((area_exp==login_key("Colgado")) & (store_exp==login_key("Ixtapaluca")) & ixta_kw)
    dobl=(area_exp==login_key("Doblado")) & pkey.str.contains(r"\bMESA\b",regex=True,na=False) & ~pkey.str.contains(r"EXH|REDONDA|OFERTA",regex=True,na=False)
    jeans=(area_exp==login_key("Jeans")) & pkey.str.contains(r"JEANS|MEZCLILLA|FERGINO|SURPRISE|SEVEN ELEVEN|SEVEN JEANS",regex=True,na=False) & ~pkey.str.contains(r"BODEGA",regex=True,na=False)
    lenc=(area_exp==login_key("Lencería")) & pkey.str.contains(r"LENCER",regex=True,na=False) & ~pkey.str.contains(r"EXHIB|ARBOL",regex=True,na=False)
    valid=(colg|dobl|jeans|lenc) & ~exhibit
    selected=parts[valid]
    if selected.empty:
        return pd.Series("",index=frame.index,dtype="object")
    first=selected.groupby(level=0,sort=False).first()
    return first.reindex(frame.index).fillna("").astype(str)


def _capacity_scope_v45(frame: pd.DataFrame, store: str="Compañía", section: str="Todas", catalog: str="Todos", add_area: bool=False) -> pd.DataFrame:
    if frame is None or frame.empty:return pd.DataFrame()
    work=frame
    if store and store!="Compañía":
        work=work[work["Tienda"].map(login_key)==login_key(store)]
    else:
        active=set(store_names(True) or PROJECT_STORES)
        work=work[work["Tienda"].isin(active)]
    if section and section!="Todas":work=work[work["Sección"].map(login_key)==login_key(section)]
    if catalog and catalog not in ("Todos","Todas","") and "Tipo catálogo" in work.columns:
        work=work[work["Tipo catálogo"].map(login_key)==login_key(catalog)]
    if work.empty:return work.copy()
    work=work.copy()
    if add_area:
        work["Área reporte"]=_capacity_area_report_series(work)
    return work


def _ddi_weighted(g: pd.DataFrame) -> float:
    if g is None or g.empty:return 0.0
    ddi=pd.to_numeric(g.get("DDI",0),errors="coerce").fillna(0.0)
    sug=pd.to_numeric(g.get("VPD",0),errors="coerce").fillna(0.0)
    mask=(ddi>=0)&(sug>0)
    if mask.any() and float(sug[mask].sum())>0:
        return float((ddi[mask]*sug[mask]).sum()/sug[mask].sum())
    vals=ddi[ddi>0]
    return float(vals.mean()) if len(vals) else 0.0


def _capacity_metrics(g: pd.DataFrame, period: str="") -> dict:
    if g is None or g.empty:
        return {"existence":0.0,"floor":0.0,"warehouse":0.0,"suggested":0.0,"capacity":0.0,"ddi":0.0,"occupancy":0.0,"sales_pzas":0.0,"sales_value":0.0,"utility_value":0.0}
    pcol,vcol=_capacity_period_columns(period)
    ex=float(pd.to_numeric(g.get("Existencia",0),errors="coerce").fillna(0).sum())
    floor=float(pd.to_numeric(g.get("Existencia piso",0),errors="coerce").fillna(0).sum())
    wh=float(pd.to_numeric(g.get("Existencia bodega",0),errors="coerce").fillna(0).sum())
    sug=float(pd.to_numeric(g.get("VPD",0),errors="coerce").fillna(0).sum())
    cap=float(pd.to_numeric(g.get("Capacidad",0),errors="coerce").fillna(0).sum())
    sp=float(pd.to_numeric(g.get(pcol,0),errors="coerce").fillna(0).sum())
    sv=float(pd.to_numeric(g.get(vcol,0),errors="coerce").fillna(0).sum())
    util_pct=pd.to_numeric(g.get("Utilidad %",0),errors="coerce").fillna(0)
    sale_row=pd.to_numeric(g.get(vcol,0),errors="coerce").fillna(0)
    uv=float((sale_row*util_pct/100).sum())
    return {"existence":ex,"floor":floor,"warehouse":wh,"suggested":sug,"capacity":cap,"ddi":_ddi_weighted(g),"occupancy":ex/cap*100 if cap else 0.0,"sales_pzas":sp,"sales_value":sv,"utility_value":uv}


def _capacity_sections_v45(work: pd.DataFrame, period: str=""):
    if work.empty:return []
    total=_capacity_metrics(work,period)
    rows=[]
    order={"Dama":0,"Caballero":1,"Infantil":2,"Sin sección":9}
    for name,g in work.groupby("Sección",dropna=False,sort=False):
        m=_capacity_metrics(g,period)
        rows.append({"section":str(name or "Sin sección"),**m,
            "part_pieces":m["sales_pzas"]/total["sales_pzas"]*100 if total["sales_pzas"] else 0.0,
            "utility":m["utility_value"]/total["utility_value"]*100 if total["utility_value"] else 0.0,
            "part_inventory":m["existence"]/total["existence"]*100 if total["existence"] else 0.0})
    return sorted(rows,key=lambda r:(order.get(r["section"],8),r["section"]))


def _capacity_locations_v45(work: pd.DataFrame, period: str=""):
    if work.empty:return []
    if "Área reporte" not in work.columns:
        work=work.copy(); work["Área reporte"]=_capacity_area_report_series(work)
    rows=[]
    for name,g in work.groupby("Área reporte",dropna=False,sort=False):
        m=_capacity_metrics(g,period)
        rows.append({"location":str(name or "Sin ubicación"),**m})
    return sorted(rows,key=lambda r:-float(r.get("suggested") or 0))


def _capacity_store_comparative_v45(frame: pd.DataFrame, managed: list[str], section: str, catalog: str, period: str):
    base=_capacity_scope_v45(frame,"Compañía",section,catalog)
    if base.empty:
        return [{"store":name,"available":False,"suggested":None,"existence":None,"floor":None,"warehouse":None,"capacity":None,"ddi":None,"occupancy":None} for name in managed]
    pcol,vcol=_capacity_period_columns(period)
    tmp=pd.DataFrame({"store":base["Tienda"].astype(str)})
    for dst,src in (("existence","Existencia"),("floor","Existencia piso"),("warehouse","Existencia bodega"),("suggested","VPD"),("capacity","Capacidad"),("sales_pzas",pcol),("sales_value",vcol)):
        tmp[dst]=pd.to_numeric(base.get(src,0),errors="coerce").fillna(0.0)
    ddi=pd.to_numeric(base.get("DDI",0),errors="coerce").fillna(0.0)
    tmp["ddi_weighted"]=ddi*tmp["suggested"]
    util_pct=pd.to_numeric(base.get("Utilidad %",0),errors="coerce").fillna(0.0)
    tmp["utility_value"]=tmp["sales_value"]*util_pct/100
    agg=tmp.groupby("store",sort=False).sum(numeric_only=True)
    out=[]
    lookup={login_key(x):x for x in agg.index.astype(str)}
    for name in managed:
        actual=lookup.get(login_key(name))
        if actual is None:
            out.append({"store":name,"available":False,"suggested":None,"existence":None,"floor":None,"warehouse":None,"capacity":None,"ddi":None,"occupancy":None})
            continue
        r=agg.loc[actual];sug=float(r["suggested"]);ex=float(r["existence"]);cap=float(r["capacity"])
        out.append({"store":name,"available":True,"existence":ex,"floor":float(r["floor"]),"warehouse":float(r["warehouse"]),"suggested":sug,"capacity":cap,
            "ddi":float(r["ddi_weighted"])/sug if sug else 0.0,"occupancy":ex/cap*100 if cap else 0.0,"sales_pzas":float(r["sales_pzas"]),"sales_value":float(r["sales_value"]),"utility_value":float(r["utility_value"])})
    return out


def _capacity_rubros_v45(work: pd.DataFrame, section: str="Todas", period: str=""):
    """Detalle por rubro/subcategoría directamente desde capacidades."""
    if work is None or work.empty:
        return []
    base=work.copy()
    if "Subcategoría" not in base.columns:
        return []
    base["Subcategoría"]=base["Subcategoría"].fillna("").astype(str).str.strip()
    base=base[base["Subcategoría"].ne("")]
    if base.empty:
        return []
    # Aun en Compañía/Todas se conserva la sección real para que el detalle sea
    # legible y pueda ordenarse macro -> sección -> rubro.
    group_cols=["Sección","Subcategoría"] if "Sección" in base.columns else ["Subcategoría"]
    rows=[]
    for keys,g in base.groupby(group_cols,dropna=False,sort=False):
        if not isinstance(keys,tuple):
            keys=(keys,)
        if len(keys)>=2:
            sec=str(keys[0] or "Sin sección"); rub=str(keys[1] or "Sin subcategoría")
        else:
            sec=section if section!="Todas" else "Compañía"; rub=str(keys[0] or "Sin subcategoría")
        m=_capacity_metrics(g,period)
        rows.append({"store":"Compañía","section":sec,"rubro":rub,"models":int(g["ID_ART"].fillna("").astype(str).str.strip().replace({"nan":"","None":""}).nunique()),**m})
    return sorted(rows,key=lambda r:(-float(r.get("sales_value") or 0),-float(r.get("suggested") or 0),str(r.get("section") or ""),r["rubro"]))


def _capacity_accordion_payload(store: str="Compañía", section: str="Todas", catalog: str="Todos", period: str="") -> dict:
    frame=_capacity_frame_for_period(period)
    work=_capacity_scope_v45(frame,store,section,catalog,add_area=True) if not frame.empty else pd.DataFrame()
    if work.empty:
        return {"general":_capacity_metrics(pd.DataFrame(),period),"sections":[],"brands":[],"rubros":[],"areas":[],"catalogs":[],"models_8020":0,"models_total":0}
    general=_capacity_metrics(work,period)
    sections=_capacity_sections_v45(work,period)
    rubros=_capacity_rubros_v45(work,section,period)[:8]
    areas=_capacity_locations_v45(work,period)
    pcol,vcol=_capacity_period_columns(period)
    brands=[]
    if "Marca" in work.columns:
        for name,g in work.groupby("Marca",dropna=False,sort=False):
            label=str(name or "Sin marca").strip() or "Sin marca"
            m=_capacity_metrics(g,period)
            brands.append({"brand":label,**m})
        brands=sorted(brands,key=lambda r:(-float(r.get("sales_value") or 0),-float(r.get("suggested") or 0)))[:8]
    catalogs=[]
    if "Tipo catálogo" in work.columns:
        for name,g in work.groupby("Tipo catálogo",dropna=False,sort=False):
            label=str(name or "Sin catálogo").strip() or "Sin catálogo"
            m=_capacity_metrics(g,period)
            catalogs.append({"catalog":label,**m})
        catalogs=sorted(catalogs,key=lambda r:-float(r.get("sales_value") or 0))
    summary=_capacity_8020_summary(store,section,catalog,period,"general")
    return {"general":general,"sections":sections,"brands":brands,"rubros":rubros,"areas":areas,"catalogs":catalogs,
            "models_8020":int(summary.get("models_80") or 0),"models_20":int(summary.get("models_20") or 0),"models_total":int(summary.get("total_models") or 0)}


@app.get("/api/commercial-accordion")
def commercial_accordion(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos"):
    u=require_user(request)
    store=effective_store(u,store)
    return {"week":week or "","store":store,"section":section,"catalog":catalog,**_capacity_accordion_payload(store,section,catalog,week or "")}

@app.get("/api/dashboard")
def dashboard(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos"):
    u=require_user(request)
    store=effective_store(u,store)
    section=section if section in ("Todas","Dama","Caballero","Infantil") else "Todas"
    periods=_capacity_period_options(week or "")
    selected=week or (periods[0] if periods else "")
    frame=_capacity_frame_for_period(selected)
    managed=store_names(True) or list(PROJECT_STORES)
    if u["role"]=="tienda":managed=[u.get("store") or ""]
    if frame.empty:
        return {"week":selected,"weeks":periods,"stores_available":managed,"processed_pdfs":0,"expected_pdfs":0,
            "data_source":"Excel de capacidades","source_file":"","kpis":_capacity_metrics(pd.DataFrame(),selected),"stores":[],"sections":[],"locations":[],"champions":[],"slow":[],"user":u,"selected_store":store,"selected_section":section,"selected_catalog":catalog}
    work=_capacity_scope_v45(frame,store,section,catalog)
    k=_capacity_metrics(work,selected)
    sections=_capacity_sections_v45(_capacity_scope_v45(frame,store,"Todas",catalog),selected)
    if section!="Todas":sections=[r for r in sections if login_key(r["section"])==login_key(section)]
    stores=_capacity_store_comparative_v45(frame,managed,section,catalog,selected)
    locations=_capacity_locations_v45(work,selected)
    entry=_capacity_source_entry(selected) or {}
    present_keys={login_key(x) for x in frame["Tienda"].dropna().astype(str).unique().tolist()}
    available=[s for s in managed if login_key(s) in present_keys]
    return {"week":selected,"weeks":periods,"stores_available":available,"processed_pdfs":1,"expected_pdfs":1,
      "data_source":"Excel de capacidades","source_file":entry.get("name","") ,"kpis":k,"stores":stores,"sections":sections,"locations":locations,
      "champions":[],"slow":[],"user":u,"selected_store":store,"selected_section":section,"selected_catalog":catalog}


@app.get("/api/model-ranking")
def model_ranking(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", slow: bool=False, mode: str|None=None, catalog: str="Todos"):
    u=require_user(request)
    selected,weeks,rows=_week_rows(week)
    store=effective_store(u,store)
    report_mode=(mode or ("slow" if slow else "80_20"))
    capacity_rows=_capacity_model_rows(store,section,report_mode,week or "",catalog)
    if capacity_rows:
        return {"week":selected,"store":store,"section":section,"slow":slow,"mode":report_mode,"rows":capacity_rows}
    if store and store!="Compañía":
        rows=[r for r in rows if r.get("store")==store]
    scoped=[]
    for snap in rows:
        s=_scope_snapshot(snap,section)
        if s:
            scoped.append(s)
    return {
        "week":selected,"store":store,"section":section,"slow":slow,"mode":report_mode,
        "rows":_model_rows(scoped,slow)
    }


CHECKLIST_FIELDS=("en_ubicacion","cenefa_correcta","todas_tallas","exhibido")
CHECKLIST_LABELS={
    "en_ubicacion":"Está en ubicación",
    "cenefa_correcta":"Cenefa correcta",
    "todas_tallas":"Todas las tallas",
    "exhibido":"Exhibido",
}

def _check_value(value):
    if value is None or value=="":
        return None
    if isinstance(value,bool):
        return 1 if value else 0
    text=login_key(value)
    if text in ("si","sí","1","true","yes"):
        return 1
    if text in ("no","0","false"):
        return 0
    raise HTTPException(400,"La respuesta de checklist debe ser Sí o No")

@app.get("/api/model-checklist")
def model_checklist_get(request: Request, week: str, store: str):
    u=require_user(request)
    store=effective_store(u,store)
    if not store or store=="Compañía":
        return {"week":week,"store":"Compañía","rows":[],"editable":False}
    with db() as con:
        rows=con.execute(
            "SELECT week,store,id_art,model,section,rubro,en_ubicacion,cenefa_correcta,todas_tallas,exhibido,updated_at,updated_by "
            "FROM model_checklist WHERE week=? AND store=? ORDER BY id_art",
            (week,store)
        ).fetchall()
    editable=(
        u["role"] in ("superadmin","admin")
        or (u["role"]=="tienda" and login_key(store)==login_key(u.get("store") or ""))
    )
    return {"week":week,"store":store,"rows":[dict(r) for r in rows],"editable":editable}

@app.post("/api/model-checklist")
async def model_checklist_save(request: Request):
    u=require_user(request,("superadmin","admin","tienda"))
    body=await request.json()
    week=str(body.get("week") or "").strip()
    store=str(body.get("store") or "").strip()
    id_art=str(body.get("id_art") or "").strip()
    if u["role"]=="tienda":
        assigned=str(u.get("store") or "")
        if store and login_key(store)!=login_key(assigned):
            raise HTTPException(403,"Sólo puedes modificar la tienda que tienes asignada")
        store=assigned
    elif u["role"] in ("superadmin","admin"):
        active={login_key(x) for x in store_names(True)}
        if login_key(store) not in active:
            raise HTTPException(400,"Selecciona una tienda activa del proyecto")
    if not week or not store or store=="Compañía" or not id_art:
        raise HTTPException(400,"Selecciona una tienda y un modelo")
    vals={f:_check_value(body.get(f)) for f in CHECKLIST_FIELDS}
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute(
            """INSERT INTO model_checklist(
                week,store,id_art,model,section,rubro,
                en_ubicacion,cenefa_correcta,todas_tallas,exhibido,updated_at,updated_by
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(week,store,id_art) DO UPDATE SET
                model=excluded.model,section=excluded.section,rubro=excluded.rubro,
                en_ubicacion=excluded.en_ubicacion,cenefa_correcta=excluded.cenefa_correcta,
                todas_tallas=excluded.todas_tallas,exhibido=excluded.exhibido,
                updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
            (
                week,store,id_art,str(body.get("model") or ""),str(body.get("section") or ""),
                str(body.get("rubro") or ""),vals["en_ubicacion"],vals["cenefa_correcta"],
                vals["todas_tallas"],vals["exhibido"],now,u["username"]
            )
        )
    return {"ok":True,"message":"Checklist guardado","updated_at":now}

@app.get("/api/model-checklist/summary")
def model_checklist_summary(request: Request, week: str):
    u=require_user(request)
    # Resumen visible para niveles ejecutivos/administrativos.
    if u["role"]=="tienda":
        allowed=[str(u.get("store") or "")]
    else:
        allowed=store_names(True)
    with db() as con:
        rows=con.execute(
            "SELECT store,id_art,model,section,rubro,en_ubicacion,cenefa_correcta,todas_tallas,exhibido,updated_at "
            "FROM model_checklist WHERE week=?",(week,)
        ).fetchall()
    grouped={}
    for rr in rows:
        r=dict(rr)
        if r["store"] not in allowed:
            continue
        g=grouped.setdefault(r["store"],{"store":r["store"],"models":0,"criteria":{f:{"yes":0,"no":0,"answered":0,"missing":[]} for f in CHECKLIST_FIELDS}})
        g["models"]+=1
        for f in CHECKLIST_FIELDS:
            v=r.get(f)
            if v is None:
                continue
            g["criteria"][f]["answered"]+=1
            if int(v)==1:
                g["criteria"][f]["yes"]+=1
            else:
                g["criteria"][f]["no"]+=1
                g["criteria"][f]["missing"].append({
                    "id_art":r["id_art"],"model":r["model"],"section":r["section"],"rubro":r["rubro"]
                })
    out=[]
    for store in allowed:
        g=grouped.get(store,{"store":store,"models":0,"criteria":{f:{"yes":0,"no":0,"answered":0,"missing":[]} for f in CHECKLIST_FIELDS}})
        total_answered=0
        criteria_scores=[]
        for f,c in g["criteria"].items():
            c["pct"]=c["yes"]/c["answered"]*100 if c["answered"] else None
            c["label"]=CHECKLIST_LABELS[f]
            total_answered+=c["answered"]
            criteria_scores.append(float(c["pct"] or 0))
        # Score = promedio simple de los 4 criterios. Un criterio sin respuesta aporta 0.
        g["score"]=sum(criteria_scores)/len(CHECKLIST_FIELDS) if CHECKLIST_FIELDS else 0.0
        g["score_answered"]=total_answered
        out.append(g)
    out.sort(key=lambda x:(-float(x.get("score") or 0),x.get("store") or ""))
    return {"week":week,"rows":out,"labels":CHECKLIST_LABELS}



@app.get("/api/export/checklist-summary")
def export_checklist_summary(request: Request, week: str):
    u=require_user(request)
    if u["role"] not in ("superadmin","admin","director"):
        raise HTTPException(403,"No autorizado")
    payload=model_checklist_summary(request,week)
    rows=payload.get("rows",[])
    bio=BytesIO(); c=pdfcanvas.Canvas(bio,pagesize=landscape(letter))
    width,height=landscape(letter); margin=28; y=height-32
    c.setFillColor(colors.HexColor("#173B73")); c.setFont("Helvetica-Bold",17)
    c.drawString(margin,y,"Operaciones Ropa · Resumen checklist de modelos lentos"); y-=22
    c.setFont("Helvetica",9); c.setFillColor(colors.black); c.drawString(margin,y,f"Periodo: {week or 'Sin periodo'}"); y-=22
    headers=["#","Tienda","Ubicación","Cenefa","Tallas","Exhibido","Score"]
    widths=[.05,.20,.14,.14,.14,.14,.12]; total_w=width-margin*2
    xs=[margin]; acc=margin
    for frac in widths[:-1]: acc+=total_w*frac; xs.append(acc)
    def hdr():
        nonlocal y
        c.setFillColor(colors.HexColor("#173B73")); c.rect(margin,y-3,total_w,16,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7)
        for i,h in enumerate(headers): c.drawString(xs[i]+2,y+1,h)
        y-=18
    hdr()
    for i,r in enumerate(rows,1):
        if y<42: c.showPage(); y=height-32; hdr()
        vals=[i,r.get("store",""),*(f'{float((r.get("criteria") or {}).get(f,{}).get("pct") or 0):.1f}%' for f in CHECKLIST_FIELDS),f'{float(r.get("score") or 0):.1f}%']
        if i%2==0:
            c.setFillColor(colors.HexColor("#F5F8FC")); c.rect(margin,y-3,total_w,14,fill=1,stroke=0)
        c.setFillColor(colors.black); c.setFont("Helvetica",7)
        for j,v in enumerate(vals): c.drawString(xs[j]+2,y,str(v)[:26])
        y-=14
    if not rows:
        c.setFont("Helvetica",9); c.drawString(margin,y,"Sin información disponible para el periodo seleccionado")
    c.save(); data=bio.getvalue()
    if not data.startswith(b"%PDF"): raise HTTPException(500,"No se generó un PDF válido")
    return Response(content=data,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="checklist_{re.sub(r"[^0-9A-Za-z_-]+","_",week or "periodo")}.pdf"'})

@app.get("/api/commercial-detail")
def commercial_detail(request: Request, week: str|None=None, store: str="Compañía", section: str="Todas", catalog: str="Todos"):
    u=require_user(request)
    store=effective_store(u,store)
    frame=_capacity_frame_for_period(week or "")
    if frame.empty:
        return {"week":week or "","store":store,"section":section,"rubros":[],"locations":[],"warnings":["Carga y procesa el Excel de capacidades para habilitar este reporte."]}
    work=_capacity_scope_v45(frame,store,section,catalog)
    rubros=_capacity_rubros_v45(work,section,week or "")
    locations=_capacity_location_detail(store,section,catalog,week or "")
    return {"week":week or "","store":store,"section":section,"catalog":catalog,"rubros":rubros,"locations":locations,"warnings":[]}


_OPERATIONS_REPARSE_LOCK=threading.Lock()

def _ensure_operations_parser_current():
    """Reprocesa el Excel persistente si la base JSON fue creada con un parser anterior."""
    current=load_ops()
    if int(current.get("parser_version") or 0) >= OPERATIONS_PARSER_VERSION:
        return

    raw_file=DATA_ROOT/"cambios_muertos_actual.xlsx"
    if not raw_file.exists():
        return

    with _OPERATIONS_REPARSE_LOCK:
        current=load_ops()
        if int(current.get("parser_version") or 0) >= OPERATIONS_PARSER_VERSION:
            return

        payload=parse_operations_excel(raw_file,persist=False)
        payload["parser_version"]=OPERATIONS_PARSER_VERSION
        payload["source_file"]=current.get("source_file") or raw_file.name
        payload["uploaded_by"]=current.get("uploaded_by") or "Migración automática V40"
        payload["uploaded_at"]=current.get("uploaded_at") or datetime.now().isoformat(timespec="seconds")
        payload["migration_at"]=datetime.now().isoformat(timespec="seconds")

        tmp=DATA_ROOT/"operations_v40_migration.tmp.json"
        tmp.write_text(_safe_json_dump(payload),encoding="utf-8")
        tmp.replace(OPS_FILE)
        _clear_operations_caches(clear_meta_file=True)
        try:
            OPS_RECOVERY_CACHE_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        print("[V40] Base operativa reprocesada: hojas Resultados productividad consolidadas y recorridos deduplicados por occurrence.")


@app.get("/api/operations/meta")
def operations_meta(request: Request):
    """Metadatos ligeros de Cambios y Muertos. No recalcula reportes ni FIFO."""
    u=require_user(request)
    meta=dict(load_operations_meta())
    if u.get("role")=="tienda" and u.get("store"):
        stores=[u.get("store")]
    else:
        configured=store_names(True)
        detected=set(meta.get("stores_detected") or [])
        stores=[s for s in configured if (not detected or s in detected)]
        if not stores:
            stores=sorted(detected)
    meta["stores_available"]=stores
    meta["project_stores"]=project_store_names(True)
    return meta


@app.get("/api/operations")
def operations(
    request: Request,
    store: str="Compañía",
    period_type: str="all",
    period_value: str="",
    area: str="",
    activity: str="",
    start_date: str="",
    end_date: str="",
    compact: bool=False,
    project_only: bool=False,
):
    u=require_user(request)
    store=effective_store(u,store)

    # Rendimiento V38: los reportes NUNCA vuelven a abrir/reprocesar el Excel.
    # El Excel se interpreta exclusivamente al cargar o reemplazar el archivo y
    # desde aquí sólo se consulta la base persistente ya procesada.

    # Las vistas del navegador usan compact=true. Cacheamos por archivo + filtro.
    source_stamp=_ops_source_stamp()
    cache_key=(source_stamp,store,period_type,period_value,area,activity,start_date,end_date,bool(compact),bool(project_only))
    if compact and cache_key in _OPS_RESPONSE_CACHE:
        return _OPS_RESPONSE_CACHE[cache_key]

    data=load_ops()
    op_all=list(data.get("rows",[]))
    co_all=list(data.get("commercial_daily",[]))

    # Catálogo de periodos reales detectados en el Excel.
    all_dates=sorted({
        str(r.get("date")) for r in (op_all+co_all)
        if r.get("date")
    })
    all_weeks=sorted({
        f"{int(r.get('year_iso'))}-W{int(r.get('week_iso')):02d}"
        for r in (op_all+co_all)
        if r.get("year_iso") and r.get("week_iso")
    })
    all_months=sorted({
        str(r.get("date"))[:7] for r in (op_all+co_all)
        if r.get("date") and len(str(r.get("date")))>=7
    })

    def in_period(r):
        if period_type=="all" or not period_value:
            return True
        date_txt=str(r.get("date") or "")
        if period_type=="day":
            return date_txt==period_value
        if period_type=="month":
            return date_txt.startswith(period_value)
        if period_type=="week":
            try:
                y,w=period_value.split("-W",1)
                return int(r.get("year_iso") or 0)==int(y) and int(r.get("week_iso") or 0)==int(w)
            except Exception:
                return False
        return True

    def in_date_range(r):
        d=str(r.get("date") or "")
        if start_date and (not d or d < start_date): return False
        if end_date and (not d or d > end_date): return False
        return True

    op=[r for r in op_all if in_period(r) and in_date_range(r)]
    co=[r for r in co_all if in_period(r) and in_date_range(r)]

    if store and store!="Compañía":
        op=[r for r in op if r.get("store")==store]
        co=[r for r in co if r.get("store")==store]
    if area:
        wanted=normalize_col(area)
        op=[r for r in op if normalize_col(r.get("area",""))==wanted]
    if activity:
        wanted=normalize_col(activity)
        op=[r for r in op if normalize_col(r.get("activity",""))==wanted or normalize_col(r.get("activity_original",""))==wanted]

    allowed_stores=[u.get("store")] if u.get("role")=="tienda" and u.get("store") else store_names(True)
    if project_only:
        project_allowed=set(project_store_names(True))
        allowed_stores=[s for s in allowed_stores if s in project_allowed]
        op=[r for r in op if r.get("store") in project_allowed]
        co=[r for r in co if r.get("store") in project_allowed]
    if store and store!="Compañía":
        allowed_stores=[store] if (not project_only or store in set(project_store_names(True))) else []
        if project_only and store not in set(project_store_names(True)):
            op=[]; co=[]

    goals=get_goals()

    # Conversión / recuperación:
    # usar lotes FIFO precalculados para que Centro Ejecutivo abra rápido.
    recovery_fifo=_get_recovery_fifo_rows(data)

    conv_detail=[]
    for r in recovery_fifo:
        if not in_period(r) or not in_date_range(r):
            continue
        if store and store!="Compañía" and r.get("store")!=store:
            continue
        if u.get("role")=="tienda" and u.get("store") and r.get("store")!=u.get("store"):
            continue
        if project_only and r.get("store") not in set(project_store_names(True)):
            continue
        conv_detail.append(r)

    # Operación por tienda: los ingresos operativos son exclusivamente las piezas de Recolección de muertos.
    # Dev Pzs se conserva aparte para Conversión/Recuperación; nunca se vuelve a sumar como ingreso operativo.
    store_map={s:{
        "store":s,"dev_pzs":0.0,"muertos":0.0,"cajas":0.0,"probador":0.0,
        "sistema_devoluciones":0.0,"sin_clasificar":0.0,
        "recolectadas":0.0,"acondicionado":0.0,"ubicado":0.0,
        "recorridos":0.0,"records":0,"productividad_piezas":0.0
    } for s in allowed_stores if s}

    for r in op:
        s=r.get("store") or "Sin tienda"
        if s not in store_map:
            if store=="Compañía" and s:
                store_map[s]={"store":s,"dev_pzs":0.0,"muertos":0.0,"cajas":0.0,"probador":0.0,
                    "sistema_devoluciones":0.0,"sin_clasificar":0.0,"recolectadas":0.0,
                    "acondicionado":0.0,"ubicado":0.0,"recorridos":0.0,"records":0,"productividad_piezas":0.0}
            else:
                continue
        d=store_map[s]; d["records"]+=1
        for key in ("muertos","cajas","probador","sistema_devoluciones","sin_clasificar","recolectadas","acondicionado","ubicado"):
            d[key]+=float(r.get(key) or 0)
        d["recorridos"]+=float(r.get("recorridos") or 0)
        if float(r.get("recolectadas") or 0)>0 or float(r.get("acondicionado") or 0)>0 or float(r.get("ubicado") or 0)>0:
            d["productividad_piezas"]+=float(r.get("pieces") or 0)

    for r in co:
        s=r.get("store") or ""
        if s in store_map: store_map[s]["dev_pzs"]+=float(r.get("dev_pzs") or 0)

    project_set=set(project_store_names(True))
    stores=[]
    for d in store_map.values():
        d["ingresos"]=d["recolectadas"]
        d["pendiente_acondicionar"]=max(d["ingresos"]-d["acondicionado"],0)
        d["pendiente_ubicar"]=max(d["acondicionado"]-d["ubicado"],0)
        d["is_project"]=d["store"] in project_set
        d["pct_acondicionado"]=d["acondicionado"]/d["ingresos"]*100 if d["ingresos"] else 0.0
        d["pct_ubicado"]=d["ubicado"]/d["acondicionado"]*100 if d["acondicionado"] else 0.0
        d["pct_ubicado_acondicionado"]=d["pct_ubicado"]
        stores.append(d)
    stores.sort(key=lambda x:(-x["ingresos"],x["store"]))

    def sum_store(key):
        return float(sum(float(s.get(key) or 0) for s in stores))

    metrics={
        "dev_pzs":sum_store("dev_pzs"),
        "cambios":sum_store("dev_pzs"),
        "muertos":sum_store("muertos"),
        "cajas":sum_store("cajas"),
        "probador":sum_store("probador"),
        "sistema_devoluciones":sum_store("sistema_devoluciones"),
        "sin_clasificar":sum_store("sin_clasificar"),
        "recolectadas":sum_store("recolectadas"),
        "ingresos":sum_store("ingresos"),
        "acondicionado":sum_store("acondicionado"),
        "ubicado":sum_store("ubicado"),
        "recorridos":sum_store("recorridos"),
        "pendiente_acondicionar":sum_store("pendiente_acondicionar"),
        "pendiente_ubicar":sum_store("pendiente_ubicar"),
        "productividad_piezas":sum_store("productividad_piezas"),
    }
    metrics["pct_acondicionado"]=metrics["acondicionado"]/metrics["ingresos"]*100 if metrics["ingresos"] else 0.0
    metrics["pct_ubicado"]=metrics["ubicado"]/metrics["acondicionado"]*100 if metrics["acondicionado"] else 0.0
    metrics["pct_ubicado_acondicionado"]=metrics["pct_ubicado"]
    metrics["pct_procesado"]=(metrics["ingresos"]-metrics["pendiente_ubicar"])/metrics["ingresos"]*100 if metrics["ingresos"] else 0.0

    # Conversión / recuperación consolidadas.
    metrics["converted_pieces"]=sum(x["converted_pieces"] for x in conv_detail)
    metrics["conversion_pct"]=metrics["converted_pieces"]/metrics["dev_pzs"]*100 if metrics["dev_pzs"] else 0.0
    metrics["return_value"]=sum(x["return_value"] for x in conv_detail)
    metrics["recovered_value"]=sum(x["recovered_value"] for x in conv_detail)
    metrics["recovery_pct"]=metrics["recovered_value"]/metrics["return_value"]*100 if metrics["return_value"] else 0.0
    metrics["pending_recovery_pieces"]=max(metrics["dev_pzs"]-metrics["converted_pieces"],0)
    metrics["pending_recovery_value"]=max(metrics["return_value"]-metrics["recovered_value"],0)

    # Recorridos: suma explícita de la columna RECORRIDOS del Excel.
    # Meta semanal = configuración recorridos_semanales (47 por defecto).
    # Para día o semana parcial, sumar las metas diarias editables según fecha real.
    weekday_goal_keys={0:"recorridos_lunes",1:"recorridos_martes",2:"recorridos_miercoles",3:"recorridos_jueves",
                       4:"recorridos_viernes",5:"recorridos_sabado",6:"recorridos_domingo"}
    def daily_goal_for(ts):
        return float(goals.get(weekday_goal_keys[ts.weekday()],0) or 0)

    selected_dates=[]
    try:
        if period_type=="day" and period_value:
            selected_dates=[pd.Timestamp(period_value)]
        elif period_type=="week" and period_value:
            y,w=period_value.split("-W",1)
            week_start=pd.Timestamp.fromisocalendar(int(y),int(w),1)
            full=[week_start+pd.Timedelta(days=i) for i in range(7)]
            selected_dates=[d for d in full if (not start_date or d.date().isoformat()>=start_date) and (not end_date or d.date().isoformat()<=end_date)]
        elif period_type=="month" and period_value:
            per=pd.Period(period_value,freq="M")
            selected_dates=list(pd.date_range(per.start_time.normalize(),per.end_time.normalize(),freq="D"))
            selected_dates=[d for d in selected_dates if (not start_date or d.date().isoformat()>=start_date) and (not end_date or d.date().isoformat()<=end_date)]
        else:
            selected_dates=[pd.Timestamp(d) for d in sorted({r.get("date") for r in op if r.get("date")})]
    except Exception:
        selected_dates=[]

    full_week=(period_type=="week" and period_value and not start_date and not end_date)
    if full_week:
        meta_per_store=float(goals.get("recorridos_semanales",47) or 0)
    else:
        meta_per_store=sum(daily_goal_for(d) for d in selected_dates)
    metrics["meta_recorridos"]=meta_per_store*len([s for s in allowed_stores if s])
    metrics["pct_recorridos"]=metrics["recorridos"]/metrics["meta_recorridos"]*100 if metrics["meta_recorridos"] else 0.0
    metrics["faltante_recorridos"]=max(metrics["meta_recorridos"]-metrics["recorridos"],0)

    # Productividad por colaborador.
    people={}
    for r in op:
        act=normalize_col(r.get("activity","")); reason=normalize_col(r.get("reason",""))
        productive=("acondicion" in act or "habilit" in act or "ubic" in act or
                    "recoleccion" in act or "caja" in reason or "probador" in reason)
        if not productive:
            continue
        name=str(r.get("name") or "").strip()
        if not name or normalize_col(name) in ("nan","none","sin dato"):
            continue
        p=people.setdefault((name,r.get("store") or ""),{"name":name,"store":r.get("store") or "",
                          "pieces":0.0,"days":set(),"records":0})
        p["pieces"]+=float(r.get("pieces") or 0); p["records"]+=1
        if r.get("date"): p["days"].add(r.get("date"))
    productivity=[]
    for p in people.values():
        workdays=max(len(p["days"]),1)
        target=float(goals.get("productividad_diaria",784))*workdays
        productivity.append({
            "name":p["name"],"store":p["store"],"pieces":p["pieces"],"days":workdays,
            "target":target,"daily":p["pieces"]/workdays if workdays else 0,
            "pct":p["pieces"]/target*100 if target else 0,
            "difference":p["pieces"]-target,"missing":max(target-p["pieces"],0)
        })
    productivity.sort(key=lambda x:(-x["pct"],-x["pieces"]))

    metrics["productivity_days"]=sum(x["days"] for x in productivity)
    metrics["productivity_daily"]=(
        sum(x["pieces"] for x in productivity)/metrics["productivity_days"]
        if metrics["productivity_days"] else 0.0
    )
    metrics["productivity_pct"]=metrics["productivity_daily"]/float(goals.get("productividad_diaria",784))*100 if goals.get("productividad_diaria") else 0.0

    # Score according to mature project V25.
    pending_control=(1-metrics["pendiente_ubicar"]/metrics["ingresos"])*100 if metrics["ingresos"] else 0.0
    score=(
        min(max(metrics["conversion_pct"],0),100)*0.40 +
        min(max(metrics["productivity_pct"],0),100)*0.40 +
        min(max(metrics["pct_recorridos"],0),100)*0.20
    )
    metrics["score_integral"]=max(0,min(score,100))

    # Recovery macro por tienda.
    recovery_by_store=[]
    for s in allowed_stores:
        det=[x for x in conv_detail if x["store"]==s]
        dev=sum(x["dev_pzs"] for x in det)
        conv=sum(x["converted_pieces"] for x in det)
        val=sum(x["return_value"] for x in det)
        rec=sum(x["recovered_value"] for x in det)
        recovery_by_store.append({
            "store":s,"is_project":s in project_set,"dev_pzs":dev,"converted_pieces":conv,
            "conversion_pct":conv/dev*100 if dev else 0.0,
            "return_value":val,"recovered_value":rec,
            "recovery_pct":rec/val*100 if val else 0.0,
            "pending_pieces":max(dev-conv,0),"pending_value":max(val-rec,0)
        })
    # Ranking ejecutivo: mayor % de conversión = posición 1.
    recovery_by_store.sort(key=lambda x:(-x["conversion_pct"],-x["recovery_pct"],x["store"]))

    # Score por tienda para lectura ejecutiva. Conserva ponderación 40/40/20.
    recovery_lookup={x["store"]:x for x in recovery_by_store}
    prod_lookup={}
    for p in productivity:
        d=prod_lookup.setdefault(p.get("store") or "",{"pieces":0.0,"days":0.0})
        d["pieces"]+=float(p.get("pieces") or 0); d["days"]+=float(p.get("days") or 0)
    score_by_store=[]
    for s in stores:
        st=s.get("store") or ""
        rr=recovery_lookup.get(st,{})
        pp=prod_lookup.get(st,{"pieces":0.0,"days":0.0})
        prod_daily=pp["pieces"]/pp["days"] if pp["days"] else 0.0
        prod_pct=prod_daily/float(goals.get("productividad_diaria",784))*100 if goals.get("productividad_diaria") else 0.0
        route_pct=float(s.get("recorridos") or 0)/meta_per_store*100 if meta_per_store else 0.0
        conv_pct=float(rr.get("conversion_pct") or 0)
        total=min(max(conv_pct,0),100)*0.40+min(max(prod_pct,0),100)*0.40+min(max(route_pct,0),100)*0.20
        score_by_store.append({
            "store":st,"is_project":bool(s.get("is_project")),"conversion_pct":conv_pct,
            "productivity_pct":prod_pct,"recorridos_pct":route_pct,"score":max(0,min(total,100))
        })
    score_by_store.sort(key=lambda x:(-x["score"],x["store"]))

    # Detalle por actividad solicitado: tienda + actividad + área.
    activity_map={}
    for r in op:
        key=(r.get("store") or "",r.get("activity") or r.get("activity_original") or "Sin actividad",r.get("area") or "Sin área")
        a=activity_map.setdefault(key,{"store":key[0],"activity":key[1],"area":key[2],"pieces":0.0,
                                   "occurrences":set(),"collaborators":set(),"hours_used":0.0,"valid_time_rows":0})
        a["pieces"]+=float(r.get("pieces") or 0)
        occ=str(r.get("occurrence") or "")
        if occ: a["occurrences"].add(occ)
        nm=str(r.get("name") or "").strip()
        if nm and normalize_col(nm) not in ("nan","none","sin dato"): a["collaborators"].add(nm)
        hv=r.get("hours_used")
        if hv is not None:
            try:
                a["hours_used"]+=float(hv); a["valid_time_rows"]+=1
            except Exception: pass
    activity_detail=[]
    for a in activity_map.values():
        activity_detail.append({"store":a["store"],"activity":a["activity"],"area":a["area"],"pieces":a["pieces"],
            "occurrences":len(a["occurrences"]),"collaborators":len(a["collaborators"]),
            "collaborator_names":sorted(a["collaborators"]),"hours_used":a["hours_used"] if a["valid_time_rows"] else None})
    activity_detail.sort(key=lambda x:(x["store"],x["activity"],x["area"]))


    # Recorridos y recolecciones por día/hora para detectar picos operativos.
    daily_peak={}; hourly_peak={}
    for r in op:
        date=str(r.get("date") or "")
        if date:
            d=daily_peak.setdefault(date,{"date":date,"recorridos":0.0,"muertos":0.0,"cajas":0.0,"probador":0.0,"recolectadas":0.0})
            d["recorridos"]+=float(r.get("recorridos") or 0)
            for k in ("muertos","cajas","probador","recolectadas"):
                d[k]+=float(r.get(k) or 0)
        if float(r.get("recolectadas") or 0)>0:
            mins=_time_to_minutes(r.get("start_time"))
            if mins is not None:
                hour=int(mins//60)%24
                h=hourly_peak.setdefault(hour,{"hour":hour,"muertos":0.0,"cajas":0.0,"probador":0.0,"recolectadas":0.0})
                for k in ("muertos","cajas","probador","recolectadas"):
                    h[k]+=float(r.get(k) or 0)
    daily_peaks=sorted(daily_peak.values(),key=lambda x:x["date"])
    hourly_peaks=[hourly_peak.get(h,{"hour":h,"muertos":0.0,"cajas":0.0,"probador":0.0,"recolectadas":0.0}) for h in range(24)]

    # Previous period deltas for weekly reports.
    previous={}
    if period_type=="week" and period_value:
        try:
            y,w=period_value.split("-W",1)
            start=pd.Timestamp.fromisocalendar(int(y),int(w),1)
            prev_start=start-pd.Timedelta(days=7)
            previous={"week":f"{prev_start.isocalendar().year}-W{prev_start.isocalendar().week:02d}"}
        except Exception:
            previous={}

    result = {
        "available":bool(data.get("rows") or data.get("commercial_daily")),
        "filtered_available":bool(op or co),
        "uploaded_at":data.get("uploaded_at"),
        "source_file":data.get("source_file",""),
        "operational_sheet":data.get("operational_sheet",""),
        "operational_sheets":data.get("operational_sheets",[data.get("operational_sheet","")]),
        "monthly_sheets":data.get("monthly_sheets",[]),
        "parse_errors":data.get("errors",[]),"rejected_rows":data.get("rejected_rows",[])[:200],
        "data_issues":data.get("data_issues",[])[:200],"duplicate_rows_removed":data.get("duplicate_rows_removed",0),
        "missing_columns_by_sheet":data.get("missing_columns_by_sheet",{}),
        "period_type":period_type,"period_value":period_value,"area":area,"activity":activity,"start_date":start_date,"end_date":end_date,
        "available_dates":all_dates,"available_weeks":all_weeks,"available_months":all_months,
        "areas_available":sorted({str(r.get("area") or "") for r in op_all if str(r.get("area") or "").strip()}),
        "activities_available":sorted({str(r.get("activity") or "") for r in op_all if str(r.get("activity") or "").strip()}),
        "stores_available":allowed_stores,
        # En modo compacto no se envían las filas operativas crudas.
        # Esto reduce drásticamente el JSON y evita congelamientos del navegador.
        "rows":[] if compact else op[:20000],"metrics":metrics,"stores":stores,
        "productivity":productivity[:300],
        "activity_detail":activity_detail[:1000],
        "recovery_by_store":recovery_by_store,
        "score_by_store":score_by_store,
        "daily_peaks":daily_peaks,"hourly_peaks":hourly_peaks,
        "conversion_detail":conv_detail[:200] if compact else conv_detail[:500],
        "goals":goals,"previous":previous,
        "project_stores":project_store_names(True),
    }
    if compact:
        # Mantener un número pequeño de variantes para no crecer indefinidamente.
        if len(_OPS_RESPONSE_CACHE) > 32:
            _OPS_RESPONSE_CACHE.clear()
        _OPS_RESPONSE_CACHE[cache_key]=result
    return result



def _report_export_payload(data: dict, report: str):
    metrics=data.get("metrics",{})
    active_project=set(project_store_names(True)); stores=[x for x in data.get("stores",[]) if x.get("store") in active_project]
    recovery=[x for x in data.get("recovery_by_store",[]) if x.get("store") in active_project]
    productivity=data.get("productivity",[])

    summary=[
        ("Reporte", report),
        ("Periodo", data.get("period_value") or "Histórico"),
        ("Piezas ingresadas", metrics.get("ingresos",0)),
        ("Conversión %", metrics.get("conversion_pct",0)),
        ("Recuperación %", metrics.get("recovery_pct",0)),
        ("Productividad %", metrics.get("productivity_pct",0)),
        ("Recorridos %", metrics.get("pct_recorridos",0)),
        ("Score Integral", metrics.get("score_integral",0)),
    ]
    return summary, stores, recovery, productivity


def _build_operations_pdf(data: dict, report: str, scope: str="Compañía") -> bytes:
    """PDF visual V40: replica jerarquía, colores, KPIs, tablas y gráficas del portal."""
    bio=BytesIO(); c=pdfcanvas.Canvas(bio,pagesize=landscape(letter))
    width,height=landscape(letter); M=26; BLUE="#173B73"; BLUE2="#246FE5"; PINK="#EC007C"; PURPLE="#7C3AED"; GREEN="#10B981"; ORANGE="#F59E0B"; BG="#F3F6FA"; LINE="#D7E0EA"; TXT="#102A56"
    y=height-M

    def safe(v):
        if v is None: return "—"
        if isinstance(v,float) and (math.isnan(v) or math.isinf(v)): return "—"
        return str(v)
    def n(v): return f"{float(v or 0):,.0f}"
    def pc(v): return f"{float(v or 0):.1f}%"
    def money(v): return f"${float(v or 0):,.0f}"
    def page_header(suffix=""):
        nonlocal y
        c.setFillColor(colors.HexColor(BG)); c.rect(0,0,width,height,fill=1,stroke=0)
        c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M,height-92,width-2*M,62,12,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",18); c.drawString(M+18,height-58,"Cambios y Muertos")
        c.setFont("Helvetica",8.5); c.drawString(M+18,height-75,"Recuperación, conversión, recolección y seguimiento operativo")
        c.setFont("Helvetica-Bold",10); c.drawRightString(width-M-18,height-56,"Operaciones Ropa · Price Shoes")
        c.setFont("Helvetica",7.5); c.drawRightString(width-M-18,height-72,f"{report}{(' · '+suffix) if suffix else ''}")
        y=height-108
    def new_page(suffix=""):
        nonlocal y
        c.showPage(); page_header(suffix)
    def ensure(h):
        nonlocal y
        if y-h < 30: new_page()
    def section(title):
        nonlocal y
        ensure(24); c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold",12); c.drawString(M,y,title); y-=18
    def kpis(items):
        nonlocal y
        cols=min(5,max(1,len(items))); gap=8; cardw=(width-2*M-gap*(cols-1))/cols; cardh=61
        rows=(len(items)+cols-1)//cols
        ensure(rows*(cardh+gap)+8)
        for idx,(label,value,sub,tone) in enumerate(items):
            r=idx//cols; col=idx%cols; x=M+col*(cardw+gap); yy=y-r*(cardh+gap)-cardh
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x,yy,cardw,cardh,8,fill=1,stroke=1)
            c.setFillColor(colors.HexColor(tone)); c.roundRect(x,yy,4,cardh,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor("#5D6B82")); c.setFont("Helvetica-Bold",6.5); c.drawString(x+12,yy+44,label.upper()[:26])
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold",16); c.drawString(x+12,yy+23,safe(value)[:18])
            c.setFillColor(colors.HexColor("#6B778C")); c.setFont("Helvetica",6.2); c.drawString(x+12,yy+9,safe(sub)[:38])
        y-=rows*(cardh+gap)+4
    def table(headers,rows,width_fracs=None,title=None,row_h=14,font=6.2):
        nonlocal y
        if title: section(title)
        if not rows:
            ensure(26); c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(M,y-20,width-2*M,22,6,fill=1,stroke=1); c.setFillColor(colors.HexColor("#6B778C")); c.setFont("Helvetica",7); c.drawString(M+10,y-12,"Información no disponible"); y-=30; return
        if width_fracs is None: width_fracs=[1/len(headers)]*len(headers)
        total=width-2*M; xs=[M]
        acc=M
        for f in width_fracs[:-1]: acc+=total*f; xs.append(acc)
        def head():
            nonlocal y
            ensure(24); c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M,y-14,total,18,4,fill=1,stroke=0); c.setFillColor(colors.white); c.setFont("Helvetica-Bold",font)
            for i,h in enumerate(headers): c.drawString(xs[i]+3,y-8,safe(h)[:25])
            y-=20
        head()
        for ridx,row in enumerate(rows):
            if y-row_h < 30: new_page(title or ""); head()
            c.setFillColor(colors.white if ridx%2==0 else colors.HexColor("#EEF4FB")); c.rect(M,y-row_h+2,total,row_h,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",font)
            for i,val in enumerate(row): c.drawString(xs[i]+3,y-8,safe(val)[:27])
            y-=row_h
        y-=7
    def horizontal_chart(title,rows,series):
        nonlocal y
        if not rows: return
        h=max(150,min(310,42+len(rows)*17)); ensure(h+24); section(title)
        x0=M+105; x1=width-M-18; maxv=max([float(r.get(key) or 0) for r in rows for key,_,_ in series]+[1]); chart_h=h-25
        for i,r in enumerate(rows):
            yy=y-8-i*17; c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",6.3); c.drawRightString(x0-7,yy,safe(r.get("store") or r.get("label") or r.get("date") or r.get("hour")))
            sh=6; base=yy-4
            for j,(key,color,label) in enumerate(series):
                v=float(r.get(key) or 0); bw=(x1-x0)*v/maxv
                c.setFillColor(colors.HexColor(color)); c.roundRect(x0,base-j*7,max(1,bw),5,2,fill=1,stroke=0)
                if bw>28: c.setFillColor(colors.white); c.setFont("Helvetica-Bold",5.5); c.drawRightString(x0+bw-2,base-j*7+1,n(v))
        ly=y+5
        xx=x0
        for _,color,label in series:
            c.setFillColor(colors.HexColor(color)); c.rect(xx,ly,8,5,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",6); c.drawString(xx+11,ly-1,label); xx+=95
        y-=h
    def mixed_chart(title,rows):
        nonlocal y
        if not rows: return
        h=245; ensure(h+24); section(title)
        vals=[float(r.get(k) or 0) for r in rows for k in ("recolectadas","acondicionado","ubicado")]; maxv=max(vals+[1]); x0=M+45; x1=width-M-15; base=y-h+38; top=y-18; plot_h=top-base; groupw=(x1-x0)/max(1,len(rows)); barw=min(12,groupw*.24)
        c.setStrokeColor(colors.HexColor(LINE));
        for q in range(5):
            gy=base+plot_h*q/4; c.line(x0,gy,x1,gy); c.setFillColor(colors.HexColor("#6B778C")); c.setFont("Helvetica",5.5); c.drawRightString(x0-5,gy-2,n(maxv*q/4))
        pts=[]
        for i,r in enumerate(rows):
            cx=x0+groupw*(i+.5); a=float(r.get("acondicionado") or 0); u=float(r.get("ubicado") or 0); inp=float(r.get("recolectadas") or 0)
            for v,off,col in ((a,-barw*.6,BLUE),(u,barw*.6,PINK)):
                bh=plot_h*v/maxv; c.setFillColor(colors.HexColor(col)); c.rect(cx+off-barw/2,base,barw,bh,fill=1,stroke=0); c.setFont("Helvetica-Bold",5.2); c.drawCentredString(cx+off,base+bh+3,n(v))
            py=base+plot_h*inp/maxv; pts.append((cx,py,inp)); c.setFillColor(colors.HexColor(BLUE2)); c.circle(cx,py,2.4,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica",5.3); c.saveState(); c.translate(cx-2,base-8); c.rotate(35); c.drawString(0,0,safe(r.get("store"))[:13]); c.restoreState()
        if len(pts)>1:
            c.setStrokeColor(colors.HexColor(BLUE2)); c.setLineWidth(1.4)
            for a,b in zip(pts,pts[1:]): c.line(a[0],a[1],b[0],b[1])
        for cx,py,v in pts:
            c.setFillColor(colors.HexColor(BLUE2)); c.setFont("Helvetica-Bold",5.2); c.drawCentredString(cx,py+5,n(v))
        # legend
        lx=x0; c.setFont("Helvetica",6); c.setFillColor(colors.HexColor(BLUE)); c.rect(lx,y-3,8,6,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.drawString(lx+11,y-2,"Acondicionado")
        lx+=100; c.setFillColor(colors.HexColor(PINK)); c.rect(lx,y-3,8,6,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.drawString(lx+11,y-2,"Ubicado")
        lx+=70; c.setStrokeColor(colors.HexColor(BLUE2)); c.line(lx,y,lx+10,y); c.setFillColor(colors.HexColor(BLUE2)); c.circle(lx+5,y,2,fill=1,stroke=0); c.setFillColor(colors.HexColor(TXT)); c.drawString(lx+14,y-2,"Ingresos")
        y-=h

    page_header()
    mt=data.get("metrics",{}); stores=data.get("stores",[]); rec=data.get("recovery_by_store",[]); prod=data.get("productivity",[])
    period=data.get("period_value") or "Histórico"
    c.setFillColor(colors.HexColor("#6B778C")); c.setFont("Helvetica",7.2); c.drawString(M,y,f"Periodo: {period}   ·   Alcance: {scope}"); y-=14

    base_kpis=[
        ("Piezas recolectadas",n(mt.get("ingresos")),"Muertos + Cajas + Probador",BLUE2),
        ("Acondicionado",n(mt.get("acondicionado")),pc(mt.get("pct_acondicionado")),PURPLE),
        ("Ubicado",n(mt.get("ubicado")),pc(mt.get("pct_ubicado")),PINK),
        ("Conversión",pc(mt.get("conversion_pct")),f"{n(mt.get('converted_pieces'))} piezas",GREEN),
        ("Recorridos",n(mt.get("recorridos")),pc(mt.get("pct_recorridos")),ORANGE),
    ]
    if "Productividad" in report:
        base_kpis=[("Piezas procesadas",n(mt.get("productividad_piezas")),"Actividades productivas",BLUE2),("Productividad",n(mt.get("productivity_daily")),"Piezas / colaborador-día",ORANGE),("Cumplimiento",pc(mt.get("productivity_pct")),"Meta diaria configurada",GREEN)]
    elif "Recorridos" in report:
        base_kpis=[("Meta consolidada",n(mt.get("meta_recorridos")),"Meta proporcional al periodo",BLUE2),("Realizados",n(mt.get("recorridos")),"Columna RECORRIDOS del Excel",PURPLE),("Cumplimiento",pc(mt.get("pct_recorridos")),"Realizados / meta",GREEN),("Faltante",n(mt.get("faltante_recorridos")),"Meta - realizados",PINK)]
    kpis(base_kpis)

    ordered_rec=sorted(rec,key=lambda r:(-float(r.get("conversion_pct") or 0),str(r.get("store") or "")))
    ordered_stores=sorted(stores,key=lambda r:(-next((float(x.get("conversion_pct") or 0) for x in ordered_rec if x.get("store")==r.get("store")),0),str(r.get("store") or "")))
    if "Productividad" in report:
        top=prod[:3]; opp=sorted(prod,key=lambda x:(x.get("pct") or 0))[:3]
        horizontal_chart("Top 3 por cumplimiento",[{"label":x.get("name"),"pct":x.get("pct")} for x in top],[("pct",BLUE2,"Cumplimiento %")])
        rows=[[i+1,x.get("name"),x.get("store"),n(x.get("pieces")),n(x.get("days")),n(x.get("daily")),pc(x.get("pct")),n(x.get("missing"))] for i,x in enumerate(prod[:60])]
        table(["#","Colaborador","Tienda","Piezas","Días","Prod. diaria","Cumpl.","Faltante"],rows,[.05,.20,.14,.11,.07,.12,.12,.13],"Ranking completo")
    elif "Recorridos" in report:
        daily=data.get("daily_peaks",[])
        horizontal_chart("Recorridos por día",[{"label":r.get("date"),"recorridos":r.get("recorridos")} for r in daily],[("recorridos",BLUE2,"Recorridos")])
        horizontal_chart("Recolecciones por día",daily,[("muertos",PINK,"Muertos"),("cajas",PURPLE,"Cajas"),("probador",ORANGE,"Probador")])
        hourly=[dict(r,label=f"{int(r.get('hour') or 0):02d}:00") for r in data.get("hourly_peaks",[]) if float(r.get("recolectadas") or 0)>0]
        horizontal_chart("Recolecciones por hora",hourly,[("muertos",PINK,"Muertos"),("cajas",PURPLE,"Cajas"),("probador",ORANGE,"Probador")])
    else:
        rec_rows=[[i+1,r.get("store"),n(r.get("dev_pzs")),n(r.get("converted_pieces")),pc(r.get("conversion_pct")),money(r.get("return_value")),money(r.get("recovered_value")),pc(r.get("recovery_pct"))] for i,r in enumerate(ordered_rec,1)]
        table(["#","Tienda","Dev","Recup.","Conv.","Valor Dev.","Recup. $","Recup. %"],rec_rows,[.05,.16,.09,.09,.09,.15,.15,.12],"Recuperación por tienda")
        horizontal_chart("Devolución y recuperación",ordered_rec,[("dev_pzs",BLUE,"Dev Pzs"),("converted_pieces",PINK,"Recup. Pzs")])
        op_rows=[[i+1,r.get("store"),n(r.get("muertos")),n(r.get("probador")),n(r.get("cajas")),n(r.get("recolectadas")),n(r.get("recorridos")),n(r.get("acondicionado")),n(r.get("ubicado")),n(r.get("pendiente_acondicionar")),n(r.get("pendiente_ubicar"))] for i,r in enumerate(ordered_stores,1)]
        table(["#","Tienda","Muertos","Probador","Cajas","Ingresos","Rec.","Acond.","Ubicado","Pend.Acond","Pend.Ubicar"],op_rows,[.04,.14,.08,.08,.07,.09,.07,.09,.09,.11,.11],"Detalle operativo")
        mixed_chart(f"Ingreso vs Acondicionado vs Ubicado · {period}",ordered_stores)

    c.save(); data_pdf=bio.getvalue()
    if not data_pdf.startswith(b"%PDF"):
        raise RuntimeError("El generador no produjo un PDF válido")
    return data_pdf

@app.get("/api/export/operations")
def export_operations(
    request: Request,
    format: str="xlsx",
    report: str="Reporte",
    store: str="Compañía",
    period_type: str="all",
    period_value: str="",
    area: str="",
    activity: str="",
    start_date: str="",
    end_date: str="",
    project_only: bool=False,
):
    require_user(request)
    data=operations(request,store=store,period_type=period_type,period_value=period_value,area=area,activity=activity,start_date=start_date,end_date=end_date,compact=True,project_only=project_only)
    summary,stores,recovery,productivity=_report_export_payload(data,report)
    safe=re.sub(r"[^A-Za-z0-9_-]+","_",report).strip("_").lower() or "reporte"

    if format.lower()=="xlsx":
        bio=io.BytesIO()
        with pd.ExcelWriter(bio,engine="openpyxl") as writer:
            pd.DataFrame(summary,columns=["Indicador","Valor"]).to_excel(writer,sheet_name="Resumen",index=False)
            pd.DataFrame(stores).to_excel(writer,sheet_name="Detalle Operativo",index=False)
            pd.DataFrame(recovery).to_excel(writer,sheet_name="Conversion Recuperacion",index=False)
            pd.DataFrame(productivity).to_excel(writer,sheet_name="Productividad",index=False)
        bio.seek(0)
        headers={"Content-Disposition":f'attachment; filename="{safe}.xlsx"'}
        return Response(content=bio.getvalue(),media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers=headers)

    if format.lower()=="pdf":
        try:
            pdf_bytes=_build_operations_pdf(data,report,scope=store)
            return Response(content=pdf_bytes,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{safe}.pdf"'})
        except Exception as exc:
            raise HTTPException(500,f"No fue posible generar PDF: {type(exc).__name__}: {exc}")

    raise HTTPException(400,"Formato no soportado")

@app.get("/api/goals")
def goals_get(request: Request):
    u=require_user(request)
    return {
        "values":get_goals(),
        "labels":GOAL_LABELS,
        "history":get_goal_history(100),
        "editable":u["role"] in ("superadmin","admin"),
    }

@app.post("/api/goals")
async def goals_save(request: Request):
    u=require_user(request,("superadmin","admin"))
    body=await request.json()
    values=body.get("values") if isinstance(body,dict) else None
    if not isinstance(values,dict):
        raise HTTPException(400,"Formato de metas inválido")
    changed=update_goals(values,u["username"])
    return {
        "ok":True,
        "changed":changed,
        "values":get_goals(),
        "history":get_goal_history(100),
    }



@app.get("/api/stores")
def stores_get(request: Request, include_inactive: bool=False):
    u=require_user(request)
    rows=get_project_stores(active_only=not include_inactive)
    if u["role"] not in ("superadmin","admin"):
        rows=[r for r in rows if r["active"]]
    return {
        "stores":rows,
        "history":get_store_history(200) if u["role"] in ("superadmin","admin") else [],
        "editable":u["role"] in ("superadmin","admin"),
    }

@app.post("/api/stores")
async def stores_create(request: Request):
    u=require_user(request,("superadmin","admin"))
    body=await request.json()
    name=" ".join(str(body.get("name") or "").split()).strip()
    if len(name)<2:
        raise HTTPException(400,"Escribe un nombre de tienda válido")
    if _store_name_exists(name):
        raise HTTPException(409,"La tienda ya existe")
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        cur=con.execute(
            "INSERT INTO stores(name,active,project,created_at,updated_at,updated_by) VALUES(?,?,?,?,?,?)",
            (name,1,0,now,now,u["username"])
        )
        sid=cur.lastrowid
    save_store_change(u["username"],sid,"create","",name,None,1,None,0)
    return {"ok":True,"message":"Tienda agregada correctamente","store_id":sid}


@app.post("/api/stores/batch")
async def stores_batch_update(request: Request):
    """Guarda Activa / Proyecto de varias tiendas en una sola transacción estable."""
    u=require_user(request,("superadmin","admin"))
    body=await request.json()
    items=body.get("items") or []
    if not isinstance(items,list) or not items:
        raise HTTPException(400,"No hay cambios de tiendas para guardar")

    now=datetime.now().isoformat(timespec="seconds")
    changed=0
    with db() as con:
        for item in items:
            try:
                store_id=int(item.get("id"))
            except Exception:
                continue
            old=con.execute("SELECT * FROM stores WHERE id=?",(store_id,)).fetchone()
            if not old:
                continue
            active=1 if bool(item.get("active",bool(old["active"]))) else 0
            project=1 if bool(item.get("project",bool(old["project"]))) else 0
            # Una tienda marcada como Proyecto debe permanecer activa para
            # poder aparecer y resaltarse en los reportes.
            if project:
                active=1
            if int(active)==int(old["active"]) and int(project)==int(old["project"]):
                continue

            con.execute(
                "UPDATE stores SET active=?,project=?,updated_at=?,updated_by=? WHERE id=?",
                (active,project,now,u["username"],store_id)
            )
            # Guardar historial dentro de la MISMA conexión.
            con.execute(
                """INSERT INTO store_history(
                    store_id,action,old_name,new_name,old_active,new_active,
                    old_project,new_project,changed_at,changed_by
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    store_id,"update",old["name"],old["name"],
                    int(old["active"]),int(active),
                    int(old["project"]),int(project),
                    now,u["username"]
                )
            )
            changed+=1

    _OPS_RESPONSE_CACHE.clear()
    return {
        "ok":True,
        "message":"Selección Activa / Proyecto guardada correctamente",
        "changed":changed,
        "project_stores":project_store_names(True)
    }


@app.put("/api/stores/{store_id}")
async def stores_update(store_id: int, request: Request):
    u=require_user(request,("superadmin","admin"))
    body=await request.json()
    with db() as con:
        old=con.execute("SELECT * FROM stores WHERE id=?",(store_id,)).fetchone()
    if not old:
        raise HTTPException(404,"Tienda no encontrada")
    name=" ".join(str(body.get("name",old["name"]) or "").split()).strip()
    active=1 if bool(body.get("active",bool(old["active"]))) else 0
    project=1 if bool(body.get("project",bool(old["project"]))) else 0
    if project:
        active=1
    if len(name)<2:
        raise HTTPException(400,"Escribe un nombre de tienda válido")
    if _store_name_exists(name,store_id):
        raise HTTPException(409,"Ya existe otra tienda con ese nombre")
    now=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        con.execute(
            "UPDATE stores SET name=?,active=?,project=?,updated_at=?,updated_by=? WHERE id=?",
            (name,active,project,now,u["username"],store_id)
        )
        if name!=old["name"]:
            con.execute("UPDATE users SET store=? WHERE store=?",(name,old["name"]))
    if name!=old["name"] or int(active)!=int(old["active"]) or int(project)!=int(old["project"]):
        save_store_change(
            u["username"],store_id,"update",old["name"],name,int(old["active"]),int(active),int(old["project"]),int(project)
        )
    return {"ok":True,"message":"Tienda actualizada correctamente"}


@app.get("/api/share-info")
def share_info(request: Request):
    require_user(request,("superadmin","admin"))
    public_url=os.environ.get("OPERACIONES_ROPA_PUBLIC_URL","").strip()
    render_host=os.environ.get("RENDER_EXTERNAL_HOSTNAME","").strip()
    forwarded_host=str(request.headers.get("x-forwarded-host") or "").strip()
    forwarded_proto=str(request.headers.get("x-forwarded-proto") or "").strip()
    local_url=str(request.base_url).rstrip("/")
    if not public_url and render_host:
        public_url=f"https://{render_host}"
    elif not public_url and forwarded_host and forwarded_proto=="https":
        public_url=f"https://{forwarded_host}"
    parsed=urlparse(local_url)
    port=parsed.port or (443 if parsed.scheme=="https" else 80)
    try:
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8",80))
        lan_ip=sock.getsockname()[0]
        sock.close()
    except Exception:
        try:
            lan_ip=socket.gethostbyname(socket.gethostname())
        except Exception:
            lan_ip=""
    lan_url=f"http://{lan_ip}:{port}" if lan_ip else ""
    data=load_ops()
    best_url=public_url or lan_url or local_url
    return {
        "public_url":public_url,"local_url":local_url,"lan_url":lan_url,"best_url":best_url,
        "source_file":data.get("source_file",""),"updated_at":data.get("uploaded_at",""),
        "note":"La URL pública sólo existe cuando OPERACIONES_ROPA_PUBLIC_URL está configurada en el hosting."
    }

@app.get("/api/files")
def files_state(request: Request):
    require_user(request); return load_manifest()

@app.post("/api/upload/pdfs")
async def upload_pdfs(request: Request, files: List[UploadFile]=File(...), week: str=Form("")):
    require_user(request,("superadmin","admin")); results=[]
    for f in files:
        filename = f.filename or "reporte.pdf"
        data = await f.read()
        if not filename.lower().endswith(".pdf") or not data.startswith(b"%PDF"):
            results.append({"file": filename, "ok": False, "error": "Archivo PDF inválido"})
            continue
        adapter=UploadAdapter(data,filename); provisional_week=week or "pendiente"
        entry=save_pdf_upload(adapter,provisional_week); path=resolve_entry_path(entry)
        try:
            snap=extract_pdf_snapshot(path); final_week=snap.get("week") or week or provisional_week
            if week and week!=final_week: snap["week"]=week; final_week=week
            save_snapshot(entry["id"],snap); update_entry("pdfs",entry["id"],status=snap.get("status","Procesado"),
                store=snap.get("store",""),week=final_week,report_date=snap.get("report_date",""),pages=snap.get("pages",0),
                records=snap.get("models",0),parser_version=snap.get("parser_version",0))
            results.append({"file":filename,"ok":True,"store":snap.get("store"),"week":final_week,"status":snap.get("status","Procesado"),"duplicate":entry.get("duplicate",False)})
        except Exception as exc:
            update_entry("pdfs",entry["id"],status="Error",error=str(exc)); results.append({"file":filename,"ok":False,"error":str(exc)})
    return {"results":results}

@app.post("/api/upload/capacity")
async def upload_capacity(request: Request,file:UploadFile=File(...)):
    require_user(request,("superadmin","admin"))
    filename=file.filename or "capacidades.xlsx"
    if not filename.lower().endswith((".xlsx",".xls")):
        raise HTTPException(400,"Selecciona un archivo Excel .xlsx o .xls")
    data=await file.read()
    if not data:
        raise HTTPException(400,"El archivo está vacío")
    entry=save_capacity_upload(UploadAdapter(data,filename))
    path=resolve_entry_path(entry)

    # Si el mismo archivo ya fue procesado, reutiliza el cache y responde de inmediato.
    if entry.get("duplicate") and str(entry.get("status") or "").lower()=="procesado":
        cached=await asyncio.to_thread(_load_capacity_cache,entry)
        if not cached.empty:
            try:
                mtime=path.stat().st_mtime if path.exists() else None
                _CAPACITY_FRAME_CACHE.update({"path":str(path),"mtime":mtime,"frame":cached})
            except Exception:
                pass
            return {"ok":True,"file":filename,"rows":int(len(cached)),"stores":int(cached["Tienda"].nunique()) if "Tienda" in cached.columns else 0,"message":"Excel ya estaba procesado; se reutilizó el catálogo normalizado","cached":True}

    update_entry("capacities",entry["id"],status="Procesando",error="")
    try:
        # IMPORTANTE: el XLSX real supera 195 mil registros. Se procesa fuera del
        # hilo principal para que Uvicorn y las demás pestañas sigan respondiendo.
        df=await asyncio.to_thread(read_capacity_file,path)
        if df.empty:
            raise ValueError("El Excel se abrió pero no se identificaron filas de capacidades/existencias")

        cache_path=_capacity_cache_path(entry["id"])
        await asyncio.to_thread(df.to_pickle,cache_path)
        cache_rel=str(cache_path.relative_to(DATA_ROOT))
        mtime=path.stat().st_mtime if path.exists() else None
        _CAPACITY_FRAME_CACHE.update({"path":str(path),"mtime":mtime,"frame":df})
        stores=sorted(df["Tienda"].dropna().unique().tolist()) if "Tienda" in df.columns else []
        report_date=_capacity_report_date({**entry,"name":filename})
        iso=report_date.isocalendar(); report_week=f"{iso.year}-W{iso.week:02d}"; report_month=f"{report_date.year:04d}-{report_date.month:02d}"
        update_entry("capacities",entry["id"],status="Procesado",rows=int(len(df)),stores=stores,cache_file=cache_rel,error="",report_date=report_date.isoformat(),week=report_week,month=report_month,data_source="Excel capacidades")
        return {"ok":True,"file":filename,"rows":int(len(df)),"stores":int(df["Tienda"].nunique()) if "Tienda" in df.columns else 0,"message":"Excel procesado correctamente y catálogo optimizado para consultas rápidas","cached":False}
    except Exception as exc:
        update_entry("capacities",entry["id"],status="Error",error=str(exc))
        raise HTTPException(400,str(exc))

@app.post("/api/upload/sales-pdfs")
async def upload_sales_pdfs(
    request: Request,
    files: List[UploadFile] = File(...),
    year: int = Form(...),
    month: int = Form(...),
):
    require_user(request, ("superadmin","admin"))
    if year < 2020 or year > 2100 or month < 1 or month > 12:
        raise HTTPException(400, "Año o mes inválido")
    results = []
    for f in files:
        filename = f.filename or "ventas.pdf"
        if not filename.lower().endswith(".pdf"):
            results.append({"file": filename, "ok": False, "error": "La venta mensual debe cargarse en PDF"})
            continue
        data = await f.read()
        if not data.startswith(b"%PDF"):
            results.append({"file": filename, "ok": False, "error": "El archivo no parece ser un PDF válido"})
            continue
        entry = save_sales_upload(UploadAdapter(data, filename))
        path = resolve_entry_path(entry)
        try:
            summary = parse_sales_pdf(path, year, month)
            save_sales_pdf_snapshot(entry["id"], summary)
            update_entry(
                "sales", entry["id"], status=summary["status"], year=year, month=month,
                rows=summary["rows"], stores=summary["stores"], pages=summary["pages"],
                total_pieces=summary["total_pieces"], total_sales=summary["total_sales"],
            )
            results.append({"file": filename, "ok": True, "duplicate": entry.get("duplicate", False), **summary})
        except Exception as exc:
            update_entry("sales", entry["id"], status="Error", error=str(exc), year=year, month=month)
            results.append({"file": filename, "ok": False, "error": str(exc)})
    return {"results": results}

@app.post("/api/upload/sales")
async def upload_sales_legacy(request: Request):
    require_user(request, ("superadmin","admin"))
    raise HTTPException(400, "La carga de ventas cambió a PDF. Usa el módulo PDF · Ventas mensuales.")


@app.get("/api/upload/operations/current")
def upload_operations_current(request: Request):
    require_user(request,("superadmin","admin"))
    data=load_ops()
    if not data.get("source_file"):
        return {"available":False}
    return {
        "available":True,
        "file":data.get("source_file",""),
        "uploaded_at":data.get("uploaded_at",""),
        "uploaded_by":data.get("uploaded_by",""),
        "period":", ".join(data.get("months") or data.get("weeks") or []) or "Información no disponible",
        "operational_sheet":data.get("operational_sheet",""),
        "operational_sheets":data.get("operational_sheets",[data.get("operational_sheet","")]),
        "monthly_sheets":data.get("monthly_sheets",[]),
        "rows":len(data.get("rows") or []),
        "rejected_records":len(data.get("rejected_rows") or []),
        "duplicate_rows_removed":data.get("duplicate_rows_removed",0),
        "missing_columns_by_sheet":data.get("missing_columns_by_sheet",{}),
        "errors":data.get("errors",[]),
    }

@app.post("/api/upload/operations/preview")
async def upload_operations_preview(request: Request,file:UploadFile=File(...)):
    u=require_user(request,("superadmin","admin"))
    filename=file.filename or "archivo.xlsx"
    suffix=Path(filename).suffix.lower()
    if suffix != ".xlsx":
        raise HTTPException(400,"Carga un archivo Excel .xlsx")
    data=await file.read()
    if not data:
        raise HTTPException(400,"El archivo está vacío")
    token=secrets.token_urlsafe(18)
    stage_path=STAGING_DIR/f"{token}{suffix}"
    stage_path.write_bytes(data)
    try:
        payload=await asyncio.to_thread(lambda: parse_operations_excel(stage_path,persist=False))
    except Exception as exc:
        stage_path.unlink(missing_ok=True)
        raise HTTPException(400,f"No fue posible validar el archivo: {type(exc).__name__}: {exc}")

    required=["Ocurrencia","Tienda","Tabla","Actividad Realizada","Número de Piezas","Motivo de ingreso"]
    missing_msgs=[]
    for sheet,cols in (payload.get("op_columns_by_sheet") or {}).items():
        detected=set(cols or [])
        missing=[c for c in required if c not in detected]
        if "Fecha" not in detected and "Fecha s" not in detected:
            missing.append("Fecha o Fecha s")
        if missing:
            missing_msgs.append(f"{sheet}: "+", ".join(missing))
    if missing_msgs:
        stage_path.unlink(missing_ok=True)
        raise HTTPException(400,"Faltan columnas requeridas por hoja: " + " | ".join(missing_msgs))

    errors=list(payload.get("errors") or [])
    preview_rows=(payload.get("rows") or [])[:12]
    valid=len(payload.get("rows") or [])
    rejected_rows=payload.get("rejected_rows") or []
    rejected=len(rejected_rows)
    period=", ".join(payload.get("months") or payload.get("weeks") or []) or "Información no disponible"
    meta={
        "token":token,"filename":filename,"suffix":suffix,"user":u["username"],
        "valid_records":valid,"rejected_records":rejected,"errors":errors,"rejected_rows":payload.get("rejected_rows",[])[:100],
        "period":period,"operational_sheet":payload.get("operational_sheet",""),
        "operational_sheets":payload.get("operational_sheets",[]),
        "monthly_sheets":payload.get("monthly_sheets",[]),
        "duplicate_rows_removed":payload.get("duplicate_rows_removed",0),
        "data_issues":payload.get("data_issues",[])[:100],
        "missing_columns_by_sheet":payload.get("missing_columns_by_sheet",{}),
    }
    (STAGING_DIR/f"{token}.json").write_text(_safe_json_dump(meta),encoding="utf-8")
    (STAGING_DIR/f"{token}.payload.json").write_text(_safe_json_dump(payload),encoding="utf-8")
    return {
        "ok":True,"token":token,"file":filename,"period_detected":period,
        "operational_sheet":payload.get("operational_sheet",""),
        "operational_sheets":payload.get("operational_sheets",[]),
        "monthly_sheets":payload.get("monthly_sheets",[]),
        "duplicate_rows_removed":payload.get("duplicate_rows_removed",0),
        "data_issues":payload.get("data_issues",[])[:100],
        "missing_columns_by_sheet":payload.get("missing_columns_by_sheet",{}),
        "valid_records":valid,"rejected_records":rejected,
        "rejection_reason":"; ".join(errors + [f"Fila {x.get('row')}: {', '.join(x.get('errors',[]))}" for x in (payload.get("rejected_rows") or [])[:10]]) if (errors or payload.get("rejected_rows")) else "",
        "preview":preview_rows,
        "message":"Archivo validado. Revisa la vista previa y confirma para publicar."
    }

@app.post("/api/upload/operations/publish")
async def upload_operations_publish(request: Request):
    u=require_user(request,("superadmin","admin"))
    body=await request.json()
    token=str(body.get("token") or "")
    meta_file=STAGING_DIR/f"{token}.json"
    payload_file=STAGING_DIR/f"{token}.payload.json"
    if not meta_file.exists():
        raise HTTPException(404,"La vista previa expiró o no existe")
    meta=json.loads(meta_file.read_text(encoding="utf-8"))
    suffix=str(meta.get("suffix") or ".xlsx")
    stage_path=STAGING_DIR/f"{token}{suffix}"
    if not stage_path.exists():
        raise HTTPException(404,"El archivo temporal ya no existe")
    try:
        if not payload_file.exists():
            raise HTTPException(409,"La validación temporal ya no existe. Valida nuevamente el archivo.")
        payload=await asyncio.to_thread(lambda: json.loads(payload_file.read_text(encoding="utf-8")))
        final_path=DATA_ROOT/f"cambios_muertos_actual{suffix}"
        tmp_ops=DATA_ROOT/"operations_publish.tmp.json"
        payload["source_file"]=meta.get("filename") or final_path.name
        payload["uploaded_by"]=u["username"]
        payload["uploaded_at"]=datetime.now().isoformat(timespec="seconds")
        await asyncio.to_thread(tmp_ops.write_text, _safe_json_dump(payload), encoding="utf-8")
        await asyncio.to_thread(shutil.copy2, stage_path, final_path)
        await asyncio.to_thread(tmp_ops.replace, OPS_FILE)
        with db() as con:
            con.execute(
                "INSERT INTO upload_history(module,filename,uploaded_at,uploaded_by,period_detected,valid_records,rejected_records,rejection_reason,published) VALUES(?,?,?,?,?,?,?,?,1)",
                ("Cambios y Muertos",meta.get("filename",""),payload["uploaded_at"],u["username"],
                 meta.get("period",""),len(payload.get("rows") or []),int(meta.get("rejected_records") or 0),
                 "; ".join(meta.get("errors") or []))
            )
        stage_path.unlink(missing_ok=True)
        meta_file.unlink(missing_ok=True)
        payload_file.unlink(missing_ok=True)
        return {
            "ok":True,"message":"Información publicada correctamente",
            "file":payload["source_file"],"uploaded_at":payload["uploaded_at"],"uploaded_by":u["username"],
            "period_detected":meta.get("period",""),"valid_records":len(payload.get("rows") or []),
            "rejected_records":int(meta.get("rejected_records") or 0)
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500,f"No fue posible publicar el Excel: {type(exc).__name__}: {exc}")

@app.get("/api/upload/operations/history")
def upload_operations_history(request: Request):
    require_user(request,("superadmin","admin"))
    with db() as con:
        rows=con.execute(
            "SELECT id,module,filename,uploaded_at,uploaded_by,period_detected,valid_records,rejected_records,rejection_reason,published "
            "FROM upload_history WHERE module='Cambios y Muertos' ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return [dict(r) for r in rows]

# Compatibilidad: la ruta antigua ahora valida y publica en una sola llamada.
@app.post("/api/upload/operations")
async def upload_operations_legacy(request: Request,file:UploadFile=File(...)):
    """Carga operativa restaurada al flujo que funcionaba antes de V21."""
    u=require_user(request,("superadmin","admin"))
    filename=file.filename or "archivo.xlsx"
    suffix=Path(filename).suffix.lower()
    if suffix != ".xlsx":
        raise HTTPException(400,"Carga un archivo Excel .xlsx")
    data=await file.read()
    if not data:
        raise HTTPException(400,"El archivo está vacío")

    # Igual que el flujo estable anterior: staging simple, parseo directo y publicación.
    p=STAGING_DIR/f"legacy_{secrets.token_hex(8)}{suffix}"
    p.write_bytes(data)

    try:
        payload=parse_operations_excel(p,persist=True)
        payload["source_file"]=filename
        payload["uploaded_by"]=u["username"]
        payload["uploaded_at"]=datetime.now().isoformat(timespec="seconds")

        # Persistir metadatos y archivo fuente actual.
        final_path=DATA_ROOT/"cambios_muertos_actual.xlsx"
        shutil.copy2(p,final_path)
        OPS_FILE.write_text(_safe_json_dump(payload),encoding="utf-8")
        _clear_operations_caches(clear_meta_file=True)
        try:
            meta=_build_operations_meta(payload,_ops_source_stamp())
            OPS_META_CACHE_FILE.write_text(_safe_json_dump(meta),encoding="utf-8")
            _OPS_META_CACHE["stamp"]=_ops_source_stamp(); _OPS_META_CACHE["data"]=meta
        except Exception:
            pass

        try:
            with db() as con:
                con.execute(
                    "INSERT INTO upload_history(module,filename,uploaded_at,uploaded_by,period_detected,valid_records,rejected_records,rejection_reason,published) VALUES(?,?,?,?,?,?,?,?,1)",
                    (
                        "Cambios y Muertos",
                        filename,
                        payload["uploaded_at"],
                        u["username"],
                        ", ".join(payload.get("months") or payload.get("weeks") or []),
                        len(payload.get("rows") or []),
                        len(payload.get("rejected_rows") or []),
                        "; ".join(payload.get("errors") or []),
                    )
                )
        except Exception:
            pass

        return {
            "ok":True,
            "message":"Excel de Cambios y Muertos cargado correctamente",
            "file":filename,
            "rows":len(payload.get("rows") or []),
            "sheets":payload.get("sheets_used",[]),
            "weeks":payload.get("weeks",[]),
            "months":payload.get("months",[]),
            "operational_sheet":payload.get("operational_sheet",""),
            "operational_sheets":payload.get("operational_sheets",[]),
            "monthly_sheets":payload.get("monthly_sheets",[]),
            "rejected_records":len(payload.get("rejected_rows") or []),
            "duplicate_rows_removed":payload.get("duplicate_rows_removed",0),
            "data_issues":payload.get("data_issues",[])[:100],
            "missing_columns_by_sheet":payload.get("missing_columns_by_sheet",{}),
            "errors":payload.get("errors",[]),
            "uploaded_by":u["username"],
            "uploaded_at":payload["uploaded_at"],
        }
    except Exception as exc:
        raise HTTPException(400,f"No fue posible cargar el Excel operativo: {type(exc).__name__}: {exc}")
    finally:
        # La carga no debe fallar sólo porque Windows/antivirus conserve
        # el archivo de staging bloqueado unos milisegundos.
        try:
            p.unlink(missing_ok=True)
        except PermissionError:
            try:
                import gc, time
                gc.collect()
                time.sleep(0.35)
                p.unlink(missing_ok=True)
            except (PermissionError, FileNotFoundError):
                # El staging sobrante puede limpiarse en el siguiente arranque.
                # Nunca sobrescribir una respuesta de carga exitosa con WinError 32.
                pass

app.mount("/static",StaticFiles(directory=WEB),name="static")
