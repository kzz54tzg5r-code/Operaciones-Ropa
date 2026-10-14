"""Regresión: los bonos leen CATALOGO oficial, no Categoria/Subcategoria."""
import pandas as pd

from commercial.parsers import _normalize_capacity_source
from v293_sales_bonus_patch import classify_bonus_catalogs_from_source


def test_real_capacidades_catalog_columns(tmp_path):
    raw = pd.DataFrame({
        "TIENDA": ["OLIVAR DEL CONDE"] * 4,
        "CATALOGO": [
            "LICENCIAS | DIG | PRI-VER | 2026 | 1E",
            "ABRIGADOR | DIG | PRI-VER | 2026",
            "BÁSICOS | DIG | PRI-VER | 2026",
            "NO CLASIFICADO | DIG",
        ],
        "CATALOGO GENERICO": ["DIG | PRI-VER ROPA"] * 4,
        "ID_ART": ["1360731", "108180", "1200001", "1200002"],
        "MODELO": ["880", "900", "300", "300"],
        "CATEGORIA": ["ROPA ABRIGADORA"] * 4,
        "SUBCATEGORIA": ["CHAMARRA"] * 4,
        "MARCA": ["YICHEN"] * 4,
        "PRECIO MAYOREO": [100] * 4,
        "EXISTENCIA": [100] * 4,
        "DIAS DE INVENTARIO SUG 7": [190] * 4,
    })
    frame = _normalize_capacity_source(raw, tmp_path / "Capacidades_13.10.26.xlsx")
    assert "Catálogo comercial" in frame
    assert "Catálogo genérico" in frame
    assert list(frame["Catálogo comercial"]) == list(raw["CATALOGO"])
    assert list(classify_bonus_catalogs_from_source(frame["Catálogo comercial"])) == [
        "Licencias", "Abrigador", "Básicos", "",
    ]


def test_licencia_overrides_abrigador_by_source_not_subcategoria():
    raw = pd.Series([
        "LICENCIAS | DIG | PRI-VER | 2026 | 1E",
        "BASICOS | DIG | 2026",
        "ABRIGADORA | DIG | 2026",
        "",
    ])
    assert classify_bonus_catalogs_from_source(raw).tolist() == [
        "Licencias", "Básicos", "Abrigador", "",
    ]
