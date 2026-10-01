const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const {test,after}=require('node:test');
const {createRuntime}=require('./runtime-fixture.cjs');
const root=path.resolve(__dirname,'../..');
const output=fs.mkdtempSync(path.join(os.tmpdir(),'ropa-ui-'));
const generated=spawnSync(process.env.PYTHON||'python3',[path.join(__dirname,'render_production_page.py'),output],{
  cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},encoding:'utf8',timeout:60000
});
assert.equal(generated.status,0,generated.stdout+'\n'+generated.stderr);
const html=fs.readFileSync(path.join(output,'page.html'),'utf8');
after(()=>fs.rmSync(output,{recursive:true,force:true}));
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

// Raw index.html alone misses the scripts added by the production installers.
test('all scripts in the served production page parse',()=>{
  let count=0;
  for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){
    if(/\bsrc\s*=/.test(match[1]))continue;
    assert.doesNotThrow(()=>new vm.Script(match[2],{filename:match[1]||'base script'}));count++;
  }
  assert.ok(count>40,'production middleware scripts must be included');
});

test('daily percentage cards settle without triggering their observer forever',async()=>{
  const script=html.match(/<script id="v111-daily-percent-final-js">([\s\S]*?)<\/script>/)[1];
  const card=(label,value,sub)=>`<div class="report-kpi"><span class="rk-label">${label}</span><b class="rk-value">${value}</b><small class="rk-sub">${sub}</small></div>`;
  const runtime=createRuntime(`<script>var OP_VIEW='Operación Diaria';</script><div id="operativoDynamicContent">${card('Acondicionado','755','42.6%')}${card('Ubicado','1679','94.6%')}</div><script>${script}</script>`,path.join(output,'web'));
  const {window:w}=runtime;
  let mutations=0;
  const observer=new w.MutationObserver(()=>mutations++);
  observer.observe(w.document.getElementById('operativoDynamicContent'),{subtree:true,childList:true,attributes:true});
  try{
    await wait(100);
    assert.deepEqual([...w.document.querySelectorAll('.rk-value')].map(x=>x.textContent),['42.6%','94.6%']);
    assert.deepEqual([...w.document.querySelectorAll('.rk-sub')].map(x=>x.textContent),['755 piezas acondicionadas','1679 piezas ubicadas']);
    const settled=mutations;
    assert.ok(settled>0);
    await wait(150);
    assert.equal(mutations,settled,'percentage cards must stop generating DOM mutations');
    assert.deepEqual(runtime.errors,[]);
  }finally{observer.disconnect();runtime.close()}
});

test('navigation decoration settles after its own observed class changes',async()=>{
  const script=html.match(/<script id="v207-contextual-report-headers-js">([\s\S]*?)<\/script>/)[1];
  const runtime=createRuntime(`<body data-v163-module="operativo"><nav id="operativoNav"><button class="active" data-opview="Reporte Mensual">Reporte Mensual</button></nav><script>${script}</script></body>`,path.join(output,'web'));
  const {window:w}=runtime;
  let mutations=0;
  const observer=new w.MutationObserver(()=>mutations++);
  observer.observe(w.document.body,{subtree:true,childList:true,attributes:true});
  try{
    await wait(200);
    assert.match(w.document.getElementById('v207Context-cm').textContent,/Mensual/i);
    const settled=mutations;
    await wait(200);
    assert.equal(mutations,settled,'navigation observers must become idle');
    assert.deepEqual(runtime.errors,[]);
  }finally{observer.disconnect();runtime.close()}
});

test('reports load after repeated initialization, tab changes and filters',{timeout:90000},async t=>{
  const runtime=createRuntime(html,path.join(output,'web'));
  const {window:w,errors,requests}=runtime,d=w.document;
  const content=()=>d.getElementById('operativoDynamicContent').textContent;
  const click=async selector=>{const button=d.querySelector(selector);assert.ok(button,selector);button.click();await wait(350);t.diagnostic('Opened '+selector)};
  try{
    await new Promise(resolve=>w.addEventListener('load',resolve,{once:true}));
    await wait(2700); // Includes all delayed V199/V200 setup calls.
    await w.enter({id:1,username:'Test Admin',role:'admin',store:'',can_preview_roles:false});
    await wait(300);
    assert.match(content(),/Detalle operativo/);
    assert.ok(requests.some(x=>x.path==='/api/operations'));

    // A later layer wraps V200; repeating setup must preserve that chain.
    const previous=w.renderOperativoView;
    let laterCalls=0;
    const later=async function(){laterCalls++;return previous.apply(this,arguments)};
    w.renderOperativoView=later;
    d.dispatchEvent(new w.CustomEvent('report-tabs-visibility-changed'));
    w.dispatchEvent(new w.Event('pageshow'));
    await wait(250);

    await click('.side [data-main="analysis"]');
    assert.equal(d.getElementById('kExist').textContent,'12,345');
    assert.equal(d.querySelector('.page.active').id,'page-macro');
    // V198 deliberately removes the legacy comparison. Loading must still finish.
    assert.equal(d.getElementById('macroRankingTitle'),null);
    assert.equal(d.getElementById('bars'),null);
    assert.ok(d.getElementById('v213AnalysisFilterCard'));

    await click('.side [data-main="operation"]');
    assert.match(content(),/Llegada Origen/);
    assert.ok(laterCalls>0,"later render layers remain callable after reinitialization");
    for(const key of ['daily','capture','productivity','standards','summary']){
      await click('[data-v200-op="'+key+'"]');
      assert.doesNotMatch(content(),/Maximum call stack|No fue posible|Calculando ranking/);
    }
    await click('.side [data-main="operativo"]');
    for(const name of ['Operación Diaria','Reporte Semanal','Reporte Mensual','Conversión','Recuperación por Tienda','Carga de datos']){
      await click('#operativoNav [data-opview="'+name+'"]');
      assert.doesNotMatch(content(),/Maximum call stack|No fue posible|Error al abrir/);
    }
    assert.ok(d.getElementById('opsModuleUploadBtn'));
    await click('.side [data-main="analysis"]');
    for(const key of ['stores','sections','areas','accordion','sellthrough','more']){
      await click('#analysisNav [data-sub="'+key+'"]');
      assert.equal(d.querySelector('.page.active').id,'page-'+key);
    }
    await click('#analysisNav [data-sub="macro"]');
    const section=d.getElementById('v213AnalysisSection');
    assert.ok(section);
    section.value='Dama';section.dispatchEvent(new w.Event('change',{bubbles:true}));
    await wait(150);
    await click('#v213AnalysisApply');
    assert.ok(requests.some(x=>x.path==='/api/dashboard' && x.query.get('section')==='Dama'));
    assert.deepEqual(errors,[],'no browser errors while loading reports');
    assert.ok(requests.every(x=>x.method==='GET'),'navigation must not mutate application data');
  }finally{runtime.close()}
});
