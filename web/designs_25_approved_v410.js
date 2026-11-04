/* Operaciones Ropa · diseños finales autorizados · V410
   Instrumentación de navegación exclusivamente visual.
   No intercepta formularios, clics de negocio, API, permisos ni cálculos. */
(function(){
  'use strict';
  const APPROVED=Object.freeze([
    ['operations.center','1','Compacto operativo'],
    ['operations.conversion','2','Comparativo de periodos'],
    ['operations.recovery','2','Comparativo de periodos'],
    ['operations.recovery_store','2','Comparativo de periodos'],
    ['operations.recovery_audit','2','Calidad y alertas'],
    ['operations.productivity','2','Comparativo y avance'],
    ['operations.capture','2','Tarjeta de desempeño'],
    ['operations.routes','2','Avance y cumplimiento'],
    ['operations.upload','2','Proceso guiado y validaciones'],
    ['operations.goals','2','Gestión por módulos'],
    ['operations.bonuses','2','Gestión por módulos'],
    ['commercial.macro','2','Inventario y capacidad'],
    ['commercial.stores','2','Inventario, ventas y participación'],
    ['commercial.sections','2','Desempeño integral'],
    ['commercial.areas','2','Desempeño integral'],
    ['commercial.pareto','2','Análisis integral'],
    ['commercial.slow','2','Análisis integral'],
    ['commercial.zero','2','Análisis integral'],
    ['commercial.sales','3','Comparativo por periodo'],
    ['commercial.sell','2','Análisis integral por bloques'],
    ['commercial.accordion','4','Lectura jerárquica'],
    ['commercial.subcat','actual','Actual optimizado'],
    ['commercial.lingerie_checklist','2','Comparativo paralelo'],
    ['commercial.upload','2','Carga guiada y validaciones'],
    ['commercial.more','2','Centro de herramientas']
  ].map(([key,option,label])=>Object.freeze({key,option,label})));
  const approvedKeys=new Set(APPROVED.map(x=>x.key));
  window.OR410_APPROVED_DESIGNS=APPROVED;
  const byOperationalView={
    'centro ejecutivo':'operations.center',
    'centro operativo':'operations.center',
    'conversion':'operations.conversion',
    'recuperacion economica':'operations.recovery',
    'recuperacion por tienda':'operations.recovery_store',
    'tasa de recuperacion':'operations.recovery_store',
    'tasa de recuperacion · revision':'operations.recovery_audit',
    'productividad por colaborador':'operations.productivity',
    'cargar productividad':'operations.capture',
    'cumplimiento de recorridos':'operations.routes',
    'carga de datos':'operations.upload',
    'metas y tiendas':'operations.goals'
  };
  const byCommercialSub={
    'macro':'commercial.macro',
    'stores':'commercial.stores',
    'sections':'commercial.sections',
    'areas':'commercial.areas',
    'accordion':'commercial.accordion',
    'lingerie-checklist':'commercial.lingerie_checklist',
    'analysis-upload':'commercial.upload',
    'more':'commercial.more',
    'sell':'commercial.sell'
  };
  const norm=x=>String(x||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim();
  function identify(){
    const analysis=document.querySelector('#analysisNav:not(.hidden) .switch.active:not(.hidden)');
    const operative=document.querySelector('#operativoNav:not(.hidden) .switch.active:not(.hidden)');
    const activeMain=document.querySelector('#sidebar [data-main].active')?.dataset.main;
    if(activeMain==='analysis'||(analysis&&!operative)){
      const sub=analysis?.dataset.sub||'';
      return byCommercialSub[sub]||'commercial.macro';
    }
    if(activeMain==='operativo'||operative){
      const key=operative?.dataset.tabKey||'';
      if(approvedKeys.has(key))return key;
      if(key==='operations.productivity_capture')return 'operations.capture';
      const label=norm(operative?.dataset.opview||operative?.textContent||'');
      if(byOperationalView[label])return byOperationalView[label];
      if(label.includes('cargar productividad'))return 'operations.capture';
      if(label.includes('bono'))return 'operations.bonuses';
      if(label.includes('recorrid'))return 'operations.routes';
      if(label.includes('revisi'))return 'operations.recovery_audit';
      if(label.includes('productiv'))return 'operations.productivity';
      if(label.includes('recuperacion'))return 'operations.recovery';
      if(label.includes('conversion'))return 'operations.conversion';
      const fallback=document.querySelector('#operativoDynamicTitle')?.textContent||'';
      if(norm(fallback).includes('centro operativo'))return 'operations.center';
    }
    return '';
  }
  let last='',pending=false;
  function update(){
    pending=false;
    const body=document.body;if(!body)return;
    body.classList.add('or410-ui');
    const next=identify();
    if(next!==last){last=next;body.dataset.or410Tab=next;}
  }
  function schedule(){
    if(pending)return;pending=true;
    window.requestAnimationFrame(update);
  }
  function init(){
    update();
    ['#operativoNav','#analysisNav','#page-operativo','#page-macro','#page-lingerie-checklist']
      .forEach(selector=>{
        const el=document.querySelector(selector);
        if(!el)return;
        new MutationObserver(schedule).observe(el,{attributes:true,attributeFilter:['class','hidden','aria-selected']});
      });
    document.addEventListener('click',e=>{
      if(e.target.closest?.('#operativoNav,#analysisNav,[data-main],#v200OperationTabs'))schedule();
    },true);
    window.addEventListener('pageshow',schedule,{passive:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
