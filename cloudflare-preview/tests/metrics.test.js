import test from "node:test";
import assert from "node:assert/strict";
import {periodBounds,aggregate,visibleInPeriod} from "../src/metrics.js";
test("Día, semana ISO (lunes), mes y año",()=>{
 assert.deepEqual(periodBounds("week","2026-10-30"),{start:"2026-10-26",end:"2026-11-01"});
 assert.deepEqual(periodBounds("day","2026-10-30"),{start:"2026-10-30",end:"2026-10-30"});
 assert.deepEqual(periodBounds("month","2026-10-30"),{start:"2026-10-01",end:"2026-10-31"});
 assert.deepEqual(periodBounds("year","2026-10-30"),{start:"2026-01-01",end:"2026-12-31"});
});
test("resúmenes y pendientes dependen de piezas",()=>{
 const a=aggregate([{store_name:"Olivar",ingested:100,prepared:80,placed:70,walks_real:9,walks_target:8}]);
 assert.equal(a.total.pending_prepared,20);
 assert.equal(a.total.pending_placed,10);
 assert.equal(a.total.pct_walks,100);
 assert.equal(a.total.pct_prepared,80);
 assert.equal(a.total.pct_placed,88);
});
test("selección de tienda y fecha",()=>{
 const data=[{store_name:"Olivar",operation_date:"2026-10-30",ingested:90},{store_name:"Centro",operation_date:"2026-10-30",ingested:20},{store_name:"Olivar",operation_date:"2026-09-30",ingested:10}];
 assert.equal(aggregate(visibleInPeriod(data,"month","2026-10-30"),"Olivar").total.ingested,90);
});
