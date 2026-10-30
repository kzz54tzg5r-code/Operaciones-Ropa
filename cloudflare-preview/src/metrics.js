// Prototipo aislado: NO reutilizar estas reglas sin compararlas con Render.
const iso = d => d.toISOString().slice(0, 10);
const utc = s => new Date(String(s).slice(0,10) + "T12:00:00Z");
export function periodBounds(mode, selectedDate) {
  const d = utc(selectedDate);
  if (Number.isNaN(d.getTime())) throw new Error("Fecha inválida");
  const y=d.getUTCFullYear(),m=d.getUTCMonth();
  let start;
  if (mode==="year") start=new Date(Date.UTC(y,0,1,12));
  else if (mode==="month") start=new Date(Date.UTC(y,m,1,12));
  else if (mode==="week") {
    start=new Date(d);
    const day=(start.getUTCDay()+6)%7;
    start.setUTCDate(start.getUTCDate()-day);
  } else start=new Date(d);
  let end;
  if(mode==="year") end=new Date(Date.UTC(y,11,31,12));
  else if(mode==="month") end=new Date(Date.UTC(y,m+1,0,12));
  else if(mode==="week") {end=new Date(start);end.setUTCDate(end.getUTCDate()+6);}
  else end=new Date(d);
  return {start:iso(start),end:iso(end)};
}
const count = x => Math.max(0,Number(x)||0);
const percent = (a,b)=>b>0?Math.min(100,Math.round(100*a/b)):0;
export function aggregate(rows,store="Compañía") {
  const selected=(rows||[]).filter(r=>store==="Compañía"||r.store_name===store);
  const stores=new Map();
  for(const r of selected) {
    const name=r.store_name||"Sin tienda";
    const a=stores.get(name)||{store_name:name,ingested:0,prepared:0,placed:0,productivity_pieces:0,walks_real:0,walks_target:0};
    for(const key of ["ingested","prepared","placed","productivity_pieces","walks_real","walks_target"])a[key]+=count(r[key]);
    stores.set(name,a);
  }
  const byStore=[...stores.values()].sort((a,b)=>a.store_name.localeCompare(b.store_name,"es"));
  const total={ingested:0,prepared:0,placed:0,productivity_pieces:0,walks_real:0,walks_target:0};
  for(const r of byStore) for(const k of Object.keys(total)) total[k]+=r[k];
  const decorate=r=>({...r,pending_prepared:Math.max(0,r.ingested-r.prepared),
    pending_placed:Math.max(0,r.prepared-r.placed),
    pct_prepared:percent(r.prepared,r.ingested),
    pct_placed:percent(r.placed,r.prepared),
    pct_walks:percent(r.walks_real,r.walks_target)});
  return {total:decorate(total),byStore:byStore.map(decorate),rows:selected.length};
}
export function visibleInPeriod(rows,mode,date) {
  const {start,end}=periodBounds(mode,date);
  return rows.filter(r=>r.operation_date>=start&&r.operation_date<=end);
}
