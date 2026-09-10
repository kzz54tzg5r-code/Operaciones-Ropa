"""V114 temporal: diagnostica etiquetas/valores del PDF Meta_ROPA_SEPTIEMBRE.
Sólo imprime líneas comerciales relevantes, nunca el documento completo.
"""
from pathlib import Path
import re, threading, time, unicodedata


def _norm(v):
    t=unicodedata.normalize('NFKD',str(v or ''));t=''.join(ch for ch in t if not unicodedata.combining(ch)).upper();return re.sub(r'\s+',' ',t).strip()


def install(m):
    if getattr(m,'_V114_SALES_LAYOUT_PROBE',False):return
    @m.app.on_event('startup')
    def _probe():
        def worker():
            time.sleep(8)
            try:
                entries=[dict(e) for e in (m.load_manifest() or {}).get('sales',[]) if int(e.get('month') or 0)==9 and int(e.get('year') or 0)==2026]
                if not entries:
                    print('[V114-PROBE] sin PDF septiembre',flush=True);return
                item=sorted(entries,key=lambda e:str(e.get('uploaded_at') or ''))[-1];path=m.resolve_entry_path(item)
                import pdfplumber
                print(f"[V114-PROBE] archivo={path.name}",flush=True)
                with pdfplumber.open(path) as pdf:
                    for pno,page in enumerate(pdf.pages,1):
                        try:text=page.extract_text(x_tolerance=2,y_tolerance=3) or ''
                        except TypeError:text=page.extract_text() or ''
                        relevant=[]
                        for raw in text.splitlines():
                            key=_norm(raw)
                            if any(tok in key for tok in ('VENTA','VTA','META','PRESUP','OBJETIVO','REAL','CUMPL','PZAS','PIEZAS')):
                                clean=re.sub(r'\s+',' ',raw).strip()
                                if clean: relevant.append(clean[:240])
                        print(f"[V114-PROBE] P{pno}: {' || '.join(relevant[:8]) if relevant else 'sin líneas relevantes'}",flush=True)
                print('[V114-PROBE] fin',flush=True)
            except Exception as exc:
                print(f'[V114-PROBE] ERROR {type(exc).__name__}: {exc}',flush=True)
        threading.Thread(target=worker,daemon=True,name='v114-sales-probe').start()
    m._V114_SALES_LAYOUT_PROBE=True
    print('[V114-PROBE] programado',flush=True)
