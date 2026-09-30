import express from "express";
import multer from "multer";
import * as XLSX from "xlsx";

const app = express();
app.use(express.json({ limit: "1mb" }));
app.use((req,res,next)=>{
  if(req.path==="/" || req.path.endsWith(".js") || req.path.endsWith(".css") || req.path.startsWith("/api/")){
    res.set("Cache-Control","no-store, no-cache, must-revalidate, proxy-revalidate");
    res.set("Pragma","no-cache");
    res.set("Expires","0");
  }
  next();
});
app.use(express.static("public",{etag:false,lastModified:false,maxAge:0}));

const PORT = process.env.PORT || 10000;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";
const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-6-astra";
const SNAPSHOT_MANIFEST_URL = "https://raw.githubusercontent.com/kzz54tzg5r-code/Operaciones-Ropa/main/data/commercial/manifest.json";
const SNAPSHOT_DATA_URL = "https://raw.githubusercontent.com/kzz54tzg5r-code/Operaciones-Ropa/main/data/commercial/snapshots.json";
let snapshotCache = { manifest:null, data:null, loadedAt:null, error:null };

async function loadReadOnlySnapshot(includeData=false){
  try{
    if(!snapshotCache.manifest){
      const mr=await fetch(SNAPSHOT_MANIFEST_URL,{headers:{"User-Agent":"Operaciones-Ropa-IA-Lab"}});
      if(!mr.ok) throw new Error("Manifest HTTP "+mr.status);
      snapshotCache.manifest=await mr.json();
    }
    if(includeData && !snapshotCache.data){
      const sr=await fetch(SNAPSHOT_DATA_URL,{headers:{"User-Agent":"Operaciones-Ropa-IA-Lab"}});
      if(!sr.ok) throw new Error("Snapshot HTTP "+sr.status);
      snapshotCache.data=await sr.json();
    }
    snapshotCache.loadedAt=new Date().toISOString();
    snapshotCache.error=null;
    return snapshotCache;
  }catch(e){snapshotCache.error=String(e?.message||e);throw e;}
}

function describeNode(value){
  if(Array.isArray(value)) return {type:"array",length:value.length,sampleKeys:value[0]&&typeof value[0]==="object"?Object.keys(value[0]).slice(0,30):[]};
  if(value&&typeof value==="object") return {type:"object",keys:Object.keys(value).slice(0,60)};
  return {type:typeof value};
}


const labUpload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 60 * 1024 * 1024 } });
let labOperationsState = { loaded:false, sourceFile:null, loadedAt:null, rows:[], periods:[], stores:[], sheets:[] };

function labNorm(v){
  return String(v ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase().replace(/[^a-z0-9]+/g," ");
}
function labNum(v){
  if(typeof v==="number" && Number.isFinite(v)) return v;
  const n=Number(String(v??"").replace(/,/g,"").replace(/[^0-9.-]/g,""));
  return Number.isFinite(n)?n:0;
}
function labPick(row,aliases){
  const map={};
  for(const [k,v] of Object.entries(row||{})) map[labNorm(k)]=v;
  for(const a of aliases){
    const k=labNorm(a);
    if(Object.prototype.hasOwnProperty.call(map,k)) return map[k];
  }
  return null;
}
function labDate(v){
  if(v instanceof Date && !isNaN(v)) return v;
  if(typeof v==="number"){
    const d=XLSX.SSF.parse_date_code(v);
    if(d) return new Date(Date.UTC(d.y,d.m-1,d.d));
  }
  const t=String(v??"").trim();
  if(!t) return null;
  const d=new Date(t);
  return isNaN(d)?null:d;
}
function labIsoWeek(d){
  const x=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()));
  const day=x.getUTCDay()||7;
  x.setUTCDate(x.getUTCDate()+4-day);
  const y0=new Date(Date.UTC(x.getUTCFullYear(),0,1));
  const w=Math.ceil((((x-y0)/86400000)+1)/7);
  return x.getUTCFullYear()+"-W"+String(w).padStart(2,"0");
}
function parseLabWorkbook(buffer,filename){
  const wb=XLSX.read(buffer,{type:"buffer",cellDates:true});
  const sheets=wb.SheetNames.filter(n=>{
    const x=labNorm(n);
    return x.startsWith("resultados productividad")||x.startsWith("resultados de productividad");
  });
  if(!sheets.length) throw new Error("No encontré una hoja Resultados de productividad.");
  const out=[];
  for(const sn of sheets){
    const rows=XLSX.utils.sheet_to_json(wb.Sheets[sn],{defval:null,raw:true});
    for(const r of rows){
      const store=String(labPick(r,["Tienda","Sucursal"])??"").trim();
      const name=String(labPick(r,["Nombre","Usuario","Colaborador"])??"").trim();
      const occurrence=String(labPick(r,["Ocurrencia","Occurrence"])??"").trim();
      const date=labDate(labPick(r,["Fecha"]));
      const activity=String(labPick(r,["Actividad Realizada","Actividad","Proceso"])??"").trim();
      const pieces=labNum(labPick(r,["Número de Piezas","Numero de Piezas","Piezas","Pzs"]));
      let dev=labNum(labPick(r,["Dev_Pzs","Dev Pzs","Devoluciones","Devolucion Pzs"]));
      let muertos=labNum(labPick(r,["Muertos"]));
      let cajas=labNum(labPick(r,["Cajas"]));
      let probador=labNum(labPick(r,["Probado","Probador","Aduana"]));
      let habilitado=labNum(labPick(r,["Habilitado","Acondicionado"]));
      let ubicado=labNum(labPick(r,["Ubicado"]));
      const recorridos=labNum(labPick(r,["RECORRIDOS","Recorridos"]));
      const a=labNorm(activity);
      if(pieces){
        if(!dev && (a.includes("dev")||a.includes("devol"))) dev=pieces;
        else if(!muertos && a.includes("muerto")) muertos=pieces;
        else if(!cajas && a.includes("caja")) cajas=pieces;
        else if(!probador && (a.includes("probador")||a.includes("probado")||a.includes("aduana"))) probador=pieces;
        else if(!habilitado && (a.includes("habilit")||a.includes("acondicion"))) habilitado=pieces;
        else if(!ubicado && a.includes("ubicad")) ubicado=pieces;
      }
      if(!store && !name && !date && !(dev||muertos||cajas||probador||habilitado||ubicado||recorridos)) continue;
      out.push({
        store,name,occurrence,
        date:date?date.toISOString().slice(0,10):"",
        week:date?labIsoWeek(date):"",
        activity,dev,muertos,cajas,probador,habilitado,ubicado,recorridos
      });
    }
  }
  if(!out.length) throw new Error("Las hojas operativas no contienen registros utilizables.");
  return {
    loaded:true,
    sourceFile:filename,
    loadedAt:new Date().toISOString(),
    rows:out,
    periods:[...new Set(out.map(r=>r.week).filter(Boolean))].sort(),
    stores:[...new Set(out.map(r=>r.store).filter(Boolean))].sort(),
    sheets
  };
}
function labFilter(rows,store,period){
  let x=rows||[];
  if(store&&store!=="Compañía") x=x.filter(r=>labNorm(r.store)===labNorm(store));
  if(period&&period!=="all") x=x.filter(r=>r.week===period);
  return x;
}
function labSummary(rows){
  const sum=k=>rows.reduce((a,r)=>a+labNum(r[k]),0);
  const dev=sum("dev"),muertos=sum("muertos"),cajas=sum("cajas"),probador=sum("probador"),habilitado=sum("habilitado"),ubicado=sum("ubicado");
  const ingresos=dev+muertos+cajas+probador;
  const recSeen=new Set();
  let recorridos=0;
  for(const r of rows){
    const key=r.occurrence?String(r.occurrence):[r.store,r.date,r.activity,r.recorridos].join("|");
    if(r.recorridos && !recSeen.has(key)){recorridos+=r.recorridos;recSeen.add(key);}
  }
  const personDays=new Set(rows.filter(r=>r.name&&r.date).map(r=>labNorm(r.name)+"|"+r.date)).size;
  const processed=dev+muertos+cajas+probador+habilitado+ubicado;
  return {
    ingresos,dev,muertos,cajas,probador,habilitado,ubicado,
    pendienteAcondicionar:Math.max(ingresos-habilitado,0),
    pendienteUbicar:Math.max(habilitado-ubicado,0),
    pctHabilitadoIngresos:ingresos?habilitado/ingresos*100:0,
    pctUbicadoHabilitado:habilitado?ubicado/habilitado*100:0,
    pctUbicadoIngresos:ingresos?ubicado/ingresos*100:0,
    recorridos,
    productivity:personDays?processed/personDays:0,
    personDays,processed,rows:rows.length
  };
}

const demoData = {
  proyecto: "Operaciones Ropa - IA Lab",
  estado: "aislado",
  reportes: ["Cambios y Muertos", "Operaciones"],
  tiendas: [
    "Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte","Ixtapaluca",
    "Querétaro","Centro","Olivar","León","Puebla","Puebla Sur",
    "Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac"
  ],
  reglas: {
    productividadMeta: 784,
    recorridosMetaSemanal: 47,
    scoreIntegral: "40% Conversión, 40% Productividad, 20% Recorridos"
  }
};

function demoReply(message) {
  const q = String(message || "").toLowerCase();
  if (q.includes("tienda") || q.includes("tiendas")) {
    return "El laboratorio reconoce las 17 tiendas del proyecto. Cuando conectemos la base real, podré filtrar por tienda, periodo, sección y ubicación sin tocar Producción.";
  }
  if (q.includes("sell") || q.includes("inventario")) {
    return "En este laboratorio el análisis de Sell Through está en modo demostración. La conexión real se hará con una fuente de solo lectura para evitar cualquier modificación en la operación actual.";
  }
  if (q.includes("muerto") || q.includes("cambio")) {
    return "Cambios y Muertos está definido como uno de los dos reportes principales del laboratorio. La siguiente fase es conectar una copia o endpoint de solo lectura de sus datos.";
  }
  if (q.includes("operacion") || q.includes("productividad") || q.includes("recorr")) {
    return "Operaciones está separado como el segundo reporte principal. Tengo registradas como referencia la meta de productividad de 784 pzas/día y 47 recorridos por semana; en la conexión final estos valores vendrán de la configuración.";
  }
  return "Este es el Asistente IA de laboratorio. Está aislado de la app principal: puedo probar navegación, preguntas operativas y la integración con OpenAI sin modificar la versión de producción.";
}

function extractOutputText(payload) {
  if (payload?.output_text) return payload.output_text;
  const parts = [];
  for (const item of payload?.output || []) {
    for (const c of item?.content || []) {
      if (c?.type === "output_text" && c?.text) parts.push(c.text);
    }
  }
  return parts.join("\n").trim();
}

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    app: "Operaciones Ropa IA Lab",
    mode: OPENAI_API_KEY ? "openai" : "demo",
    productionTouched: false
  });
});

app.get("/api/context", (_req, res) => {
  res.json({ ...demoData, aiEnabled: Boolean(OPENAI_API_KEY), model: OPENAI_MODEL });
});

app.get("/api/lab/snapshot/status",async(_req,res)=>{
  try{
    const s=await loadReadOnlySnapshot(false),m=s.manifest||{};
    res.json({ok:true,mode:"read-only-copy",source:"GitHub snapshot main",productionTouched:false,manifestUpdatedAt:m.updated_at||null,capacities:Array.isArray(m.capacities)?m.capacities.length:0,pdfs:Array.isArray(m.pdfs)?m.pdfs.length:0,sales:Array.isArray(m.sales)?m.sales.length:0,stores:[...new Set((m.pdfs||[]).map(x=>x.store).filter(Boolean))].sort(),loadedAt:s.loadedAt});
  }catch(e){res.status(502).json({ok:false,mode:"read-only-copy",productionTouched:false,error:String(e?.message||e)});}
});

app.get("/api/lab/snapshot/inspect",async(_req,res)=>{
  try{
    const s=await loadReadOnlySnapshot(true),data=s.data,out={root:describeNode(data)};
    if(data&&typeof data==="object"&&!Array.isArray(data)) out.children=Object.fromEntries(Object.entries(data).slice(0,30).map(([k,v])=>[k,describeNode(v)]));
    else if(Array.isArray(data)) out.first=data.length?describeNode(data[0]):null;
    res.json({ok:true,mode:"read-only-copy",productionTouched:false,loadedAt:s.loadedAt,inspection:out});
  }catch(e){res.status(502).json({ok:false,mode:"read-only-copy",productionTouched:false,error:String(e?.message||e)});}
});


app.get("/api/lab/operations/status",(_req,res)=>{
  const st=labOperationsState;
  res.json({
    ok:true,productionTouched:false,loaded:st.loaded,sourceFile:st.sourceFile,
    loadedAt:st.loadedAt,periods:st.periods,stores:st.stores,sheets:st.sheets,rowCount:st.rows.length
  });
});

app.post("/api/lab/operations/upload",labUpload.single("file"),(req,res)=>{
  try{
    if(!req.file) return res.status(400).json({ok:false,error:"Selecciona un archivo Excel."});
    labOperationsState=parseLabWorkbook(req.file.buffer,req.file.originalname);
    const latest=labOperationsState.periods.at(-1)||"all";
    res.json({
      ok:true,productionTouched:false,sourceFile:labOperationsState.sourceFile,
      loadedAt:labOperationsState.loadedAt,sheets:labOperationsState.sheets,
      stores:labOperationsState.stores,periods:labOperationsState.periods,latestPeriod:latest,
      summary:labSummary(labFilter(labOperationsState.rows,"Compañía",latest))
    });
  }catch(e){
    res.status(400).json({ok:false,productionTouched:false,error:String(e?.message||e)});
  }
});

app.get("/api/lab/operations/summary",(req,res)=>{
  if(!labOperationsState.loaded){
    return res.status(404).json({ok:false,productionTouched:false,error:"No hay copia operativa cargada en el laboratorio."});
  }
  const period=String(req.query.period||labOperationsState.periods.at(-1)||"all");
  const store=String(req.query.store||"Compañía");
  const rows=labFilter(labOperationsState.rows,store,period);
  const byStore={};
  for(const st of labOperationsState.stores){
    const sr=labFilter(labOperationsState.rows,st,period);
    if(sr.length) byStore[st]=labSummary(sr);
  }
  res.json({
    ok:true,productionTouched:false,sourceFile:labOperationsState.sourceFile,
    loadedAt:labOperationsState.loadedAt,period,store,periods:labOperationsState.periods,
    stores:labOperationsState.stores,summary:labSummary(rows),byStore
  });
});

app.post("/api/chat", async (req, res) => {
  const message = String(req.body?.message || "").trim();
  if (!message) return res.status(400).json({ error: "Escribe una pregunta." });

  if (!OPENAI_API_KEY) {
    return res.json({ mode: "demo", answer: demoReply(message) });
  }

  const instructions = [
    "Eres el Asistente IA del laboratorio aislado de Operaciones Ropa.",
    "No afirmes haber modificado Producción.",
    "El sistema tiene dos reportes principales: Cambios y Muertos, y Operaciones.",
    "Responde en español, de forma ejecutiva y clara.",
    "Cuando no haya datos reales disponibles, dilo expresamente y no inventes cifras."
  ].join(" ");

  try {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${OPENAI_API_KEY}`
      },
      body: JSON.stringify({
        model: OPENAI_MODEL,
        instructions,
        input: message
      })
    });

    const payload = await response.json();
    if (!response.ok) {
      return res.status(response.status).json({
        error: payload?.error?.message || "La API de OpenAI devolvió un error."
      });
    }

    res.json({
      mode: "openai",
      answer: extractOutputText(payload) || "La API respondió sin texto."
    });
  } catch (error) {
    res.status(500).json({ error: "No se pudo conectar con OpenAI.", detail: String(error?.message || error) });
  }
});

app.listen(PORT, () => {
  console.log(`Operaciones Ropa IA Lab escuchando en puerto ${PORT}`);
});
