const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const source=fs.readFileSync(path.join(__dirname,'../../web/pwa_install.js'),'utf8');
const settle=()=>new Promise(r=>setImmediate(r));
async function fixture(options={}){
  let version='aaaaaaaa', reloads=0, now=100000, fail=false, writer=null;
  const intervals=new Map();
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>{if(/navigation/.test(e.message))reloads++;else throw e;});
  const dom=new JSDOM('<div class="profile"></div><div id="capture"><input id="pieces" type="number"></div>',{url:'https://app.example/',runScripts:'outside-only',virtualConsole:vc});
  const w=dom.window;
  await new Promise(r=>w.addEventListener('load',r,{once:true}));
  Object.defineProperty(w.document,'visibilityState',{value:'visible'});
  w.matchMedia=()=>({matches:true});
  w.Date.now=()=>now;
  w.setInterval=(fn,delay)=>{intervals.set(delay,fn);return delay;};
  w.fetch=async (url,opt)=>{
    if(opt?.method==='POST')return new Promise(r=>{writer=r;});
    if(fail)throw new Error('offline');
    return {ok:true,json:async()=>({version})};
  };
  if(options.loadedVersion)w.localStorage.setItem('operaciones-ropa:loaded-version',options.loadedVersion);
  w.eval(source);
  w.dispatchEvent(new w.Event('load'));await settle();
  return {w,dom,intervals,get reloads(){return reloads;},
    async update(){version='bbbbbbbb';await intervals.get(60000)();await settle();},
    async idle(){now+=31000;await settle();},
    edit(){const el=w.document.getElementById('pieces');el.focus();el.value='42';el.dispatchEvent(new w.Event('input',{bubbles:true}));return el;},
    offline(){fail=true;},finishWrite(){writer({ok:true});}};
}
test('new version displays persistent popup until explicit update, and keeps original version label',async()=>{
  const f=await fixture();try{
    await f.update();
    assert.match(f.w.document.querySelector('.or-version-badge').textContent,/aaaaaaaa/);
    assert.ok(f.w.document.querySelector('.or-update-banner'));
    await f.idle();await f.idle();
    assert.equal(f.reloads,0);
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,1);
    assert.equal(f.w.localStorage.getItem('operaciones-ropa:loaded-version'),'bbbbbbbb');
  }finally{f.dom.window.close();}
});
test('stale PWA opens with new-version popup even after server was updated while app was closed',async()=>{
  const f=await fixture({loadedVersion:'zzzzzzzz'});try{
    assert.ok(f.w.document.querySelector('.or-update-banner'));
    assert.match(f.w.document.querySelector('.or-version-badge').textContent,/zzzzzzzz/);
  }finally{f.dom.window.close();}
});
test('explicit update preserves unsaved fields',async()=>{
  const f=await fixture();try{
    f.edit();await f.update();
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,0);
    assert.equal(f.w.document.getElementById('pieces').value,'42');
  }finally{f.dom.window.close();}
});
test('explicit capture save releases dirty guard and permits update',async()=>{
  const f=await fixture();try{
    f.edit();await f.update();
    f.w.document.dispatchEvent(new f.w.CustomEvent('or:capture-saved',{detail:{root:f.w.document.getElementById('capture')}}));
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});
test('active writes block manual reload',async()=>{
  const f=await fixture();try{
    await f.update();
    const p=f.w.fetch('/api/capture',{method:'POST'});
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();assert.equal(f.reloads,0);
    f.finishWrite();await p;
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});
test('server failure never reloads current working page',async()=>{
  const f=await fixture();try{
    await f.update();f.offline();
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,0);
    assert.equal(f.w.document.querySelector('.or-update-banner button').disabled,false);
  }finally{f.dom.window.close();}
});
test('manual update button API shows up-to-date notice when no new deployment',async()=>{
  const f=await fixture();try{
    await f.w.OperacionesPWA.checkForUpdates({manual:true});
    assert.match(f.w.document.querySelector('.or-update-current').textContent,/versión más reciente/);
  }finally{f.dom.window.close();}
});

test('capture restores all four areas and keeps draft on failed save',async()=>{
  const f=await fixture();try{
    const w=f.w;
    w.document.body.insertAdjacentHTML('beforeend','<div id="operativoDynamicContent"></div>');
    const patch=fs.readFileSync(path.join(__dirname,'../../v222_operation_capture_nav_admin_patch.py'),'utf8');
    const capture=patch.slice(patch.indexOf('  function paintCapture('),patch.indexOf('  async function renderCapture('));
    w.eval(`
      const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)];
      const esc=x=>String(x),num=x=>Number(x)||0,hms=()=>'',startClock=()=>{};
      let captureState={},timerHandle=null,timerStartedAt='';
      const activityOptions=()=>['Ubicado'];
      const areasFromInputs=()=>Object.fromEntries(qa('[data-v222-area]').map(x=>[x.dataset.v222Area,Number(x.value)||0]));
      const updateAreaTotal=()=>{};
      let succeeds=false;
      const A=async()=>{if(!succeeds)throw new Error('sin red');return {message:'ok'};};
      const renderCapture=async()=>{};
      ${capture}
      window.paintCapture=paintCapture;window.allowSave=()=>{succeeds=true;};
    `);
    const key='or.capture.v1:123:Tienda:17';
    w.sessionStorage.setItem(key,JSON.stringify({Colgado:'10',Doblado:'20',Jeans:'30','Lencería':'40'}));
    w.paintCapture({employee_no:'123',store:'Tienda'},{id:17,activity:'Ubicado'},{items:[]});
    assert.deepEqual([...w.document.querySelectorAll('[data-v222-area]')].map(x=>x.value),['10','20','30','40']);
    assert.equal(JSON.parse(w.sessionStorage.getItem(key))['Lencería'],'40');
    w.document.getElementById('v222Finish').click();await settle();
    assert.ok(w.sessionStorage.getItem(key));
    assert.equal(w.document.getElementById('v222Finish').disabled,false);
    // Re-rendering must not leave the removed input nodes blocking updates forever.
    w.paintCapture({employee_no:'123',store:'Tienda'},{id:17,activity:'Ubicado'},{items:[]});
    await f.update();await f.idle();assert.equal(f.reloads,0);
    w.allowSave();w.document.getElementById('v222Finish').click();await settle();
    assert.equal(w.sessionStorage.getItem(key),null);
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});


test('changing Bono filters cannot block a manual update',async()=>{
  const f=await fixture();try{
    f.w.document.body.insertAdjacentHTML('beforeend',
      '<div class="v313-filters"><select id="v313Store"><option>Centro</option><option>Vallejo</option></select></div>');
    const select=f.w.document.getElementById('v313Store');
    select.focus();select.value='Vallejo';
    select.dispatchEvent(new f.w.Event('change',{bubbles:true}));
    await f.update();
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,1,'report filters should not be treated as unsaved forms');
  }finally{f.dom.window.close();}
});
test('a stale detached report input is never a permanent update blocker',async()=>{
  const f=await fixture();try{
    f.w.document.body.insertAdjacentHTML('beforeend','<section id="oldreport"><input id="oldField"></section>');
    const input=f.w.document.getElementById('oldField');
    input.focus();input.value='A';input.dispatchEvent(new f.w.Event('input',{bubbles:true}));
    f.w.document.getElementById('oldreport').remove();
    await f.update();
    f.w.document.querySelector('.or-update-banner button').click();
    await settle();
    assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});
test('persistent capture draft remains protected even after its input re-renders',async()=>{
  const f=await fixture();try{
    f.w.sessionStorage.setItem('or.capture.v1:42:Centro:18',JSON.stringify({Colgado:'9'}));
    await f.update();
    const button=f.w.document.querySelector('.or-update-banner button');
    button.click();
    await settle();
    assert.equal(f.reloads,0);
    assert.match(f.w.document.querySelector('.or-update-banner span').textContent,/sin guardar/);
    f.w.sessionStorage.removeItem('or.capture.v1:42:Centro:18');
    button.click();await settle();
    assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});


test('update prompt offers deliberate override for old drafts and then reloads',async()=>{
  const f=await fixture();try{
    f.edit();
    await f.update();
    const button=f.w.document.querySelector('.or-update-banner button');
    button.click();await settle();
    assert.equal(f.reloads,0);
    assert.match(button.textContent,/de todos modos/);
    f.w.confirm=()=>true;
    button.click();await settle();
    assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});
