/* Escáner AC: cámara trasera + ZXing 1D, con alternativa BarcodeDetector.
 * ZXing es MIT, versión fija para decodificar Code 128 / EAN en Safari iOS.
 * El video no se transmite a servidores, sólo se procesa en el navegador.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.ACScanner=api;
})(typeof window!=="undefined"?window:null,function(){
"use strict";
const CDNS=[
 // Principal: biblioteca incluida en Operaciones Ropa, sin CDN ni terceros.
 "/static/ac_zxing_browser_0_2_1.min.js?v=416",
 // Respaldo si el servidor está sirviendo una versión sin el archivo local.
 "https://cdn.jsdelivr.net/npm/@zxing/browser@0.2.1/umd/zxing-browser.min.js",
 "https://unpkg.com/@zxing/browser@0.2.1/umd/zxing-browser.min.js"
];
let loading=null;
function loadScript(src){
 return new Promise((resolve,reject)=>{
   const script=document.createElement("script");
   script.src=src;script.async=true;script.referrerPolicy="no-referrer";
   const timer=setTimeout(()=>{script.remove();reject(Error("Tiempo de carga excedido"))},12000);
   script.onload=()=>{clearTimeout(timer);resolve()};
   script.onerror=()=>{clearTimeout(timer);script.remove();reject(Error("No se pudo cargar el lector"))};
   document.head.append(script);
 });
}
async function loadReader(){
 if(window.ZXingBrowser?.BrowserMultiFormatOneDReader)return window.ZXingBrowser;
 if(loading)return loading;
 loading=(async()=>{
   for(const url of CDNS){
     try{
       await loadScript(url);
       if(window.ZXingBrowser?.BrowserMultiFormatOneDReader)return window.ZXingBrowser;
     }catch(e){/* intentar la siguiente fuente */}
   }
   throw Error("No se pudo cargar el lector de códigos; revisa la conexión");
 })();
 try{return await loading}finally{loading=null}
}
function create({video,overlay,status,torchButton,onCode}){
 let stream=null,readerControls=null,frameId=0,generation=0,torch=false;
 let detector=null,busy=false;
 function statusText(message){status.textContent=message}
 function stop(){
   ++generation;
   if(frameId){cancelAnimationFrame(frameId);frameId=0}
   if(readerControls){try{readerControls.stop()}catch(e){}readerControls=null}
   if(stream){for(const track of stream.getTracks())try{track.stop()}catch(e){}stream=null}
   video.pause();
   video.srcObject=null;
   detector=null;busy=false;torch=false;
   torchButton.hidden=true;
   overlay.hidden=true;
   document.body.style.overflow="";
 }
 function accept(text){
   if(busy)return;
   busy=true;
   try{
     const approved=onCode(String(text??""));
     if(approved===true){stop();return}
   }catch(e){statusText("Código no reconocido. Intenta enfocarlo de nuevo.")}
   busy=false;
 }
 async function nativeLoop(mine){
   if(mine!==generation||overlay.hidden||!detector)return;
   if(video.readyState>=2){
     try{
       const codes=await detector.detect(video);
       if(mine!==generation)return;
       for(const c of codes){if(c.rawValue){accept(c.rawValue);break}}
     }catch(e){/* seguir intentando, algunas imágenes son borrosas */}
   }
   if(mine===generation)frameId=requestAnimationFrame(()=>nativeLoop(mine));
 }
 async function open(){
   if(!overlay.hidden)return;
   ++generation;const mine=generation;
   overlay.hidden=false;document.body.style.overflow="hidden";
   statusText("Solicitando permiso para la cámara trasera…");
   try{
     if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)
       throw Error("La cámara requiere HTTPS y permisos del navegador");
     stream=await navigator.mediaDevices.getUserMedia({
       audio:false,video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}}
     });
     if(mine!==generation){for(const t of stream.getTracks())t.stop();return}
     video.srcObject=stream;await video.play();
     if(mine!==generation)return;
     const track=stream.getVideoTracks()[0];
     const caps=track?.getCapabilities?.();
     torchButton.hidden=!caps?.torch;
     torch=false;
     statusText("Centra las barras horizontales dentro del recuadro. Se leerán automáticamente.");
     try{
       const lib=await loadReader();
       if(mine!==generation)return;
       const reader=new lib.BrowserMultiFormatOneDReader();
       readerControls=await reader.decodeFromStream(stream,video,(result)=>{
         if(result?.getText)accept(result.getText());
       });
     }catch(error){
       if(mine!==generation)return;
       if("BarcodeDetector" in window){
         try{
           detector=new BarcodeDetector({formats:["code_128","code_39","ean_13","ean_8","itf","upc_a"]});
           statusText("Lector alternativo activo. Acerca la etiqueta al centro.");
           frameId=requestAnimationFrame(()=>nativeLoop(mine));
           return;
         }catch(e){/* no hay alternativa nativa en Safari */}
       }
       statusText(error.message+". Puedes tomar una foto o escribir el ID.");
     }
   }catch(error){
     if(mine!==generation)return;
     if(stream){for(const t of stream.getTracks())try{t.stop()}catch(e){}stream=null}
     video.srcObject=null;
     const name=String(error.name||"");
     statusText(/NotAllowed|Permission/.test(name)
       ?"No hay permiso de cámara. Autorízalo en Safari o usa captura manual."
       :/NotFound/.test(name)
       ?"No se encontró una cámara disponible."
       :"No se pudo abrir la cámara: "+(error.message||name));
     // Mantener el panel abierto para que usuario use foto/manual.
   }
 }
 async function scanFile(file){
   if(!file)return;
   const mine=generation;
   try{
     statusText("Leyendo fotografía de la etiqueta…");
     const lib=await loadReader();
     if(mine!==generation)return;
     const reader=new lib.BrowserMultiFormatOneDReader();
     const uri=URL.createObjectURL(file);
     try{
       const result=await reader.decodeFromImageUrl(uri);
       if(mine===generation)accept(result.getText());
     }finally{URL.revokeObjectURL(uri)}
     if(mine===generation&&!overlay.hidden)statusText("No se reconoció un ID válido. Prueba otra foto.");
   }catch(e){
     if(mine===generation)statusText("No pude leer la foto. Enfoca solo el código y prueba de nuevo.");
   }
 }
 async function switchTorch(){
   const track=stream?.getVideoTracks()[0];
   if(!track||!track.getCapabilities?.().torch)return;
   try{await track.applyConstraints({advanced:[{torch:!torch}]});torch=!torch;
      torchButton.textContent=torch?"🔦 Apagar linterna":"🔦 Encender linterna";
   }catch(e){statusText("La linterna no está disponible en este dispositivo.")}
 }
 return {open,stop,scanFile,switchTorch,statusText};
}
return {create,loadReader};
});
