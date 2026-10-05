"""Paridad de Render con la versión Python validada V89/V90.2.

Este parche NO sustituye la optimización de memoria de Render. Se instala al
final del arranque y restaura exactamente las reglas funcionales que quedaron
validadas en la versión local:

* El arrastre se conserva por etapa: Acondicionar y Ubicar tienen saldos separados.
* Lunes inicia únicamente con el pendiente generado el domingo anterior.
* Martes toma cierre de lunes; miércoles cierre de martes; así hasta domingo.
* Nunca se reconstruye el Pendiente Anterior sumando todo el histórico.
* Pend. acondicionar = apertura acond. + ingresos - acondicionado.
* Pend. ubicar = apertura ubicar + acondicionado - ubicado.
* % Acondicionado y % Ubicado usan Total pzs como denominador.
* Menú de Super Administrador con tarjeta "Vista de usuario" y acceso directo
  a "Pestañas visibles", conservando el botón de contraer/expandir.
* Vista temporal también permite rol Tienda y seleccionar la tienda.
* PDF V90 replica KPIs, tabla y gráfico del reporte visible.
"""
from __future__ import annotations

from functools import wraps
import inspect
import io
import math
import re


def _number(value):
    try:
        value = float(value or 0)
        return value if math.isfinite(value) else 0.0
    except Exception:
        return 0.0


def _install_role_preview(module) -> None:
    """Extiende la vista temporal del propietario a Tienda + tienda elegida."""
    if getattr(module, "_V90_ROLE_PREVIEW_PATCH", False):
        return

    def current_user_v90(request):
        row = module._session_user_row(request)
        if not row:
            return None
        real_role = str(row["role"] or "")
        view_role = str(request.session.get("view_role") or "")
        if real_role != "superadmin" or view_role not in ("admin", "director", "tienda"):
            view_role = ""
        effective_role = view_role or real_role
        view_store = str(request.session.get("view_store") or "").strip()
        if effective_role == "tienda":
            available = module.store_names(True)
            if view_store not in available:
                view_store = available[0] if available else str(row["store"] or "")
        else:
            view_store = ""
        return {
            "id": row["id"],
            "username": row["username"],
            "role": effective_role,
            "store": view_store if effective_role == "tienda" else row["store"],
            "real_role": real_role,
            "view_role": view_role,
            "view_store": view_store,
            "can_preview_roles": real_role == "superadmin",
            "must_change_password": bool(row["must_change_password"]) if "must_change_password" in row.keys() else False,
        }

    async def set_view_role_v90(request):
        module.require_real_superadmin(request)
        body = await request.json()
        role = str(body.get("role") or "superadmin").strip().lower()
        if role not in ("superadmin", "admin", "director", "tienda"):
            raise module.HTTPException(400, "Vista de rol inválida")
        if role == "superadmin":
            request.session.pop("view_role", None)
            request.session.pop("view_store", None)
        else:
            request.session["view_role"] = role
            if role == "tienda":
                stores = module.store_names(True)
                selected = str(body.get("store") or request.session.get("view_store") or "").strip()
                if selected not in stores:
                    selected = stores[0] if stores else ""
                request.session["view_store"] = selected
            else:
                request.session.pop("view_store", None)
        return {"ok": True, "user": current_user_v90(request)}

    module.current_user = current_user_v90
    module.set_view_role = set_view_role_v90
    for route in module.app.router.routes:
        if getattr(route, "path", None) == "/api/me/view-role" and hasattr(route, "dependant"):
            route.dependant.call = set_view_role_v90
    module._V90_ROLE_PREVIEW_PATCH = True


def _install_pending_cut(module) -> None:
    """Aplica la regla V89 sobre la respuesta ya corregida por V87."""
    if getattr(module, "_V90_PENDING_PATCH", False):
        return
    original = module.operations
    signature = inspect.signature(original)

    def _period_opening_pending(params, result):
        """Saldo de apertura por ETAPA con corte semanal real.

        Regla solicitada:
        - El LUNES toma ÚNICAMENTE lo que quedó pendiente del DOMINGO anterior.
        - MARTES toma el cierre del lunes.
        - MIÉRCOLES toma el cierre del martes.
        - ... y así hasta DOMINGO.
        - Al iniciar el lunes siguiente se vuelve a sembrar con el pendiente
          generado por ese domingo, sin reconstruir ni sumar toda la historia.

        Las etapas siguen separadas:
        - Pend. acondicionar = apertura acond. + ingresos - acondicionado.
        - Pend. ubicar       = apertura ubicar + acondicionado - ubicado.
        """
        period_type = str(params.get("period_type") or "").strip().lower()
        period_value = str(params.get("period_value") or "").strip()
        explicit_start = str(params.get("start_date") or "").strip()
        try:
            if explicit_start:
                period_start = module.pd.Timestamp(explicit_start).normalize()
            elif period_type == "day" and period_value:
                period_start = module.pd.Timestamp(period_value).normalize()
            elif period_type == "week" and period_value:
                y, w = period_value.upper().split("-W", 1)
                period_start = module.pd.Timestamp.fromisocalendar(int(y), int(w), 1).normalize()
            elif period_type == "month" and period_value:
                period_start = module.pd.Period(period_value, freq="M").start_time.normalize()
            elif period_type == "year" and period_value:
                period_start = module.pd.Timestamp(f"{str(period_value)[:4]}-01-01").normalize()
            else:
                return {}
        except Exception:
            return {}

        stores = [str(r.get("store") or "") for r in (result.get("stores") or []) if r.get("store")]
        allowed = set(stores)
        if not allowed:
            return {}

        wanted_area = module.normalize_col(params.get("area") or "")
        wanted_activity = module.normalize_col(params.get("activity") or "")
        data = module.load_ops() or {}

        # Para calcular el inicio del periodo sólo necesitamos:
        # domingo anterior + lunes..día anterior dentro de esa misma semana.
        week_monday = period_start - module.pd.Timedelta(days=int(period_start.weekday()))
        seed_sunday = week_monday - module.pd.Timedelta(days=1)
        carry_end = period_start - module.pd.Timedelta(days=1)
        seed_date = seed_sunday.date().isoformat()
        carry_end_date = carry_end.date().isoformat()

        daily = {store: {} for store in stores}

        def bucket(store, day):
            return daily[store].setdefault(day, {
                "dev": 0.0,
                "muertos": 0.0,
                "cajas": 0.0,
                "probador": 0.0,
                "acondicionado": 0.0,
                "ubicado": 0.0,
            })

        # Leer exclusivamente desde el domingo semilla hasta el día previo
        # al periodo. Nada anterior puede inflar el Pendiente Anterior.
        for row in data.get("rows") or []:
            store = str(row.get("store") or "")
            day = str(row.get("date") or "")[:10]
            if store not in allowed or not day or day < seed_date or day > carry_end_date:
                continue
            if wanted_area and module.normalize_col(row.get("area") or "") != wanted_area:
                continue
            if wanted_activity:
                a1 = module.normalize_col(row.get("activity") or "")
                a0 = module.normalize_col(row.get("activity_original") or "")
                if a1 != wanted_activity and a0 != wanted_activity:
                    continue

            d = bucket(store, day)
            muertos = _number(row.get("muertos"))
            if (
                str(row.get("activity") or "") == "Recolección de muertos"
                and str(row.get("motive_class") or "") == "Sin clasificar"
            ):
                muertos += _number(row.get("pieces"))
            d["muertos"] += muertos
            d["cajas"] += _number(row.get("cajas"))
            d["probador"] += _number(row.get("probador"))
            d["acondicionado"] += _number(row.get("acondicionado"))
            d["ubicado"] += _number(row.get("ubicado"))

        # Dev Pzs también se limita al domingo semilla + días corridos de la semana.
        try:
            recovery = module._get_recovery_fifo_rows(data)
        except Exception:
            recovery = data.get("recovery_fifo") or data.get("commercial_daily") or []

        for row in recovery or []:
            store = str(row.get("store") or "")
            day = str(row.get("date") or "")[:10]
            if store not in allowed or not day or day < seed_date or day > carry_end_date:
                continue
            bucket(store, day)["dev"] += _number(row.get("dev_pzs"))

        opening = {}
        monday_date = week_monday.date().isoformat()

        for store in stores:
            # 1) Domingo anterior: saldo semilla calculado SÓLO con ese domingo.
            sunday = daily.get(store, {}).get(seed_date, {})
            sunday_ingresos = (
                _number(sunday.get("dev")) +
                _number(sunday.get("muertos")) +
                _number(sunday.get("cajas")) +
                _number(sunday.get("probador"))
            )
            pending_acond = max(
                sunday_ingresos - _number(sunday.get("acondicionado")),
                0.0,
            )
            pending_ubicar = max(
                _number(sunday.get("acondicionado")) - _number(sunday.get("ubicado")),
                0.0,
            )

            # 2) Desde lunes hasta el día inmediatamente anterior al consultado,
            #    cada cierre alimenta únicamente al siguiente día.
            if period_start.weekday() > 0:
                cursor = week_monday
                while cursor < period_start:
                    day = cursor.date().isoformat()
                    d = daily.get(store, {}).get(day, {})
                    ingresos = (
                        _number(d.get("dev")) +
                        _number(d.get("muertos")) +
                        _number(d.get("cajas")) +
                        _number(d.get("probador"))
                    )
                    acondicionado = _number(d.get("acondicionado"))
                    ubicado = _number(d.get("ubicado"))
                    pending_acond = max(pending_acond + ingresos - acondicionado, 0.0)
                    pending_ubicar = max(pending_ubicar + acondicionado - ubicado, 0.0)
                    cursor += module.pd.Timedelta(days=1)

            opening[store] = {
                "acondicionar": pending_acond,
                "ubicar": pending_ubicar,
                "seed_sunday": seed_date,
                "week_monday": monday_date,
            }

        return opening

    @wraps(original)
    def operations_v90(*args, **kwargs):
        bound = signature.bind_partial(*args, **kwargs)
        params = dict(bound.arguments)
        result = original(*args, **kwargs)
        if not isinstance(result, dict):
            return result

        stores = result.get("stores") or []
        opening = _period_opening_pending(params, result)

        for row in stores:
            stage_open = opening.get(str(row.get("store") or ""), {}) or {}
            pending_prev_acond = _number(stage_open.get("acondicionar"))
            pending_prev_ubicar = _number(stage_open.get("ubicar"))
            base = (
                _number(row.get("dev_pzs")) + _number(row.get("muertos")) +
                _number(row.get("cajas")) + _number(row.get("probador"))
            )
            acondicionado = _number(row.get("acondicionado"))
            ubicado = _number(row.get("ubicado"))

            # "Pend. Ant." visible representa la cola que entra a Acondicionado.
            # Se guardan también ambos saldos de apertura para trazabilidad.
            row["pendiente_anterior"] = pending_prev_acond
            row["pendiente_anterior_acondicionar"] = pending_prev_acond
            row["pendiente_anterior_ubicar"] = pending_prev_ubicar
            row["pendiente_regla"] = "domingo->lunes->...->domingo"
            row["pendiente_semilla_domingo"] = str(stage_open.get("seed_sunday") or "")
            row["ingresos_periodo"] = base

            workload_acond = pending_prev_acond + base
            workload_ubicar = pending_prev_ubicar + acondicionado
            row["total_pzs"] = workload_acond
            row["ingresos"] = workload_acond
            row["pendiente_acondicionar"] = max(workload_acond - acondicionado, 0.0)
            row["pendiente_ubicar"] = max(workload_ubicar - ubicado, 0.0)

            row["pct_acondicionado"] = acondicionado / workload_acond * 100 if workload_acond else 0.0
            # Conservar la lectura histórica aprobada de % ubicado contra Total Pzs.
            row["pct_ubicado"] = ubicado / workload_acond * 100 if workload_acond else 0.0
            row["pct_ubicado_acondicionado"] = ubicado / acondicionado * 100 if acondicionado else 0.0

        stores.sort(key=lambda r: (-_number(r.get("ingresos")), str(r.get("store") or "")))
        result["stores"] = stores
        metrics = result.setdefault("metrics", {})
        sum_key = lambda key: float(sum(_number(r.get(key)) for r in stores))
        metrics["pendiente_anterior"] = sum_key("pendiente_anterior")
        metrics["pendiente_anterior_acondicionar"] = sum_key("pendiente_anterior_acondicionar")
        metrics["pendiente_anterior_ubicar"] = sum_key("pendiente_anterior_ubicar")
        metrics["ingresos_periodo"] = sum_key("ingresos_periodo")
        metrics["total_pzs"] = sum_key("total_pzs")
        metrics["ingresos"] = metrics["total_pzs"]
        metrics["pendiente_acondicionar"] = sum_key("pendiente_acondicionar")
        metrics["pendiente_ubicar"] = sum_key("pendiente_ubicar")
        metrics["pct_acondicionado"] = (
            _number(metrics.get("acondicionado")) / metrics["total_pzs"] * 100 if metrics["total_pzs"] else 0.0
        )
        metrics["pct_ubicado"] = (
            _number(metrics.get("ubicado")) / metrics["total_pzs"] * 100 if metrics["total_pzs"] else 0.0
        )
        metrics["pct_ubicado_acondicionado"] = (
            _number(metrics.get("ubicado")) / _number(metrics.get("acondicionado")) * 100
            if _number(metrics.get("acondicionado")) else 0.0
        )
        metrics["pct_procesado"] = (
            (metrics["total_pzs"] - metrics["pendiente_ubicar"]) / metrics["total_pzs"] * 100
            if metrics["total_pzs"] else 0.0
        )
        try:
            module._OPS_RESPONSE_CACHE.clear()
        except Exception:
            pass
        return result

    module.operations = operations_v90
    for route in module.app.router.routes:
        if getattr(route, "path", None) == "/api/operations" and hasattr(route, "dependant"):
            route.dependant.call = operations_v90
    module._V90_PENDING_PATCH = True


def _install_pdf_v90(module) -> None:
    """PDF espejo V90 para los reportes que el usuario validó en Python."""
    if getattr(module, "_V90_PDF_PATCH", False):
        return
    original = module._build_operations_pdf

    def build_pdf_v90(data: dict, report: str, scope: str = "Compañía") -> bytes:
        handled = {
            "Operación Diaria", "Centro Ejecutivo", "Reporte Semanal", "Reporte Mensual",
            "Conversión", "Recuperación Económica",
        }
        if report not in handled:
            return original(data, report, scope)

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen import canvas

        BLUE = "#16457F"; BLUE2 = "#1E6FE8"; PINK = "#EC007C"; PURPLE = "#7C3AED"
        GREEN = "#10B981"; ORANGE = "#F59E0B"; RED = "#EF4444"; TXT = "#123B6C"
        BG = "#F4F7FB"; LINE = "#D9E2EE"; MUTED = "#64748B"
        bio = io.BytesIO(); width, height = landscape(letter); M = 28
        c = canvas.Canvas(bio, pagesize=(width, height)); y = height - 28
        mt = data.get("metrics") or {}; stores = list(data.get("stores") or [])
        recovery = list(data.get("recovery_by_store") or [])
        period = str(data.get("period_value") or "Histórico")

        def n(v): return f"{_number(v):,.0f}"
        def pc(v): return f"{_number(v):.1f}%"
        def money(v): return f"${_number(v):,.0f}"
        def page_header(suffix=""):
            nonlocal y
            c.setFillColor(colors.HexColor(BG)); c.rect(0, 0, width, height, fill=1, stroke=0)
            c.setFillColor(colors.HexColor(BLUE)); c.roundRect(M, height-92, width-2*M, 62, 12, fill=1, stroke=0)
            c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 18); c.drawString(M+18, height-58, "Cambios y Muertos")
            c.setFont("Helvetica", 8.5); c.drawString(M+18, height-75, "Recuperación, conversión, recolección y seguimiento operativo")
            c.setFont("Helvetica-Bold", 10); c.drawRightString(width-M-18, height-56, "Operaciones Ropa · Price Shoes")
            c.setFont("Helvetica", 7.5); c.drawRightString(width-M-18, height-72, f"{report}{(' · '+suffix) if suffix else ''}")
            y = height - 108
        def new_page(suffix=""):
            nonlocal y
            c.showPage(); page_header(suffix)
        def ensure(space):
            if y-space < 28: new_page()
        def section(title):
            nonlocal y
            ensure(26); c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold", 12); c.drawString(M, y, title); y -= 18
        def wrap_text(text, limit=32):
            words = str(text or "").split(); lines=[]; cur=""
            for word in words:
                candidate=(cur+" "+word).strip()
                if len(candidate)<=limit or not cur: cur=candidate
                else: lines.append(cur);cur=word
            if cur:lines.append(cur)
            return lines[:2]
        def kpis(items):
            nonlocal y
            cols=min(5,max(1,len(items))); gap=8; cardw=(width-2*M-gap*(cols-1))/cols; cardh=62
            rows=(len(items)+cols-1)//cols; ensure(rows*(cardh+gap)+8)
            for idx,(label,value,sub,tone) in enumerate(items):
                rr=idx//cols; cc=idx%cols; x=M+cc*(cardw+gap); yy=y-rr*(cardh+gap)-cardh
                c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.roundRect(x,yy,cardw,cardh,8,fill=1,stroke=1)
                c.setFillColor(colors.HexColor(tone)); c.roundRect(x,yy,4,cardh,2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica-Bold",6.4); c.drawString(x+12,yy+44,str(label).upper()[:28])
                c.setFillColor(colors.HexColor(TXT)); c.setFont("Helvetica-Bold",16); c.drawString(x+12,yy+23,str(value)[:20])
                c.setFillColor(colors.HexColor(MUTED)); c.setFont("Helvetica",5.7)
                lines=wrap_text(sub,33)
                if len(lines)==1:c.drawString(x+12,yy+8,lines[0])
                elif lines:c.drawString(x+12,yy+11,lines[0]);c.drawString(x+12,yy+4,lines[1])
            y -= rows*(cardh+gap)+5
        def table(headers, rows, widths, title):
            nonlocal y
            if not rows:return
            section(title); total=width-2*M; xs=[M];acc=M
            for frac in widths[:-1]:acc+=total*frac;xs.append(acc)
            def head():
                nonlocal y
                hh=27 if any("\n" in h for h in headers) else 19; ensure(hh+6)
                c.setFillColor(colors.HexColor(BLUE));c.roundRect(M,y-hh+4,total,hh,4,fill=1,stroke=0)
                c.setFillColor(colors.white);c.setFont("Helvetica-Bold",4.8)
                for i,h in enumerate(headers):
                    lines=str(h).split("\n");c.drawString(xs[i]+2,y-7,lines[0][:22])
                    if len(lines)>1:c.drawString(xs[i]+2,y-15,lines[1][:22])
                y-=hh+2
            head()
            for ridx,row in enumerate(rows):
                if y-15<28:new_page(title);head()
                if ridx%2==1:
                    c.setFillColor(colors.HexColor("#EEF4FB"));c.rect(M,y-13,total,15,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(TXT));c.setFont("Helvetica",4.7)
                for i,value in enumerate(row):c.drawString(xs[i]+2,y-9,str(value if value is not None else "")[:28])
                y-=15
            y-=8
        def operational_table(rows):
            vals=[]
            for i,r in enumerate(rows,1):
                total=r.get("total_pzs")
                if total is None:total=_number(r.get("dev_pzs"))+_number(r.get("muertos"))+_number(r.get("probador"))+_number(r.get("cajas"))+_number(r.get("pendiente_anterior"))
                vals.append([f"#{i}",r.get("store"),n(r.get("dev_pzs")),n(r.get("muertos")),n(r.get("probador")),n(r.get("cajas")),n(r.get("pendiente_anterior")),n(total),n(r.get("recorridos")),n(r.get("acondicionado")),n(r.get("ubicado")),n(r.get("pendiente_acondicionar")),n(r.get("pendiente_ubicar"))])
            table(["Ranking","Tienda","Dev pzs","Muertos","Probador","Cajas","Pend. Ant.","Total pzs","Recorridos\nrealizados","Acondicionado","Ubicado","Pendiente de\nacondicionar","Pendiente de\nubicar"],vals,[.04,.12,.065,.06,.06,.055,.07,.07,.08,.075,.07,.12,.115],"Detalle operativo")
        def recovery_table(rows):
            vals=[]
            for i,r in enumerate(rows,1):vals.append([f"#{i}",r.get("store"),n(r.get("dev_pzs")),n(r.get("converted_pieces")),pc(r.get("conversion_pct")),money(r.get("return_value")),money(r.get("recovered_value")),pc(r.get("recovery_pct")),n(r.get("pending_pieces")),money(r.get("pending_value"))])
            table(["#","Tienda","Dev Pzs","Pzas\nrecuperadas","Conversión","Valor\ndevolución","Recuperación $","Recup. %","Pend. Pzs","Pend. $"],vals,[.04,.16,.08,.09,.09,.13,.13,.09,.09,.10],"Recuperación por tienda")
        def chart(rows):
            nonlocal y
            if not rows:return
            h=205; ensure(h+30); section(f"Ingreso vs Acondicionado vs Ubicado · {period}")
            shown=rows[:17]; vals=[]
            for r in shown:vals.extend([_number(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos")),_number(r.get("acondicionado")),_number(r.get("ubicado"))])
            maxv=max(vals+[1]);x0=M+42;x1=width-M-12;base=y-h+38;top=y-18;plot=top-base;gw=(x1-x0)/max(1,len(shown));bw=min(10,gw*.22)
            c.setStrokeColor(colors.HexColor(LINE));
            for q in range(5):
                gy=base+plot*q/4;c.line(x0,gy,x1,gy);c.setFillColor(colors.HexColor(MUTED));c.setFont("Helvetica",5);c.drawRightString(x0-4,gy-2,n(maxv*q/4))
            pts=[]
            for i,r in enumerate(shown):
                cx=x0+gw*(i+.5);a=_number(r.get("acondicionado"));u=_number(r.get("ubicado"));inp=_number(r.get("total_pzs") if r.get("total_pzs") is not None else r.get("ingresos"))
                for value,off,col in ((a,-bw*.65,BLUE),(u,bw*.65,PINK)):
                    bh=plot*value/maxv;c.setFillColor(colors.HexColor(col));c.rect(cx+off-bw/2,base,bw,bh,fill=1,stroke=0)
                py=base+plot*inp/maxv;pts.append((cx,py));c.setFillColor(colors.HexColor(BLUE2));c.circle(cx,py,2.2,fill=1,stroke=0)
                c.setFillColor(colors.HexColor(MUTED));c.setFont("Helvetica",4.3);c.saveState();c.translate(cx-2,base-5);c.rotate(55);c.drawRightString(0,0,str(r.get("store") or "")[:12]);c.restoreState()
            if len(pts)>1:
                c.setStrokeColor(colors.HexColor(BLUE2));c.setLineWidth(1.4)
                for p1,p2 in zip(pts,pts[1:]):c.line(p1[0],p1[1],p2[0],p2[1])
            y-=h+5

        page_header(); c.setFillColor(colors.HexColor(MUTED));c.setFont("Helvetica",7.2);c.drawString(M,y,f"Periodo: {period}   ·   Alcance: {scope}");y-=14
        ordered_stores=sorted(stores,key=lambda r:(-_number(r.get("ingresos")),str(r.get("store") or "")))
        ordered_rec=sorted(recovery,key=lambda r:(-_number(r.get("conversion_pct")),str(r.get("store") or "")))

        if report == "Operación Diaria":
            kpis([("Dev pzs",n(mt.get("dev_pzs")),"Devoluciones del periodo",BLUE),("Muertos",n(mt.get("muertos")),"Recolección · motivo Muertos",PINK),("Probador",n(mt.get("probador")),"Motivo Probador",ORANGE),("Cajas",n(mt.get("cajas")),"Recolección · Cajas",PURPLE),("Total pzs",n(mt.get("total_pzs")),"Dev + Muertos + Cajas + Probador + Pend. Ant.",BLUE2),("Recorridos realizados",n(mt.get("recorridos")),f"{pc(mt.get('pct_recorridos'))} · meta {n(mt.get('meta_recorridos'))}",GREEN),("Acondicionado",n(mt.get("acondicionado")),pc(mt.get("pct_acondicionado")),PURPLE),("Ubicado",n(mt.get("ubicado")),pc(mt.get("pct_ubicado")),PINK),("Pendiente de acondicionar",n(mt.get("pendiente_acondicionar")),"Total pzs - Acondicionado",ORANGE),("Pendiente de ubicar",n(mt.get("pendiente_ubicar")),"Total pzs - Ubicado",RED)])
            operational_table(ordered_stores);chart(ordered_stores)
        elif report == "Centro Ejecutivo":
            kpis([("Conversión",pc(mt.get("conversion_pct")),"FIFO diario · misma semana ISO",PURPLE),("Pzas recuperadas",n(mt.get("converted_pieces")),"Sólo ventas posteriores a la devolución",GREEN),("Recuperación económica",pc(mt.get("recovery_pct")),"Recuperación $ / Valor devolución",PINK),("Valor de la devolución",money(mt.get("return_value")),"Devoluciones del periodo consultado",BLUE2),("Recuperación $",money(mt.get("recovered_value")),"Misma semana ISO",GREEN),("Pendiente $",money(mt.get("pending_recovery_value")),"Valor devolución - Recuperación $",RED)])
            recovery_table(ordered_rec);operational_table(ordered_stores);chart(ordered_stores)
        elif report in ("Reporte Semanal","Reporte Mensual"):
            label="Total pzs mes" if report=="Reporte Mensual" else "Total pzs"
            kpis([(label,n(mt.get("total_pzs")),period,BLUE2),("Acondicionado",pc(mt.get("pct_acondicionado")),n(mt.get("acondicionado")),PURPLE),("Ubicado",pc(mt.get("pct_ubicado")),n(mt.get("ubicado")),PINK),("Conversión",pc(mt.get("conversion_pct")),f"{n(mt.get('converted_pieces'))} piezas",GREEN),("Recuperación económica",pc(mt.get("recovery_pct")),money(mt.get("recovered_value")),BLUE),("Productividad",pc(mt.get("productivity_pct")),f"{n(mt.get('productivity_daily'))} pzs/día",ORANGE),("Recorridos",pc(mt.get("pct_recorridos")),f"{n(mt.get('recorridos'))} realizados",RED)])
            recovery_table(ordered_rec);operational_table(ordered_stores);chart(ordered_stores)
        elif report == "Conversión":
            kpis([("Dev Pzs",n(mt.get("dev_pzs")),"Devoluciones detectadas",BLUE2),("Piezas convertidas",n(mt.get("converted_pieces")),"Venta validada misma semana",GREEN),("% Conversión",pc(mt.get("conversion_pct")),"Convertidas / Dev Pzs",GREEN),("Pendiente",n(mt.get("pending_recovery_pieces")),"Dev - convertidas",RED)]);recovery_table(ordered_rec)
        elif report == "Recuperación Económica":
            kpis([("Valor devolución",money(mt.get("return_value")),"Precio unitario neto × Dev Pzs",BLUE2),("Recuperación $",money(mt.get("recovered_value")),"Venta recuperada",GREEN),("% Recuperación",pc(mt.get("recovery_pct")),"Recuperado / valor devolución",GREEN),("Pendiente $",money(mt.get("pending_recovery_value")),"Valor aún no recuperado",RED)]);recovery_table(ordered_rec)
        c.save();pdf=bio.getvalue()
        if not pdf.startswith(b"%PDF"):raise RuntimeError("El generador no produjo un PDF válido")
        return pdf

    module._build_operations_pdf = build_pdf_v90
    module._V90_PDF_PATCH = True


def _install_ui(module) -> None:
    """Postprocesa el HTML final (incluye los cambios del middleware V87)."""
    if getattr(module, "_V90_UI_PATCH", False):
        return
    from fastapi.responses import HTMLResponse

    css = r"""
<style id="v90-render-parity-css">
.owner-tools{margin:7px 0 4px;padding:9px 8px;border:1px solid #dce4ee;border-radius:10px;background:#f7faff;display:grid;gap:6px}
.owner-tools-title{font-size:8px;font-weight:950;text-transform:uppercase;letter-spacing:.45px;color:#667085}
.owner-tools select{width:100%;min-height:32px;border:1px solid #cfd9e6;border-radius:8px;background:#fff;color:var(--text);padding:5px 7px;font-size:9px;font-weight:800}
.owner-action{border:1px solid #a9bdd8;background:#fff;color:var(--navy);border-radius:8px;padding:7px 8px;font-size:8px;font-weight:900;cursor:pointer}
.owner-action:hover{background:#eef5ff}.shell.sidebar-collapsed .owner-tools{display:none!important}
</style>
"""
    script = r"""
<script id="v90-render-parity-js">
(function(){
  function setupOwnerTools(){
    const box=document.getElementById('viewRoleBox'), role=document.getElementById('viewRoleSelect'), store=document.getElementById('viewStoreSelect');
    if(!box||!role)return;
    if(![...role.options].some(o=>o.value==='tienda'))role.add(new Option('Tienda','tienda'));
    const refreshStoreVisibility=async()=>{
      if(!store)return;
      const isStore=role.value==='tienda';store.classList.toggle('hidden',!isStore);if(!isStore)return;
      try{const r=await api('/api/stores');const rows=r.stores||[];const current=(USER&&USER.view_store)||USER?.store||store.value;store.innerHTML=rows.map(x=>`<option value="${x.name}">${x.name}</option>`).join('');if([...store.options].some(o=>o.value===current))store.value=current}catch(e){console.warn(e)}
    };
    role.addEventListener('change',async e=>{e.stopImmediatePropagation();role.disabled=true;try{await refreshStoreVisibility();const r=await api('/api/me/view-role',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role:role.value,store:store?.value||''})});await enter(r.user);await refreshStoreVisibility()}catch(err){alert('No fue posible cambiar la vista: '+err.message)}finally{role.disabled=false}},true);
    store?.addEventListener('change',async()=>{try{const r=await api('/api/me/view-role',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role:'tienda',store:store.value})});await enter(r.user)}catch(err){alert('No fue posible cambiar la tienda: '+err.message)}});
    refreshStoreVisibility();
  }
  document.getElementById('openTabConfig')?.addEventListener('click',async()=>{try{await goMain('users');setTimeout(()=>document.getElementById('tabVisibilityPanel')?.scrollIntoView({behavior:'smooth',block:'start'}),80)}catch(e){console.warn(e)}});
  setupOwnerTools();

  // Tabla de Operación Diaria V89: incluye Pend. Ant. y Total pzs en el mismo orden de Python.
  if(typeof operationalDetailTable==='function'){
    operationalDetailTable=function(stores,recovery=[]){
      const rows=[...(stores||[])].sort((a,b)=>(Number(b.ingresos)||0)-(Number(a.ingresos)||0));
      return `<div class="tablewrap"><table class="table"><thead><tr><th>Ranking</th><th>Tienda</th><th>Dev pzs</th><th>Muertos</th><th>Probador</th><th>Cajas</th><th>Pend. Ant.</th><th>Total pzs</th><th>Recorridos realizados</th><th>Acondicionado</th><th>Ubicado</th><th>Pendiente de acondicionar</th><th>Pendiente de ubicar</th></tr></thead><tbody>${rows.map((r,i)=>`<tr><td><b>#${i+1}</b></td><td><b>${r.store}</b></td><td>${fmt(r.dev_pzs)}</td><td>${fmt(r.muertos)}</td><td>${fmt(r.probador)}</td><td>${fmt(r.cajas)}</td><td>${fmt(r.pendiente_anterior||0)}</td><td><b>${fmt(r.total_pzs??r.ingresos)}</b></td><td>${fmt(r.recorridos)}</td><td>${fmt(r.acondicionado)}</td><td>${fmt(r.ubicado)}</td><td>${fmt(r.pendiente_acondicionar)}</td><td>${fmt(r.pendiente_ubicar)}</td></tr>`).join('')}</tbody></table></div>`;
    };
  }
})();
</script>
"""

    @module.app.middleware("http")
    async def _v90_html_parity(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v90-render-parity-js" in html:
                return HTMLResponse(html, status_code=response.status_code, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})

            # Reemplazar el selector simple por la tarjeta que quedó validada en Python.
            profile_pattern = re.compile(r'<div class="profile"><b id="profileName">Usuario</b><small id="profileRole"></small><div id="viewRoleBox".*?</div><small id="profileMeta">.*?</small><button class="logout" id="logout">Cerrar sesión</button></div></aside>', re.S)
            replacement = '''<div class="owner-tools hidden" id="viewRoleBox"><div class="owner-tools-title">Vista de usuario</div><select id="viewRoleSelect" aria-label="Ver sistema como"><option value="superadmin">Super Administrador</option><option value="admin">Administrador</option><option value="director">Director / Consulta</option><option value="tienda">Tienda</option></select><select id="viewStoreSelect" class="hidden" aria-label="Tienda para vista previa"></select><button type="button" class="owner-action" id="openTabConfig">⚙ Pestañas visibles</button></div><div class="profile"><b id="profileName">Usuario</b><small id="profileRole"></small><small id="profileMeta">V90 · Render sincronizado</small><button class="logout" id="logout">Cerrar sesión</button></div></aside>'''
            html, _ = profile_pattern.subn(replacement, html, count=1)
            html = html.replace("Dev + Muertos + Cajas + Probador','#3366CC'", "Dev + Muertos + Cajas + Probador + Pend. Ant.','#3366CC'")
            html = html.replace("Acondicionado - Ubicado','#EF4444'", "Total pzs - Ubicado','#EF4444'")
            html = html.replace("V49 · menú fijo + móvil", "V90 · Render sincronizado")
            html = html.replace("V49 · Menú fijo · Excel capacidades", "V90 · Excel capacidades")
            html = html.replace("</head>", css + "</head>", 1)
            html = html.replace("</body>", script + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})
        except Exception as exc:
            print(f"[V90-PARITY] UI warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    module._V90_UI_PATCH = True


def install(module) -> None:
    if getattr(module, "_V90_RENDER_PARITY", False):
        return
    _install_role_preview(module)
    _install_pending_cut(module)
    _install_pdf_v90(module)
    _install_ui(module)
    module._V90_RENDER_PARITY = True
    print("[V90.2-PARITY] Pendiente semanal: domingo semilla -> lunes -> ... -> domingo; sin arrastre histórico.", flush=True)
