"""Pruebas de las transformaciones del ETL."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etl_transform as T  # noqa: E402


def _flujos_sinteticos() -> pd.DataFrame:
    base = {
        "Destination Port": [80, 443, 22, 21, 8080, 53],
        "Flow Duration": [100, 200, 300, 400, 500, 600],
        "Total Fwd Packets": [10, 20, 30, 40, 50, 60],
        "Total Backward Packets": [5, 10, 15, 20, 25, 30],
        "Total Length of Fwd Packets": [1000, 2000, 3000, 4000, 5000, 6000],
        "SYN Flag Count": [0, 1, 0, 1, 0, 1],
    }
    filas = []
    for etiqueta in ("BENIGN", "PortScan"):
        for i in range(10):
            fila = {k: float(v[i % len(v)]) for k, v in base.items()}
            fila["Label"] = etiqueta
            filas.append(fila)
    frame = pd.DataFrame(filas)
    frame.loc[0, "Flow Duration"] = np.inf
    frame.loc[1, "Total Fwd Packets"] = np.nan
    frame = pd.concat([frame, frame.iloc[[2]]], ignore_index=True)
    return frame


def test_normalizar_etiqueta_unicode():
    assert T.normalizar_etiqueta("Web Attack \u2013 Brute Force") == "Web Attack - Brute Force"
    assert T.normalizar_etiqueta("Web Attack \ufffd XSS") == "Web Attack - XSS"
    assert T.normalizar_etiqueta("  DoS   Hulk ") == "DoS Hulk"


def test_winsorizar_recorta_atipicos():
    frame = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]})
    afectados = T.winsorizar(frame, ["x"], factor=3.0)
    assert afectados >= 1
    assert frame["x"].max() < 1000


@pytest.fixture(scope="module")
def resultado():
    datos = {"flujos": _flujos_sinteticos(), "reportes": pd.DataFrame()}
    out, tracker = T.transformar(datos)
    return out, tracker


def test_pipeline_registra_transformaciones(resultado):
    _, tracker = resultado
    pasos = {r.paso for r in tracker.registros}
    assert {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}.issubset(pasos)


def test_etiquetas_agrupadas(resultado):
    out, _ = resultado
    clases = set(out["flujos_red"]["label"].astype(str).unique())
    assert clases == {"BENIGN", "PortScan"}


def test_division_estratificada_y_escalado(resultado):
    out, _ = resultado
    assert not out["train"].empty and not out["test"].empty
    assert "label" in out["train"].columns
    assert out["escalado"]["columnas"]
    media = out["train"][out["escalado"]["columnas"]].mean().abs().max()
    assert media < 1e-6
