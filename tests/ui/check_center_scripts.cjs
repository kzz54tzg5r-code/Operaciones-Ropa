// V360: detectar inmediatamente scripts rotos antes de cargar Playwright.
const fs=require('node:fs');
const vm=require('node:vm');
function check(path,embedded){
 const content=fs.readFileSync(path,'utf8');
 let code=content;
 if(embedded){
  const match=/js = r'''<script[^>]*>([\s\S]*?)<\/script>'''/.exec(content);
  if(!match)throw Error(path+': no se encontró JavaScript embebido');
  code=match[1];
 }
 new vm.Script(code,{filename:path});
 console.log('JavaScript válido: '+path);
}
check('v236_center_operativo_final_patch.py',true);
check('v266_operational_period_authority_patch.py',true);
check('web/centro_operativo_opcion4_v356.js',false);
check('web/compact_reports.js',false);
