/* Verifica que la pantalla AC incluye colas, validación de tallas y JS válido. */
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const html=fs.readFileSync("ac_capture_laboratorio.html","utf8");
const match=html.match(/<script>([\s\S]*?)<\/script>/i);
assert.ok(match,"Debe existir script de captura AC");
new vm.Script(match[1],{filename:"ac_capture_laboratorio.html"});
for(const needle of [
 'id="queueSection"',
 'id="taskList"',
 'id="refreshQueue"',
 'async function refreshTasks()',
 'async function takeTask(task)',
 '"/tasks?session_id="',
 '"/claim"',
 'selectedTask.remaining',
 'task_id:selectedTask?.id||null',
 'Ubicada toda la talla',
 'Modelo completo: se marcaron',
 'La talla "+size+" supera las piezas pendientes'
]){
 assert.ok(html.includes(needle),"Falta en pantalla: "+needle);
}
console.log("13 verificaciones de colas y sintaxis de interfaz completadas");
