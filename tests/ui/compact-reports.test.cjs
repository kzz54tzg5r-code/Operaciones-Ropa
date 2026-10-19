const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync('web/compact_reports.js','utf8');
const wait=()=>new Promise(r=>setTimeout(r,90));
function runtime(content){const dom=new JSDOM(`<main class="main"><section id="page-operativo"><nav id="operativoNav"><button class="active" data-opview="Resumen">Resumen</button></nav><select id="store"><option>Olivar</option></select><div id="operativoDynamicContent">${content}</div></section></main>`,{runScripts:'outside-only',pretendToBeVisual:true});dom.window.scrollTo=()=>{};dom.window.eval(source);return dom;}
test('accordion retains original table nodes, values, handlers and filter selection after opening and closing',async()=>{
 const dom=runtime('<div class="report-kpis"><b>85.1%</b></div><div class="panel"><h3>Ranking</h3><table><tbody><tr><td>123</td></tr></tbody></table><button id="export">Excel</button></div>');
 const d=dom.window.document,table=d.querySelector('table');let clicks=0;d.querySelector('#export').onclick=()=>clicks++;
 await wait();const root=d.querySelector('#operativoDynamicContent'),section=root.querySelector('details.compact-section');
 assert.ok(section);assert.equal(section.open,false);assert.equal(root.querySelector('.compact-preview'),null);
 section.querySelector('summary').click();await wait();assert.equal(section.open,true);
 d.querySelector('#export').click();assert.equal(clicks,1);assert.equal(d.querySelector('table'),table);assert.equal(d.querySelector('#store').value,'Olivar');
 section.querySelector('.compact-section-back').click();await wait();assert.equal(section.open,false);assert.equal(table.textContent,'123');assert.equal(root.querySelectorAll('details').length,1);
 dom.window.close();
});
test('editing forms and error states remain visible and outside disclosures',async()=>{
 const dom=runtime('<div class="error">Sin datos disponibles</div><form><table><tr><td><input value="20"></td></tr></table></form>');await wait();
 assert.equal(dom.window.document.querySelector('input').closest('details'),null);assert.equal(dom.window.document.querySelector('input').value,'20');assert.match(dom.window.document.querySelector('.error').textContent,/Sin datos/);dom.window.close();
});
test('monthly sections expose collection/progress/routes while retaining one complete export table',async()=>{
 const cards=[['TOTAL OPERACIÓN','2,184'],['TOTAL PENDIENTES','5,156'],['TOTAL GENERAL','5,156'],['RECORRIDOS REALIZADOS','5 / 282'],['% ACONDICIONADO','24.2%'],['% UBICADO','10.7%']].map(([l,v])=>`<div class="mct-kpi"><div class="mct-kpi-label">${l}</div><div class="mct-kpi-value">${v}</div></div>`).join('');
 const rows=[['DEV PZS','1,257','—','—','1,257'],['MUERTOS','488','—','—','488'],['TOTAL OPERACIÓN','2,184','—','—','2,184'],['PENDIENTE DE UBICAR','550','—','—','550'],['TOTAL PENDIENTES','5,156','—','—','5,156'],['RECORRIDOS REALIZADOS','5','1.8%','282','—'],['% ACONDICIONADO','24.2%','24.2%','—','—'],['% UBICADO','10.7%','10.7%','—','—']].map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('');
 const dom=runtime(`<div class="mct-kpi-grid">${cards}</div><div class="tablewrap monthly-cross-desktop"><table class="monthly-cross-table"><tbody>${rows}</tbody></table></div>`);
 const d=dom.window.document,table=d.querySelector('table'),original=table.textContent;await wait();
 assert.equal(d.querySelectorAll('table').length,1);assert.equal(table.textContent,original);assert.equal(d.querySelectorAll('.compact-monthly-sections>.compact-section').length,5);
 assert.match(d.querySelector('[data-section="progress"] summary').textContent,/24.2% \/ 10.7%/);
 const collection=d.querySelector('[data-section="collection"]'),progress=d.querySelector('[data-section="progress"]');collection.open=true;await wait();progress.open=true;await wait();assert.equal(collection.open,false);assert.equal(progress.open,true);
 assert.match(collection.textContent,/1,257/);assert.ok(d.querySelector('.mct-kpi-grid.compact-summary-band'));assert.equal(d.querySelector('.compact-preview'),null);dom.window.close();
});
