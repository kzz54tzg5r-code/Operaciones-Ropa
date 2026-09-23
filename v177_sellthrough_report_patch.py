"""V177 · Restaura Sell Through en Análisis Comercial con datos reales.

El reporte anterior de Sell Through existía sólo dentro de demos visuales V135/V136.
Esta versión lo integra a producción usando el Excel de capacidades vigente.
"""
from __future__ import annotations

import math
import time
import unicodedata
import json
import sqlite3
import threading

from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V177_SELLTHROUGH_REPORT", False):
        return

    # La pestaña vuelve a formar parte de la configuración de visibilidad.
    try:
        if "commercial.sellthrough" not in m.REPORT_TABS:
            items = list(m.REPORT_TABS.items())
            m.REPORT_TABS.clear()
            inserted = False
            for key, label in items:
                m.REPORT_TABS[key] = label
                if key == "commercial.areas":
                    m.REPORT_TABS["commercial.sellthrough"] = "Sell Through"
                    inserted = True
            if not inserted:
                m.REPORT_TABS["commercial.sellthrough"] = "Sell Through"
    except Exception:
        pass

    def norm(v):
        t = unicodedata.normalize("NFKD", str(v or ""))
        return " ".join("".join(c for c in t if not unicodedata.combining(c)).casefold().split())

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    cache = {}

    # Ventas acumuladas reales por ID desde las hojas mensuales de
    # "Base de muertos y cambios". Se conserva en SQLite para no cargar
    # cientos de miles de filas en RAM cada vez que se abre Sell Through.
    sales_cache_path = m.DATA_ROOT / "sellthrough_sales_by_id.sqlite3"
    sales_cache_lock = threading.Lock()
    sales_cache_state = {"building": False, "error": "", "built_at": 0.0}

    def _ops_sales_source():
        return m.DATA_ROOT / "cambios_muertos_actual.xlsx"

    def _ops_sales_source_stamp(path):
        try:
            stat = path.stat()
            return f"{stat.st_mtime_ns}:{stat.st_size}"
        except Exception:
            return ""

    def _month_sort_key(name):
        key = norm(name)
        months = {
            "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
            "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
            "noviembre":11,"diciembre":12,
        }
        return next((n for label,n in months.items() if label in key),99)

    def _sales_cache_meta():
        if not sales_cache_path.exists():
            return {}
        try:
            con=sqlite3.connect(sales_cache_path)
            try:
                return {str(k):str(v) for k,v in con.execute("SELECT k,v FROM meta")}
            finally:
                con.close()
        except Exception:
            return {}

    def _sales_cache_ready():
        src=_ops_sales_source()
        if not src.exists() or not sales_cache_path.exists():
            return False
        meta=_sales_cache_meta()
        return (
            meta.get("version")=="2"
            and meta.get("source_stamp")==_ops_sales_source_stamp(src)
        )

    def _build_sales_cache():
        src=_ops_sales_source()
        if not src.exists():
            raise FileNotFoundError("No está disponible el archivo vigente de Base de muertos y cambios")
        tmp=sales_cache_path.with_suffix(".tmp.sqlite3")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        target=sqlite3.connect(tmp)
        try:
            target.executescript("""
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                PRAGMA temp_store=FILE;
                CREATE TABLE meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
                CREATE TABLE sales(
                    store TEXT NOT NULL,
                    id_art TEXT NOT NULL,
                    month_source TEXT NOT NULL,
                    sales REAL NOT NULL,
                    PRIMARY KEY(store,id_art,month_source)
                );
                CREATE INDEX idx_sales_id ON sales(id_art);
                CREATE INDEX idx_sales_store ON sales(store);
            """)
            with m._xlsx_stream_book(src) as book:
                names=list(book["sheet_paths"])
                sheets=[name for name in names if m._monthly_sheet_name(name)]
                sheets=sorted(sheets,key=lambda x:(_month_sort_key(x),norm(x)))
                archive=book["archive"]; shared_value=book["shared_value"]
                months_used=[]
                for sheet in sheets:
                    member=book["sheet_paths"].get(sheet,"")
                    if not member or member not in archive.namelist():
                        continue
                    rows=m._xlsx_monthly_rows(archive,member,shared_value)
                    next(rows,None)  # encabezado superior
                    next(rows,None)  # subtítulos
                    batch=[]
                    for values in rows:
                        values=dict(values or {})
                        store=m._normalize_store_value(values.get(25,""))
                        art=m._clean_occurrence(values.get(1,""))
                        if not store or not art:
                            continue
                        try:
                            sale=float(values.get(26,0) or 0)
                            if not math.isfinite(sale) or sale<=0:
                                continue
                        except Exception:
                            continue
                        batch.append((store,art,sheet,sale))
                        if len(batch)>=5000:
                            target.executemany(
                                """INSERT INTO sales(store,id_art,month_source,sales)
                                   VALUES(?,?,?,?)
                                   ON CONFLICT(store,id_art,month_source)
                                   DO UPDATE SET sales=sales+excluded.sales""",
                                batch,
                            )
                            batch.clear()
                    if batch:
                        target.executemany(
                            """INSERT INTO sales(store,id_art,month_source,sales)
                               VALUES(?,?,?,?)
                               ON CONFLICT(store,id_art,month_source)
                               DO UPDATE SET sales=sales+excluded.sales""",
                            batch,
                        )
                    months_used.append(sheet)
                    target.commit()

            stamp=_ops_sales_source_stamp(src)
            target.executemany(
                "INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)",
                [
                    ("version","2"),
                    ("source_stamp",stamp),
                    ("months",json.dumps(months_used,ensure_ascii=False)),
                    ("built_at",str(time.time())),
                    ("source_file",src.name),
                ],
            )
            target.commit()
        finally:
            target.close()
        tmp.replace(sales_cache_path)

    def _start_sales_cache_build():
        if _sales_cache_ready():
            return
        with sales_cache_lock:
            if sales_cache_state["building"]:
                return
            sales_cache_state["building"]=True
            sales_cache_state["error"]=""
        def worker():
            try:
                _build_sales_cache()
                sales_cache_state["built_at"]=time.time()
                print("[V179-SELLTHROUGH] Cache de ventas por ID construido desde Base de muertos y cambios.",flush=True)
            except Exception as exc:
                sales_cache_state["error"]=f"{type(exc).__name__}: {exc}"
                print(f"[V179-SELLTHROUGH] Error construyendo ventas por ID: {sales_cache_state['error']}",flush=True)
            finally:
                sales_cache_state["building"]=False
        threading.Thread(target=worker,name="sellthrough-sales-cache",daemon=True).start()

    def _sales_by_id(selected_store, company_scope):
        if not _sales_cache_ready():
            _start_sales_cache_build()
            return None, [], "building"
        try:
            con=sqlite3.connect(sales_cache_path)
            try:
                if company_scope:
                    rows=con.execute(
                        "SELECT id_art,SUM(sales) FROM sales GROUP BY id_art"
                    ).fetchall()
                else:
                    rows=con.execute(
                        "SELECT id_art,SUM(sales) FROM sales WHERE store=? GROUP BY id_art",
                        (selected_store,),
                    ).fetchall()
                meta={str(k):str(v) for k,v in con.execute("SELECT k,v FROM meta")}
            finally:
                con.close()
            try:
                months=json.loads(meta.get("months") or "[]")
            except Exception:
                months=[]
            return {str(art):float(value or 0) for art,value in rows}, months, "ready"
        except Exception as exc:
            sales_cache_state["error"]=f"{type(exc).__name__}: {exc}"
            return None, [], "error"

    # El cache se construye al abrir Sell Through, evitando competir con
    # reparaciones y cargas al arrancar el servicio de 512 MB.

    @m.app.get("/api/commercial-sellthrough-v177")
    def commercial_sellthrough_v177(
        request: Request,
        week: str = "",
        store: str = "Compañía",
        section: str = "Todas",
        catalog: str = "Todos",
    ):
        actor = m.require_user(request)
        selected_store = str(m.effective_store(actor, store) or "Compañía")
        company_scope = norm(selected_store) == norm("Compañía")
        # Sell Through es un reporte especial: usa únicamente los registros cuyo
        # campo TIPO CATALOGO MAX VIG esté marcado como VIGENTE.
        sales_stamp=_ops_sales_source_stamp(_ops_sales_source())
        key = (week, norm(selected_store), norm(section), "tipo-catalogo-vigente-ops-sales-v185", sales_stamp)
        now = time.monotonic()
        cached = cache.get(key)
        if cached and now - cached[0] < 300:
            return cached[1]

        sales_map, sales_months, sales_state = _sales_by_id(selected_store, company_scope)
        if sales_state=="building":
            from fastapi import HTTPException
            raise HTTPException(503,"Preparando ventas acumuladas por ID desde Base de muertos y cambios")
        if sales_state=="error" or sales_map is None:
            from fastapi import HTTPException
            raise HTTPException(503,sales_cache_state.get("error") or "No fue posible preparar las ventas acumuladas por ID")

        frame = m._capacity_frame_for_period(week)
        empty_payload = {
            "week": week, "store": selected_store, "section": section,
            "catalog": "TIPO CATALOGO MAX VIG", "status": "Estatus catálogo: Vigente",
            "rows": [], "totals": {},
            "formula": "Vta acum pzs / (Vta acum pzs + Stock disponible), donde Stock disponible = Existencia + Tránsito" + (" + Existencia CEDIS" if company_scope else ""),
            "source": "Base de muertos y cambios + Excel de capacidades fuente (RAW-V2)",
            "sales_scope": "Acumulado meses disponibles en Base de muertos y cambios",
            "cedis_in_sellthrough": company_scope,
        }
        if frame is None or frame.empty:
            return empty_payload

        # No dependemos del selector global de catálogo: el campo fuente de este
        # reporte es siempre TIPO CATALOGO MAX VIG.
        work = m._capacity_scope_v45(frame, selected_store, section, "Todos")
        if work is None or work.empty or "ID_ART" not in work.columns:
            return empty_payload

        pd = m.pd

        # El archivo de capacidades usa la columna fuente
        # "TIPO CATALOGO MAX VIG" como el estatus vigente/descontinuado del modelo.
        # Antes se estaba filtrando por "Estatus comercial", lo que eliminaba todos
        # los registros y dejaba Sell Through en ceros.
        # Normalizar ID antes de evaluar vigencia. La vigencia es atributo del
        # MODELO, no de cada fila/tienda individual. Si un ID está vigente, se
        # deben conservar TODAS sus filas para sumar la existencia real del Excel.
        work["__id"] = work["ID_ART"].fillna("").astype(str).str.strip()
        work = work[~work["__id"].isin(["", "nan", "None"])]
        if work.empty:
            return empty_payload

        status_filter_applied = False
        source_status_col = ""
        active = None

        if "Estatus catálogo" in work.columns:
            estatus_key = work["Estatus catálogo"].fillna("").astype(str).map(norm)
            candidate = estatus_key.str.contains(r"(^|\s)vig(ente)?(\s|$)", regex=True, na=False)
            candidate = candidate & ~estatus_key.str.contains(
                r"no\s+vig|descontinu|inactiv|baja|cancel|suspend",
                regex=True, na=False,
            )
            if bool(candidate.any()):
                source_status_col = "Estatus catálogo"
                active = candidate
                status_filter_applied = True

        # En este archivo el campo disponible para vigencia es
        # TIPO CATALOGO MAX VIG. Se usa sólo para decidir QUÉ IDs entran;
        # después se recuperan todas las filas de esos IDs para no perder
        # existencias de otras tiendas.
        if active is None and "Tipo catálogo" in work.columns:
            catalog_key = work["Tipo catálogo"].fillna("").astype(str).map(norm)
            candidate = catalog_key.str.contains(r"(^|\s)vig(ente)?(\s|$)", regex=True, na=False)
            candidate = candidate & ~catalog_key.str.contains(
                r"no\s+vig|descontinu|inactiv|baja|cancel|suspend",
                regex=True, na=False,
            )
            if bool(candidate.any()):
                source_status_col = "TIPO CATALOGO MAX VIG"
                active = candidate
                status_filter_applied = True

        before_rows = int(len(work))
        active_rows = 0
        eligible_ids = None
        if active is not None:
            active_rows = int(active.sum())
            eligible_ids = set(work.loc[active, "__id"].astype(str))
            work = work[work["__id"].isin(eligible_ids)]
            print(
                f"[V185-SELLTHROUGH-FILTER] {week or 'vigente'} {selected_store} {section} "
                f"fuente={source_status_col} filas={before_rows} filas_marcadas={active_rows} "
                f"ids_vigentes={len(eligible_ids)} filas_conservadas={len(work)}",
                flush=True,
            )

        if work.empty:
            empty_payload["status_filter_applied"] = status_filter_applied
            empty_payload["status_source"] = source_status_col
            return empty_payload

        # Diagnóstico controlado del ID usado para validar contra el Excel.
        # No altera el cálculo y permite confirmar que las 24 filas/existencia
        # fuente llegan completas hasta el endpoint.
        _dbg_id="1322682"
        if _dbg_id in set(work["__id"].astype(str)):
            _dbg=work[work["__id"].astype(str)==_dbg_id]
            _dbg_exist=float(pd.to_numeric(_dbg.get("Existencia",0),errors="coerce").fillna(0).sum())
            _dbg_trans=float(pd.to_numeric(_dbg.get("Tránsito",0),errors="coerce").fillna(0).sum())
            _dbg_stores=int(_dbg.get("Tienda",pd.Series("",index=_dbg.index)).fillna("").astype(str).nunique())
            print(
                f"[V185-SELLTHROUGH-ID] id={_dbg_id} filas={len(_dbg)} tiendas={_dbg_stores} "
                f"existencia_raw={_dbg_exist:.0f} transito_raw={_dbg_trans:.0f}",
                flush=True,
            )

        # La venta acumulada viene de Base de muertos y cambios, donde cada
        # hoja mensual contiene venta por ID y tienda desde abril. La existencia
        # continúa viniendo del Excel de capacidades.
        agg = pd.DataFrame(index=work.index)
        agg["__id"] = work["__id"]
        agg["__store"] = work.get("Tienda", pd.Series("", index=work.index)).fillna("").astype(str).map(norm)
        agg["existence"] = pd.to_numeric(work.get("Existencia", 0), errors="coerce").fillna(0.0)
        agg["cedis_existence"] = pd.to_numeric(work.get("Existencia CEDIS", 0), errors="coerce").fillna(0.0)
        agg["transit"] = pd.to_numeric(work.get("Tránsito", 0), errors="coerce").fillna(0.0)
        agg["suggested"] = pd.to_numeric(work.get("VPD", 0), errors="coerce").fillna(0.0)

        # Para Sell Through la conciliación debe cuadrar exactamente
        # con el Excel: al filtrar un ID_ART y sumar la columna EXISTENCIA,
        # el reporte debe devolver esa misma suma. Por ello Existencia y Tránsito
        # se suman sobre TODAS las filas fuente del alcance, sin deduplicar por
        # tienda/ubicación. Sugerido se mantiene como suma del alcance.
        sums = (
            agg.groupby("__id", sort=False, observed=True)
               [["existence","transit","suggested"]]
               .sum(numeric_only=True)
        )

        # CEDIS es inventario central por modelo y se repite entre tiendas/filas:
        # se toma una sola vez por ID.
        cedis = agg.groupby("__id", sort=False)["cedis_existence"].max().rename("cedis_existence")
        numeric = sums.join(cedis, how="left").fillna({"cedis_existence": 0.0})
        numeric["sales_pzas"] = [
            float(sales_map.get(str(ident),0.0) or 0.0)
            for ident in numeric.index
        ]

        if "1322682" in numeric.index.astype(str):
            _r=numeric.loc["1322682"]
            print(
                f"[V185-SELLTHROUGH-ID-FINAL] id=1322682 existencia={float(_r.get('existence',0) or 0):.0f} "
                f"cedis={float(_r.get('cedis_existence',0) or 0):.0f} "
                f"transito={float(_r.get('transit',0) or 0):.0f} "
                f"venta={float(_r.get('sales_pzas',0) or 0):.0f}",
                flush=True,
            )

        meta_cols = {
            "model": "Modelo",
            "brand": "Marca",
            "section": "Sección",
            "rubro": "Subcategoría",
        }
        for dest, src in meta_cols.items():
            if src in work.columns:
                values = work[src].fillna("").astype(str).str.strip().replace({"nan":"", "None":""})
                part = pd.DataFrame({"__id":work["__id"], dest:values.replace("", pd.NA)})
                numeric = numeric.join(part.groupby("__id", sort=False)[dest].first(), how="left")

        for col, default in (("model",""),("brand","Sin marca"),("section","Sin sección"),("rubro","Sin rubro")):
            if col not in numeric.columns:
                numeric[col] = default
            numeric[col] = numeric[col].fillna(default).astype(str)

        models = numeric.reset_index().rename(columns={"__id":"id_art"})
        model_row_counts = work.groupby("__id", sort=False).size().to_dict()
        model_store_counts = (
            work.assign(__store_key=work.get("Tienda", pd.Series("", index=work.index)).fillna("").astype(str).map(norm))
                .groupby("__id", sort=False)["__store_key"].nunique()
                .to_dict()
        )
        # Tránsito sí entra al Sell Through tanto en Compañía como por tienda.
        # CEDIS entra sólo en Compañía, como se definió previamente.
        models["inventory_for_sell"] = models["existence"] + models["transit"] + (models["cedis_existence"] if company_scope else 0.0)
        # Stock disponible = inventario actual que aún puede venderse.
        # Base ST = lo vendido + el stock disponible; es el denominador real.
        models["stock_available"] = models["inventory_for_sell"]
        models["available_base"] = models["sales_pzas"] + models["stock_available"]
        models["sell_through"] = (
            models["sales_pzas"] / models["available_base"].replace(0, pd.NA) * 100
        ).fillna(0.0).clip(lower=0, upper=100)

        total_sales = float(models["sales_pzas"].sum())
        total_exist = float(models["existence"].sum())
        total_cedis = float(models["cedis_existence"].sum())
        total_transit = float(models["transit"].sum())
        total_inventory_for_sell = total_exist + total_transit + (total_cedis if company_scope else 0.0)
        total_stock_available = total_inventory_for_sell
        total_base = total_sales + total_stock_available
        overall = (total_sales / total_base * 100) if total_base else 0.0
        total_models = int(len(models))
        over80 = int((models["sell_through"] >= 80).sum())
        mid = int(((models["sell_through"] >= 50) & (models["sell_through"] < 80)).sum())
        low = int((models["sell_through"] < 50).sum())

        models = models.sort_values(
            ["sell_through","sales_pzas","existence"],
            ascending=[False,False,False],
        ).head(300).reset_index(drop=True)

        rows = []
        for idx, row in models.iterrows():
            rows.append({
                "rank": int(idx + 1),
                "id_art": str(row.get("id_art") or ""),
                "model": str(row.get("model") or row.get("id_art") or ""),
                "brand": str(row.get("brand") or "Sin marca"),
                "section": str(row.get("section") or "Sin sección"),
                "rubro": str(row.get("rubro") or "Sin rubro"),
                "sales_pzas": num(row.get("sales_pzas")),
                "existence": num(row.get("existence")),
                "cedis_existence": num(row.get("cedis_existence")),
                "transit": num(row.get("transit")),
                "inventory_for_sell": num(row.get("inventory_for_sell")),
                "stock_available": num(row.get("stock_available")),
                "available_base": num(row.get("available_base")),
                "suggested": num(row.get("suggested")),
                "sell_through": num(row.get("sell_through")),
                "capacity_rows": int(model_row_counts.get(str(row.get("id_art") or ""),0) or 0),
                "capacity_stores": int(model_store_counts.get(str(row.get("id_art") or ""),0) or 0),
            })

        payload = {
            "week": week,
            "store": selected_store,
            "section": section,
            "catalog": "TIPO CATALOGO MAX VIG",
            "status": "Estatus catálogo: Vigente",
            "rows": rows,
            "totals": {
                "sell_through": overall,
                "sales_pzas": total_sales,
                "existence": total_exist,
                "cedis_existence": total_cedis,
                "transit": total_transit,
                "inventory_for_sell": total_inventory_for_sell,
                "stock_available": total_stock_available,
                "available_base": total_base,
                "models": total_models,
                "over80": over80,
                "mid50_79": mid,
                "under50": low,
            },
            "formula": "Vta acum pzs / (Vta acum pzs + Stock disponible), donde Stock disponible = Existencia + Tránsito" + (" + Existencia CEDIS" if company_scope else ""),
            "source": "Base de muertos y cambios + Excel de capacidades fuente (RAW-V2)",
            "sales_scope": "Acumulado " + (" + ".join(sales_months) if sales_months else "meses disponibles"),
            "sales_months": sales_months,
            "cedis_in_sellthrough": company_scope,
            "status_filter_applied": status_filter_applied,
            "status_source": source_status_col,
        }
        if len(cache) >= 24:
            cache.pop(next(iter(cache)))
        cache[key] = (now, payload)
        print(
            f"[V185-SELLTHROUGH] {week} {selected_store} {section} "
            f"modelos={total_models} ST={overall:.1f}% VTA_ACUM={total_sales:.0f} "
            f"CEDIS={total_cedis:.0f} TRANSITO={total_transit:.0f} include_cedis={company_scope} meses={sales_months}",
            flush=True,
        )
        return payload

    css = r'''<style id="v177-sellthrough-css">
#page-sellthrough .v177-st-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px;margin:9px 0}
#page-sellthrough .v177-st-kpi{background:#fff;border:1px solid #d9e4f1;border-radius:12px;padding:12px 14px;min-width:0}
#page-sellthrough .v177-st-kpi .lab{font-size:8px;font-weight:950;color:#66768d;text-transform:uppercase}
#page-sellthrough .v177-st-kpi .val{font-size:22px;font-weight:950;color:#123f7b;margin-top:3px}
#page-sellthrough .v177-st-kpi .note{font-size:8px;color:#75849a;margin-top:2px}
#page-sellthrough .v177-st-head{display:flex;align-items:end;justify-content:space-between;gap:8px;flex-wrap:wrap;margin:8px 0}
#page-sellthrough .v177-st-tabs{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
#page-sellthrough .v177-st-tabs::-webkit-scrollbar{display:none}
#page-sellthrough .v177-st-tabs button{border:1px solid #d7e1ee;background:#fff;color:#17477f;border-radius:9px;min-height:36px;padding:7px 12px;font-size:8px;font-weight:900;white-space:nowrap;cursor:pointer}
#page-sellthrough .v177-st-tabs button.active{background:#176fe8;border-color:#176fe8;color:#fff}
#page-sellthrough .v177-st-pill{display:inline-block;min-width:48px;padding:3px 6px;border-radius:999px;text-align:center;font-weight:950;background:#eef4fb;color:#17477f}
#page-sellthrough .v177-st-pill.good{background:#e9f8ef;color:#118a52}
#page-sellthrough .v177-st-pill.mid{background:#fff5d9;color:#9a6a00}
#page-sellthrough .v177-st-table td,#page-sellthrough .v177-st-table th{white-space:nowrap}
#page-sellthrough .v177-st-note{font-size:8px;color:#64748b;margin:6px 0}
#analysisNav [data-sub="sellthrough"] .v177-nav-ico{display:inline-flex;width:18px;height:18px;align-items:center;justify-content:center;margin-right:6px;vertical-align:middle}
#analysisNav [data-sub="sellthrough"] .v177-nav-ico svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
/* Un solo icono por pestaña. V165/V167 pueden ejecutarse en distinto orden y
   antes dejaban dos capas de iconos visibles en la barra comercial. */
#analysisNav .switch:has(.v167-tab-icon) .v164-tab-icon,
#analysisNav .switch:has(.v167-tab-icon) .v166-tab-icon{display:none!important}
#analysisNav [data-sub="sellthrough"] .v164-tab-icon,
#analysisNav [data-sub="sellthrough"] .v166-tab-icon,
#analysisNav [data-sub="sellthrough"] .v167-tab-icon{display:none!important}
@media(max-width:900px){
  #page-sellthrough .v177-st-kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  #page-sellthrough .v177-st-kpi{padding:9px 10px}
  #page-sellthrough .v177-st-kpi .val{font-size:16px}
  #page-sellthrough .v177-st-tabs button{min-height:34px;padding:6px 10px}
}
</style>'''

    js = r'''<script id="v177-sellthrough-js">
(function(){
  const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const p1=v=>Number(v||0).toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
  let band='all',busy=false,lastData=null,navObserver=null,navDedupeBusy=false;
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

  function dedupeAnalysisNavIcons(){
    const nav=q('#analysisNav');if(!nav||navDedupeBusy)return;
    navDedupeBusy=true;
    try{
      qa('.switch',nav).forEach(btn=>{
        const icons=qa('.v164-tab-icon,.v166-tab-icon,.v167-tab-icon,.v177-nav-ico',btn);
        if(icons.length<=1)return;
        let keep=null;
        if(btn.dataset.sub==='sellthrough')keep=icons.find(x=>x.classList.contains('v177-nav-ico'))||icons[0];
        else keep=icons.find(x=>x.classList.contains('v167-tab-icon'))||
                  icons.find(x=>x.classList.contains('v164-tab-icon'))||
                  icons.find(x=>x.classList.contains('v166-tab-icon'))||icons[0];
        icons.forEach(x=>{if(x!==keep)x.remove()});
      });
    }finally{navDedupeBusy=false}
  }

  function watchAnalysisNav(){
    const nav=q('#analysisNav');if(!nav)return;
    dedupeAnalysisNavIcons();
    if(navObserver)return;
    navObserver=new MutationObserver(()=>dedupeAnalysisNavIcons());
    navObserver.observe(nav,{childList:true,subtree:true});
  }

  function ensureUI(){
    const nav=q('#analysisNav');
    if(nav&&!q('[data-sub="sellthrough"]',nav)){
      const btn=document.createElement('button');
      btn.type='button';btn.className='switch';btn.dataset.sub='sellthrough';btn.dataset.tabKey='commercial.sellthrough';
      btn.innerHTML='<span class="v177-nav-ico"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M19 5 5 19"/></svg></span><span>Sell Through</span>';
      const before=q('[data-sub="more"]',nav)||q('[data-sub="analysis-upload"]',nav);
      nav.insertBefore(btn,before||null);
      btn.onclick=()=>openSellThrough();
    }

    if(!q('#page-sellthrough')){
      const page=document.createElement('section');
      page.className='page';page.id='page-sellthrough';
      page.innerHTML=
        '<div class="title">Sell Through</div>'+
        '<div class="subtitle">Rotación por modelo con inventario leído directamente del Excel fuente y venta acumulada por ID · Estatus de catálogo VIGENTE · usando TIPO CATALOGO MAX VIG del archivo.</div>'+
        '<div class="v177-st-kpis" id="v177StKpis"></div>'+
        '<div class="v177-st-head"><div><div class="title" style="margin:0">Ranking de modelos</div><div class="v177-st-note" id="v177StContext"></div></div>'+
          '<div class="v177-st-tabs" id="v177StTabs">'+
            '<button type="button" class="active" data-st-band="all">Todos</button>'+
            '<button type="button" data-st-band="over80">≥ 80%</button>'+
            '<button type="button" data-st-band="mid">50–79%</button>'+
            '<button type="button" data-st-band="low">&lt; 50%</button>'+
          '</div>'+
        '</div>'+
        '<div class="v177-st-note" id="v177StFormula">Sell Through con Vta acum pzs por ID desde Base de muertos y cambios. En Compañía incluye existencia CEDIS; por tienda CEDIS sólo se muestra y no entra al cálculo.</div>'+
        '<div class="tablewrap"><table class="table v177-st-table"><thead><tr>'+
          '<th>#</th><th>% Sell Through</th><th>ID_ART</th><th>Modelo</th><th>Marca</th><th>Sección</th><th>Rubro</th><th>Vta acum pzs</th><th>Existencia</th><th>Existencia CEDIS</th><th>Tránsito</th><th>Stock disponible</th><th>Base ST</th><th>Sugerido 7</th>'+
        '</tr></thead><tbody id="v177StRows"><tr><td colspan="14">Selecciona Sell Through para consultar.</td></tr></tbody></table></div>';
      const anchor=q('#page-more')||q('#page-analysis-upload')||q('#appView');
      if(anchor?.parentNode)anchor.parentNode.insertBefore(page,anchor);
      else document.body.appendChild(page);
      qa('[data-st-band]',page).forEach(b=>b.onclick=()=>{
        band=b.dataset.stBand||'all';
        qa('[data-st-band]',page).forEach(x=>x.classList.toggle('active',x===b));
        renderRows(lastData);
      });
    }
    watchAnalysisNav();
    dedupeAnalysisNavIcons();
  }

  async function A(url){
    let lastError=null;
    const waits=[0,3500,6500,9000];
    for(let attempt=0;attempt<waits.length;attempt++){
      if(waits[attempt])await sleep(waits[attempt]);
      try{
        const res=await fetch(url,{credentials:'same-origin',cache:'no-store'});
        if(res.ok)return res.json();
        let msg='Error '+res.status;
        try{const j=await res.json();msg=j.detail||msg}catch(_){}
        const err=new Error(msg);err.status=res.status;
        if(![502,503,504].includes(res.status))throw err;
        lastError=err;
      }catch(e){
        if(e?.status&&!([502,503,504].includes(e.status)))throw e;
        lastError=e;
      }
      const body=q('#v177StRows');
      if(body&&attempt<waits.length-1){
        body.innerHTML='<tr><td colspan="14">Preparando Sell Through… reintentando automáticamente ('+(attempt+2)+'/'+waits.length+').</td></tr>';
      }
    }
    throw lastError||new Error('No fue posible consultar Sell Through');
  }

  function inBand(x){
    const st=Number(x.sell_through||0);
    if(band==='over80')return st>=80;
    if(band==='mid')return st>=50&&st<80;
    if(band==='low')return st<50;
    return true;
  }
  function pill(st){
    const c=st>=80?'good':st>=50?'mid':'';
    return '<span class="v177-st-pill '+c+'">'+p1(st)+'</span>';
  }
  function renderRows(d){
    if(!d)return;
    const rows=(d.rows||[]).filter(inBand);
    const body=q('#v177StRows');
    if(body)body.innerHTML=rows.map((r,i)=>
      '<tr><td><b>#'+(i+1)+'</b></td><td>'+pill(r.sell_through)+'</td><td>'+esc(r.id_art)+'</td><td><b>'+esc(r.model)+'</b></td><td>'+esc(r.brand)+'</td><td>'+esc(r.section)+'</td><td>'+esc(r.rubro)+'</td><td>'+nf(r.sales_pzas)+'</td><td>'+nf(r.existence)+'</td><td>'+nf(r.cedis_existence)+'</td><td>'+nf(r.transit)+'</td><td>'+nf(r.stock_available)+'</td><td>'+nf(r.available_base)+'</td><td>'+Number(r.suggested||0).toLocaleString('es-MX',{maximumFractionDigits:2})+'</td></tr>'
    ).join('')||'<tr><td colspan="14">Sin modelos para este rango.</td></tr>';
  }
  function render(d){
    lastData=d;
    const t=d.totals||{};
    const k=q('#v177StKpis');
    if(k)k.innerHTML=
      '<div class="v177-st-kpi"><div class="lab">Sell Through general</div><div class="val">'+p1(t.sell_through)+'</div><div class="note">'+(d.cedis_in_sellthrough?'incluye CEDIS':'CEDIS no entra al cálculo')+'</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Vta acum pzs</div><div class="val">'+nf(t.sales_pzas)+'</div><div class="note">'+esc(d.sales_scope||'Acumulado anual')+'</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Existencia</div><div class="val">'+nf(t.existence)+'</div><div class="note">inventario en tiendas</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Existencia CEDIS</div><div class="val">'+nf(t.cedis_existence)+'</div><div class="note">'+(d.cedis_in_sellthrough?'incluida en Compañía':'sólo informativa por tienda')+'</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Stock disponible</div><div class="val">'+nf(t.stock_available)+'</div><div class="note">Existencia + Tránsito'+(d.cedis_in_sellthrough?' + CEDIS':'')+'</div></div>'+
      '<div class="v177-st-kpi"><div class="lab">Modelos ≥ 80%</div><div class="val">'+nf(t.over80)+'</div><div class="note">de '+nf(t.models)+' modelos</div></div>';
    const ctx=q('#v177StContext');
    if(ctx)ctx.textContent=(d.store||'Compañía')+' · '+(d.section||'Todas')+' · Estatus catálogo vigente · '+(d.sales_scope||'Acumulado anual')+' · '+(d.source||'Base de muertos y cambios + Excel de capacidades fuente (RAW-V2)');
    const formula=q('#v177StFormula');
    if(formula)formula.textContent='Archivo fuente: '+(d.source_file||'sin identificar')+' · Motor: '+(d.engine||'legacy')+' · Sell Through = '+(d.formula||'Vta acum pzs / (Vta acum pzs + Stock disponible)')+'. Stock disponible es inventario actual, mientras que Base ST = Vta acum pzs + Stock disponible. Existencia CEDIS '+(d.cedis_in_sellthrough?'sí se considera en Compañía.':'se muestra, pero no se considera al filtrar una tienda.');
    renderRows(d);
  }

  async function load(){
    if(busy)return;
    ensureUI();busy=true;
    const body=q('#v177StRows');if(body)body.innerHTML='<tr><td colspan="14">Cargando Sell Through…</td></tr>';
    try{
      const week=q('#week')?.value||'';
      const store=q('#store')?.value||'Compañía';
      const section=q('#section')?.value||'Todas';
      const d=await A('/api/commercial-sellthrough-v2?week='+encodeURIComponent(week)+'&store='+encodeURIComponent(store)+'&section='+encodeURIComponent(section)+'&catalog='+encodeURIComponent('Todos'));
      render(d);
    }catch(e){
      if(body)body.innerHTML='<tr><td colspan="14">No fue posible cargar Sell Through: '+esc(e.message||e)+'. Reintentando al estabilizar el servicio…</td></tr>';
      setTimeout(()=>{if(q('#page-sellthrough.active')&&!busy)load()},12000);
    }finally{busy=false}
  }

  async function fixedCapacityUpload(file,logTarget,button){
    if(!file)return;
    const logNode=q(logTarget);
    const say=msg=>{if(logNode){logNode.classList?.remove('hidden');logNode.textContent=msg}};
    const fd=new FormData();fd.append('file',file,file.name);
    button.disabled=true;button.textContent='Procesando Excel…';
    say('Subiendo '+file.name+'… No cierres esta pestaña.');
    try{
      const start=await fetch('/api/upload/jobs/capacity',{method:'POST',body:fd,credentials:'same-origin',cache:'no-store'});
      const raw=await start.text();let job={};try{job=raw?JSON.parse(raw):{}}catch(_){}
      if(!start.ok)throw new Error(job.detail||job.message||('Error HTTP '+start.status));
      if(!job.id)throw new Error('El servidor no devolvió identificador de carga.');
      localStorage.setItem('operacionesRopaUploadJob.capacity',job.id);
      for(;;){
        await sleep(2500);
        const res=await fetch('/api/upload/jobs/'+encodeURIComponent(job.id),{credentials:'same-origin',cache:'no-store'});
        const txt=await res.text();let state={};try{state=txt?JSON.parse(txt):{}}catch(_){}
        if(!res.ok)throw new Error(state.detail||state.message||('Error HTTP '+res.status));
        say((state.message||'Procesando capacidades…')+'\nProgreso: '+Number(state.progress||0).toLocaleString('es-MX')+'%');
        if(state.status==='complete'){
          localStorage.removeItem('operacionesRopaUploadJob.capacity');
          const result=state.result||{};
          say('Capacidades procesadas correctamente.\n\nRegistros: '+Number(result.rows||0).toLocaleString('es-MX')+'\nTiendas: '+Number(result.stores||0).toLocaleString('es-MX')+'\nLa nueva versión ya quedó publicada.');
          try{if(typeof loadUploadHistories==='function')await loadUploadHistories()}catch(_){}
          try{if(typeof safeRefreshDash==='function')await safeRefreshDash()}catch(_){}
          break;
        }
        if(state.status==='error'||state.status==='interrupted'){
          localStorage.removeItem('operacionesRopaUploadJob.capacity');
          throw new Error(state.error||state.message||'No fue posible procesar el Excel.');
        }
      }
    }catch(e){
      say('Error procesando capacidades: '+(e?.message||e));
    }finally{
      button.disabled=false;button.textContent='Procesar Excel';
    }
  }

  // El botón de la pantalla Análisis Comercial dejó de emitir solicitudes en
  // algunos navegadores. Este listener delegado en captura no depende del
  // onclick legado y garantiza que el archivo seleccionado se envíe.
  document.addEventListener('click',e=>{
    const btn=e.target.closest?.('#analysisCapUploadBtn,#uploadCap');
    if(!btn)return;
    e.preventDefault();e.stopImmediatePropagation();
    const analysis=btn.id==='analysisCapUploadBtn';
    const input=q(analysis?'#analysisCapFile':'#capFile');
    const file=input?.files?.[0];
    const target=analysis?'#analysisUploadLog':'#log';
    if(!file){
      const node=q(target);if(node)node.textContent='Selecciona Excel de capacidades/existencias.';
      return;
    }
    fixedCapacityUpload(file,target,btn);
  },true);

  function openSellThrough(){
    ensureUI();
    try{
      if(typeof goSub==='function')goSub('sellthrough');
      else{
        qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-sellthrough'));
        qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='sellthrough'));
      }
    }catch(_){
      qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-sellthrough'));
      qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='sellthrough'));
    }
    const cf=q('.commercialFilter');if(cf)cf.style.display='block';
    const ht=q('#heroTitle'),hs=q('#heroSub');
    if(ht)ht.textContent='Análisis Comercial';
    if(hs)hs.textContent='Sell Through · rotación por modelo';
    load();
  }
  window.loadSellThroughV177=load;

  document.addEventListener('change',e=>{
    if(e.target.matches?.('#week,#store,#section')&&q('#page-sellthrough.active'))load();
  },true);
  document.addEventListener('click',e=>{
    const navBtn=e.target.closest?.('#analysisNav .switch');
    if(navBtn)setTimeout(dedupeAnalysisNavIcons,0);
    const b=e.target.closest?.('#analysisNav [data-sub="sellthrough"]');
    if(b){e.preventDefault();e.stopImmediatePropagation();openSellThrough();}
  },true);

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensureUI,{once:true});
  else ensureUI();
  setTimeout(ensureUI,300);setTimeout(ensureUI,1200);
  console.info('[V182] Sell Through filtra VIGENTE por Estatus de catálogo y conserva TIPO CATALOGO MAX VIG como clasificación.');
})();
</script>'''

    @m.app.middleware("http")
    async def v177_sellthrough_html(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v177-sellthrough-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v177-sellthrough-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            headers["X-Operations-SellThrough"] = "V177"
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        return response

    m._V177_SELLTHROUGH_REPORT = True
    print("[V177] Sell Through de producción restaurado con datos reales.", flush=True)
