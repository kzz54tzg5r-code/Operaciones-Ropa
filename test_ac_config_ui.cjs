const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const html=fs.readFileSync("ac_configuracion.html","utf8");
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
assert.ok(match,"No se encontró script de configuración AC");
new vm.Script(match[1],{filename:"ac_configuracion.html"});
for(const label of [
 'id="setStore"','id="capacityFile"','id="capacityVersion"',
 'id="kind"','id="location"','id="saveCount"',
 'id="username"','id="password"','id="role"',
 '/api/ac/stock/initial-count','/api/ac/stock/locations',
 '/api/ac/capacity/upload','/api/ac/select-store',
 '/api/users','acPendingPhysicalCount'
]){
 assert.ok(html.includes(label),"Falta pantalla AC: "+label);
}
console.log("16 comprobaciones de configuración AC y sintaxis completadas");
