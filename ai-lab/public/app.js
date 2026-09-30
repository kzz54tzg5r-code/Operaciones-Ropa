const titles={home:"Centro de control IA",cambios:"Cambios y Muertos",operaciones:"Operaciones",ia:"Asistente IA",usuarios:"Usuarios y permisos"};
const contexts={home:"Laboratorio independiente",cambios:"Reporte 01 · Laboratorio",operaciones:"Reporte 02 · Laboratorio",ia:"Inteligencia artificial · Laboratorio",usuarios:"Control de acceso · Laboratorio"};
const nav=[...document.querySelectorAll(".nav")],views=[...document.querySelectorAll(".view")];

function openView(id){
  nav.forEach(x=>x.classList.toggle("active",x.dataset.view===id));
  views.forEach(v=>v.classList.toggle("active",v.id===id));
  document.getElementById("title").textContent=titles[id]||"Operaciones Ropa";
  document.getElementById("contextLabel").textContent=contexts[id]||"Laboratorio";
  window.scrollTo({top:0,behavior:"smooth"});
}
nav.forEach(btn=>btn.addEventListener("click",()=>openView(btn.dataset.view)));
document.querySelectorAll("[data-open]").forEach(card=>card.addEventListener("click",e=>{if(e.target.closest("button")||e.currentTarget===card)openView(card.dataset.open)}));

document.querySelectorAll(".report-tabs").forEach(group=>{
  const buttons=[...group.querySelectorAll("button")];
  buttons.forEach(btn=>btn.addEventListener("click",()=>{
    buttons.forEach(x=>x.classList.remove("active"));
    btn.classList.add("active");
    const report=group.closest(".report-view");
    report.querySelectorAll(".tab-panel").forEach(p=>p.classList.remove("active"));
    document.getElementById(btn.dataset.tab)?.classList.add("active");
    btn.scrollIntoView({behavior:"smooth",inline:"center",block:"nearest"});
  }));
});

const stores=["Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte","Ixtapaluca","Querétaro","Centro","Olivar","León","Puebla","Puebla Sur","Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac"];
document.getElementById("storeGoalRows").innerHTML=stores.map(s=>`<tr><td>${s}</td><td>✓</td><td>✓</td><td>784</td><td>47</td></tr>`).join("");
document.getElementById("recoveryRows").innerHTML=stores.slice(0,8).map(s=>`<tr><td>${s}</td><td>$—</td><td>$—</td><td>—%</td><td>—</td></tr>`).join("");
const months=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
document.getElementById("monthRows").innerHTML=months.map(m=>`<tr><td>${m}</td><td>$—</td><td>$—</td><td>—%</td><td>—%</td><td>＋ Ver detalle</td></tr>`).join("");

const roleHints={
  "Super Administrador":"Acceso completo al laboratorio, incluidas vistas de rol, usuarios, cargas y metas.",
  "Administrador":"Gestión operativa, datos, reportes y usuarios autorizados.",
  "Director / Consulta":"Consulta de reportes ejecutivos sin administración ni cargas.",
  "Tienda":"Vista limitada a una tienda y sus indicadores.",
  "Colaborador Lencería":"Acceso enfocado al Checklist Lencería y evidencias.",
  "Colaborador Operativo":"Acceso enfocado a productividad y captura operativa."
};
document.getElementById("roleDemo").addEventListener("change",e=>{document.getElementById("roleHint").textContent=roleHints[e.target.value]||""});

async function health(){
  try{
    const r=await fetch("/api/health"),j=await r.json();
    const active=j.mode==="openai";
    document.getElementById("mode").textContent=active?"OpenAI conectado":"Demo · sin consumo API";
    document.getElementById("aiState").textContent=active?"OpenAI conectado":"Modo demo: aún sin API key";
    document.getElementById("aiPill").textContent=active?"OpenAI conectado":"Modo demo";
  }catch{
    document.getElementById("mode").textContent="Servicio disponible";
  }
}
health();

const form=document.getElementById("chatForm"),input=document.getElementById("chatInput"),box=document.getElementById("messages");
function add(text,type){const d=document.createElement("div");d.className="msg "+type;d.textContent=text;box.appendChild(d);box.scrollTop=box.scrollHeight}
async function ask(q){
  if(!q.trim())return;
  add(q,"user");input.value="";input.disabled=true;
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q})});
    const j=await r.json();
    if(!r.ok)throw new Error(j.error||"Error");
    add(j.answer,"bot");
  }catch(e){add("Error: "+e.message,"error")}finally{input.disabled=false;input.focus()}
}
form.addEventListener("submit",e=>{e.preventDefault();ask(input.value)});
document.querySelectorAll("[data-q]").forEach(b=>b.addEventListener("click",()=>ask(b.dataset.q)));