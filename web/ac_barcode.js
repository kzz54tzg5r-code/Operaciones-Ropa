/* Etiquetas Price Shoes: código = ID(7) + variante/talla(2) + terminador.
 * Basado en ejemplos 133408714$, 133408726$, 122400022$, 122400018$.
 * Nunca inventar una talla para códigos desconocidos.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.ACBarcode=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  const ageSizes=Object.freeze({"14":"7/8","18":"9/10","22":"11/12","26":"13/14"});
  function parse(raw){
    const original=String(raw??"").trim();
    if(!original||original.length>90)return {valid:false,raw:original,reason:"Código vacío o demasiado largo"};
    // Los lectores pueden añadir un prefijo de etiqueta OI25/OI26 que no
    // pertenece al ID. El dato de las fotos empieza por siete dígitos.
    const cleaned=original.toUpperCase().replace(/\s+/g,"");
    const single=cleaned.match(/^(\d{7})$/);
    if(single)return {valid:true,raw:original,modelId:single[1],size:null,sizeCode:null,needsReview:false};
    const labeled=cleaned.match(/^(?:(?:O[I1]\d{2})|0)?(\d{7})(\d{2})(?:\$|S)?$/);
    if(!labeled)return {valid:false,raw:original,reason:"Formato de etiqueta desconocido; verifica el ID impreso"};
    const size=ageSizes[labeled[2]]||null;
    return {valid:true,raw:original,modelId:labeled[1],sizeCode:labeled[2],
            size,needsReview:!size};
  }
  function sizeToken(value){
    return String(value??"").toUpperCase().trim()
      .replace(/AÑOS?|ANOS?|YEARS?|TALLA|SIZE/g,"")
      .replace(/\s+/g,"").replace(/[–—-]/g,"/");
  }
  function resolveSize(barcode, availableSizes){
    // Los sufijos de barra NO tienen equivalencia universal.
    // Se aceptan sólo coincidencias que existan en el corte de Capacidades
    // para el ID y tienda consultados, nunca una talla fabricada por el lector.
    const sizes=Array.isArray(availableSizes)?availableSizes.map(x=>String(x)):[];
    if(!barcode?.valid||!barcode.sizeCode||!sizes.length)
      return {size:null,status:"not_available"};
    const candidateTokens=new Set([sizeToken(barcode.sizeCode)]);
    if(barcode.size)candidateTokens.add(sizeToken(barcode.size));
    const candidates=sizes.filter(x=>candidateTokens.has(sizeToken(x)));
    if(candidates.length===1)return {size:candidates[0],status:"matched"};
    if(candidates.length>1)return {size:null,status:"ambiguous"};
    return {size:null,status:"unknown_code"};
  }
  return {parse,ageSizes,resolveSize,sizeToken};
});
