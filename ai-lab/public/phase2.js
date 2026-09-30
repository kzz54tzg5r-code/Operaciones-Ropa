
(()=>{
  const $=s=>document.querySelector(s);
  const $$=s=>[...document.querySelectorAll(s)];
  const nf=new Intl.NumberFormat("es-MX",{maximumFractionDigits:0});
  const pf=v=>(Number(v||0)).toFixed(1)+"%";
  const set=(id,v)=>{const el=document.getElementById(id);if(el)el.textContent=v};

  const css=document.createElement("link");
  css.rel="stylesheet"; css.href="/phase2.css?v=20260930-2120"; document.head.appendChild(css);

  function panelFor(reportId,label){
    const report=document.getElementById(reportId);
    if(!report) return null;
    return [...report.querySelectorAll(".panel")].find(p=>p.textContent.includes(label));
  }
  function assignKpiIds(){
    const cy=document.getElementById("cy-resumen");
    if(cy){
      for(const k of cy.querySelectorAll(".kpi")){
        const label=(k.querySelector("small")?.textContent||"").trim();
        const strong=k.querySelector("strong");
        if(!strong) continue;
        const ids={Ingresos:"cyIngresos",Muertos:"cyMuertos",Habilitado:"cyHabilitado",Ubicado:"cyUbicado",Pendiente:"cyPendiente"};
        if(ids[label]) strong.id=ids[label];
      }
      for(const row of cy.querySelectorAll(".progress-list>div")){
        const t=row.textContent;
        const b=row.querySelector("b");
        if(!b) continue;
        if(t.includes("Habilitado / Ingresos")) b.id="cyPctHI";
        else if(t.includes("Ubicado / Habilitado")) b.id="cyPctUH";
        else if(t.includes("Ubicado / Ingresos")) b.id="cyPctUI";
      }
      const filters=document.querySelector("#cambios .filters");
      if(filters){
        const sels=filters.querySelectorAll("select");
        if(sels[0]) sels[0].id="cyPeriod";
        if(sels[1]) sels[1].id="cyStore";
        const btn=filters.querySelector(".filter-action"); if(btn) btn.id="cyRefresh";
      }
    }
    const op=document.getElementById("op-resumen");
    if(op){
      for(const k of op.querySelectorAll(".kpi")){
        const label=(k.querySelector("small")?.textContent||"").trim();
        const strong=k.querySelector("strong");
        if(!strong) continue;
        const ids={Ingresos:"opIngresos",Habilitado:"opHabilitado",Ubicado:"opUbicado",Recorridos:"opRecorridos",Productividad:"opProductividad"};
        if(ids[label]) strong.id=ids[label];
      }
      const filters=document.querySelector("#operaciones .filters");
      if(filters){
        const sels=filters.querySelectorAll("select");
        if(sels[0]) sels[0].id="opPeriod";
        if(sels[1]) sels[1].id="opStore";
        const btn=filters.querySelector(".filter-action"); if(btn) btn.id="opRefresh";
      }
    }
  }

  function installUploader(){
    const p=panelFor("cambios","Fuente del laboratorio");
    if(!p||p.querySelector("#opsFileInput")) return;
    const tag=p.querySelector(".tag"); if(tag){tag.id="opsSourceTag";tag.textContent="Sin copia operativa";}
    const desc=p.querySelector(".muted"); if(desc){desc.id="opsSourceText";desc.textContent="Carga una copia del Excel operativo para alimentar estos indicadores sin tocar Producción.";}
    const wrap=document.createElement("div"); wrap.className="lab-upload-row";
    wrap.innerHTML='<input id="opsFileInput" type="file" accept=".xlsx,.xls"><button id="opsUploadBtn">Cargar copia operativa</button>';
    const help=document.createElement("small"); help.className="lab-upload-help";help.id="opsUploadHelp";help.textContent="Se procesa únicamente dentro del IA Lab.";
    p.append(wrap,help);
  }

  function populate(periods,stores){
    for(const id of ["cyPeriod","opPeriod"]){
      const el=document.getElementById(id); if(!el) continue;
      el.innerHTML=(periods||[]).slice().reverse().map((p,i)=>'<option value="'+p+'">'+(i===0?"Semana actual · ":"")+p+"</option>").join("")||'<option value="all">Sin periodos</option>';
    }
    for(const id of ["cyStore","opStore"]){
      const el=document.getElementById(id); if(!el) continue;
      el.innerHTML='<option value="Compañía">Compañía</option>'+(stores||[]).map(s=>'<option value="'+s+'">'+s+"</option>").join("");
    }
  }
  function fill(s){
    if(!s)return;
    set("cyIngresos",nf.format(s.ingresos)); set("cyMuertos",nf.format(s.muertos));
    set("cyHabilitado",nf.format(s.habilitado)); set("cyUbicado",nf.format(s.ubicado)); set("cyPendiente",nf.format(s.pendienteUbicar));
    set("cyPctHI",pf(s.pctHabilitadoIngresos)); set("cyPctUH",pf(s.pctUbicadoHabilitado)); set("cyPctUI",pf(s.pctUbicadoIngresos));
    set("opIngresos",nf.format(s.ingresos)); set("opHabilitado",nf.format(s.habilitado)); set("opUbicado",nf.format(s.ubicado));
    set("opRecorridos",nf.format(s.recorridos)); set("opProductividad",nf.format(s.productivity));
  }
  async function summary(prefix){
    const p=document.getElementById(prefix==="op"?"opPeriod":"cyPeriod");
    const st=document.getElementById(prefix==="op"?"opStore":"cyStore");
    const q=new URLSearchParams({period:p?.value||"",store:st?.value||"Compañía"});
    const r=await fetch("/api/lab/operations/summary?"+q);
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||"Sin copia operativa");
    fill(j.summary);
    return j;
  }
  async function status(){
    try{
      const r=await fetch("/api/lab/operations/status"); const j=await r.json();
      if(j.loaded){
        set("opsSourceTag","Copia operativa activa");
        set("opsSourceText",(j.sourceFile||"Copia operativa")+" · "+nf.format(j.rowCount||0)+" registros");
        populate(j.periods,j.stores);
        await summary("cy");
      }
    }catch(e){}
  }
  async function upload(){
    const input=$("#opsFileInput"), btn=$("#opsUploadBtn"), help=$("#opsUploadHelp");
    if(!input?.files?.[0]){if(help)help.textContent="Selecciona primero el Excel de la copia.";return;}
    const fd=new FormData(); fd.append("file",input.files[0]);
    btn.disabled=true; if(help)help.textContent="Procesando copia operativa…";
    try{
      const r=await fetch("/api/lab/operations/upload",{method:"POST",body:fd}); const j=await r.json();
      if(!r.ok) throw new Error(j.error||"No se pudo procesar");
      set("opsSourceTag","Copia operativa activa");
      set("opsSourceText",j.sourceFile+" · "+nf.format(j.summary.rows)+" registros · "+j.latestPeriod);
      populate(j.periods,j.stores); fill(j.summary);
      if(help) help.textContent="Copia cargada en el IA Lab. Producción no fue modificada.";
    }catch(e){if(help)help.textContent="Error: "+e.message}
    finally{btn.disabled=false}
  }

  assignKpiIds(); installUploader();
  $("#opsUploadBtn")?.addEventListener("click",upload);
  $("#cyRefresh")?.addEventListener("click",()=>summary("cy").catch(e=>set("opsUploadHelp",e.message)));
  $("#opRefresh")?.addEventListener("click",()=>summary("op").catch(()=>{}));
  status();
})();
