"""V279 · Bonos Operativos por clúster A/B/C/D."""
from __future__ import annotations
import re, math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX=ZoneInfo("America/Mexico_City")
CLUSTERS=("A","B","C","D")
ADMIN=("superadmin","admin")
PRIV=("superadmin","admin","director","consulta")
RESTRICTED=("tienda","colaborador","colaborador_operativo","colaborador_lenceria")
BANDS=((1,400,"Top 1%","1%"),(2,350,"Sig. 1%","1%"),(5,300,"Sig. 3%","3%"),(15,250,"Sig. 10%","10%"),(25,200,"Sig. 10%","10%"),(35,150,"Sig. 10%","10%"),(45,120,"Sig. 10%","10%"),(55,100,"Sig. 10%","10%"),(65,90,"Sig. 10%","10%"))

def install(m):
    if getattr(m,"_V279_BONUS_CLUSTER",False): return
    try: m.REPORT_TABS.setdefault("operation.bonuses","Bonos")
    except Exception: pass
    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS operation_store_cluster_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,store TEXT NOT NULL,cluster_code TEXT NOT NULL DEFAULT '',effective_from TEXT NOT NULL,changed_at TEXT NOT NULL,changed_by TEXT NOT NULL)""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_op_cluster_store_date ON operation_store_cluster_versions(store,effective_from,id)")

    def norm(v):
        try:return m.login_key(v)
        except Exception:return str(v or '').strip().casefold()
    def num(v):
        try:
            x=float(v or 0);return x if math.isfinite(x) else 0.0
        except Exception:return 0.0
    def stores(): return list(m.store_names(True) or [])
    def canon(v,ss):
        k=norm(v)
        for s in ss:
            if norm(s)==k:return s
        return str(v or '').strip()
    def week_bounds(v):
        raw=str(v or '').strip(); today=datetime.now(MX).date()
        if raw:
            mt=re.fullmatch(r"(\d{4})-W(\d{1,2})",raw,re.I)
            if not mt: raise HTTPException(400,"Semana ISO inválida")
            start=date.fromisocalendar(int(mt.group(1)),int(mt.group(2)),1)
        else:
            iso=today.isocalendar(); start=date.fromisocalendar(iso.year,iso.week,1)
        return start,start+timedelta(days=6)
    def cluster_map(ss,day):
        out={s:"" for s in ss}
        with m.db() as con:
            rows=con.execute("SELECT store,cluster_code FROM operation_store_cluster_versions WHERE effective_from<=? ORDER BY effective_from,id",(day.isoformat(),)).fetchall()
        for r in rows:
            s=canon(r['store'],ss); c=str(r['cluster_code'] or '').upper()
            if s in out: out[s]=c if c in CLUSTERS else ''
        return out
    def fallback():
        try:
            g=m.get_goals() or {}
            for k in ("productividad_diaria","productivity_daily","productivity","productividad"):
                if num(g.get(k))>0:return num(g.get(k))
        except Exception:pass
        return 784.0
    def bonus(rank,total):
        if not rank or not total:return 0,"Sin bono","0%"
        p=(rank-1)/total*100
        for lim,amt,label,pct in BANDS:
            if p<lim:return amt,label,pct
        return 0,"Sin bono","0%"
    def level(amt):
        return "Nivel 4" if amt>=350 else "Nivel 3" if amt>=250 else "Nivel 2" if amt>=120 else "Nivel 1" if amt>0 else "Sin bono"
    def compute(start,end,ss,cmap):
        if not ss:return []
        marks=','.join('?' for _ in ss)
        with m.db() as con:
            cols={r['name'] for r in con.execute("PRAGMA table_info(operation_productivity_timer)").fetchall()}
            extra=lambda n,fb: n if n in cols else fb+" AS "+n
            sql="SELECT id,date,store,user_id,employee_no,employee_name,area,activity,pieces,"+extra('duration_seconds','0')+","+extra('operation_type',"''")+","+extra('capture_group',"''")+","+extra('standard_value','0')+","+extra('hire_date',"''")+" FROM operation_productivity_timer WHERE status='finished' AND date>=? AND date<=? AND store IN ("+marks+") ORDER BY date,id"
            rows=[dict(r) for r in con.execute(sql,(start.isoformat(),end.isoformat(),*ss)).fetchall()]
            users=[dict(r) for r in con.execute("SELECT id,employee_no,fecha_ingreso FROM users WHERE active=1").fetchall()]
        byid={int(x['id']):x for x in users}; byno={str(x.get('employee_no') or ''):x for x in users if str(x.get('employee_no') or '')}
        fb=fallback(); events={}
        for r in rows:
            st=canon(r.get('store'),ss); cl=cmap.get(st,'')
            if not cl: continue
            eno=str(r.get('employee_no') or '').strip(); name=' '.join(str(r.get('employee_name') or 'Sin nombre').split())
            pk=eno or str(r.get('user_id') or '')+'|'+norm(name); grp=str(r.get('capture_group') or '').strip() or 'row-'+str(r.get('id'))
            ek=(str(r.get('date') or '')[:10],st,pk,grp)
            e=events.setdefault(ek,{'date':ek[0],'store':st,'cluster':cl,'eno':eno,'name':name,'uid':int(r.get('user_id') or 0),'pieces':0.0,'dur':0.0,'stdw':0.0,'w':0.0,'ops':set(),'acts':set(),'hire':str(r.get('hire_date') or '')})
            pcs=max(num(r.get('pieces')),0); std=num(r.get('standard_value')) or fb
            e['pieces']+=pcs; e['dur']=max(e['dur'],max(num(r.get('duration_seconds')),0)); e['stdw']+=std*max(pcs,1); e['w']+=max(pcs,1)
            op=str(r.get('operation_type') or 'Origen').title(); e['ops'].add(op if op in ('Origen','Resurtido') else 'Origen'); e['acts'].add(str(r.get('activity') or ''))
        people={}
        for e in events.values():
            k=(e['eno'] or str(e['uid'])+'|'+norm(e['name']),norm(e['store']))
            p=people.setdefault(k,{'employee_no':e['eno'],'name':e['name'],'store':e['store'],'cluster':e['cluster'],'uid':e['uid'],'events':[],'ops':set(),'acts':set(),'hire':e['hire']})
            p['events'].append(e); p['ops']|=e['ops']; p['acts']|=e['acts']; p['hire']=p['hire'] or e['hire']
        out=[]
        for p in people.values():
            u=byid.get(p['uid']) or byno.get(p['employee_no']) or {}; hire=str(u.get('fecha_ingreso') or p['hire'] or '')
            byday={}
            for e in p['events']:byday.setdefault(e['date'],[]).append(e)
            actual=expected=0.0
            for es in byday.values():
                actual+=sum(e['pieces'] for e in es); timed=0.0; daily=[]; missing=False
                for e in es:
                    std=e['stdw']/e['w'] if e['w'] else fb; daily.append((std,max(e['pieces'],1)))
                    if e['dur']>0: timed+=std*(min(e['dur'],43200)/28800)
                    else: missing=True
                den=sum(w for _,w in daily) or 1; dstd=sum(s*w for s,w in daily)/den if daily else fb
                expected+=max(timed,dstd) if missing else (timed if timed>0 else dstd)
            comp=actual/expected*100 if expected else 0
            ops=p['ops']; opt='Mixto' if 'Origen' in ops and 'Resurtido' in ops else ('Resurtido' if 'Resurtido' in ops else 'Origen')
            tenure=-1
            try: tenure=(end-date.fromisoformat(hire[:10])).days if hire else -1
            except Exception:pass
            out.append({'employee_no':p['employee_no'],'name':p['name'],'store':p['store'],'cluster':p['cluster'],'operation_type':opt,'activities':sorted(x for x in p['acts'] if x),'pieces':round(actual,1),'expected':round(expected,1),'compliance_pct':round(comp,1),'days_registered':len(byday),'tenure_ok':tenure>=15,'registration_ok':len(byday)>=6})
        return out
    def rank(items):
        ordered=sorted(items,key=lambda x:(-num(x['compliance_pct']),-num(x['pieces']),norm(x['name'])))
        eligible=[x for x in ordered if x['tenure_ok'] and x['registration_ok']]; pos={id(x):i for i,x in enumerate(eligible,1)}; total=len(eligible)
        for i,x in enumerate(ordered,1):
            er=pos.get(id(x),0); amt,band,pct=(bonus(er,total) if er and num(x['compliance_pct'])>=100 else (0,'Bajo estándar' if er else 'No elegible','0%'))
            x.update(rank=i,eligible_rank=er,bonus=amt,assignment=pct,bonus_band=band,bonus_level=level(amt),eligible=bool(er))
        return ordered

    @m.app.get('/api/operation/clusters-v279')
    def get_clusters(request:Request,effective_date:str=''):
        actor=m.require_user(request); role=str(actor.get('role') or '').lower(); day=date.fromisoformat(effective_date[:10]) if effective_date else datetime.now(MX).date(); ss=stores(); mp=cluster_map(ss,day); counts={c:sum(1 for s in ss if mp.get(s)==c) for c in CLUSTERS}; hist=[]
        if role in ADMIN:
            with m.db() as con: hist=[dict(r) for r in con.execute("SELECT store,cluster_code,effective_from,changed_at,changed_by FROM operation_store_cluster_versions ORDER BY id DESC LIMIT 50").fetchall()]
        return {'stores':[{'store':s,'cluster':mp.get(s,'')} for s in ss],'counts':counts,'editable':role in ADMIN,'history':hist}

    @m.app.post('/api/operation/clusters-v279')
    async def save_clusters(request:Request):
        actor=m.require_user(request,ADMIN); body=await request.json(); eff=str(body.get('effective_from') or datetime.now(MX).date().isoformat())[:10]; date.fromisoformat(eff); ss=stores(); active={norm(s):s for s in ss}; now=datetime.now(MX).isoformat(timespec='seconds'); changed=0
        with m.db() as con:
            for x in body.get('assignments') or []:
                st=active.get(norm(x.get('store'))); c=str(x.get('cluster') or '').upper()
                if not st:continue
                if c and c not in CLUSTERS:raise HTTPException(400,'Clúster inválido')
                r=con.execute("SELECT cluster_code FROM operation_store_cluster_versions WHERE store=? AND effective_from<=? ORDER BY effective_from DESC,id DESC LIMIT 1",(st,eff)).fetchone(); old=str(r['cluster_code'] or '') if r else ''
                if old==c:continue
                con.execute("INSERT INTO operation_store_cluster_versions(store,cluster_code,effective_from,changed_at,changed_by) VALUES(?,?,?,?,?)",(st,c,eff,now,str(actor.get('username') or ''))); changed+=1
        return {'ok':True,'changed':changed,'message':'Clústeres actualizados'}

    @m.app.get('/api/operation/bonuses-v279')
    def get_bonuses(request:Request,week:str='',cluster:str='',store:str='Todas',operation_type:str='Todos'):
        actor=m.require_user(request); role=str(actor.get('role') or '').lower(); start,end=week_bounds(week); ss=stores(); mp=cluster_map(ss,start)
        if role in RESTRICTED:
            ast=canon(actor.get('store'),ss); allowed={mp.get(ast)} if mp.get(ast) else set(); assigned=mp.get(ast,'')
        elif role in PRIV: allowed=set(CLUSTERS); assigned=''
        else: allowed=set(); assigned=''
        selected=str(cluster or '').upper(); selected=selected if selected in allowed else (assigned if assigned in allowed else (sorted(allowed)[0] if allowed else ''))
        people=compute(start,end,ss,mp); grouped={c:[] for c in CLUSTERS}
        for p in people:
            if p['cluster'] in allowed:grouped[p['cluster']].append(p)
        ranked={c:rank(v) for c,v in grouped.items()}; cards=[]
        for c in CLUSTERS:
            if c not in allowed:continue
            xs=ranked[c]; cs=[s for s in ss if mp.get(s)==c]; avg=sum(num(x['compliance_pct']) for x in xs)/len(xs) if xs else 0; wb=sum(1 for x in xs if x['bonus']>0)
            cards.append({'cluster':c,'stores':len(cs),'collaborators':len(xs),'compliance_pct':round(avg,1),'bonus_total':sum(x['bonus'] for x in xs),'with_bonus_pct':round(wb/len(xs)*100,1) if xs else 0})
        view=list(ranked.get(selected,[])); st=canon(store,ss) if store!='Todas' else 'Todas'; op=str(operation_type or 'Todos').title(); op=op if op in ('Todos','Origen','Resurtido','Mixto') else 'Todos'
        if st!='Todas':view=[x for x in view if norm(x['store'])==norm(st)]
        if op!='Todos':view=[x for x in view if x['operation_type']==op]
        return {'week':f'{start.isocalendar().year}-W{start.isocalendar().week:02d}','selected_cluster':selected,'selected_store':st,'operation_type':op,'clusters':cards,'ranking':view,'stores':[s for s in ss if mp.get(s)==selected],'unassigned_stores':[s for s in ss if not mp.get(s)]}

    css=r'''<style id="v279-css">body[data-v163-module="operation"] #v200OperationTabs{grid-template-columns:repeat(6,minmax(0,1fr))!important}.v279{color:#153f70}.v279-filter{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:7px;padding:9px;border:1px solid #d8e4ef;border-radius:12px;background:#fff;margin:5px 0 8px}.v279-f label{display:block;font-size:7px;font-weight:900;color:#65798f;margin-bottom:3px}.v279-f select,.v279-reset{width:100%;height:34px;border:1px solid #ccd9e7;border-radius:8px;background:#fbfdff;color:#173e6d;padding:4px 7px;font-size:8px;font-weight:800}.v279-reset{width:auto;padding:0 12px;align-self:end;background:#fff}.v279-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-bottom:8px}.v279-card{border:1px solid #d9e4ef;border-radius:12px;background:#fff;padding:9px;text-align:left;cursor:pointer;border-top:4px solid var(--c)}.v279-card.active{box-shadow:0 0 0 2px color-mix(in srgb,var(--c) 35%,transparent)}.v279-card b{font-size:12px;color:var(--c)}.v279-card strong{display:block;font-size:20px;margin:7px 0 3px}.v279-card small,.v279-card span{font-size:6.5px;color:#6b7f95}.v279-panel{border:1px solid #d8e4ef;border-radius:12px;background:#fff;padding:9px}.v279-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}.v279-head h3{margin:0;font-size:11px;color:#153f70}.v279-tablewrap{overflow:auto;border:1px solid #e1e8f0;border-radius:9px}.v279-table{width:100%;min-width:880px;border-collapse:collapse;font-size:7px}.v279-table th{background:#103f72;color:#fff;padding:7px 5px;white-space:nowrap}.v279-table td{padding:6px 5px;border-top:1px solid #edf2f6;text-align:center;white-space:nowrap}.v279-table td:nth-child(2),.v279-table th:nth-child(2){text-align:left}.v279-type,.v279-band{display:inline-flex;padding:3px 6px;border-radius:999px;background:#eaf3ff;color:#1768bd;font-weight:900}.v279-type.res{background:#f1eaff;color:#6b45c9}.v279-type.mix{background:#e7f8ef;color:#16824d}.v279-pct{font-weight:950;color:#16824d}.v279-money{font-weight:950;color:#13783f}.v279-note{margin-top:7px;padding:7px 9px;background:#f4f8fd;border-radius:8px;color:#65798f;font-size:7px}.v279-admin{margin-top:12px}.v279-admin-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin:8px 0}.v279-admin-grid div{padding:7px;border:1px solid #dbe6f0;border-radius:8px;text-align:center;font-size:8px}.v279-admin-table{width:100%;min-width:560px;border-collapse:collapse;font-size:7px}.v279-admin-table th{background:#124d84;color:#fff;padding:6px}.v279-admin-table td{padding:5px;border-bottom:1px solid #e8eef4}.v279-admin-table select,.v279-admin-date{height:30px;border:1px solid #ccd8e5;border-radius:7px;background:#fff;padding:3px 6px}.v279-save{border:0;border-radius:8px;background:#176fe8;color:#fff;padding:8px 12px;font-size:7px;font-weight:900;margin-top:7px}@media(max-width:900px){.v279-filter{grid-template-columns:repeat(4,minmax(0,1fr));gap:3px;padding:6px}.v279-f label{font-size:5px}.v279-f select,.v279-reset{height:29px;font-size:6px;padding:2px}.v279-cards{gap:3px}.v279-card{padding:6px;min-height:75px}.v279-card b{font-size:8px}.v279-card strong{font-size:14px}.v279-card small,.v279-card span{font-size:5px}.v279-panel{padding:6px}.v279-table{font-size:6px}.v279-table th,.v279-table td{padding:5px 3px}}</style>'''
    js=r'''<script id="v279-js">(function(){if(window.__V279)return;window.__V279=1;const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)],esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),nf=v=>Math.round(Number(v||0)).toLocaleString('es-MX'),pc=v=>Number(v||0).toLocaleString('es-MX',{maximumFractionDigits:1})+'%',money=v=>'$'+nf(v);let S={week:'',cluster:'',store:'Todas',op:'Todos'},busy=0;async function A(u,o={}){if(typeof api==='function')return api(u,o);let r=await fetch(u,{credentials:'same-origin',cache:'no-store',...o});if(!r.ok)throw new Error(await r.text());return r.json()}function isOp(){return String(document.body.dataset.v163Module||'').toLowerCase()==='operation'}function wk(){let d=new Date(),x=new Date(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())),dy=x.getUTCDay()||7;x.setUTCDate(x.getUTCDate()+4-dy);let y0=new Date(Date.UTC(x.getUTCFullYear(),0,1)),w=Math.ceil((((x-y0)/86400000)+1)/7);return x.getUTCFullYear()+'-W'+String(w).padStart(2,'0')}function opts(){let a=[],d=new Date();for(let i=0;i<12;i++){let x=new Date(d);x.setDate(d.getDate()-i*7);let z=new Date(Date.UTC(x.getFullYear(),x.getMonth(),x.getDate())),dy=z.getUTCDay()||7;z.setUTCDate(z.getUTCDate()+4-dy);let y0=new Date(Date.UTC(z.getUTCFullYear(),0,1)),w=Math.ceil((((z-y0)/86400000)+1)/7),k=z.getUTCFullYear()+'-W'+String(w).padStart(2,'0');if(!a.some(t=>t.k===k))a.push({k,l:'Semana '+w})}return a}function tab(){let h=q('#v200OperationTabs');if(!h)return;let b=q('[data-v200-op="bonuses"]',h);if(!b){b=document.createElement('button');b.type='button';b.dataset.v200Op='bonuses';b.innerHTML='<span class="v203-tab-icon">🏆</span><span class="v203-tab-label">Bonos</span>';let s=q('[data-v200-op="standards"]',h);s?h.insertBefore(b,s):h.appendChild(b);b.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();open()},true)}h.style.setProperty('grid-template-columns','repeat(6,minmax(0,1fr))','important');h.style.setProperty('--v220-count','6')}function active(){qa('#v200OperationTabs [data-v200-op]').forEach(b=>b.classList.toggle('active',b.dataset.v200Op==='bonuses'));let p=q('#operativoPeriodBar');if(p)p.style.setProperty('display','none','important');q('#operativoCentro')?.classList.add('hidden');q('#operativoDynamic')?.classList.remove('hidden');let t=q('#operativoDynamicTitle'),s=q('#operativoDynamicSub');if(t)t.textContent='Bonos Operativos';if(s)s.textContent='Ranking general por clúster y tienda'}function badge(v){let c=v==='Resurtido'?'res':v==='Mixto'?'mix':'';return '<span class="v279-type '+c+'">'+esc(v)+'</span>'}function page(d){let weeks=opts(),stores=['Todas',...(d.stores||[])],colors={A:'#2f80ed',B:'#20b86a',C:'#f3a326',D:'#ed5573'};return '<div class="v279"><div class="v279-filter"><div class="v279-f"><label>Periodo</label><select id="v279W">'+weeks.map(x=>'<option value="'+x.k+'" '+(x.k===S.week?'selected':'')+'>'+x.l+'</option>').join('')+'</select></div><div class="v279-f"><label>Tipo de operación</label><select id="v279O">'+['Todos','Origen','Resurtido','Mixto'].map(x=>'<option '+(x===S.op?'selected':'')+'>'+x+'</option>').join('')+'</select></div><div class="v279-f"><label>Tienda</label><select id="v279S">'+stores.map(x=>'<option '+(x===S.store?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select></div><button class="v279-reset" id="v279R">↻ Restablecer</button></div><div class="v279-cards">'+(d.clusters||[]).map(c=>'<button class="v279-card '+(c.cluster===d.selected_cluster?'active':'')+'" data-c="'+c.cluster+'" style="--c:'+colors[c.cluster]+'"><b>Cluster '+c.cluster+'</b><small>'+nf(c.stores)+' tiendas</small><strong>'+pc(c.compliance_pct)+'</strong><span>'+nf(c.collaborators)+' colaboradores · '+pc(c.with_bonus_pct)+' con bono</span><div class="v279-money">'+money(c.bonus_total)+'</div></button>').join('')+'</div><div class="v279-panel"><div class="v279-head"><h3>🏆 Ranking general por clúster y tienda</h3><span>'+((d.ranking||[]).length)+' colaboradores</span></div><div class="v279-tablewrap"><table class="v279-table"><thead><tr><th>Pos.</th><th>Colaborador</th><th>Tienda</th><th>Tipo operación</th><th>Piezas realizadas</th><th>Piezas esperadas</th><th>% Cumplimiento</th><th>% Asignación</th><th>Nivel bono</th><th>Monto bono</th></tr></thead><tbody>'+((d.ranking||[]).map(r=>'<tr><td>'+(r.rank===1?'🥇':r.rank===2?'🥈':r.rank===3?'🥉':r.rank)+'</td><td><b>'+esc(r.name)+'</b><br><small>'+esc(r.employee_no||'')+'</small></td><td>'+esc(r.store)+'</td><td>'+badge(r.operation_type)+'</td><td>'+nf(r.pieces)+'</td><td>'+nf(r.expected)+'</td><td class="v279-pct">'+pc(r.compliance_pct)+'</td><td><span class="v279-band">'+esc(r.assignment)+'</span></td><td>'+esc(r.bonus_level)+'</td><td class="v279-money">'+money(r.bonus)+'</td></tr>').join('')||'<tr><td colspan="10">Sin datos para esta selección</td></tr>')+'</tbody></table></div><div class="v279-note">Ranking dentro del mismo clúster. El score usa productividad normalizada contra el estándar de circuito completo; Origen, Resurtido y Mixto se clasifican automáticamente. Para bono: 15 días de antigüedad, 6 días con registro, ≥100% del estándar y posición dentro del 65% superior.</div></div>'+(d.unassigned_stores?.length?'<div class="v279-note">⚠ '+d.unassigned_stores.length+' tienda(s) sin clúster. Asígnalas en Estándares Operativos.</div>':'')+'</div>'}async function load(){active();let h=q('#operativoDynamicContent');if(!h)return;h.innerHTML='<div class="infoempty">Cargando bonos…</div>';try{let p=new URLSearchParams({week:S.week||wk(),cluster:S.cluster||'',store:S.store,operation_type:S.op}),d=await A('/api/operation/bonuses-v279?'+p);S.week=d.week;S.cluster=d.selected_cluster;S.store=d.selected_store;S.op=d.operation_type;h.innerHTML=page(d);q('#v279W').onchange=e=>{S.week=e.target.value;S.store='Todas';load()};q('#v279O').onchange=e=>{S.op=e.target.value;load()};q('#v279S').onchange=e=>{S.store=e.target.value;load()};q('#v279R').onclick=()=>{S={week:wk(),cluster:'',store:'Todas',op:'Todos'};load()};qa('.v279-card').forEach(b=>b.onclick=()=>{S.cluster=b.dataset.c;S.store='Todas';load()})}catch(e){h.innerHTML='<div class="infoempty">No fue posible cargar Bonos: '+esc(e.message||e)+'</div>'}}async function open(){if(!isOp())return;S.week=S.week||wk();active();load()}function monday(){let d=new Date(),dy=d.getDay()||7;d.setDate(d.getDate()-dy+1);return d.toLocaleDateString('en-CA',{timeZone:'America/Mexico_City'})}async function admin(){if(busy||!isOp()||!q('#v200OperationTabs [data-v200-op="standards"].active'))return;let h=q('#operativoDynamicContent');if(!h||q('#v279Admin',h)||!q('.v210-std-panel',h))return;busy=1;try{let d=await A('/api/operation/clusters-v279');if(!d.editable)return;h.insertAdjacentHTML('beforeend','<div class="v210-std-panel v279-admin" id="v279Admin"><h3>Configuración de clústeres</h3><div class="v210-note">Administrador y Super Administrador asignan cada tienda a A, B, C o D. La vigencia conserva los rankings históricos.</div><div class="v279-admin-grid">'+['A','B','C','D'].map(c=>'<div><b>Cluster '+c+'</b><br>'+nf(d.counts[c]||0)+' tiendas</div>').join('')+'</div><label class="v210-note">Aplicar desde</label> <input id="v279Date" class="v279-admin-date" type="date" value="'+monday()+'"><div class="v279-tablewrap"><table class="v279-admin-table"><thead><tr><th>Tienda</th><th>Clúster</th></tr></thead><tbody>'+d.stores.map(x=>'<tr><td><b>'+esc(x.store)+'</b></td><td><select class="v279CS" data-store="'+esc(x.store)+'"><option value="">Sin asignar</option>'+['A','B','C','D'].map(c=>'<option '+(x.cluster===c?'selected':'')+'>'+c+'</option>').join('')+'</select></td></tr>').join('')+'</tbody></table></div><button id="v279Save" class="v279-save">Guardar clústeres</button> <span id="v279Msg" class="v210-msg"></span></div>');q('#v279Save').onclick=async()=>{let msg=q('#v279Msg'),eff=q('#v279Date').value,assignments=qa('.v279CS').map(s=>({store:s.dataset.store,cluster:s.value}));msg.textContent='Guardando…';try{let r=await A('/api/operation/clusters-v279',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({effective_from:eff,assignments})});msg.textContent=r.message+' · '+r.changed+' cambio(s)';q('#v279Admin')?.remove();setTimeout(admin,100)}catch(e){msg.textContent=e.message||e}}}catch(e){console.warn(e)}finally{busy=0}}let mo=new MutationObserver(()=>{if(isOp()){tab();setTimeout(admin,20)}});function start(){tab();mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-v163-module']});[150,500,1200].forEach(t=>setTimeout(()=>{tab();admin()},t))}document.addEventListener('click',()=>setTimeout(admin,100),true);if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();})();</script>'''
    @m.app.middleware('http')
    async def v279_html(request,call_next):
        response=await call_next(request)
        if request.url.path!='/' or getattr(response,'status_code',200)!=200:return response
        try:
            body=b''
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode('utf-8',errors='replace')
            if 'id="v279-css"' not in html:html=html.replace('</head>',css+'</head>',1)
            if 'id="v279-js"' not in html:html=html.replace('</body>',js+'</body>',1)
            headers=dict(getattr(response,'headers',{}) or {});headers.pop('content-length',None);headers.update({'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','X-Operations-UI-Version':'V279-BONUS-CLUSTER'})
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print('[V279] HTML warning:',type(exc).__name__,exc,flush=True);return response
    m._V279_BONUS_CLUSTER=True
    print('[V279] Bonos Operativos por clúster A/B/C/D activos.',flush=True)
