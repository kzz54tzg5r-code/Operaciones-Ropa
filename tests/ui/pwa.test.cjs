const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const source=fs.readFileSync(path.join(__dirname,'../../web/pwa_install.js'),'utf8');
const settle=()=>new Promise(r=>setImmediate(r));
async function fixture(){
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
  w.eval(source);
  w.dispatchEvent(new w.Event('load'));await settle();
  return {w,dom,intervals,get reloads(){return reloads;},
    async update(){version='bbbbbbbb';await intervals.get(120000)();await settle();},
    async idle(){now+=31000;intervals.get(10000)();await settle();},
    edit(){const el=w.document.getElementById('pieces');el.focus();el.value='42';el.dispatchEvent(new w.Event('input',{bubbles:true}));return el;},
    offline(){fail=true;},finishWrite(){writer({ok:true});}};
}
test('pending version does not relabel loaded build; clean idle app refreshes once',async()=>{
  const f=await fixture();try{await f.update();assert.match(f.w.document.querySelector('.or-version-badge').textContent,/aaaaaaaa/);await f.idle();await f.idle();assert.equal(f.reloads,1);}finally{f.dom.window.close();}
});
test('manual and automatic update preserve unsaved fields',async()=>{
  const f=await fixture();try{f.edit();await f.update();f.w.document.querySelector('.or-update-banner button').click();await f.idle();assert.equal(f.reloads,0);assert.equal(f.w.document.getElementById('pieces').value,'42');}finally{f.dom.window.close();}
});
test('only explicit capture save releases dirty guard',async()=>{
  const f=await fixture();try{f.edit();await f.update();f.w.document.dispatchEvent(new f.w.CustomEvent('or:capture-saved',{detail:{root:f.w.document.getElementById('capture')}}));await f.idle();assert.equal(f.reloads,1);}finally{f.dom.window.close();}
});
test('active writes block automatic reload',async()=>{
  const f=await fixture();try{await f.update();const p=f.w.fetch('/api/capture',{method:'POST'});await f.idle();assert.equal(f.reloads,0);f.finishWrite();await p;await f.idle();assert.equal(f.reloads,1);}finally{f.dom.window.close();}
});
test('server failure never reloads the current working page',async()=>{
  const f=await fixture();try{await f.update();f.offline();await f.idle();assert.equal(f.reloads,0);assert.equal(f.w.document.querySelector('.or-update-banner button').disabled,false);}finally{f.dom.window.close();}
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
    await f.idle();assert.equal(f.reloads,1);
  }finally{f.dom.window.close();}
});
