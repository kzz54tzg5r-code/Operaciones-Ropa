"""Lectura de la ficha AC desde el catálogo comercial que ya existe.

No importa ni escribe datos comerciales. El caller proporciona un dataframe
normalizado, habitualmente web_app._latest_capacity_frame(). Se consulta sólo
la tienda del usuario; no inventa descripción, color ni ubicación.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import unicodedata


def _key(value):
    raw = unicodedata.normalize("NFKD", str(value or "").strip())
    return "".join(c for c in raw if not unicodedata.combining(c)).casefold()


def _clean(value):
    text = str(value if value is not None else "").strip()
    return "" if text.casefold() in {"", "nan", "none", "nat", "<na>"} else text


def from_capacity_frame(frame, store, model_id):
    """Busca ID exacto y tienda exacta en el dataframe ya normalizado.

    Distintos locales pueden tener un modelo en ubicaciones diferentes.
    En tal caso no se devuelve una ubicación arbitraria: se listan hasta
    tres ubicaciones existentes sin confundirlas con una asignación operativa.
    """
    store = _clean(store)
    model_id = _clean(model_id)
    if not store or not model_id or frame is None or getattr(frame, "empty", True):
        return None
    if not {"ID_ART", "Tienda"}.issubset(frame.columns):
        return None

    scoped = frame.loc[
        frame["Tienda"].astype(str).map(_key).eq(_key(store)) &
        frame["ID_ART"].astype(str).str.replace(r"\\.0$", "", regex=True).str.strip().eq(model_id)
    ]
    if scoped.empty:
        return None

    def first(*columns):
        for column in columns:
            if column not in scoped:
                continue
            for value in scoped[column]:
                clean = _clean(value)
                if clean:
                    return clean
        return None

    locs = []
    for column in ("Ubicación detalle", "Pasillo operativo", "Pasillo"):
        if column in scoped.columns:
            locs = list(dict.fromkeys(
                clean for clean in (_clean(v) for v in scoped[column])
                if clean
            ))
            if locs:
                break

    return {
        "name": first("Modelo", "Descripción", "Descripcion") or model_id,
        "color": first("Color", "COLOR"),
        "location": " / ".join(locs[:3]) if locs else None,
    }


class ExistingCatalogLookup:
    """Consulta el catálogo ya cargado. Cachea hasta 4 tiendas para evitar
    recorrer 196 mil filas en cada escaneo de un colaborador.
    """

    def __init__(self, frame_provider):
        self.frame_provider = frame_provider
        self._frame_id = None
        self._store_frames = OrderedDict()
        self._lock = RLock()

    def __call__(self, store, model_id):
        if not store or not model_id:
            return None
        frame = self.frame_provider()
        if frame is None or getattr(frame, "empty", True):
            return None
        if not {"ID_ART", "Tienda"}.issubset(frame.columns):
            return None
        key = _key(store)
        with self._lock:
            if id(frame) != self._frame_id:
                self._store_frames.clear()
                self._frame_id = id(frame)
            if key in self._store_frames:
                scoped = self._store_frames[key]
                self._store_frames.move_to_end(key)
            else:
                scoped = frame.loc[frame["Tienda"].astype(str).map(_key).eq(key)]
                # Sólo conservar metadatos de la ficha, no cientos de columnas
                # de inventario, ventas y costos.
                fields = [c for c in (
                    "Tienda", "ID_ART", "Modelo", "Descripción", "Descripcion",
                    "Color", "COLOR", "Ubicación detalle",
                    "Pasillo operativo", "Pasillo"
                ) if c in scoped.columns]
                scoped = scoped[fields].copy()
                self._store_frames[key] = scoped
                if len(self._store_frames) > 4:
                    self._store_frames.popitem(last=False)
        return from_capacity_frame(scoped, store, model_id)
