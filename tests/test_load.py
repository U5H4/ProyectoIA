"""Pruebas del LOAD del ETL: perfilado y validacion de minimos."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etl_load as L  # noqa: E402


def test_perfilar_devuelve_columnas_esperadas():
    frame = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
    perfil = L.perfilar(frame, destino="test.parquet")
    assert set(perfil.columns) >= {"destino", "columna", "tipo", "no_nulos", "nulos"}
    assert len(perfil) == 2
    fila_a = perfil.loc[perfil["columna"] == "a"].iloc[0]
    assert fila_a["nulos"] == 1
    assert fila_a["tipo"] in {"entero", "decimal"}


def test_validar_minimos_cumple():
    conteos = {
        "Flujos": ("flujos.parquet", 100, 500),
        "Reportes": ("reportes.parquet", 100, 300),
    }
    df = L.validar_minimos(conteos)
    assert set(df["cumple"]) == {"SI"}


def test_validar_minimos_lanza_si_no_cumple():
    conteos = {"Flujos": ("flujos.parquet", 1000, 500)}
    with pytest.raises(RuntimeError):
        L.validar_minimos(conteos)
