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
            import pandas as pd
            if files:
                df=pd.read_pickle(files[0])
                print(f"[V323-CATALOG-AUDIT] archivo={files[0].name} filas={len(df)} campos={list(df.columns)}",flush=True)
            else:
                print("[V323-CATALOG-AUDIT] Sin caché; se examinará una muestra del XLSX original sin escribir datos",flush=True)
                manifest=m.load_manifest()
                entries=manifest.get("capacities") or []
                entry=next((e for e in entries if "13.10.26" in str(e.get("name") or e.get("filename") or "")),None)
                if not entry:
                    print("[V323-CATALOG-AUDIT] No se encontró el archivo de octubre en el manifiesto",flush=True)
                    return
                source=m.resolve_entry_path(entry)
                if not source or not source.exists():
                    print("[V323-CATALOG-AUDIT] Fuente física no disponible",flush=True)
                    return
                from commercial.parsers import _iter_fast_capacity_xlsx, _normalize_capacity_source
                iterator=_iter_fast_capacity_xlsx(source,chunk_rows=1800)
                raw=next(iterator,None)
                iterator.close()
                if raw is None or raw.empty:
                    print("[V323-CATALOG-AUDIT] Archivo sin filas de muestra",flush=True)
                    return
                df=_normalize_capacity_source(raw,source)
                del raw
                print(f"[V323-CATALOG-AUDIT] fuente={source.name} filas_muestra={len(df)} campos={list(df.columns)}",flush=True)
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
