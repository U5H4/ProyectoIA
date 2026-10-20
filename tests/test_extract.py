"""Pruebas del EXTRACT del ETL (sin descargar): muestreo y perfilado."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etl_extract as E  # noqa: E402


def _frame(n_por_clase: int = 20) -> pd.DataFrame:
    filas = []
    for etiqueta in ("BENIGN", "DoS Hulk"):
        for i in range(n_por_clase):
            filas.append(
                {
                    "Label": etiqueta,
                    "Destination Port": 80,
                    "valor": i,
                }
            )
    return pd.DataFrame(filas)


def test_muestreo_por_archivo_respeta_cap():
    frame = _frame(20)
    muestra = E._muestreo_por_archivo(frame, cap=5)
    assert len(muestra) == 10
    assert set(muestra["Label"]) == {"BENIGN", "DoS Hulk"}


def test_muestreo_por_archivo_es_aleatorio_reproducible():
    frame = _frame(20)
    a = E._muestreo_por_archivo(frame, cap=5)
    b = E._muestreo_por_archivo(frame, cap=5)
    pd.testing.assert_frame_equal(a, b)


def test_muestreo_por_archivo_sin_columna_etiqueta():
    frame = pd.DataFrame({"x": [1, 2, 3]})
    assert len(E._muestreo_por_archivo(frame, cap=1)) == 3


def test_inferir_tipo_numerico_y_texto():
    assert E.inferir_tipo(pd.Series([1, 2, 3])) == "entero"
    assert E.inferir_tipo(pd.Series([1.5, 2.5])) == "decimal"
    assert E.inferir_tipo(pd.Series(["hola", "mundo"])) == "texto"
    assert E.inferir_tipo(pd.Series([], dtype=float)) == "vacio"


def test_contar_nulos_cuenta_marcadores():
    frame = pd.DataFrame({"a": ["n/a", "1", "null", "3"]})
    assert E._contar_nulos(frame) >= 2
