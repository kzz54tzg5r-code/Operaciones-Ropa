// V315 focused navigation/runtime smoke for the Bonos module only.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {test}=require('node:test');
const {createRuntime}=require('./runtime-fixture.cjs');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'v302_six_sales_bonuses_patch.py'),'utf8');
const match=source.match(/<script id="v302-js">([\s\S]*?)<\/script>/);
assert.ok(match,'embedded V302 Bonus JavaScript must exist');
const js=match[1];
const markup='<!doctype html><html><body>'+
  '<aside id="sidebar"></aside><nav id="mobileMainNav"></nav>'+
  '<div id="heroTitle"></div><div id="heroSub"></div>'+
  '<main class="main"></main><script>'+js+'</script></body></html>';
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

test('V315 opens all Bonus tabs and drills from company ranking to store panorama',{timeout:12000},async()=>{
  const runtime=createRuntime(markup,path.join(root,'web'));
  const {window:w,errors,requests}=runtime,d=w.document;
  const waitFor=async (selector,pattern)=>{
    for(let i=0;i<50;i++){
      const el=d.querySelector(selector);
      if(el&&(!pattern||pattern.test(el.textContent)))return el;
      await wait(50);
    }
    throw new Error('Missing/unfinished '+selector+(pattern?' '+pattern:''));
  };
  const click=async selector=>{
    const el=await waitFor(selector);
    el.click();
    await wait(80);
    return el;
  };
  try{
    d.dispatchEvent(new w.Event('DOMContentLoaded',{bubbles:true}));
    await wait(400);
    await click('#sidebar [data-main="bonuses"]');
    const host=await waitFor('#v302Host',/Resumen general · Compañía/);

    assert.equal(d.querySelector('.page.active')?.id,'page-bonuses');
    assert.equal(d.getElementById('v302Store'),null,'company summary must not force a store');
    assert.ok(d.getElementById('v302Month'),'company summary keeps period');

    for(let i=1;i<=6;i++){
      await click('[data-v302-bonus="'+i+'"]');
      await waitFor('#v302Host',new RegExp('Bono '+i));
      assert.ok(requests.some(x=>x.path==='/api/bonuses-v302'&&x.query.get('bonus')===String(i)),'Bono '+i+' payload must load');
    }

    const sections=[
      ['summary',/Resumen general · Compañía/],
      ['ranking',/Ranking completo de todas las tiendas/],
      ['store',/Panorama por tienda/],
      ['models',/Modelos a detalle/],
      ['compare',/Impacto de las seis metodologías/],
      ['glossary',/Glosario del Bono/],
      ['config',/Configuración administrativa/]
    ];
    for(const [section,pattern] of sections){
      await click('[data-v302-section="'+section+'"]');
      await waitFor('#v302Host',pattern);
      assert.ok(d.querySelector('[data-v302-section="'+section+'"]'));
    }

    await click('[data-v302-section="ranking"]');
    const row=await waitFor('[data-v304-store="Iztapalapa"]');
    row.click();
    await waitFor('#v302Host',/Panorama por tienda/);
    assert.ok(d.getElementById('v302Store'),'store panorama exposes store selector');
    assert.equal(d.getElementById('v302Store').value,'Iztapalapa');
    assert.deepEqual(errors,[],'Bonus navigation must not raise browser errors');
  } finally {
    runtime.close();
  }
});
