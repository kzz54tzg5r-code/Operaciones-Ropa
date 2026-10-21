/* V355 · Presentación seleccionada de Centro Operativo.
   Solo refleja controles originales: sin cálculos ni peticiones propias. */
(() => {
 'use strict';
 if (window.__or355Installed) return;
 window.__or355Installed = true;

 const q = selector => document.querySelector(selector);
 const originalTabs = () => [...document.querySelectorAll('#operativoNav > button[data-opview]')];
 const labels = {
  'operations.center':'Centro Operativo',
  'operations.conversion':'Conversión',
  'operations.recovery':'Recuperación $',
  'operations.recovery_store':'Recuperación por tienda',
  'operations.recovery_audit':'Tasa de recuperación',
  'operations.productivity':'Productividad',
  'operations.routes':'Recorridos',
  'operations.score':'Score',
  'operations.alerts':'Alertas',
  'operations.goals':'Metas y tiendas'
 };
 const symbols = {
  'operations.center':'▣', 'operations.conversion':'%', 'operations.recovery':'$',
  'operations.recovery_store':'▤','operations.recovery_audit':'↗',
  'operations.productivity':'▥','operations.routes':'⌁',
  'operations.score':'☆','operations.alerts':'!', 'operations.goals':'⚙'
 };
 let header,sideMenu,contentObserver,queued=false;
 const visible = tab => tab && !tab.hidden && !tab.classList.contains('hidden') &&
  tab.getAttribute('aria-hidden') !== 'true' && getComputedStyle(tab).display !== 'none';
 const selected = () => {
  const center = q('#operativoNav button[data-opview="Centro Ejecutivo"]');
  return !!(center?.classList.contains('active')
   && q('#page-operativo')?.classList.contains('active')
   && !q('#appView')?.classList.contains('hidden'));
 };
 function ensureHeader(){
  if (header || !q('#operativoNav')) return;
  header = document.createElement('div');
  header.className = 'or355-page-header';
  const title = document.createElement('h2');
  const sub = document.createElement('p');
  header.append(title, sub);
  q('#operativoNav').before(header);
 }
 function updateHeader(){
  if (!header) return;
  header.querySelector('h2').textContent = q('#operativoDynamicTitle')?.textContent?.trim() || 'Centro Operativo';
  header.querySelector('p').textContent = q('#operativoDynamicSub')?.textContent?.trim() || 'Operación y desempeño consolidado';
 }
 function ensureSidebar(){
  const sidebar = q('#sidebar');
  if (sideMenu || !sidebar) return;
  sideMenu=document.createElement('nav');
  sideMenu.className='or355-submenu';
  sideMenu.setAttribute('aria-label','Accesos a reportes de Cambios y Muertos');
  const caption=document.createElement('span');
  caption.className='or355-submenu-label';
  caption.textContent='Reportes';
  sideMenu.append(caption);
  for (const tab of originalTabs()){
   const key=tab.dataset.tabKey || tab.dataset.opview;
   const button=document.createElement('button');
   button.type='button';button.className='or355-subtab';
   button.dataset.or355Key=key;
   button.title=labels[key]||tab.dataset.opview||tab.textContent.trim();
   const mark=document.createElement('span');
   mark.className='or355-mark';mark.setAttribute('aria-hidden','true');
   mark.textContent=symbols[key]||'•';
   const text=document.createElement('span');
   text.className='or355-text';text.textContent=labels[key]||tab.textContent.trim();
   button.append(mark,text);
   button.addEventListener('click',()=>{
    const source=originalTabs().find(x=>(x.dataset.tabKey||x.dataset.opview)===key);
    if (visible(source)) source.click();
   });
   sideMenu.append(button);
  }
  (sidebar.querySelector('.profile')||null)?.before(sideMenu);
  if (!sideMenu.parentElement) sidebar.append(sideMenu);
 }
 function updateSidebar(){
  if (!sideMenu) return;
  for(const button of sideMenu.querySelectorAll('.or355-subtab')){
   const key=button.dataset.or355Key;
   const original=originalTabs().find(x=>(x.dataset.tabKey||x.dataset.opview)===key);
   button.hidden=!visible(original);
   const active=!!original?.classList.contains('active');
   button.classList.toggle('active',active);
   if(active)button.setAttribute('aria-current','page');
   else button.removeAttribute('aria-current');
  }
 }
 function getTargets(original){
  const children=[...original.children];
  const titleLike=children.filter(x=>x.classList?.contains('title'));
  const findTitle=(re)=>titleLike.find(x=>re.test(x.textContent||''));
  return [
   ['Resumen',original.querySelector('.compact-monthly-sections')||original.querySelector('.monthly-cross-desktop')],
   ['Recuperación',findTitle(/recuperaci[oó]n por tienda/i)],
   ['Detalle por tienda',findTitle(/detalle operativo/i)],
   ['Gráficos',original.querySelector('.recovery-svg,.combo-svg,.chart-box')],
   ['Exportar',original.querySelector('.report-actions')]
  ].filter(([,target])=>target);
 }
 function updateJumps(){
  const original=q('#operativoDynamicContent .ocl-original');
  if(!original || !selected())return;
  const targets=getTargets(original);
  if(targets.length<2)return;
  let toolbar=original.querySelector(':scope > .or355-jumps');
  if(!toolbar){
   toolbar=document.createElement('nav');toolbar.className='or355-jumps';
   toolbar.setAttribute('aria-label','Secciones del reporte completo');
   original.prepend(toolbar);
  }
  const current=[...toolbar.querySelectorAll('button')].map(x=>x.dataset.or355Target).join('|');
  const desired=targets.map(([,target])=>target===original.querySelector('.compact-monthly-sections')||target===original.querySelector('.monthly-cross-desktop')?'summary':target.textContent?.trim().slice(0,28)||target.tagName).join('|');
  if(current===desired)return;
  toolbar.replaceChildren();
  targets.forEach(([label,target],i)=>{
   const token=target===original.querySelector('.compact-monthly-sections')||target===original.querySelector('.monthly-cross-desktop')?'summary':target.textContent?.trim().slice(0,28)||target.tagName;
   const b=document.createElement('button');b.type='button';b.dataset.or355Target=token;
   b.textContent=label;
   b.addEventListener('click',()=>{
    if(target.isConnected)target.scrollIntoView({behavior:'smooth',block:'start'});
   });
   toolbar.append(b);
  });
 }
 function update(){
  const active=selected();
  document.body.classList.toggle('or355-center-choice',active);
  document.body.classList.toggle('or355-module-choice', !!(q('#page-operativo')?.classList.contains('active') && !q('#appView')?.classList.contains('hidden')));
  ensureHeader();
  ensureSidebar();
  updateHeader();
  updateSidebar();
  if(active)updateJumps();
 }
 function schedule(){
  if(queued)return;queued=true;
  requestAnimationFrame(()=>{queued=false;update();});
 }
 function install(){
  ensureHeader();ensureSidebar();update();
  const tabs=q('#operativoNav');
  if(tabs)new MutationObserver(schedule).observe(tabs,{subtree:true,childList:true,attributes:true,attributeFilter:['class','hidden','style','aria-hidden']});
  const page=q('#page-operativo');
  if(page)new MutationObserver(schedule).observe(page,{attributes:true,attributeFilter:['class','style']});
  const app=q('#appView');
  if(app)new MutationObserver(schedule).observe(app,{attributes:true,attributeFilter:['class']});
  for(const selector of ['#operativoDynamicTitle','#operativoDynamicSub']){
   const node=q(selector);
   if(node)new MutationObserver(schedule).observe(node,{subtree:true,childList:true,characterData:true});
  }
  const content=q('#operativoDynamicContent');
  if(content){
   contentObserver=new MutationObserver(schedule);
   contentObserver.observe(content,{subtree:true,childList:true});
  }
  tabs?.addEventListener('click',schedule);
  window.addEventListener('pageshow',schedule,{passive:true});
  window.addEventListener('resize',schedule,{passive:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
 else install();
})();
