const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../web/index.html'),'utf8');
const script=html.slice(html.indexOf('const ropaApiInflight='),html.indexOf('async function start(){'));
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function runtime(fetch, timers={}){
 const ctx={fetch,AbortController,DOMException,Headers,structuredClone,
   setTimeout,clearTimeout,console,Map,Date,Promise,...timers};
 ctx.window=ctx;
 vm.createContext(ctx);vm.runInContext(script,ctx);
 return ctx;
}
const json=(data,status=200)=>({ok:status<400,status,text:async()=>JSON.stringify(data)});

test('identical GET reports share one request and return independent objects',async()=>{
 let calls=0;
 const r=runtime(async()=>{calls++;await pause(10);return json({pieces:784,rows:[{store:'Olivar'}]})});
 const results=await Promise.all(Array.from({length:20},()=>r.api('/api/operations?store=Olivar')));
 assert.equal(calls,1);
 assert.equal(results[1].pieces,784);
 results[0].rows[0].store='changed';
 assert.equal(results[1].rows[0].store,'Olivar');
 await r.api('/api/operations?store=Olivar');
 assert.equal(calls,2,'settled results are never retained by the browser helper');
});

test('different scopes, headers and POST bodies are not combined',async()=>{
 let calls=0;
 const r=runtime(async()=>{calls++;await pause(5);return json({ok:true})});
 await Promise.all([
  r.api('/api/operations?store=Olivar'),r.api('/api/operations?store=Vallejo'),
  r.api('/api/operations?store=Olivar',{headers:{'Cache-Control':'no-cache'}}),
  r.api('/api/upload',{method:'POST',body:'one'}),r.api('/api/upload',{method:'POST',body:'two'})
 ]);
 assert.equal(calls,5);
});

test('caller cancellation reaches fetch and stays an AbortError for stale tabs',async()=>{
 let signal;
 const r=runtime((_url,cfg)=>new Promise((_resolve,reject)=>{
  signal=cfg.signal;
  cfg.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true});
 }));
 const controller=new AbortController();
 const promise=r.api('/api/operations?store=Olivar',{signal:controller.signal});
 controller.abort();
 await assert.rejects(promise,{name:'AbortError'});
 assert.equal(signal.aborted,true);
});

test('a request timeout retains the readable timeout message',async()=>{
 const r=runtime((_url,cfg)=>new Promise((_resolve,reject)=>{
  cfg.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true});
 }));
 await assert.rejects(r.api('/api/operations',{timeoutMs:10}),/tardó demasiado/);
});

test('failed requests are released so the user can retry',async()=>{
 let calls=0;
 const r=runtime(async()=>{calls++;return calls===1?json({detail:'Intenta de nuevo'},503):json({pieces:784})});
 await assert.rejects(r.api('/api/operations'),/Intenta de nuevo/);
 assert.equal((await r.api('/api/operations')).pieces,784);
 assert.equal(calls,2);
});

test('sales PDF upload polls short HTTP requests and returns full parser output',async()=>{
 const requests=[],progress=[];
 let polls=0;
 const r=runtime(async(url,opt)=>{
  requests.push({url,method:opt.method||'GET'});
  if(url==='/api/upload/jobs/sales-pdfs')return json({id:'job1',status:'queued'},202);
  polls++;
  return json(polls===1?{status:'processing',message:'Procesando PDF'}:
   {status:'complete',result:{results:[{file:'ventas.pdf',ok:true,total_sales:125000.25,rows:784}]}});
 },{setTimeout:(fn,ms)=>ms===1500?setTimeout(fn,0):setTimeout(fn,ms)});
 const result=await r.uploadSalesPdfs('form',message=>progress.push(message));
 assert.equal(result.results[0].total_sales,125000.25);
 assert.equal(result.results[0].rows,784);
 assert.equal(requests[0].method,'POST');
 assert.ok(requests.slice(1).every(x=>x.url==='/api/upload/jobs/job1'&&x.method==='GET'));
 assert.ok(progress.includes('Procesando PDF'));
});
