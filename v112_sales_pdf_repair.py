"""V112: reparación integral de Ventas mensuales en Análisis Comercial.

Corrige tres fallas observadas en producción:
1) /api/commercial-sales-summary respondía 422 porque el `request` de la ruta
   dinámica V109 no estaba tipado como Request y FastAPI lo interpretaba como
   parámetro obligatorio de query.
2) El selector "Corte hasta" arrancaba en Enero porque tomaba el primer option
   antes de aplicar el mes del periodo vigente.
3) PDF multipágina / exportados de BI podían traer la etiqueta y el importe en
   posiciones distintas o una página por tienda; V109 sólo buscaba una cifra en
   la misma línea y asignaba el PDF completo a la primera tienda detectada.

V112 reconstruye renglones por coordenadas, analiza cada página por separado,
consolida por tienda cuando un PDF contiene varias sucursales y, si el PDF no
expone un total mensual legible, usa únicamente el Excel de capacidades del
MISMO mes como respaldo (columna `Venta $ mes` / `Venta pzas`). Nunca usa un
mes distinto para rellenar datos.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import inspect
import math
import re
import threading
import time
import unicodedata

PARSER_VERSION = 112


def _norm(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    return re.sub(r"\s+", " ", text).strip()


def _num(raw) -> float:
    text = re.sub(r"[^0-9,.-]", "", str(raw or "")).strip()
    if not text or text in {"-", ".", ","}:
        return 0.0
    try:
        if "," in text and "." in text:
            # Formato habitual MX: 1,234,567.89
            if text.rfind(".") > text.rfind(","):
                text = text.replace(",", "")
            else:
                text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            parts = text.split(",")
            if len(parts) > 1 and all(len(x) == 3 for x in parts[1:]):
                text = "".join(parts)
            else:
                text = text.replace(",", ".")
        value = float(text)
        return value if math.isfinite(value) else 0.0
    except Exception:
        return 0.0


def _numbers(text: str):
    out = []
    for token in re.findall(r"\$?\s*-?\d[\d,.]*(?:\.\d+)?", str(text or "")):
        value = _num(token)
        if value > 0 and not (2020 <= value <= 2100 and "$" not in token):
            out.append((token.strip(), value))
    return out


def _visual_rows(words, tolerance=3.2):
    """Reconstruye renglones visuales cuando extract_text separa etiqueta/valor."""
    rows = []
    for word in sorted(words or [], key=lambda w: (float(w.get("top", 0)), float(w.get("x0", 0)))):
        text = str(word.get("text") or "").strip()
        if not text:
            continue
        top = float(word.get("top", 0))
        target = None
        for row in rows[-5:]:
            if abs(row["top"] - top) <= tolerance:
                target = row
                break
        if target is None:
            target = {"top": top, "words": []}
            rows.append(target)
        target["words"].append(word)
    output = []
    for row in rows:
        ordered = sorted(row["words"], key=lambda w: float(w.get("x0", 0)))
        line = " ".join(str(w.get("text") or "").strip() for w in ordered if str(w.get("text") or "").strip())
        if line:
            output.append(line)
    return output


def _score_sale_line(raw: str):
    line = _norm(raw)
    if not ("VENTA" in line or re.search(r"\bVTA\b", line)):
        return None
    if any(bad in line for bad in ("UTILIDAD", "COSTO", "PRECIO", "EXISTENCIA", "INVENTARIO", "DDI", "CAPACIDAD")):
        return None
    is_pieces = any(k in line for k in ("PZAS", "PZA", "PIEZAS", "UNIDADES", "UDS"))
    is_money = ("$" in raw or any(k in line for k in ("PESOS", "IMPORTE", "MONTO", "VENTA $", "VTA $", "EN $")))
    score = 10
    if "ACUM" in line: score += 18
    if "MES" in line or "MENSUAL" in line: score += 15
    if "TOTAL" in line or "GENERAL" in line: score += 18
    if "NETA" in line or "NETAS" in line: score += 8
    if "ACTUAL" in line or "REAL" in line: score += 5
    if " 7" in line or line.endswith(" 7"): score -= 14
    if " 30" in line or line.endswith(" 30"): score -= 5
    if "META" in line and not any(k in line for k in ("REAL", "ACTUAL")): score -= 22
    return score, is_money, is_pieces


def _extract_page_metrics(raw_text: str, visual_lines: list[str]):
    """Devuelve la mejor venta mensual y piezas de una página."""
    # Unificar texto normal y reconstrucción por posición, sin duplicar líneas.
    lines = []
    seen = set()
    for source in (str(raw_text or "").splitlines(), visual_lines or []):
        for raw in source:
            clean = re.sub(r"\s+", " ", str(raw or "")).strip()
            key = _norm(clean)
            if clean and key not in seen:
                seen.add(key); lines.append(clean)

    money = []
    pieces = []
    goal = []

    for i, raw in enumerate(lines):
        scored = _score_sale_line(raw)
        line = _norm(raw)
        vals = _numbers(raw)
        if scored:
            score, is_money, is_pieces = scored
            # Cuando el encabezado y su valor quedaron en líneas consecutivas,
            # revisar hasta dos renglones posteriores con una penalización leve.
            candidates = [(raw, vals, score)]
            if not vals:
                for jump in (1, 2):
                    if i + jump >= len(lines):
                        break
                    nxt = lines[i+jump]
                    nvals = _numbers(nxt)
                    if nvals:
                        candidates.append((f"{raw} -> {nxt}", nvals, score - jump*3))
            for source_line, nvals, base in candidates:
                for token, value in nvals:
                    if is_pieces:
                        pieces.append((base + 8, value, source_line))
                    # Si dice PZAS sin signo $, no tratar la misma cifra como pesos.
                    if is_money or (not is_pieces and value >= 1000):
                        mscore = base + (10 if "$" in token or "$" in source_line else 0)
                        money.append((mscore, value, source_line))

        # Meta separada de Venta. Se conserva para diagnóstico; no se usa como
        # venta real, evitando inflar el reporte con objetivos.
        if "META" in line and vals and not ("VENTA REAL" in line or "VENTA ACTUAL" in line):
            for _, value in vals:
                if value >= 1000:
                    goal.append((10 + (8 if "$" in raw else 0), value, raw))

    # Patrones que toleran salto de línea entre etiqueta y valor.
    joined = "\n".join(lines)
    norm_joined = _norm(joined.replace("\n", " \n "))
    patterns_money = (
        r"VTA\s+ACUM(?:ULADA)?\s+MES\s+EN\s+\$\s*[:\-]?\s*\$?\s*([\d,.]+)",
        r"VENTA\s+ACUM(?:ULADA)?\s+(?:DEL\s+)?MES\s*(?:EN\s+\$|EN\s+PESOS)?\s*[:\-]?\s*\$?\s*([\d,.]+)",
        r"(?:VENTA|VTA)\s+(?:NETA|TOTAL|REAL|ACTUAL)\s*(?:MES|MENSUAL)?\s*[:\-]?\s*\$?\s*([\d,.]+)",
        r"TOTAL\s+(?:DE\s+)?VENTA\s*[:\-]?\s*\$?\s*([\d,.]+)",
    )
    for pat in patterns_money:
        for mt in re.finditer(pat, norm_joined, re.I):
            value = _num(mt.group(1))
            if value > 0 and not (2020 <= value <= 2100):
                money.append((70, value, mt.group(0)))

    patterns_pieces = (
        r"VTA\s+ACUM(?:ULADA)?\s+MES\s+EN\s+(?:PZAS|PIEZAS)\s*[:\-]?\s*([\d,.]+)",
        r"VENTA\s+(?:DEL\s+)?MES\s+EN\s+(?:PZAS|PIEZAS)\s*[:\-]?\s*([\d,.]+)",
    )
    for pat in patterns_pieces:
        for mt in re.finditer(pat, norm_joined, re.I):
            value = _num(mt.group(1))
            if value > 0 and not (2020 <= value <= 2100):
                pieces.append((70, value, mt.group(0)))

    def choose(values):
        if not values:
            return 0.0, "", 0
        best = max(values, key=lambda x: (x[0], x[1]))
        return float(best[1]), str(best[2]), int(best[0])

    sales, source, sale_score = choose(money)
    pzs, psource, pscore = choose(pieces)
    meta, msource, _ = choose(goal)
    return {
        "sales": sales, "pieces": pzs, "goal": meta,
        "source": source, "piece_source": psource, "goal_source": msource,
        "score": sale_score, "piece_score": pscore,
        "candidate_lines": [x for x in lines if ("VENTA" in _norm(x) or re.search(r"\bVTA\b", _norm(x)) or "META" in _norm(x))][:18],
    }


def _stores_in_text(text: str, available: list[str]):
    haystack = _norm(text)
    found = []
    for store in sorted(available, key=lambda x: len(_norm(x)), reverse=True):
        key = _norm(store)
        if key and re.search(rf"(?<![A-Z0-9]){re.escape(key)}(?![A-Z0-9])", haystack):
            found.append(str(store))
    return found


def _capacity_month_fallback(m, year: int, month: int, store: str):
    """Usa capacidades sólo si la versión corresponde exactamente al mes pedido."""
    period = f"{int(year):04d}-{int(month):02d}"
    try:
        entry = m._capacity_source_entry(period)
        if not entry:
            return 0.0, 0.0, ""
        report_date = m._capacity_report_date(entry)
        if f"{report_date.year:04d}-{report_date.month:02d}" != period:
            return 0.0, 0.0, ""
        frame = m._capacity_frame_for_period(period)
        if frame is None or frame.empty:
            return 0.0, 0.0, ""
        working = frame
        scope = str(store or "Compañía").strip()
        if _norm(scope) not in {"COMPANIA", "COMPANY", ""} and "Tienda" in working.columns:
            mask = working["Tienda"].astype(str).map(_norm) == _norm(scope)
            working = working.loc[mask]
        if working.empty:
            return 0.0, 0.0, ""
        sales_col = "Venta $ mes" if "Venta $ mes" in working.columns else ""
        pieces_col = "Venta pzas" if "Venta pzas" in working.columns else ("Venta pzas 30" if "Venta pzas 30" in working.columns else "")
        sales = float(m.pd.to_numeric(working[sales_col], errors="coerce").fillna(0).clip(lower=0).sum()) if sales_col else 0.0
        pieces = float(m.pd.to_numeric(working[pieces_col], errors="coerce").fillna(0).clip(lower=0).sum()) if pieces_col else 0.0
        source = f"Excel capacidades {entry.get('name') or ''}".strip()
        return sales, pieces, source
    except Exception as exc:
        print(f"[V112-SALES] fallback capacidades {period}: {type(exc).__name__}: {exc}", flush=True)
        return 0.0, 0.0, ""


def install(m):
    if getattr(m, "_V112_SALES_REPAIR", False):
        return

    try:
        available_stores = list(m.store_names(True) or [])
    except Exception:
        available_stores = list(getattr(m, "PROJECT_STORES", []) or [])

    def parse_sales_pdf_v112(path: str | Path, year: int | None = None, month: int | None = None) -> dict:
        path = Path(path)
        y = int(year or 0); mo = int(month or 0)
        record = {
            "file": path.name, "year": y, "month": mo, "rows": 0,
            "store": "", "stores": 0, "pages": 0,
            "total_pieces": 0.0, "total_sales": 0.0, "total_goal": 0.0,
            "status": "Sin información útil", "parser_version": PARSER_VERSION,
            "source_method": "", "source_line": "", "detected_stores": [],
        }
        try:
            import pdfplumber
            page_records = []
            all_text = []
            with pdfplumber.open(path) as pdf:
                record["pages"] = len(pdf.pages)
                for page_no, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    except TypeError:
                        text = page.extract_text() or ""
                    visual = []
                    try:
                        visual = _visual_rows(page.extract_words(x_tolerance=2, y_tolerance=3, use_text_flow=True) or [])
                    except Exception:
                        try:
                            visual = _visual_rows(page.extract_words() or [])
                        except Exception:
                            pass
                    combined = text + "\n" + "\n".join(visual)
                    stores = _stores_in_text(combined, available_stores)
                    metrics = _extract_page_metrics(text, visual)
                    page_records.append({"page": page_no, "stores": stores, **metrics})
                    all_text.append(text)

            # Una tienda por página es común en los PDF corporativos. Agrupar por
            # tienda y tomar el mejor total de cada una evita asignar 21 páginas a
            # la primera tienda detectada y evita duplicar páginas repetidas.
            store_best = {}
            for page in page_records:
                if len(page["stores"]) == 1 and page["sales"] > 0:
                    store = page["stores"][0]
                    old = store_best.get(store)
                    if old is None or (page["score"], page["sales"]) > (old["score"], old["sales"]):
                        store_best[store] = page

            unique_stores = sorted({s for page in page_records for s in page["stores"]})
            record["detected_stores"] = unique_stores
            record["rows"] = len(page_records)

            # Buscar primero un total explícito de compañía. Sólo se acepta si la
            # misma página no está identificada como una única tienda.
            company_candidates = [
                p for p in page_records
                if p["sales"] > 0 and len(p["stores"]) != 1
                and any(k in _norm(p.get("source") or "") for k in ("TOTAL", "GENERAL", "COMPANIA", "NACIONAL"))
            ]
            company_best = max(company_candidates, key=lambda p: (p["score"], p["sales"]), default=None)

            if len(store_best) >= 2:
                # Si existe total de compañía con score alto, es más confiable que
                # sumar subtotales. Si no, consolidar el mejor total de cada tienda.
                summed_sales = sum(float(p["sales"] or 0) for p in store_best.values())
                summed_pieces = sum(float(p["pieces"] or 0) for p in store_best.values())
                if company_best and company_best["score"] >= 65 and company_best["sales"] >= max(p["sales"] for p in store_best.values()):
                    sales = float(company_best["sales"]); pieces = float(company_best["pieces"] or summed_pieces)
                    source = f"Pág. {company_best['page']} · {company_best['source']}"
                    method = "PDF · total compañía"
                else:
                    sales = summed_sales; pieces = summed_pieces
                    source = f"Suma de {len(store_best)} tiendas detectadas"
                    method = "PDF · consolidado por tienda"
                record.update({"store": "Compañía", "stores": len(store_best), "total_sales": sales, "total_pieces": pieces, "source_line": source[:300], "source_method": method})
            else:
                best = max([p for p in page_records if p["sales"] > 0], key=lambda p: (p["score"], p["sales"]), default=None)
                if best:
                    one_store = best["stores"][0] if len(best["stores"]) == 1 else (unique_stores[0] if len(unique_stores) == 1 else "")
                    record.update({
                        "store": one_store, "stores": 1 if one_store else len(unique_stores),
                        "total_sales": float(best["sales"] or 0), "total_pieces": float(best["pieces"] or 0),
                        "source_line": f"Pág. {best['page']} · {best['source']}"[:300], "source_method": "PDF · total detectado",
                    })
                elif len(unique_stores) == 1:
                    record["store"] = unique_stores[0]; record["stores"] = 1
                elif len(unique_stores) > 1:
                    record["store"] = "Compañía"; record["stores"] = len(unique_stores)

            # Meta sólo para diagnóstico; no se transforma en venta.
            goals = [p for p in page_records if p.get("goal", 0) > 0]
            if goals:
                if len(unique_stores) > 1:
                    goal_by_store = {}
                    for p in goals:
                        if len(p["stores"]) == 1:
                            st = p["stores"][0]
                            if st not in goal_by_store or p["goal"] > goal_by_store[st]["goal"]:
                                goal_by_store[st] = p
                    record["total_goal"] = sum(float(p["goal"] or 0) for p in goal_by_store.values())
                else:
                    record["total_goal"] = max(float(p["goal"] or 0) for p in goals)

            # Respaldo mensual: únicamente el Excel de capacidades del MISMO mes.
            # Esto permite mostrar venta aunque un PDF de BI no exponga el importe
            # como texto, sin inventar ni copiar cifras de otro periodo.
            if record["total_sales"] <= 0 and y > 0 and 1 <= mo <= 12:
                scope = record["store"] or "Compañía"
                cap_sales, cap_pieces, cap_source = _capacity_month_fallback(m, y, mo, scope)
                if cap_sales > 0:
                    record.update({
                        "total_sales": cap_sales,
                        "total_pieces": cap_pieces or record["total_pieces"],
                        "source_line": cap_source[:300],
                        "source_method": "Excel capacidades · respaldo mismo mes",
                    })

            if record["total_sales"] > 0:
                record["status"] = "Procesado"
                if record["source_method"].startswith("Excel"):
                    record["status"] = "Procesado · venta recuperada del Excel capacidades"
            else:
                # Guardar una muestra útil para depuración, sin volcar el PDF entero.
                interesting = []
                for p in page_records:
                    if p.get("candidate_lines"):
                        interesting.extend([f"P{p['page']}: {x}" for x in p["candidate_lines"][:4]])
                    if len(interesting) >= 12:
                        break
                record["diagnostic"] = " | ".join(interesting[:12])[:1200]
                record["status"] = "Procesado · el PDF no contiene un total de venta mensual legible"

            print(
                f"[V112-SALES] {path.name} · {y}-{mo:02d} · páginas={record['pages']} · "
                f"tiendas={record['stores']} · alcance={record['store'] or 'sin tienda'} · "
                f"venta={record['total_sales']:.2f} · pzas={record['total_pieces']:.0f} · "
                f"método={record['source_method'] or 'sin total'}",
                flush=True,
            )
            if record.get("diagnostic"):
                print(f"[V112-SALES-DIAG] {path.name}: {record['diagnostic']}", flush=True)
        except Exception as exc:
            record.update({"status": f"Error: {type(exc).__name__}", "error": str(exc)})
            print(f"[V112-SALES] ERROR {path.name}: {type(exc).__name__}: {exc}", flush=True)
        return record

    m.parse_sales_pdf = parse_sales_pdf_v112

    # ---------- Corregir rutas V109 que FastAPI estaba interpretando como query ----------
    def _route(path, method):
        for route in list(m.app.router.routes):
            if getattr(route, "path", None) == path and method.upper() in (getattr(route, "methods", set()) or set()):
                return route
        return None

    summary_route = _route("/api/commercial-sales-summary", "GET")
    goals_route = _route("/api/commercial-sales-goals", "POST")
    old_summary = getattr(summary_route, "endpoint", None)
    old_goals = getattr(goals_route, "endpoint", None)

    if summary_route and callable(old_summary):
        m.app.router.routes.remove(summary_route)
        from fastapi import Request

        async def sales_summary_v112(request: Request, year: int | None = None, through_month: int | None = None, store: str = "Compañía"):
            result = old_summary(request=request, year=year, through_month=through_month, store=store)
            if inspect.isawaitable(result):
                result = await result
            # Si el PDF histórico no dio cifra, completar únicamente el mes del
            # corte desde capacidades del mismo periodo y recalcular totales.
            if isinstance(result, dict):
                selected_year = int(result.get("year") or year or datetime.now().year)
                cut = int(result.get("through_month") or through_month or datetime.now().month)
                months = list(result.get("months") or [])
                if 1 <= cut <= 12 and len(months) >= cut:
                    row = months[cut-1]
                    if float(row.get("current") or 0) <= 0:
                        cap_sales, cap_pieces, source = _capacity_month_fallback(m, selected_year, cut, str(result.get("store") or store))
                        if cap_sales > 0:
                            row["current"] = cap_sales
                            row["pieces"] = cap_pieces
                            row["sources"] = max(int(row.get("sources") or 0), 1)
                            row["source_type"] = "Excel capacidades"
                            row["source_name"] = source
                # Recalcular YTD y razones después del respaldo.
                goal_ytd = sum(float(x.get("target") or 0) for x in months[:cut])
                current_ytd = sum(float(x.get("current") or 0) for x in months[:cut])
                previous_ytd = sum(float(x.get("previous") or 0) for x in months[:cut])
                totals = result.setdefault("totals", {})
                totals.update({
                    "goal_ytd": goal_ytd,
                    "current_ytd": current_ytd,
                    "previous_ytd": previous_ytd,
                    "compliance_pct": current_ytd/goal_ytd*100 if goal_ytd else None,
                    "growth_pct": (current_ytd/previous_ytd-1)*100 if previous_ytd else None,
                    "gap_to_goal": current_ytd-goal_ytd if goal_ytd else None,
                })
                result["months"] = months
                result["has_sales"] = any(float(x.get("current") or 0) > 0 or float(x.get("previous") or 0) > 0 for x in months[:cut])
                fallback_used = any(x.get("source_type") == "Excel capacidades" for x in months[:cut])
                result["source_label"] = "Fuente: PDF de ventas mensuales" + (" + Excel capacidades (respaldo mismo mes)" if fallback_used else "")
                result["parser_version"] = PARSER_VERSION
            return result

        m.app.add_api_route("/api/commercial-sales-summary", sales_summary_v112, methods=["GET"])

    if goals_route and callable(old_goals):
        m.app.router.routes.remove(goals_route)
        from fastapi import Request

        async def sales_goals_v112(request: Request):
            result = old_goals(request=request)
            return await result if inspect.isawaitable(result) else result

        m.app.add_api_route("/api/commercial-sales-goals", sales_goals_v112, methods=["POST"])

    # ---------- HTML: corte correcto y mensaje de fuente ----------
    from fastapi.responses import HTMLResponse
    js = r'''
<script id="v112-sales-ui-fix">
(function(){
  function activeCut(){
    const now=new Date(), w=document.getElementById('week')?.value||'';
    let x=String(w).match(/^(\d{4})-W(\d{1,2})$/);
    if(x){
      const y=+x[1],wk=+x[2],d=new Date(Date.UTC(y,0,4)),day=d.getUTCDay()||7;
      d.setUTCDate(d.getUTCDate()-day+1+(wk-1)*7);
      return {year:y,month:d.getUTCMonth()+1};
    }
    x=String(w).match(/^(\d{4})-(\d{2})$/);
    if(x)return {year:+x[1],month:+x[2]};
    return {year:now.getFullYear(),month:now.getMonth()+1};
  }
  function setCorrectCut(){
    const d=activeCut(), ys=document.getElementById('salesExecYear'), ms=document.getElementById('salesExecThrough');
    if(ms && !ms.dataset.v112){ms.dataset.v112='1';ms.value=String(d.month)}
    if(window.loadSalesExecutive){
      setTimeout(()=>window.loadSalesExecutive(d.year,d.month),80);
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(setCorrectCut,900));
  else setTimeout(setCorrectCut,900);
  console.log('[V112] Ventas mensuales: API y corte reparados');
})();
</script>
'''

    @m.app.middleware("http")
    async def _v112_sales_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            # Mostrar el origen híbrido cuando el API utilice respaldo de capacidades.
            old_src = "document.getElementById('salesExecSource').textContent='Fuente: PDF de ventas mensuales · alcance '+d.store;"
            new_src = "document.getElementById('salesExecSource').textContent=(d.source_label||'Fuente: PDF de ventas mensuales')+' · alcance '+d.store;"
            html = html.replace(old_src, new_src)
            if "v112-sales-ui-fix" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache", "Expires":"0"
            })
        except Exception as exc:
            print(f"[V112-UI] warning {type(exc).__name__}: {exc}", flush=True)
            return response

    # ---------- Reprocesar automáticamente PDFs ya cargados que quedaron en cero ----------
    @m.app.on_event("startup")
    def _schedule_repair_existing_sales():
        def worker():
            time.sleep(12)
            try:
                entries = list((m.load_manifest() or {}).get("sales") or [])
                candidates = [
                    dict(e) for e in entries
                    if Path(str(e.get("name") or e.get("path") or "")).suffix.lower() == ".pdf"
                    and int(e.get("year") or 0) > 0
                    and int(e.get("month") or 0) in range(1,13)
                    and (float(e.get("total_sales") or 0) <= 0 or int(e.get("parser_version") or 0) < PARSER_VERSION)
                ]
                fixed = 0
                for item in candidates:
                    try:
                        path = m.resolve_entry_path(item)
                        if not path.exists():
                            continue
                        parsed = parse_sales_pdf_v112(path, int(item.get("year") or 0), int(item.get("month") or 0))
                        changes = {
                            "status": parsed.get("status", ""), "store": parsed.get("store", ""),
                            "rows": parsed.get("rows", 0), "stores": parsed.get("stores", 0),
                            "pages": parsed.get("pages", 0), "total_pieces": parsed.get("total_pieces", 0),
                            "total_sales": parsed.get("total_sales", 0), "parser_version": PARSER_VERSION,
                            "source_line": parsed.get("source_line", ""), "source_method": parsed.get("source_method", ""),
                            "detected_stores": parsed.get("detected_stores", []), "diagnostic": parsed.get("diagnostic", ""),
                        }
                        m.update_entry("sales", str(item.get("id") or ""), **changes)
                        if float(parsed.get("total_sales") or 0) > 0:
                            fixed += 1
                    except Exception as exc:
                        print(f"[V112-REPAIR] {item.get('name','')}: {type(exc).__name__}: {exc}", flush=True)
                print(f"[V112-REPAIR] historial revisado={len(candidates)} · con venta={fixed}", flush=True)
            except Exception as exc:
                print(f"[V112-REPAIR] ERROR general: {type(exc).__name__}: {exc}", flush=True)
        threading.Thread(target=worker, daemon=True, name="v112-sales-repair").start()

    # Autopruebas: FastAPI route y formatos separados de PDF.
    assert _extract_page_metrics("VTA ACUM MES EN $ 1,234,567\nVTA ACUM MES EN PZAS 8,901", [])["sales"] == 1234567
    assert _extract_page_metrics("VTA ACUM MES EN $\n1,234,567", [])["sales"] == 1234567
    m._V112_SALES_REPAIR = True
    print("[V112] Ventas PDF multipágina + API Macro + corte mensual reparados.", flush=True)
