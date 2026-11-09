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
 // Versión fijada de ZXing para iPhone; requiere red al cargar por primera vez.
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
 let detector=null,busy=false,lastNativeScan=0;
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
   if(video.readyState>=2&&performance.now()-lastNativeScan>=160){
     lastNativeScan=performance.now();
     try{
       const codes=await detector.detect(video);
       if(mine!==generation)return;
       for(const c of codes){if(c.rawValue){accept(c.rawValue);break}}
     }catch(e){/* seguir intentando, algunas imágenes son borrosas */}
   }
   if(mine===generation&&!overlay.hidden)frameId=requestAnimationFrame(()=>nativeLoop(mine));
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
       audio:false,video:{facingMode:{ideal:"environment"},width:{ideal:1920},height:{ideal:1080}}
     });
     if(mine!==generation){for(const t of stream.getTracks())t.stop();return}
     video.srcObject=stream;await video.play();
     if(mine!==generation)return;
     const track=stream.getVideoTracks()[0];
     const caps=track?.getCapabilities?.();
     torchButton.hidden=!caps?.torch;
     torch=false;
     if(caps?.focusMode?.includes?.("continuous")){
       try{await track.applyConstraints({advanced:[{focusMode:"continuous"}]})}catch(e){}
     }
     statusText("Escaneo automático activado. Apunta a las barras verticales; no necesitas tomar una foto.");
     // Priorizar la lectura nativa, sin red ni retrasos de descarga.
     if(typeof window.BarcodeDetector==="function"){
       try{
         const supported=await window.BarcodeDetector.getSupportedFormats();
         if(mine!==generation)return;
         if(supported.includes("code_128")){
           detector=new window.BarcodeDetector({formats:["code_128"]});
           statusText("Leyendo CODE128 automáticamente… Mantén la etiqueta centrada y enfocada.");
           frameId=requestAnimationFrame(()=>nativeLoop(mine));
           return;
         }
       }catch(e){/* El navegador no admite este formato; usar ZXing */}
     }
     statusText("Activando el lector CODE128 continuo…");
     try{
       const lib=await loadReader();
       if(mine!==generation)return;
       const reader=new lib.BrowserMultiFormatOneDReader();
       readerControls=await reader.decodeFromStream(stream,video,(result)=>{
         if(result?.getText)accept(result.getText());
       });
       if(mine!==generation){readerControls?.stop?.();return}
       statusText("Lectura automática activa. Centra la etiqueta con las barras verticales.");
     }catch(error){
       if(mine!==generation)return;
       if(typeof window.BarcodeDetector==="function"){
         try{
           detector=new window.BarcodeDetector({formats:["code_128"]});
           statusText("Lector alternativo activo. Acerca la etiqueta al centro.");
           frameId=requestAnimationFrame(()=>nativeLoop(mine));
           return;
         }catch(e){/* no hay alternativa nativa en Safari */}
       }
       statusText(error.message+". La lectura automática no pudo activarse; puedes escribir el ID.");
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
     // Mantener el panel abierto para captura manual.
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
