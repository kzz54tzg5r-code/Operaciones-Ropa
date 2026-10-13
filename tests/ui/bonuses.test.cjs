// V315 dedicated navigation/runtime smoke for Bonos
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {test,after}=require('node:test');
const {createRuntime}=require('./runtime-fixture.cjs');
const root=path.resolve(__dirname,'../..');
const output=fs.mkdtempSync(path.join(os.tmpdir(),'ropa-bonus-tabs-'));
const generated=spawnSync(process.env.PYTHON||'python3',[path.join(__dirname,'render_production_page.py'),output],{
  cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},encoding:'utf8',timeout:60000
});
assert.equal(generated.status,0,generated.stdout+'\n'+generated.stderr);
const html=fs.readFileSync(path.join(output,'page.html'),'utf8');
after(()=>fs.rmSync(output,{recursive:true,force:true}));
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

test('V315 all Bonus tabs are reachable and ranking drills into store panorama',{timeout:45000},async()=>{
  const runtime=createRuntime(html,path.join(output,'web'));
  const {window:w,errors,requests}=runtime,d=w.document;
  const waitFor=async selector=>{
    for(let i=0;i<60;i++){
      const el=d.querySelector(selector);
      if(el)return el;
      await wait(100);
    }
    throw new Error('Missing '+selector);
  };
  const click=async selector=>{
    const el=await waitFor(selector);
    el.click();
    await wait(220);
    return el;
  };
  try{
    if(d.readyState!=='complete')await Promise.race([new Promise(resolve=>w.addEventListener('load',resolve,{once:true})),wait(3000)]);
    await wait(2600);
    await w.enter({id:1,username:'Test Admin',role:'admin',store:'',can_preview_roles:false});
    await wait(500);
    await click('[data-main="bonuses"]');
    await wait(400);

    assert.equal(d.querySelector('.page.active')?.id,'page-bonuses');
    assert.match(d.getElementById('v302Host').textContent,/Resumen general · Compañía/);
    assert.equal(d.getElementById('v302Store'),null);
    assert.ok(d.getElementById('v302Month'));

    for(let i=1;i<=6;i++){
      await click('[data-v302-bonus="'+i+'"]');
      assert.ok(requests.some(x=>x.path==='/api/bonuses-v302' && x.query.get('bonus')===String(i)));
      assert.match(d.getElementById('v302Host').textContent,new RegExp('Bono '+i));
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
      assert.match(d.getElementById('v302Host').textContent,pattern,'section '+section);
    }

    await click('[data-v302-section="ranking"]');
    const row=await waitFor('[data-v304-store="Iztapalapa"]');
    row.click();
    await wait(350);
    assert.match(d.getElementById('v302Host').textContent,/Panorama por tienda/);
    assert.ok(d.getElementById('v302Store'));
    assert.equal(d.getElementById('v302Store').value,'Iztapalapa');
    assert.deepEqual(errors,[]);
  } finally {
    runtime.close();
  }
});
