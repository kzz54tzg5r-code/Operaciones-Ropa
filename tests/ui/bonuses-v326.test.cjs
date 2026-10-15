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
  let exportMode=opts.mode||'error', navigations=0, downloaded=0;
  const dom=new JSDOM('<div id="sidebar"><button data-main="bonuses">Bonos</button></div><main class="main"><section class="page" id="page-bonuses"></section></main>',{
    url:'https://operaciones.example/',runScripts:'outside-only'
  });
  const w=dom.window;
  w.fetch=async url=>{
    if(String(url).startsWith('/api/bonuses-v313'))return {ok:true,json:async()=>data};
    if(String(url).startsWith('/api/bonuses-b2-v327'))return {ok:true,json:async()=>({
      ...data,b2_cohort:true,b2_status:'ready',source_error:'',cutoff_date:'2026-10-13',
      details:[{
        catalog:'Licencias',id_art:'10001',model:'P1',sales_30:0,
        last_arrival:'2026-10-05',arrival_age_days:8,initial_ddi:135,
        initial_existence:25,initial_investment:12000
      }],b2_stats:{models:1,sales_30:0,avg_ddi:135,existence:25,investment:12000,
         catalog_counts:{Abrigador:0,Licencias:1,'Básicos':0}},
      selected:{formula:'0 ventas últimos 30 días; última entrada >=7 días; catálogo vigente'},
      ranking:[{store:'Olivar',models:1,avg_ddi:135,investment:12000,classification:'En seguimiento',rank:1}]
    })};
    if(String(url).startsWith('/api/bonuses/models-export')){
      if(exportMode==='error')return {ok:false,status:404,text:async()=>JSON.stringify({detail:'No hay modelos para exportar en este catálogo y periodo'})};
      return {ok:true,headers:{get:key=>key.toLowerCase()==='content-disposition'?'attachment; filename="Bonos_Olivar_Abrigador_2026-10.xlsx"':null},blob:async()=>new w.Blob(['fake xlsx'],{type:'application/octet-stream'})};
    }
    return {ok:true,json:async()=>({})};
  };
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
  return {w,dom,data,setMode:m=>{exportMode=m},get downloads(){return downloaded},get navigations(){return navigations}};
}

test('Excel 404 is shown inside Bonos without navigating to JSON error screen',async()=>{
  const f=await setup();try{
    assert.equal(f.w.document.querySelectorAll('.v313-model-table tbody tr').length,66);
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

test('Bono 2 shares the Bono 1 four-tab design and lists zero-sales recent-arrival models',async()=>{
  const f=await setup();try{
    f.w.document.querySelector('[data-v313-bonus="2"]').click();
    await tick();await tick();
    const tabs=Array.from(f.w.document.querySelectorAll('[data-v313-section]')).map(x=>x.dataset.v313Section);
    assert.deepEqual(tabs,['summary','ranking','panorama','models']);
    assert.match(f.w.document.querySelector('#v313Host').textContent,/Venta últimos 30 días/);
    f.w.document.querySelector('[data-v313-section="models"]').click();
    await tick();
    f.w.document.querySelector('[data-v313-cat="Licencias"]').click();
    await tick();
    const list=f.w.document.querySelector('.v313-model-table');
    assert.equal(list.querySelectorAll('tbody tr').length,1);
    assert.match(list.textContent,/Venta pzas 30/);
    assert.match(list.textContent,/05\/10\/2026/);
    assert.match(list.textContent,/135/);
    assert.match(list.textContent,/DDI inicial/);
    assert.match(f.w.document.querySelector('#v313Host').textContent,/hace 7 días o más/i);
    assert.ok(f.w.document.querySelector('[data-v313-return]'));
    assert.ok(f.w.document.querySelector('[data-v313-download="xlsx"]'));
  }finally{f.dom.window.close();}
});
