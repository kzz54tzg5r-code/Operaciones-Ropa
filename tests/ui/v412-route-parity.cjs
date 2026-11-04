/* V412: probar ruta real -> diseño aprobado, no solo lista estática. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const script=fs.readFileSync(path.join(__dirname,'../../web/designs_25_approved_v410.js'),'utf8');

async function probe({main='analysis',analysisSub='macro',operTab='operations.center',page='page-macro',capture=false,expected}){
 const analysis=main==='analysis',oper=main==='operativo';
 const markup=[
  '<!doctype html><html><body'+(capture?' class="v241-cm-capture"':'')+'>',
  '<div id="sidebar"><button data-main="analysis" class="'+(analysis?'active':'')+'"></button><button data-main="operativo" class="'+(oper?'active':'')+'"></button></div>',
  '<div id="analysisNav" class="'+(analysis?'':'hidden')+'"><button data-sub="'+analysisSub+'" data-tab-key="commercial.'+analysisSub+'" class="switch active"></button></div>',
  '<div id="operativoNav" class="'+(oper?'':'hidden')+'"><button data-tab-key="'+operTab+'" data-opview="Cargar productividad" class="switch active"></button></div>',
  '<section id="page-operativo" class="'+(page==='page-operativo'?'active':'')+'"></section>',
  '<section id="page-macro" class="'+(page==='page-macro'?'active':'')+'"></section>',
  '<section id="page-sellthrough-clean" class="'+(page==='page-sellthrough-clean'?'active':'')+'"></section>',
  '<section id="page-bonuses" class="'+(page==='page-bonuses'?'active':'')+'"></section>',
  '<section id="page-lingerie-checklist"></section></body></html>'
 ].join('');
 const dom=new JSDOM(markup,{url:'https://operaciones-ropa.onrender.com/',pretendToBeVisual:true,runScripts:'dangerously'});
 dom.window.eval(script);
 dom.window.document.dispatchEvent(new dom.window.Event('DOMContentLoaded'));
 await new Promise(resolve=>setTimeout(resolve,50));
 const actual=dom.window.document.body.dataset.or410Tab;
 assert.equal(actual,expected,'Vista inesperada para '+JSON.stringify({main,analysisSub,operTab,page,capture}));
 assert.equal(dom.window.OR410_APPROVED_DESIGNS.length,25);
 dom.window.close();
}

(async()=>{
 await probe({expected:'commercial.macro'});
 await probe({analysisSub:'accordion',page:'page-macro',expected:'commercial.accordion'});
 await probe({analysisSub:'sellthrough-clean',page:'page-sellthrough-clean',expected:'commercial.sell'});
 await probe({main:'operativo',operTab:'operations.center',page:'page-operativo',expected:'operations.center'});
 await probe({main:'operativo',operTab:'operations.productivity_capture',page:'page-operativo',capture:true,expected:'operations.capture'});
 await probe({main:'operativo',operTab:'operations.recovery_audit',page:'page-operativo',expected:'operations.recovery_audit'});
 await probe({main:'operativo',operTab:'operations.goals',page:'page-operativo',expected:'operations.goals'});
 await probe({main:'operativo',page:'page-bonuses',expected:'operations.bonuses'});
 console.log('V412 rutas de pestaña -> diseño aprobado OK');
})().catch(err=>{console.error(err);process.exitCode=1;});
