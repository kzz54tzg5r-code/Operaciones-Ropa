"""V281 · Resurtido de Pasillos con layout del boceto 2+7+9.
Conserva backend V280 para capturas, añade historial y reemplaza únicamente la
presentación para igualar: bloques consecutivos + productividad de pareja +
avance por pasillo. También expone un renderer DEMO de sólo lectura.
"""

def install(m):
    if getattr(m,"_V281_AISLE_BOCETO",False): return
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from fastapi import Request
    from fastapi.responses import HTMLResponse

    MX=ZoneInfo("America/Mexico_City")
    PRIV={"superadmin","admin","director","consulta"}

    def _norm(v):
        try:return m.login_key(v)
        except Exception:return str(v or "").strip().casefold()

    def _store(actor,requested=""):
        stores=list(m.store_names(True) or [])
        active={_norm(x):x for x in stores}
        role=str(actor.get("role") or "").lower()
        assigned=str(actor.get("store") or "").strip()
        if role not in PRIV:
            if not assigned: raise m.HTTPException(409,"El usuario no tiene tienda asignada")
            return active.get(_norm(assigned),assigned)
        val=str(requested or "").strip()
        if not val or val=="Compañía":
            if assigned and _norm(assigned) in active:return active[_norm(assigned)]
            if stores:return stores[0]
            raise m.HTTPException(409,"No hay tiendas activas")
        chosen=active.get(_norm(val))
        if not chosen:raise m.HTTPException(400,"Tienda inválida")
        return chosen

    @m.app.get("/api/operation/aisle-resupply-v281/history")
    def aisle_history(request:Request,store:str="",date:str="",shift:str="Matutino"):
        actor=m.require_user(request)
        selected=_store(actor,store)
        day=str(date or datetime.now(MX).date().isoformat())[:10]
        sh=str(shift or "Matutino").title()
        where=["store=?","date=?","status='finished'"];args=[selected,day]
        if sh in ("Matutino","Vespertino"):
            where.append("shift=?");args.append(sh)
        with m.db() as con:
            rows=con.execute(
                """SELECT id,date,shift,store,block_no,aisle,aisle_no,suggested7,displacement,
                          upper_employee_no,upper_name,lower_employee_no,lower_name,pieces,
                          started_at,finished_at,duration_seconds,status
                   FROM operation_aisle_pair_runs
                   WHERE """+" AND ".join(where)+" ORDER BY id DESC LIMIT 80",
                tuple(args)
            ).fetchall()
        items=[dict(r) for r in rows]
        return {"store":selected,"date":day,"shift":sh,"items":items}

    css=r'''<style id="v281-aisle-boceto-css">
body[data-v281-view="aisle-resupply"] #operativoPeriodBar,
body[data-v281-view="aisle-resupply"] #v161FilterBar{display:none!important}
.v281{color:#123f73;width:100%;max-width:100%;font-family:inherit}
.v281 *{box-sizing:border-box}
.v281-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin:4px 0 10px}
.v281-head h2{margin:0!important;font-size:22px!important;line-height:1.05;color:#0c2f55}
.v281-sub{font-size:8px;color:#70849a;margin-top:4px}
.v281-filters{display:flex;align-items:end;gap:7px;flex-wrap:wrap;justify-content:flex-end}
.v281-f{display:grid;gap:3px}.v281-f label{font-size:7px;font-weight:950;color:#385a7a}
.v281 select,.v281 input{height:36px;border:1px solid #cbd9e7;border-radius:9px;background:#fff;color:#123f73;padding:0 10px;font-size:9px;font-weight:850;outline:none}
.v281-f-store select{min-width:160px}.v281-f-date input{min-width:135px}.v281-f-shift select{min-width:130px}
.v281-kpis{display:grid;grid-template-columns:1fr 1fr 1fr 1.2fr;gap:10px;margin-bottom:10px}
.v281-kpi{border:1px solid #d7e3ee;border-radius:11px;background:#fff;padding:12px 14px;min-height:92px;box-shadow:0 2px 8px rgba(16,63,108,.035)}
.v281-kpi-line{display:flex;align-items:center;gap:10px;height:100%}.v281-kico{width:45px;height:45px;border-radius:10px;display:grid;place-items:center;font-size:23px;flex:0 0 45px}
.v281-kico.red{background:#ffe9ec;color:#e8485e}.v281-kico.blue{background:#e9f3ff;color:#176fe8}.v281-kico.green{background:#e9f8f1;color:#0aa568}
.v281-kpi small{display:block;color:#65798e;font-size:8px;font-weight:850}.v281-kpi b{display:block;font-size:27px;line-height:1;color:#123f73;margin:5px 0}.v281-kpi span{font-size:8px;color:#687d92}
.v281-progress-kpi{display:grid;grid-template-columns:72px 1fr;align-items:center;gap:12px}
.v281-ring{--pct:0;--ring:#0aa568;width:68px;height:68px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--ring) calc(var(--pct)*1%),#e4edf4 0);position:relative}
.v281-ring:after{content:"";position:absolute;width:49px;height:49px;border-radius:50%;background:#fff}.v281-ring b{position:relative;z-index:1;font-size:18px;margin:0}
.v281-progress-kpi .v281-ptext b{font-size:16px;margin:2px 0 5px}.v281-mini-track{height:8px;background:#e7eef5;border-radius:99px;overflow:hidden}.v281-mini-track i{display:block;height:100%;background:#0aa568;border-radius:99px}
.v281-main{display:grid;grid-template-columns:minmax(0,2fr) minmax(330px,.9fr);gap:10px;align-items:start}
.v281-panel{border:1px solid #d5e1ec;border-radius:11px;background:#fff;overflow:hidden;min-width:0}
.v281-panel-h{height:38px;background:#103a64;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 12px;font-size:13px;font-weight:950}
.v281-auto{border:1px solid #ffffff75;background:#ffffff14;color:#fff;border-radius:7px;padding:6px 10px;font-size:8px;font-weight:900}
.v281-block{border:1px solid #dbe5ee;border-radius:9px;margin:8px;overflow:hidden;background:#fff}
.v281-block.critical{border-color:#ffb7bf}.v281-block.high{border-color:#ffc59b}.v281-block.medium{border-color:#f4dc7e}.v281-block.low{border-color:#bbdaf7}
.v281-bhead{display:grid;grid-template-columns:minmax(200px,1fr) auto auto auto;gap:8px;align-items:center;padding:7px 9px;background:#f8fbfd;cursor:pointer}
.v281-block.critical .v281-bhead{background:#fff0f2}.v281-block.high .v281-bhead{background:#fff5ec}.v281-block.medium .v281-bhead{background:#fff9df}.v281-block.low .v281-bhead{background:#f2f8ff}
.v281-bhead strong{font-size:10px}.v281-bmeta{font-size:8px;color:#4c6680;font-weight:850;white-space:nowrap}.v281-prio{display:inline-flex;padding:4px 8px;border-radius:6px;font-size:7px;font-weight:950}
.v281-prio.critical{background:#ffdce1;color:#c8233b}.v281-prio.high{background:#ffe8d3;color:#c65b0a}.v281-prio.medium{background:#fff0a9;color:#8f6b00}.v281-prio.low{background:#dff0ff;color:#1766a9}.v281-prio.done{background:#ddf7e7;color:#087b43}
.v281-assign{border:1px solid #0b74e8;background:#147ef5;color:#fff;border-radius:7px;padding:7px 11px;font-size:8px;font-weight:950;white-space:nowrap}
.v281-table{width:100%;border-collapse:collapse;table-layout:fixed}.v281-table th{background:#0f4d83;color:#fff;padding:5px 4px;font-size:7px;font-weight:900}.v281-table td{padding:5px 4px;border-top:1px solid #e7eef4;text-align:center;font-size:8px;color:#214b72}.v281-table tbody tr:nth-child(even) td{background:#fbfdff}
.v281-num-red{color:#e52f42!important;font-weight:950}.v281-pct{display:grid;grid-template-columns:1fr 34px;align-items:center;gap:5px}.v281-track{height:10px;background:#e5edf4;border-radius:99px;overflow:hidden}.v281-track i{height:100%;display:block;border-radius:99px}.v281-track i.red{background:#ef4d5e}.v281-track i.orange{background:#ff8b38}.v281-track i.green{background:#0fbd66}
.v281-pair-tabs{display:grid;grid-template-columns:1fr 1fr;gap:0;margin:9px 10px 4px;border:1px solid #cfddea;border-radius:8px;overflow:hidden}.v281-pair-tabs button{border:0;background:#fff;color:#365a7d;height:32px;font-size:8px;font-weight:950}.v281-pair-tabs button.active{background:#1682ee;color:#fff}
.v281-cap{padding:8px 11px 11px}.v281-field{display:grid;gap:4px;margin-bottom:9px}.v281-field label{font-size:8px;font-weight:950;color:#173f68}.v281-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v281-worker label{display:flex;gap:4px;align-items:center}
.v281-pieces{display:grid;grid-template-columns:1fr 36px 36px;gap:5px}.v281-pieces input{text-align:center;font-size:20px;font-weight:950}.v281-step{border:1px solid #ccd9e6;border-radius:7px;background:#f9fbfd;color:#123f73;font-size:17px;font-weight:950}
.v281-times{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v281-stat2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0}.v281-statbox{border:1px solid #dfe8f0;border-radius:8px;padding:9px}.v281-statbox small{display:block;font-size:7px;color:#60768c}.v281-statbox b{display:block;font-size:18px;color:#102f50;margin-top:4px}
.v281-primary{width:100%;height:39px;border:0;border-radius:8px;color:#fff;font-size:9px;font-weight:950}.v281-primary.start{background:#1682ee}.v281-primary.finish{background:#0aaa5c}.v281-primary:disabled{opacity:.45}
.v281-msg{font-size:7px;color:#7a8da0;min-height:12px;margin-top:5px}
.v281-hist{max-height:420px;overflow:auto}.v281-hist-row{border-bottom:1px solid #e8eef4;padding:8px 2px}.v281-hist-row b{font-size:8px}.v281-hist-row span{display:block;font-size:7px;color:#6a7f94;margin-top:3px}
.v281-bottom{display:grid;grid-template-columns:minmax(0,1fr) 265px;gap:10px;margin-top:10px}
.v281-summary{padding:12px}.v281-sumtop{display:flex;align-items:center;gap:14px}.v281-sumtop .v281-ring{width:66px;height:66px}.v281-sumtop .v281-ring:after{width:48px;height:48px}
.v281-sumtop strong{font-size:18px}.v281-status{display:grid;gap:7px;margin-top:12px}.v281-status-row{display:grid;grid-template-columns:12px 1fr auto auto;align-items:center;gap:7px;font-size:8px}.v281-dot{width:9px;height:9px;border-radius:50%}.v281-dot.green{background:#0aad5d}.v281-dot.yellow{background:#f1bf1a}.v281-dot.red{background:#ee4155}
.v281-alert{margin-top:12px;padding:9px;border-radius:8px;background:#fff0f2;color:#ae2539;font-size:8px;font-weight:850}.v281-alert b{display:block;margin-bottom:3px}
.v281-foot{display:flex;gap:8px;align-items:flex-start;margin-top:10px;border:1px solid #d6e4ef;border-radius:9px;background:#f5faff;padding:9px 11px;font-size:8px;color:#3b5d7b}
.v281-demo-badge{display:inline-flex;padding:3px 7px;border-radius:999px;background:#e9354c;color:#fff;font-size:7px;font-weight:950;margin-left:6px;vertical-align:middle}
@media(max-width:1050px){.v281-main{grid-template-columns:1fr}.v281-bottom{grid-template-columns:1fr}.v281-kpis{grid-template-columns:repeat(2,1fr)}}
@media(max-width:700px){
 .v281-head{display:block}.v281-head h2{font-size:16px!important}.v281-filters{display:grid;grid-template-columns:1.25fr 1fr .9fr;margin-top:8px;gap:4px}
 .v281-f-store select,.v281-f-date input,.v281-f-shift select{min-width:0;width:100%}.v281 select,.v281 input{height:29px;font-size:6px;padding:0 5px}
 .v281-kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:3px}.v281-kpi{min-height:68px;padding:6px}.v281-kico{width:28px;height:28px;flex-basis:28px;font-size:14px}.v281-kpi-line{gap:5px}
 .v281-kpi b{font-size:16px}.v281-kpi small,.v281-kpi span{font-size:4.8px}.v281-progress-kpi{grid-template-columns:42px 1fr;gap:5px}.v281-ring{width:40px;height:40px}.v281-ring:after{width:29px;height:29px}.v281-ring b{font-size:9px}
 .v281-panel-h{height:30px;font-size:8px;padding:0 7px}.v281-auto{font-size:5px;padding:4px 6px}.v281-block{margin:4px}.v281-bhead{grid-template-columns:1fr auto;gap:3px;padding:5px}.v281-bhead strong{font-size:6px}.v281-bmeta{font-size:5px}.v281-bhead .v281-prio{display:none}.v281-assign{font-size:5px;padding:5px}
 .v281-table th{font-size:4.5px;padding:4px 1px}.v281-table td{font-size:5px;padding:4px 1px}.v281-pct{grid-template-columns:1fr 23px;gap:2px}.v281-track{height:6px}
 .v281-cap{padding:6px}.v281-field label{font-size:5px}.v281-pair{gap:4px}.v281-pieces{grid-template-columns:1fr 28px 28px}.v281-pieces input{font-size:13px}.v281-statbox{padding:6px}.v281-statbox small{font-size:5px}.v281-statbox b{font-size:12px}.v281-primary{height:31px;font-size:6px}
 .v281-summary{padding:8px}.v281-sumtop strong{font-size:12px}.v281-status-row,.v281-alert,.v281-foot{font-size:5px}.v281-sub{font-size:5px}
}
</style>'''

    js=r'''<script id="v281-aisle-boceto-js">(function(){
if(window.__V281_AISLE_BOCETO)return;window.__V281_AISLE_BOCETO=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
const n=v=>Number(v||0)||0,nf=v=>Math.round(n(v)).toLocaleString('es-MX'),pc=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';
const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let M=null,R=null,A=null,H=[],P=null,busy=0,selected='',pane='registro',expanded=new Set([1,2]),tickId=0;
const isOp=()=>String(document.body.dataset.v163Module||'').toLowerCase()==='operation';
async function api281(u,o){let r=await fetch(u,{credentials:'same-origin',cache:'no-store',...(o||{})}),d={};try{d=await r.json()}catch(_){}if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));return d}
function priClass(x){let k=String(x?.priority_key||'').toLowerCase();return k==='critical'?'critical':k==='high'?'high':k==='medium'?'medium':k==='done'?'done':'low'}
function priLabel(x){let k=priClass(x);return k==='critical'?'Alta prioridad':k==='high'?'Alta prioridad':k==='medium'?'Media prioridad':k==='done'?'Terminado':'Baja prioridad'}
function barClass(v){return n(v)>=75?'green':n(v)>=40?'orange':'red'}
function fmtTime(iso){if(!iso)return '—';try{return new Date(iso).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit',hour12:false})}catch(_){return '—'}}
function hms(sec){sec=Math.max(0,Math.floor(n(sec)));let h=String(Math.floor(sec/3600)).padStart(2,'0'),m=String(Math.floor(sec%3600/60)).padStart(2,'0'),s=String(sec%60).padStart(2,'0');return h+':'+m+':'+s}
function transform(raw){
 const xs=(raw?.aisles||[]).map(x=>{
   const target=Math.max(0,n(x.suggested7)),base=Math.min(target,Math.max(0,n(x.existence))),added=Math.max(0,n(x.resupplied)),covered=Math.min(target,base+added),remaining=Math.max(0,target-covered),pct=target?covered/target*100:0;
   const status=remaining<=.01?'Terminado':(covered>0?'En proceso':'Pendiente');
   return {...x,target,actual:base,resupplied_added:added,covered,remaining2:remaining,progress2:Math.min(100,pct),status};
 });
 const byNo=new Map(xs.map(x=>[Number(x.aisle_no),x]));
 const ranked=[...xs].sort((a,b)=>n(b.priority_score)-n(a.priority_score)||n(b.displacement)-n(a.displacement)||n(b.remaining2)-n(a.remaining2)||n(a.aisle_no)-n(b.aisle_no));
 const pending=new Map(ranked.filter(x=>x.remaining2>0).map(x=>[Number(x.aisle_no),x]));let blocks=[],bn=0;
 while(pending.size){
   let seed=[...pending.values()].sort((a,b)=>n(b.priority_score)-n(a.priority_score)||n(b.displacement)-n(a.displacement)||n(b.remaining2)-n(a.remaining2))[0];
   let members=[],cursor=Number(seed.aisle_no),sum=0;
   while(members.length<4&&pending.has(cursor)){
      let x=pending.get(cursor);pending.delete(cursor);members.push(x);sum+=x.remaining2;if(sum>=150)break;cursor++;
   }
   bn++;let planned=Math.min(150,Math.max(0,sum)),rate=230,mins=planned?Math.max(1,Math.round(planned/rate*60)):0;
   blocks.push({block_no:bn,items:members,aisles:members.map(x=>x.aisle),pending:sum,planned,minutes:mins,priority_key:seed.priority_key,priority:seed.priority});
 }
 const objective=xs.reduce((a,x)=>a+x.target,0),covered=xs.reduce((a,x)=>a+x.covered,0),pendingTotal=Math.max(0,objective-covered),pct=objective?covered/objective*100:0,cap=Math.max(1,n(raw?.summary?.pair_capacity)||300),pairs=pendingTotal?Math.ceil(pendingTotal/cap):0;
 return {store:raw?.store,date:raw?.date,shift:raw?.shift,capacity_period:raw?.capacity_period,aisles:ranked,blocks,summary:{objective,covered,pending:pendingTotal,progress:pct,pairs,collabs:pairs*2,pair_capacity:cap,critical:xs.filter(x=>x.remaining2>0&&['critical','high'].includes(priClass(x))).length}};
}
function tabBlockNo(aisle){let b=P?.blocks?.find(z=>z.items.some(x=>x.aisle===aisle));return b?.block_no||0}
function rowBlock(x){
 return '<tr data-v281-aisle="'+e(x.aisle)+'"><td><b>'+x.aisle_no+'</b></td><td>'+nf(x.target)+'</td><td>'+nf(x.actual+x.resupplied_added)+'</td><td class="v281-num-red">'+nf(x.remaining2)+'</td><td><div class="v281-pct"><div class="v281-track"><i class="'+barClass(x.progress2)+'" style="width:'+Math.min(100,x.progress2)+'%"></i></div><b>'+pc(x.progress2)+'</b></div></td><td><span class="v281-prio '+priClass(x)+'">'+e(x.status==='Terminado'?'Terminado':priLabel(x).replace(' prioridad',''))+'</span></td></tr>';
}
function blocksHTML(){
 if(!(P?.blocks||[]).length)return '<div class="v281-summary">No hay pasillos pendientes para el Sugerido 7 actual.</div>';
 return P.blocks.map(b=>{
   const open=expanded.has(b.block_no),cls=priClass(b);
   return '<div class="v281-block '+cls+'"><div class="v281-bhead" data-v281-toggle="'+b.block_no+'"><strong>👤 Bloque '+b.block_no+' ('+e((b.aisles||[]).join(' · ').replaceAll('Pasillo ','P'))+')</strong><span class="v281-prio '+cls+'">'+e(priLabel(b))+'</span><span class="v281-bmeta">Total bloque: <b>'+nf(b.planned)+' pzas</b> &nbsp; ~ '+nf(b.minutes)+' min</span><button class="v281-assign" data-v281-assign="'+b.block_no+'">Asignar pareja</button></div>'+(open?'<table class="v281-table"><thead><tr><th>Pasillo</th><th>Sugerido 7</th><th>Actual</th><th>Falta</th><th>%</th><th>Prioridad</th></tr></thead><tbody>'+b.items.map(rowBlock).join('')+'</tbody></table>':'')+'</div>';
 }).join('');
}
function statusInfo(){
 const xs=P?.aisles||[],total=Math.max(1,xs.length),done=xs.filter(x=>x.status==='Terminado').length,proc=xs.filter(x=>x.status==='En proceso').length,pend=xs.filter(x=>x.status==='Pendiente').length;
 return {done,proc,pend,donePct:done/total*100,procPct:proc/total*100,pendPct:pend/total*100};
}
function historyHTML(){
 if(!H.length)return '<div class="v281-cap"><div class="v281-msg">Todavía no hay registros finalizados para esta fecha y turno.</div></div>';
 return '<div class="v281-cap v281-hist">'+H.map(x=>'<div class="v281-hist-row"><b>'+e(x.aisle)+' · '+nf(x.pieces)+' pzas · '+(x.duration_seconds?nf(n(x.pieces)/(n(x.duration_seconds)/3600))+' pz/h':'—')+'</b><span>↑ '+e(x.upper_name||'—')+' &nbsp; ↓ '+e(x.lower_name||'—')+'</span><span>'+e(fmtTime(x.started_at))+' – '+e(fmtTime(x.finished_at))+' · '+e(x.shift||'')+'</span></div>').join('')+'</div>';
}
function staffOptions(v){return '<option value="">Seleccionar</option>'+(M?.staff||[]).map(x=>'<option value="'+x.id+'" '+(String(v||'')===String(x.id)?'selected':'')+'>'+e(x.name)+(x.employee_no?' · '+e(x.employee_no):'')+'</option>').join('')}
function currentAisle(){let x=(P?.aisles||[]).find(z=>z.aisle===selected)||(P?.aisles||[]).find(z=>z.remaining2>0)||(P?.aisles||[])[0];if(x)selected=x.aisle;return x}
function liveSeconds(){if(!A?.started_at)return 0;return Math.max(0,(Date.now()-new Date(A.started_at).getTime())/1000)}
function registerHTML(){
 let x=currentAisle(),running=!!A,id=A?.aisle||x?.aisle||'',pieces=n(q('#v281Pieces')?.value||0),secs=running?liveSeconds():0,prod=secs>0?pieces/(secs/3600):0;
 let opts=(P?.aisles||[]).map(z=>'<option value="'+e(z.aisle)+'" '+(z.aisle===id?'selected':'')+'>'+e(z.aisle)+' (Bloque '+tabBlockNo(z.aisle)+') · falta '+nf(z.remaining2)+'</option>').join('');
 return '<div class="v281-cap"><div class="v281-field"><label>Selecciona pasillo o bloque</label><select id="v281Aisle" '+(running?'disabled':'')+'>'+opts+'</select></div><div class="v281-field"><label>Pareja de trabajo</label><div class="v281-pair"><div class="v281-worker"><label>↑ Colaborador (altura)</label><select id="v281Up" '+(running?'disabled':'')+'>'+staffOptions(A?.upper_user_id)+'</select></div><div class="v281-worker"><label>↓ Colaborador (recibe / acomoda)</label><select id="v281Lo" '+(running?'disabled':'')+'>'+staffOptions(A?.lower_user_id)+'</select></div></div></div><div class="v281-field"><label>Piezas resurtidas</label><div class="v281-pieces"><input id="v281Pieces" type="number" min="0" value="'+nf(pieces)+'" '+(!running?'disabled':'')+'><button class="v281-step" id="v281Minus" '+(!running?'disabled':'')+'>−</button><button class="v281-step" id="v281Plus" '+(!running?'disabled':'')+'>+</button></div></div><div class="v281-times"><div class="v281-field"><label>Hora inicio</label><input value="'+e(running?fmtTime(A.started_at):'—')+'" disabled></div><div class="v281-field"><label>Hora fin</label><input value="'+e(running?'En curso':'—')+'" disabled></div></div><div class="v281-stat2"><div class="v281-statbox"><small>Tiempo</small><b id="v281Elapsed">'+(running?hms(secs):'00:00:00')+'</b></div><div class="v281-statbox"><small>Productividad</small><b id="v281Pph">'+nf(prod)+' pz/h</b></div></div><button id="v281Primary" class="v281-primary '+(running?'finish':'start')+'" '+(!M?.can_write?'disabled':'')+'>'+(running?'💾 Finalizar y guardar':'▶ Iniciar resurtido')+'</button><div id="v281Msg" class="v281-msg">'+(running?'Las piezas se guardan una sola vez para la pareja.':'Selecciona los dos colaboradores y el pasillo para comenzar.')+'</div></div>';
}
function pairPanel(){
 return '<section class="v281-panel"><div class="v281-panel-h"><span>2. Productividad de pareja por pasillo</span></div><div class="v281-pair-tabs"><button data-v281-pane="registro" class="'+(pane==='registro'?'active':'')+'">Registro</button><button data-v281-pane="historial" class="'+(pane==='historial'?'active':'')+'">Historial</button></div><div id="v281PairBody">'+(pane==='historial'?historyHTML():registerHTML())+'</div></section>';
}
function progressRow(x){
 return '<tr data-v281-aisle="'+e(x.aisle)+'"><td><b>'+x.aisle_no+'</b></td><td>'+nf(x.target)+'</td><td>'+nf(x.covered)+'</td><td class="v281-num-red">'+nf(x.remaining2)+'</td><td>'+pc(x.progress2)+'</td><td><div class="v281-track"><i class="'+barClass(x.progress2)+'" style="width:'+Math.min(100,x.progress2)+'%"></i></div></td><td><span class="v281-prio '+(x.status==='Terminado'?'done':x.status==='En proceso'?'medium':'critical')+'">'+e(x.status)+'</span></td></tr>';
}
function shell(isDemo=false){
 let s=P?.summary||{},st=statusInfo(),stores=(M?.stores||[]).map(x=>'<option '+(x===P?.store?'selected':'')+'>'+e(x)+'</option>').join(''),high=(P?.aisles||[]).filter(x=>x.remaining2>0&&['critical','high'].includes(priClass(x))).slice(0,5);
 return '<span class="v201-demo-marker" hidden></span><div class="v281"><div class="v281-head"><div><h2>Resurtido de Pasillos'+(isDemo?'<span class="v281-demo-badge">DEMO</span>':'')+'</h2><div class="v281-sub">Objetivo total = Sugerido 7. Los bloques de ~150 pzas organizan el recorrido consecutivo.</div></div><div class="v281-filters"><div class="v281-f v281-f-store"><label>Tienda</label><select id="v281Store" '+(isDemo?'disabled':'')+'>'+stores+'</select></div><div class="v281-f v281-f-date"><label>Fecha</label><input id="v281Date" type="date" value="'+e(P?.date||M?.date||'')+'" '+(isDemo?'disabled':'')+'></div><div class="v281-f v281-f-shift"><label>Turno</label><select id="v281Shift" '+(isDemo?'disabled':'')+'><option '+(P?.shift==='Matutino'?'selected':'')+'>Matutino</option><option '+(P?.shift==='Vespertino'?'selected':'')+'>Vespertino</option></select></div></div></div><div class="v281-kpis"><div class="v281-kpi"><div class="v281-kpi-line"><div class="v281-kico red">▣</div><div><b>'+nf(s.pending)+'</b><small>Piezas pendientes</small><span>de '+nf(s.objective)+' objetivo Sugerido 7</span></div></div></div><div class="v281-kpi"><div class="v281-kpi-line"><div class="v281-kico blue">▦</div><div><b>'+nf(P?.blocks?.length||0)+'</b><small>Bloques planeados</small><span>pasillos consecutivos</span></div></div></div><div class="v281-kpi"><div class="v281-kpi-line"><div class="v281-kico green">●●</div><div><b>'+nf(s.pairs)+'</b><small>Parejas necesarias</small><span>'+nf(s.collabs)+' colaboradores · 2 por pareja</span></div></div></div><div class="v281-kpi v281-progress-kpi"><div class="v281-ring" style="--pct:'+Math.min(100,n(s.progress))+'"><b>'+pc(s.progress)+'</b></div><div class="v281-ptext"><small>Avance general</small><b>'+nf(s.covered)+' / '+nf(s.objective)+' piezas</b><div class="v281-mini-track"><i style="width:'+Math.min(100,n(s.progress))+'%"></i></div></div></div></div><div class="v281-main"><section class="v281-panel"><div class="v281-panel-h"><span>1. Bloques consecutivos por resurtir</span><button class="v281-auto" type="button">⚙ Asignación automática</button></div>'+blocksHTML()+'</section>'+pairPanel()+'</div><div class="v281-bottom"><section class="v281-panel"><div class="v281-panel-h"><span>3. Avance de resurtido por pasillo</span><span style="font-size:8px;font-weight:800">Vista tabla</span></div><table class="v281-table"><thead><tr><th>Pasillo</th><th>Sugerido 7 (objetivo)</th><th>Actual + resurtido</th><th>Falta</th><th>%</th><th>Barra de avance</th><th>Estado</th></tr></thead><tbody>'+(P?.aisles||[]).map(progressRow).join('')+'</tbody></table></section><aside class="v281-panel"><div class="v281-panel-h"><span>Resumen de avance</span></div><div class="v281-summary"><div class="v281-sumtop"><div class="v281-ring" style="--pct:'+Math.min(100,n(s.progress))+'"><b>'+pc(s.progress)+'</b></div><div><strong>'+nf(s.covered)+' / '+nf(s.objective)+'</strong><div class="v281-sub">piezas cubiertas del Sugerido 7</div></div></div><div class="v281-status"><div class="v281-status-row"><i class="v281-dot green"></i><span>Terminados</span><b>'+st.done+'</b><b>'+pc(st.donePct)+'</b></div><div class="v281-status-row"><i class="v281-dot yellow"></i><span>En proceso</span><b>'+st.proc+'</b><b>'+pc(st.procPct)+'</b></div><div class="v281-status-row"><i class="v281-dot red"></i><span>Pendientes</span><b>'+st.pend+'</b><b>'+pc(st.pendPct)+'</b></div></div><div class="v281-alert"><b>⚠ '+high.length+' pasillos con alta prioridad</b>'+(high.length?high.map(x=>'Pasillo '+x.aisle_no).join(', ')+' requieren atención para cumplir el plan del turno.':'Sin alertas críticas en este momento.')+'</div></div></aside></div><div class="v281-foot"><b>ℹ</b><span><strong>Estructura:</strong> agrupación de pasillos consecutivos por carga de trabajo, captura de productividad por pareja y seguimiento del avance por pasillo. <strong>Ideal para:</strong> asignar parejas, registrar piezas resurtidas y dar seguimiento al plan en tiempo real.</span></div></div>';
}
function enter(){window.V149_OPERATION_TAB='aisle-resupply';window.V125_OPERATION_TAB='aisle-resupply';document.body.dataset.v281View='aisle-resupply';qa('#v200OperationTabs [data-v200-op]').forEach(b=>{let on=b.dataset.v200Op==='aisle-resupply';b.classList.toggle('active',on);b.setAttribute('aria-selected',on?'true':'false')});let bar=q('#operativoPeriodBar');if(bar){bar.classList.add('hidden');bar.style.setProperty('display','none','important')}q('#operativoCentro')?.classList.add('hidden');q('#operativoDynamic')?.classList.remove('hidden')}
function render(){enter();let h=q('#operativoDynamicContent');if(!h)return;h.innerHTML=shell(false);bind();clock()}
function bind(){
 q('#v281Store')?.addEventListener('change',load);q('#v281Date')?.addEventListener('change',load);q('#v281Shift')?.addEventListener('change',load);
 q('#v281Aisle')?.addEventListener('change',ev=>selected=ev.target.value);
 qa('[data-v281-toggle]').forEach(x=>x.addEventListener('click',ev=>{if(ev.target.closest('[data-v281-assign]'))return;let id=Number(x.dataset.v281Toggle);expanded.has(id)?expanded.delete(id):expanded.add(id);render()}));
 qa('[data-v281-assign]').forEach(x=>x.addEventListener('click',ev=>{ev.preventDefault();ev.stopPropagation();let b=P?.blocks?.find(z=>z.block_no===Number(x.dataset.v281Assign)),a=b?.items?.find(z=>z.remaining2>0)||b?.items?.[0];if(a){selected=a.aisle;pane='registro';render();setTimeout(()=>q('#v281Up')?.focus(),30)}}));
 qa('[data-v281-aisle]').forEach(x=>x.addEventListener('click',()=>{selected=x.dataset.v281Aisle;pane='registro';render()}));
 qa('[data-v281-pane]').forEach(x=>x.addEventListener('click',()=>{pane=x.dataset.v281Pane;render()}));
 q('#v281Minus')?.addEventListener('click',()=>{let z=q('#v281Pieces');if(z){z.value=Math.max(0,n(z.value)-1);updateLive()}});
 q('#v281Plus')?.addEventListener('click',()=>{let z=q('#v281Pieces');if(z){z.value=n(z.value)+1;updateLive()}});
 q('#v281Pieces')?.addEventListener('input',updateLive);q('#v281Primary')?.addEventListener('click',()=>A?finish():start());
}
function updateLive(){if(!A)return;let secs=liveSeconds(),pieces=n(q('#v281Pieces')?.value);if(q('#v281Elapsed'))q('#v281Elapsed').textContent=hms(secs);if(q('#v281Pph'))q('#v281Pph').textContent=nf(secs?pieces/(secs/3600):0)+' pz/h'}
function clock(){clearInterval(tickId);if(!A)return;updateLive();tickId=setInterval(updateLive,1000)}
async function start(){
 let msg=q('#v281Msg');try{let x=currentAisle(),up=Number(q('#v281Up')?.value||0),lo=Number(q('#v281Lo')?.value||0);if(!x||!up||!lo)throw new Error('Selecciona pasillo y los dos integrantes de la pareja');if(up===lo)throw new Error('Arriba y abajo deben ser colaboradores diferentes');if(msg)msg.textContent='Iniciando…';await api281('/api/operation/aisle-resupply-v280/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({store:P.store,date:P.date,shift:P.shift,capacity_period:P.capacity_period||'',block_no:tabBlockNo(x.aisle),aisle:x.aisle,suggested7:x.target,displacement:x.displacement,upper_user_id:up,lower_user_id:lo})});await load()}catch(err){if(msg)msg.textContent=err.message}}
async function finish(){let msg=q('#v281Msg');try{if(msg)msg.textContent='Guardando…';await api281('/api/operation/aisle-resupply-v280/'+A.id+'/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pieces:n(q('#v281Pieces')?.value)})});A=null;await load()}catch(err){if(msg)msg.textContent=err.message}}
async function load(){
 if(busy)return;busy=1;try{enter();let store=q('#v281Store')?.value||q('#operStoreSelect')?.value||M?.store||'',date=q('#v281Date')?.value||M?.date||'',shift=q('#v281Shift')?.value||P?.shift||'Matutino';M=await api281('/api/operation/aisle-resupply-v280/meta?store='+encodeURIComponent(store));store=store&&store!=='Compañía'?store:M.store;date=date||M.date;
 let [raw,active,hist]=await Promise.all([api281('/api/operation/aisle-resupply-v280/plan?'+new URLSearchParams({store,date,shift})),api281('/api/operation/aisle-resupply-v280/active').then(x=>x.item||null),api281('/api/operation/aisle-resupply-v281/history?'+new URLSearchParams({store,date,shift})).catch(()=>({items:[]}))]);
 R=raw;A=active;H=hist.items||[];P=transform(raw);if(A)selected=A.aisle;render();
 }catch(err){let h=q('#operativoDynamicContent');if(h)h.innerHTML='<div class="infoempty">No fue posible cargar Resurtido de Pasillos: '+e(err.message||err)+'</div>'}finally{busy=0}
}
function openReal(){if(!isOp()||document.body.classList.contains('v201-demo-mode'))return;load()}
document.addEventListener('click',ev=>{let t=ev.target.closest?.('#v200OperationTabs [data-v200-op="aisle-resupply"]');if(!t||document.body.classList.contains('v201-demo-mode'))return;ev.preventDefault();ev.stopImmediatePropagation();openReal()},true);
let mo=new MutationObserver(()=>{if(!isOp()||document.body.classList.contains('v201-demo-mode'))return;let active=q('#v200OperationTabs [data-v200-op="aisle-resupply"].active');if(active){let bar=q('#operativoPeriodBar');if(bar)bar.style.setProperty('display','none','important');let h=q('#operativoDynamicContent');if(h&&!h.querySelector('.v281')&&!busy)setTimeout(openReal,20)}});
function boot(){mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-v163-module','style']});if(isOp()&&String(window.V149_OPERATION_TAB||'')==='aisle-resupply')openReal()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();

function demoData(d){
 let store=(d?.stores||[])[0]||{store:'Vallejo',sales_pieces:12000},objective=Math.max(900,Math.min(2800,Math.round(n(store.sales_pieces||12000)/Math.max(1,n(d?.workdays||20))*4.3)));
 let nums=[21,22,23,24,35,36,37,38,12,13,14,15],weights=[.087,.071,.067,.063,.075,.063,.059,.055,.052,.05,.048,.046],aisles=nums.map((no,i)=>{let target=Math.max(80,Math.round(objective*weights[i])),prog=[68,47,47,75,42,59,67,89,35,22,15,10][i],covered=Math.round(target*prog/100);return {aisle:'Pasillo '+no,aisle_no:no,suggested7:target,existence:covered,resupplied:0,displacement:Math.round(target*(2.1-i*.06)),priority_score:100-i*5,priority:i<4?'Alta':i<8?'Media':'Baja',priority_key:i<4?'critical':i<8?'medium':'low'}});
 let raw={store:store.store||'Vallejo',date:new Date().toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'}),shift:'Matutino',capacity_period:'DEMO',aisles,summary:{pair_capacity:300}};return raw;
}
window.V281AisleDemoHTML=function(d){
 let oldM=M,oldR=R,oldA=A,oldH=H,oldP=P,oldSel=selected,oldPane=pane;try{let raw=demoData(d);M={stores:[raw.store],store:raw.store,date:raw.date,staff:[{id:1,name:'Juan Pérez',employee_no:'DEMO-01'},{id:2,name:'Luis García',employee_no:'DEMO-02'}],can_write:false};R=raw;A=null;H=[];P=transform(raw);selected=P.aisles[0]?.aisle||'';pane='registro';return shell(true)}finally{M=oldM;R=oldR;A=oldA;H=oldH;P=oldP;selected=oldSel;pane=oldPane}
};
console.info('[V281] Boceto 2+7+9 activo para Resurtido de Pasillos.');
})();</script>'''

    @m.app.middleware("http")
    async def v281_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v281-aisle-boceto-css"' not in html:html=html.replace("</head>",css+"</head>",1)
            if 'id="v281-aisle-boceto-js"' not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers["Cache-Control"]="no-store";headers["X-Operations-UI-Version"]="V281-AISLE-BOCETO-2-7-9"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V281] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V281_AISLE_BOCETO=True
    print("[V281] Resurtido de Pasillos: boceto 2+7+9 + historial + DEMO instalado.",flush=True)
