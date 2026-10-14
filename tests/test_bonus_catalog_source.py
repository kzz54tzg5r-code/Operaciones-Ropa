"""Regresión: los bonos leen CATALOGO oficial, no Categoria/Subcategoria."""
import pandas as pd

from commercial.parsers import _normalize_capacity_source
from v293_sales_bonus_patch import classify_bonus_catalogs_from_source, select_vigente_bonus_catalog_rows


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


def test_catalog_classifier_accepts_compressed_categorical_series():
    # El lector streaming almacena textos repetidos como pd.Categorical.
    compressed = pd.Series(pd.Categorical([
        "LICENCIAS | DIG | PRI-VER | 2026 | 1E",
        "BASICOS | DIG | 2026",
        "ABRIGADOR | DIG | 2026",
    ]))
    assert classify_bonus_catalogs_from_source(compressed).tolist() == [
        "Licencias", "Básicos", "Abrigador",
    ]


def test_abrigador_second_segment_and_licencias_first_segment():
    values = pd.Series([
        "COL IMP | ABRIGADOR | 2026 | 1E",
        "LICENCIAS | DIG | PRI-VER | 2026 | 1E",
        "BASICOS | OTO-INV | 2026",
        "CIERRE DE TEMPORADA | OI | 2025 | 1E",
    ])
    assert classify_bonus_catalogs_from_source(values).tolist() == [
        "Abrigador", "Licencias", "Básicos", "",
    ]


def test_catalogs_do_not_depend_on_tipo_catalogo_or_subcategoria(tmp_path):
    raw = pd.DataFrame({
        "TIENDA": ["OLIVAR"] * 3,
        "CATALOGO": [
            "COL IMP | ABRIGADOR | 2026 | 1E",
            "LICENCIAS | DIG | PRI-VER | 2026 | 1E",
            "BASICOS | DIG | 2026",
        ],
        "CATEGORIA": ["ROPA CASUAL"] * 3,
        "SUBCATEGORIA": ["CHAMARRA"] * 3,
        "TIPO CATALOGO MAX VIG": ["VIGENTE", "DESCONTINUADO", "PROXIMO A SALIR"],
        "ID_ART": ["101001", "101002", "101003"],
        "MODELO": ["A", "B", "C"],
    })
    frame = _normalize_capacity_source(raw, tmp_path / "Capacidades_13.10.26.xlsx")
    assert frame["Tipo catálogo"].tolist() == list(raw["TIPO CATALOGO MAX VIG"])
    assert classify_bonus_catalogs_from_source(frame["Catálogo comercial"]).tolist() == [
        "Abrigador", "Licencias", "Básicos",
    ]


def test_opening_bonus_cohort_includes_only_vigente_after_normalization():
    frame=pd.DataFrame({
        "ID_ART":["1","2","3","4","5"],
        "Tipo catálogo":pd.Categorical(["VIGENTE","DESCONTINUADO","  vigente ","PROXIMO A SALIR","IMPULSO"]),
        "Catálogo comercial":["COL IMP | ABRIGADOR | 2026","LICENCIAS | DIG | 2026","BASICOS | DIG","LICENCIAS | DIG","BASICOS | DIG"],
    })
    selected=select_vigente_bonus_catalog_rows(frame)
    assert selected["ID_ART"].tolist()==["1","3"]
    assert classify_bonus_catalogs_from_source(selected["Catálogo comercial"]).tolist()==["Abrigador","Básicos"]
