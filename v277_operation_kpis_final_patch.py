"""V277 · Operación: 8 tarjetas finales, sin duplicados ni iconos.

Alcance exclusivo al módulo Operación / Resumen:
- elimina la tarjeta "Llegada Origen" marcada por el usuario;
- elimina la tarjeta duplicada #v162Staff ("Colab. necesarios Origen");
- conserva la tarjeta correcta "Colaboradores necesarios" del resumen;
- usa el <small> nativo como encabezado de color para que el título nunca desaparezca;
- elimina cintas/iconos heredados V166/V269/V275/V276;
- desktop: 8 tarjetas en una fila; tablet/móvil compactan sin perder scroll vertical.
No modifica cálculos, datos, filtros, permisos ni endpoints.
"""
from fastapi.responses import HTMLResponse


def install(m):
    if getattr(m, "_V277_OPERATION_KPIS_FINAL", False):
        return

    css = r'''<style id="v277-operation-kpis-final-css">
/* Ocultar cualquier decoración heredada: la tarjeta usa únicamente su encabezado nativo. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi
:is(.v166-kpi-icon,.v164-kpi-icon,.v269-ribbon,.v275-ribbon,.v276-ribbon){
  display:none!important;
  visibility:hidden!important;
  opacity:0!important;
  pointer-events:none!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi:before{
  display:none!important;
}

/* Matriz final. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpis{
  display:grid!important;
  grid-template-columns:repeat(var(--v277-cols,8),minmax(0,1fr))!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  gap:5px!important;
  margin:5px 0 7px!important;
  align-items:stretch!important;
}

/* Tarjeta compacta, pero con título visible. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi{
  position:relative!important;
  box-sizing:border-box!important;
  width:100%!important;
  min-width:0!important;
  max-width:100%!important;
  height:61px!important;
  min-height:61px!important;
  max-height:61px!important;
  margin:0!important;
  padding:23px 7px 5px!important;
  overflow:hidden!important;
  border:1px solid #d7e3ef!important;
  border-radius:9px!important;
  background:#fff!important;
  box-shadow:0 2px 7px rgba(18,63,115,.045)!important;
}

/* El small original es el encabezado: no depende de JS para verse. */
body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>small{
  position:absolute!important;
  z-index:40!important;
  left:0!important;
  right:0!important;
  top:0!important;
  display:flex!important;
  align-items:center!important;
  width:100%!important;
  height:19px!important;
  min-height:19px!important;
  margin:0!important;
  padding:0 7px!important;
  border-radius:8px 8px 0 0!important;
  background:var(--k,#176fe8)!important;
  color:#fff!important;
  font-size:6.2px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:0!important;
  text-transform:uppercase!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>b{
  display:block!important;
  margin:1px 0 0!important;
  padding:0!important;
  color:#103f76!important;
  font-size:18px!important;
  line-height:1!important;
  font-weight:950!important;
  letter-spacing:-.02em!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

body:is(.v238-module-operation,[data-v163-module="operation"])
#operativoDynamicContent .v149-kpi>span:not(.v166-kpi-icon):not(.v164-kpi-icon){
  display:block!important;
  margin:3px 0 0!important;
  padding:0!important;
  color:#6b7f96!important;
  font-size:6px!important;
  line-height:1!important;
  font-weight:650!important;
  white-space:nowrap!important;
  overflow:hidden!important;
  text-overflow:ellipsis!important;
}

/* La tarjeta duplicada no debe ocupar espacio ni un instante mientras el observer la retira. */
body:is(.v238-module-operation,[data-v163-module="operation"]) #v162Staff{
  display:none!important;
}

/* Tablet */
@media(min-width:701px) and (max-width:1024px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:4px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:57px!important;
    min-height:57px!important;
    max-height:57px!important;
    padding:21px 5px 4px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>small{height:18px!important;min-height:18px!important;font-size:5.8px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:16px!important}
}

/* Móvil: aspecto de laptop, 4 por fila, scroll vertical libre. */
@media(max-width:700px){
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpis{
    grid-template-columns:repeat(4,minmax(0,1fr))!important;
    gap:3px!important;
    margin:4px 0 6px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi{
    height:54px!important;
    min-height:54px!important;
    max-height:54px!important;
    padding:20px 3px 3px!important;
    border-radius:7px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>small{
    height:17px!important;
    min-height:17px!important;
    padding:0 3px!important;
    border-radius:6px 6px 0 0!important;
    font-size:4.6px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>b{font-size:13px!important}
  body:is(.v238-module-operation,[data-v163-module="operation"])
  #operativoDynamicContent .v149-kpi>span:not(.v166-kpi-icon):not(.v164-kpi-icon){font-size:4.7px!important}

  html,
  html body.v238-module-operation,
  html body[data-v163-module="operation"]{
    min-height:100%!important;
    height:auto!important;
    max-height:none!important;
    overflow-y:auto!important;
    overflow-x:hidden!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"])
  :is(#appView,.shell,.main,section.page,section.page.active,#operativoDynamic,#operativoDynamicContent){
    min-height:0!important;
    height:auto!important;
    max-height:none!important;
    overflow-y:visible!important;
    overscroll-behavior-y:auto!important;
    touch-action:pan-y pinch-zoom!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"]) .main{
    overflow-x:hidden!important;
    padding-bottom:92px!important;
  }
  body:is(.v238-module-operation,[data-v163-module="operation"]) .tablewrap{
    touch-action:pan-x pan-y pinch-zoom!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:auto!important;
  }
}
</style>'''

    js = r'''<script id="v277-operation-kpis-final-js">
(function(){
  if(window.__V277_OPERATION_KPIS_FINAL)return;
  window.__V277_OPERATION_KPIS_FINAL=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const imp=(el,p,v)=>el&&el.style.setProperty(p,v,'important');

  function isOperation(){
    if(document.body.classList.contains('v238-module-operation'))return true;
    if(String(document.body.dataset.v163Module||'').toLowerCase()==='operation')return true;
    try{return String(window.MAIN||MAIN||'').toLowerCase()==='operation'}catch(_){return false}
  }

  function label(card){
    return String(
      q(':scope>small',card)?.textContent ||
      q(':scope>.v275-ribbon .v275-title',card)?.textContent ||
      q(':scope>.v276-ribbon .v276-title',card)?.textContent ||
      q(':scope>.v269-ribbon .v269-title',card)?.textContent ||
      ''
    ).replace(/\s+/g,' ').trim();
  }

  function clean(){
    if(!isOperation())return;
    const grid=q('#operativoDynamicContent .v149-kpis');
    if(!grid)return;

    /* 1) eliminar la tarjeta duplicada inferior marcada. */
    q('#v162Staff')?.remove();

    /* 2) eliminar Llegada Origen marcada. */
    qa(':scope>.v149-kpi',grid).forEach(card=>{
      const l=label(card).toLowerCase();
      if(l==='llegada origen'||l.startsWith('llegada origen ')){
        card.remove();
        return;
      }

      /* Nada de iconos/cintas superpuestas: conservar small/b/span originales. */
      qa(':scope>.v166-kpi-icon,:scope>.v164-kpi-icon,:scope>.v269-ribbon,:scope>.v275-ribbon,:scope>.v276-ribbon',card)
        .forEach(x=>x.remove());
      card.classList.remove('v166-iconized-card','v269-option4-card');
      card.style.removeProperty('padding-left');
    });

    const cards=qa(':scope>.v149-kpi',grid);
    const count=cards.length||8;
    let cols;
    if(window.innerWidth>=1025)cols=count;
    else if(window.innerWidth>=701)cols=Math.min(4,count);
    else cols=Math.min(4,count);
    grid.style.setProperty('--v277-cols',String(cols));
    imp(grid,'grid-template-columns','repeat('+cols+',minmax(0,1fr))');
  }

  function unlockScroll(){
    if(!isOperation()||window.innerWidth>900)return;
    if(q('.modal-backdrop:not(.hidden),[role="dialog"]:not(.hidden)'))return;
    [document.documentElement,document.body,q('#appView'),q('.shell'),q('.main'),q('section.page.active'),q('#operativoDynamic'),q('#operativoDynamicContent')]
      .filter(Boolean).forEach(el=>{
        imp(el,'height','auto');
        imp(el,'max-height','none');
        imp(el,'overflow-y',(el===document.documentElement||el===document.body)?'auto':'visible');
        imp(el,'overscroll-behavior-y','auto');
        imp(el,'touch-action','pan-y pinch-zoom');
      });
    imp(document.documentElement,'overflow-x','hidden');
    imp(document.body,'overflow-x','hidden');
  }

  function sync(){clean();unlockScroll()}
  let t=0;
  function queue(ms=20){clearTimeout(t);t=setTimeout(sync,ms)}

  const mo=new MutationObserver(()=>queue(25));
  function start(){
    mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style']});
    sync();
    [50,120,250,500,900,1500,2500,4000].forEach(ms=>setTimeout(sync,ms));
  }
  document.addEventListener('click',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('change',()=>[20,80,180,420].forEach(ms=>setTimeout(sync,ms)),true);
  document.addEventListener('touchstart',()=>unlockScroll(),{passive:true,capture:true});
  window.addEventListener('resize',()=>queue(30),{passive:true});
  window.addEventListener('orientationchange',()=>[80,220,500].forEach(ms=>setTimeout(sync,ms)),{passive:true});
  window.addEventListener('pageshow',()=>[40,160,420].forEach(ms=>setTimeout(sync,ms)),{passive:true});

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();

  console.info('[V277] Operación: 8 KPIs finales; Llegada Origen y duplicado de personal retirados.');
})();
</script>'''

    @m.app.middleware("http")
    async def v277_html(request, call_next):
        response=await call_next(request)
        if request.url.path != "/" or getattr(response,"status_code",200) != 200:
            return response
        try:
            body=b""
            async for chunk in response.body_iterator:
                body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v277-operation-kpis-final-css"' not in html:
                html=html.replace("</head>",css+"</head>",1)
            if 'id="v277-operation-kpis-final-js"' not in html:
                html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {})
            headers.pop("content-length",None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache",
                "Expires":"0",
                "X-Operations-UI-Version":"V277-OPERATION-KPIS-FINAL",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V277] HTML warning: {type(exc).__name__}: {exc}",flush=True)
            return response


    # ================================================================
    # V278 · Opción 1 aprobada · Score Operativo + ranking integral
    # ================================================================
    from collections import defaultdict as _v278_defaultdict
    from datetime import date as _v278_date, datetime as _v278_datetime, timedelta as _v278_timedelta
    from zoneinfo import ZoneInfo as _V278ZoneInfo
    from fastapi import Request as _V278Request
    import math as _v278_math
    import re as _v278_re

    _V278_MX = _V278ZoneInfo("America/Mexico_City")
    _V278_AREAS = ("Colgado", "Doblado", "Jeans", "Lencería")
    _V278_PRIV = ("superadmin", "admin", "director", "consulta")

    def _v278_num(v):
        try:
            x=float(v or 0)
            return x if _v278_math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def _v278_norm(v):
        try:
            return m.login_key(v)
        except Exception:
            return str(v or "").strip().casefold()

    def _v278_bounds(kind, value):
        kind=str(kind or "week").lower().strip()
        value=str(value or "").strip()
        today=_v278_datetime.now(_V278_MX).date()
        if kind=="day":
            d=_v278_date.fromisoformat((value or today.isoformat())[:10]); return d,d
        if kind=="week":
            mt=_v278_re.fullmatch(r"(\d{4})-W(\d{1,2})",value,_v278_re.I)
            if mt: s=_v278_date.fromisocalendar(int(mt.group(1)),int(mt.group(2)),1)
            else:
                iso=today.isocalendar(); s=_v278_date.fromisocalendar(iso.year,iso.week,1)
            return s,s+_v278_timedelta(days=6)
        if kind=="month":
            if value: y,mo=[int(x) for x in value.split("-")[:2]]
            else: y,mo=today.year,today.month
            s=_v278_date(y,mo,1); e=_v278_date(y+(mo==12),1 if mo==12 else mo+1,1)-_v278_timedelta(days=1); return s,e
        y=int(value[:4]) if value else today.year
        return _v278_date(y,1,1),_v278_date(y,12,31)

    def _v278_canon(v, stores):
        k=_v278_norm(v)
        for st in stores:
            if _v278_norm(st)==k: return st
        return str(v or "").strip()

    def _v278_scope(actor, requested):
        stores=list(m.store_names(True) or [])
        role=str(actor.get("role") or "").lower().strip()
        assigned=_v278_canon(actor.get("store"),stores)
        if role not in _V278_PRIV:
            if not assigned: raise m.HTTPException(409,"El usuario no tiene tienda asignada")
            return [assigned],assigned,False
        selected=str(requested or "Compañía").strip() or "Compañía"
        if selected!="Compañía": selected=_v278_canon(selected,stores)
        return stores,selected,True

    def _v278_status(score):
        if score>=95:return "Excelente","excellent"
        if score>=80:return "En objetivo","target"
        if score>=70:return "Atención","attention"
        return "Crítico","critical"

    @m.app.get("/api/operation/scorecard-v278")
    def _v278_scorecard(request:_V278Request,period_type:str="week",period_value:str="",store:str="Compañía"):
        actor=m.require_user(request)
        start,end=_v278_bounds(period_type,period_value)
        stores,selected,can_rank_all=_v278_scope(actor,store)
        if not stores:
            return {"store":selected,"summary":{},"flow":{},"areas":[],"ranking":[],"status_counts":{}}
        ss,es=start.isoformat(),end.isoformat()
        marks=",".join("?" for _ in stores)
        with m.db() as con:
            tcols={str(r["name"]) for r in con.execute("PRAGMA table_info(operation_productivity_timer)").fetchall()}
            std="standard_value" if "standard_value" in tcols else "0 AS standard_value"
            rows=[dict(r) for r in con.execute(
                "SELECT date,store,employee_no,employee_name,area,activity,pieces,operation_type,"+std+
                " FROM operation_productivity_timer WHERE status='finished' AND date>=? AND date<=? AND store IN ("+marks+") ORDER BY date,id",
                (ss,es,*stores)).fetchall()]
            caps=[dict(r) for r in con.execute(
                "SELECT date,store,arrival,pending_manual,COALESCE(excess,0) excess FROM operation_daily_capture WHERE origin='Origen' AND date<=? AND store IN ("+marks+") ORDER BY date",
                (es,*stores)).fetchall()]
        by=_v278_defaultdict(list); bc=_v278_defaultdict(list)
        for r in rows:
            st=_v278_canon(r.get("store"),stores);r["store"]=st;by[st].append(r)
        for r in caps:
            st=_v278_canon(r.get("store"),stores);r["store"]=st;bc[st].append(r)
        try:
            goals=m.get_goals() or {}
            fallback=float(goals.get("productividad_diaria") or 784)
        except Exception:
            fallback=784.0
        today=_v278_datetime.now(_V278_MX).date()
        total_days=max((end-start).days+1,1)
        elapsed=total_days if today>end else (1 if today<start else max((today-start).days+1,1))
        frac=max(min(elapsed/total_days,1),.01)

        def stages(items,op):
            keys=("Clasificado","Acondicionado","Ubicado") if op=="Origen" else ("Pizca","Acondicionado","Ubicado")
            out={k:0.0 for k in keys}
            for r in items:
                typ=str(r.get("operation_type") or "Origen").strip().title()
                if typ!=op: continue
                a=str(r.get("activity") or "").strip()
                if a in out: out[a]+=_v278_num(r.get("pieces"))
            return out

        def opening(st):
            if hasattr(m,"operation_pending_at"):
                try:
                    value, _source, _seed = m.operation_pending_at(st,(start-_v278_timedelta(days=1)).isoformat())
                    return max(_v278_num(value),0) if value is not None else 0.0
                except Exception:
                    pass
            xs=bc.get(st,[])
            prev=[r for r in xs if str(r.get("date") or "")<ss and r.get("pending_manual") is not None]
            return max(_v278_num(prev[-1].get("pending_manual")),0) if prev else 0.0

        def metric(st):
            items=by.get(st,[]); o=stages(items,"Origen"); r=stages(items,"Resurtido")
            piece=0.0;target=0.0;ap=_v278_defaultdict(float);at=_v278_defaultdict(float);seen=set()
            for x in items:
                area=str(x.get("area") or "")
                if area not in _V278_AREAS: continue
                val=_v278_num(x.get("pieces")); piece+=val; ap[area]+=val
                emp=str(x.get("employee_no") or "") or _v278_norm(x.get("employee_name"))
                k=(str(x.get("date") or ""),emp,area,str(x.get("activity") or ""))
                if k not in seen:
                    seen.add(k); sv=_v278_num(x.get("standard_value")) or fallback; target+=sv; at[area]+=sv
            pc=[x for x in bc.get(st,[]) if ss<=str(x.get("date") or "")<=es]
            excess=sum(_v278_num(x.get("excess")) for x in pc)
            progress=piece+excess
            prod=progress/target*100 if target else 0
            begin=o["Clasificado"]+r["Pizca"]; located=o["Ubicado"]+r["Ubicado"]; close=located/begin*100 if begin else 0
            opn=opening(st)
            if hasattr(m,"operation_pending_at"):
                try:
                    pv,_src,_seed=m.operation_pending_at(st,es)
                    pend=max(_v278_num(pv),0) if pv is not None else 0.0
                except Exception:
                    pend=0.0
            else:
                manual=[x for x in pc if x.get("pending_manual") is not None]
                if manual:
                    a=max(manual,key=lambda x:str(x.get("date") or "")); ad=str(a.get("date") or "")
                    pend=max(_v278_num(a.get("pending_manual")),0)
                    pend+=sum(_v278_num(x.get("arrival")) for x in pc if str(x.get("date") or "")>ad)
                    pend-=sum(_v278_num(x.get("pieces")) for x in items if str(x.get("operation_type") or "Origen").title()=="Origen" and str(x.get("activity") or "")=="Ubicado" and str(x.get("date") or "")>ad)
                    pend=max(pend,0)
                else:
                    arrival=sum(_v278_num(x.get("arrival")) for x in pc); new=arrival if arrival>0 else o["Clasificado"]
                    pend=max(opn+new-o["Ubicado"],0)
            workload=opn+(sum(_v278_num(x.get("arrival")) for x in pc) or o["Clasificado"])
            pscore=max(0,min(100,(1-pend/workload)*100)) if workload else (100 if pend<=0 else 0)
            advance=progress/(target*frac)*100 if target else (located/(begin*frac)*100 if begin else 0)
            area={}
            parts=[]
            for a in _V278_AREAS:
                pct=ap[a]/at[a]*100 if at[a] else 0
                area[a]={"pieces":ap[a],"target":at[a],"pct":pct};parts.append(max(0,min(pct,100)))
            coverage=sum(parts)/len(parts)
            score=max(0,min(prod,100))*.35+max(0,min(close,100))*.30+pscore*.20+max(0,min(advance,100))*.10+coverage*.05
            if pscore<70:score=min(score,94)
            label,key=_v278_status(score)
            return {"store":st,"score":round(score,1),"status":label,"status_key":key,"productivity_pct":round(prod,1),
                    "productivity_pieces":round(progress,1),"productivity_raw":round(piece,1),"excess":round(excess,1),
                    "progress_pieces":round(progress,1),"productivity_target":round(target,1),"flow_pct":round(close,1),
                    "pending":round(pend,1),"pending_score":round(pscore,1),"advance_pct":round(advance,1),
                    "coverage_pct":round(coverage,1),"located_pieces":round(located,1),"origin":o,"resupply":r,"areas":area,
                    "has_data":bool(items or pc)}

        ranking=[metric(st) for st in stores]
        ranking=[x for x in ranking if x["has_data"]]
        ranking.sort(key=lambda x:(-x["score"],-x["productivity_pct"],x["store"]))
        for i,x in enumerate(ranking,1):x["rank"]=i
        view=ranking if selected=="Compañía" else [x for x in ranking if _v278_norm(x["store"])==_v278_norm(selected)]
        if not can_rank_all: ranking=view
        def sum_stage(name,key):
            return sum(_v278_num(x[name].get(key)) for x in view)
        flow={"origin":{"Clasificado":sum_stage("origin","Clasificado"),"Acondicionado":sum_stage("origin","Acondicionado"),"Ubicado":sum_stage("origin","Ubicado")},
              "resupply":{"Pizca":sum_stage("resupply","Pizca"),"Acondicionado":sum_stage("resupply","Acondicionado"),"Ubicado":sum_stage("resupply","Ubicado")}}
        raw=sum(x.get("productivity_raw",0) for x in view)
        excess=sum(x.get("excess",0) for x in view)
        tp=raw+excess
        tt=sum(x["productivity_target"] for x in view)
        prod=tp/tt*100 if tt else 0
        begin=flow["origin"]["Clasificado"]+flow["resupply"]["Pizca"]; located=flow["origin"]["Ubicado"]+flow["resupply"]["Ubicado"]
        close=located/begin*100 if begin else 0
        pend=sum(x["pending"] for x in view); pscore=sum(x["pending_score"] for x in view)/len(view) if view else 0
        advance=tp/(tt*frac)*100 if tt else (sum(x["advance_pct"] for x in view)/len(view) if view else 0)
        areas=[]
        for a in _V278_AREAS:
            p=sum(x["areas"][a]["pieces"] for x in view);t=sum(x["areas"][a]["target"] for x in view);pct=p/t*100 if t else 0
            areas.append({"area":a,"pieces":round(p,1),"target":round(t,1),"compliance_pct":round(pct,1)})
        coverage=sum(min(max(x["compliance_pct"],0),100) for x in areas)/len(areas)
        score=max(0,min(prod,100))*.35+max(0,min(close,100))*.30+pscore*.20+max(0,min(advance,100))*.10+coverage*.05
        if pscore<70:score=min(score,94)
        label,key=_v278_status(score)
        counts={"Excelente":0,"En objetivo":0,"Atención":0,"Crítico":0}
        for x in ranking:counts[x["status"]]=counts.get(x["status"],0)+1
        return {"store":selected,"period_type":period_type,"period_value":period_value,"start_date":ss,"end_date":es,
                "summary":{"score":round(score,1),"status":label,"status_key":key,"productivity_pct":round(prod,1),
                           "productivity_pieces":round(tp,1),"productivity_raw":round(raw,1),"excess":round(excess,1),
                           "progress_pieces":round(tp,1),"productivity_target":round(tt,1),"flow_pct":round(close,1),
                           "pending":round(pend,1),"pending_score":round(pscore,1),"advance_pct":round(advance,1),
                           "coverage_pct":round(coverage,1),"located_pieces":round(located,1)},
                "flow":flow,"areas":areas,"ranking":ranking,"status_counts":counts}

    _v278_css=r'''<style id="v278-option1-css">
body:is(.v238-module-operation,[data-v163-module="operation"]) #operativoDynamicContent .v278{width:100%;min-width:0;color:#123f73}
.v278 *{box-sizing:border-box}.v278-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 14px;margin:5px 0 8px;border-radius:14px;background:linear-gradient(135deg,#184d7f,#0d3f70);color:#fff}.v278-head h2{margin:0!important;color:#fff!important;font-size:20px!important}.v278-head p{margin:5px 0 0!important;color:#d9e9f7!important;font-size:8px!important}.v278-date{padding:7px 10px;border:1px solid #ffffff35;border-radius:9px;background:#ffffff18;font-size:8px;font-weight:900}
.v278-kpis{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:7px;margin-bottom:8px}.v278-kpi{height:112px;padding:10px;border:1px solid #d8e4ef;border-radius:13px;background:#fff;overflow:hidden;box-shadow:0 4px 14px #143f6910}.v278-kpi.g{background:linear-gradient(#effcf4,#fff)}.v278-kpi.b{background:linear-gradient(#eff8ff,#fff)}.v278-kpi.p{background:linear-gradient(#f5f1ff,#fff)}.v278-kpi.o{background:linear-gradient(#fff7e8,#fff)}.v278-kpi.r{background:linear-gradient(#fff0f5,#fff)}.v278-l{font-size:8px;font-weight:950}.v278-v{font-size:27px;font-weight:950;line-height:1;margin-top:14px;letter-spacing:-.04em}.v278-s{font-size:7px;color:#708399;margin-top:6px;font-weight:750}.v278-bar{height:8px;margin-top:10px;border-radius:999px;background:#e8eef4;overflow:hidden}.v278-bar i{display:block;height:100%;border-radius:inherit;background:#2586e8}.v278-ring{width:70px;height:70px;margin:3px auto 0;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#20bd63 calc(var(--p)*1%),#dfece5 0);position:relative}.v278-ring:after{content:"";position:absolute;inset:8px;border-radius:50%;background:#fff}.v278-ring b{z-index:1;font-size:23px}.v278-tag{display:block;width:max-content;margin:1px auto 0;padding:3px 7px;border-radius:999px;background:#dff7e8;color:#13733b;font-size:6.5px;font-weight:900}
.v278-grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(320px,.95fr);gap:8px;margin-bottom:8px}.v278-panel{min-width:0;padding:10px;border:1px solid #d8e4ef;border-radius:13px;background:#fff;overflow:hidden}.v278-panel h3{display:flex;gap:6px;align-items:center;margin:0 0 8px!important;font-size:12px!important;color:#123f73!important}.v278-panel h3 small{margin-left:auto;font-size:6.5px;color:#7d90a3}.v278-flows{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v278-flow{padding:9px;border:1px solid #e0e9f2;border-radius:11px}.v278-ft{font-size:10px;font-weight:950;margin-bottom:7px}.v278-steps,.v278-nums{display:grid;grid-template-columns:repeat(3,1fr);gap:3px}.v278-step{padding:9px 2px;border-radius:8px;color:#fff;text-align:center;font-size:7.5px;font-weight:900}.v278-step:nth-child(1){background:#2d82e8}.v278-step:nth-child(2){background:#8152e8}.v278-step:nth-child(3){background:#12b76a}.v278-nums{margin-top:6px;text-align:center}.v278-nums b{font-size:10px}.v278-nums span{display:block;font-size:5.8px;color:#71849a;margin-top:2px}
.v278-ar{display:grid;grid-template-columns:72px 1fr 42px 82px;gap:6px;align-items:center;padding:6px 0;border-bottom:1px solid #edf2f6;font-size:7.5px}.v278-pr{height:11px;border-radius:5px;background:#edf2f6;overflow:hidden}.v278-pr i{display:block;height:100%;background:#2dbd66}.v278-ap{text-align:right;font-size:8.5px;font-weight:950}.v278-an{text-align:right;color:#637b93;font-size:6.5px}
.v278-rank{max-height:300px;overflow:auto}.v278-rr{display:grid;grid-template-columns:24px minmax(85px,1fr) minmax(90px,1.5fr) 32px;gap:5px;align-items:center;padding:5px 2px;border-bottom:1px solid #edf2f6;font-size:7px}.v278-rr.h{position:sticky;top:0;background:#f6f9fc;z-index:2;font-weight:950}.v278-rb{height:10px;border-radius:4px;background:#edf2f6;overflow:hidden}.v278-rb i{display:block;height:100%;background:#32bc61}.v278-rs{text-align:right;font-size:8.5px;font-weight:950}.v278-status td{padding:7px;border-bottom:1px solid #edf2f6;font-size:7.5px}.v278-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.excellent{--st:#12b95f}.target{--st:#70d852}.attention{--st:#f6ae2d}.critical{--st:#ef476f}.v278-dot{background:var(--st)}
.v278-tw{overflow:auto;border:1px solid #dfe8f1;border-radius:10px}.v278-table{width:100%;min-width:900px;border-collapse:collapse}.v278-table th{position:sticky;top:0;background:#f1f6fb;padding:7px 5px;font-size:6.5px;color:#315776;white-space:nowrap}.v278-table td{padding:6px 5px;border-top:1px solid #edf2f6;font-size:7px;text-align:center;white-space:nowrap}.v278-table td:nth-child(2),.v278-table th:nth-child(2){text-align:left}.v278-chip{display:inline-block;min-width:52px;padding:4px 5px;border-radius:7px;background:#edf4fb;font-weight:900}.v278-state{display:inline-block;padding:4px 7px;border-radius:999px;background:color-mix(in srgb,var(--st) 18%,white);color:#245;font-weight:900}.v278-w{display:block;font-size:5px;color:#8a9bae}
@media(max-width:1024px){.v278-kpis{gap:4px}.v278-kpi{height:96px;padding:7px}.v278-v{font-size:20px}.v278-ring{width:58px;height:58px}.v278-grid{grid-template-columns:1.2fr .9fr}.v278-panel{padding:7px}}
@media(max-width:700px){.v278-head{padding:8px}.v278-head h2{font-size:14px!important}.v278-date{font-size:5.5px;padding:5px}.v278-kpis{grid-template-columns:repeat(3,1fr);gap:3px}.v278-kpi{height:75px;padding:5px}.v278-l{font-size:5.2px}.v278-v{font-size:15px;margin-top:9px}.v278-s{font-size:4.8px}.v278-ring{width:43px;height:43px}.v278-ring b{font-size:14px}.v278-tag{font-size:4.6px;padding:2px 4px}.v278-grid{grid-template-columns:1fr;gap:5px}.v278-flows{grid-template-columns:1fr 1fr;gap:4px}.v278-flow{padding:5px}.v278-step{font-size:5px;padding:6px 1px}.v278-ar{grid-template-columns:50px 1fr 30px 58px;gap:3px;font-size:5.5px}.v278-rr{grid-template-columns:20px 72px 1fr 28px;font-size:5.5px}.v278-panel h3{font-size:8px!important}.v278-table{min-width:720px}.v278-table th,.v278-table td{font-size:5.5px;padding:5px 3px}html body:is(.v238-module-operation,[data-v163-module="operation"]){overflow-y:auto!important;touch-action:pan-y pinch-zoom!important}}
</style>'''

    _v278_js=r'''<script id="v278-option1-js">
(function(){if(window.__V278_OPTION1)return;window.__V278_OPTION1=true;
const q=(s,r=document)=>r.querySelector(s),n=v=>Number(v||0),nf=v=>Math.round(n(v)).toLocaleString("es-MX"),p=v=>n(v).toLocaleString("es-MX",{maximumFractionDigits:1}),esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let seq=0,t=0,wrapped=false;
function op(){return document.body.classList.contains("v238-module-operation")||String(document.body.dataset.v163Module||"").toLowerCase()==="operation"}
function sum(){try{return String(window.V149_OPERATION_TAB||"summary")==="summary"}catch(_){return true}}
function per(){let type="week",value="",store="Compañía";try{type=String(OPER_PERIOD?.type||"week");value=String(OPER_PERIOD?.value||"")}catch(_){}store=String(q("#operStoreSelect")?.value||"Compañía");return {type,value,store}}
function bar(v){return Math.min(Math.max(n(v),0),100)}
function flow(x,names){let a=n(x[names[0]]),b=n(x[names[1]]),c=n(x[names[2]]),pb=a?b/a*100:0,pc=a?c/a*100:0;return '<div class="v278-steps"><div class="v278-step">'+names[0]+'</div><div class="v278-step">'+names[1]+'</div><div class="v278-step">'+names[2]+'</div></div><div class="v278-nums"><div><b>'+nf(a)+'</b><span>inicio</span></div><div><b>'+nf(b)+'</b><span>'+p(pb)+'%</span></div><div><b>'+nf(c)+'</b><span>'+p(pc)+'%</span></div></div>'}
function kpis(s){return '<div class="v278-kpis"><div class="v278-kpi g"><div class="v278-l">Score Operativo</div><div class="v278-ring" style="--p:'+bar(s.score)+'"><b>'+p(s.score)+'</b></div><span class="v278-tag">'+esc(s.status||"Sin datos")+'</span></div><div class="v278-kpi b"><div class="v278-l">Avance productivo</div><div class="v278-v">'+p(s.productivity_pct)+'%</div><div class="v278-s">'+nf(s.productivity_raw)+' prod. + '+nf(s.excess)+' exc.</div><div class="v278-bar"><i style="width:'+bar(s.productivity_pct)+'%"></i></div></div><div class="v278-kpi g"><div class="v278-l">Excedente</div><div class="v278-v" style="color:#0a9b62">'+nf(s.excess)+'</div><div class="v278-s">Suma al avance · no al pendiente</div></div><div class="v278-kpi p"><div class="v278-l">Cierre de flujo</div><div class="v278-v">'+p(s.flow_pct)+'%</div><div class="v278-s">Ubicado ÷ inicio</div><div class="v278-bar"><i style="width:'+bar(s.flow_pct)+'%;background:#8056e8"></i></div></div><div class="v278-kpi o"><div class="v278-l">Pendiente actual</div><div class="v278-v" style="color:#ef7b08">'+nf(s.pending)+'</div><div class="v278-s">Saldo automático · Control '+p(s.pending_score)+'%</div></div><div class="v278-kpi r"><div class="v278-l">Avance vs esperado</div><div class="v278-v" style="color:#e71954">'+p(s.advance_pct)+'%</div><div class="v278-s">Productividad + excedente</div></div><div class="v278-kpi b"><div class="v278-l">Pzas ubicadas</div><div class="v278-v">'+nf(s.located_pieces)+'</div><div class="v278-s">Origen + Resurtido</div></div></div>'}
function areas(xs){return (xs||[]).map(x=>'<div class="v278-ar"><b>'+esc(x.area)+'</b><div class="v278-pr"><i style="width:'+bar(x.compliance_pct)+'%"></i></div><div class="v278-ap">'+p(x.compliance_pct)+'%</div><div class="v278-an">'+nf(x.pieces)+' / '+nf(x.target)+'</div></div>').join("")}
function ranking(xs){return '<div class="v278-rank"><div class="v278-rr h"><div>#</div><div>Tienda</div><div>Score Operativo</div><div></div></div>'+((xs||[]).map(x=>'<div class="v278-rr"><b>'+x.rank+'</b><b title="'+esc(x.store)+'">'+esc(x.store)+'</b><div class="v278-rb"><i style="width:'+bar(x.score)+'%"></i></div><div class="v278-rs">'+p(x.score)+'</div></div>').join("")||'<div style="padding:10px;font-size:8px">Sin datos.</div>')+'</div>'}
function states(c,total){return '<table class="v278-status">'+[["Excelente","excellent"],["En objetivo","target"],["Atención","attention"],["Crítico","critical"]].map(x=>{let v=n(c?.[x[0]]);return '<tr><td><span class="v278-dot '+x[1]+'"></span><b>'+x[0]+'</b></td><td>'+v+'</td><td>'+(total?p(v/total*100):"0")+'%</td></tr>'}).join("")+'</table>'}
function detail(xs){return '<div class="v278-tw"><table class="v278-table"><thead><tr><th>#</th><th>Tienda</th><th>Score</th><th>Avance productivo<span class="v278-w">35%</span></th><th>Excedente</th><th>Cierre de flujo<span class="v278-w">30%</span></th><th>Pendientes<span class="v278-w">20%</span></th><th>Avance<span class="v278-w">10%</span></th><th>Cobertura áreas<span class="v278-w">5%</span></th><th>Estado</th></tr></thead><tbody>'+((xs||[]).map(x=>'<tr><td>'+x.rank+'</td><td><b>'+esc(x.store)+'</b></td><td><span class="v278-chip">'+p(x.score)+'</span></td><td>'+p(x.productivity_pct)+'%</td><td>'+nf(x.excess)+'</td><td>'+p(x.flow_pct)+'%</td><td>'+nf(x.pending)+' pzs</td><td>'+p(x.advance_pct)+'%</td><td>'+p(x.coverage_pct)+'%</td><td><span class="v278-state '+x.status_key+'">'+esc(x.status)+'</span></td></tr>').join("")||'<tr><td colspan="10">Sin información.</td></tr>')+'</tbody></table></div>'}
function page(r){let total=(r.ranking||[]).length;return '<div class="v278"><div class="v278-head"><div><h2>Reporte de Operación</h2><p>Tienda: '+esc(r.store||"Compañía")+' &nbsp;|&nbsp; '+esc(r.period_value||r.start_date||"")+'</p></div><div class="v278-date">'+esc(r.start_date||"")+' — '+esc(r.end_date||"")+'</div></div>'+kpis(r.summary||{})+'<div class="v278-grid"><div class="v278-panel"><h3>▦ Flujo de Operación</h3><div class="v278-flows"><div class="v278-flow"><div class="v278-ft">Origen</div>'+flow(r.flow?.origin||{},["Clasificado","Acondicionado","Ubicado"])+'</div><div class="v278-flow"><div class="v278-ft">Resurtido</div>'+flow(r.flow?.resupply||{},["Pizca","Acondicionado","Ubicado"])+'</div></div></div><div class="v278-panel"><h3>▥ Productividad por área <small>Excedente se muestra separado</small></h3>'+areas(r.areas||[])+'</div></div><div class="v278-grid"><div class="v278-panel"><h3>🏆 Ranking por tienda — Score Operativo <small>'+total+' tiendas</small></h3>'+ranking(r.ranking||[])+'</div><div class="v278-panel"><h3>▥ Estado de indicadores</h3>'+states(r.status_counts||{},total)+'</div></div><div class="v278-panel"><h3>▦ Detalle de evaluación por tienda <small>Score: 35% Productividad · 30% Cierre · 20% Pendientes · 10% Avance · 5% Cobertura</small></h3>'+detail(r.ranking||[])+'</div></div>'}
async function render(){if(!op()||!sum()||document.body.classList.contains("v201-demo-mode"))return;let host=q("#operativoDynamicContent");if(!host)return;let id=++seq,a=per(),u="/api/operation/scorecard-v278?"+new URLSearchParams({period_type:a.type,period_value:a.value,store:a.store});let res=await fetch(u,{credentials:"same-origin",cache:"no-store"});if(!res.ok)return;let r=await res.json();if(id!==seq||!op()||!sum())return;let rail=q("#v200OperationTabs",host)||q(":scope>.v125-tabs",host);if(rail)rail.remove();host.innerHTML=page(r);if(rail)host.prepend(rail);let title=q("#operativoDynamicTitle");if(title)title.textContent="Reporte de Operación";let sub=q("#operativoDynamicSub");if(sub)sub.textContent="Score Operativo · "+(r.store||a.store)}
function sched(ms=80){clearTimeout(t);t=setTimeout(()=>render().catch(e=>console.warn("[V278]",e)),ms)}
function wrap(){if(wrapped||typeof window.renderOperativoView!=="function")return;wrapped=true;let prev=window.renderOperativoView;window.renderOperativoView=async function(name,force){let out=await prev.apply(this,arguments);if(String(name)==="Operación"&&sum())await render();return out}}
function start(){wrap();[120,350,800,1500,2600].forEach(ms=>setTimeout(()=>{wrap();sched(20)},ms))}
document.addEventListener("click",e=>{if(e.target.closest?.('[data-main="operation"],[data-v149-tab="summary"],[data-v200-op="summary"]'))[80,220,500].forEach(ms=>setTimeout(()=>sched(10),ms))},true);
document.addEventListener("change",e=>{if(["operPeriodMode","operPeriodSelect","operStoreSelect"].includes(e.target?.id||""))setTimeout(()=>sched(10),160)},true);
window.addEventListener("pageshow",()=>setTimeout(()=>sched(10),160),{passive:true});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});else start();
console.info("[V278] Opción 1 del Reporte de Operación instalada.");
})();</script>'''

    @m.app.middleware("http")
    async def _v278_option1_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v278-option1-css"' not in html:html=html.replace("</head>",_v278_css+"</head>",1)
            if 'id="v278-option1-js"' not in html:html=html.replace("</body>",_v278_js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None)
            headers.update({"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V278-OPTION1-SCORECARD"})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V278] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V278_OPTION1_SCORECARD_EXTENSION=True
    print("[V278] Opción 1 + Score Operativo + ranking integral instalada.",flush=True)


    m._V277_OPERATION_KPIS_FINAL=True
    print("[V277] Operación: 8 KPIs finales y scroll móvil instalados.",flush=True)
