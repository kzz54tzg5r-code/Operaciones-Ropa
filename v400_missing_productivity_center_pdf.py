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
    aliases = {}
    with m.db() as con:
        alias_table=con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operation_collaborator_aliases'"
        ).fetchone()
        if alias_table:
            q=",".join("?" for _ in allowed)
            for a in con.execute(
                f"SELECT store,alias_key,canonical_key FROM operation_collaborator_aliases "
                f"WHERE store IN ({q})",tuple(sorted(allowed))
            ).fetchall():
                aliases[(a["store"],norm(a["alias_key"]))] = (
                    a["store"],norm(a["canonical_key"]))
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
        # Alias del padrón: la captura histórica mantiene su nombre original
        # pero cuenta para la persona principal si fue unificado por admin.
        key = aliases.get(key,key)
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
            "status": "Sin captura de productividad",
        })
    rows.sort(key=lambda r: (r["store"].casefold(), r["name"].casefold()))
    return {**empty, "rows": rows, "count": len(rows),
            "store_count": len({r["store"] for r in rows})}


def appendix(original_pdf, result):
    """Anexo con identidad visual de Centro Operativo, en el extremo final del PDF.

    Tablas legibles, filas densas, salto paginado real y marca blanca sin fondo.
    El PDF principal se preserva íntegro para que coincidan datos y gráficas.
    """
    from v403_white_price_logo_pdf import draw_price_white
    W, H = landscape(letter)
    M=27
    usable=W-2*M
    navy=colors.HexColor("#173B73")
    blue=colors.HexColor("#265B98")
    pink=colors.HexColor("#EC007C")
    textcolor=colors.HexColor("#173B73")
    muted=colors.HexColor("#667085")
    pale=colors.HexColor("#F3F6FA")
    stripe=colors.HexColor("#EEF4FB")
    border=colors.HexColor("#D8E0EB")
    ink=colors.white
    rows=result.get("rows") or []
    # Dimensionar el ancho por contenido, no dividirlo en siete columnas minúsculas.
    cols=["#","Colaborador","Tienda","Perfil / actividad","Último registro","Estatus"]
    fractions=[.048,.275,.155,.187,.139,.196]
    widths=[usable*x for x in fractions]
    xs=[M]
    for w in widths[:-1]:
        xs.append(xs[-1]+w)
    buf=BytesIO()
    c=canvas.Canvas(buf,pagesize=(W,H),pageCompression=1)
    page_number=0
    y=0
    # Paginación equilibrada: nunca dejar una sola fila en una hoja nueva.
    # Para 11 registros usar una única hoja casi completa; para más de 18,
    # repartirlos de manera pareja entre páginas.
    page_count=max(1, (len(rows)+17)//18)
    per_page=max(1,(len(rows)+page_count-1)//page_count)
    row_h=min(28.4,max(17.4,(H-298)/per_page))
    head_h=31

    def fitting(raw,width,font="Helvetica",start=10.0):
        value=str(raw if raw not in (None,"") else "—")
        size=start
        while size>=8.0 and c.stringWidth(value,font,size)>width-12:
            size-=.25
        if c.stringWidth(value,font,size)<=width-12:
            return value,size
        while value and c.stringWidth(value+"…",font,8.0)>width-12:
            value=value[:-1]
        return value+"…",8.0

    def table_header():
        nonlocal y
        c.setFillColor(navy)
        c.roundRect(M,y-head_h,usable,head_h,6,stroke=0,fill=1)
        c.setFillColor(ink)
        for col,(x,w,label) in enumerate(zip(xs,widths,cols)):
            font="Helvetica-Bold"
            value,size=fitting(label,w,font,9.0)
            c.setFont(font,size)
            if col==0:
                c.drawCentredString(x+w/2,y-20,value)
            else:
                c.drawString(x+7,y-20,value)
        y-=head_h

    def begin_page():
        nonlocal y,page_number
        page_number+=1
        c.setFillColor(pale)
        c.rect(0,0,W,H,stroke=0,fill=1)
        # Mismo encabezado oscuro del PDF de Centro Operativo.
        c.setFillColor(blue)
        c.roundRect(M,H-91,usable,61,11,stroke=0,fill=1)
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold",18)
        c.drawString(M+17,H-56,"Cambios y Muertos")
        c.setFont("Helvetica",9.4)
        c.drawString(M+17,H-75,"Recuperación, conversión, recolección y seguimiento operativo")
        try:
            draw_price_white(c,W-M-108,H-85,99,53)
        except Exception as error:
            print(f"[V403 PDF] Marca blanca: {error}",flush=True)
            c.setFillColor(ink)
            c.setFont("Helvetica-Bold",10)
            c.drawRightString(W-M-12,H-56,"PRICE SHOES")
        y=H-118
        c.setFillColor(textcolor)
        c.setFont("Helvetica-Bold",15.5)
        c.drawString(M,y,"Colaboradores sin productividad")
        y-=21
        c.setFillColor(muted)
        c.setFont("Helvetica",9.8)
        c.drawString(M,y,f"Periodo: {result.get('period_value') or 'Consulta'}   ·   "
                         f"{result.get('start_date') or ''} a {result.get('end_date') or ''}")
        y-=25
        # Tarjetas resumen compactas, mismas gamas cromáticas que la pantalla.
        c.setFillColor(colors.HexColor("#FCE7F3"))
        c.roundRect(M,y-29,191,29,7,stroke=0,fill=1)
        c.setFillColor(pink)
        c.setFont("Helvetica-Bold",13)
        c.drawString(M+12,y-20,str(result.get("count",len(rows))))
        c.setFont("Helvetica-Bold",9.0)
        c.drawString(M+42,y-20,"colaboradores sin captura")
        c.setFillColor(colors.HexColor("#DCEBFF"))
        c.roundRect(M+199,y-29,186,29,7,stroke=0,fill=1)
        c.setFillColor(navy)
        c.setFont("Helvetica-Bold",13)
        c.drawString(M+210,y-20,str(result.get("store_count",0)))
        c.setFont("Helvetica-Bold",9.0)
        c.drawString(M+241,y-20,"tiendas con casos")
        y-=41
        c.setFillColor(muted)
        c.setFont("Helvetica",9.0)
        c.drawString(M,y,"Sin captura no significa inasistencia; validar jornada con la tienda.")
        y-=15
        table_header()

    begin_page()
    if not rows:
        c.setFillColor(textcolor)
        c.setFont("Helvetica",11)
        c.drawString(M+12,y-31,"No se encontraron colaboradores activos sin registro para este periodo.")
    for idx,item in enumerate(rows,1):
        if idx>1 and (idx-1)%per_page==0:
            c.showPage()
            begin_page()
        c.setFillColor(colors.white if idx%2 else stripe)
        c.rect(M,y-row_h,usable,row_h,stroke=0,fill=1)
        values=[
            str(idx),item.get("name") or "—",item.get("store") or "—",
            item.get("profile") or "Operativo",item.get("last_date") or "Sin registro",
            "Sin productividad",
        ]
        for col,(x,w,value) in enumerate(zip(xs,widths,values)):
            font="Helvetica-Bold" if col in (0,1,5) else "Helvetica"
            value,size=fitting(value,w,font,9.6 if col!=1 else 10.0)
            c.setFont(font,size)
            c.setFillColor(pink if col==5 else textcolor)
            if col==0:
                c.drawCentredString(x+w/2,y-row_h/2-3,value)
            else:
                c.drawString(x+7,y-row_h/2-3,value)
        c.setStrokeColor(border)
        c.setLineWidth(.3)
        c.line(M,y-row_h,M+usable,y-row_h)
        y-=row_h
    # Nota de pie y folio. Nunca generar páginas vacías.
    c.setFillColor(muted)
    c.setFont("Helvetica",8.8)
    c.drawString(M,25,"Operaciones Ropa · Price Shoes")
    c.drawRightString(W-M,25,f"Anexo · pág. {page_number}")
    c.save()
    writer=PdfWriter()
    for p in PdfReader(BytesIO(original_pdf)).pages:
        writer.add_page(p)
    for p in PdfReader(BytesIO(buf.getvalue())).pages:
        writer.add_page(p)
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
                    "name","store","profile","last_date","status"
                ]).rename(columns={
                    "name":"Colaborador","store":"Tienda","profile":"Perfil / Actividad",
                    "last_date":"Último registro","status":"Estatus"
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
