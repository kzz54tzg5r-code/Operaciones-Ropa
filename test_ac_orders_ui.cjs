const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const orders=fs.readFileSync("ac_orders_laboratorio.html","utf8");
const capture=fs.readFileSync("ac_capture_laboratorio.html","utf8");
for(const [label,html] of [["orders",orders],["capture",capture]]){
 const match=html.match(/<script>([\s\S]*?)<\/script>/i);
 assert.ok(match,"No hay script "+label);
 new vm.Script(match[1],{filename:label+".html"});
}
for(const fragment of [
 'id="model"','id="criterion"','id="area"','id="sizes"','id="approve"',
 '"/orders/preview?model_id="','"/orders/approve"',
 'acPendingOrder','Autorizar y reservar','confirm("¿Autorizar',
 'id="history"','"/orders"','/api/bonuses/product-photo/'
])assert.ok(orders.includes(fragment),"Falta en pedidos: "+fragment);
for(const fragment of [
 'id="floorLocation"','async function loadFloorLocations()',
 '"/locations?kind=Piso"','target_location_id',
 'Origen: ','"Resurtido"&&$("stage").value==="Ubicar"',
 'selectedTask?.id||null'
])assert.ok(capture.includes(fragment),"Falta en captura: "+fragment);
console.log("22 verificaciones de pedidos, ubicaciones e interfaz completadas");
