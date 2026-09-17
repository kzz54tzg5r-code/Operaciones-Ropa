from __future__ import annotations

from datetime import datetime
from fastapi import Request
from fastapi.responses import HTMLResponse
import threading
import time


def install(m):
    if getattr(m, "_V169_PERIOD_FRESHNESS", False):
        return

    raw_state = {
        "status": "pending",
        "source_file": "",
        "raw_operational_max": "",
        "raw_monthly_max": "",
        "parsed_max": "",
        "checked_at": "",
        "error": "",
    }

    def _max_date(current: str, candidate: str) -> str:
        candidate = str(candidate or "")[:10]
        if len(candidate) == 10 and candidate > str(current or ""):
            return candidate
        return str(current or "")

    def _scan_current_source():
        try:
            meta = m.load_operations_meta()
            parsed_dates = list(meta.get("available_dates") or [])
            raw_state["parsed_max"] = max(parsed_dates) if parsed_dates else ""
            raw = m.DATA_ROOT / "cambios_muertos_actual.xlsx"
            raw_state["source_file"] = str(meta.get("source_file") or raw.name)
            if not raw.exists():
                raw_state.update(status="missing", checked_at=datetime.now().isoformat(timespec="seconds"))
                print(f"[V169-COVERAGE] parsed_max={raw_state['parsed_max'] or 'none'} · raw source missing", flush=True)
                return

            op_max = ""
            month_max = ""
            with m._xlsx_stream_book(raw) as book:
                names = list(book.get("sheet_paths") or {})
                op_sheets = m._detect_operational_sheets(names)
                header_tokens = (
                    "fecha s","fecha","occurrence","ocurrencia","ocurrense","tienda","ubicacion","tabla",
                    "actividad realizada","area","numero de piezas","hora inicio","hora fin","nombre","nomina",
                    "motivo de ingreso","ingreso al area de acondicionado","recorridos"
                )
                for sheet in op_sheets:
                    try:
                        header_row, header = m._xlsx_best_header(book, sheet, header_tokens, minimum=4)
                        date_col = None
                        date_s_col = None
                        for idx, value in sorted(header.items()):
                            canonical = m._operational_canonical_header(value)
                            if canonical == "Fecha" and date_col is None:
                                date_col = idx
                            elif canonical == "Fecha s" and date_s_col is None:
                                date_s_col = idx
                        for row_number, values in m._xlsx_stream_rows(book, sheet):
                            if row_number <= header_row:
                                continue
                            raw_date = values.get(date_col) if date_col is not None else None
                            if (raw_date is None or raw_date == "") and date_s_col is not None:
                                raw_date = values.get(date_s_col)
                            ds, _w, _y, _mo = m._safe_date_iso(raw_date)
                            if ds:
                                op_max = _max_date(op_max, ds)
                    except Exception as exc:
                        print(f"[V169-COVERAGE] warning op sheet {sheet}: {type(exc).__name__}: {exc}", flush=True)

                monthly = [sheet for sheet in names if m._monthly_sheet_name(sheet)]
                archive = book["archive"]
                paths = book["sheet_paths"]
                shared = book["shared_value"]
                for sheet in monthly:
                    member = paths.get(sheet, "")
                    if not member or member not in archive.namelist():
                        continue
                    try:
                        rows = m._xlsx_monthly_rows(archive, member, shared)
                        first = dict(next(rows, {}) or {})
                        for idx in range(29, max(first.keys(), default=28) + 1, 3):
                            ds, _w, _y, _mo = m._safe_date_iso(first.get(idx))
                            if ds:
                                month_max = _max_date(month_max, ds)
                    except Exception as exc:
                        print(f"[V169-COVERAGE] warning monthly {sheet}: {type(exc).__name__}: {exc}", flush=True)

            raw_state.update(
                status="ready",
                raw_operational_max=op_max,
                raw_monthly_max=month_max,
                checked_at=datetime.now().isoformat(timespec="seconds"),
                error="",
            )
            print(
                f"[V169-COVERAGE] source={raw_state['source_file']} · "
                f"parsed_max={raw_state['parsed_max'] or 'none'} · "
                f"raw_operational_max={op_max or 'none'} · raw_monthly_max={month_max or 'none'}",
                flush=True,
            )
        except Exception as exc:
            raw_state.update(
                status="error",
                checked_at=datetime.now().isoformat(timespec="seconds"),
                error=f"{type(exc).__name__}: {exc}",
            )
            print(f"[V169-COVERAGE] ERROR {raw_state['error']}", flush=True)

    @m.app.get("/api/operations/coverage-v169")
    def operations_coverage_v169(request: Request):
        m.require_user(request)
        meta = m.load_operations_meta()
        dates = list(meta.get("available_dates") or [])
        weeks = list(meta.get("available_weeks") or [])
        months = list(meta.get("available_months") or [])
        return {
            "source_stamp": meta.get("source_stamp"),
            "source_file": meta.get("source_file") or "",
            "uploaded_at": meta.get("uploaded_at"),
            "min_date": min(dates) if dates else "",
            "max_date": max(dates) if dates else "",
            "max_week": max(weeks) if weeks else "",
            "max_month": max(months) if months else "",
            "available_dates": dates,
            "available_weeks": weeks,
            "available_months": months,
            "raw": dict(raw_state),
        }

    @m.app.on_event("startup")
    def _v169_start_coverage_scan():
        def delayed():
            time.sleep(4)
            _scan_current_source()
        threading.Thread(target=delayed, daemon=True, name="v169-coverage-scan").start()

    css = r'''<style id="v169-period-css">
#v169Coverage{display:flex;align-items:center;gap:7px;margin:4px 0 0;font-size:7.5px;color:#65758b;font-weight:800}
#v169Coverage b{color:#123f7c}.v169-latest-btn{border:1px solid #cbd9e8;background:#fff;color:#176fe8;border-radius:7px;padding:4px 8px;font-size:7.5px;font-weight:950;cursor:pointer}
.v169-latest-btn:hover{background:#eef5ff}
</style>'''

    js = r'''<script id="v169-period-js">
(function(){
if(window.__V169_PERIOD)return;window.__V169_PERIOD=true;
const q=s=>document.querySelector(s);
let lastStamp=null,busy=false;

function maxOption(select){
  if(!select)return '';
  return [...select.options].map(o=>String(o.value||'')).filter(Boolean).sort().at(-1)||'';
}
function coverageHost(){
  const bar=q('#operativoPeriodBar');
  if(!bar)return null;
  let el=q('#v169Coverage');
  if(!el){
    el=document.createElement('div');el.id='v169Coverage';
    bar.insertAdjacentElement('afterend',el);
  }
  return el;
}
async function syncCoverage(force=false){
  if(busy||!q('#operativoPeriodBar'))return;
  busy=true;
  try{
    const r=await fetch('/api/operations/coverage-v169',{credentials:'same-origin',cache:'no-store'});
    if(!r.ok)return;
    const d=await r.json();
    const host=coverageHost(),sel=q('#operPeriodSelect'),mode=q('#operPeriodMode')?.value||window.OPER_PERIOD?.type||'';
    const max=d.max_date||'', domMax=maxOption(sel);
    if(host){
      host.innerHTML=max
        ? '<span>Cobertura publicada: <b>'+max+'</b></span>'+(mode==='day'&&domMax&&domMax<max?'<button type="button" class="v169-latest-btn">Actualizar al último día</button>':'')
        : '<span>Sin fechas publicadas en la base vigente.</span>';
      host.querySelector('.v169-latest-btn')?.addEventListener('click',()=>applyFreshMeta(d,true));
    }
    const changed=lastStamp!==null && String(lastStamp)!==String(d.source_stamp||'');
    const staleOptions=mode==='day' && max && (!domMax || domMax<max);
    lastStamp=d.source_stamp||lastStamp;
    if(changed||staleOptions||force) await applyFreshMeta(d,changed||staleOptions);
  }catch(e){
    console.warn('[V169] cobertura',e);
  }finally{busy=false}
}
async function applyFreshMeta(cov,jumpLatest){
  try{
    if(typeof window.refreshOperativoMeta==='function'){
      const meta=await window.refreshOperativoMeta();
      window.OPSDATA=meta;
      const name=window.OP_VIEW||'Centro Ejecutivo';
      const sel=q('#operPeriodSelect');
      const before=maxOption(sel);
      if(jumpLatest && window.OPER_PERIOD){
        window.OPER_PERIOD.value='';
      }
      if(typeof window.setPeriodSelector==='function')window.setPeriodSelector(name,meta);
      const after=maxOption(sel);
      if(jumpLatest && after && window.OPER_PERIOD){
        window.OPER_PERIOD.value=after;
        if(sel)sel.value=after;
      }
      const host=coverageHost();
      if(host && after)host.innerHTML='<span>Cobertura publicada: <b>'+after+'</b></span>';
      if(jumpLatest && typeof window.renderOperativoView==='function'){
        await window.renderOperativoView(name,true);
      }
      console.info('[V169] periodos refrescados',before,'→',after);
    }
  }catch(e){console.warn('[V169] refresh',e)}
}
document.addEventListener('DOMContentLoaded',()=>{setTimeout(()=>syncCoverage(false),900)});
document.addEventListener('click',e=>{if(e.target.closest?.('[data-main="operativo"],#operativoNav,#refresh,#operPeriodApply'))setTimeout(()=>syncCoverage(false),350)},true);
document.addEventListener('change',e=>{if(e.target?.matches?.('#operPeriodMode,#operPeriodSelect'))setTimeout(()=>syncCoverage(false),80)},true);
setInterval(()=>{if(document.visibilityState==='visible')syncCoverage(false)},30000);
console.info('[V169] refresco automático de cobertura operativa instalado.');
})();
</script>'''

    @m.app.middleware("http")
    async def v169_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if "v169-period-css" not in html:
                html=html.replace("</head>",css+"</head>",1)
            if "v169-period-js" not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-Period-Version":"V169"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V169-HTML] {type(exc).__name__}: {exc}",flush=True)
            return response

    m._V169_PERIOD_FRESHNESS=True
    print("[V169] cobertura, diagnóstico y refresco de periodos instalados.",flush=True)
