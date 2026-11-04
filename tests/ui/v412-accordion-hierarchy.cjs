const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync(path.resolve(__dirname,'../../web/acordeon_jerarquico_v412.js'),'utf8');
const names=['Resumen general','Secciones','Marcas campeonas','Rubros campeones','Ubicaciones','Modelos 80/20','Tipo de catálogo'];
function cards(version='old'){
 return names.map((title,i)=>'<div class="acc '+(i===0?'open':'')+'"><button>'+title+'<span>'+(i===0?'−':'+')+'</span></button>'+
 '<div class="accbody"><table class="table"><thead><tr><th>'+title+'</th></tr></thead>'+
 '<tbody><tr><td data-sentinel="'+version+'-'+i+'">'+version+' '+i+'</td></tr></tbody></table></div></div>').join('');
}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function run(){
 const dom=new JSDOM('<!doctype html><html><body><section id="page-accordion"><div id="accordion">'+cards()+'</div></section></body></html>',{
  url:'https://operaciones-ropa.onrender.com/',pretendToBeVisual:true,runScripts:'dangerously'
 });
 const w=dom.window,d=w.document,root=d.getElementById('accordion');
 const originalNodes=[...root.querySelectorAll(':scope > .acc')];
 const originalCells=[...root.querySelectorAll('td')];
 try {
  w.eval(source);
  d.dispatchEvent(new w.Event('DOMContentLoaded'));
  await delay(70);
  assert.equal(root.querySelectorAll('.or412-accordion-step').length,7);
  assert.equal(root.querySelectorAll('.or412-accordion-detail>.acc').length,7);
  assert.equal(root.querySelectorAll('.or412-accordion-detail>.acc.or412-selected').length,1);
  assert.equal(root.querySelectorAll('.or412-accordion-sidebar [aria-pressed="true"]').length,1);
  assert.ok(root.querySelector('.or412-accordion-layout'));
  assert.deepEqual([...root.querySelectorAll('td')],originalCells,'original real table cells retained');
  assert.deepEqual([...root.querySelectorAll('.or412-accordion-detail>.acc')],originalNodes,'original accordion handlers kept');
  const buttons=[...root.querySelectorAll('.or412-accordion-step')];
  buttons[5].click();
  assert.equal(buttons[5].getAttribute('aria-pressed'),'true');
  assert.equal(root.querySelectorAll('.or412-accordion-detail>.acc.or412-selected').length,1);
  assert.equal(root.querySelector('.or412-accordion-detail>.acc.or412-selected td').getAttribute('data-sentinel'),'old-5');
  assert.equal(root.querySelectorAll('td').length,7);
  buttons[6].dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
  assert.equal(root.querySelector('.or412-accordion-detail>.acc.or412-selected td').getAttribute('data-sentinel'),'old-0');
  // The existing API re-renders the seven real panels after a filter change.
  root.innerHTML=cards('new');
  await delay(80);
  assert.equal(root.querySelectorAll('.or412-accordion-step').length,7,'rerender must not multiply navigation');
  assert.equal(root.querySelectorAll('.or412-accordion-detail>.acc').length,7);
  assert.equal(root.querySelector('.or412-accordion-detail>.acc.or412-selected td').getAttribute('data-sentinel'),'new-0');
  assert.equal(root.querySelectorAll('td').length,7);
  console.log('V412 Acordeón jerárquico: navegación, datos y refiltros OK');
 } finally {
  dom.window.close();
 }
}
run().catch(e=>{console.error(e);process.exitCode=1});
