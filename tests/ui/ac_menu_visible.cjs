const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const html=fs.readFileSync(path.join(__dirname,"../../web/index.html"),"utf8");
const sw=fs.readFileSync(path.join(__dirname,"../../web/service-worker.js"),"utf8");
function matches(s){return html.split(s).length-1;}
for(const id of ["acSidebarLink","acMobileLink","acHeroLink"]){
  assert.equal(matches('id="'+id+'"'),1,"Enlace duplicado o faltante: "+id);
}
for(const id of ["acSidebarLink","acMobileLink","acHeroLink"]){
  assert.match(html,new RegExp('id="'+id+'"[^>]*href="/ac"'));
}
assert.equal(matches('class="ac-sidebar-entry ac-entry hidden"'),1);
assert.equal(matches('class="mnav ac-mobile-entry ac-entry hidden"'),1);
assert.equal(matches('class="ac-hero-entry ac-entry hidden"'),1);
assert.match(html,/canOpenAC=\['superadmin','admin','supervisor','gerente','tienda','colaborador_operativo'\]/);
assert.ok(html.includes("document.querySelectorAll('.ac-entry').forEach(x=>x.classList.toggle('hidden',!canOpenAC));"));
assert.ok(html.includes("document.querySelectorAll('.adminOnly').forEach(x=>x.classList.toggle('hidden',!adminView));"));
assert.ok(!html.match(/id="acMobileLink"[^>]*data-main=/),"AC no debe activar tabs del sistema");
assert.match(html,/if\(\['supervisor','gerente'\]\.includes\(u\.role\)\)/);
assert.match(html,/location\.assign\('\/ac\/pedidos'\)/);
assert.match(html,/repeat\(5,minmax\(0,1fr\)\)/);
assert.match(html,/repeat\(2,minmax\(0,1fr\)\)/);
assert.equal(matches('<option value="supervisor">Supervisor · AC</option>'),2);
assert.equal(matches('<option value="gerente">Gerente · AC</option>'),2);
assert.match(html,/colaborador_operativo','supervisor','gerente'\]\.includes\(\$\('#newRole'\)\.value\)/);
assert.match(sw,/operaciones-ropa-runtime-safe-update-v415/);
for(const block of html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)){
  if(block[1].trim())new vm.Script(block[1],{filename:"web/index.html"});
}
console.log("AC visible navigation: all 18 assertions and inline script syntax passed");
