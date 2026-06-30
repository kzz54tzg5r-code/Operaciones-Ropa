# -*- coding: utf-8 -*-
from __future__ import annotations
import pandas as pd


def load_excel(uploaded_file) -> pd.DataFrame:
    """Carga Excel o CSV. Si el Excel tiene varias hojas, une las hojas compatibles."""
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    frames = []
    for sheet_name, df in sheets.items():
        if df is not None and not df.empty:
            df = df.copy()
            df["Hoja_Origen"] = sheet_name
            frames.append(df)

    if not frames:
        raise ValueError("El archivo no contiene hojas con datos.")

    return pd.concat(frames, ignore_index=True, sort=False)
