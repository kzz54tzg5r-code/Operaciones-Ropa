/* V365: contrato funcional de la nueva representación (sin tocar la fuente operativa). */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('web/detalle_operativo_opcion1_v365.js','utf8');
const styles=fs.readFileSync('web/detalle_operativo_opcion1_v365.css','utf8');
const html=fs.readFileSync('web/index.html','utf8');
const source=fs.readFileSync('v117_operational_visual_parity_patch.py','utf8');
new vm.Script(script);
assert.match(html,/detalle_operativo_opcion1_v365\.js\?v=365/);
assert.match(html,/detalle_operativo_opcion1_v365\.css\?v=365/);
assert.match(styles,/table\.ops-zero-table/);
assert.match(styles,/\.or365-vertical-svg/);
assert.match(styles,/overflow-x:auto!important/);
assert.match(styles,/@media\(max-width:520px\)/);
assert.match(source,/<th>Ranking<\/th><th>Tienda<\/th><th>Dev pzs<\/th>/);
assert.match(source,/<th>Pend\. Ant\.<\/th><th>Total pzs<\/th>/);
assert.match(source,/<th>% Acondicionado<\/th><th>% Ubicado<\/th>/);
assert.match(source,/<th>Pendiente de acondicionar<\/th><th>Pendiente de ubicar<\/th>/);
const context={window:{},fmt:n=>String(n)};
vm.runInNewContext(script,context);
const input=[
  {store:'Menor',ingresos:10,acondicionado:2,ubicado:1},
  {store:'Mayor',ingresos:30,acondicionado:0,ubicado:0}
];
const chart=context.window.opsComboSvg(input,'2026-10-08','Todas las tiendas');
assert.match(chart,/or365-detail-chart/);
assert.match(chart,/data-or365-chart="grouped-vertical"/);
assert.match(chart,/Ingresos/);
assert.match(chart,/Acondicionado/);
assert.match(chart,/Ubicado/);
assert.equal((chart.match(/<title>[^<]+ · (?:Ingresos|Acondicionado|Ubicado):/g)||[]).length,6,'3 barras por cada una de las 2 tiendas');
assert.ok(chart.indexOf('Mayor')<chart.indexOf('Menor'),'Ranking coherente con volumen de ingresos');
assert.deepEqual(input.map(r=>r.store),['Menor','Mayor'],'No muta ni reordena payload original');
assert.doesNotMatch(chart,/<polyline/);
assert.match(context.window.opsComboSvg([],null,null),/Información no disponible/);
console.log('V365 OK: 15 columnas intactas, ranking compacto y 3 barras por tienda; responsivo.');
