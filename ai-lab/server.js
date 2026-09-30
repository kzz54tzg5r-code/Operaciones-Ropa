import express from "express";

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
