const fs=require('node:fs'),path=require('node:path');
const {JSDOM,ResourceLoader,VirtualConsole}=require('jsdom');
const store={store:'Iztapalapa',name:'Iztapalapa',is_project:true,ingresos:100,total_pzs:100,dev_pzs:20,muertos:50,cajas:30,probador:20,acondicionado:85,ubicado:80,recorridos:4,arrival:100,processed:85,released:80,compliance_pct:85};
const periods={dates:['2026-10-01'],weeks:['2026-W40'],months:['2026-10'],years:['2026'],available_dates:['2026-10-01'],available_weeks:['2026-W40'],available_months:['2026-10'],available_years:['2026']};
const report={available:true,...periods,period_value:'2026-10',stores:[store],project_stores:['Iztapalapa'],stores_available:['Iztapalapa'],areas_available:['Piso'],activities_available:['Recolección de muertos'],metrics:{...store,pct_acondicionado:85,pct_ubicado:80,conversion_pct:50,recovery_pct:50,converted_pieces:10,recovered_value:1000,return_value:2000},rows:[],recovery_by_store:[{...store,conversion_pct:50}],productivity:[],activity_detail:[],daily_peaks:[],hourly_peaks:[],score_by_store:[],goals:{},summary:{arrival_origin:100,processed:85,released:80,pending:15,efficiency_pct:85,productivity_avg:85,compliance_pct:85,collaborators:1},comparison:[],top:[],alerts:[]};
function bonusFixture(query){
 const b=Number(query.get('bonus')||1),selected=query.get('store')||'Iztapalapa';
 const breakdown=[
  {key:'sales',indicator:'Venta vs Meta',compliance_pct:95,max_points:50,points:47.5,weight:50,status:'En avance',meta:100,result:95,unit:'%'},
  {key:'ddi',indicator:'DDI por Cat',compliance_pct:60,max_points:30,points:18,weight:30,status:'En avance',meta:100,result:60,unit:'%'},
  {key:'attendance',indicator:'Asistencia',compliance_pct:98,max_points:20,points:19.6,weight:20,status:'En avance',meta:100,result:98,unit:'%'}
 ];
 const ranking=[
  {rank:1,store:'Iztapalapa',points:85.1,max_points:100,compliance_pct:85.1,classification:'Bueno',ready:true},
  {rank:2,store:'Vallejo',points:72,max_points:100,compliance_pct:72,classification:'Bueno',ready:true}
 ];
 const companyComparison=Array.from({length:6},(_,i)=>({bonus_no:i+1,name:'Bono '+(i+1),average_pct:80+i,stores_ready:2,stores_incomplete:0,excellent:i%2,good:2-(i%2),risk:0,critical:0,best_store:'Iztapalapa',best_pct:85+i,delta_vs_bonus1:i}));
 return {
  month:'2026-10',bonus_no:b,name:'Bono '+b,official_bonus:1,can_admin:true,
  stores:['Iztapalapa','Vallejo'],months:[{value:'2026-10',label:'Octubre 2026'}],selected_store:selected,
  model:{bonus_no:b,name:'Bono '+b,points:85.1,max_points:100,compliance_pct:85.1,ready:true,config_ready:true,classification:'Bueno',criteria_total:3,criteria_met:0,criteria_pending:3,breakdown,formula:'Fórmula de prueba'},
  ranking,comparison:companyComparison.map(x=>({bonus_no:x.bonus_no,name:x.name,points:x.average_pct,max_points:100,compliance_pct:x.average_pct,rank:1,ready:true,classification:'Bueno',active:true})),
  company_summary:{stores_total:2,stores_complete:2,stores_incomplete:0,sales_actual:190,sales_goal:200,sales_pct:95,attendance_pct:98,target_models:20,ddi_initial:150,ddi_current:100,ddi_reduction_pct:33.3,initial_investment:100000,current_investment:70000,investment_reduction_pct:30,initial_existence:1000,current_existence:700,existence_reduction_pct:30,initial_models:20,current_models:15,models_reduction_pct:25,catalogs:[{catalog:'Abrigador',models:8,ddi_reduction_pct:35,investment_reduction_pct:30,bonus1_ddi_component_pct:60},{catalog:'Licencias',models:6,ddi_reduction_pct:30,investment_reduction_pct:25,bonus1_ddi_component_pct:55},{catalog:'Básicos',models:6,ddi_reduction_pct:32,investment_reduction_pct:28,bonus1_ddi_component_pct:58}]},
  company_comparison:companyComparison,
  configs:Object.fromEntries(Array.from({length:6},(_,i)=>[i+1,{active:true,version:1,effective_from:'2026-10'}])),
  base:{selected_store:selected,can_edit_attendance:true,selected:{score:85.1,score_ready:true,target_models:10,sales:{actual:95,goal:100,pct:95},ddi:{pct:60,catalogs:[]},attendance:{pct:98},inventory:{},details:[]},ranking:[]},
  glossary:{name:'Bono '+b,objective:'Objetivo de prueba',methodology:'Metodología de prueba',evaluated:'Tiendas',period:'Mes',difference:'Prueba',formula:'Fórmula',sources:[],rules:[],criteria:breakdown.map(x=>({key:x.key,name:x.indicator,meaning:'Criterio',source:'Fuente',meta:'100%',parameter:'Parámetro',rule:'Regla',criterion_formula:'Fórmula'})),example_inputs:{sales:90,ddi:80,attendance:95},example:{classification:'Bueno',points:80,max_points:100,compliance_pct:80,breakdown},config:{active:true}}
 };
}
function fixture(p, query){
 if(p==='/api/bootstrap')return {needs_owner:false,user:null,tabs:{}};
 if(p==='/api/app-version')return {version:'test'};
 if(p==='/api/settings/report-tabs')return {tabs:[]};
 if(p==='/api/operations/meta')return {...report,stores_available:['Iztapalapa']};
 if(p==='/api/operation/meta')return {...periods,stores:['Iztapalapa'],standards:{},activities:[],areas:[]};
 if(p==='/api/operations'||p==='/api/operation/summary-v149')return report;
 if(p==='/api/commercial-bootstrap-v188')return {...periods,week:'2026-W40',stores_available:['Iztapalapa']};
 if(p==='/api/dashboard')return {...report,week:'2026-W40',selected_store:query.get('store')||'Compañía',source_file:'fixture.xlsx',kpis:{existence:12345,floor:10000,warehouse:2345,suggested:500,capacity:15000,occupancy:80},sections:[],ranking:[],catalogs:[],models:[],locations:[],group_rows:[]};
 if(p==='/api/bonuses-v302')return bonusFixture(query);
 if(p==='/api/bonuses-v302/config')return {month:'2026-10',configs:{},official_bonus:1,history:[],official_history:[],user:'Test Admin'};
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
