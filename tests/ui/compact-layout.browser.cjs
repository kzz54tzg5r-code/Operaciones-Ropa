// Full served-page browser QA with isolated fixture data; no production login or writes.
const fs=require('fs'),path=require('path'),Module=require('module');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const assert=require('node:assert/strict'),os=require('os'),{spawnSync}=require('child_process');
const root=path.resolve(__dirname,'../..');
const output=fs.mkdtempSync(path.join(os.tmpdir(),'ropa-layout-'));
const generated=spawnSync(process.env.PYTHON||'python3',[root+'/tests/ui/render_production_page.py',output],{cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},encoding:'utf8',timeout:60000});
assert.equal(generated.status,0,generated.stderr);
const snap=async(page,name)=>{if(process.env.ROPA_UI_OUTPUT){fs.mkdirSync(process.env.ROPA_UI_OUTPUT,{recursive:true});await page.screenshot({path:path.join(process.env.ROPA_UI_OUTPUT,name+'.png'),fullPage:true});}};
const file=root+'/tests/ui/runtime-fixture.cjs',mod=new Module(file,module);mod.filename=file;mod.paths=Module._nodeModulePaths(path.dirname(file));mod._compile(fs.readFileSync(file,'utf8')+'\nmodule.exports.fixture=fixture;module.exports.report=report;',file);
const {fixture,report}=mod.exports;
const mt={...report.metrics,dev_pzs:1257,muertos:488,probador:0,cajas:439,recolectadas:2184,ingresos:5156,total_pzs:5156,acondicionado:1246,ubicado:550,recorridos:5,meta_recorridos:282,pct_acondicionado:24.2,pct_ubicado:10.7,pct_recorridos:1.8,pendiente_acondicionar:3910,pendiente_ubicar:696,conversion_pct:42,converted_pieces:528,recovery_pct:42,recovered_value:42000,return_value:100000,productivity_daily:720,productivity_pct:92};
const ops={...report,metrics:mt,goals:{conversion:80},stores:[{...report.stores[0],...mt}],recovery_by_store:[{store:'Iztapalapa',dev_pzs:1257,converted_pieces:528,conversion_pct:42,recovered_value:42000,return_value:100000,recovery_pct:42}],daily_peaks:[{date:'2026-10-01',recorridos:5}],productivity:[{name:'Colaborador A',store:'Iztapalapa',pieces:720,days:1,daily:720,target:784,pct:92,missing:64}]};
function bonus(q){const n=Number(q.get('bonus')||1);return {bonus_no:n,is_v330:n>=3,month:'2026-10',months:[{value:'2026-10',label:'Octubre 2026'}],stores:['Compañía','Iztapalapa'],selected_store:q.get('store')||'Compañía',details:Array.from({length:31},(_,i)=>({id_art:String(1100000+i),model:'Modelo '+i,catalog:'Abrigador',initial_ddi:140,current_ddi:105,ddi_reduction_pct:25,initial_existence:100,current_existence:70,initial_investment:9000,current_investment:6000})),ranking:[{rank:1,store:'Iztapalapa',sales_pct:98,eligible:true,ready:true,classification:'En avance',indicator:'33%'}],summary:{sales_pct:98,attendance_reference:98,stores_total:17,stores_enabled:12,ddi_models_pct:33,ddi_models:120,ddi_improved_models:40,inventory:{ddi_reduction_pct:33,initial_ddi:140,current_ddi:105,initial_investment:90000,current_investment:60000}},legacy_components:{sales_pct:98,ddi_pct:70,attendance_pct:98,legacy_score_avg:88,stores_with_score:17},source_dates:{opening_capacity:'2026-10-01',current_capacity:'2026-10-12'},processing:{capacity:false,sales:false},selected:{formula:'Criterios vigentes'},model:{name:'Indicadores vigentes',design:'Criterios vigentes',cut_comparable:true}};}
(async()=>{
 const b=await chromium.launch({executablePath:process.env.ROPA_CHROMIUM_PATH||undefined,args:['--no-sandbox','--disable-dev-shm-usage','--single-process','--no-zygote','--in-process-gpu','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'],headless:true});
 const page=await b.newPage({viewport:{width:1366,height:950}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{const u=new URL(route.request().url());if(u.pathname==='/'){await route.fulfill({contentType:'text/html',body:fs.readFileSync(output+'/page.html','utf8')});return;}
 if(u.pathname.startsWith('/static/')){const f=output+'/web/'+u.pathname.slice(8);if(fs.existsSync(f)){await route.fulfill({path:f});return;}}
 if(u.pathname.startsWith('/api/')){let d=fixture(u.pathname,u.searchParams);if(u.pathname==='/api/operations')d=ops;if(/bonuses-v313|bonuses-v330|bonuses-b2/.test(u.pathname))d=bonus(u.searchParams);if(u.pathname==='/api/operations/routes-calendar-v240')d={period_type:'week',columns:[{label:'Lun'}],rows:[{store:'Iztapalapa',cells:[5],total:5}],totals:[5],grand_total:5};if(u.pathname==='/api/goals')d={values:{productividad_diaria:784,recorridos_semanales:47},labels:{productividad_diaria:'Productividad diaria',recorridos_semanales:'Recorridos semanales'},editable:true,history:[]};if(u.pathname==='/api/stores')d={stores:[{id:1,name:'Iztapalapa',active:true,project:true}],editable:true,history:[]};await route.fulfill({json:d});return;}await route.fulfill({status:204,body:''});});
 await page.goto('https://app.test/');await page.waitForTimeout(1800);await page.evaluate(async()=>{await enter({id:1,username:'Prueba',role:'admin',store:'',can_preview_roles:false})});await page.waitForTimeout(1800);
 const metrics=async()=>page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,headers:[...document.querySelectorAll('#operativoDynamicContent .compact-monthly-sections>.compact-section>summary')].filter(el=>el.getBoundingClientRect().width).map(el=>el.getBoundingClientRect().height),cards:[...document.querySelectorAll('.page.active .compact-summary-band')].map(b=>[...b.children].filter(el=>el.getBoundingClientRect().width).length),nav:[...document.querySelectorAll('#operativoNav>[data-opview]')].filter(el=>el.getBoundingClientRect().width).map(el=>({x:el.getBoundingClientRect().x,w:el.getBoundingClientRect().width})),filters:['operPeriodMode','operPeriodSelect','operStoreSelect'].map(id=>{const el=document.getElementById(id);return el?el.getBoundingClientRect().width:0})}));
 const measure=async name=>{const m=await metrics();assert.ok(m.overflow<=1,name+' causes page overflow: '+m.overflow);m.cards.forEach(n=>assert.ok(n<=2,name+' shows more than two primary cards'));return m;};
 for(const width of [320,390,768,1366,1920]){
  await page.setViewportSize({width,height:950});await page.waitForTimeout(250);
  const m=await measure('width '+width);assert.ok(m.headers.every(h=>h<=100),'overlarge summary header at '+width);
  assert.ok(m.filters.every(w=>w>70),'hidden or cramped period/store filter at '+width);
  for(let i=1;i<m.nav.length;i++)assert.ok(m.nav[i].x>=m.nav[i-1].x+m.nav[i-1].w-1,'overlapping tabs at '+width);
  await snap(page,'center-'+width);
 }
 await page.setViewportSize({width:390,height:844});
 const section=page.locator('#operativoDynamicContent [data-section="progress"]');
 if(await section.count()){
  const filter=await page.locator('#operStoreSelect').inputValue();
  await section.locator('summary').click();assert.ok(await section.evaluate(el=>el.open));
  await measure('open progress');await snap(page,'progress-mobile');
  await section.locator('.compact-section-back').click();assert.equal(await section.evaluate(el=>el.open),false);
  assert.equal(await page.locator('#operStoreSelect').inputValue(),filter);
 }

 const views=await page.locator('#operativoNav>[data-opview]').evaluateAll(els=>els.filter(el=>el.getBoundingClientRect().width).map(el=>el.dataset.opview));
 for(const name of views){
  await page.locator('#operativoNav>[data-opview]').evaluateAll((els,name)=>els.find(el=>el.dataset.opview===name)?.click(),name);
  await page.waitForTimeout(400);await measure(name);
 }
 await page.setViewportSize({width:1366,height:950});
 const nav=page.locator('[data-main="bonuses"]').first();
 if(await nav.count()){
  await nav.evaluate(el=>el.click());await page.waitForTimeout(800);
  for(let n=1;n<=6;n++){
   await page.locator('[data-v313-bonus="'+n+'"]').click();await page.waitForTimeout(300);await measure('Bono '+n);
   const toggle=page.locator('#compactBonusToggle');assert.ok(await toggle.count(),'missing bonus summary');
   await toggle.click();await page.waitForTimeout(100);assert.equal(await page.locator('#compactBonusToggle').getAttribute('aria-expanded'),'true');
   await page.locator('[data-compact-close]').click();await page.waitForTimeout(100);assert.equal(await page.locator('#compactBonusToggle').getAttribute('aria-expanded'),'false');
   await snap(page,'bonus-'+n);
  }
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);await measure('bonus mobile');await snap(page,'bonus-mobile');
 }
 assert.deepEqual(errors,[],'browser runtime errors');
 console.log(JSON.stringify({viewports:[320,390,768,1366,1920],tabs:views,bonuses:6,runtimeErrors:errors.length,status:'passed'}));
 await b.close();fs.rmSync(output,{recursive:true,force:true});

})().catch(e=>{console.error(e);process.exit(1)});
