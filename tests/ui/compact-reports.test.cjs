const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync('web/compact_reports.js','utf8');
const wait=()=>new Promise(r=>setTimeout(r,70));
test('summary/detail keeps original values, handlers, filters and survives content refresh',async()=>{
 const dom=new JSDOM(`<main class="main"><section id="page-operativo"><button class="active" data-opview="Resumen">Resumen</button><select id="store"><option>Olivar</option></select><div id="operativoDynamicContent"><div class="report-kpis"><b>85.1%</b></div><div class="panel"><h3>Ranking</h3><div class="tablewrap"><table><tbody><tr><td>123</td></tr></tbody></table></div><button id="export">Excel</button></div></div></section></main>`,{runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;w.scrollTo=()=>{};w.eval(source);await wait();
 const d=w.document,root=d.querySelector('#operativoDynamicContent');let clicks=0;d.querySelector('#export').onclick=()=>clicks++;
 let button=root.querySelector('.compact-detail-bar button');assert.ok(button);assert.equal(button.textContent,'Ver detalle');
 assert.ok(root.querySelector('.compact-detail-closed'));assert.equal(root.querySelector('.report-kpis').textContent,'85.1%');
 button.click();assert.equal(button.getAttribute('aria-expanded'),'true');assert.equal(root.querySelector('.compact-detail-closed'),null);
 d.querySelector('#export').click();assert.equal(clicks,1);assert.equal(d.querySelector('#store').value,'Olivar');
 root.querySelector('td').textContent='456';await wait();assert.equal(root.querySelectorAll('.compact-detail-bar').length,1);
 button.click();assert.equal(button.textContent,'Ver detalle');assert.equal(root.querySelector('td').textContent,'456');
 root.innerHTML='<div class="report-kpis">90%</div><div class="tablewrap"><table><tr><td>789</td></tr></table></div>';
 await wait();assert.equal(root.querySelectorAll('.compact-detail-bar').length,1);assert.equal(root.querySelector('.compact-detail-bar button').getAttribute('aria-expanded'),'false');
 dom.window.close();
});
test('editing forms and error/empty states remain visible',async()=>{
 const dom=new JSDOM('<main class="main"><div id="v313Host"><div class="error">Sin datos disponibles</div><form><table><tr><td><input value="20"></td></tr></table></form></div></main>',{runScripts:'outside-only',pretendToBeVisual:true});
 dom.window.eval(source);await wait();assert.equal(dom.window.document.querySelector('.compact-detail-closed'),null);assert.equal(dom.window.document.querySelector('input').value,'20');dom.window.close();
});
