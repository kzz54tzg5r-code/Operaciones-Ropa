// V362 · Tests de contrato: preservación de captura, vistas y scripts.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const read=file=>fs.readFileSync(file,'utf8');
const cm=read('v199_access_perf_productivity_patch.py');
const op=read('v222_operation_capture_nav_admin_patch.py');
const index=read('web/index.html');
const css=read('web/operaciones_aprobadas_v362.css');
const client=read('web/operaciones_aprobadas_v362.js');
const extract=(source,filename)=>{
 const match=source.match(/\bjs\s*=\s*r(?:'''|""")<script[^>]*>([\s\S]*?)<\/script>(?:'''|""")/);
 assert.ok(match,'No se encontró JavaScript embebido en '+filename);
 return match[1];
};
[
 ['Cambios y Muertos',extract(cm,'v199')],
 ['Captura Operación',extract(op,'v222')],
 ['Diseños aprobados',client],
].forEach(([name,script])=>{
 new vm.Script(script,{filename:name});
 console.log('Sintaxis correcta:',name);
});
for(const source of [cm,op]){
 assert.match(source,/id=\\"v199Start\\"|id="v199Start"|id=\\"v222Start\\"|id="v222Start"/);
 assert.match(source,/id=\\"v199Finish\\"|id="v199Finish"|id=\\"v222Finish\\"|id="v222Finish"/);
 assert.match(source,/Hora de inicio/);
 assert.match(source,/Hora de fin/);
 assert.match(source,/Tiempo realizado/);
 assert.match(source,/clockTime\(r.started_at\)/);
 assert.match(source,/clockTime\(r.ended_at\)/);
}
assert.match(op,/"ended_at": str\(row.get\("ended_at"\)/);
assert.match(index,/operaciones_aprobadas_v362.css/);
assert.match(index,/operaciones_aprobadas_v362.js/);
assert.match(index,/OR362_ENHANCE_REPORT\(name,d\)/);
assert.match(cm,/OR362_PRODUCTIVITY_LAYOUT\(rep\)/);
assert.match(client,/lastProductivityReport/);
assert.match(client,/\.storeProjectEdit/);
assert.match(client,/operations\.goals/);
assert.match(client,/Cumplimiento de Recorridos/);
assert.match(css,/operations\.recovery_store/);
assert.match(css,/operations\.productivity/);
assert.match(css,/or362-time-grid/);
assert.match(css,/or362-goals-kpis/);
console.log('Contrato V362: botones, horas, registros, informes y diseño: OK');
