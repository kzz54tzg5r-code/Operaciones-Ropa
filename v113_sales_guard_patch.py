"""V113: evita falsos importes pequeños de PDF Meta_ROPA y consolida ventas.

Los PDF Meta_ROPA tienen 19/21 páginas y el extractor PDF puede confundir
números de página/posición (25, 26, etc.) con una venta. Este parche considera
inválidos esos importes, identifica los PDF multipágina sin tienda en nombre
como alcance Compañía y usa el Excel de capacidades del mismo mes como respaldo
cuando contiene VTA ACUM MES EN $ / PZAS.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import inspect
import re
import threading
import time

PARSER_VERSION = 113
MIN_MONTHLY_SALE = 1000.0


def _norm(v):
    import unicodedata
    t=unicodedata.normalize('NFKD',str(v or ''))
    t=''.join(ch for ch in t if not unicodedata.combining(ch)).upper()
    return re.sub(r'\s+',' ',t).strip()


def _filename_has_store(m,path: Path):
    stem=_norm(path.stem)
    try: stores=list(m.store_names(True) or [])
    except Exception: stores=list(getattr(m,'PROJECT_STORES',[]) or [])
    for store in stores:
        key=_norm(store)
        if key and key in stem:
            return str(store)
    return ''


def install(m):
    if getattr(m,'_V113_SALES_GUARD',False): return

    previous_parser=m.parse_sales_pdf

    def parse_sales_pdf_v113(path,year=None,month=None):
        path=Path(path); y=int(year or 0); mo=int(month or 0)
        result=dict(previous_parser(path,y,mo) or {})
        pages=int(result.get('pages') or 0)
        filename_store=_filename_has_store(m,path)
        sale=float(result.get('total_sales') or 0)

        # 19/21 páginas con nombre genérico Meta_ROPA representan un reporte
        # consolidado; no asignarlo a León sólo porque sea el único nombre que
        # pdfplumber pudo leer en una de las páginas.
        generic_multi=(pages>=8 and not filename_store)
        if generic_multi:
            result['store']='Compañía'

        # Los falsos 25/26 detectados en producción son posiciones/paginación,
        # no importes de venta. Nunca publicarlos como venta mensual.
        suspicious=0 < sale < MIN_MONTHLY_SALE
        if suspicious:
            result['rejected_pdf_value']=sale
            result['total_sales']=0.0
            result['total_pieces']=0.0 if float(result.get('total_pieces') or 0)<1 else result.get('total_pieces')
            result['source_method']=''

        # Respaldo estrictamente del mismo mes. Para PDF multipágina genérico
        # se usa Compañía; para archivos explícitamente nombrados por tienda se
        # conserva esa tienda.
        if float(result.get('total_sales') or 0) <= 0 and y>0 and 1<=mo<=12:
            scope=filename_store or ('Compañía' if generic_multi else (result.get('store') or 'Compañía'))
            try:
                from v112_sales_pdf_repair import _capacity_month_fallback
                cap_sales,cap_pieces,cap_source=_capacity_month_fallback(m,y,mo,scope)
            except Exception as exc:
                print(f'[V113-SALES] fallback {y}-{mo:02d}: {type(exc).__name__}: {exc}',flush=True)
                cap_sales=cap_pieces=0;cap_source=''
            if cap_sales>=MIN_MONTHLY_SALE:
                result.update({
                    'store':scope,'stores':len(m.store_names(True) or []) if scope=='Compañía' else 1,
                    'total_sales':float(cap_sales),'total_pieces':float(cap_pieces or 0),
                    'source_method':'Excel capacidades · VTA ACUM MES · mismo mes',
                    'source_line':cap_source,'status':'Procesado · venta tomada del Excel capacidades del mismo mes',
                })

        if float(result.get('total_sales') or 0) < MIN_MONTHLY_SALE:
            result['total_sales']=0.0
            result['status']='Procesado · PDF de metas sin venta mensual legible'
        result['parser_version']=PARSER_VERSION
        print(
            f"[V113-SALES] {path.name} {y}-{mo:02d} pages={pages} scope={result.get('store') or 'sin'} "
            f"venta={float(result.get('total_sales') or 0):.2f} pzas={float(result.get('total_pieces') or 0):.0f} "
            f"rechazado={float(result.get('rejected_pdf_value') or 0):.2f} método={result.get('source_method') or 'sin venta'}",
            flush=True,
        )
        return result

    m.parse_sales_pdf=parse_sales_pdf_v113

    def _find_route(path,method='GET'):
        for r in list(m.app.router.routes):
            if getattr(r,'path',None)==path and method in (getattr(r,'methods',set()) or set()): return r
        return None

    # V112 ya arregló la firma de Request. Envolver su respuesta para que el
    # Macro jamás muestre 25/26 como venta y para completar el corte desde el
    # Excel del mismo mes cuando exista.
    route=_find_route('/api/commercial-sales-summary','GET')
    old_endpoint=getattr(route,'endpoint',None)
    if route and callable(old_endpoint):
        m.app.router.routes.remove(route)
        from fastapi import Request
        async def sales_summary_v113(request: Request,year:int|None=None,through_month:int|None=None,store:str='Compañía'):
            out=old_endpoint(request=request,year=year,through_month=through_month,store=store)
            if inspect.isawaitable(out): out=await out
            if not isinstance(out,dict): return out
            yy=int(out.get('year') or year or datetime.now().year); cut=int(out.get('through_month') or through_month or datetime.now().month)
            rows=list(out.get('months') or [])
            used=False
            from v112_sales_pdf_repair import _capacity_month_fallback
            for row in rows:
                mo=int(row.get('month') or 0)
                if mo<1 or mo>cut: continue
                cur=float(row.get('current') or 0)
                if 0 < cur < MIN_MONTHLY_SALE: row['current']=0.0;cur=0.0
                if cur<=0:
                    cs,cp,src=_capacity_month_fallback(m,yy,mo,str(out.get('store') or store))
                    if cs>=MIN_MONTHLY_SALE:
                        row.update({'current':cs,'pieces':cp,'sources':max(1,int(row.get('sources') or 0)),'source_type':'Excel capacidades','source_name':src});used=True
                prev=float(row.get('previous') or 0)
                if 0 < prev < MIN_MONTHLY_SALE: row['previous']=0.0
            goal=sum(float(r.get('target') or 0) for r in rows[:cut]);cur=sum(float(r.get('current') or 0) for r in rows[:cut]);prev=sum(float(r.get('previous') or 0) for r in rows[:cut])
            out['months']=rows;out['totals']={
                'goal_ytd':goal,'current_ytd':cur,'previous_ytd':prev,
                'compliance_pct':cur/goal*100 if goal else None,
                'growth_pct':(cur/prev-1)*100 if prev else None,
                'gap_to_goal':cur-goal if goal else None,
            }
            out['has_sales']=any(float(r.get('current') or 0)>0 or float(r.get('previous') or 0)>0 for r in rows[:cut])
            out['source_label']='Fuente: PDF mensual' + (' + Excel capacidades (mismo mes)' if used else '')
            out['parser_version']=PARSER_VERSION
            return out
        m.app.add_api_route('/api/commercial-sales-summary',sales_summary_v113,methods=['GET'])

    @m.app.on_event('startup')
    def _repair_v113():
        def worker():
            time.sleep(10)
            try:
                manifest=m.load_manifest() or {};entries=list(manifest.get('sales') or []);fixed=0
                for item0 in entries:
                    item=dict(item0);y=int(item.get('year') or 0);mo=int(item.get('month') or 0)
                    if not y or mo not in range(1,13): continue
                    path=m.resolve_entry_path(item)
                    if not path.exists() or path.suffix.lower()!='.pdf': continue
                    parsed=parse_sales_pdf_v113(path,y,mo)
                    changes={k:parsed.get(k) for k in ('status','store','rows','stores','pages','total_pieces','total_sales','parser_version','source_line','source_method','detected_stores','diagnostic','rejected_pdf_value') if k in parsed}
                    m.update_entry('sales',str(item.get('id') or ''),**changes)
                    if float(parsed.get('total_sales') or 0)>=MIN_MONTHLY_SALE: fixed+=1
                # Diagnóstico exacto del Excel capacidades disponible por mes.
                from v112_sales_pdf_repair import _capacity_month_fallback
                for mo in range(1,13):
                    sale,pzs,src=_capacity_month_fallback(m,2026,mo,'Compañía')
                    if sale>0:
                        print(f'[V113-CAP] 2026-{mo:02d} venta={sale:.2f} pzas={pzs:.0f} fuente={src}',flush=True)
                print(f'[V113-REPAIR] PDF revisados={len(entries)} · con venta válida={fixed}',flush=True)
            except Exception as exc:
                print(f'[V113-REPAIR] ERROR {type(exc).__name__}: {exc}',flush=True)
        threading.Thread(target=worker,daemon=True,name='v113-sales-repair').start()

    m._V113_SALES_GUARD=True
    print('[V113] Guardia de importes y respaldo mensual exacto activados.',flush=True)
