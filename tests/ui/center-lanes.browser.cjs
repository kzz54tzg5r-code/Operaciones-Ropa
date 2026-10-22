// Full production HTML, isolated API fixtures. Never signs into production.
const fs=require('fs'),path=require('path'),os=require('os'),Module=require('module'),assert=require('node:assert/strict'),{spawnSync}=require('child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const root=path.resolve(__dirname,'../..'),out=fs.mkdtempSync(path.join(os.tmpdir(),'ropa-center-'));
const rendered=spawnSync(process.env.PYTHON||'python3',[root+'/tests/ui/render_production_page.py',out],{cwd:root,encoding:'utf8',timeout:60000});assert.equal(rendered.status,0,rendered.stderr);
if(process.env.ROPA_LEGACY_HTML){const file=out+'/page.html';fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace(/<script src="\/static\/center_lanes.js[^"]*" defer><\/script>/,''));}
const fixtureFile=root+'/tests/ui/runtime-fixture.cjs',mod=new Module(fixtureFile,module);mod.filename=fixtureFile;mod.paths=Module._nodeModulePaths(path.dirname(fixtureFile));mod._compile(fs.readFileSync(fixtureFile,'utf8')+'\nmodule.exports.fixture=fixture;module.exports.report=report;',fixtureFile);const {fixture,report}=mod.exports;
const metrics={...report.metrics,dev_pzs:600,muertos:200,cajas:150,probador:50,ingresos:1000,total_pzs:1000,acondicionado:800,ubicado:600,recorridos:5,meta_recorridos:10,pct_acondicionado:80,pct_ubicado:60,pct_recorridos:50,pendiente_acondicionar:200,pendiente_ubicar:200};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.ROPA_CHROMIUM_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process','--no-zygote','--in-process-gpu','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1366,height:950}}),errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:fs.readFileSync(out+'/page.html','utf8')});if(u.pathname.startsWith('/static/')){const file=out+'/web/'+u.pathname.slice(8);if(fs.existsSync(file))return route.fulfill({path:file});}
 if(u.pathname.startsWith('/api/')){requests.push(u.pathname+u.search);if(u.pathname.includes('export')){const pdf=u.searchParams.get('format')==='pdf';return route.fulfill({contentType:pdf?'application/pdf':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers:{'Content-Disposition':'attachment; filename="fixture.'+(pdf?'pdf':'xlsx')+'"'},body:Buffer.from(pdf?'%PDF-1.4 fixture':'xlsx fixture')});}let data=fixture(u.pathname,u.searchParams);if(u.pathname==='/api/operations/meta')data={...report,stores:['Iztapalapa'],stores_available:['Iztapalapa'],stores_detected:['Iztapalapa']};if(u.pathname==='/api/stores')data={stores:[{id:1,name:'Iztapalapa',active:true,project:true}],editable:true,history:[]};if(/^\/api\/operations(?:\/project-scope-v151|\/year)?$/.test(u.pathname))data={...report,metrics,stores:[{...report.stores[0],...metrics}],recovery_by_store:[{...report.recovery_by_store[0],recovery_pct:52.7,recovered_value:1000}],v153_project_store_count:1};return route.fulfill({json:data});}return route.fulfill({status:204,body:''});});
 await page.goto('https://app.test/');await page.waitForTimeout(1200);await page.evaluate(()=>enter({id:1,username:'QA',role:'admin',store:'',can_preview_roles:false}));await page.evaluate(()=>refreshOperativoMeta());await page.locator('.ocl-lanes').waitFor();await page.waitForTimeout(400);
 await page.locator('.or356-dashboard .or356-table tbody tr').first().waitFor({timeout:12000});
 const snapshot=await page.evaluate(()=>({
  rows:[...document.querySelectorAll('.or356-dashboard .or356-table tbody tr')].map(tr=>tr.textContent),
  side:[...document.querySelectorAll('.or356-dashboard .or356-sidepanels .or356-card')].map(x=>x.textContent),
  data:window.OR356_CENTER_DATA?.response?.stores?.length
 }));
 assert.equal(snapshot.data,1,'Centro Operativo debe recibir tiendas reales de API');
 assert.ok(snapshot.rows.some(x=>x.includes('Iztapalapa')&&x.includes('1,000')),'La tabla principal debe mostrar tiendas e ingresos reales');
 assert.ok(snapshot.side[0].includes('200'),'Pendientes por tienda deben provenir de API');
 assert.ok(snapshot.side[1].includes('52.7%'),'Recuperación por tienda debe usar porcentaje recuperado real');

 // Opción 3: Consultar debe ser visible, accesible y mantenerse funcional.
 await page.locator('#operPeriodApply').waitFor({state:'visible'});
 assert.notEqual(await page.locator('#operPeriodApply').getAttribute('aria-hidden'),'true');
 assert.equal(await page.locator('.v266-period-view:not(.hidden) .v266-period-buttons').isVisible(),true);
 assert.equal(await page.locator('.v266-period-btn').count(),4,'Centro must have four quick period tabs');
 assert.equal(await page.locator('#operPeriodSelect').isVisible(),true);
 assert.equal(await page.locator('#operStoreSelect').isVisible(),true);
 const formBefore=requests.length;
 await page.locator('#operPeriodApply').click();
 await page.waitForTimeout(450);
 assert.ok(requests.length>formBefore,'Consultar did not request updated center data');
 await page.locator('.ocl-lanes').waitFor();

 const screenshot=async name=>{if(process.env.ROPA_UI_OUTPUT){fs.mkdirSync(process.env.ROPA_UI_OUTPUT,{recursive:true});await page.screenshot({path:process.env.ROPA_UI_OUTPUT+'/'+name+'.png',fullPage:true});}};
 async function measure(width,height){await page.setViewportSize({width,height});await page.waitForTimeout(180);const m=await page.evaluate(()=>{const cards=[...document.querySelectorAll('.ocl-lane')].map(n=>{const r=n.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,right:r.right}});return {overflow:document.documentElement.scrollWidth-innerWidth,cards,values:[...document.querySelectorAll('.ocl-number')].map(n=>n.textContent),clipped:[...document.querySelectorAll('.ocl-shell :is(.ocl-number,.ocl-route-number,.ocl-detail-button,.ocl-label,h3)')].filter(n=>n.getBoundingClientRect().width&&n.scrollWidth>n.clientWidth+2).map(n=>n.textContent),routesY:document.querySelector('.ocl-routes').getBoundingClientRect().y,cardBottom:document.querySelector('.ocl-lane').getBoundingClientRect().bottom};});assert.equal(m.cards.length,4);assert.ok(m.overflow<=1,JSON.stringify(m));assert.ok(m.cards.every((n,i)=>Math.abs(n.y-m.cards[i<2?0:(width<=700?2:0)].y)<2),'cards must align in rows');assert.ok(m.cards[1].x>=m.cards[0].right-1);assert.deepEqual(m.values,['1,000','800','600']);assert.deepEqual(m.clipped,[],JSON.stringify(m));assert.ok(Math.abs(m.routesY-(width<=700?m.cards[2].y:m.cards[0].y))<3,'Recorridos must be the fourth summary card');await screenshot('center-'+width+'x'+height);}
 for(const [w,h]of [[320,700],[390,844],[844,390],[768,1024],[1024,768],[1366,950],[1920,1080]])await measure(w,h);
 await page.setViewportSize({width:390,height:844});
 for(const selector of ['.ocl-received','.ocl-conditioned','.ocl-located','.ocl-routes']){const button=page.locator(selector+' .ocl-detail-button');await button.click();await page.waitForTimeout(100);assert.equal(await page.locator('.ocl-drawer').isVisible(),true);assert.ok(await page.locator('.ocl-drawer tbody tr').count());await screenshot(selector.slice(1)+'-detail-mobile');await page.locator('.ocl-drawer .ocl-back').click();assert.equal(await page.locator('.ocl-drawer').isVisible(),false);}
 const modes=page.locator('#operPeriodMode');for(const mode of ['day','week','month','year']){await page.locator('.v266-period-btn[data-mode="'+mode+'"]').click();await page.waitForTimeout(600);await page.locator('.ocl-lanes').waitFor();assert.equal(await modes.inputValue(),mode);await page.locator('.ocl-conditioned button').click();await page.waitForTimeout(80);assert.match(await page.locator('.ocl-drawer').textContent(),/800/);await page.locator('.ocl-drawer .ocl-back').click();}
 const requestCount=requests.length;await page.locator('#centerLaneRefresh').click();await page.waitForTimeout(600);assert.ok(requests.length>requestCount);assert.equal(await modes.inputValue(),'year');
 await page.locator('#operStoreSelect').selectOption('Iztapalapa');await page.waitForTimeout(600);await page.locator('.ocl-located button').click();assert.match(await page.locator('.ocl-context').textContent(),/Iztapalapa/);await page.locator('.ocl-drawer .ocl-back').click();assert.equal(await page.locator('#operStoreSelect').inputValue(),'Iztapalapa');
 if(!(await page.locator('.ocl-full').evaluate(n=>n.open)))await page.locator('.ocl-full>summary').click();await screenshot('center-full-table-mobile');assert.equal(await page.locator('.monthly-cross-table').count(),1);assert.ok(await page.locator('.monthly-cross-table tbody tr').count()>10);for(const label of ['Descargar PDF','Descargar Excel']){const download=page.waitForEvent('download');await page.locator('.ocl-original button').filter({hasText:label}).click();await download;}const exports=requests.filter(x=>x.includes('export'));assert.equal(exports.length,2);for(const request of exports){const q=new URL(request,'https://app.test').searchParams;assert.equal(q.get('store'),'Iztapalapa');assert.equal(q.get('period_type'),'year');assert.equal(q.get('period_value'),'2026');}await page.locator('.ocl-full>.ocl-back').click();
 // A different report retains the presentation already on main.
 await page.locator('#operativoNav [data-opview="Conversión"]').evaluate(n=>n.click());await page.waitForTimeout(600);assert.equal(await page.locator('.ocl-shell').count(),0);await page.locator('#operativoNav [data-opview="Centro Ejecutivo"]').evaluate(n=>n.click());await page.locator('.ocl-lanes').waitFor();
 assert.deepEqual(errors,[]);console.log(JSON.stringify({status:'passed',viewports:7,periodModes:4,details:4,sourceTable:'preserved',runtimeErrors:errors}));await browser.close();fs.rmSync(out,{recursive:true,force:true});
})().catch(e=>{console.error(e);process.exit(1)});
