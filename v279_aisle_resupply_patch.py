"""V280 · Resurtido de Pasillos integrado en Operación.
Objetivo = Sugerido 7 (VPD normalizado). Los ~150 pzas sólo organizan rutas
consecutivas de máximo 4 pasillos. La productividad se guarda por pareja.
"""

def install(m):
    if getattr(m,"_V280_AISLE_RESUPPLY",False): return
    import math,re
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    from fastapi import Request
    from fastapi.responses import HTMLResponse

    MX=ZoneInfo("America/Mexico_City")
    PRIV={"superadmin","admin","director","consulta"}
    WRITE={"superadmin","admin","tienda","colaborador_operativo"}
    TARGET=150.0; MAX_AISLES=4

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS operation_aisle_pair_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,date TEXT NOT NULL,shift TEXT NOT NULL DEFAULT 'Matutino',
          store TEXT NOT NULL,capacity_period TEXT DEFAULT '',block_no INTEGER DEFAULT 0,
          aisle TEXT NOT NULL,aisle_no INTEGER,suggested7 REAL NOT NULL DEFAULT 0,
          displacement REAL NOT NULL DEFAULT 0,upper_user_id INTEGER,upper_employee_no TEXT DEFAULT '',
          upper_name TEXT NOT NULL,lower_user_id INTEGER,lower_employee_no TEXT DEFAULT '',
          lower_name TEXT NOT NULL,pieces REAL NOT NULL DEFAULT 0,started_at TEXT NOT NULL,
          finished_at TEXT,duration_seconds INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'active',
          created_by TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_aisle_pair_scope ON operation_aisle_pair_runs(date,store,shift,aisle)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_aisle_pair_actor ON operation_aisle_pair_runs(created_by,status)")

    def num(v):
        try:
            x=float(v or 0); return x if math.isfinite(x) else 0.0
        except Exception: return 0.0
    def norm(v):
        try: return m.login_key(v)
        except Exception: return str(v or "").strip().casefold()
    def actor_store(actor,requested=""):
        stores=list(m.store_names(True) or []); active={norm(x):x for x in stores}
        role=str(actor.get("role") or "").lower(); assigned=str(actor.get("store") or "").strip()
        if role not in PRIV:
            if not assigned: raise m.HTTPException(409,"El usuario no tiene tienda asignada")
            return active.get(norm(assigned),assigned)
        value=str(requested or "").strip()
        if not value or value=="Compañía":
            if assigned and norm(assigned) in active:return active[norm(assigned)]
            if stores:return stores[0]
            raise m.HTTPException(409,"No hay tiendas activas")
        chosen=active.get(norm(value))
        if not chosen: raise m.HTTPException(400,"Tienda inválida")
        return chosen
    def aisle_no(label):
        raw=str(label or "").strip()
        if not raw:return None
        key=raw.upper()
        if any(t in key for t in ("MESA","BOTADERO","EXHIB","PROBADOR")) and "PASILLO" not in key:return None
        for p in (r"\bPASILLO\s*[-#:]?\s*(\d{1,3})\b",r"\bP\s*[-#:]?\s*(\d{1,3})\b",r"\bR\.?\s*COLGAD[AO]\s*[-#:]?\s*(\d{1,3})\b"):
            hit=re.search(p,key)
            if hit:return int(hit.group(1))
        return int(key) if re.fullmatch(r"\d{1,3}",key) else None
    def latest_period():
        try:
            vals=list(m._capacity_period_options("") or []); return vals[0] if vals else ""
        except Exception:return ""
    def staff(store):
        with m.db() as con:
            cols={str(r["name"]) for r in con.execute("PRAGMA table_info(users)").fetchall()}
            ne="full_name" if "full_name" in cols else "username AS full_name"
            ee="employee_no" if "employee_no" in cols else "'' AS employee_no"
            rows=con.execute(f"SELECT id,username,role,store,{ne},{ee} FROM users WHERE active=1 ORDER BY full_name,username").fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            if norm(d.get("store"))!=norm(store):continue
            name=" ".join(str(d.get("full_name") or d.get("username") or "").split())
            if name:out.append({"id":int(d.get("id") or 0),"name":name,"employee_no":str(d.get("employee_no") or ""),"role":str(d.get("role") or "")})
        return out
    def pair_capacity(store):
        start=(datetime.now(MX).date()-timedelta(days=30)).isoformat()
        with m.db() as con:
            rows=con.execute("""SELECT date,upper_user_id,lower_user_id,SUM(pieces) pieces
              FROM operation_aisle_pair_runs WHERE store=? AND status='finished' AND date>=?
              GROUP BY date,upper_user_id,lower_user_id""",(store,start)).fetchall()
        vals=[num(r["pieces"]) for r in rows if num(r["pieces"])>0]
        if len(vals)<3:return 300.0,"Base inicial"
        return max(150.0,min(sum(vals)/len(vals),2000.0)),"Promedio 30 días"
    def done_by_aisle(store,date,shift):
        wh=["store=?","date=?","status='finished'"]; args=[store,date]
        if shift!="Todos":wh.append("shift=?");args.append(shift)
        with m.db() as con:
            rows=con.execute("SELECT aisle,SUM(pieces) pieces FROM operation_aisle_pair_runs WHERE "+" AND ".join(wh)+" GROUP BY aisle",tuple(args)).fetchall()
        return {str(r["aisle"]):num(r["pieces"]) for r in rows}

    def plan(store,date,shift):
        period=latest_period()
        try:raw=list(m._capacity_location_detail(store,"Todas","Todos",period) or [])
        except Exception as exc:
            print(f"[V280] capacidades: {type(exc).__name__}: {exc}",flush=True);raw=[]
        agg={}
        for r in raw:
            no=aisle_no(r.get("location"))
            if no is None:continue
            x=agg.setdefault(no,{"aisle":f"Pasillo {no}","aisle_no":no,"suggested7":0.0,"existence":0.0,"displacement":0.0,"groups":set()})
            x["suggested7"]+=max(num(r.get("suggested")),0)
            x["existence"]+=max(num(r.get("existence")),0)
            x["displacement"]+=max(num(r.get("sales_pzas")),0)
            if r.get("group"):x["groups"].add(str(r.get("group")))
        done=done_by_aisle(store,date,shift); aisles=[]
        for no,x in agg.items():
            target=max(x["suggested7"],0); supplied=max(done.get(x["aisle"],0),0); left=max(target-supplied,0)
            pct=(supplied/target*100) if target else (100 if supplied else 0)
            aisles.append({**{k:v for k,v in x.items() if k!="groups"},"groups":sorted(x["groups"]),"resupplied":supplied,"remaining":left,"progress_pct":min(max(pct,0),100)})
        md=max((x["displacement"] for x in aisles),default=0) or 1; mr=max((x["remaining"] for x in aisles),default=0) or 1
        for x in aisles:
            score=(x["displacement"]/md*100)*.70+(x["remaining"]/mr*100)*.30;x["priority_score"]=round(score,1)
            if x["remaining"]<=0:level,key="Terminado","done"
            elif score>=75:level,key="Crítica","critical"
            elif score>=50:level,key="Alta","high"
            elif score>=25:level,key="Media","medium"
            else:level,key="Baja","low"
            x["priority"]=level;x["priority_key"]=key
        ranked=sorted(aisles,key=lambda x:(-x["priority_score"],-x["displacement"],-x["remaining"],x["aisle_no"]))
        pending={x["aisle_no"]:x for x in ranked if x["remaining"]>0}; blocks=[]; bn=0
        while pending:
            seed=min(pending.values(),key=lambda x:(-x["priority_score"],-x["displacement"],-x["remaining"],x["aisle_no"]))
            members=[]; cursor=seed["aisle_no"]; cumulative=0.0
            while len(members)<MAX_AISLES and cursor in pending:
                x=pending.pop(cursor);members.append(x);cumulative+=max(x["suggested7"],0)
                if cumulative>=TARGET:break
                cursor+=1
            bn+=1
            blocks.append({"block_no":bn,"aisles":[x["aisle"] for x in members],"objective_suggested7":round(sum(x["suggested7"] for x in members),2),
              "resupplied":round(sum(x["resupplied"] for x in members),2),"pending":round(sum(x["remaining"] for x in members),2),
              "displacement":round(sum(x["displacement"] for x in members),2),"priority":members[0]["priority"],"priority_key":members[0]["priority_key"],"items":members})
        objective=sum(x["suggested7"] for x in aisles); supplied=sum(x["resupplied"] for x in aisles); left=max(objective-supplied,0)
        cap,source=pair_capacity(store);pairs=int(math.ceil(left/cap)) if left else 0
        return {"store":store,"date":date,"shift":shift,"capacity_period":period,"aisles":ranked,"blocks":blocks,
          "summary":{"objective_suggested7":round(objective,2),"resupplied":round(supplied,2),"pending":round(left,2),
            "progress_pct":round(min(supplied/objective*100 if objective else 0,100),1),"blocks":len(blocks),"pairs_needed":pairs,
            "collaborators_needed":pairs*2,"pair_capacity":round(cap,1),"pair_capacity_source":source,
            "critical_aisles":sum(1 for x in aisles if x["remaining"]>0 and x["priority_key"]=="critical")},
          "warnings":[] if aisles else ["No se encontraron pasillos numéricos en el archivo vigente de capacidades."]}

    def member(con,user_id,store):
        cols={str(r["name"]) for r in con.execute("PRAGMA table_info(users)").fetchall()}
        ne="full_name" if "full_name" in cols else "username AS full_name"; ee="employee_no" if "employee_no" in cols else "'' AS employee_no"
        row=con.execute(f"SELECT id,username,store,{ne},{ee},active FROM users WHERE id=?",(int(user_id),)).fetchone()
        if not row:raise m.HTTPException(400,"Colaborador no encontrado")
        d=dict(row)
        if not bool(d.get("active")) or norm(d.get("store"))!=norm(store):raise m.HTTPException(400,"El colaborador no pertenece a la tienda")
        return {"id":int(d["id"]),"name":" ".join(str(d.get("full_name") or d.get("username") or "").split()),"employee_no":str(d.get("employee_no") or "")}

    @m.app.get("/api/operation/aisle-resupply-v280/meta")
    def meta(request:Request,store:str=""):
        actor=m.require_user(request);selected=actor_store(actor,store);cap,source=pair_capacity(selected)
        return {"stores":list(m.store_names(True) or []),"store":selected,"date":datetime.now(MX).date().isoformat(),
          "shifts":["Matutino","Vespertino"],"staff":staff(selected),"pair_capacity":round(cap,1),"pair_capacity_source":source,
          "can_write":str(actor.get("role") or "").lower() in WRITE}
    @m.app.get("/api/operation/aisle-resupply-v280/plan")
    def get_plan(request:Request,store:str="",date:str="",shift:str="Matutino"):
        actor=m.require_user(request);selected=actor_store(actor,store)
        try:day=datetime.fromisoformat((date or datetime.now(MX).date().isoformat())[:10]).date().isoformat()
        except Exception:raise m.HTTPException(400,"Fecha inválida")
        sh=str(shift or "Matutino").title();sh=sh if sh in ("Matutino","Vespertino","Todos") else "Matutino"
        return plan(selected,day,sh)
    @m.app.get("/api/operation/aisle-resupply-v280/active")
    def active(request:Request):
        actor=m.require_user(request)
        with m.db() as con:row=con.execute("SELECT * FROM operation_aisle_pair_runs WHERE created_by=? AND status='active' ORDER BY id DESC LIMIT 1",(str(actor.get("username") or ""),)).fetchone()
        return {"item":dict(row) if row else None}
    @m.app.post("/api/operation/aisle-resupply-v280/start")
    async def start(request:Request):
        actor=m.require_user(request,tuple(WRITE));body=await request.json();store=actor_store(actor,str(body.get("store") or ""))
        uid=int(body.get("upper_user_id") or 0);lid=int(body.get("lower_user_id") or 0)
        if not uid or not lid:raise m.HTTPException(400,"Selecciona a los dos integrantes")
        if uid==lid:raise m.HTTPException(400,"Arriba y abajo deben ser colaboradores diferentes")
        no=aisle_no(body.get("aisle"))
        if no is None:raise m.HTTPException(400,"Pasillo inválido")
        try:day=datetime.fromisoformat(str(body.get("date") or datetime.now(MX).date().isoformat())[:10]).date().isoformat()
        except Exception:raise m.HTTPException(400,"Fecha inválida")
        sh=str(body.get("shift") or "Matutino").title();sh=sh if sh in ("Matutino","Vespertino") else "Matutino";now=datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            if con.execute("SELECT id FROM operation_aisle_pair_runs WHERE created_by=? AND status='active' LIMIT 1",(str(actor.get("username") or ""),)).fetchone():raise m.HTTPException(409,"Ya tienes un resurtido en proceso")
            up=member(con,uid,store);lo=member(con,lid,store)
            cur=con.execute("""INSERT INTO operation_aisle_pair_runs(date,shift,store,capacity_period,block_no,aisle,aisle_no,suggested7,displacement,
              upper_user_id,upper_employee_no,upper_name,lower_user_id,lower_employee_no,lower_name,pieces,started_at,status,created_by,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'active',?,?)""",(day,sh,store,str(body.get("capacity_period") or ""),int(body.get("block_no") or 0),
              f"Pasillo {no}",no,max(num(body.get("suggested7")),0),max(num(body.get("displacement")),0),up["id"],up["employee_no"],up["name"],
              lo["id"],lo["employee_no"],lo["name"],0.0,now,str(actor.get("username") or ""),now))
            rid=int(cur.lastrowid)
        return {"ok":True,"id":rid,"message":f"Resurtido iniciado en Pasillo {no}"}
    @m.app.post("/api/operation/aisle-resupply-v280/{record_id}/finish")
    async def finish(record_id:int,request:Request):
        actor=m.require_user(request,tuple(WRITE));body=await request.json();pieces=max(num(body.get("pieces")),0);now_dt=datetime.now(MX);now=now_dt.isoformat(timespec="seconds")
        with m.db() as con:
            row=con.execute("SELECT * FROM operation_aisle_pair_runs WHERE id=?",(record_id,)).fetchone()
            if not row:raise m.HTTPException(404,"Registro no encontrado")
            d=dict(row)
            if d.get("status")!="active":raise m.HTTPException(409,"Este resurtido ya fue finalizado")
            if str(d.get("created_by") or "")!=str(actor.get("username") or "") and str(actor.get("role") or "").lower() not in {"superadmin","admin"}:raise m.HTTPException(403,"No puedes finalizar el registro de otro usuario")
            try:
                began=datetime.fromisoformat(str(d.get("started_at") or ""));began=began if began.tzinfo else began.replace(tzinfo=MX);secs=max(int((now_dt-began.astimezone(MX)).total_seconds()),1)
            except Exception:secs=1
            con.execute("UPDATE operation_aisle_pair_runs SET pieces=?,finished_at=?,duration_seconds=?,status='finished',updated_at=? WHERE id=?",(pieces,now,secs,now,record_id))
        return {"ok":True,"message":"Productividad de la pareja guardada","pieces":pieces,"duration_seconds":secs,"productivity_per_hour":round(pieces/(secs/3600),1) if secs else 0}

    css=r'''<style id="v280-aisle-css">
body[data-v163-module="operation"] #v200OperationTabs [data-v200-op="aisle-resupply"]{display:flex!important}
body[data-v280-view="aisle-resupply"] #operativoPeriodBar{display:none!important}.v280{color:#123f73}.v280 *{box-sizing:border-box}
.v280-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:4px 0 7px}.v280-head h2{margin:0!important;font-size:18px!important}.v280-filters{display:flex;gap:5px}
.v280 select,.v280 input{height:30px;border:1px solid #cad8e5;border-radius:8px;background:#fff;color:#123f73;padding:0 7px;font-size:8px;font-weight:800}
.v280-kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:6px}.v280-k{padding:7px;border:1px solid #dce7f1;border-radius:10px;background:#fff;min-height:72px}
.v280-k b{display:block;font-size:21px;margin-top:7px}.v280-k small,.v280-note{font-size:6px;color:#73879a}.v280-grid{display:grid;grid-template-columns:1.55fr .8fr;gap:6px}.v280-bottom{display:grid;grid-template-columns:1fr 240px;gap:6px;margin-top:6px}
.v280-panel{border:1px solid #d8e4ee;border-radius:10px;background:#fff;overflow:hidden}.v280-title{background:#123f68;color:#fff;padding:7px 9px;font-size:9px;font-weight:950}
.v280-block{border:1px solid #dce7f0;border-left:4px solid #ff8a34;border-radius:8px;margin:5px;overflow:hidden}.v280-block.critical{border-left-color:#ef476f}.v280-block.medium{border-left-color:#f3c42f}.v280-block.low{border-left-color:#56bf70}
.v280-bh{display:grid;grid-template-columns:1fr auto auto;gap:5px;align-items:center;padding:5px 6px;font-size:6px}.v280-bh strong{font-size:7px}.v280-bh button{border:0;border-radius:6px;background:#1682ee;color:#fff;padding:5px 7px;font-size:6px;font-weight:900}
.v280 table{width:100%;border-collapse:collapse;table-layout:fixed}.v280 th{background:#f2f7fb;font-size:5.5px;padding:4px 1px}.v280 td{border-top:1px solid #edf2f6;text-align:center;font-size:6px;padding:4px 1px}
.v280-bar{height:7px;background:#e8eef3;border-radius:99px;overflow:hidden}.v280-bar i{display:block;height:100%;background:#22b868}.v280-cap{padding:8px}.v280-field{margin-bottom:6px}.v280-field label{display:block;font-size:6px;font-weight:900;margin-bottom:3px}.v280-pair{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.v280-timer{text-align:center;font-size:23px;font-weight:950;background:#edf6ff;padding:7px;border-radius:9px;margin:5px 0}.v280-actions{display:grid;grid-template-columns:1fr 1fr;gap:4px}.v280-actions button{border:0;border-radius:7px;height:32px;color:#fff;font-size:6px;font-weight:950}.v280-start{background:#1682ee}.v280-finish{background:#10a95b}.v280-actions button:disabled{opacity:.45}
.v280-summary{padding:9px}.v280-summary b{font-size:24px}.v280-alert{margin-top:7px;padding:6px;border-radius:7px;background:#fff0f2;color:#a7283f;font-size:6px;font-weight:900}
@media(max-width:700px){.v280-head h2{font-size:13px!important}.v280 select,.v280 input{height:24px;font-size:5px;max-width:96px}.v280-kpis{gap:2px}.v280-k{padding:4px;min-height:52px}.v280-k b{font-size:13px}.v280-k small,.v280-note{font-size:4px}.v280-grid,.v280-bottom{grid-template-columns:1fr;gap:3px}.v280-title{font-size:6px;padding:5px}.v280 th,.v280 td{font-size:4px;padding:3px 1px}.v280-bh{font-size:4px}.v280-timer{font-size:17px}}
</style>'''
    js=r'''<script id="v280-aisle-js">(function(){if(window.__V280_AISLE_RESUPPLY)return;window.__V280_AISLE_RESUPPLY=true;
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)],n=v=>Number(v||0)||0,nf=v=>Math.round(n(v)).toLocaleString('es-MX'),pc=v=>n(v).toLocaleString('es-MX',{maximumFractionDigits:1})+'%',e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let meta=null,p=null,act=null,aisle='',block=0,timer=0,busy=false;
const isOp=()=>String(document.body.dataset.v163Module||'').toLowerCase()==='operation';
async function A(u,o){let r=await fetch(u,{credentials:'same-origin',cache:'no-store',...(o||{})}),d={};try{d=await r.json()}catch(_){}if(!r.ok)throw new Error(d.detail||d.message||('HTTP '+r.status));return d}
function tab(){let h=q('#v200OperationTabs');if(!h)return null;let b=q('[data-v200-op="aisle-resupply"]',h);if(!b){b=document.createElement('button');b.type='button';b.dataset.v200Op='aisle-resupply';b.innerHTML='<span class="v203-tab-icon">↕</span><span class="v203-tab-label">Resurtido<br>Pasillos</span>';let before=q('[data-v200-op="bonuses"]',h)||q('[data-v200-op="standards"]',h);before?h.insertBefore(b,before):h.appendChild(b)}const count=Math.max(1,h.querySelectorAll(':scope > button[data-v200-op]').length);h.style.setProperty('grid-template-columns','repeat('+count+',minmax(0,1fr))','important');h.style.setProperty('--v220-count',String(count));return b}
function view(){window.V149_OPERATION_TAB='aisle-resupply';window.V125_OPERATION_TAB='aisle-resupply';document.body.dataset.v280View='aisle-resupply';qa('#v200OperationTabs [data-v200-op]').forEach(b=>b.classList.toggle('active',b.dataset.v200Op==='aisle-resupply'));let x=q('#operativoPeriodBar');if(x)x.style.display='none'}
function staff(v){return '<option value="">Seleccionar</option>'+(meta?.staff||[]).map(x=>'<option value="'+x.id+'" '+(String(v||'')===String(x.id)?'selected':'')+'>'+e(x.name)+(x.employee_no?' · '+e(x.employee_no):'')+'</option>').join('')}
function row(x,withPriority){return '<tr data-v280-aisle="'+e(x.aisle)+'"><td>'+x.aisle_no+'</td><td>'+nf(x.suggested7)+'</td><td>'+nf(x.resupplied)+'</td><td>'+nf(x.remaining)+'</td><td>'+nf(x.displacement)+'</td><td>'+pc(x.progress_pct)+'</td>'+(withPriority?'<td>'+e(x.priority)+'</td>':'')+'<td><div class="v280-bar"><i style="width:'+Math.min(100,n(x.progress_pct))+'%"></i></div></td></tr>'}
function blocks(){return (p?.blocks||[]).map(b=>'<div class="v280-block '+e(b.priority_key)+'"><div class="v280-bh"><strong>Bloque '+b.block_no+' · '+e((b.aisles||[]).join(' · '))+'</strong><span>Objetivo S7 '+nf(b.objective_suggested7)+' pzas · '+e(b.priority)+'</span><button data-v280-block="'+b.block_no+'">Asignar pareja</button></div><table><thead><tr><th>Pasillo</th><th>Sugerido 7</th><th>Resurtido</th><th>Falta</th><th>Desp.</th><th>%</th><th>Avance</th></tr></thead><tbody>'+(b.items||[]).map(x=>row(x,false)).join('')+'</tbody></table></div>').join('')||'<div class="v280-summary">Sin pasillos pendientes.</div>'}
function cap(){let a=(p?.aisles||[]).find(x=>x.aisle===aisle)||(p?.aisles||[]).find(x=>x.remaining>0)||(p?.aisles||[])[0];if(a)aisle=a.aisle;let run=!!act,id=act?.aisle||a?.aisle||'',target=act?.suggested7??a?.suggested7??0;return '<div class="v280-cap"><div class="v280-field"><label>Pasillo</label><select id="v280Aisle" '+(run?'disabled':'')+'>'+(p?.aisles||[]).map(x=>'<option value="'+e(x.aisle)+'" '+(x.aisle===id?'selected':'')+'>'+e(x.aisle)+' · S7 '+nf(x.suggested7)+' · falta '+nf(x.remaining)+'</option>').join('')+'</select></div><div class="v280-pair"><div class="v280-field"><label>↑ Altura · baja tallas</label><select id="v280Up" '+(run?'disabled':'')+'>'+staff(act?.upper_user_id)+'</select></div><div class="v280-field"><label>↓ Abajo · recibe/acomoda</label><select id="v280Lo" '+(run?'disabled':'')+'>'+staff(act?.lower_user_id)+'</select></div></div><div class="v280-field"><label>Objetivo pasillo · Sugerido 7</label><input value="'+nf(target)+' pzas" disabled></div><div id="v280Timer" class="v280-timer">00:00:00</div><div class="v280-field"><label>Piezas resurtidas por la pareja</label><input id="v280Pieces" type="number" min="0" value="0" '+(!run?'disabled':'')+'></div><div class="v280-actions"><button id="v280Start" class="v280-start" '+(run||!meta?.can_write?'disabled':'')+'>▶ Iniciar</button><button id="v280Finish" class="v280-finish" '+(!run||!meta?.can_write?'disabled':'')+'>■ Finalizar</button></div><div id="v280Msg" class="v280-note"></div><div class="v280-note">Las piezas se contabilizan una sola vez para la pareja.</div></div>'}
function render(){view();let h=q('#operativoDynamicContent');if(!h)return;let s=p?.summary||{},stores=(meta?.stores||[]).map(x=>'<option '+(x===p?.store?'selected':'')+'>'+e(x)+'</option>').join('');h.innerHTML='<div class="v280"><div class="v280-head"><div><h2>Resurtido de Pasillos</h2><div class="v280-note">Objetivo total = Sugerido 7. Los bloques de ~150 sólo organizan el recorrido consecutivo.</div></div><div class="v280-filters"><select id="v280Store">'+stores+'</select><input id="v280Date" type="date" value="'+e(p?.date||meta?.date||'')+'"><select id="v280Shift"><option '+(p?.shift==='Matutino'?'selected':'')+'>Matutino</option><option '+(p?.shift==='Vespertino'?'selected':'')+'>Vespertino</option></select></div></div><div class="v280-kpis"><div class="v280-k"><small>Piezas pendientes</small><b>'+nf(s.pending)+'</b><small>de '+nf(s.objective_suggested7)+' Sugerido 7</small></div><div class="v280-k"><small>Bloques</small><b>'+nf(s.blocks)+'</b><small>máx. 4 pasillos</small></div><div class="v280-k"><small>Parejas necesarias</small><b>'+nf(s.pairs_needed)+'</b><small>'+nf(s.pair_capacity)+' pzas/pareja</small></div><div class="v280-k"><small>Colaboradores</small><b>'+nf(s.collaborators_needed)+'</b><small>2 por pareja</small></div><div class="v280-k"><small>Avance general</small><b>'+pc(s.progress_pct)+'</b><small>'+nf(s.resupplied)+' / '+nf(s.objective_suggested7)+'</small></div></div><div class="v280-grid"><section class="v280-panel"><div class="v280-title">1. Bloques consecutivos por resurtir</div>'+blocks()+'</section><section class="v280-panel"><div class="v280-title">2. Productividad de pareja por pasillo</div><div id="v280Cap">'+cap()+'</div></section></div><div class="v280-bottom"><section class="v280-panel"><div class="v280-title">3. Avance de resurtido por pasillo · Objetivo = Sugerido 7</div><table><thead><tr><th>Pasillo</th><th>Sugerido 7</th><th>Resurtido</th><th>Falta</th><th>Desp.</th><th>%</th><th>Prioridad</th><th>Avance</th></tr></thead><tbody>'+(p?.aisles||[]).map(x=>row(x,true)).join('')+'</tbody></table></section><section class="v280-panel"><div class="v280-title">Resumen</div><div class="v280-summary"><b>'+pc(s.progress_pct)+'</b><div>'+nf(s.resupplied)+' de '+nf(s.objective_suggested7)+' piezas</div><div class="v280-alert">'+nf(s.critical_aisles)+' pasillos críticos</div><div class="v280-note">Capacidad: '+nf(s.pair_capacity)+' pzas/pareja · '+e(s.pair_capacity_source||'')+'</div></div></section></div></div>';bind();clock()}
function clock(){clearInterval(timer);let z=q('#v280Timer');if(!z)return;if(!act?.started_at){z.textContent='00:00:00';return}let f=()=>{let sec=Math.max(0,Math.floor((Date.now()-new Date(act.started_at).getTime())/1000)),hh=String(Math.floor(sec/3600)).padStart(2,'0'),mm=String(Math.floor(sec%3600/60)).padStart(2,'0'),ss=String(sec%60).padStart(2,'0');z.textContent=hh+':'+mm+':'+ss};f();timer=setInterval(f,1000)}
function bind(){q('#v280Store')?.addEventListener('change',()=>load());q('#v280Date')?.addEventListener('change',()=>load());q('#v280Shift')?.addEventListener('change',()=>load());q('#v280Aisle')?.addEventListener('change',x=>aisle=x.target.value);qa('[data-v280-aisle]').forEach(x=>x.addEventListener('click',()=>{aisle=x.dataset.v280Aisle;q('#v280Cap').innerHTML=cap();bind()}));qa('[data-v280-block]').forEach(x=>x.addEventListener('click',()=>{let b=(p?.blocks||[]).find(y=>y.block_no===Number(x.dataset.v280Block)),a=b?.items?.find(y=>y.remaining>0)||b?.items?.[0];if(a){aisle=a.aisle;block=b.block_no;q('#v280Cap').innerHTML=cap();bind()}}));q('#v280Start')?.addEventListener('click',start);q('#v280Finish')?.addEventListener('click',finish)}
async function start(){let msg=q('#v280Msg');try{let a=(p?.aisles||[]).find(x=>x.aisle===(q('#v280Aisle')?.value||aisle)),up=Number(q('#v280Up')?.value||0),lo=Number(q('#v280Lo')?.value||0);if(!a||!up||!lo)throw new Error('Selecciona pasillo y pareja');msg.textContent='Iniciando…';await A('/api/operation/aisle-resupply-v280/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({store:q('#v280Store')?.value,date:q('#v280Date')?.value,shift:q('#v280Shift')?.value,capacity_period:p?.capacity_period||'',block_no:block,aisle:a.aisle,suggested7:a.suggested7,displacement:a.displacement,upper_user_id:up,lower_user_id:lo})});await load()}catch(err){msg.textContent=err.message}}
async function finish(){let msg=q('#v280Msg');try{let pieces=Number(q('#v280Pieces')?.value||0);await A('/api/operation/aisle-resupply-v280/'+act.id+'/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pieces})});act=null;await load()}catch(err){msg.textContent=err.message}}
async function load(){if(busy)return;busy=true;try{let st=q('#v280Store')?.value||q('#operStoreSelect')?.value||'';meta=await A('/api/operation/aisle-resupply-v280/meta?store='+encodeURIComponent(st));st=st&&st!=='Compañía'?st:meta.store;let date=q('#v280Date')?.value||meta.date,shift=q('#v280Shift')?.value||'Matutino';[p,act]=await Promise.all([A('/api/operation/aisle-resupply-v280/plan?'+new URLSearchParams({store:st,date,shift})),A('/api/operation/aisle-resupply-v280/active').then(x=>x.item||null)]);if(act){aisle=act.aisle;block=Number(act.block_no||0)}render()}catch(err){let h=q('#operativoDynamicContent');if(h)h.innerHTML='<div class="v280-summary">'+e(err.message)+'</div>'}finally{busy=false}}
function activate(){if(isOp()){view();load()}}
function boot(){let b=tab();if(b&&!b.dataset.v280){b.dataset.v280='1';b.addEventListener('click',ev=>{ev.preventDefault();ev.stopImmediatePropagation();activate()},true)}if(isOp()&&String(window.V149_OPERATION_TAB||'')==='aisle-resupply')activate()}
document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,250),{once:true});document.addEventListener('click',x=>{if(x.target.closest?.('[data-main="operation"]'))setTimeout(boot,150)},true);[500,1200,2500].forEach(ms=>setTimeout(boot,ms));
})();</script>'''

    @m.app.middleware("http")
    async def v280_html(request,call_next):
        response=await call_next(request)
        if request.url.path!="/" or getattr(response,"status_code",200)!=200:return response
        try:
            body=b""
            async for chunk in response.body_iterator:body+=chunk
            html=body.decode("utf-8",errors="replace")
            if 'id="v280-aisle-css"' not in html:html=html.replace("</head>",css+"</head>",1)
            if 'id="v280-aisle-js"' not in html:html=html.replace("</body>",js+"</body>",1)
            headers=dict(getattr(response,"headers",{}) or {});headers.pop("content-length",None);headers["Cache-Control"]="no-store";headers["X-Operations-UI-Version"]="V280-AISLE-RESUPPLY-SUG7"
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V280] HTML warning: {type(exc).__name__}: {exc}",flush=True);return response

    m._V280_AISLE_RESUPPLY=True
    print("[V280] Resurtido de Pasillos + Sugerido 7 + parejas instalado.",flush=True)
