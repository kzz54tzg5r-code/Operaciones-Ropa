"""V240 · Centro Operativo 4 vistas + Recorridos calendario/semanas.

Cierra las observaciones de 2026-10-02:
- Centro Operativo mantiene Día / Semanal / Mensual / Anual de forma autoritativa.
- Recuperación por tienda conserva la tabla en Semanal/Mensual/Anual; se elimina sólo su gráfica.
- Operación permanece como módulo principal y se retira cualquier pestaña duplicada de C&M.
- En C&M el filtro Actividad sólo ofrece Clasificado/Acondicionado/Ubicado/Pizca.
- Matriz de recolección fija de 10:00 a 19:00, completa y sin gráfica secundaria.
- Recorridos por tienda en calendario: días para Semanal y semanas ISO para Mensual/Anual.
- Tendencia de recolección como 4 tarjetas semanales con variación vs semana anterior,
  incluyendo una quinta semana oculta para calcular la primera variación visible.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import math
import re
import unicodedata

from fastapi import Request
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V240_CENTER_ROUTES_CALENDAR", False):
        return

    # Operación ya es módulo principal desde V124. No debe volver a existir como
    # pestaña administrable dentro de Cambios y Muertos.
    try:
        m.REPORT_TABS.pop("operations.operation", None)
    except Exception:
        pass
    try:
        with m.db() as con:
            con.execute("DELETE FROM report_tab_visibility WHERE tab_key='operations.operation'")
    except Exception:
        pass

    ALLOWED_ACTIVITIES = ("Clasificado", "Acondicionado", "Ubicado", "Pizca")
    DAY_SHORT = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
    DAY_FULL = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

    def norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return " ".join(text.casefold().strip().split())

    def num(value):
        try:
            x = float(value or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def bounds(kind, value):
        kind = str(kind or "month").strip().lower()
        value = str(value or "").strip()
        today = date.today()
        if kind == "day":
            try:
                d = date.fromisoformat(value[:10])
            except Exception:
                d = today
            return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt:
                y, w = int(mt.group(1)), int(mt.group(2))
            else:
                iso = today.isocalendar()
                y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1)
            return d, d + timedelta(days=6)
        if kind == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            if mt:
                y, mo = int(mt.group(1)), int(mt.group(2))
            else:
                y, mo = today.year, today.month
            start = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return start, nxt - timedelta(days=1)
        if kind == "year":
            try:
                y = int(value[:4])
            except Exception:
                y = today.year
            return date(y, 1, 1), date(y, 12, 31)
        return date(2000, 1, 1), today

    def selected_store(actor, requested):
        try:
            return str(m.effective_store(actor, requested) or "Compañía")
        except Exception:
            return str(requested or "Compañía")

    def row_date(row):
        try:
            return date.fromisoformat(str(row.get("date") or "")[:10])
        except Exception:
            return None

    def accepted(row, selected, area, activity, start, end):
        d = row_date(row)
        if d is None or d < start or d > end:
            return None
        if selected != "Compañía" and norm(row.get("store")) != norm(selected):
            return None
        if str(area or "") not in ("", "Todas", "Todos") and norm(row.get("area")) != norm(area):
            return None
        if str(activity or "") not in ("", "Todas", "Todos"):
            act = row.get("activity") or row.get("activity_original") or ""
            if norm(act) != norm(activity):
                return None
        return d

    def hour_of(value):
        raw = str(value or "").strip()
        mt = re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)", raw)
        if mt:
            return int(mt.group(1))
        try:
            x = float(raw)
            if 0 <= x < 1:
                return int(x * 24)
        except Exception:
            pass
        return None

    @m.app.get("/api/operations/collection-hour-matrix-v240")
    def collection_hour_matrix_v240(
        request: Request,
        period_type: str = "week",
        period_value: str = "",
        store: str = "Compañía",
        area: str = "Todas",
        activity: str = "Todas",
    ):
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        selected = selected_store(actor, store)
        grouped = defaultdict(lambda: {"muertos": 0.0, "cajas": 0.0, "probador": 0.0})
        totals = {"muertos": 0.0, "cajas": 0.0, "probador": 0.0}
        stores = set()

        for row in list((m.load_ops() or {}).get("rows") or []):
            d = accepted(row, selected, area, activity, start, end)
            if d is None:
                continue
            muertos = num(row.get("muertos"))
            cajas = num(row.get("cajas"))
            probador = num(row.get("probador"))
            if muertos <= 0 and cajas <= 0 and probador <= 0:
                continue
            h = hour_of(row.get("start_time"))
            # Regla operativa solicitada: después de las 09:00 y hasta 19:00.
            if h is None or h < 10 or h > 19:
                continue
            cell = grouped[(h, d.weekday())]
            cell["muertos"] += muertos
            cell["cajas"] += cajas
            cell["probador"] += probador
            totals["muertos"] += muertos
            totals["cajas"] += cajas
            totals["probador"] += probador
            st = str(row.get("store") or "").strip()
            if st:
                stores.add(st)

        hours = []
        for h in range(10, 20):
            cells = []
            for dno in range(7):
                cell = grouped[(h, dno)]
                total = cell["muertos"] + cell["cajas"] + cell["probador"]
                cells.append({
                    "day": DAY_FULL[dno],
                    "total": total,
                    "muertos": cell["muertos"],
                    "cajas": cell["cajas"],
                    "probador": cell["probador"],
                })
            hours.append({
                "hour": h,
                "label": f"{h:02d}:00",
                "cells": cells,
                "total": sum(c["total"] for c in cells),
            })
        return {
            "days": list(DAY_FULL),
            "hours": hours,
            "summary": {
                "pieces": sum(totals.values()),
                "stores": len(stores),
                "first_hour": 10,
                "last_hour": 19,
            },
            "source_totals": totals,
        }

    def week_key(d):
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    @m.app.get("/api/operations/routes-calendar-v240")
    def routes_calendar_v240(
        request: Request,
        period_type: str = "week",
        period_value: str = "",
        store: str = "Compañía",
        area: str = "Todas",
        activity: str = "Todas",
    ):
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        selected = selected_store(actor, store)
        source = list((m.load_ops() or {}).get("rows") or [])

        if period_type == "week":
            dates = [start + timedelta(days=i) for i in range(7)]
            columns = [{
                "key": d.isoformat(),
                "label": DAY_SHORT[d.weekday()],
                "sub": f"{d.day:02d}",
                "date": d.isoformat(),
            } for d in dates]
            key_for = lambda d: d.isoformat()
        elif period_type == "day":
            columns = [{
                "key": start.isoformat(),
                "label": DAY_SHORT[start.weekday()],
                "sub": f"{start.day:02d}",
                "date": start.isoformat(),
            }]
            key_for = lambda d: d.isoformat()
        else:
            # Mes y anual: una columna compacta por semana ISO que intersecta el periodo.
            monday = start - timedelta(days=start.weekday())
            last_monday = end - timedelta(days=end.weekday())
            weeks = []
            cursor = monday
            while cursor <= last_monday:
                iso = cursor.isocalendar()
                weeks.append({
                    "key": f"{iso.year}-W{iso.week:02d}",
                    "label": f"Sem {iso.week}",
                    "sub": "",
                    "start": cursor.isoformat(),
                })
                cursor += timedelta(days=7)
            columns = weeks
            key_for = week_key

        grouped = defaultdict(float)
        stores_seen = set()
        for row in source:
            d = accepted(row, selected, area, activity, start, end)
            if d is None:
                continue
            value = num(row.get("recorridos"))
            if value <= 0:
                continue
            st = str(row.get("store") or "Sin tienda").strip() or "Sin tienda"
            grouped[(st, key_for(d))] += value
            stores_seen.add(st)

        if selected != "Compañía":
            stores = [selected]
        else:
            active = list(m.store_names(True) or [])
            stores = [s for s in active if s in stores_seen]
            stores += sorted(s for s in stores_seen if s not in set(stores))
            if not stores:
                stores = active

        rows = []
        for st in stores:
            cells = [grouped[(st, c["key"])] for c in columns]
            rows.append({"store": st, "cells": cells, "total": sum(cells)})
        rows.sort(key=lambda x: (-x["total"], norm(x["store"])))

        totals = [sum(row["cells"][i] for row in rows) for i in range(len(columns))]
        return {
            "period_type": period_type,
            "period_value": period_value,
            "columns": columns,
            "rows": rows,
            "totals": totals,
            "grand_total": sum(totals),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }

    def percent_change(current, previous):
        current = num(current)
        previous = num(previous)
        if previous <= 0:
            return None
        return (current / previous - 1.0) * 100.0

    @m.app.get("/api/operations/collection-week-summary-v240")
    def collection_week_summary_v240(
        request: Request,
        period_type: str = "month",
        period_value: str = "",
        store: str = "Compañía",
        area: str = "Todas",
        activity: str = "Todas",
    ):
        actor = m.require_user(request)
        _start, end = bounds(period_type, period_value)
        selected = selected_store(actor, store)
        source = list((m.load_ops() or {}).get("rows") or [])
        anchor = end - timedelta(days=end.weekday())

        # Cinco semanas de datos; se muestran sólo las últimas cuatro.
        # La primera oculta sirve como base de comparación.
        windows = []
        for offset in range(4, -1, -1):
            ws = anchor - timedelta(days=7 * offset)
            we = ws + timedelta(days=6)
            windows.append((ws, we))

        values = []
        for ws, we in windows:
            totals = {"muertos": 0.0, "cajas": 0.0, "probador": 0.0}
            for row in source:
                d = accepted(row, selected, area, activity, ws, we)
                if d is None:
                    continue
                totals["muertos"] += num(row.get("muertos"))
                totals["cajas"] += num(row.get("cajas"))
                totals["probador"] += num(row.get("probador"))
            total = totals["muertos"] + totals["cajas"] + totals["probador"]
            iso = ws.isocalendar()
            values.append({
                "key": f"{iso.year}-W{iso.week:02d}",
                "week": iso.week,
                "year": iso.year,
                "label": f"Sem {iso.week}",
                "start": ws.isoformat(),
                "end": we.isoformat(),
                "total": total,
                **totals,
            })

        cards = []
        for idx in range(1, len(values)):
            cur = dict(values[idx])
            prev = values[idx - 1]
            cur["previous_label"] = prev["label"]
            cur["total_pct"] = percent_change(cur["total"], prev["total"])
            cur["muertos_pct"] = percent_change(cur["muertos"], prev["muertos"])
            cur["cajas_pct"] = percent_change(cur["cajas"], prev["cajas"])
            cur["probador_pct"] = percent_change(cur["probador"], prev["probador"])
            cards.append(cur)

        return {
            "cards": cards[-4:],
            "hidden_previous": values[0] if values else None,
            "period_type": period_type,
        }

    css = r'''<style id="v240-center-routes-css">
/* Operación sólo vive como módulo principal. */
body.v238-module-operativo #operativoNav>button[data-opview="Operación"],
body.v238-module-operativo #operativoNav>button[data-tab-key="operations.operation"]{
  display:none!important;
}

/* Centro Operativo: selector siempre visible y con sus cuatro vistas. */
body.v238-module-operativo #operPeriodModeWrap{
  display:block!important;
}
body.v238-module-operativo #operPeriodMode{
  display:block!important;
}

/* Sólo desaparece la gráfica de recuperación, nunca su tabla. */
.recovery-svg,
.chart-box:has(.recovery-svg){
  display:none!important;
}

/* Recorridos: matriz completa 10:00–19:00, sin scroll vertical interno. */
#v166RoutesMatrix{margin:0 0 10px!important}
#v166RoutesMatrix .panel{padding:10px!important}
#v166RoutesMatrix .tablewrap,
#v166RoutesMatrix .v240-matrix-wrap{
  max-height:none!important;
  height:auto!important;
  overflow-x:auto!important;
  overflow-y:visible!important;
  -webkit-overflow-scrolling:touch;
}
#v166RoutesMatrix .v166-matrix-table{
  min-width:920px!important;
}
#v166RoutesMatrix .v166-matrix-table th,
#v166RoutesMatrix .v166-matrix-table td{
  padding:7px 8px!important;
}
#v166RoutesMatrix .v166-matrix-cell b{font-size:10px!important}
#v166RoutesMatrix .v166-matrix-cell small{font-size:6.7px!important}
#v167MatrixVisual{display:none!important}

/* Calendario de recorridos. */
.v240-route-calendar{
  max-width:100%;
  overflow:auto;
  -webkit-overflow-scrolling:touch;
  border:1px solid #d9e5f1;
  border-radius:12px;
}
.v240-route-calendar table{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  min-width:760px;
}
.v240-route-calendar.month table{min-width:920px}
.v240-route-calendar.year table{min-width:2600px}
.v240-route-calendar th{
  position:sticky;top:0;z-index:3;
  background:#124a80;color:#fff;
  padding:7px 5px;
  font-size:8px;font-weight:900;text-align:center;
  white-space:nowrap;
}
.v240-route-calendar td{
  padding:7px 5px;border-bottom:1px solid #e7edf5;
  font-size:8px;color:#294b70;text-align:center;
  font-variant-numeric:tabular-nums;
}
.v240-route-calendar th:first-child,
.v240-route-calendar td:first-child{
  position:sticky;left:0;z-index:4;
  width:125px;min-width:125px;max-width:125px;
  text-align:left;font-weight:900;
}
.v240-route-calendar th:first-child{z-index:5}
.v240-route-calendar td:first-child{background:#fff}
.v240-route-calendar tbody tr:nth-child(even) td:first-child{background:#f7faff}
.v240-route-calendar tbody tr:nth-child(even){background:#f7faff}
.v240-route-calendar .v240-day-head{display:grid;place-items:center;gap:1px}
.v240-route-calendar .v240-day-head b{font-size:8px}
.v240-route-calendar .v240-day-head small{font-size:6.5px;opacity:.82;font-weight:800}
.v240-route-calendar .v240-week-head{font-size:7px;letter-spacing:-.1px}
.v240-route-calendar .v240-total-row td{background:#edf5ff!important;font-weight:900}
.v240-route-calendar .v240-zero{color:#b1bdc9}

/* Resumen semanal de recolección. */
.v240-week-cards{
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:8px;
}
.v240-week-card{
  min-width:0;border:1px solid #d9e5f1;border-radius:13px;background:#fff;
  padding:10px 11px;
}
.v240-week-card-head{
  display:flex;justify-content:space-between;align-items:flex-start;gap:6px;
}
.v240-week-card-head b{font-size:11px;color:#123f73}
.v240-week-card-head small{font-size:6.8px;color:#8090a2;text-align:right}
.v240-week-total{margin-top:6px;color:#0f467d;font-size:24px;font-weight:950;line-height:1}
.v240-week-total small{font-size:8px;font-weight:800;color:#71849a}
.v240-delta{
  margin-top:5px;font-size:8px;font-weight:900;color:#60758f;
}
.v240-delta.up{color:#07894f}.v240-delta.down{color:#c43d3d}
.v240-week-detail{
  display:grid;grid-template-columns:1fr;gap:4px;margin-top:8px;padding-top:7px;border-top:1px solid #edf1f5;
}
.v240-week-detail-row{
  display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:5px;align-items:center;
  font-size:7px;color:#667c93;
}
.v240-week-detail-row b{font-size:8px;color:#274c70}
.v240-week-detail-row em{font-style:normal;font-size:6.7px;font-weight:900;color:#6e8297}
.v240-week-detail-row em.up{color:#07894f}.v240-week-detail-row em.down{color:#c43d3d}

@media(max-width:900px){
  .v240-week-cards{grid-template-columns:repeat(2,minmax(0,1fr))}
  .v240-route-calendar th:first-child,.v240-route-calendar td:first-child{
    width:92px;min-width:92px;max-width:92px;
  }
}
@media(max-width:520px){
  .v240-week-cards{grid-template-columns:1fr 1fr;gap:5px}
  .v240-week-card{padding:8px}
  .v240-week-total{font-size:19px}
  .v240-route-calendar{font-size:7px}
}
</style>'''

    js = r'''<script id="v240-center-routes-js">
(function(){
  if(window.__V240_CENTER_ROUTES)return;
  window.__V240_CENTER_ROUTES=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const CENTER='Centro Ejecutivo';
  const MODES=[['day','Día'],['week','Semanal'],['month','Mensual'],['year','Anual']];
  const MODE_LABEL={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'};
  const MODE_SUB={
    day:'Consulta por fecha · ingresos, pendientes y avance por tienda',
    week:'Semana ISO · operación y seguimiento consolidado',
    month:'Mes seleccionado · operación y desempeño consolidado',
    year:'Acumulado anual · operación y desempeño consolidado'
  };
  const ACTIVITIES=['Clasificado','Acondicionado','Ubicado','Pizca'];
  let centerSeq=0;
  let centerMode='';
  const periodByMode={};
  const routeCache=new Map();

  function norm(v){
    return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  }
  function esc(v){
    return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
  function nf(v){
    return Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  }
  function centerButton(){
    return q('#operativoNav [data-tab-key="operations.center"]')||q('#operativoNav [data-opview="Centro Ejecutivo"]');
  }
  function isCm(){
    return document.body.classList.contains('v238-module-operativo')||String(document.body.dataset.v163Module||'')==='operativo';
  }
  function isCenterActive(){
    return !!centerButton()?.classList.contains('active');
  }
  function yearsFrom(meta){
    const vals=[...(meta?.available_dates||[]),...(meta?.available_weeks||[]),...(meta?.available_months||[])];
    return Array.from(new Set(vals.map(v=>String(v||'').slice(0,4)).filter(v=>/^\d{4}$/.test(v)))).sort();
  }
  function listFor(meta,mode){
    if(mode==='day')return [...(meta?.available_dates||[])];
    if(mode==='week')return [...(meta?.available_weeks||[])];
    if(mode==='month')return [...(meta?.available_months||[])];
    return yearsFrom(meta||{});
  }
  function savedMode(){
    const dom=q('#operPeriodMode')?.value;
    if(MODES.some(x=>x[0]===dom)&&q('#operPeriodMode')?.options.length===4)return dom;
    if(MODES.some(x=>x[0]===centerMode))return centerMode;
    try{
      const v=localStorage.getItem('operacionesRopa.centerMode.v240');
      if(MODES.some(x=>x[0]===v))return v;
    }catch(_){}
    return 'month';
  }
  function saveMode(mode){
    centerMode=MODES.some(x=>x[0]===mode)?mode:'month';
    try{localStorage.setItem('operacionesRopa.centerMode.v240',centerMode)}catch(_){}
    try{
      window.V166_VIEW_TYPE=centerMode;
      OPER_PERIOD.type=centerMode;
    }catch(_){}
  }
  function setOptions(el,values,current){
    if(!el)return;
    const sig=values.map(x=>Array.isArray(x)?x.join('|'):String(x)).join('¦');
    const old=[...el.options].map(o=>o.value+'|'+o.text).join('¦');
    const expected=values.map(x=>Array.isArray(x)?x[0]+'|'+x[1]:String(x)+'|'+String(x)).join('¦');
    if(old!==expected){
      el.innerHTML='';
      values.forEach(x=>{
        const p=Array.isArray(x)?x:[x,x];
        el.add(new Option(p[1],p[0]));
      });
    }
    if([...el.options].some(o=>o.value===current))el.value=current;
  }
  function setAllowedActivities(){
    if(!isCm())return;
    const el=q('#operActivitySelect');
    if(!el)return;
    const current=ACTIVITIES.includes(el.value)?el.value:'';
    const values=[['','Todas'],...ACTIVITIES.map(x=>[x,x])];
    setOptions(el,values,current);
    el.value=current;
  }
  function removeDuplicateOperation(){
    qa('#operativoNav>button').forEach(btn=>{
      const key=String(btn.dataset.tabKey||'');
      const op=norm(btn.dataset.opview||'');
      const txt=norm(btn.dataset.v232Original||btn.dataset.rtLabel||btn.title||btn.textContent);
      if(key==='operations.operation'||op==='operacion'||txt==='operacion')btn.remove();
    });
    qa('#tabVisibilityOptions input[data-tab-setting="operations.operation"]').forEach(input=>input.closest('label')?.remove());
  }
  function removeDistribution(){
    q('#v167MatrixVisual')?.remove();
    qa('#operativoDynamicContent .chart-box,#operativoDynamicContent .panel').forEach(box=>{
      const title=norm(q('.chart-title,.title,h3',box)?.textContent||'');
      if(title.includes('distribucion por hora y dia'))box.remove();
    });
  }
  function removeRecoveryGraph(){
    qa('.recovery-svg').forEach(svg=>{
      const box=svg.closest('.chart-box');
      if(box)box.remove();else svg.remove();
    });
  }
  try{window.recoveryHorizontalChart=()=>''}catch(_){}

  function ensureCenterControls(meta,mode,reset=false){
    const bar=q('#operativoPeriodBar'),wrap=q('#operPeriodModeWrap'),ms=q('#operPeriodMode'),ps=q('#operPeriodSelect'),lab=q('#operPeriodLabel');
    if(!bar||!wrap||!ms||!ps||!lab)return'';
    bar.classList.remove('hidden');bar.style.removeProperty('display');
    wrap.classList.remove('hidden');wrap.style.removeProperty('display');
    setOptions(ms,MODES,mode);
    ms.value=mode;
    const list=listFor(meta||{},mode).filter(Boolean);
    let desired=reset?'':String(periodByMode[mode]||'');
    if(!desired){
      try{if(OPER_PERIOD.type===mode)desired=String(OPER_PERIOD.value||'')}catch(_){}
    }
    if(!list.includes(desired))desired=list.at(-1)||'';
    setOptions(ps,list,desired);
    if(desired)ps.value=desired;
    lab.textContent=mode==='day'?'Fecha':mode==='week'?'Semana ISO':mode==='month'?'Mes':'Año';
    periodByMode[mode]=desired;
    try{OPER_PERIOD.type=mode;OPER_PERIOD.value=desired;window.V166_VIEW_TYPE=mode}catch(_){}
    setAllowedActivities();
    return desired;
  }
  function markCenter(mode){
    const btn=centerButton();
    qa('#operativoNav>button').forEach(x=>{
      const on=x===btn;
      x.classList.toggle('active',on);
      x.setAttribute('aria-selected',on?'true':'false');
    });
    try{OP_VIEW=CENTER}catch(_){}
    const title=q('#operativoDynamicTitle'),sub=q('#operativoDynamicSub');
    if(title)title.textContent='Centro Operativo · '+MODE_LABEL[mode];
    if(sub)sub.textContent=MODE_SUB[mode];
  }
  async function meta(){
    if(window.OPSDATA)return window.OPSDATA;
    try{
      const d=await api('/api/operations/meta',{timeoutMs:30000});
      window.OPSDATA=d;
      return d;
    }catch(_){return{}}
  }
  async function fetchCenter(mode,value){
    const store=q('#operStoreSelect')?.value||'Compañía';
    const area=q('#operAreaSelect')?.value||'';
    const activity=q('#operActivitySelect')?.value||'';
    if(mode==='year'){
      return await api('/api/operations/year?year='+encodeURIComponent(value)+'&store='+encodeURIComponent(store)+'&area='+encodeURIComponent(area)+'&activity='+encodeURIComponent(activity)+'&compact=true&project_only=false',{timeoutMs:180000});
    }
    return await api('/api/operations/project-scope-v151?store='+encodeURIComponent(store)+'&period_type='+encodeURIComponent(mode)+'&period_value='+encodeURIComponent(value)+'&area='+encodeURIComponent(area)+'&activity='+encodeURIComponent(activity)+'&compact=true',{timeoutMs:180000});
  }
  function centerHtml(data,mode,value){
    const mt=data?.metrics||{},rec=data?.recovery_by_store||[],stores=data?.stores||[];
    let out='';
    if(typeof monthlyCrossTable==='function')out+=monthlyCrossTable(mt,mode==='day');
    if(mode!=='day'&&typeof recoveryTable==='function'){
      out+='<div class="title">Recuperación por tienda</div>'+recoveryTable(rec);
    }
    const ordered=typeof orderByConversion==='function'
      ?orderByConversion(stores.filter(x=>x.is_project),rec)
      :stores.filter(x=>x.is_project);
    if(typeof operationalDetailTable==='function'){
      const detailLabel=mode==='day'?'Detalle operativo · '+value:'Detalle operativo · tiendas del proyecto';
      out+='<div class="title">'+esc(detailLabel)+'</div>'+
        (ordered.length?operationalDetailTable(ordered,rec):'<div class="infoempty">No hay tiendas guardadas como Proyecto.</div>');
    }
    if(ordered.length&&typeof opsComboSvg==='function'){
      const scope=(q('#operStoreSelect')?.value||'Compañía')==='Compañía'?'Todas las tiendas':q('#operStoreSelect').value;
      out+=opsComboSvg(ordered,value||MODE_LABEL[mode],scope,rec);
    }
    if(typeof reportDownloadBar==='function')out+=reportDownloadBar(CENTER);
    return out;
  }
  async function renderCenter(mode=savedMode(),reset=false){
    const seq=++centerSeq;
    saveMode(mode);
    removeDuplicateOperation();
    const dmeta=await meta();
    if(seq!==centerSeq)return;
    const value=ensureCenterControls(dmeta,mode,reset);
    markCenter(mode);
    const dyn=q('#operativoDynamic'),centro=q('#operativoCentro'),host=q('#operativoDynamicContent');
    centro?.classList.add('hidden');dyn?.classList.remove('hidden');
    if(host)host.innerHTML='<div class="infoempty">Cargando '+MODE_LABEL[mode].toLowerCase()+'…</div>';
    try{
      const data=await fetchCenter(mode,value);
      if(seq!==centerSeq)return;
      if(host)host.innerHTML=centerHtml(data,mode,value);
      markCenter(mode);
      ensureCenterControls(dmeta,mode,false);
      removeRecoveryGraph();
    }catch(err){
      if(seq!==centerSeq)return;
      if(host)host.innerHTML='<div class="infoempty">No fue posible cargar la vista '+MODE_LABEL[mode]+': '+esc(err?.message||err)+'</div>';
      markCenter(mode);ensureCenterControls(dmeta,mode,false);
    }
  }
  window.V240_renderCenter=renderCenter;

  /* ---------- Recorridos V240 ---------- */
  function routeParams(){
    const type=['day','week','month','year'].includes(q('#operPeriodMode')?.value)?q('#operPeriodMode').value:(window.V166_VIEW_TYPE||window.OPER_PERIOD?.type||'month');
    return {
      period_type:type,
      period_value:q('#operPeriodSelect')?.value||window.OPER_PERIOD?.value||'',
      store:q('#operStoreSelect')?.value||'Compañía',
      area:q('#operAreaSelect')?.value||'Todas',
      activity:q('#operActivitySelect')?.value||'Todas'
    };
  }
  function queryString(p){
    return new URLSearchParams(p).toString();
  }
  function matrixMarkup(d){
    const body=(d.hours||[]).map(r=>'<tr><td><b>'+esc(r.label)+'</b></td>'+
      (r.cells||[]).map(c=>'<td><div class="v166-matrix-cell"><b class="'+(Number(c.total||0)===0?'v166-zero':'')+'">'+nf(c.total)+'</b>'+
        (Number(c.total||0)>0?'<small>M '+nf(c.muertos)+' · C '+nf(c.cajas)+' · P '+nf(c.probador)+'</small>':'<small>—</small>')+
      '</div></td>').join('')+'<td><b>'+nf(r.total)+'</b></td></tr>').join('');
    return '<div class="panel"><div class="v166-matrix-head"><div><h3>Matriz de recolección · día y hora</h3>'+
      '<p>Lunes a domingo · horario operativo de 10:00 a 19:00.</p></div><b style="color:#103f7d">'+nf(d.summary?.pieces)+' pzas</b></div>'+
      '<div class="v240-matrix-wrap"><table class="table v166-matrix-table"><thead><tr><th>Hora</th>'+
      (d.days||[]).map(x=>'<th>'+esc(x)+'</th>').join('')+'<th>Total</th></tr></thead><tbody>'+body+'</tbody></table></div></div>';
  }
  function calendarMarkup(d){
    const kind=d.period_type||'week';
    const heads=(d.columns||[]).map(c=>{
      if(kind==='week'||kind==='day')return '<th><span class="v240-day-head"><b>'+esc(c.label)+'</b><small>'+esc(c.sub||'')+'</small></span></th>';
      return '<th><span class="v240-week-head">'+esc(c.label)+'</span></th>';
    }).join('');
    const rows=(d.rows||[]).map(r=>'<tr><td>'+esc(r.store)+'</td>'+
      (r.cells||[]).map(v=>'<td class="'+(Number(v||0)===0?'v240-zero':'')+'">'+nf(v)+'</td>').join('')+
      '<td><b>'+nf(r.total)+'</b></td></tr>').join('');
    const totals='<tr class="v240-total-row"><td>Total</td>'+
      (d.totals||[]).map(v=>'<td>'+nf(v)+'</td>').join('')+'<td>'+nf(d.grand_total)+'</td></tr>';
    return '<div class="chart-title">Recorridos por tienda · calendario</div>'+
      '<div class="v240-route-calendar '+esc(kind)+'"><table><thead><tr><th>Tienda</th>'+heads+'<th>Total</th></tr></thead>'+
      '<tbody>'+rows+totals+'</tbody></table></div>';
  }
  function pctText(v){
    if(v===null||v===undefined||!Number.isFinite(Number(v)))return 'Sin base';
    const n=Number(v);
    return (n>0?'+':'')+n.toLocaleString('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
  }
  function pctClass(v){
    if(v===null||v===undefined||!Number.isFinite(Number(v)))return'';
    return Number(v)>0?'up':Number(v)<0?'down':'';
  }
  function trendMarkup(d){
    return '<div class="chart-title">Resumen semanal de recolección</div>'+
      '<div class="v240-week-cards">'+(d.cards||[]).map(card=>
        '<div class="v240-week-card"><div class="v240-week-card-head"><b>'+esc(card.label)+'</b><small>'+esc(card.start)+'<br>'+esc(card.end)+'</small></div>'+
        '<div class="v240-week-total">'+nf(card.total)+' <small>pzas</small></div>'+
        '<div class="v240-delta '+pctClass(card.total_pct)+'">'+pctText(card.total_pct)+' vs '+esc(card.previous_label)+'</div>'+
        '<div class="v240-week-detail">'+
          [['Muertos','muertos','muertos_pct'],['Cajas','cajas','cajas_pct'],['Probador','probador','probador_pct']].map(x=>
            '<div class="v240-week-detail-row"><span>'+x[0]+'</span><b>'+nf(card[x[1]])+'</b><em class="'+pctClass(card[x[2]])+'">'+pctText(card[x[2]])+'</em></div>'
          ).join('')+
        '</div></div>'
      ).join('')+'</div>';
  }
  function findRouteBox(kind){
    const boxes=qa('#operativoDynamicContent .chart-box');
    if(kind==='calendar'){
      return boxes.find(x=>{const t=norm(q('.chart-title',x)?.textContent||'');return t.includes('recorridos por dia')||t.includes('recorridos por tienda')});
    }
    return boxes.find(x=>{const t=norm(q('.chart-title',x)?.textContent||'');return t.includes('recolecciones por hora')||t.includes('tendencia de recoleccion')||t.includes('resumen semanal de recoleccion')});
  }
  async function enhanceRoutes(force=false){
    if(!isCm())return;
    const active=q('#operativoNav .active');
    const key=String(active?.dataset.tabKey||'');
    const op=norm(active?.dataset.opview||active?.dataset.rtLabel||active?.textContent||'');
    if(key!=='operations.routes'&&!op.includes('recorridos'))return;
    removeDistribution();setAllowedActivities();
    const p=routeParams(),sig=queryString(p);
    let data=routeCache.get(sig);
    if(!data||force||Date.now()-data.at>45000){
      try{
        const [matrix,calendar,trend]=await Promise.all([
          api('/api/operations/collection-hour-matrix-v240?'+sig,{timeoutMs:120000}),
          api('/api/operations/routes-calendar-v240?'+sig,{timeoutMs:120000}),
          api('/api/operations/collection-week-summary-v240?'+sig,{timeoutMs:120000})
        ]);
        data={at:Date.now(),matrix,calendar,trend};routeCache.set(sig,data);
      }catch(err){
        console.warn('[V240] recorridos',err);return;
      }
    }
    const host=q('#operativoDynamicContent');if(!host)return;
    let matrixRoot=q('#v166RoutesMatrix');
    if(!matrixRoot){
      matrixRoot=document.createElement('div');matrixRoot.id='v166RoutesMatrix';host.prepend(matrixRoot);
    }
    if(matrixRoot.dataset.v240Sig!==sig||!q('.v240-matrix-wrap',matrixRoot)){
      matrixRoot.innerHTML=matrixMarkup(data.matrix);
      matrixRoot.dataset.v240Sig=sig;
    }
    q('#v167MatrixVisual')?.remove();

    let cal=findRouteBox('calendar');
    if(!cal){
      cal=document.createElement('div');cal.className='chart-box v240-calendar-box';host.append(cal);
    }
    if(cal.dataset.v240Sig!==sig||!q('.v240-route-calendar',cal)){
      cal.innerHTML=calendarMarkup(data.calendar);
      cal.dataset.v240Sig=sig;
    }

    let trend=findRouteBox('trend');
    if(!trend){
      trend=document.createElement('div');trend.className='chart-box v240-trend-box';host.append(trend);
    }
    if(trend.dataset.v240Sig!==sig||!q('.v240-week-cards',trend)){
      trend.innerHTML=trendMarkup(data.trend);
      trend.dataset.v240Sig=sig;
    }

    // Retirar cualquier visual heredado que V167 pueda haber vuelto a insertar.
    removeDistribution();
    qa('#operativoDynamicContent .chart-box').forEach(box=>{
      if(box===cal||box===trend)return;
      const title=norm(q('.chart-title',box)?.textContent||'');
      if(title.includes('recolecciones por dia')||title.includes('distribucion por hora y dia')||title.includes('tendencia de recoleccion'))box.remove();
    });
  }
  window.V240_enhanceRoutes=enhanceRoutes;

  /* ---------- Autoridad final de navegación/filtros ---------- */
  const previousRender=window.renderOperativoView;
  if(typeof previousRender==='function'){
    window.renderOperativoView=async function(name,force=false){
      const n=norm(name);
      if(name===CENTER||n==='centro operativo'||n==='centro ejecutivo'){
        return await renderCenter(savedMode(),false);
      }
      const out=await previousRender.apply(this,arguments);
      removeDuplicateOperation();setAllowedActivities();removeRecoveryGraph();
      if(n.includes('recorridos')){
        [40,250,700,1400].forEach((ms,i)=>setTimeout(()=>enhanceRoutes(i===0&&!!force),ms));
      }
      return out;
    };
  }

  function captureEvents(){
    document.addEventListener('click',e=>{
      const center=e.target.closest?.('#operativoNav [data-tab-key="operations.center"],#operativoNav [data-opview="Centro Ejecutivo"]');
      if(center){
        e.preventDefault();e.stopImmediatePropagation();
        document.body.dataset.v163Module='operativo';
        document.body.classList.add('v238-module-operativo');
        renderCenter(savedMode(),false);
        return;
      }
      const apply=e.target.closest?.('#operPeriodApply');
      if(apply&&isCenterActive()){
        e.preventDefault();e.stopImmediatePropagation();
        const mode=savedMode(),ps=q('#operPeriodSelect');
        if(ps)periodByMode[mode]=ps.value;
        renderCenter(mode,false);
      }
    },true);

    document.addEventListener('change',e=>{
      if(e.target?.id==='operPeriodMode'&&isCenterActive()){
        e.stopImmediatePropagation();
        const mode=e.target.value;
        saveMode(mode);
        periodByMode[mode]='';
        renderCenter(mode,true);
        return;
      }
      if(e.target?.id==='operPeriodSelect'&&isCenterActive()){
        e.stopImmediatePropagation();
        const mode=savedMode();
        periodByMode[mode]=e.target.value;
        try{OPER_PERIOD.type=mode;OPER_PERIOD.value=e.target.value}catch(_){}
        renderCenter(mode,false);
        return;
      }
      if(isCm()&&['operStoreSelect','operAreaSelect','operActivitySelect'].includes(e.target?.id)){
        setAllowedActivities();
        const active=q('#operativoNav .active');
        if(String(active?.dataset.tabKey||'')==='operations.routes'){
          setTimeout(()=>enhanceRoutes(true),60);
        }
      }
    },true);
  }

  let tidy=0;
  const observer=new MutationObserver(()=>{
    clearTimeout(tidy);
    tidy=setTimeout(()=>{
      removeDuplicateOperation();setAllowedActivities();removeRecoveryGraph();removeDistribution();
      if(isCenterActive()){
        const mode=savedMode();
        meta().then(d=>ensureCenterControls(d,mode,false));
      }
      enhanceRoutes(false);
    },35);
  });

  function init(){
    removeDuplicateOperation();setAllowedActivities();removeRecoveryGraph();removeDistribution();
    captureEvents();
    if(!document.body.dataset.v240Observer){
      document.body.dataset.v240Observer='1';
      observer.observe(document.body,{subtree:true,childList:true});
    }
    [120,400,900,1800].forEach(ms=>setTimeout(()=>{
      removeDuplicateOperation();setAllowedActivities();removeRecoveryGraph();removeDistribution();
      if(isCenterActive())meta().then(d=>ensureCenterControls(d,savedMode(),false));
      enhanceRoutes(false);
    },ms));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();

  console.info('[V240] Centro 4 vistas + Recorridos calendario/semanas activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v240_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v240-center-routes-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v240-center-routes-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V240-CENTER-ROUTES",
            })
            return HTMLResponse(html, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print(f"[V240] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V240_CENTER_ROUTES_CALENDAR = True
    print("[V240] Centro 4 vistas + Recorridos calendario/semanas instalado.", flush=True)
