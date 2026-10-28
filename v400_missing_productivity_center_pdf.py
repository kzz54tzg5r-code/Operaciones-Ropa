"""V400 · Colaboradores activos sin registro de productividad, Centro y PDF.

Usa el padrón administrable V166 (no inventa empleados). Mismo periodo y
alcance Proyecto en web, XLSX y última sección del PDF. No modifica KPIs.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from collections import defaultdict
from io import BytesIO
import math
import re
import unicodedata
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import Response
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from pypdf import PdfReader, PdfWriter


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(text.encode("ascii", "ignore").decode().casefold().split())


def bounds(kind, value):
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    try:
        if kind == "day":
            d = date.fromisoformat(str(value)[:10]); return d, d
        if kind == "week":
            m = re.fullmatch(r"(\d{4})-W(\d{1,2})", str(value))
            if not m: raise ValueError("Semana ISO incorrecta")
            d = date.fromisocalendar(int(m[1]), int(m[2]), 1)
            return d, d + timedelta(days=6)
        if kind == "month":
            m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(value))
            if not m: raise ValueError("Mes incorrecto")
            y, mo = int(m[1]), int(m[2])
            d = date(y, mo, 1)
            next_month = date(y + (mo == 12), mo % 12 + 1, 1)
            return d, next_month - timedelta(days=1)
        if kind == "year":
            y = int(value); return date(y, 1, 1), date(y, 12, 31)
    except (TypeError, ValueError) as ex:
        raise HTTPException(400, "Periodo incorrecto") from ex
    return today, today


def is_productive(r):
    try:
        pieces = float(r.get("pieces") or 0)
    except (TypeError, ValueError):
        pieces = 0
    if not math.isfinite(pieces) or pieces <= 0:
        return False
    a = norm(r.get("activity") or r.get("activity_original"))
    reason = norm(r.get("reason"))
    return any(t in a for t in ("acondicion", "habilit", "ubic", "recoleccion")) or "caja" in reason or "probador" in reason


def build_missing(m, allowed_stores, period_type, period_value):
    """Filtrar por tienda AUTORIZADA ANTES de leer nombres; V166 active=1 es fuente."""
    first, last = bounds(period_type, period_value)
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    through = min(last, today)
    allowed = set(allowed_stores or ())
    empty = {"rows": [], "count": 0, "store_count": 0,
             "period_type": period_type, "period_value": period_value,
             "start_date": first.isoformat(), "end_date": last.isoformat(),
             "coverage": "Padrón activo con historial; no equivale a asistencia"}
    if not allowed:
        return empty
    roster = {}
    with m.db() as con:
        exists = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='operation_collaborators'").fetchone()
        if not exists:
            return empty
        q = ",".join("?" for _ in allowed)
        for r in con.execute(
            f"SELECT store,name_key,name,first_seen,last_seen,last_activity "
            f"FROM operation_collaborators WHERE active=1 AND store IN ({q})", tuple(sorted(allowed))
        ).fetchall():
            r = dict(r)
            if r["first_seen"] and str(r["first_seen"])[:10] > last.isoformat():
                continue
            key = (r["store"], norm(r["name_key"] or r["name"]))
            if key[1]:
                roster[key] = r
    if not roster or through < first:
        return empty

    seen = defaultdict(set)
    latest = {}
    def add(store, name, day):
        key = (str(store or ""), norm(name))
        if key not in roster:
            return
        ds = str(day or "")[:10]
        if not ds or ds > through.isoformat():
            return
        if key not in latest or ds > latest[key]:
            latest[key] = ds
        if ds >= first.isoformat():
            seen[key].add(ds)

    # Base de Muertos/Cambios y captura digital son fuentes paralelas.
    # Un registro válido en cualquiera evita falsos casos de "sin productividad".
    for r in (m.load_ops() or {}).get("rows") or ():
        if r.get("store") not in allowed or not is_productive(r):
            continue
        add(r.get("store"), r.get("name"), r.get("date"))

    with m.db() as con:
        q = ",".join("?" for _ in allowed)
        for table, extra in (
            ("operation_productivity", ""),
            ("operation_productivity_timer", " AND status='finished'"),
        ):
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                continue
            try:
                sql = (f"SELECT store,employee_name,date,pieces FROM {table} "
                       f"WHERE date<=? AND store IN ({q}) AND pieces>0" + extra)
                for r in con.execute(sql, (through.isoformat(), *sorted(allowed))).fetchall():
                    add(r["store"], r["employee_name"], r["date"])
            except Exception as ex:
                print(f"[V400] Consulta digital {table}: {type(ex).__name__}: {ex}", flush=True)

    rows = []
    total_days = (through - first).days + 1
    for key, r in roster.items():
        # Solo quienes no tienen ningún registro productivo en todo el periodo.
        if seen[key]:
            continue
        last_record = latest.get(key, "")
        # Evitar atribuir registros futuros a una fecha histórica seleccionada.
        rows.append({
            "name": r["name"], "store": r["store"],
            "profile": r.get("last_activity") or "Operativo",
            "last_date": last_record,
            "days_without_record": total_days,
            "status": "Sin captura de productividad",
        })
    rows.sort(key=lambda r: (r["store"].casefold(), r["name"].casefold()))
    return {**empty, "rows": rows, "count": len(rows),
            "store_count": len({r["store"] for r in rows})}


def appendix(original_pdf, result):
    """Agregar páginas nuevas; conservar intactas TODAS las páginas ya generadas."""
    from reportlab.lib.utils import ImageReader
    W, H = landscape(letter)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    m = 28
    y = 0
    navy = colors.HexColor("#173B73")
    pink = colors.HexColor("#EC007C")
    pale = colors.HexColor("#F2F6FC")
    row_h = 19
    heads = ["#", "Colaborador", "Tienda", "Perfil / actividad",
             "Último registro", "Días sin captura", "Estatus"]
    ratios = [.045,.22,.16,.19,.12,.11,.155]
    widths = [r*(W-2*m) for r in ratios]
    xs = [m]
    for w in widths[:-1]:
        xs.append(xs[-1]+w)

    def fit(text, width, font="Helvetica", size=7):
        value = str(text if text not in (None,"") else "—")
        if c.stringWidth(value,font,size) <= width-8:
            return value
        while value and c.stringWidth(value+"…",font,size)>width-8:
            value=value[:-1]
        return value+"…"
    def page():
        nonlocal y
        c.setFillColor(pale); c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(navy); c.roundRect(m,H-90,W-2*m,63,10,fill=1,stroke=0)
        c.setFillColor(colors.white);c.setFont("Helvetica-Bold",16)
        c.drawString(m+16,H-55,"Colaboradores sin productividad")
        c.setFont("Helvetica",8)
        c.drawString(m+16,H-75, "Operaciones Ropa · Price Shoes")
        # Imprimir marca existente sin alterar su tamaño.
        from pathlib import Path
        logo=Path(__file__).resolve().parent / "assets" / "price_shoes_logo.png"
        if logo.exists():
            c.setFillColor(colors.white);c.roundRect(W-m-103,H-81,86,44,6,fill=1,stroke=0)
            c.drawImage(ImageReader(str(logo)),W-m-100,H-79,width=80,height=40,
                        preserveAspectRatio=True,anchor="c",mask="auto")
        c.setFillColor(navy);c.setFont("Helvetica-Bold",10)
        c.drawString(m,H-111,f"Periodo: {result['period_value']} · {result['start_date']} a {result['end_date']}")
        c.setFont("Helvetica",8)
        c.drawString(m,H-128,f"{result['count']} colaboradores  ·  {result['store_count']} tiendas con casos")
        c.setFont("Helvetica",7)
        c.drawString(m,H-142,"Sin registro no significa ausencia; validar jornada y asistencia en tienda.")
        y=H-165
        header()
    def header():
        nonlocal y
        c.setFillColor(navy);c.roundRect(m,y-22,W-2*m,22,4,fill=1,stroke=0)
        c.setFillColor(colors.white);c.setFont("Helvetica-Bold",7)
        for x,w,t in zip(xs,widths,heads):
            c.drawString(x+5,y-14,fit(t,w,"Helvetica-Bold",7))
        y-=22
    page()
    rows=result.get("rows") or []
    if not rows:
        c.setFillColor(navy);c.setFont("Helvetica",9)
        c.drawString(m+10,y-28,"No se encontraron colaboradores activos sin captura en el periodo.")
    for idx,r in enumerate(rows,1):
        if y-row_h < 36:
            c.showPage();page()
        c.setFillColor(colors.white if idx%2 else colors.HexColor("#E8EFF8"))
        c.rect(m,y-row_h,W-2*m,row_h,fill=1,stroke=0)
        values = [str(idx),r.get("name"),r.get("store"),r.get("profile"),
                  r.get("last_date") or "Sin registro",str(r.get("days_without_record",0)),
                  "Sin productividad"]
        for col,(x,w,val) in enumerate(zip(xs,widths,values)):
            c.setFillColor(pink if col==6 else navy)
            c.setFont("Helvetica-Bold" if col in (1,6) else "Helvetica",6.7)
            c.drawString(x+5,y-12,fit(val,w,"Helvetica-Bold" if col in (1,6) else "Helvetica",6.7))
        y-=row_h
    c.save()
    writer = PdfWriter()
    for page_item in PdfReader(BytesIO(original_pdf)).pages:
        writer.add_page(page_item)
    for page_item in PdfReader(BytesIO(buf.getvalue())).pages:
        writer.add_page(page_item)
    output=BytesIO()
    writer.write(output)
    return output.getvalue()


def install(m):
    if getattr(m, "_V400_MISSING_CENTER", False):
        return
    from fastapi.responses import HTMLResponse
    def scope(request, store):
        actor=m.require_user(request, ("superadmin","admin","director","tienda"))
        selected=m.effective_store(actor,store)
        projects=set(m.project_store_names(True))
        allowed=projects if selected == "Compañía" else ({selected} & projects)
        if str(actor.get("role")) == "tienda":
            allowed &= {str(actor.get("store") or "")}
        return allowed

    @m.app.get("/api/operations/without-productivity-v400")
    def without_productivity(request: Request, period_type: str="day",
                             period_value: str="", store: str="Compañía"):
        return build_missing(m,scope(request,store),period_type,period_value)

    @m.app.get("/api/export/operations/without-productivity-v400")
    def export_without_productivity(request: Request, period_type: str="day",
                                    period_value: str="", store: str="Compañía"):
        result=build_missing(m,scope(request,store),period_type,period_value)
        with BytesIO() as output:
            with m.pd.ExcelWriter(output,engine="openpyxl") as writer:
                m.pd.DataFrame(result["rows"],columns=[
                    "name","store","profile","last_date","days_without_record","status"
                ]).rename(columns={
                    "name":"Colaborador","store":"Tienda","profile":"Perfil / Actividad",
                    "last_date":"Último registro","days_without_record":"Días sin captura",
                    "status":"Estatus"
                }).to_excel(writer,sheet_name="Sin productividad",index=False)
            body=output.getvalue()
        safe=re.sub(r"[^0-9A-Za-z_-]+","_",period_value) or "consulta"
        return Response(body,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition":f'attachment; filename="sin_productividad_{safe}.xlsx"',"Cache-Control":"no-store"})

    old_builder=m._build_operations_pdf
    def build_pdf_with_appendix(data,report,scope="Compañía"):
        original=old_builder(data,report,scope)
        if not any(x in str(report).casefold() for x in
                   ("centro ejecutivo","centro operativo","reporte semanal","reporte mensual","operación diaria","operacion diaria")):
            return original
        period_type=str(data.get("period_type") or "day")
        period_value=str(data.get("period_value") or "")
        # Restringir exactamente a las tiendas ya presentes en payload autorizado.
        projects=set(data.get("project_stores") or m.project_store_names(True))
        stores={r.get("store") for r in data.get("stores",[])
                if r.get("store") in projects}
        if scope and scope!="Compañía":
            stores &= {scope}
        result=build_missing(m,stores,period_type,period_value)
        return appendix(original,result)
    m._build_operations_pdf=build_pdf_with_appendix
    m._V400_MISSING_CENTER=True
    print("[V400] Colaboradores sin captura · Centro, XLSX y apéndice PDF instalados.",flush=True)
