"""V323: diagnóstico acotado de clasificación de catálogos de bonos.
No modifica datos, cortes, permisos, metas ni rankings.
"""
from __future__ import annotations
import gc
import threading
import time
from pathlib import Path

def install(m):
    if getattr(m, "_V323_CATALOG_AUDIT", False):
        return

    def audit():
        # Dar prioridad al inicio del servicio y no competir con migraciones/cargas.
        time.sleep(40)
        try:
            cache_dir=Path(m.CAPACITY_NORMALIZED_DIR)
            files=sorted(cache_dir.glob("*bonus-v*.pkl"),key=lambda p:p.stat().st_mtime,reverse=True)
            if not files:
                print("[V323-CATALOG-AUDIT] No hay caché ligero de Bonos; no se audita",flush=True)
                return
            import pandas as pd
            # Solo el caché más reciente; contiene columnas comerciales, no fotos.
            df=pd.read_pickle(files[0])
            print(f"[V323-CATALOG-AUDIT] archivo={files[0].name} filas={len(df)} campos={list(df.columns)}",flush=True)
            for store in ("Olivar", "Ixtapaluca"):
                subset=df.loc[df["Tienda"].fillna("").astype(str).str.casefold()==store.casefold()]
                print(f"[V323-CATALOG-AUDIT] tienda={store} filas={len(subset)}",flush=True)
                for field in ("Marca","Categoría","Subcategoría","Tipo catálogo"):
                    if field not in subset.columns:continue
                    values=subset[field].fillna("").astype(str)
                    top={str(k)[:65]:int(v) for k,v in values.value_counts().head(30).items()}
                    print(f"[V323-CATALOG-AUDIT] tienda={store} campo={field} valores_frecuentes={top}",flush=True)
                # Solo conteos agregados; no IDs ni datos sensibles.
                if "Marca" in subset.columns:
                    brands=subset["Marca"].fillna("").astype(str)
                    match=brands.str.contains("disney|marvel|sanrio|warner|licen|basic|mattel|nickelodeon|star wars",case=False,regex=True)
                    print(f"[V323-CATALOG-AUDIT] tienda={store} marca_coincidencias_licencia_basico={int(match.sum())} marcas_distintas={int(brands.nunique())}",flush=True)
            del df
            gc.collect()
        except Exception as exc:
            print(f"[V323-CATALOG-AUDIT] diagnóstico no disponible: {type(exc).__name__}: {str(exc)[:240]}",flush=True)

    @m.app.on_event("startup")
    async def v323_catalog_startup_audit():
        threading.Thread(target=audit,name="v323-catalog-audit",daemon=True).start()

    m._V323_CATALOG_AUDIT=True
