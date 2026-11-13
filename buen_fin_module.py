"""Buen Fin 2026: catálogo promocional, retiros y consulta por escaneo.
Fuente aislada: archivo Excel autorizado; las imágenes se consultan del
servicio de fotos de Bonos, sin duplicarlas ni depender de imágenes Excel.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from threading import RLock
import gzip
import hashlib
import json
import os
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
RNS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
STRATEGIES = (
    "2do al 50% o 3x2", "FINDE 20-30%", "Ganchos 40-50%",
    "Todo a $399 y $499", "Mamelucos 3x$999", "Semana PUMA",
    "Oport. Importados", "Price Electro Home",
)
WITHDRAWALS = ("Retiro Promo 10 Nov", "Retiro Promo 13 Nov")
_lock = RLock()
_cache_key = None
_cache_data = None


def _plain(v):
    return "" if v is None else str(v).strip()


def _money(v):
    if not _plain(v):
        return None
    try:
        return float(round(Decimal(str(v)), 2))
    except (ValueError, InvalidOperation):
        return None


def _status(note):
    n = _plain(note).upper()
    if "PENDIENTE" in n:
        return "Pendiente de liberación"
    if "REINTEGRAD" in n:
        return "Reintegrado"
    if "CANCELA" in n:
        return "Cancelado"
    return "Vigente"


def _xlsx_sheets(data):
    """Lee valores sin procesar las miles de imágenes embebidas en el XLSX."""
    with zipfile.ZipFile(BytesIO(data)) as archive:
        infos = {i.filename: i for i in archive.infolist()}
        if len(infos) > 9000:
            raise ValueError("El archivo contiene demasiadas partes.")
        if not {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"} <= infos.keys():
            raise ValueError("No se reconoció la estructura del Excel.")
        if sum(i.file_size for i in infos.values() if i.filename.startswith("xl/worksheets/")) > 45_000_000:
            raise ValueError("Las hojas del Excel superan el tamaño permitido.")
        shares = []
        if "xl/sharedStrings.xml" in infos:
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shares = ["".join((t.text or "") for t in si.iter(NS + "t")) for si in shared_root]
        root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target", "") for r in rels.findall(RNS+"Relationship")}
        wanted = set(STRATEGIES + WITHDRAWALS)
        for sheet in root.findall(NS+"sheets/"+NS+"sheet"):
            name = sheet.get("name", "")
            if name not in wanted:
                continue
            target = targets.get(sheet.get(REL+"id"), "")
            if not target:
                continue
            path = target.lstrip("/") if target.startswith("/") else "xl/"+target
            import posixpath
            path = posixpath.normpath(path)
            if path not in infos or not path.startswith("xl/worksheets/"):
                raise ValueError("Falta una hoja requerida: "+name)
            if infos[path].file_size > 15_000_000:
                raise ValueError("Una hoja del Excel es demasiado grande")
            xroot = ET.fromstring(archive.read(path))
            rows = []
            for row in xroot.findall(NS+"sheetData/"+NS+"row"):
                cells = {}
                for c in row.findall(NS+"c"):
                    address = c.get("r", "")
                    m = re.match(r"[A-Z]+", address)
                    if not m:
                        continue
                    value = c.find(NS+"v")
                    inline = c.find(NS+"is")
                    raw = value.text if value is not None else None
                    if c.get("t") == "s" and raw is not None:
                        ix = int(raw)
                        raw = shares[ix] if 0 <= ix < len(shares) else ""
                    elif c.get("t") == "inlineStr" and inline is not None:
                        raw = "".join(t.text or "" for t in inline.iter(NS+"t"))
                    if raw is not None:
                        cells[m.group()] = raw
                rows.append((int(row.get("r", "0")), cells))
            yield name, rows


def parse_workbook(data):
    sheets = dict(_xlsx_sheets(data))
    missing = set(STRATEGIES + WITHDRAWALS) - set(sheets)
    if missing:
        raise ValueError("Faltan pestañas: "+", ".join(sorted(missing)))
    records = []
    withdrawn = []
    for name in STRATEGIES:
        rows = sheets[name]
        headers = next((r for idx, r in rows if idx == 4), {})
        if headers.get("C") != "ID" or headers.get("B") != "NOTAS CANCELACIONES":
            raise ValueError("Encabezados inesperados: "+name)
        price_scheme = name == STRATEGIES[0]
        stock_start = "S" if price_scheme else "U"
        col_index = lambda s: sum((ord(c)-64)*26**i for i,c in enumerate(s[::-1]))
        start = col_index(stock_start)
        stock_columns = [(col, head) for col, head in headers.items()
                         if col_index(col) >= start
                         and head not in ("Mín. tiendas ≥5%", "Mín. tiendas <5%")
                         and not head.lower().startswith(("total", "cedis", "darkstore"))]
        for index, row in rows:
            if index < 5 or not re.fullmatch(r"\d{1,15}", _plain(row.get("C"))):
                continue
            note = _plain(row.get("B"))
            discount = _money(row.get("Q")) if not price_scheme else None
            price = _money(row.get("O")) if not price_scheme else None
            sale_price = _money(row.get("P")) if not price_scheme else None
            normal_ver = _money(row.get("R")) if not price_scheme else _money(row.get("P"))
            sale_ver = _money(row.get("S")) if not price_scheme else _money(row.get("Q"))
            stock = {head: int(float(row.get(col))) for col, head in stock_columns
                     if _plain(row.get(col)) and _plain(row.get(col)).replace(".","",1).isdigit()}
            records.append({
                "id": _plain(row["C"]), "corrida": _plain(row.get("D")),
                "modelo": _plain(row.get("E")), "marca": _plain(row.get("F")),
                "familia": _plain(row.get("G")), "categoria": _plain(row.get("I")),
                "subcategoria": _plain(row.get("J")),
                "estrategia": name, "propuesta": _plain(row.get("L")),
                "vigencia": _plain(row.get("M")), "mecanica": _plain(row.get("O")) if price_scheme else name,
                "estado": _status(note), "nota": note,
                "descuento": discount,
                "precio_tienda": price, "precio_promo_tienda": sale_price,
                "precio_veracruz": normal_ver, "precio_promo_veracruz": sale_ver,
                "inventario": stock,
            })
    for date, name in (("2026-11-10", WITHDRAWALS[0]), ("2026-11-13", WITHDRAWALS[1])):
        rows = sheets[name]
        hdr = next((r for idx,r in rows if idx == 4), {})
        if hdr.get("C") != "ID":
            raise ValueError("Encabezados inesperados de retiros: "+name)
        for index, row in rows:
            if index < 5 or not re.fullmatch(r"\d{1,15}", _plain(row.get("C"))):
                continue
            withdrawn.append({
                "id": _plain(row["C"]), "fecha": date,
                "modelo": _plain(row.get("F")), "marca": _plain(row.get("E")),
                "promocion_retirada": _plain(row.get("N")),
                "estrategia_destino": _plain(row.get("S")),
                "precio_anterior": _money(row.get("P")),
                "precio_socio": _money(row.get("O")),
                "observacion": _plain(row.get("U")) if date == "2026-11-13" else "",
            })
    retiro_by_id = Counter(x["id"] for x in withdrawn)
    for record in records:
        record["retiro_previo"] = retiro_by_id.get(record["id"], 0)
    status_counts = Counter(x["estado"] for x in records)
    by_strategy = {}
    for name in STRATEGIES:
        items = [r for r in records if r["estrategia"] == name]
        by_strategy[name] = {"total":len(items),
                             **{k:sum(x["estado"] == k for x in items)
                                for k in ("Vigente", "Reintegrado", "Cancelado", "Pendiente de liberación")}}
    return {"version":"2026-11-12", "rows":records, "retiros":withdrawn,
            "resumen":{"registros":len(records),"ids_unicos":len({r["id"] for r in records}),
                "retiros":len(withdrawn),"retiros_10":sum(x["fecha"]=="2026-11-10" for x in withdrawn),
                "retiros_13":sum(x["fecha"]=="2026-11-13" for x in withdrawn),
                "estados":dict(status_counts),"estrategias":by_strategy}}


def _data_path(m):
    directory = Path(m.DATA_ROOT) / "buen_fin"
    directory.mkdir(parents=True,exist_ok=True)
    return directory / "catalogo_2026.json.gz"


def _load(m):
    global _cache_key, _cache_data
    path = _data_path(m)
    if not path.exists():
        return None
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    with _lock:
        if key != _cache_key:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                _cache_data = json.load(f)
            _cache_key = key
        return _cache_data


def _save(m, data):
    global _cache_key, _cache_data
    path = _data_path(m)
    with _lock:
        fd, temp = tempfile.mkstemp(prefix=".buen_fin_",suffix=".gz",dir=path.parent)
        try:
            with os.fdopen(fd,"wb") as out:
                with gzip.GzipFile(fileobj=out,mode="wb",compresslevel=6) as gz:
                    gz.write(json.dumps(data,ensure_ascii=False,separators=(",",":")).encode("utf-8"))
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp,path)
            _cache_key=None
            _cache_data=None
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def _scan_id(raw):
    value = _plain(raw).replace(" ","").upper()
    if re.fullmatch(r"\d{1,8}", value):
        return value
    barcode = re.fullmatch(r"(?:O[I1]\d{2}|0)?(\d{7})\d{2}(?:\$|S)?", value)
    return barcode.group(1) if barcode else ""


_wholesale_lock = RLock()
_wholesale_cache = {"key": None, "data": None}


def _store_for_user(m, user, requested=""):
    """Limita la tienda a una del padrón sin permitir saltar el alcance del usuario."""
    role = _plain(user.get("role"))
    bound = _plain(user.get("store"))
    selected = _plain(requested) if role in {"superadmin", "admin", "director"} else bound
    active = {m.login_key(name): name for name in m.store_names(True)}
    return active.get(m.login_key(selected), "")


def _wholesale_snapshot(m, dataset):
    """Precio mayoreo del ÚLTIMO Excel Capacidades procesado, no de Bonos.

    El parser comercial conserva PRECIO MAYOREO en Costo unitario; Precio
    unitario mezcla menudeo/oferta y sería una fuente equivocada.
    Cacheamos únicamente IDs participantes, nunca el dataframe de 196 mil filas.
    """
    global _wholesale_cache
    ids = {r["id"] for r in dataset.get("rows", []) if r.get("estrategia") == STRATEGIES[0]}
    try:
        entry = m._capacity_source_entry("")
    except Exception:
        entry = None
    source = dict(entry) if entry else {}
    key = (_plain(source.get("id")), _plain(source.get("uploaded_at")),
           _plain(source.get("cache_file")), hashlib.sha256("|".join(sorted(ids)).encode("utf-8")).hexdigest())
    with _wholesale_lock:
        if _wholesale_cache["key"] == key and _wholesale_cache["data"] is not None:
            return _wholesale_cache["data"]
        empty = {"company": {}, "store": {}, "source": {
            "archivo": _plain(source.get("name")), "cargado": _plain(source.get("uploaded_at")),
            "fecha_corte": _plain(source.get("report_date")), "disponible": False}}
        if not entry or not ids:
            return empty
        try:
            frame = m._latest_capacity_frame()
            columns = {"ID_ART", "Costo unitario", "Tienda"}
            if frame is None or frame.empty or not columns.issubset(frame.columns):
                return empty
            subset = frame.loc[
                frame["ID_ART"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().isin(ids),
                ["ID_ART", "Tienda", "Costo unitario"],
            ].copy()
            if subset.empty:
                return empty
            subset["Costo unitario"] = m.pd.to_numeric(subset["Costo unitario"], errors="coerce")
            subset = subset.loc[
                subset["Costo unitario"].gt(0) & subset["Costo unitario"].lt(1_000_000)
            ]
            if subset.empty:
                return empty
            votes_by_id = {}
            votes_by_store = {}
            for row in subset.itertuples(index=False, name=None):
                ident, store, value = row
                ident = _plain(ident).removesuffix(".0")
                price = round(float(value), 2)
                if ident not in ids:
                    continue
                votes_by_id.setdefault(ident, Counter())[price] += 1
                skey = m.login_key(_plain(store))
                votes_by_store.setdefault((ident, skey), Counter())[price] += 1
            def majority(counter):
                # Un ID puede repetirse por ubicación: se toma su precio más frecuente.
                return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
            result = {
                "company": {ident: majority(v) for ident, v in votes_by_id.items()},
                "store": {key: majority(v) for key, v in votes_by_store.items()},
                "source": {**empty["source"], "disponible": bool(votes_by_id)},
            }
            _wholesale_cache = {"key": key, "data": result}
            return result
        except Exception as exc:
            print("[BUEN-FIN] Capacidades mayoreo no disponible: " + type(exc).__name__, flush=True)
            # Nunca inventar precios si el último Excel no se puede leer.
            return empty


def _priced_record(m, record, wholesale, selected_store=""):
    """Mantener precios actuales/propuestos del Excel salvo mecánica 3x2."""
    output = {k: v for k, v in record.items() if k != "inventario"}
    if record.get("estrategia") != STRATEGIES[0]:
        output["fuente_precio"] = "Listado oficial Buen Fin"
        return output
    ident = record["id"]
    price_by_store = wholesale["store"]
    company_price = wholesale["company"].get(ident)
    selected_price = (price_by_store.get((ident, m.login_key(selected_store)))
                      if selected_store else None)
    veracruz = price_by_store.get((ident, m.login_key("Veracruz")))
    # Una tienda especificada no hereda el precio de otra si no tiene registro.
    output["precio_tienda"] = (selected_price if selected_store else company_price)
    # Veracruz tiene precio propio: no inventar un valor con la referencia nacional.
    output["precio_veracruz"] = veracruz
    # El 3x2/segundo al 50% es una mecánica, no un precio unitario rebajado.
    # No fabricar un 'precio propuesto' con 33.33% ni asumir un ticket de 3 piezas.
    output["precio_promo_tienda"] = None
    output["precio_promo_veracruz"] = None
    output["descuento"] = None
    output["fuente_precio"] = "Precio mayoreo · último Excel Capacidades"
    output["fuente_capacidades"] = wholesale["source"]
    output["precio_mayoreo_tienda_especifico"] = selected_price is not None
    return output


def install(m):
    """Se instala tras V314; no cambia ninguna ruta comercial/operativa."""
    from ac_catalog import ExistingCatalogLookup
    catalog_lookup = ExistingCatalogLookup(m._latest_capacity_frame)

    @m.app.get("/buen-fin",include_in_schema=False)
    def page(request: Request):
        m.require_user(request)
        return FileResponse(Path(__file__).resolve().parent/"web"/"buen_fin.html",
                            headers={"Cache-Control":"no-store", "X-Robots-Tag":"noindex"})

    @m.app.get("/api/buen-fin/resumen")
    def summary(request: Request):
        m.require_user(request)
        dataset = _load(m)
        if not dataset:
            return {"cargado":False,"resumen":None}
        return {"cargado":True,"resumen":dataset["resumen"],"version":dataset["version"],
                "importado":dataset.get("importado"),"archivo":dataset.get("archivo")}

    @m.app.post("/api/buen-fin/importar")
    async def upload(request: Request, file: UploadFile = File(...)):
        actor = m.require_user(request,("superadmin","admin"))
        origin=request.headers.get("origin","")
        if origin:
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc != request.url.netloc:
                raise HTTPException(403,"Origen no autorizado")
        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            raise HTTPException(400,"Selecciona un archivo .xlsx")
        content = await file.read(22_000_001)
        if len(content)>22_000_000:
            raise HTTPException(413,"El archivo supera 22 MB")
        try:
            dataset = parse_workbook(content)
        except (ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, OverflowError) as exc:
            raise HTTPException(400,"Archivo de Buen Fin inválido: "+str(exc)[:180]) from exc
        dataset["importado"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
        dataset["archivo"]=Path(file.filename).name[:150]
        dataset["sha256"]=hashlib.sha256(content).hexdigest()
        _save(m,dataset)
        return {"ok":True,"resumen":dataset["resumen"],"archivo":dataset["archivo"]}

    @m.app.get("/api/buen-fin/modelos")
    def list_models(request:Request, q:str="", estado:str="", estrategia:str="",
                    pagina:int=1, limite:int=30, tienda:str=""):
        user = m.require_user(request)
        dataset=_load(m)
        if not dataset:
            return {"items":[],"total":0,"pagina":1,"paginas":0}
        if pagina<1 or pagina>100000 or limite<1 or limite>100:
            raise HTTPException(400,"Paginación inválida")
        needle=q.strip().casefold()[:90]
        items=[r for r in dataset["rows"]
               if (not estado or r["estado"]==estado)
               and (not estrategia or r["estrategia"]==estrategia)
               and (not needle or needle in " ".join((r["id"],r["modelo"],r["marca"],
                       r["subcategoria"],r["estrategia"])).casefold())]
        total=len(items);start=(pagina-1)*limite
        # Inventario por tienda sólo en consulta detallada para mantener ligera la vista.
        selected = _store_for_user(m, user, tienda)
        wholesale = _wholesale_snapshot(m, dataset) if any(
            r["estrategia"] == STRATEGIES[0] for r in items[start:start+limite]
        ) else None
        result = [
            _priced_record(m, r, wholesale, selected) if wholesale else
            {**{k: v for k, v in r.items() if k != "inventario"},
             "fuente_precio": "Listado oficial Buen Fin"}
            for r in items[start:start+limite]
        ]
        return {"items":result,"total":total,"pagina":pagina,
                "paginas":(total+limite-1)//limite}

    @m.app.get("/api/buen-fin/articulo")
    def article(request:Request, codigo:str="", tienda:str=""):
        user=m.require_user(request)
        dataset=_load(m)
        if not dataset:
            raise HTTPException(404,"Aún no se ha cargado el catálogo del Buen Fin")
        product_id=_scan_id(codigo)
        if not product_id:
            raise HTTPException(400,"Etiqueta no reconocida: verifica el ID")
        rows=[r for r in dataset["rows"] if r["id"]==product_id]
        withdrawals=[r for r in dataset["retiros"] if r["id"]==product_id]
        if not rows and not withdrawals:
            raise HTTPException(404,"ID no incluido en las estrategias o retiros del Buen Fin")
        # Alcance de tienda y precio mayoreo se calculan por ID en la última carga.
        selected = _store_for_user(m, user, tienda)
        wholesale = _wholesale_snapshot(m, dataset) if any(
            r["estrategia"] == STRATEGIES[0] for r in rows
        ) else None
        color=None
        if selected:
            try:
                detail=catalog_lookup(selected,product_id)
                color=detail.get("color") if detail else None
            except Exception:
                color=None
        response_rows=[]
        for r in rows:
            item = _priced_record(m, r, wholesale, selected) if wholesale else {
                **{k: v for k, v in r.items() if k != "inventario"},
                "fuente_precio": "Listado oficial Buen Fin"}
            item["inventario_tienda"] = r["inventario"].get(selected) if selected else None
            response_rows.append(item)
        return {"id":product_id,"tienda":selected,"color":color or None,
                "modelos":response_rows,"retiros":withdrawals,
                "foto":"/api/bonuses/product-photo/"+product_id}
