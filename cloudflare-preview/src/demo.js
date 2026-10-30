// SOLO datos artificiales. No incluyen datos internos de ninguna tienda.
export const stores=[
  "Iztapalapa","Vallejo","Ecatepec","Toluca","Arco Norte",
  "Ixtapaluca","Querétaro","Centro","Olivar","León","Puebla","Puebla Sur",
  "Aguascalientes","Veracruz","Naucalpan","Miravalle","Atemajac"
];
export const sampleRows=(()=>{
  const rows=[];
  for (let month=8;month<=9;month++) {
    const last=month===9?30:30; // Septiembre y octubre, hasta el 30
    for(let day=1;day<=last;day++){
      const date=new Date(Date.UTC(2026,month,day,12));
      const iso=date.toISOString().slice(0,10);
      const wd=(date.getUTCDay()+6)%7;
      const target=wd<=2?5:8;
      stores.forEach((name,i)=>{
        const ingested=180+((day*41+i*69+month*23)%470);
        const prepared=Math.round(ingested*(0.73+((i+day)%14)/100));
        const placed=Math.round(prepared*(0.77+((i+day*3)%17)/100));
        rows.push({operation_date:iso,store_name:name,
          ingested,prepared,placed,
          productivity_pieces:470+((i*61+day*47)%530),
          walks_real:Math.min(target,target-1+((i+day)%2)),
          walks_target:target});
      });
    }
  }
  return rows;
})();
