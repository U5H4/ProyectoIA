"""Pruebas de las transformaciones del ETL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etl_transform as T  # noqa: E402
from utils import DERIVADAS_T07, crear_derivada  # noqa: E402


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
def resultado(tmp_path_factory):
    # redirige el artefacto de metadatos a un tmp para no escribir el repo real
    ruta = tmp_path_factory.mktemp("metadatos") / "transformacion.json"
    original = T.TRANSFORMACION_JSON
    T.TRANSFORMACION_JSON = ruta
    try:
        datos = {"flujos": _flujos_sinteticos(), "reportes": pd.DataFrame()}
        out, tracker = T.transformar(datos)
    finally:
        T.TRANSFORMACION_JSON = original
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


def test_derivadas_t07_orden_y_nombres():
    nombres = [spec["nombre"] for spec in DERIVADAS_T07]
    assert nombres == [
        "bytes_por_paquete_fwd",
        "ratio_paquetes_bwd_fwd",
        "ratio_flag_syn",
        "tasa_bytes_fwd",
    ]


def test_crear_derivada_formula_compartida():
    frame = pd.DataFrame(
        {
            "Total Length of Fwd Packets": [10.0, 5.0, 3.0],
            "Total Fwd Packets": [2.0, 0.0, 3.0],
        }
    )
    spec = DERIVADAS_T07[0]
    salida = crear_derivada(frame, spec)
    assert list(salida) == [5.0, 0.0, 1.0]


def test_transformacion_json_persistido_y_coherente(tmp_path, monkeypatch):
    ruta = tmp_path / "transformacion.json"
    monkeypatch.setattr(T, "TRANSFORMACION_JSON", ruta)
    datos = {"flujos": _flujos_sinteticos(), "reportes": pd.DataFrame()}
    out, _ = T.transformar(datos)

    assert ruta.exists()
    cargado = json.loads(ruta.read_text(encoding="utf-8"))
    assert cargado == out["transformacion"]

    # estructura esperada
    assert {"version", "factor_winsor", "winsor_limites", "columnas_constantes", "derivadas", "columnas_escalado"} <= set(cargado)
    assert cargado["factor_winsor"] == T.IQR_FACTOR

    # derivadas: nombres en orden T07, cada una con su formula y fuentes
    derivadas = cargado["derivadas"]
    assert [d["nombre"] for d in derivadas] == [s["nombre"] for s in DERIVADAS_T07]
    assert [d["orden"] for d in derivadas] == list(range(len(DERIVADAS_T07)))
    for d, spec in zip(derivadas, DERIVADAS_T07):
        assert d["numerador"] == spec["numerador"]
        assert d["denominador"] == spec["denominador"]
        assert d["formula"]

    # limites winsor bien formados (bajo < alto) y solo para columnas reales
    columnas_train = set(out["escalado"]["columnas"]) | set(cargado["columnas_constantes"])
    for col, (bajo, alto) in cargado["winsor_limites"].items():
        assert bajo < alto
        assert col in columnas_train

    # las columnas constantes (detectadas en train, eliminadas de train/test) son strings
    assert isinstance(cargado["columnas_constantes"], list)
    assert all(isinstance(c, str) for c in cargado["columnas_constantes"])
    # y NO figuran ni como limites winsor ni en escalado
    for col in cargado["columnas_constantes"]:
        assert col not in cargado["winsor_limites"]
        assert col not in cargado["columnas_escalado"]
