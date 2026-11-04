const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const code=fs.readFileSync(path.join(__dirname,'../../web/correccion_visual_v411.js'),'utf8');
const html=fs.readFileSync(path.join(__dirname,'../../web/index.html'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../../web/correccion_visual_v411.css'),'utf8');
assert.ok(html.indexOf('reporte_adaptable_v407.css')<html.indexOf('correccion_visual_v411.css'));
assert.ok(html.indexOf('designs_25_approved_v410.css')<html.indexOf('correccion_visual_v411.css'));
assert.equal((html.match(/correccion_visual_v411\.css/g)||[]).length,1);
assert.equal((html.match(/correccion_visual_v411\.js/g)||[]).length,1);
assert.ok(css.includes('grid-template-columns:repeat(auto-fit,minmax(168px,1fr))'));
assert.ok(css.includes('#accordion>.acc:first-child .mini3'));
assert.ok(css.includes('.or411-duplicate{display:none!important}'));
assert.ok(css.includes('#analysisNav:has(#v193SellBtn)>button[data-sub="sellthrough"]'));
assert.ok(css.includes('display:none!important'));

const parts=[
'<div id="appView"><main class="main"><header class="hero">Cabecera</header>',
'<div class="bad-legacy-flex">',
'<div class="rt-carousel-shell" id="ops-shell"><div id="operativoNav" class="hidden">',
'<button class="switch" data-opview="Centro Ejecutivo">Centro Ejecutivo</button></div></div>',
'<div class="rt-carousel-shell" id="analysis-shell"><div id="analysisNav">',
'<button class="switch active" data-sub="accordion" data-tab-key="commercial.accordion">Acordeón comercial</button>',
'<button class="switch" data-sub="stores" data-tab-key="commercial.stores">Tiendas</button>',
'<button class="switch" data-sub="stores" data-tab-key="commercial.stores">Tiendas</button>',
'<button class="switch" data-sub="sellthrough" data-tab-key="commercial.sellthrough">Sell Through</button>',
'<button class="switch" data-sub="sell" data-tab-key="commercial.sell">Sell Through</button>',
'</div></div><div id="globalFilters"><select id="week"><option>2026-S44</option></select></div>',
'</div><section id="page-accordion">Contenido real</section></main></div>'
];
const dom=new JSDOM(parts.join(''),{url:'https://operaciones-ropa.onrender.com/',runScripts:'dangerously',pretendToBeVisual:true});
dom.window.eval(code);
dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
setTimeout(()=>{
 const d=dom.window.document;
 const hero=d.querySelector('.hero');
 assert.equal(hero.nextElementSibling.id,'ops-shell');
 assert.equal(d.querySelector('#ops-shell').nextElementSibling.id,'analysis-shell');
 assert.equal(d.querySelector('#analysis-shell').nextElementSibling.id,'globalFilters');
 assert.ok(d.body.classList.contains('or411-fix'));
 assert.equal(d.querySelector('#globalFilters select').value,'2026-S44');
 assert.equal(d.querySelectorAll('#analysisNav button.or411-duplicate').length,1);
 assert.equal(d.querySelectorAll('#analysisNav button:not(.or411-duplicate)').length,4);
 assert.equal(d.querySelector('#analysisNav button.active').dataset.sub,'accordion');
 const before=d.querySelectorAll('#analysisNav button').length;
 d.querySelector('[data-sub="accordion"]').click();
 setTimeout(()=>{
  assert.equal(d.querySelectorAll('#analysisNav button').length,before);
  dom.window.close();
  console.log('V411 navegación y filtros: PASS');
 },35);
},35);
