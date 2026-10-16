"""V332: compact multi-line column headers across Operaciones Ropa tables.

The metadata row retains ($ mil). Values never repeat 'mil' after monetary
numbers. No table data, column ordering, calculations or filters are changed.
"""
from fastapi.responses import HTMLResponse

CSS = r'''<style id="v332-universal-multiline-headers">
/* Use heading HEIGHT instead of heading WIDTH, consistent on PC/tablet/mobile. */
html body table thead tr th,
html body table thead tr td[role="columnheader"]{
  white-space:normal!important;
  overflow-wrap:break-word!important;
  word-break:normal!important;
  hyphens:auto!important;
  line-height:1.18!important;
  text-align:center!important;
  vertical-align:middle!important;
  max-width:118px!important;
  min-width:0!important;
  height:auto!important;
  min-height:54px!important;
  padding:9px 5px!important;
  font-size:clamp(9px,.75vw,12px)!important;
  font-weight:850!important;
}
html body table thead tr th :is(span,b,strong,small,.v273-line){
  white-space:normal!important;
  overflow-wrap:break-word!important;
  text-overflow:clip!important;
}
html body table thead tr th:nth-child(odd){
  background:#164c83!important;
  color:#fff!important;
}
html body table thead tr th:nth-child(even){
  background:#617892!important;
  color:#fff!important;
}
/* Long labels no longer force 1480px matrices that previously only fit on widescreens. */
html body .rr243-table{
  min-width:970px!important;
  width:100%!important;
  table-layout:auto!important;
}
html body .rr243-table td{white-space:nowrap!important}
html body .rr243-tablewrap,.v331-tablewrap{
  overflow-x:auto!important;
  overscroll-behavior-x:contain!important;
}
/* Preserve data legibility, sticky first columns, sort and filter controls. */
html body table tbody td{
  overflow-wrap:normal;
  font-variant-numeric:tabular-nums;
}
@media(max-width:1024px){
  html body table thead tr th{
    min-height:50px!important;
    padding:6px 3px!important;
    max-width:102px!important;
    font-size:9px!important;
  }
}
@media(max-width:700px){
  html body table thead tr th{
    max-width:86px!important;
    min-height:48px!important;
    font-size:8px!important;
    padding:6px 2px!important;
    line-height:1.12!important;
  }
}
</style>'''

JS = r'''<script id="v332-units-cleanup-js">(function(){
 if(window.__v332_units)return;
 window.__v332_units=true;
 var pattern=/(\$\s*-?\s*[\d][\d,.]*)\s+mil\b/gi;
 function visit(root){
   if(!root||root.nodeType!==1)return;
   var matches=[];
   if(root.matches&&root.matches('table tbody td,.rr243-kpi .val'))matches.push(root);
   if(root.querySelectorAll)root.querySelectorAll('table tbody td,.rr243-kpi .val').forEach(function(cell){matches.push(cell)});
   matches.forEach(function(cell){
     // Do not touch thead, field labels, user inputs or editable content.
     if(cell.closest('thead')||cell.isContentEditable)return;
     var walker=document.createTreeWalker(cell,NodeFilter.SHOW_TEXT);
     var node;
     while((node=walker.nextNode())){
       if(!node.nodeValue||node.parentElement&&node.parentElement.closest('input,textarea,script,style'))continue;
       pattern.lastIndex=0;
       if(pattern.test(node.nodeValue)){pattern.lastIndex=0;node.nodeValue=node.nodeValue.replace(pattern,'$1')}
     }
   });
 }
 function boot(){
   visit(document.body);
   var pending=new Set(),scheduled=false;
   function update(){
     scheduled=false;
     pending.forEach(function(node){visit(node)});
     pending.clear();
   }
   var observer=new MutationObserver(function(records){
     records.forEach(function(rec){rec.addedNodes.forEach(function(node){
       if(node.nodeType===1)pending.add(node);
     })});
     if(pending.size&&!scheduled){scheduled=true;requestAnimationFrame(update)}
   });
   observer.observe(document.body,{childList:true,subtree:true});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});
 else boot();
})();</script>'''


def install(m):
    if getattr(m, "_V332_MULTILINE_TABLES", False):
        return

    @m.app.middleware("http")
    async def install_v332_markup(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or not response.headers.get("content-type", "").startswith("text/html"):
            return response
        try:
            data = bytearray()
            async for chunk in response.body_iterator:
                data.extend(chunk)
            page = bytes(data).decode("utf-8", errors="replace")
            if 'id="v332-universal-multiline-headers"' not in page:
                pos = page.lower().rfind("</body>")
                page = page[:pos] + CSS + page[pos:] if pos >= 0 else page + CSS
            if 'id="v332-units-cleanup-js"' not in page:
                pos = page.lower().rfind("</body>")
                page = page[:pos] + JS + page[pos:] if pos >= 0 else page + JS
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return HTMLResponse(page, status_code=response.status_code, headers=headers)
        except Exception as exc:
            print("[V332] Markup preservation fallback", type(exc).__name__, flush=True)
            return response

    m._V332_MULTILINE_TABLES = True
    print("[V332] Multi-line table headers and unit-free monetary values enabled.", flush=True)
