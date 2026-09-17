"""V164 · Boceto aprobado + Matriz de recolección real.

Alcance autorizado:
- En reportes existentes NO modifica tablas, gráficas, cálculos, PDF ni Excel.
- Unifica el único bloque de filtros V161 al estilo aprobado, ahora con iconos.
- Uniforma pestañas existentes con iconos y tarjetas KPI al estilo aprobado.
- Corrige el bloque inferior del sidebar y muestra Cerrar sesión con icono real.
- Agrega exclusivamente una nueva pestaña en Cambios y Muertos:
  ``Matriz de recolección``. Esta pestaña sí incluye su tabla y visuales propios,
  alimentados sólo con datos reales del Excel operativo (Muertos, Cajas,
  Probador, fecha y horarios ya parseados por la base vigente).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import math
import re
import unicodedata

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V164_FILTERS_CARDS_MATRIX", False):
        return

    # La nueva pestaña también queda administrable desde "Pestañas visibles".
    ordered = {}
    inserted = False
    for key, label in list(m.REPORT_TABS.items()):
        ordered[key] = label
        if key == "operations.routes":
            ordered["operations.collection"] = "Matriz de recolección"
            inserted = True
    if not inserted:
        ordered["operations.collection"] = "Matriz de recolección"
    m.REPORT_TABS.clear()
    m.REPORT_TABS.update(ordered)
    try:
        with m.db() as con:
            con.execute(
                "INSERT OR IGNORE INTO report_tab_visibility(tab_key,visible,updated_at,updated_by) VALUES(?,?,?,?)",
                ("operations.collection", 1, datetime.now().isoformat(timespec="seconds"), "system-v164"),
            )
    except Exception as exc:
        print(f"[V164] Visibilidad Matriz: {type(exc).__name__}: {exc}", flush=True)

    def _norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return " ".join(text.casefold().strip().split())

    def _num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def _bounds(period_type: str, period_value: str):
        ptype = str(period_type or "week").strip().lower()
        value = str(period_value or "").strip()
        today = date.today()
        if ptype == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date()
            return d, d
        if ptype == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, flags=re.I)
            if mt:
                start = date.fromisocalendar(int(mt.group(1)), int(mt.group(2)), 1)
            else:
                iso = today.isocalendar()
                start = date.fromisocalendar(iso.year, iso.week, 1)
            return start, start + timedelta(days=6)
        if ptype == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            if mt:
                y, mo = int(mt.group(1)), int(mt.group(2))
            else:
                y, mo = today.year, today.month
            start = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return start, nxt - timedelta(days=1)
        if ptype == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        raise HTTPException(400, "Vista inválida")

    def _time_label(value):
        raw = str(value or "").strip()
        if not raw or raw.lower() in {"nan", "nat", "none"}:
            return "Sin horario"
        mt = re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)", raw)
        if mt:
            return f"{int(mt.group(1)):02d}:{mt.group(2)}"
        # Horas de Excel ocasionalmente pueden persistir como fracción del día.
        try:
            x = float(raw)
            if 0 <= x < 1:
                mins = int(round(x * 24 * 60)) % (24 * 60)
                return f"{mins // 60:02d}:{mins % 60:02d}"
        except Exception:
            pass
        return raw[:16]

    DAY_NAMES = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    DAY_SHORT = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

    @m.app.get("/api/operations/collection-matrix-v164")
    def collection_matrix_v164(
        request: Request,
        period_type: str = "week",
        period_value: str = "",
        store: str = "Compañía",
        area: str = "Todas",
        activity: str = "Todas",
    ):
        actor = m.require_user(request)
        start, end = _bounds(period_type, period_value)
        selected_store = m.effective_store(actor, store)
        rows = list((m.load_ops() or {}).get("rows") or [])

        # El reporte sólo usa filas reales clasificadas por el parser como
        # Muertos, Cajas o Probador. No crea horarios ni cantidades ficticias.
        filtered = []
        for r in rows:
            ds = str(r.get("date") or "")[:10]
            if not ds:
                continue
            try:
                d = date.fromisoformat(ds)
            except Exception:
                continue
            if d < start or d > end:
                continue
            st = str(r.get("store") or "").strip()
            if selected_store and selected_store != "Compañía" and st != selected_store:
                continue
            if str(area or "").strip() not in ("", "Todas", "Todos"):
                if _norm(r.get("area")) != _norm(area):
                    continue
            if str(activity or "").strip() not in ("", "Todas", "Todos"):
                candidate = r.get("activity") or r.get("activity_original") or ""
                if _norm(candidate) != _norm(activity):
                    continue
            muertos, cajas, probador = _num(r.get("muertos")), _num(r.get("cajas")), _num(r.get("probador"))
            if muertos <= 0 and cajas <= 0 and probador <= 0:
                continue
            filtered.append({
                "date": ds,
                "store": st,
                "area": str(r.get("area") or "").strip(),
                "start": _time_label(r.get("start_time")),
                "end": _time_label(r.get("end_time")),
                "name": str(r.get("name") or "").strip(),
                "muertos": muertos,
                "cajas": cajas,
                "probador": probador,
            })

        # Una fila de matriz representa tienda + área + día + franja horaria.
        # De esta forma los tres motivos quedan juntos aunque el Excel los traiga
        # como renglones separados.
        grouped = {}
        for r in filtered:
            key = (r["date"], r["store"], r["area"], r["start"], r["end"])
            g = grouped.setdefault(key, {
                "date": r["date"], "store": r["store"], "area": r["area"],
                "start": r["start"], "end": r["end"], "muertos": 0.0,
                "cajas": 0.0, "probador": 0.0, "names": set(),
            })
            g["muertos"] += r["muertos"]
            g["cajas"] += r["cajas"]
            g["probador"] += r["probador"]
            if r["name"]:
                g["names"].add(r["name"])

        matrix = []
        source_totals = {"muertos": 0.0, "cajas": 0.0, "probador": 0.0}
        daily = defaultdict(lambda: {"muertos": 0.0, "cajas": 0.0, "probador": 0.0, "slots": 0})
        stores = defaultdict(lambda: {"muertos": 0.0, "cajas": 0.0, "probador": 0.0, "slots": 0})
        for key in sorted(grouped):
            g = grouped[key]
            d = date.fromisoformat(g["date"])
            total = g["muertos"] + g["cajas"] + g["probador"]
            schedule = g["start"] if g["end"] in ("", "Sin horario") else f'{g["start"]} - {g["end"]}'
            item = {
                "date": g["date"], "day": DAY_NAMES[d.weekday()], "day_short": DAY_SHORT[d.weekday()],
                "schedule": schedule, "store": g["store"], "area": g["area"] or "Sin área",
                "muertos": g["muertos"], "cajas": g["cajas"], "probador": g["probador"],
                "total": total, "responsible": ", ".join(sorted(g["names"])) or "Sin responsable",
                "status": "Registrada",
            }
            matrix.append(item)
            for k in source_totals:
                source_totals[k] += g[k]
                daily[g["date"]][k] += g[k]
                stores[g["store"]][k] += g[k]
            daily[g["date"]]["slots"] += 1
            stores[g["store"]]["slots"] += 1

        daily_rows = []
        cursor = start
        while cursor <= end:
            vals = daily.get(cursor.isoformat(), {"muertos":0.0,"cajas":0.0,"probador":0.0,"slots":0})
            daily_rows.append({
                "date": cursor.isoformat(), "label": DAY_SHORT[cursor.weekday()] if period_type == "week" else cursor.strftime("%d/%m"),
                "muertos": vals["muertos"], "cajas": vals["cajas"], "probador": vals["probador"],
                "total": vals["muertos"] + vals["cajas"] + vals["probador"], "slots": vals["slots"],
            })
            cursor += timedelta(days=1)

        store_rows = []
        for st, vals in stores.items():
            total = vals["muertos"] + vals["cajas"] + vals["probador"]
            store_rows.append({"store": st, **vals, "total": total})
        store_rows.sort(key=lambda x: (-x["total"], x["store"]))

        peak = max(matrix, key=lambda x: x["total"], default=None)
        total_pieces = sum(source_totals.values())
        return {
            "period_type": period_type, "period_value": period_value,
            "start_date": start.isoformat(), "end_date": end.isoformat(), "store": selected_store,
            "summary": {
                "records": len(matrix), "pieces": total_pieces, "stores": len(stores),
                "peak_schedule": peak["schedule"] if peak else "Sin datos",
                "peak_day": peak["day"] if peak else "",
                "peak_pieces": peak["total"] if peak else 0,
            },
            "source_totals": source_totals,
            "matrix": matrix,
            "daily": daily_rows,
            "stores": store_rows,
        }

    css = r'''<style id="v164-filters-cards-matrix-css">
/* ---------- ÚNICO SISTEMA DE FILTROS ---------- */
#v158FilterBar,#v103FilterShell,#v102FilterMode,#v102Drill,#v103ClassicBack,
#globalFilters,.filters,#operativoPeriodBar{display:none!important}
#v161FilterBar{display:none!important}
#v161FilterBar.on{display:block!important;background:#fff!important;border:1px solid #d6e3f1!important;border-radius:15px!important;padding:11px!important;box-shadow:0 3px 12px rgba(18,63,125,.05)!important}
.v161-filter-grid{gap:9px!important}
.v161-field{position:relative!important;min-width:0!important}
.v161-field label{font-size:8px!important;color:#60758f!important;margin:0 0 5px 2px!important;font-weight:950!important}
.v161-field select,.v161-field input{height:42px!important;border:1px solid #cbdcec!important;border-radius:10px!important;padding:7px 30px 7px 36px!important;color:#103f7d!important;font-weight:850!important;background:#fff!important}
.v164-filter-icon{position:absolute;left:11px;bottom:11px;width:18px;height:18px;color:#176fe8;pointer-events:none;display:grid;place-items:center}
.v164-filter-icon svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.v161-apply{height:42px!important;min-width:138px!important;border-radius:10px!important;background:linear-gradient(90deg,#1769e8,#147df5)!important;display:flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;font-size:9px!important}
.v161-apply .v164-search-icon{width:17px;height:17px;display:inline-flex}.v161-apply .v164-search-icon svg{width:17px;height:17px;stroke:#fff;fill:none;stroke-width:2}

/* ---------- PESTAÑAS CON ICONOS ---------- */
#operativoNav .switch,#analysisNav .switch,.v125-tab{display:flex!important;align-items:center!important;justify-content:center!important;gap:7px!important;border-radius:9px!important;min-height:39px!important;font-size:8.5px!important}
.v164-tab-icon{display:inline-flex;width:18px;height:18px;flex:0 0 18px;color:currentColor}
.v164-tab-icon svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
body[data-v163-module="operativo"] #operativoNav:not(.hidden){grid-template-columns:repeat(6,minmax(0,1fr))!important}

/* ---------- TARJETAS: sólo apariencia, valores intactos ---------- */
.kpi,.report-kpi,.v149-kpi,.v125-kpi{position:relative!important;border:1px solid #d8e4f0!important;border-radius:13px!important;padding:12px 12px 12px 50px!important;background:#fff!important;box-shadow:0 2px 8px rgba(20,64,114,.035)!important;overflow:hidden!important}
.v164-kpi-icon{position:absolute;left:13px;top:16px;width:27px;height:27px;border-radius:50%;display:grid;place-items:center;background:#edf5ff;color:#176fe8}
.v164-kpi-icon svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.kpi:nth-child(4n+2) .v164-kpi-icon,.report-kpi:nth-child(4n+2) .v164-kpi-icon,.v149-kpi:nth-child(4n+2) .v164-kpi-icon,.v125-kpi:nth-child(4n+2) .v164-kpi-icon{background:#ecfbf4;color:#0ca96b}
.kpi:nth-child(4n+3) .v164-kpi-icon,.report-kpi:nth-child(4n+3) .v164-kpi-icon,.v149-kpi:nth-child(4n+3) .v164-kpi-icon,.v125-kpi:nth-child(4n+3) .v164-kpi-icon{background:#f4edff;color:#7135e8}
.kpi:nth-child(4n) .v164-kpi-icon,.report-kpi:nth-child(4n) .v164-kpi-icon,.v149-kpi:nth-child(4n) .v164-kpi-icon,.v125-kpi:nth-child(4n) .v164-kpi-icon{background:#fff0f3;color:#ef376c}

/* ---------- SIDEBAR / CERRAR SESIÓN ---------- */
.side .profile{background:transparent!important;min-height:0!important;height:auto!important;border-top:1px solid rgba(255,255,255,.18)!important;padding:10px 8px 3px!important}
.side .logout{display:flex!important;align-items:center!important;justify-content:flex-start!important;gap:8px!important;width:100%!important;min-height:38px!important;background:transparent!important;color:inherit!important;border:1px solid rgba(140,169,205,.45)!important;border-radius:9px!important;padding:8px 10px!important;font-weight:850!important}
.v164-logout-icon{display:inline-flex;width:18px;height:18px}.v164-logout-icon svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.shell.sidebar-collapsed .profile{display:block!important;padding:8px 2px!important;border-top:1px solid rgba(255,255,255,.18)!important}
.shell.sidebar-collapsed .profile>b,.shell.sidebar-collapsed .profile>small,.shell.sidebar-collapsed #viewRoleBox{display:none!important}
.shell.sidebar-collapsed .logout{width:42px!important;height:42px!important;margin:0 auto!important;padding:0!important;justify-content:center!important;font-size:0!important}
.shell.sidebar-collapsed .logout:before{display:none!important;content:none!important}.shell.sidebar-collapsed .v164-logout-icon{width:20px;height:20px}

/* ---------- MATRIZ DE RECOLECCIÓN (única vista nueva completa) ---------- */
.v164-matrix-head{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;margin:10px 0 7px}.v164-matrix-head h2{margin:0;color:#103f7d;font-size:20px}.v164-matrix-head p{margin:4px 0 0;color:#71839a;font-size:9px}
.v164-matrix-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:8px 0 11px}.v164-matrix-kpi{position:relative;background:#fff;border:1px solid #d8e4f0;border-radius:13px;padding:12px 12px 12px 49px;min-height:92px;overflow:hidden}.v164-matrix-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c,#176fe8)}.v164-matrix-kpi .ico{position:absolute;left:13px;top:15px;width:27px;height:27px;border-radius:50%;display:grid;place-items:center;background:#edf5ff;color:var(--c,#176fe8)}.v164-matrix-kpi .ico svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2}.v164-matrix-kpi small{font-size:7.5px;color:#687b93;font-weight:950;text-transform:uppercase}.v164-matrix-kpi b{display:block;font-size:24px;color:#103f7d;line-height:1.1;margin:6px 0 2px}.v164-matrix-kpi span{font-size:8px;color:#71839a}
.v164-panel{background:#fff;border:1px solid #d8e4f0;border-radius:13px;padding:11px;margin:9px 0}.v164-panel h3{font-size:13px;color:#103f7d;margin:0 0 3px}.v164-panel .sub{font-size:8px;color:#71839a;margin-bottom:8px}.v164-matrix-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr);gap:9px}.v164-donut-wrap{display:flex;align-items:center;justify-content:center;gap:18px;min-height:210px}.v164-donut{width:154px;height:154px;border-radius:50%;display:grid;place-items:center;position:relative}.v164-donut:after{content:"";position:absolute;width:92px;height:92px;border-radius:50%;background:#fff}.v164-donut-center{position:relative;z-index:2;text-align:center;color:#103f7d}.v164-donut-center b{display:block;font-size:18px}.v164-donut-center span{font-size:8px}.v164-legend{display:grid;gap:8px;font-size:8px}.v164-legend div{display:grid;grid-template-columns:10px 1fr auto;gap:6px;align-items:center}.v164-dot{width:9px;height:9px;border-radius:50%}
.v164-trend{height:215px;display:flex;align-items:flex-end;gap:8px;padding:15px 6px 20px;border-left:1px solid #e5ecf4;border-bottom:1px solid #e5ecf4}.v164-day{flex:1;height:100%;display:flex;align-items:flex-end;justify-content:center;gap:3px;position:relative}.v164-bar{width:21%;min-width:7px;border-radius:4px 4px 0 0}.v164-day-label{position:absolute;bottom:-17px;left:0;right:0;text-align:center;font-size:7px;color:#667a92}.v164-value{position:absolute;top:-13px;font-size:6.5px;color:#60758f;font-weight:850}
.v164-status{display:inline-flex;align-items:center;gap:5px;color:#087a36;font-weight:850}.v164-status:before{content:"";width:7px;height:7px;border-radius:50%;background:#15a66a}

@media(max-width:900px){
  body[data-v163-module="operativo"] #operativoNav:not(.hidden){display:flex!important;overflow-x:auto!important;grid-template-columns:none!important}
  #operativoNav .switch,#analysisNav .switch,.v125-tab{min-width:132px!important;font-size:9px!important}
  .v161-field select,.v161-field input{padding-left:35px!important}
  .v164-filter-icon{bottom:13px}
  .kpi,.report-kpi,.v149-kpi,.v125-kpi{padding-left:45px!important}.v164-kpi-icon{left:10px;top:14px;width:25px;height:25px}
  .v164-matrix-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v164-matrix-grid{grid-template-columns:1fr}.v164-donut-wrap{min-height:190px}
}
</style>'''

    js = r'''<script id="v164-filters-cards-matrix-js">
(function(){
  if(window.__V164_FILTERS_CARDS_MATRIX)return;
  window.__V164_FILTERS_CARDS_MATRIX=true;
  const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const nf=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});

  const icons={
    calendar:'<svg viewBox="0 0 24 24"><path d="M4 5h16v15H4zM8 3v4M16 3v4M4 9h16"/></svg>',
    store:'<svg viewBox="0 0 24 24"><path d="M4 10h16l-2-5H6zM5 10v9h14v-9M9 19v-5h6v5"/></svg>',
    grid:'<svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg>',
    list:'<svg viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11M4 6h1M4 12h1M4 18h1"/></svg>',
    user:'<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
    chart:'<svg viewBox="0 0 24 24"><path d="M5 20V11M12 20V4M19 20v-7"/></svg>',
    dollar:'<svg viewBox="0 0 24 24"><path d="M12 3v18M16 7.2c-.8-1-2.2-1.7-4-1.7-2.2 0-4 1.2-4 3s1.5 2.5 4.3 3.1c2.7.6 4.2 1.4 4.2 3.4 0 2.1-1.9 3.5-4.5 3.5-2 0-3.7-.7-4.8-2"/></svg>',
    pin:'<svg viewBox="0 0 24 24"><path d="M12 21s7-6.1 7-12a7 7 0 10-14 0c0 5.9 7 12 7 12z"/><circle cx="12" cy="9" r="2"/></svg>',
    table:'<svg viewBox="0 0 24 24"><path d="M4 5h16v14H4zM4 10h16M9 5v14M15 5v14"/></svg>',
    box:'<svg viewBox="0 0 24 24"><path d="M4 7l8-4 8 4-8 4zM4 7v10l8 4 8-4V7M12 11v10"/></svg>',
    target:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 2v3M22 12h-3"/></svg>',
    upload:'<svg viewBox="0 0 24 24"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></svg>',
    logout:'<svg viewBox="0 0 24 24"><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"/></svg>',
    search:'<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M16 16l5 5"/></svg>',
    home:'<svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8M5 10v10h14V10M9 20v-6h6v6"/></svg>',
    settings:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 00-.1-1l2-1.5-2-3.4-2.4 1a8 8 0 00-1.8-1L14.4 3h-4.8l-.4 3.1a8 8 0 00-1.8 1L5 6.1 3 9.5 5.1 11a7 7 0 000 2L3 14.5 5 18l2.4-1.1a8 8 0 001.8 1l.4 3.1h4.8l.4-3.1a8 8 0 001.8-1L19 18l2-3.5-2.1-1.5c.1-.3.1-.7.1-1z"/></svg>'
  };

  function iconForFilter(label){label=label.toLowerCase();if(label.includes('vista')||label.includes('periodo')||label.includes('fecha'))return icons.calendar;if(label.includes('tienda'))return icons.store;if(label.includes('área')||label.includes('area')||label.includes('sección')||label.includes('seccion'))return icons.grid;if(label.includes('actividad')||label.includes('catálogo')||label.includes('catalogo')||label.includes('origen'))return icons.list;if(label.includes('colaborador'))return icons.user;return icons.grid}
  function iconForTab(txt){txt=txt.toLowerCase();if(txt.includes('centro')||txt.includes('resumen'))return icons.table;if(txt.includes('convers'))return icons.chart;if(txt.includes('recuperación')||txt.includes('recuperacion'))return icons.dollar;if(txt.includes('productividad'))return icons.chart;if(txt.includes('recorrido'))return icons.pin;if(txt.includes('matriz'))return icons.table;if(txt.includes('captura'))return icons.list;if(txt.includes('cargar'))return icons.upload;if(txt.includes('estándar')||txt.includes('estandar'))return icons.settings;if(txt.includes('tienda'))return icons.store;if(txt.includes('sección')||txt.includes('seccion')||txt.includes('ubicación')||txt.includes('ubicacion'))return icons.grid;return icons.table}

  function decorateFilters(){
    $$('#v161FilterBar .v161-field').forEach(f=>{
      if(f.querySelector('.v164-filter-icon'))return;
      const label=f.querySelector('label')?.textContent||'';const i=document.createElement('span');i.className='v164-filter-icon';i.innerHTML=iconForFilter(label);f.appendChild(i);
    });
    const b=$('#v161FilterBar .v161-apply');if(b){b.innerHTML='<span class="v164-search-icon">'+icons.search+'</span><span>Consultar</span>'}
  }
  function decorateTabs(){
    $$('#operativoNav .switch,#analysisNav .switch,.v125-tab').forEach(b=>{
      if(b.querySelector('.v164-tab-icon'))return;
      const i=document.createElement('span');i.className='v164-tab-icon';i.innerHTML=iconForTab(b.textContent||'');b.prepend(i);
    });
  }
  function decorateCards(root=document){
    root.querySelectorAll?.('.kpi,.report-kpi,.v149-kpi,.v125-kpi').forEach(c=>{
      if(c.querySelector('.v164-kpi-icon'))return;
      const txt=(c.querySelector('.lab,.rk-label,small')?.textContent||c.textContent||'').toLowerCase();
      const i=document.createElement('span');i.className='v164-kpi-icon';i.innerHTML=txt.includes('$')||txt.includes('valor')||txt.includes('recuper')?icons.dollar:txt.includes('tienda')?icons.store:txt.includes('colab')?icons.user:txt.includes('pend')?icons.list:txt.includes('cumpl')?icons.target:txt.includes('pieza')||txt.includes('mercanc')?icons.box:icons.chart;c.prepend(i);
    });
  }
  function fixLogout(){
    const b=$('#logout');if(!b)return;if(!b.querySelector('.v164-logout-icon')){b.innerHTML='<span class="v164-logout-icon">'+icons.logout+'</span><span class="v164-logout-text">Cerrar sesión</span>'}
  }

  function ensureMatrixTab(){
    const nav=$('#operativoNav');if(!nav)return null;
    let b=nav.querySelector('[data-opview="Matriz de recolección"]');
    if(!b){b=document.createElement('button');b.className='switch';b.dataset.opview='Matriz de recolección';b.dataset.tabKey='operations.collection';b.textContent='Matriz de recolección';nav.appendChild(b)}
    if(!b.dataset.v164Bound){b.dataset.v164Bound='1';b.addEventListener('click',async e=>{e.preventDefault();e.stopPropagation();window.OP_VIEW='Matriz de recolección';nav.querySelectorAll('.switch').forEach(x=>x.classList.toggle('active',x===b));await renderMatrix();setTimeout(()=>{syncMatrixFilters();decorateAll()},50)},true)}
    return b;
  }

  function syncMatrixFilters(){
    const active=$('#operativoNav [data-opview="Matriz de recolección"].active');if(!active)return;
    const grid=$('#v161FilterGrid'),bar=$('#v161FilterBar');if(!grid||!bar)return;
    const wanted=[['Área','operAreaSelect'],['Actividad','operActivitySelect']];
    wanted.forEach(([label,id])=>{
      if(grid.querySelector('[data-v164-source="'+id+'"]'))return;
      const src=document.getElementById(id);if(!src)return;
      const w=document.createElement('div');w.className='v161-field';w.dataset.v164Source=id;
      const l=document.createElement('label');l.textContent=label;const s=document.createElement('select');[...src.options].forEach(o=>s.add(new Option(o.text,o.value,o.defaultSelected,o.selected)));s.value=src.value;s.addEventListener('change',()=>{src.value=s.value;src.dispatchEvent(new Event('change',{bubbles:true}))});w.append(l,s);const i=document.createElement('span');i.className='v164-filter-icon';i.innerHTML=iconForFilter(label);w.append(i);const apply=grid.querySelector('.v161-apply');grid.insertBefore(w,apply)
    });
    bar.classList.add('on');decorateFilters();
  }

  function periodParams(){return {period_type:document.getElementById('operPeriodMode')?.value||window.OPER_PERIOD?.type||'week',period_value:document.getElementById('operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',store:document.getElementById('operStoreSelect')?.value||'Compañía',area:document.getElementById('operAreaSelect')?.value||'Todas',activity:document.getElementById('operActivitySelect')?.value||'Todas'}}
  function pieStyle(s){const m=Number(s.muertos||0),c=Number(s.cajas||0),p=Number(s.probador||0),t=Math.max(1,m+c+p),a=m/t*100,b=(m+c)/t*100;return `conic-gradient(#1769e8 0 ${a}%,#24a7ef ${a}% ${b}%,#9bcdf8 ${b}% 100%)`}
  function pct(v,t){return t?Number(v||0)/t*100:0}
  function trendHtml(rows){const max=Math.max(1,...rows.map(r=>Number(r.total||0)));return `<div class="v164-trend">${rows.map(r=>{const vals=[['#1769e8',r.muertos],['#24a7ef',r.cajas],['#9bcdf8',r.probador]];return `<div class="v164-day">${vals.map(x=>`<div class="v164-bar" style="height:${Math.max(1,Number(x[1]||0)/max*100)}%;background:${x[0]}" title="${nf(x[1])}"></div>`).join('')}<span class="v164-value">${nf(r.total)}</span><span class="v164-day-label">${esc(r.label)}</span></div>`}).join('')}</div>`}

  async function renderMatrix(){
    const centro=$('#operativoCentro'),dyn=$('#operativoDynamic');centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    if($('#operativoDynamicTitle'))$('#operativoDynamicTitle').textContent='Matriz de recolección';if($('#operativoDynamicSub'))$('#operativoDynamicSub').textContent='Muertos, Cajas y Probador por día y horario';
    const cont=$('#operativoDynamicContent');if(!cont)return;cont.innerHTML='<div class="infoempty">Consultando Matriz de recolección…</div>';
    const p=periodParams(),q=new URLSearchParams(p);
    let data;try{data=await api('/api/operations/collection-matrix-v164?'+q,{timeoutMs:180000})}catch(err){cont.innerHTML='<div class="infoempty">No fue posible consultar la Matriz de recolección: '+esc(err?.message||err)+'</div>';return}
    const s=data.summary||{},src=data.source_totals||{},total=Number(src.muertos||0)+Number(src.cajas||0)+Number(src.probador||0);
    cont.innerHTML=`
      <div class="v164-matrix-head"><div><h2>Matriz de recolección de mercancía · ${esc((p.period_type||'').toLowerCase()==='week'?'Semanal':(p.period_type||''))}</h2><p>Seguimiento real de Muertos, Cajas y Probador por día y horario.</p></div></div>
      <div class="v164-matrix-kpis">
        <div class="v164-matrix-kpi" style="--c:#1769e8"><span class="ico">${icons.table}</span><small>Registros de recolección</small><b>${nf(s.records)}</b><span>Franjas con recolección registrada</span></div>
        <div class="v164-matrix-kpi" style="--c:#16a36a"><span class="ico">${icons.box}</span><small>Piezas recolectadas</small><b>${nf(s.pieces)}</b><span>Muertos + Cajas + Probador</span></div>
        <div class="v164-matrix-kpi" style="--c:#7135e8"><span class="ico">${icons.store}</span><small>Tiendas con recolección</small><b>${nf(s.stores)}</b><span>Con movimiento en el periodo</span></div>
        <div class="v164-matrix-kpi" style="--c:#ef376c"><span class="ico">${icons.calendar}</span><small>Franja con mayor volumen</small><b style="font-size:17px">${esc(s.peak_schedule||'Sin datos')}</b><span>${esc(s.peak_day||'')} · ${nf(s.peak_pieces)} pzas</span></div>
      </div>
      <div class="v164-panel"><h3>Matriz de recolección de mercancía</h3><div class="sub">Datos de horario y día tomados directamente de la base operativa vigente.</div><div class="tablewrap"><table class="table"><thead><tr><th>Día</th><th>Fecha</th><th>Horario</th><th>Tienda</th><th>Área</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Total</th><th>Responsable</th><th>Estatus</th></tr></thead><tbody>${(data.matrix||[]).length?(data.matrix||[]).map(r=>`<tr><td><b>${esc(r.day)}</b></td><td>${esc(r.date)}</td><td>${esc(r.schedule)}</td><td>${esc(r.store)}</td><td>${esc(r.area)}</td><td>${nf(r.muertos)}</td><td>${nf(r.cajas)}</td><td>${nf(r.probador)}</td><td><b>${nf(r.total)}</b></td><td>${esc(r.responsible)}</td><td><span class="v164-status">${esc(r.status)}</span></td></tr>`).join(''):'<tr><td colspan="11">Sin recolecciones para los filtros seleccionados.</td></tr>'}</tbody></table></div></div>
      <div class="v164-matrix-grid">
        <div class="v164-panel"><h3>Tendencia de recolección</h3><div class="sub">Muertos, Cajas y Probador dentro del periodo seleccionado.</div>${trendHtml(data.daily||[])}</div>
        <div class="v164-panel"><h3>Participación por fuente de mercancía</h3><div class="sub">Distribución de piezas recolectadas.</div><div class="v164-donut-wrap"><div class="v164-donut" style="background:${pieStyle(src)}"><div class="v164-donut-center"><b>${nf(total)}</b><span>piezas</span></div></div><div class="v164-legend"><div><i class="v164-dot" style="background:#1769e8"></i><span>Muertos</span><b>${pct(src.muertos,total).toFixed(1)}%</b></div><div><i class="v164-dot" style="background:#24a7ef"></i><span>Cajas</span><b>${pct(src.cajas,total).toFixed(1)}%</b></div><div><i class="v164-dot" style="background:#9bcdf8"></i><span>Probador</span><b>${pct(src.probador,total).toFixed(1)}%</b></div></div></div></div>
      </div>
      <div class="v164-panel"><h3>Resumen por tienda</h3><div class="sub">Recolecciones y piezas por tienda en el periodo.</div><div class="tablewrap"><table class="table"><thead><tr><th>#</th><th>Tienda</th><th>Franjas</th><th>Muertos</th><th>Cajas</th><th>Probador</th><th>Total piezas</th></tr></thead><tbody>${(data.stores||[]).length?(data.stores||[]).map((r,i)=>`<tr><td>#${i+1}</td><td><b>${esc(r.store)}</b></td><td>${nf(r.slots)}</td><td>${nf(r.muertos)}</td><td>${nf(r.cajas)}</td><td>${nf(r.probador)}</td><td><b>${nf(r.total)}</b></td></tr>`).join(''):'<tr><td colspan="7">Sin información.</td></tr>'}</tbody></table></div></div>`;
  }

  // Conserva todas las vistas existentes intactas; sólo intercepta la nueva.
  const previousRender=window.renderOperativoView;
  if(typeof previousRender==='function'){
    window.renderOperativoView=async function(name,force=false){if(name==='Matriz de recolección')return renderMatrix();const out=await previousRender.apply(this,arguments);setTimeout(decorateAll,20);return out}
  }

  function decorateAll(){ensureMatrixTab();decorateFilters();decorateTabs();decorateCards(document);fixLogout();if($('#operativoNav [data-opview="Matriz de recolección"].active'))syncMatrixFilters()}
  function schedule(){[0,80,220,600,1200].forEach(ms=>setTimeout(decorateAll,ms))}

  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-main],#operativoNav,#analysisNav,.v125-tabs,#v161FilterBar'))schedule();
    if(e.target.closest?.('#v161FilterBar .v161-apply')&&$('#operativoNav [data-opview="Matriz de recolección"].active'))setTimeout(renderMatrix,80);
  },true);
  document.addEventListener('change',e=>{if(e.target?.matches?.('select,input'))schedule()},true);
  const obs=new MutationObserver(()=>{clearTimeout(window.__v164mo);window.__v164mo=setTimeout(decorateAll,80)});if(document.body)obs.observe(document.body,{childList:true,subtree:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();
  console.info('[V164] Filtros/pestañas con iconos, tarjetas de boceto y Matriz de recolección real instalados.');
})();
</script>'''

    @m.app.middleware("http")
    async def _v164_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v164-filters-cards-matrix-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v164-filters-cards-matrix-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache", "Expires": "0",
                "X-Operations-UI-Version": "V164-FILTERS-CARDS-MATRIX",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V164] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V164_FILTERS_CARDS_MATRIX = True
    print("[V164] Filtros/tabs con iconos + tarjetas boceto + Matriz de recolección real.", flush=True)
