const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');

const py=fs.readFileSync(path.join(__dirname,'../../v313_bonus_visual_and_cut_patch.py'),'utf8');
const start=py.indexOf('js=r\x27\x27\x27<script id="v313-js">');
const tag='<script id="v313-js">';
const end=py.indexOf('</script>\x27\x27\x27',start);
if(start<0||end<0)throw Error('V313 script not found');
const code=py.slice(start+("js=r'''"+tag).length,end);
new Function(code);
const tick=()=>new Promise(resolve=>setImmediate(resolve));

function details(count=66){
  return Array.from({length:count},(_,i)=>({
    catalog:'Abrigador',id_art:String(1100000+i),model:'M'+i,
    initial_ddi:145,current_ddi:108,ddi_reduction_pct:25.5,
    initial_existence:100,current_existence:84,initial_investment:9500,current_investment:7700,
    investment_reduction_pct:19,
  }));
}
async function setup(opts={}){
  const data={
    month:'2026-10',months:[{value:'2026-10',label:'Octubre 2026'}],stores:['Olivar'],
    selected_store:'Olivar',details:opts.data||details(),ranking:[],summary:{},
    source_dates:{opening_capacity:'2026-09-29',current_capacity:'2026-10-13'},
    processing:{capacity:false,sales:false},selected:{formula:'Bono 1 vigente'},
  };
  let exportMode=opts.mode||'error', navigations=0, downloaded=0,reportRequests=0;
  const dom=new JSDOM('<div id="sidebar"><button data-main="bonuses">Bonos</button></div><main class="main"><section class="page" id="page-bonuses"></section></main>',{
    url:'https://operaciones.example/',runScripts:'outside-only'
  });
  const w=dom.window;
  w.fetch=async (url,requestOpt)=>{
    if(String(url).startsWith("/api/bonuses-v330") && opts.bonusResponse)return opts.bonusResponse(url,requestOpt);
    if(String(url).startsWith('/api/bonuses-v313')){reportRequests++;return {ok:true,json:async()=>data};}
    if(String(url).startsWith('/api/bonuses-b2-v340'))return {ok:true,json:async()=>({
      ...data,b2_subcategories:true,b2_status:'ready',subcategories:['Chamarra','Sudadera','Jeans'],
      legacy_components:{sales_pct:100,ddi_pct:100,attendance_pct:100,legacy_score_avg:100},
      details:[{catalog:'Jeans',id_art:'10001',model:'P1',initial_ddi:200,current_ddi:50,fixed_ddi:150,
        initial_sug7:1,current_sug7:3,initial_existence:200,current_existence:150,initial_investment:12000,
        current_investment:10000,ddi_reduction_pct:25,comparison_status:'Comparable'}],
      bonus2_rows:[{store:'Olivar',score:100,score_ready:true,display_order:1,ddi_pct:100,sales_pct:100,attendance_pct:100,catalogs:[]}]
    })};
    if(String(url).startsWith('/api/bonuses/models-export')){
      if(exportMode==='error')return {ok:false,status:404,text:async()=>JSON.stringify({detail:'No hay modelos para exportar en este catálogo y periodo'})};
      return {ok:true,headers:{get:key=>key.toLowerCase()==='content-disposition'?'attachment; filename="Bonos_Olivar_Abrigador_2026-10.xlsx"':null},blob:async()=>new w.Blob(['fake xlsx'],{type:'application/octet-stream'})};
    }
    return {ok:true,json:async()=>({})};
  };
  w.scrollTo=()=>{};
  w.URL.createObjectURL=()=> 'blob:fake';
  w.URL.revokeObjectURL=()=>{};
  w.document.addEventListener('click',e=>{
    if(e.target.tagName==='A'&&e.target.download){
      downloaded++;e.preventDefault();
    }
  },true);
  w.eval(code);
  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  await new Promise(r=>setTimeout(r,900));
  w.document.querySelector('#sidebar [data-main="bonuses"]').click();
  await tick();await tick();await tick();
  const tab=w.document.querySelector('[data-v313-section="models"]');
  assert.ok(tab,'models tab');
  tab.click();await tick();
  assert.equal(w.document.querySelector('.v313-model-table'),null,'models are deferred in summary');
  w.document.querySelector('#compactBonusToggle').click();await tick();
  return {w,dom,data,get reportRequests(){return reportRequests},setMode:m=>{exportMode=m},get downloads(){return downloaded},get navigations(){return navigations}};
}

test('Excel 404 is shown inside Bonos without navigating to JSON error screen',async()=>{
  const f=await setup();try{
    assert.equal(f.w.document.querySelectorAll('.v313-model-table tbody tr').length,30);
    assert.match(f.w.document.querySelector('.v313-model-pagination').textContent,/1 de 3/);
    const before=f.w.location.href;
    f.w.document.querySelector('[data-v313-download="xlsx"]').click();
    await tick();await tick();await tick();
    assert.equal(f.w.location.href,before);
    const notice=f.w.document.querySelector('#v313ExportNotice');
    assert.ok(notice.textContent.includes('No hay modelos'));
    assert.equal(notice.hidden,false);
    assert.ok(f.w.document.querySelector('.v313-model-scroll'),'models table retained');
    assert.ok(f.w.document.querySelector('[data-v313-return]'),'back button retained');
  }finally{f.dom.window.close();}
});

test('Excel success creates file download while keeping the same report and store',async()=>{
  const f=await setup({mode:'success'});try{
    f.w.document.querySelector('[data-v313-download="xlsx"]').click();
    await tick();await tick();await tick();
    assert.equal(f.downloads,1);
    assert.equal(f.w.document.querySelector('#v313Store').value,'Olivar');
    assert.ok(f.w.document.querySelector('.v313-model-scroll'));
    assert.match(f.w.document.querySelector('#v313ExportNotice').textContent,/Descarga preparada/);
  }finally{f.dom.window.close();}
});

test('model table scroll arrows and return button preserve navigation',async()=>{
  const f=await setup();try{
    let viewport=f.w.document.querySelector('.v313-model-scroll');
    viewport.scrollBy=function({top}){this.scrollTop+=top;this.dispatchEvent(new f.w.Event('scroll'))};
    f.w.document.querySelector('[data-v313-scroll-down]').click();
    assert.equal(viewport.scrollTop,1290);
    f.w.document.querySelector('[data-v313-cat="Licencias"]').click();
    f.w.document.querySelector('[data-v313-cat="Abrigador"]').click();
    viewport=f.w.document.querySelector('.v313-model-scroll');
    assert.equal(viewport.scrollTop,1290);
    f.w.document.querySelector('[data-v313-return]').click();
    assert.equal(f.w.document.querySelector('[data-v313-section="summary"]').classList.contains('active'),true);
  }finally{f.dom.window.close();}
});

test('Bono 2 shares the Bono 1 four-tab design and lists subcategories and comparable inventory',async()=>{
  const f=await setup();try{
    f.w.document.querySelector('[data-v313-bonus="2"]').click();
    await tick();await tick();
    const tabs=Array.from(f.w.document.querySelectorAll('[data-v313-section]')).map(x=>x.dataset.v313Section);
    assert.deepEqual(tabs,['summary','ranking','panorama','models']);
    assert.match(f.w.document.querySelector('#v313Host').textContent,/DDI por subcategoría/);
    f.w.document.querySelector('[data-v313-section="models"]').click();
    await tick();
    f.w.document.querySelector('#compactBonusToggle').click();await tick();
    f.w.document.querySelector('[data-v313-cat="Jeans"]').click();
    await tick();
    const list=f.w.document.querySelector('.v313-model-table');
    assert.equal(list.querySelectorAll('tbody tr').length,1);
    assert.match(list.textContent,/Inventario inicial/);
    assert.match(list.textContent,/SUG 7/);
    assert.match(list.textContent,/150/);
    assert.match(list.textContent,/DDI inicial/);
    assert.match(list.textContent,/No disponibles/);
    assert.equal(f.w.document.querySelector('[data-v313-cat="Abrigador"]'),null);
    assert.ok(f.w.document.querySelector('[data-v313-return]'));
    assert.ok(f.w.document.querySelector('[data-v313-download="xlsx"]'));
    f.w.document.querySelector('[data-v313-bonus="1"]').click();await tick();await tick();
    f.w.document.querySelector('[data-v313-section="models"]').click();await tick();
    const toggle=f.w.document.querySelector('#compactBonusToggle');if(toggle.getAttribute('aria-expanded')==='false')toggle.click();await tick();
    assert.ok(f.w.document.querySelector('[data-v313-cat="Abrigador"].active'));
    assert.equal(f.w.document.querySelectorAll('.v313-model-table tbody tr').length,30);
  }finally{f.dom.window.close();}
});


test('bonus tabs respond immediately and stale server responses cannot overwrite selected tab',async()=>{
  const waiting=new Map();
  const f=await setup({bonusResponse:(url,opts)=>new Promise(resolve=>{
    const b=new URL(url,'https://operaciones.example').searchParams.get('bonus');
    waiting.set(b,{resolve,signal:opts?.signal});
  })});
  try{
    f.w.document.querySelector('[data-v313-bonus="3"]').click();
    assert.ok(f.w.document.querySelector('[data-v313-bonus="3"].active'));
    assert.match(f.w.document.querySelector('#v313Host').textContent,/Consultando indicadores reales del Bono 3/);
    f.w.document.querySelector('[data-v313-bonus="6"]').click();
    assert.ok(f.w.document.querySelector('[data-v313-bonus="6"].active'));
    assert.equal(waiting.get("3").signal.aborted,true);
    const createPayload=b=>({
      is_v330:true,bonus_no:b,
      month:'2026-10',months:[{value:'2026-10',label:'Octubre 2026'}],
      stores:['Compañía','Olivar'],selected_store:'Compañía',
      processing:{capacity:false,sales:false},
      source_dates:{opening_capacity:'2026-10-01',current_capacity:'2026-10-13'},
      model:{name:b===6?'Resultado colectivo por tienda':'Puntos ponderados',design:b===6?'6.1':'3.2',cut_comparable:true},
      summary:{sales_pct:98,attendance_reference:95,ddi_models_pct:33,ddi_models:9,ddi_improved_models:3,inventory:{}},
      selected:null,ranking:[]
    });
    waiting.get("6").resolve({ok:true,json:async()=>createPayload(6)});
    await tick();await tick();
    assert.match(f.w.document.querySelector('#v313Host').textContent,/Resultado colectivo por tienda/);
    waiting.get("3").resolve({ok:true,json:async()=>createPayload(3)});
    await tick();await tick();
    assert.ok(f.w.document.querySelector('[data-v313-bonus="6"].active'));
    assert.doesNotMatch(f.w.document.querySelector('.v313-hero').textContent,/Puntos ponderados/);
    f.w.document.querySelector('[data-v313-bonus="5"]').click();
    assert.ok(f.w.document.querySelector('[data-v313-bonus="5"].active'));
    assert.match(f.w.document.querySelector('.v313-hero').textContent,/Multiplicador por DDI/);
  }finally{f.dom.window.close();}
});


test('157 models remain accessible using pagination when browser scroll is intercepted',async()=>{
 const f=await setup({data:details(157)});
 try {
   let table=f.w.document.querySelector('.v313-model-table');
   assert.equal(table.querySelectorAll('tbody tr').length,30);
   assert.match(table.textContent,/M0/);
   assert.ok(f.w.document.querySelector('.v313-model-scroll'));
   f.w.document.querySelector('[data-v313-page="next"]').click();
   table=f.w.document.querySelector('.v313-model-table');
   assert.equal(table.querySelectorAll('tbody tr').length,30);
   assert.equal(table.querySelectorAll('tbody tr')[0].textContent.includes('M30'),true);
   assert.match(f.w.document.querySelector('.v313-model-pagination').textContent,/2 de 6/);
   for(let n=0;n<4;n++)f.w.document.querySelector('[data-v313-page="next"]').click();
   table=f.w.document.querySelector('.v313-model-table');
   assert.equal(table.querySelectorAll('tbody tr').length,7);
   assert.match(table.textContent,/M156/);
   f.w.document.querySelector('[data-v313-page="prev"]').click();
   assert.equal(f.w.document.querySelector('.v313-model-table tbody tr').textContent.includes('M120'),true);
 }finally{f.dom.window.close()}
});

test('mouse wheel movement is consumed by model list and not the surrounding report',async()=>{
 const f=await setup();
 try{
   const scroll=f.w.document.querySelector('.v313-model-scroll');
   Object.defineProperty(scroll,'scrollHeight',{configurable:true,value:2000});
   Object.defineProperty(scroll,'clientHeight',{configurable:true,value:350});
   const wheel=new f.w.WheelEvent('wheel',{deltaY:200,bubbles:true,cancelable:true});
   scroll.dispatchEvent(wheel);
   assert.equal(wheel.defaultPrevented,true);
   assert.equal(scroll.scrollTop,200);
 }finally{f.dom.window.close()}
});

test('a missing photo can be retried using exactly the same model ID',async()=>{
 const f=await setup();
 try{
  const photo=f.w.document.querySelector('.v313-model-table tbody tr .v313-photo');
  const missing=f.w.document.querySelector('[data-v313-retry-photo]');
  assert.ok(photo&&missing);
  const id=missing.dataset.v313RetryPhoto;
  assert.equal(id,'1100000');
  missing.style.display='inline';
  missing.click();
  assert.equal(photo.style.display,'block');
  assert.equal(missing.style.display,'none');
  assert.ok(photo.getAttribute('src').startsWith('/api/bonuses/product-photo/'+id+'?retry=1&t='));
  assert.ok(f.w.document.querySelector('[data-v313-retry-visible]'));
 }finally{f.dom.window.close()}
});

test('all six bonuses expose summary/detail and retain numerical values on return',async()=>{
 const f=await setup({bonusResponse:async url=>({ok:true,json:async()=>({
   is_v330:true,bonus_no:Number(new URL(url,'https://test').searchParams.get('bonus')),
   month:'2026-10',months:[{value:'2026-10',label:'Octubre 2026'}],stores:['Olivar'],selected_store:'Olivar',
   model:{name:'Seguimiento',design:'Prueba',cut_comparable:true},
   summary:{sales_pct:98,attendance_reference:95,ddi_models_pct:33,ddi_models:9,ddi_improved_models:3,inventory:{}},
   selected:null,ranking:[],details:[],source_dates:{},processing:{}
 })})});
 try{
  for(let n=1;n<=6;n++){
   f.w.document.querySelector(`[data-v313-bonus="${n}"]`).click();await tick();await tick();
   const before=f.w.document.querySelector('.v313-kpis').textContent;
   const toggle=f.w.document.querySelector('#compactBonusToggle');assert.equal(toggle.getAttribute('aria-expanded'),'false');
   toggle.click();assert.equal(f.w.document.querySelector('#compactBonusToggle').getAttribute('aria-expanded'),'true');
   f.w.document.querySelector('#compactBonusToggle').click();
   assert.equal(f.w.document.querySelector('.v313-kpis').textContent,before);
   assert.equal(f.w.document.querySelector('#v313Store').value,'Olivar');
  }
 }finally{f.dom.window.close()}
});

test('Bono 1 shows original components, partial scores and missing sources, and Actualizar reloads data',async()=>{
 const f=await setup();try{
  f.data.legacy_components={sales_pct:41.7,ddi_pct:null,attendance_pct:100,attendance_provisional_stores:1,stores_with_score:0};
  f.data.bonus1_rows=[{store:'Olivar',display_order:1,sales_pct:41.7,ddi_pct:null,attendance_pct:100,attendance_provisional:true,score:40.9,score_ready:false,missing_sources:['Preparando DDI de Capacidades','Asistencia provisional: pendiente de captura']}];
  f.w.OperacionesPWA={checkForUpdates:async()=>({available:false})};
  f.w.document.querySelector('[data-v313-section="summary"]').click();await tick();
  const before=f.reportRequests;
  f.w.document.querySelector('#v313UpdateBtn').click();await tick();await tick();
  assert.ok(f.reportRequests>before,'Actualizar must fetch current report data');
  const rank=f.w.document.querySelector('[data-compact-panel="ranking"]');
  if(rank.getAttribute('aria-expanded')==='false')rank.click();
  let body=f.w.document.querySelector('.v313-table').textContent;
  assert.match(body,/DDI por catálogo/);assert.match(body,/40.9%/);assert.match(body,/Parcial/);assert.match(body,/pendiente de captura/);assert.match(body,/1\*/);
  f.data.legacy_components.ddi_pct=73.2;f.data.bonus1_rows[0].ddi_pct=73.2;
  f.w.document.querySelector('#v313UpdateBtn').click();await tick();await tick();
  assert.match(f.w.document.querySelector('.compact-summary-band').textContent,/73.2%/);
  assert.equal(f.w.document.querySelector('#v313Store').value,'Olivar');
 }finally{f.dom.window.close()}
});

test('capacity polling continues beyond sixty attempts and stops when the source is ready',async()=>{
 const f=await setup();try{
  const jobs=[],original=f.w.setTimeout.bind(f.w);
  f.w.setTimeout=(fn,ms,...args)=>{if([1800,3000,10000].includes(ms)){jobs.push(()=>fn(...args));return 9876;}return original(fn,ms,...args)};
  f.w.OperacionesPWA={checkForUpdates:async()=>({available:false})};
  f.data.processing.capacity=true;
  f.w.document.querySelector('#v313UpdateBtn').click();await tick();await tick();
  for(let i=0;i<65;i++){
   assert.equal(jobs.length,1,'source must keep refreshing at attempt '+i);
   jobs.shift()();await tick();await tick();
  }
  f.data.processing.capacity=false;
  jobs.shift()();await tick();await tick();
  assert.equal(jobs.length,0);
  assert.equal(f.w.document.querySelector('#v313Store').value,'Olivar');
 }finally{f.dom.window.close()}
});

test('Bono 1 restores the existing attendance form only for authorized store views',async()=>{
 const f=await setup();try{
  f.data.can_edit_attendance=true;f.data.legacy_components={attendance_pct:100,attendance_provisional_stores:1};
  f.w.OperacionesPWA={checkForUpdates:async()=>({available:false})};
  f.w.document.querySelector('[data-v313-section="summary"]').click();await tick();
  f.w.document.querySelector('#v313UpdateBtn').click();await tick();await tick();
  let toggle=f.w.document.querySelector('#compactBonusToggle');if(toggle.getAttribute('aria-expanded')==='false')toggle.click();
  let form=f.w.document.querySelector('#v313AttendanceForm');assert.ok(form);
  assert.equal(f.w.document.querySelector('#v313AttendancePct').value,'','provisional 100% must require explicit input');
  const oldFetch=f.w.fetch;let saved;
  f.w.fetch=async(url,opt)=>{if(String(url).endsWith('/attendance')){saved=JSON.parse(opt.body);return {ok:true,json:async()=>({ok:true})}}return oldFetch(url,opt)};
  form.dispatchEvent(new f.w.Event('submit',{cancelable:true,bubbles:true}));await tick();assert.equal(saved,undefined);
  f.w.document.querySelector('#v313AttendancePct').value='95';form.dispatchEvent(new f.w.Event('submit',{cancelable:true,bubbles:true}));await tick();await tick();
  assert.deepEqual(saved,{month:'2026-10',store:'Olivar',attendance_pct:95});
  f.data.can_edit_attendance=false;f.w.document.querySelector('#v313UpdateBtn').click();await tick();await tick();
  assert.equal(f.w.document.querySelector('#v313AttendanceForm'),null);
 }finally{f.dom.window.close()}
});

test('a late bonus refresh cannot reopen Bonos after leaving the module',async()=>{
 let release;const f=await setup({bonusResponse:()=>new Promise(resolve=>{release=resolve})});
 try{
  f.w.document.querySelector('[data-v313-bonus="3"]').click();await tick();assert.ok(release);
  const other=f.w.document.createElement('button');other.dataset.main='operativo';f.w.document.body.append(other);other.click();
  f.w.document.querySelector('#page-bonuses').classList.remove('active');
  release({ok:true,json:async()=>({is_v330:true,bonus_no:3,month:'2026-10',selected_store:'Olivar',model:{name:'Bono 3'},summary:{},ranking:[],details:[],processing:{}})});await tick();await tick();
  assert.equal(f.w.document.querySelector('#page-bonuses').classList.contains('active'),false);
  assert.equal(f.w.document.body.hasAttribute('data-v313'),false);
 }finally{f.dom.window.close()}
});
