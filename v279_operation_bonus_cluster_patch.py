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
        return {'week':f'{start.isocalendar().year}-W{start.isocalendar().week:02d}','selected_cluster':selected,'selected_store':st,'operation_type':op,'clusters':cards,'ranking':view,'stores':[s f