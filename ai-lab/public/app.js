const titles={home:"Centro de control IA",cambios:"Cambios y Muertos",operaciones:"Operaciones",ia:"Asistente IA",usuarios:"Usuarios y permisos"};
const nav=[...document.querySelectorAll(".nav")];
const views=[...document.querySelectorAll(".view")];
nav.forEach(btn=>btn.addEventListener("click",()=>{nav.forEach(x=>x.classList.remove("active"));btn.classList.add("active");views.forEach(v=>v.classList.remove("active"));document.getElementById(btn.dataset.view).classList.add("active");document.getElementById("title").textContent=titles[btn.dataset.view]}));

async function health(){
  try{
    const r=await fetch("/api/health"); const j=await r.json();
    document.getElementById("mode").textContent=j.mode==="openai"?"OpenAI conectado":"Demo · sin consumo API";
    document.getElementById("aiState").textContent=j.mode==="openai"?"OpenAI conectado":"Modo demo: aún sin API key";
  }catch{document.getElementById("mode").textContent="Servicio disponible";}
}
health();

const form=document.getElementById("chatForm");
const input=document.getElementById("chatInput");
const box=document.getElementById("messages");
function add(text,type){const d=document.createElement("div");d.className="msg "+type;d.textContent=text;box.appendChild(d);box.scrollTop=box.scrollHeight}
async function ask(q){
  if(!q.trim())return;
  add(q,"user"); input.value=""; input.disabled=true;
  try{
    const r=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q})});
    const j=await r.json();
    if(!r.ok) throw new Error(j.error||"Error");
    add(j.answer,"bot");
  }catch(e){add("Error: "+e.message,"error")}finally{input.disabled=false;input.focus()}
}
form.addEventListener("submit",e=>{e.preventDefault();ask(input.value)});
document.querySelectorAll("[data-q]").forEach(b=>b.addEventListener("click",()=>ask(b.dataset.q)));