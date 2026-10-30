import React,{useEffect,useMemo,useState} from "react";
import{createRoot}from"react-dom/client";
import{createClient}from"@supabase/supabase-js";
import{sampleRows,stores as demoStores}from"./demo.js";
import{aggregate,visibleInPeriod,periodBounds}from"./metrics.js";
import"./style.css";

const env=import.meta.env;
const DEMO=env.VITE_DEMO_MODE!=="false";
const configured=Boolean(env.VITE_SUPABASE_URL&&env.VITE_SUPABASE_ANON_KEY);
const supabase=!DEMO&&configured?createClient(env.VITE_SUPABASE_URL,env.VITE_SUPABASE_ANON_KEY):null;
const num=n=>new Intl.NumberFormat("es-MX",{maximumFractionDigits:0}).format(n||0);

function csv(rows){
 const cols=[["Tienda","store_name"],["Ingresado","ingested"],["Habilitado","prepared"],["Ubicado","placed"],["Pend. acondicionar","pending_prepared"],["Pend. ubicar","pending_placed"],["% habilitado","pct_prepared"],["% ubicado","pct_placed"],["Recorridos","walks_real"],["Meta recorridos","walks_target"]];
 const safe=value=>{const raw=String(value??"");const guarded=/^[=+\-@]/.test(raw)?"'"+raw:raw;return '"'+guarded.replaceAll('"','""')+'"';};
 return [cols.map(c=>safe(c[0])).join(","),...rows.map(r=>cols.map(c=>safe(r[c[1]])).join(","))].join("\r\n");
}
function exportFile(rows){
 const blob=new Blob(["\ufeff",csv(rows)],{type:"text/csv;charset=utf-8"});
 const url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download="centro_operativo_prueba.csv";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
}
function Login({onSignedIn}){
 const[email,setEmail]=useState("");const[password,setPassword]=useState("");const[error,setError]=useState("");const[loading,setLoading]=useState(false);
 const submit=async e=>{e.preventDefault();setError("");setLoading(true);try{
  const {data,error}=await supabase.auth.signInWithPassword({email,password});
  if(error)throw error;onSignedIn(data.session);
 }catch(ex){setError(ex.message||"No fue posible iniciar sesión");}finally{setLoading(false);}};
 return <main className="login-wrap"><form className="login-panel" onSubmit={submit}>
   <img src="/price_shoes_white.svg" alt="Price Shoes" className="login-logo"/>
   <h1>Acceso a entorno de pruebas</h1>
   <p>Proyecto Supabase de prueba. Nunca ingresar credenciales de la aplicación principal.</p>
   <label>Correo de prueba<input type="email" required autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)}/></label>
   <label>Contraseña de prueba<input type="password" required autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
   {error&&<p className="error" role="alert">{error}</p>}
   <button className="action primary" disabled={loading}>{loading?"Ingresando…":"Entrar a la prueba"}</button>
 </form></main>;
}
function App(){
 const [mode,setMode]=useState("day"),[date,setDate]=useState("2026-10-30"),[store,setStore]=useState("Compañía");
 const [rows,setRows]=useState(DEMO?sampleRows:[]),[session,setSession]=useState(null);
 const [loading,setLoading]=useState(!DEMO),[error,setError]=useState("");
 useEffect(()=>{
   if(!supabase)return;
   let mounted=true;
   supabase.auth.getSession().then(({data,error})=>{if(mounted){if(error)setError(error.message);setSession(data?.session||null);setLoading(false);}});
   const {data:{subscription}}=supabase.auth.onAuthStateChange((_event,current)=>{if(mounted)setSession(current);});
   return()=>{mounted=false;subscription.unsubscribe();};
 },[]);
 useEffect(()=>{
  if(!supabase)return;
  if(!session){setRows([]);return;}
  let cancelled=false;
  const load=async()=>{
    setLoading(true);setError("");
    try{
      const{start,end}=periodBounds(mode,date);
      const next=[];
      for(let from=0;from<20000;from+=1000){
        const{data,error}=await supabase.from("operational_metrics_daily")
          .select("operation_date,store_name,ingested,prepared,placed,productivity_pieces,walks_real,walks_target")
          .gte("operation_date",start).lte("operation_date",end)
          .order("operation_date",{ascending:true}).order("store_name",{ascending:true}).range(from,from+999);
        if(error)throw error;
        next.push(...(data||[]));
        if(!data||data.length<1000)break;
        if(from>=19000)throw new Error("La consulta excede el límite de la prueba. Reducir el periodo.");
      }
      if(!cancelled)setRows(next);
    }catch(ex){if(!cancelled){setRows([]);setError(ex.message||"Error de consulta");}}
    finally{if(!cancelled)setLoading(false);}
  };
  load();return()=>{cancelled=true;};
 },[session,mode,date]);
 const availableStores=useMemo(()=>DEMO?demoStores:[...new Set(rows.map(r=>r.store_name))].sort((a,b)=>a.localeCompare(b,"es")),[rows]);
 const periodRows=useMemo(()=>DEMO?visibleInPeriod(rows,mode,date):rows,[rows,mode,date]);
 const summary=useMemo(()=>aggregate(periodRows,store),[periodRows,store]);
 const totals=summary.total;
 const noRows=summary.rows===0;
 const bounds=periodBounds(mode,date);
 if(!DEMO&&!configured)return <main className="setup"><h1>Supabase no configurado</h1><p>La prueba real requiere una base independiente y variables VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY. Por seguridad no se muestran datos ni se conecta a Render.</p></main>;
 if(!DEMO&&!session)return loading?<main className="setup">Comprobando sesión de pruebas…</main>:<Login onSignedIn={setSession}/>;
 return <div className="app">
  <aside className="sidebar">
   <div className="brand"><img src="/price_shoes_white.svg" alt="Price Shoes"/><div><strong>Operaciones Ropa</strong><small>Laboratorio Cloudflare</small></div></div>
   <div className="nav-caption">OPERACIÓN</div>
   <div className="nav-item active">▦ &nbsp; Centro Operativo</div>
   <div className="nav-caption">INFORMACIÓN</div>
   <div className="nav-note">Versión secundaria exclusivamente para comparar diseño y filtros con Render.</div>
   <div className="sidebar-bottom"><strong>Price Shoes</strong><small>Entorno aislado · sin cambios a producción</small></div>
  </aside>
  <main className="main">
   <header className="hero">
    <div><div className="overline">OPERACIÓN / CENTRO OPERATIVO</div><h1>Centro Operativo</h1><p>Consolidado de operación por tienda y periodo</p></div>
    <div className="hero-side"><img src="/price_shoes_white.svg" alt="Price Shoes"/><span className="pilot-tag">PRUEBA SECUNDARIA</span></div>
   </header>
   <div className="notice" role="status">
    <strong>{DEMO?"DATOS SIMULADOS":"SUPABASE DE PRUEBAS"}</strong>
    <span>{DEMO?"Ningún indicador procede de Render ni de archivos reales.":"Consulta autorizada de solo lectura; protección de tienda mediante RLS."}</span>
    {!DEMO&&<button className="small-btn" onClick={()=>supabase.auth.signOut()}>Cerrar sesión</button>}
   </div>
   <section className="filters" aria-label="Filtros de Centro Operativo">
     <div className="filter-block wide"><label>Vista</label><div className="segments">{[["day","Día"],["week","Semana"],["month","Mensual"],["year","Anual"]].map(([key,label])=><button key={key} className={mode===key?"on":""} aria-pressed={mode===key} onClick={()=>setMode(key)}>{label}</button>)}</div></div>
     <div className="filter-block"><label>Fecha de referencia</label><input type="date" value={date} max="2026-12-31" onChange={e=>e.target.value&&setDate(e.target.value)}/></div>
     <div className="filter-block"><label>Tienda</label><select value={store} onChange={e=>setStore(e.target.value)}><option>Compañía</option>{availableStores.map(s=><option key={s}>{s}</option>)}</select></div>
     <button className="small-btn reset" onClick={()=>{setMode("day");setDate("2026-10-30");setStore("Compañía");}}>Restablecer</button>
   </section>
   <div className="summary-line"><span>Periodo: <b>{bounds.start} a {bounds.end}</b></span><span>{loading?"Consultando…":num(summary.rows)+" registros disponibles"}</span></div>
   {error&&<div className="error" role="alert">{error}</div>}
   <section className="kpis" aria-label="Indicadores principales">
    {[
      ["Ingresado",totals.ingested,"Piezas recibidas en el periodo","blue"],
      ["Habilitado",totals.prepared,totals.pct_prepared+"% de lo ingresado","violet"],
      ["Ubicado",totals.placed,totals.pct_placed+"% del habilitado","pink"],
      ["Pend. acondicionar",totals.pending_prepared,"Ingresado menos habilitado","orange"],
      ["Pend. ubicar",totals.pending_placed,"Habilitado menos ubicado","teal"],
      ["Recorridos",totals.walks_real,num(totals.walks_target)+" meta · "+totals.pct_walks+"% cumplimiento","green"]
    ].map(([title,value,note,color])=><article key={title} className={"kpi "+color}><span>{title}</span><strong>{noRows?"—":num(value)}</strong><small>{noRows?"Sin capturas en este periodo":note}</small></article>)}
   </section>
   <section className="panel">
    <div className="panel-head"><div><h2>Reporte completo por tienda</h2><p>Solo periodos con información · encabezados fijos · porcentajes limitados a 100% para la vista</p></div>
     <div className="buttons"><button className="small-btn" disabled={!summary.byStore.length} onClick={()=>exportFile(summary.byStore)}>Exportar CSV</button><button className="small-btn primary" disabled={!summary.byStore.length} onClick={()=>window.print()}>Imprimir piloto / PDF</button></div>
    </div>
    <div className="table-scroll"><table><thead><tr>{["Tienda","Ingresado","Habilitado","Ubicado","Pend. acond.","Pend. ubicar","% Hab./Ing.","% Ubic./Hab.","Recorridos","Meta"].map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>
     {summary.byStore.map(r=><tr key={r.store_name}><td className="store-name">{r.store_name}</td><td>{num(r.ingested)}</td><td>{num(r.prepared)}</td><td>{num(r.placed)}</td><td>{num(r.pending_prepared)}</td><td>{num(r.pending_placed)}</td><td>{r.pct_prepared}%</td><td>{r.pct_placed}%</td><td>{num(r.walks_real)}</td><td>{num(r.walks_target)}</td></tr>)}
     {!summary.byStore.length&&<tr><td colSpan={10} className="empty">No hay registros en el periodo seleccionado. No se generan días sin captura.</td></tr>}
    </tbody></table></div>
   </section>
   <div className="foot-note">Prueba funcional de filtros, agregación y navegación. Los resultados y la impresión son ilustrativos, no sustituye el reporte PDF oficial. Render continúa siendo el sistema principal.</div>
  </main>
 </div>;
}
createRoot(document.getElementById("root")).render(<App/>);
