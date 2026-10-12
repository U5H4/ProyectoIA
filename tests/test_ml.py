"""Pruebas del modulo de Machine Learning (sin entrenar los 6 modelos completos)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ml  # noqa: E402


def _frame(n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "a": rng.normal(size=n),
            "b": rng.normal(size=n),
            "label_raw": ["BENIGN"] * n,
            "Label": ["BENIGN"] * n,
            "label": ["BENIGN" if i % 2 else "PortScan" for i in range(n)],
        }
    )


def test_separar_xy_excluye_etiquetas_y_deja_solo_numericas():
    X, y = ml.separar_xy(_frame())
    assert list(X.columns) == ["a", "b"]
    assert set(y.unique()) == {"BENIGN", "PortScan"}


def test_matriz_confusion_cuadrada_y_diagonal():
    y_true = pd.Series(["A", "A", "B", "B"])
    y_pred = np.array(["A", "A", "B", "A"])
    matriz = ml.matriz_confusion(y_true, y_pred)
    assert matriz.shape == (2, 2)
    assert matriz.loc["A", "A"] == 2
    assert matriz.loc["B", "A"] == 1


def test_importancia_devuelve_ordenada_para_arbol():
    X, y = ml.separar_xy(_frame())
    modelo = DecisionTreeClassifier(random_state=0).fit(X, y)
    imp = ml.importancia(modelo, list(X.columns))
    assert list(imp.columns) == ["variable", "importancia"]
    assert imp["importancia"].is_monotonic_decreasing
    assert set(imp["variable"]) == {"a", "b"}


def test_evaluar_modelo_devuelve_metricas_esperadas():
    X, y = ml.separar_xy(_frame(60))
    meta = {
        "modelo": DecisionTreeClassifier(random_state=0),
        "descripcion": "prueba",
        "hiperparametros": "default",
    }
    fila, pred, modelo = ml.evaluar_modelo("Arbol", meta, X, y, X, y)
    assert {"accuracy", "f1_macro", "f1_weighted", "cv_f1_macro"}.issubset(fila)
    assert len(pred) == len(y)
    assert hasattr(modelo, "predict")


def test_definir_modelos_incluye_al_menos_cuatro_algoritmos():
    modelos = ml.definir_modelos()
    assert len(modelos) >= 4
    assert "Random Forest" in modelos
    for meta in modelos.values():
        assert {"modelo", "descripcion", "hiperparametros"} == set(meta)
