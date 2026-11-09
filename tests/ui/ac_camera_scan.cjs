/* Price Shoes barcode camera: exact examples from real garment tags. */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const barcode=require("../../web/ac_barcode.js");
const samples=[
 ["133408714$","1334087","7/8","14"],
 ["133408726$","1334087","13/14","26"],
 ["122400022$","1224000","11/12","22"],
 ["122400018$","1224000","9/10","18"],
 ["OI26133408726$","1334087","13/14","26"],
 ["OI25122400022S","1224000","11/12","22"],
 ["O126133408726$","1334087","13/14","26"],
 ["122400022S","1224000","11/12","22"],
 ["0133408714$","1334087","7/8","14"]
];
for(const [raw,id,size,code] of samples){
 const parsed=barcode.parse(raw);
 assert.equal(parsed.valid,true,raw);
 assert.equal(parsed.modelId,id,raw);
 assert.equal(parsed.size,size,raw);
 assert.equal(parsed.sizeCode,code,raw);
 assert.equal(parsed.needsReview,false,raw);
}
assert.deepEqual(barcode.parse("1334087").modelId,"1334087");
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),["7/8","9/10","11/12","13/14"]).size,"7/8");
assert.equal(barcode.resolveSize(barcode.parse("133408726$"),["9/10","11/12","13/14"]).size,"13/14");
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),["M","G"]).size,null);
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),[]).size,null);
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),["7-8","9-10"]).size,"7-8");
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),["7/8","14"]).status,"ambiguous");
assert.equal(barcode.resolveSize(barcode.parse("133408714$"),["7/8 AÑOS"]).size,"7/8 AÑOS");

assert.equal(barcode.parse("133408799$").needsReview,true);
assert.equal(barcode.parse("133408799$").size,null);
for(const input of ["","99","1234567890123","1234567XYZ","OI2613340872","129900000000"]){
 assert.equal(barcode.parse(input).valid,false,input);
}
for(const file of ["ac_capture_laboratorio.html"]){
 const html=fs.readFileSync(path.join(__dirname,"../../",file),"utf8");
 assert.ok(html.includes('id="openCamera"'),"Visible camera button missing");
 assert.ok(html.includes('id="cameraOverlay"'),"Full-screen camera overlay missing");
 assert.ok(html.includes('id="cameraVideo"'),"Video tag missing");
 assert.ok(!html.includes('id="cameraFile"'),"Continuous scanning should not require taking photos");
 assert.ok(!html.includes('id="cameraPhoto"'),"Remove Take Photo button for automatic scanning");
 assert.ok(html.includes('id="sizeRange"'),"Must show sizes from Capacidades");
 assert.ok(html.includes('/capacity/model-sizes?model_id='),"Must request model-specific size range");
 assert.ok(html.includes('window.ACBarcode.resolveSize'),"Must verify suffix against real model sizes");
 assert.ok(html.includes('if(selectedTask)return Object.keys(selectedTask.remaining||{})'),"Keep assigned-task sizes");
 assert.ok(html.includes('id="scanSize"'),"Detected child age size missing");
 assert.ok(html.includes('id="manualId"'),"Keyboard fallback missing");
 assert.ok(html.includes('$("model").addEventListener("click"'),"Tapping ID should open iPhone camera");
 assert.ok(html.includes("scannedLabelSize"),"Age size must be included in quantities");
 assert.ok(html.includes("findModel();"),"Scanned model must invoke official photo lookup");
 assert.ok(html.includes('src="/static/ac_barcode.js?v=417"'));
 assert.ok(html.includes('src="/static/ac_scanner.js?v=417"'));
 for(const match of html.matchAll(/<script(?: [^>]*)?>([\s\S]*?)<\/script>/g)){
   if(match[1].trim())new vm.Script(match[1],{filename:file});
 }
}
const camera=fs.readFileSync(path.join(__dirname,"../../web/ac_scanner.js"),"utf8");
new vm.Script(camera,{filename:"web/ac_scanner.js"});
for(const k of ["getUserMedia","facingMode","environment","decodeFromStream",
 "BrowserMultiFormatOneDReader","BarcodeDetector","getVideoTracks",
 "track.stop()","getSupportedFormats","code_128"]){
  assert.ok(camera.includes(k),"Camera feature missing: "+k);
}
assert.ok(camera.includes("window.ZXingBrowser")||camera.includes("root.ZXingBrowser"));
console.log("AC barcode camera: examples, iPhone scanner, fallback and syntax OK");
