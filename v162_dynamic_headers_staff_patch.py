from fastapi.responses import HTMLResponse

def install(m):
    if getattr(m,'_V162_DYNAMIC',False): return
    js='''<script id="v162-dynamic-js">
(function(){if(window.__v162d)return;window.__v162d=1;const $=id=>document.getElementById(id),N={day:'Día',week:'Semanal',month:'Mensual',year:'Anual'},W={day:'diario',week:'semanal',month:'mensual',year:'anual'};let key='',busy=0;
function mod(){try{return String(MAIN||'').toLowerCase()}catch(_){return''}}function mode(){return String($('operPeriodMode')?.value||'day')}function period(){return String($('operPeriodSelect')?.value||'')}function store(){return String($('operStoreSelect')?.value||'Compañía')}
function heads(){if(mod()==='operativo'){let md=mode(),lab=N[md]||'Día',word=W[md]||'diario';document.querySelectorAll('.title').forEach(x=>{if(/^Centro Operativo\\s*·/i.test(x.textContent||''))x.textContent='Centro Operativo · '+lab});document.querySelectorAll('.subtitle').forEach(x=>{if(/Acumulado\\s+(diario|semanal|mensual|anual)/i.test(x.textContent||''))x.textContent=x.textContent.replace(/Acumulado\\s+(diario|semanal|mensual|anual)/i,'Acumulado '+word)})}if(mod()==='operation'){let a=(document.querySelector('.v125-tabs .active')?.textContent||'').toLowerCase();if(a.includes('resumen')){if($('operativoDynamicTitle'))$('operativoDynamicTitle').textContent='Operación · '+(N[mode()]||'Día');if($('operativoDynamicSub'))$('operativoDynamicSub').textContent='Resumen ejecutivo de operación y productividad'+(period()?' · '+period():'')}}}
async function staff(){if(mod()!=='operation'||busy)return;let a=(document.querySelector('.v125-tabs .active')?.textContent||'').toLowerCase();if(!a.includes('resumen'))return;let g=$('operativoDynamicContent')?.querySelector('.v149-kpis,.v126-kpis,.report-kpis,.kpis');if(!g)return;let k=[mode(),period(),store()].join('|');if(k===key&&$('v162Staff'))return;busy=1;try{let q=new URLSearchParams({period_type:mode(),period_value:period(),store:store()}),d=await api('/api/operation/staff-needed-v159?'+q.toString(),{timeoutMs:60000}),rows=Array.isArray(d?.rows)?d.rows:[],need=rows.reduce((s,r)=>s+Number(r.origin_required||0),0),pend=rows.reduce((s,r)=>s+Number(r.origin_pending||0),0),c=$('v162Staff');if(!c){c=document.createElement('div');c.id='v162Staff';c.className=(g.querySelector('.v149-kpi,.v126-kpi,.report-kpi,.kpi')?.className||'v149-kpi')+' v162-staff';g.appendChild(c)}c.innerHTML='<small>COLAB. NECESARIOS ORIGEN</small><b>'+need.toLocaleString('es-MX')+'</b><span>'+pend.toLocaleString('es-MX',{maximumFractionDigits:0})+' pzas pendientes</span>';key=k}catch(e){console.warn('[V162]',e)}finally{busy=0}}
function sync(){heads();staff()}function sched(){[0,120,400,900].forEach(t=>setTimeout(sync,t))}document.addEventListener('click',e=>{if(e.target.closest?.('[data-main],[data-opview],.v125-tab,#operPeriodApply,#refresh,.v158-apply'))sched()},true);document.addEventListener('change',e=>{if(e.target?.matches?.('select,input')){key='';sched()}},true);if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sched);else sched();console.info('[V162] Encabezados dinámicos y personal Origen activos.');})();
</script>'''
    @m.app.middleware('http')
    async def _v162_dynamic(request,call_next):
        r=await call_next(request)
        if request.url.path!='/' or getattr(r,'status_code',200)!=200:return r
        b=b''
        async for c in r.body_iterator:b+=c
        h=b.decode('utf-8',errors='replace')
        if 'v162-dynamic-js' not in h:h=h.replace('</body>',js+'</body>',1)
        headers=dict(getattr(r,'headers',{}) or {});headers.pop('content-length',None);headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
        return HTMLResponse(h,status_code=r.status_code,headers=headers)
    m._V162_DYNAMIC=True
    print('[V162] Encabezados y personal Origen activos.',flush=True)
