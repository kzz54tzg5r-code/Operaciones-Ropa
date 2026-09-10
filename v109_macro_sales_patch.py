"""V109: Ventas ejecutivas en Macro + reparación de carga de PDF mensuales.

- Macro: Meta, Venta año, Venta año pasado, Cumplimiento y Crecimiento.
- Tendencia mensual: año actual vs anterior + línea de meta.
- Fuente: historial de PDF de ventas mensuales.
- Metas editables por año/alcance para Super Admin y Admin.
- Repara parse_sales_pdf y los botones Procesar ventas que no ejecutaban acción.
- Refresca Macro inmediatamente después de procesar una carga.

No modifica Cambios y Muertos ni los PDF operativos V107/V108.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import re
import threading
import time
import unicodedata

PARSER_VERSION = 109


def _norm(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"\s+", " ", text).strip()


def _num_token(raw) -> float:
    text = re.sub(r"[^0-9,.\-]", "", str(raw or "").strip())
    if not text or text in {"-", ".", ","}:
        return 0.0
    try:
        if "," in text and "." in text:
            text = text.replace(",", "")
        elif "," in text:
            parts = text.split(",")
            if all(len(x) == 3 for x in parts[1:]):
                text = "".join(parts)
            else:
                text = text.replace(",", ".")
        return float(text)
    except Exception:
        return 0.0


def _numbers(line: str):
    result = []
    for token in re.findall(r"\$?\s*-?\d[\d,]*(?:\.\d+)?", str(line or "")):
        value = _num_token(token)
        if math.isfinite(value):
            result.append((token, value))
    return result


def _extract_sales_totals(text: str):
    """Extrae Venta $ y Venta pzas con reglas conservadoras y tolerantes."""
    money_candidates = []
    piece_candidates = []
    lines = [re.sub(r"\s+", " ", x).strip() for x in str(text or "").splitlines() if x.strip()]
    skip = (
        "UTILIDAD", "COSTO", "PRECIO", "INVERSION", "INVENTARIO", "EXISTENCIA",
        "SUGERIDO", " SUG ", "DDI", "CAPACIDAD",
    )
    for idx, raw in enumerate(lines):
        line = _norm(raw)
        if any(word in line for word in skip):
            continue
        if "VENTA" not in line and re.search(r"\bVTA\b", line) is None:
            continue
        vals = _numbers(raw)
        if not vals:
            continue
        score = 10
        if "TOTAL" in line or "GENERAL" in line:
            score += 8
        if "ACUM" in line:
            score += 7
        if "NETA" in line or "NETAS" in line:
            score += 6
        if "MES" in line or "MENSUAL" in line:
            score += 4
        if "IMPORTE" in line or "MONTO" in line or "PESOS" in line:
            score += 5
        for raw_token, value in vals:
            if value <= 0 or (2020 <= value <= 2100 and "$" not in raw_token):
                continue
            mscore = score + (12 if "$" in raw_token else 0) + (5 if "$" in raw else 0)
            money_candidates.append((mscore, value, idx, raw))
        if any(word in line for word in ("PZAS", "PZA", "PIEZAS", "UNIDADES", "UDS")):
            for raw_token, value in vals:
                if value <= 0 or 2020 <= value <= 2100 or "$" in raw_token:
                    continue
                piece_candidates.append((score + 8, value, idx, raw))

    joined = "\n".join(lines)
    for pattern in (
        r"(?:VENTA|VTA)\s*(?:NETA|NETAS|TOTAL|ACUM(?:ULADA)?|MENSUAL)?\s*(?:EN)?\s*\$?\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
        r"(?:TOTAL\s+(?:DE\s+)?)?(?:VENTA|VTA)\s*(?:EN\s+PESOS|EN\s+\$|IMPORTE|MONTO)\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
    ):
        for match in re.finditer(pattern, _norm(joined), flags=re.I):
            value = _num_token(match.group(1))
            if value > 0 and not (2020 <= value <= 2100):
                money_candidates.append((40, value, -1, match.group(0)))
    for pattern in (
        r"(?:VENTA|VTA)\s*(?:TOTAL|ACUM(?:ULADA)?|MENSUAL)?\s*(?:EN)?\s*(?:PZAS|PIEZAS|UNIDADES)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
        r"(?:PZAS|PIEZAS)\s*(?:VENDIDAS|VENTA)?\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
    ):
        for match in re.finditer(pattern, _norm(joined), flags=re.I):
            value = _num_token(match.group(1))
            if value > 0 and not (2020 <= value <= 2100):
                piece_candidates.append((40, value, -1, match.group(0)))

    def choose(candidates):
        if not candidates:
            return 0.0, ""
        best = max(candidates, key=lambda x: (x[0], x[1]))
        return float(best[1]), str(best[3])

    sales, source_line = choose(money_candidates)
    pieces, _ = choose(piece_candidates)
    return sales, pieces, source_line


def install(m):
    if getattr(m, "_V109_MACRO_SALES", False):
        return

    # 1) Parser de PDF mensual reparado. El endpoint existente lo resuelve por global.
    def parse_sales_pdf_v109(path: str | Path, year: int | None = None, month: int | None = None) -> dict:
        path = Path(path)
        record = {
            "file": path.name, "year": int(year or 0), "month": int(month or 0),
            "rows": 0, "store": "", "stores": 0, "pages": 0,
            "total_pieces": 0.0, "total_sales": 0.0,
            "status": "Sin información útil", "parser_version": PARSER_VERSION,
        }
        try:
            import pdfplumber
            try:
                from commercial.parsers import store_from_filename, _store_from_pdf_text
            except Exception:
                store_from_filename = None
                _store_from_pdf_text = None
            chunks = []
            with pdfplumber.open(path) as pdf:
                record["pages"] = len(pdf.pages)
                for page in pdf.pages:
                    try:
                        chunks.append(page.extract_text(x_tolerance=2, y_tolerance=3) or "")
                    except TypeError:
                        chunks.append(page.extract_text() or "")
            text = "\n".join(chunks)
            store = ""
            if callable(store_from_filename):
                try:
                    store = store_from_filename(path) or ""
                except Exception:
                    pass
            if not store and callable(_store_from_pdf_text):
                try:
                    store = _store_from_pdf_text(text) or ""
                except Exception:
                    pass
            if not store:
                haystack = _norm(path.stem + " " + "\n".join(text.splitlines()[:80]))
                try:
                    available = list(m.store_names(True) or [])
                except Exception:
                    available = list(getattr(m, "PROJECT_STORES", []) or [])
                for candidate in sorted(available, key=lambda x: len(str(x)), reverse=True):
                    if _norm(candidate) and _norm(candidate) in haystack:
                        store = str(candidate)
                        break
            total_sales, total_pieces, source_line = _extract_sales_totals(text)
            record.update({
                "store": store, "stores": 1 if store else 0,
                "rows": 1 if text.strip() else 0,
                "total_sales": max(float(total_sales or 0), 0.0),
                "total_pieces": max(float(total_pieces or 0), 0.0),
                "source_line": source_line[:300],
            })
            if not text.strip():
                record["status"] = "PDF sin texto legible"
            elif total_sales > 0:
                record["status"] = "Procesado"
            else:
                record["status"] = "Procesado · total de venta no detectado"
        except Exception as exc:
            record.update({"status": f"Error: {type(exc).__name__}", "error": str(exc)})
        return record

    m.parse_sales_pdf = parse_sales_pdf_v109

    # 2) Metas mensuales de venta persistentes.
    with m.db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sales_goals(
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                store TEXT NOT NULL DEFAULT 'Compañía',
                target REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY(year, month, store)
            )
        """)

    def canon_scope(store):
        value = str(store or "Compañía").strip() or "Compañía"
        return "Compañía" if _norm(value) in {"COMPANIA", "COMPANY"} else value

    def repair_entry(entry):
        item = dict(entry or {})
        if int(item.get("parser_version") or 0) >= PARSER_VERSION:
            return item
        try:
            path = m.resolve_entry_path(item)
            if not path.exists() or path.suffix.lower() != ".pdf":
                return item
            year = int(item.get("year") or 0); month = int(item.get("month") or 0)
            if not year or month not in range(1, 13):
                return item
            parsed = parse_sales_pdf_v109(path, year, month)
            changes = {
                "status": parsed.get("status", ""), "year": year, "month": month,
                "store": parsed.get("store", ""), "rows": parsed.get("rows", 0),
                "stores": parsed.get("stores", 0), "pages": parsed.get("pages", 0),
                "total_pieces": parsed.get("total_pieces", 0), "total_sales": parsed.get("total_sales", 0),
                "parser_version": PARSER_VERSION, "source_line": parsed.get("source_line", ""),
            }
            m.update_entry("sales", str(item.get("id") or ""), **changes)
            item.update(changes)
            try:
                m.save_sales_pdf_snapshot(str(item.get("id") or ""), parsed)
            except Exception:
                pass
        except Exception as exc:
            print(f"[V109-SALES] reparo {item.get('name','')}: {type(exc).__name__}: {exc}", flush=True)
        return item

    def sales_entries():
        result = []
        for entry in list((m.load_manifest() or {}).get("sales") or []):
            item = dict(entry)
            if Path(str(item.get("name") or item.get("path") or "")).suffix.lower() != ".pdf":
                continue
            if int(item.get("year") or 0) <= 0 or int(item.get("month") or 0) not in range(1, 13):
                continue
            if int(item.get("parser_version") or 0) < PARSER_VERSION:
                item = repair_entry(item)
            result.append(item)
        return result

    def latest_month_values(year, scope):
        grouped = {}
        for e in sales_entries():
            if int(e.get("year") or 0) != int(year):
                continue
            month = int(e.get("month") or 0)
            store = canon_scope(e.get("store") or "Compañía")
            key = (month, store)
            previous = grouped.get(key)
            if previous is None or str(e.get("uploaded_at") or "") >= str(previous.get("uploaded_at") or ""):
                grouped[key] = e
        out = {}
        for month in range(1, 13):
            if scope != "Compañía":
                matches = [e for (mo, st), e in grouped.items() if mo == month and _norm(st) == _norm(scope)]
                chosen = max(matches, key=lambda x: str(x.get("uploaded_at") or ""), default=None)
                values = [chosen] if chosen else []
            else:
                company = [e for (mo, st), e in grouped.items() if mo == month and st == "Compañía"]
                if company:
                    values = [max(company, key=lambda x: str(x.get("uploaded_at") or ""))]
                else:
                    values = [e for (mo, st), e in grouped.items() if mo == month and st != "Compañía"]
            valid = [e for e in values if e and float(e.get("total_sales") or 0) > 0]
            out[month] = {
                "sales": sum(max(float((e or {}).get("total_sales") or 0), 0.0) for e in values if e),
                "pieces": sum(max(float((e or {}).get("total_pieces") or 0), 0.0) for e in values if e),
                "sources": len(valid),
                "files": [str(e.get("name") or "") for e in valid],
                "last_upload": max([str(e.get("uploaded_at") or "") for e in valid] or [""]),
            }
        return out

    async def sales_summary(request, year: int | None = None, through_month: int | None = None, store: str = "Compañía"):
        user = m.require_user(request)
        now = datetime.now(); selected_year = int(year or now.year); cut = max(1, min(12, int(through_month or now.month)))
        try:
            scope = m.effective_store(user, store)
        except Exception:
            scope = store
        scope = canon_scope(scope)
        current = latest_month_values(selected_year, scope)
        previous = latest_month_values(selected_year - 1, scope)
        with m.db() as con:
            rows = con.execute(
                "SELECT month,target,updated_at,updated_by FROM sales_goals WHERE year=? AND store=? ORDER BY month",
                (selected_year, scope),
            ).fetchall()
            goals = {int(r["month"]): float(r["target"] or 0) for r in rows}
        labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        months = []
        for mo in range(1, 13):
            goal = float(goals.get(mo, 0)); cur = float(current.get(mo, {}).get("sales") or 0); prev = float(previous.get(mo, {}).get("sales") or 0)
            months.append({
                "month": mo, "label": labels[mo-1], "target": goal, "current": cur, "previous": prev,
                "pieces": float(current.get(mo, {}).get("pieces") or 0),
                "previous_pieces": float(previous.get(mo, {}).get("pieces") or 0),
                "compliance": cur/goal*100 if goal else None,
                "growth": (cur/prev-1)*100 if prev else None,
                "sources": int(current.get(mo, {}).get("sources") or 0),
                "last_upload": current.get(mo, {}).get("last_upload") or "",
                "files": current.get(mo, {}).get("files") or [],
            })
        goal_ytd = sum(x["target"] for x in months if x["month"] <= cut)
        current_ytd = sum(x["current"] for x in months if x["month"] <= cut)
        previous_ytd = sum(x["previous"] for x in months if x["month"] <= cut)
        source_count = sum(x["sources"] for x in months if x["month"] <= cut)
        last_upload = max([x["last_upload"] for x in months if x["last_upload"]] or [""])
        role = str(user.get("real_role") or user.get("role") or "") if hasattr(user, "get") else str(user["role"] or "")
        years = sorted({int(e.get("year") or 0) for e in sales_entries() if int(e.get("year") or 0) > 0} | {selected_year, selected_year-1}, reverse=True)
        return {
            "year": selected_year, "previous_year": selected_year-1, "through_month": cut, "store": scope,
            "months": months,
            "totals": {
                "goal_ytd": goal_ytd, "current_ytd": current_ytd, "previous_ytd": previous_ytd,
                "compliance_pct": current_ytd/goal_ytd*100 if goal_ytd else None,
                "growth_pct": (current_ytd/previous_ytd-1)*100 if previous_ytd else None,
                "gap_to_goal": current_ytd-goal_ytd if goal_ytd else None,
            },
            "source_count": source_count, "last_upload": last_upload, "available_years": years,
            "editable": role in ("superadmin","admin"),
            "has_sales": any(x["current"] > 0 or x["previous"] > 0 for x in months),
            "parser_version": PARSER_VERSION,
        }

    async def save_sales_goals(request):
        user = m.require_user(request, ("superadmin","admin")); body = await request.json()
        year = int(body.get("year") or datetime.now().year); store = canon_scope(body.get("store") or "Compañía"); values = body.get("values") or {}
        now_text = datetime.now().astimezone().isoformat(timespec="seconds")
        username = str(user.get("username") if hasattr(user,"get") else user["username"]); changed = 0
        with m.db() as con:
            for month in range(1,13):
                try: target = max(float(values.get(str(month), values.get(month, 0)) or 0), 0.0)
                except Exception: target = 0.0
                old = con.execute("SELECT target FROM sales_goals WHERE year=? AND month=? AND store=?", (year,month,store)).fetchone()
                if old is None or abs(float(old["target"] or 0)-target) > .005: changed += 1
                con.execute("""INSERT INTO sales_goals(year,month,store,target,updated_at,updated_by) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(year,month,store) DO UPDATE SET target=excluded.target,updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
                    (year,month,store,target,now_text,username))
        return {"ok":True,"changed":changed,"year":year,"store":store}

    m.app.add_api_route("/api/commercial-sales-summary", sales_summary, methods=["GET"])
    m.app.add_api_route("/api/commercial-sales-goals", save_sales_goals, methods=["POST"])

    # 3) Inserción visual en Macro y reparación de ambos botones de ventas.
    index_path = Path(m.WEB) / "index.html"
    try:
        html = index_path.read_text(encoding="utf-8")
        if 'id="v109-sales-exec"' not in html:
            block = r'''<div id="v109-sales-exec" class="sales-exec">
<div class="sales-exec-head"><div><div class="title sales-exec-title">Ventas · Año vs año pasado</div><div class="subtitle" id="salesExecSource">Fuente: PDF de ventas mensuales</div></div><div class="sales-exec-controls"><label>Año<select id="salesExecYear"></select></label><label>Corte hasta<select id="salesExecThrough"><option value="1">Enero</option><option value="2">Febrero</option><option value="3">Marzo</option><option value="4">Abril</option><option value="5">Mayo</option><option value="6">Junio</option><option value="7">Julio</option><option value="8">Agosto</option><option value="9">Septiembre</option><option value="10">Octubre</option><option value="11">Noviembre</option><option value="12">Diciembre</option></select></label><button class="owner-action hidden" id="salesGoalsToggle" type="button">Editar metas</button></div></div>
<div class="sales-kpi-grid" id="salesExecKpis"></div><div class="sales-empty hidden" id="salesExecEmpty">Aún no hay venta mensual procesada para este corte. Carga los PDF de ventas en Carga de datos.</div>
<div class="sales-chart-card"><div class="sales-chart-head"><b id="salesChartTitle">Evolución mensual</b><span id="salesCoverage"></span></div><div class="sales-legend"><span><i class="cur"></i>Venta año</span><span><i class="prev"></i>Venta año pasado</span><span><i class="goal"></i>Meta</span></div><div class="sales-chart-scroll"><div id="salesExecChart"></div></div></div>
<div class="sales-goal-editor hidden" id="salesGoalEditor"><div class="sales-goal-editor-head"><b>Metas mensuales de venta</b><span>Importes en pesos · se guardan por año y alcance</span></div><div class="sales-goal-inputs" id="salesGoalInputs"></div><div class="sales-goal-actions"><button class="primary" id="saveSalesGoals" type="button">Guardar metas</button><span id="salesGoalMsg"></span></div></div>
<div class="tablewrap sales-month-table"><table class="table"><thead><tr><th>Mes</th><th>Meta</th><th id="salesYearTh">Venta año</th><th id="salesPrevTh">Año pasado</th><th>Cumplimiento</th><th>Crecimiento</th><th>Venta pzas</th><th>PDF</th></tr></thead><tbody id="salesExecRows"></tbody></table></div></div>'''
            anchor = '<div class="title">Macro sección</div><div class="cards" id="sectionSummary">'
            if anchor in html:
                html = html.replace(anchor, block + anchor, 1)
            else:
                hit = re.search(r'(<div class="title">Macro sección</div>)', html)
                if not hit: raise RuntimeError("No se encontró Macro sección")
                html = html[:hit.start()] + block + html[hit.start():]

            css = r'''<style id="v109-sales-css">
.sales-exec{margin:14px 0 18px;background:linear-gradient(180deg,#fff,#fbfdff);border:1px solid var(--line);border-radius:15px;padding:14px}.sales-exec-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}.sales-exec-title{margin:0 0 4px!important}.sales-exec-controls{display:flex;gap:7px;align-items:flex-end;flex-wrap:wrap}.sales-exec-controls label{font-size:7px;font-weight:950;text-transform:uppercase;color:var(--muted)}.sales-exec-controls select{display:block;margin-top:4px;min-height:32px;border:1px solid #cfdae7;border-radius:8px;background:#fff;color:var(--text);padding:5px 25px 5px 8px;font-size:9px;font-weight:800}.sales-kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:12px 0}.sales-kpi{background:#fff;border:1px solid #dfe7f0;border-radius:12px;padding:11px 12px;min-height:88px;position:relative;overflow:hidden}.sales-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--sk,#1769e8)}.sales-kpi .sl{font-size:7px;color:var(--muted);font-weight:950;text-transform:uppercase}.sales-kpi .sv{font-size:20px;font-weight:1000;margin:7px 0 3px;color:var(--navy)}.sales-kpi .ss{font-size:7.5px;color:var(--muted);line-height:1.3}.sales-chart-card{background:#fff;border:1px solid #e1e8f0;border-radius:12px;padding:12px;margin:10px 0}.sales-chart-head{display:flex;justify-content:space-between;gap:10px;align-items:center;color:var(--navy);font-size:10px}.sales-chart-head span{font-size:7px;color:var(--muted)}.sales-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:7px;color:var(--muted);margin:8px 0}.sales-legend span{display:flex;gap:5px;align-items:center}.sales-legend i{display:inline-block;width:11px;height:6px;border-radius:2px}.sales-legend .cur{background:#1769e8}.sales-legend .prev{background:#9fb0c6}.sales-legend .goal{height:2px;background:#ec007c}.sales-chart-scroll{overflow-x:auto}.sales-chart-scroll svg{min-width:760px;display:block;width:100%;height:auto}.sales-empty{border:1px dashed #e0a7c7;background:#fff7fb;color:#8b3867;border-radius:10px;padding:12px;font-size:9px;margin:9px 0}.sales-goal-editor{background:#f6f9fd;border:1px solid #d9e3ef;border-radius:12px;padding:11px;margin:10px 0}.sales-goal-editor-head{display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:9px}.sales-goal-editor-head span{font-size:7px;color:var(--muted)}.sales-goal-inputs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;margin-top:9px}.sales-goal-inputs label{font-size:7px;color:var(--muted);font-weight:900}.sales-goal-inputs input{width:100%;margin-top:3px;border:1px solid #ced9e6;border-radius:7px;padding:7px;font-size:8px;color:var(--text);background:#fff}.sales-goal-actions{display:flex;gap:9px;align-items:center;margin-top:9px}.sales-goal-actions span{font-size:8px}.sales-month-table{margin-top:10px}.sales-month-table .table{min-width:860px}.sales-pos{color:var(--green)!important;font-weight:900}.sales-mid{color:var(--yellow)!important;font-weight:900}.sales-neg{color:var(--red)!important;font-weight:900}@media(max-width:900px){.sales-exec{padding:9px}.sales-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sales-goal-inputs{grid-template-columns:repeat(2,minmax(0,1fr))}.sales-exec-controls{width:100%}.sales-exec-controls label{flex:1}.sales-exec-controls select{width:100%}}
</style>'''
            js = r'''<script id="v109-sales-js">
(function(){
const months=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];let lastSalesPayload=null;
const money=v=>'$'+Math.round(Number(v||0)).toLocaleString('es-MX');const shortMoney=v=>{const n=Number(v||0),a=Math.abs(n);return a>=1e6?'$'+(n/1e6).toFixed(a>=1e7?0:1)+'M':a>=1e3?'$'+(n/1e3).toFixed(a>=1e5?0:1)+'k':'$'+Math.round(n)};const per=v=>v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toFixed(1)+'%';
function tone(v,k){if(v===null||v===undefined||!Number.isFinite(Number(v)))return'';const n=Number(v);return k==='c'?n>=100?'sales-pos':n>=90?'sales-mid':'sales-neg':n>=0?'sales-pos':'sales-neg'}
function scope(){try{if(typeof DASH!=='undefined'&&DASH&&DASH.selected_store)return DASH.selected_store}catch(e){}return document.getElementById('store')?.value||'Compañía'}
function cutDefault(){const n=new Date();try{const w=document.getElementById('week')?.value||'';let x=String(w).match(/^(\d{4})-W(\d{1,2})$/);if(x){const y=+x[1],wk=+x[2],d=new Date(Date.UTC(y,0,4)),day=d.getUTCDay()||7;d.setUTCDate(d.getUTCDate()-day+1+(wk-1)*7);return{year:y,month:d.getUTCMonth()+1}}x=String(w).match(/^(\d{4})-(\d{2})$/);if(x)return{year:+x[1],month:+x[2]}}catch(e){}return{year:n.getFullYear(),month:n.getMonth()+1}}
async function json(url,opt){const r=await fetch(url,{credentials:'same-origin',...(opt||{})});let d={};try{d=await r.json()}catch(e){}if(!r.ok)throw Error(d.detail||d.message||('HTTP '+r.status));return d}
function kpi(l,v,s,c,cl=''){return`<div class="sales-kpi" style="--sk:${c}"><div class="sl">${l}</div><div class="sv ${cl}">${v}</div><div class="ss">${s||''}</div></div>`}
function chart(d){const h=document.getElementById('salesExecChart');if(!h)return;const rows=d.months||[],W=980,H=310,L=72,R=18,T=18,B=42,pw=W-L-R,ph=H-T-B,vals=[];rows.forEach(r=>vals.push(+r.current||0,+r.previous||0,+r.target||0));const mx=Math.max(1,...vals)*1.12,y=v=>T+ph-(+v||0)/mx*ph,gw=pw/12,bw=Math.min(20,gw*.28);let s=`<svg viewBox="0 0 ${W} ${H}">`;for(let q=0;q<=4;q++){const v=mx*q/4,yy=y(v);s+=`<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" stroke="#dce4ee"/><text x="${L-7}" y="${yy+3}" text-anchor="end" font-size="8" fill="#6b778c">${shortMoney(v)}</text>`}let pts=[];rows.forEach((r,i)=>{const cx=L+gw*(i+.5),a=+r.current||0,b=+r.previous||0,g=+r.target||0,y0=y(0),ya=y(a),yb=y(b);s+=`<rect x="${cx-bw-2}" y="${ya}" width="${bw}" height="${Math.max(0,y0-ya)}" rx="3" fill="#1769e8"><title>${r.label} ${d.year}: ${money(a)}</title></rect><rect x="${cx+2}" y="${yb}" width="${bw}" height="${Math.max(0,y0-yb)}" rx="3" fill="#9fb0c6"><title>${r.label} ${d.previous_year}: ${money(b)}</title></rect><text x="${cx}" y="${H-18}" text-anchor="middle" font-size="8" fill="#52657d">${r.label}</text>`;if(g>0)pts.push(`${cx},${y(g)}`)});if(pts.length>1)s+=`<polyline points="${pts.join(' ')}" fill="none" stroke="#ec007c" stroke-width="2.2"/>`;rows.forEach((r,i)=>{if(+r.target>0){const cx=L+gw*(i+.5);s+=`<circle cx="${cx}" cy="${y(r.target)}" r="2.8" fill="#ec007c"><title>Meta ${r.label}: ${money(r.target)}</title></circle>`}});h.innerHTML=s+'</svg>'}
function goals(d){const b=document.getElementById('salesGoalInputs');if(b)b.innerHTML=(d.months||[]).map(r=>`<label>${r.label}<input type="number" min="0" step="1000" data-sales-goal="${r.month}" value="${Math.round(+r.target||0)}"></label>`).join('')}
async function loadSalesExecutive(forceYear,forceMonth){const root=document.getElementById('v109-sales-exec');if(!root)return;const def=cutDefault(),ys=document.getElementById('salesExecYear'),ms=document.getElementById('salesExecThrough'),year=+(forceYear||ys?.value||def.year),cut=+(forceMonth||ms?.value||def.month);try{const d=await json(`/api/commercial-sales-summary?year=${year}&through_month=${cut}&store=${encodeURIComponent(scope())}`);lastSalesPayload=d;if(ys){let yy=[...(d.available_years||[])];if(!yy.includes(d.year))yy.push(d.year);ys.innerHTML=yy.sort((a,b)=>b-a).map(y=>`<option value="${y}" ${+y===+d.year?'selected':''}>${y}</option>`).join('')}if(ms)ms.value=String(d.through_month);document.getElementById('salesGoalsToggle')?.classList.toggle('hidden',!d.editable);const t=d.totals||{},gap=t.gap_to_goal;document.getElementById('salesExecKpis').innerHTML=kpi('Meta acumulada',money(t.goal_ytd),gap===null?'Configura metas mensuales':gap>=0?'Meta superada por '+money(gap):'Brecha '+money(Math.abs(gap)),'#ec007c')+kpi('Venta '+d.year,money(t.current_ytd),'Acumulado hasta '+months[d.through_month-1],'#1769e8')+kpi('Venta '+d.previous_year,money(t.previous_ytd),'Mismo corte del año pasado','#9fb0c6')+kpi('Cumplimiento',per(t.compliance_pct),'Venta / Meta','#10b981',tone(t.compliance_pct,'c'))+kpi('Crecimiento',per(t.growth_pct),d.year+' vs '+d.previous_year,'#f59e0b',tone(t.growth_pct,'g'));document.getElementById('salesExecEmpty')?.classList.toggle('hidden',!!d.has_sales);document.getElementById('salesChartTitle').textContent=`Venta mensual ${d.year} vs ${d.previous_year} · ${d.store}`;document.getElementById('salesCoverage').textContent=`${d.source_count||0} PDF válidos · ${d.last_upload?'última carga '+String(d.last_upload).slice(0,16).replace('T',' '):'sin carga'}`;document.getElementById('salesExecSource').textContent='Fuente: PDF de ventas mensuales · alcance '+d.store;document.getElementById('salesYearTh').textContent='Venta '+d.year;document.getElementById('salesPrevTh').textContent='Venta '+d.previous_year;document.getElementById('salesExecRows').innerHTML=(d.months||[]).map(r=>`<tr><td><b>${r.label}</b></td><td>${r.target?money(r.target):'—'}</td><td><b>${money(r.current)}</b></td><td>${money(r.previous)}</td><td class="${tone(r.compliance,'c')}">${per(r.compliance)}</td><td class="${tone(r.growth,'g')}">${per(r.growth)}</td><td>${Math.round(+r.pieces||0).toLocaleString('es-MX')}</td><td>${r.sources?r.sources+' ✓':'—'}</td></tr>`).join('');chart(d);goals(d)}catch(e){document.getElementById('salesExecKpis').innerHTML=kpi('Ventas','Sin información',e.message,'#ef4444');console.warn('[V109]',e)}}window.loadSalesExecutive=loadSalesExecutive;
document.getElementById('salesExecYear')?.addEventListener('change',()=>loadSalesExecutive());document.getElementById('salesExecThrough')?.addEventListener('change',()=>loadSalesExecutive());document.getElementById('store')?.addEventListener('change',()=>setTimeout(()=>loadSalesExecutive(),250));document.getElementById('week')?.addEventListener('change',()=>{const d=cutDefault();loadSalesExecutive(d.year,d.month)});document.getElementById('salesGoalsToggle')?.addEventListener('click',()=>document.getElementById('salesGoalEditor')?.classList.toggle('hidden'));
document.getElementById('saveSalesGoals')?.addEventListener('click',async()=>{if(!lastSalesPayload)return;const values={};document.querySelectorAll('[data-sales-goal]').forEach(i=>values[i.dataset.salesGoal]=+i.value||0);const b=document.getElementById('saveSalesGoals'),msg=document.getElementById('salesGoalMsg');b.disabled=true;b.textContent='Guardando...';try{const r=await json('/api/commercial-sales-goals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({year:lastSalesPayload.year,store:lastSalesPayload.store,values})});if(msg){msg.className='sales-pos';msg.textContent='✓ Guardado · '+(r.changed||0)+' cambios'}await loadSalesExecutive()}catch(e){if(msg){msg.className='sales-neg';msg.textContent='Error: '+e.message}}finally{b.disabled=false;b.textContent='Guardar metas'}});
function msg(t,a){const n=document.getElementById(a?'analysisUploadLog':'log');if(n)n.textContent=t}async function process(inputId,yearId,monthId,buttonId,a){const input=document.getElementById(inputId),fs=Array.from(input?.files||[]);if(!fs.length)return msg('Selecciona uno o más PDF de ventas mensuales.',a);const year=+document.getElementById(yearId)?.value||new Date().getFullYear(),month=+document.getElementById(monthId)?.value||new Date().getMonth()+1;if(month<1||month>12)return msg('Selecciona un mes válido.',a);const b=document.getElementById(buttonId),old=b?.textContent||'Procesar';if(b){b.disabled=true;b.textContent='Procesando PDF...'}msg(`Procesando ${fs.length} PDF · ${year}-${String(month).padStart(2,'0')}...`,a);try{const fd=new FormData();fs.forEach(f=>fd.append('files',f,f.name));fd.append('year',year);fd.append('month',month);const r=await json('/api/upload/sales-pdfs',{method:'POST',body:fd}),rr=r.results||[],ok=rr.filter(x=>x.ok).length,det=rr.filter(x=>+x.total_sales>0).length,detail=rr.map(x=>`${x.ok?'✓':'✗'} ${x.file||''} · ${x.store||'Compañía'} · ${x.status||''}${+x.total_sales>0?' · '+money(x.total_sales):''}${x.error?' · '+x.error:''}`).join('\n');msg(`Carga terminada: ${ok}/${rr.length} PDF procesados · ${det} con venta detectada.\n${detail}`,a);input.value='';const sn=document.getElementById(a?'analysisSalesSelection':'salesSelection');if(sn)sn.textContent='Ningún PDF seleccionado';try{if(typeof window.loadDash==='function')await window.loadDash()}catch(e){}await loadSalesExecutive(year,month);try{if(typeof window.loadUploadHistories==='function')await window.loadUploadHistories()}catch(e){}}catch(e){msg('Error procesando PDF de ventas: '+e.message,a)}finally{if(b){b.disabled=false;b.textContent=old}}}
function bind(){const a=document.getElementById('uploadSales');if(a&&!a.dataset.v109){a.dataset.v109='1';a.onclick=()=>process('salesFiles','salesYear','salesMonth','uploadSales',false);document.getElementById('salesFiles')?.addEventListener('change',e=>{const fs=Array.from(e.target.files||[]),n=document.getElementById('salesSelection');if(n)n.textContent=fs.length?fs.length+' PDF seleccionado'+(fs.length===1?'':'s'):'Ningún PDF seleccionado'})}const b=document.getElementById('analysisSalesUploadBtn');if(b&&!b.dataset.v109){b.dataset.v109='1';b.onclick=()=>process('analysisSalesFiles','analysisSalesYear','analysisSalesMonth','analysisSalesUploadBtn',true)}}bind();const macro=document.getElementById('page-macro');if(macro){let timer;new MutationObserver(()=>{if(macro.classList.contains('active')){clearTimeout(timer);timer=setTimeout(()=>loadSalesExecutive(),120)}}).observe(macro,{attributes:true,attributeFilter:['class']})}setTimeout(()=>loadSalesExecutive(),800);console.log('[V109] Macro Ventas + carga PDF mensual activa');
})();</script>'''
            html = html.replace("</head>", css + "\n</head>", 1).replace("</body>", js + "\n</body>", 1)
            index_path.write_text(html, encoding="utf-8")
            print("[V109-UI] Reporte ejecutivo de Ventas insertado en Macro.", flush=True)
    except Exception as exc:
        print(f"[V109-UI] ERROR: {type(exc).__name__}: {exc}", flush=True)

    @m.app.on_event("startup")
    def v109_startup():
        def worker():
            time.sleep(4)
            try:
                entries = list((m.load_manifest() or {}).get("sales") or [])
                pdfs = [e for e in entries if str(e.get("name") or "").lower().endswith(".pdf")]
                pending = [e for e in pdfs if int(e.get("parser_version") or 0) < PARSER_VERSION]
                print(f"[V109-SALES] listo · PDF ventas={len(pdfs)} · pendientes de reparo={len(pending)} · parser={PARSER_VERSION}", flush=True)
            except Exception as exc:
                print(f"[V109-SALES] autodiagnóstico: {type(exc).__name__}: {exc}", flush=True)
        threading.Thread(target=worker, daemon=True, name="v109-sales-check").start()

    m._V109_MACRO_SALES = True
    print("[V109] Ventas Macro + metas + PDF mensual + botón Procesar instalados.", flush=True)
