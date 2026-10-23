const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const html=fs.readFileSync(path.join(__dirname,'../../web/index.html'),'utf8');
const start=html.indexOf('async function waitForUploadJob(');
const end=html.indexOf('const ACTIVE_UPLOAD_WATCHES=',start);
if(start<0||end<0)throw Error('No se localizó el seguimiento de carga.');
const code=html.slice(start,end);

function fixture(responses){
  const state=new Map();
  const progress=[];
  let apiCalls=0, sent=0, now=1000;
  const context={
    Date:{now:()=>now},Promise,Number,FormData:class {append(){}},
    encodeURIComponent,Error,
    setTimeout:fn=>{now+=5000;fn();},
    localStorage:{
      getItem:k=>state.get(k)||null,
      setItem:(k,v)=>state.set(k,v),
      removeItem:k=>state.delete(k)
    },
    api:async (url,opts)=>{
      apiCalls++;
      if(url.startsWith('/api/upload/jobs/')&&opts?.method==='POST'){
        sent++;
        return {id:'existing-job'};
      }
      const next=responses.shift();
      if(next instanceof Error)throw next;
      return next;
    }
  };
  vm.runInNewContext(code+'\nthis.waitForUploadJob=waitForUploadJob;this.backgroundFileUpload=backgroundFileUpload;',context);
  return {context,progress,state,get apiCalls(){return apiCalls},get sent(){return sent}};
}
const temporary=(status)=>Object.assign(new Error('Render reiniciando'),{status});

test('A temporary 502 during a deployment reconnects to the same job',async()=>{
  const f=fixture([{status:'processing',progress:25,message:'Procesando'},temporary(502),temporary(503),{status:'complete',progress:100,result:{rows:13844}}]);
  const result=await f.context.waitForUploadJob('existing-job',x=>f.progress.push(x));
  assert.equal(result.rows,13844);
  assert.equal(f.apiCalls,4);
  assert.equal(f.progress.filter(x=>x.status==='reconnecting').length,2);
});

test('A known pending upload is reused without sending another 208MB Excel',async()=>{
  const f=fixture([{status:'complete',result:{rows:13844}}]);
  f.state.set('operacionesRopaUploadJob.operations','existing-job');
  const result=await f.context.backgroundFileUpload('operations',{name:'datos.xlsx'},x=>f.progress.push(x));
  assert.equal(result.rows,13844);
  assert.equal(f.sent,0);
  assert.equal(f.state.has('operacionesRopaUploadJob.operations'),false);
});

test('A terminal backend error is never silently retried',async()=>{
  const f=fixture([{status:'error',error:'Archivo inválido'}]);
  await assert.rejects(f.context.waitForUploadJob('existing-job'),/Archivo inválido/);
  assert.equal(f.apiCalls,1);
});
