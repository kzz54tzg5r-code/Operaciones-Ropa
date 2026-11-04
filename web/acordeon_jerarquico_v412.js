/* V412 · Acordeón Comercial opción 4 — lectura jerárquica real.
   Mueve nodos existentes; no reemplaza contenido/API/listeners y respeta permisos. */
(()=>{
 'use strict';
 if(window.__or412AccordionHierarchical)return;
 window.__or412AccordionHierarchical=true;
 const names=['Resumen general','Secciones','Marcas campeonas','Rubros campeones','Ubicaciones','Modelos 80/20','Tipo de catálogo'];
 const query=()=>document.getElementById('accordion');
 let scheduled=false;
 function upgrade(){
  const root=query();
  if(!root||root.querySelector(':scope > .or412-accordion-layout'))return;
  const items=[...root.querySelectorAll(':scope > .acc')];
  if(items.length!==7)return;
  // Reconstruir solo al completarse una respuesta real de la API.
  const layout=document.createElement('div');
  layout.className='or412-accordion-layout';
  const sidebar=document.createElement('nav');
  sidebar.className='or412-accordion-sidebar';
  sidebar.setAttribute('aria-label','Ruta de consulta del Acordeón Comercial');
  const sidebarTitle=document.createElement('div');
  sidebarTitle.className='or412-accordion-heading';
  sidebarTitle.textContent='Ruta de consulta';
  sidebar.appendChild(sidebarTitle);
  const detail=document.createElement('section');
  detail.className='or412-accordion-detail';
  detail.setAttribute('aria-label','Detalle comercial seleccionado');
  const buttons=[];
  let selected=items.findIndex(x=>x.classList.contains('open'));
  if(selected<0)selected=0;
  function choose(index,focus=false){
    items.forEach((item,i)=>{
      const active=i===index;
      item.classList.toggle('open',active);
      item.classList.toggle('or412-selected',active);
      item.setAttribute('aria-hidden',active?'false':'true');
      const marker=item.querySelector(':scope > button > span');
      if(marker)marker.textContent=active?'−':'+';
    });
    buttons.forEach((button,i)=>{
      const active=i===index;
      button.classList.toggle('or412-selected',active);
      button.setAttribute('aria-current',active?'step':'false');
      button.setAttribute('aria-pressed',active?'true':'false');
      button.tabIndex=active?0:-1;
    });
    if(focus)detail.focus({preventScroll:true});
  }
  items.forEach((item,i)=>{
    item.dataset.or412Title=names[i];
    detail.appendChild(item);
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='or412-accordion-step';
    btn.innerHTML='<span class="or412-step-number">'+(i+1)+'</span><span class="or412-step-label"></span>';
    btn.querySelector('.or412-step-label').textContent=names[i];
    btn.addEventListener('click',()=>choose(i,true));
    btn.addEventListener('keydown',event=>{
      if(event.key!=='ArrowDown'&&event.key!=='ArrowUp')return;
      event.preventDefault();
      const next=(i+(event.key==='ArrowDown'?1:items.length-1))%items.length;
      choose(next);
      buttons[next]?.focus();
    });
    sidebar.appendChild(btn);
    buttons.push(btn);
  });
  const caption=document.createElement('div');
  caption.className='or412-accordion-caption';
  caption.textContent='Resumen general → detalle comercial';
  sidebar.appendChild(caption);
  detail.tabIndex=-1;
  layout.append(sidebar,detail);
  root.replaceChildren(layout);
  root.classList.add('or412-accordion-hierarchy');
  choose(selected);
 }
 function schedule(){
  if(scheduled)return;
  scheduled=true;
  requestAnimationFrame(()=>{scheduled=false;upgrade()});
 }
 function init(){
  const root=query();if(!root)return;
  new MutationObserver(changes=>{
   if(changes.some(c=>c.type==='childList'))schedule();
  }).observe(root,{childList:true});
  schedule();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
 else init();
})();
