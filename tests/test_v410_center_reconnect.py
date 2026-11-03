"""V410: reconexión automática de Centro Operativo sin reenviar escrituras."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_center_keeps_filters_and_has_bounded_retry():
    source=(ROOT/"v240_center_routes_calendar_patch.py").read_text("utf-8")
    assert "const centerRecoveryAttempts=new Map()" in source
    assert "centerRecoveryAttempts.delete(sig)" in source
    assert "const status=Number(err?.status||0)" in source
    assert "if(temporary&&count<2&&!document.hidden)" in source
    assert "q('#operPeriodSelect')?.value||''" in source
    assert "q('#operStoreSelect')?.value||'Compañía'" in source
    assert "Volver a consultar" in source
    assert "renderCenter(mode,false)" in source


def test_transient_get_retries_but_never_retries_post_or_auth_errors():
    source=(ROOT/"web/index.html").read_text("utf-8")
    assert "const retryDelays=[1200,2600,5100]" in source
    assert "if(!canRetry||!transient||attempt>=retryDelays.length)throw error" in source
    assert "callerSignal?.aborted||controller.signal.aborted" in source
    js=r"""
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync(process.argv[1],'utf8');
const begin=html.indexOf('async function apiRequest(url,opt={})');
const end=html.indexOf('async function uploadSalesPdfs(',begin);
if(begin<0||end<=begin)throw Error('No se encontró apiRequest');
const body=html.slice(begin,end);
async function run(statuses,url,method='GET'){
  let count=0;
  const context={
    AbortController,console,
    setTimeout:(fn,ms)=>setTimeout(fn,ms<6000?2:60000),
    clearTimeout,
    fetch:async()=>{
      const status=statuses[Math.min(count++,statuses.length-1)];
      return {ok:status===200,status,
        text:async()=>status===200?'{"metrics":{"total_pzs":42}}':''};
    }
  };
  vm.createContext(context);
  vm.runInContext(body+'; globalThis.check=apiRequest;',context);
  let result=null,error=null;
  try{result=await context.check(url,{method,timeoutMs:0});}catch(e){error=e;}
  return {count,result,error};
}
(async()=>{
  let a=await run([502,503,200],'/api/operations/project-scope-v151?period_type=day');
  if(a.count!==3||a.result?.metrics?.total_pzs!==42)throw Error('No recuperó los datos después del reinicio');
  a=await run([502,200],'/api/operations?period_type=week','POST');
  if(a.count!==1||a.error?.status!==502)throw Error('Nunca debe reintentar POST');
  a=await run([401,200],'/api/operations/meta');
  if(a.count!==1||a.error?.status!==401)throw Error('No debe reintentar acceso no autorizado');
  a=await run([503,200],'/api/bootstrap');
  if(a.count!==1||a.error?.status!==503)throw Error('No debe reintentar consultas fuera de Operaciones');
  a=await run([502,502,502,502,200],'/api/operations/meta');
  if(a.count!==4||a.error?.status!==502)throw Error('El reintento debe ser acotado');
})().catch(e=>{console.error(e);process.exit(1)});
"""
    result=subprocess.run(["node","-e",js,str(ROOT/"web/index.html")],
        capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+"\n"+result.stderr
