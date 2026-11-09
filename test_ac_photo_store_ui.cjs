const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const html=fs.readFileSync("ac_capture_laboratorio.html","utf8");
const api=fs.readFileSync("ac_api.py","utf8");

assert.ok(html.includes('id="acStoreChooser"'),"Missing admin store chooser");
assert.ok(html.includes('id="acStore"'),"Missing store dropdown");
assert.ok(html.includes('id="applyAcStore"'),"Missing store selection button");
assert.ok(html.includes('getJson("/stores")'),"Store selector must list authorized project stores");
assert.ok(html.includes('await api("/select-store",{store})'),"Store change must be server-authenticated");
assert.ok(html.includes('if(session||pending)'),"Store switching must be locked during an active session");
assert.ok(html.includes('function showBonusPhoto(model,token,force=false)'),"Missing independent Bonos photo component");
assert.ok(html.includes('"/api/bonuses/product-photo/"+encodeURIComponent(model)'),"Must reuse same Bonos photo endpoint by exact ID");
assert.ok(html.includes('showBonusPhoto(model,token);'),"Photo must load before metadata and Capacidades");
assert.ok(html.includes('↻ Reintentar foto de Bonos'),"Photo must have retry");
assert.ok(!html.includes('No se pudo consultar la fotografía o ubicación.'),"Bad combined error may hide photo");
assert.ok(api.includes('if not store and role not in {"admin","superadmin","director"}'),"Photo must allow authorized admin without store");
assert.ok(api.includes('if store:\n            try:\n                result = catalog_lookup(store, model_id)'),"Catalog only gets verified store");
assert.ok(api.includes('except Exception:'),"Failed catalog should not block photo");

for(const match of html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)){
 if(match[1].trim())new vm.Script(match[1],{filename:"ac_capture_laboratorio.html"});
}
console.log("AC photo/authorization checks and capture HTML JavaScript syntax passed");
