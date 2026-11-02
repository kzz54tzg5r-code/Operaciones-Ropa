/* V407: semanas en pantalla con S, ancho de pestañas medido por su texto.
   Mantiene W en option.value, consultas de backend, localStorage e ISO 8601.
*/
(()=>{
'use strict';
if(window.__v407VisualLabels)return;
window.__v407VisualLabels=true;
const navs=['#operativoNav','#analysisNav','#v200OperationTabs'];
const week=/\b((?:19|20)\d{2})-W([0-5]\d)\b/g;
const short=/\bW([0-5]\d)\b/g;
const format=value=>String(value||'').replace(week,'$1-S$2').replace(short,'S$1');
let measureCtx=null;
function textWidth(value){
 if(!measureCtx){const canvas=document.createElement('canvas');measureCtx=canvas.getContext('2d')}
 if(!measureCtx)return String(value).length*7;
 measureCtx.font='800 11px Arial';
 return measureCtx.measureText(String(value)).width;
}
function label(button){
 const node=button.querySelector('.rt-tab-label,.v203-tab-label');
 return (node?.textContent||button.dataset.tabLabel||button.textContent||'').trim().replace(/\s+/g,' ');
}
function sizeTabs(){
 navs.forEach(selector=>{
  const container=document.querySelector(selector);
  if(!container)return;
  container.querySelectorAll(':scope > button').forEach(b=>{
   if(b.hidden||b.classList.contains('hidden'))return;
   const title=label(b);
   if(!title)return;
   // Dejar margen para icono y texto (hasta dos renglones).
   const natural=textWidth(title)+24;
   const width=Math.ceil(Math.max(106,Math.min(211,natural)));
   b.style.setProperty('--v407-tab-width',width+'px');
   b.title=title;
  });
 });
}
function transformText(node){
 if(node.nodeType!==3)return;
 const parent=node.parentElement;
 if(!parent||parent.closest('script,style,textarea,code,pre,[contenteditable="true"]'))return;
 const raw=node.nodeValue||'';
 if(!raw.includes('W'))return;
 const converted=format(raw);
 if(converted!==raw)node.nodeValue=converted;
}
function transformTree(root){
 if(!root||!root.isConnected)return;
 if(root.nodeType===3){transformText(root);return;}
 if(root.nodeType!==1)return;
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 let current;
 while((current=walker.nextNode()))transformText(current);
}
let tabFrame=0;
function scheduleTabs(){
 if(tabFrame)return;
 tabFrame=requestAnimationFrame(()=>{tabFrame=0;sizeTabs();});
}
function initialize(){
 const root=document.querySelector('#appView');
 if(!root)return;
 transformTree(root);
 sizeTabs();
 const observer=new MutationObserver(mutations=>{
  let resized=false;
  for(const m of mutations){
   if(m.type==='characterData'){
    transformText(m.target);
    if(m.target.parentElement?.closest(navs.join(',')))resized=true;
    continue;
   }
   for(const added of m.addedNodes){
    if(added.nodeType!==1&&added.nodeType!==3)continue;
    transformTree(added);
    if(added.nodeType===1&&
       (added.matches?.(navs.join(','))||added.closest?.(navs.join(','))||
        added.querySelector?.(navs.join(','))))resized=true;
   }
   if(m.target?.closest?.(navs.join(',')))resized=true;
  }
  if(resized)scheduleTabs();
 });
 observer.observe(root,{subtree:true,childList:true,characterData:true});
 window.addEventListener('resize',scheduleTabs,{passive:true});
 document.fonts?.ready?.then(scheduleTabs).catch(()=>{});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});
else initialize();
})();
