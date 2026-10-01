const fs=require('node:fs'),path=require('node:path');
const {JSDOM,ResourceLoader,VirtualConsole}=require('jsdom');
const store={store:'Iztapalapa',name:'Iztapalapa',is_project:true,ingresos:100,total_pzs:100,dev_pzs:20,muertos:50,cajas:30,probador:20,acondicionado:85,ubicado:80,recorridos:4,arrival:100,processed:85,released:80,compliance_pct:85};
const periods={dates:['2026-10-01'],weeks:['2026-W40'],months:['2026-10'],years:['2026'],available_dates:['2026-10-01'],available_weeks:['2026-W40'],available_months:['2026-10'],available_years:['2026']};
const report={available:true,...periods,period_value:'2026-10',stores:[store],project_stores:['Iztapalapa'],stores_available:['Iztapalapa'],areas_available:['Piso'],activities_available:['Recolección de muertos'],metrics:{...store,pct_acondicionado:85,pct_ubicado:80,conversion_pct:50,recovery_pct:50,converted_pieces:10,recovered_value:1000,return_value:2000},rows:[],recovery_by_store:[{...store,conversion_pct:50}],productivity:[],activity_detail:[],daily_peaks:[],hourly_peaks:[],score_by_store:[],goals:{},summary:{arrival_origin:100,processed:85,released:80,pending:15,efficiency_pct:85,productivity_avg:85,compliance_pct:85,collaborators:1},comparison:[],top:[],alerts:[]};
function fixture(p, query){
 if(p==='/api/bootstrap')return {needs_owner:false,user:null,tabs:{}};
 if(p==='/api/app-version')return {version:'test'};
 if(p==='/api/settings/report-tabs')return {tabs:[]};
 if(p==='/api/operations/meta')return {...report,stores_available:['Iztapalapa']};
 if(p==='/api/operation/meta')return {...periods,stores:['Iztapalapa'],standards:{},activities:[],areas:[]};
 if(p==='/api/operations'||p==='/api/operation/summary-v149')return report;
 if(p==='/api/commercial-bootstrap-v188')return {...periods,week:'2026-W40',stores_available:['Iztapalapa']};
 if(p==='/api/dashboard')return {...report,week:'2026-W40',selected_store:query.get('store')||'Compañía',source_file:'fixture.xlsx',kpis:{existence:12345,floor:10000,warehouse:2345,suggested:500,capacity:15000,occupancy:80},sections:[],ranking:[],catalogs:[],models:[],locations:[],group_rows:[]};
 if(p==='/api/upload/operations/current')return {available:true,file:'fixture.xlsx',rows:1};
 if(p.includes('/history'))return {history:[],files:[],entries:[]};
 if(p==='/api/operation-productivity/meta')return {store:'Iztapalapa',activities:[],areas:[],people:[],active:null,history:[]};
 return {...report,items:[],users:[],rows:[],sections:[],locations:[],models:[],catalogs:[],families:[],statuses:[],values:[],months:[],totals:{},stores:[],data:[],groups:[],roster:[],entries:[],results:[],levels:[],profile_complete:true,standards:{},meta:{},permissions:{}};
}

function createRuntime(html, assets) {
  const errors=[], requests=[];
  let closing=false;
  class LocalResources extends ResourceLoader {
    fetch(url) {
      const u=new URL(url);
      if(u.pathname.startsWith('/static/')) {
        const p=path.join(assets,u.pathname.slice(8));
        if(fs.existsSync(p)) return Promise.resolve(fs.readFileSync(p));
      }
      return null;
    }
  }
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>{if(!closing && e.type!=='css parsing')errors.push(e.detail?.stack||e.message)});
  vc.on('error',(...a)=>{if(!closing)errors.push(a.map(x=>x?.stack||String(x)).join(' '))});
  const dom=new JSDOM(html,{
    url:'https://app.test/',runScripts:'dangerously',resources:new LocalResources(),
    pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w) {
      w.fetch=async (url, options={})=>{
        const u=new URL(url,'https://app.test/');
        requests.push({path:u.pathname,query:u.searchParams,method:options.method||'GET'});
        return new Response(JSON.stringify(fixture(u.pathname,u.searchParams)),{
          status:200,headers:{'Content-Type':'application/json'}
        });
      };
      w.matchMedia=q=>({matches:false,media:q,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}});
      w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
      w.ResizeObserver=class{observe(){}disconnect(){}};
      w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
      w.alert=msg=>errors.push(String(msg));w.confirm=()=>false;
      w.requestIdleCallback=cb=>w.setTimeout(cb,0);
    }
  });
  return {window:dom.window,errors,requests,close(){closing=true;dom.window.close()}};
}
module.exports={createRuntime};
