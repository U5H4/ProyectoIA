"""Pruebas del modulo de Machine Learning (sin entrenar los 6 modelos completos)."""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ml  # noqa: E402
from utils import DERIVADAS_T07, crear_derivada  # noqa: E402


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


# --------------------------------------------------------------------------
# Inferencia: round-trip sobre un CSV crudo en memoria/disco
# --------------------------------------------------------------------------
_COLUMNAS_CRUDAS = [
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "SYN Flag Count",
]


def _crudo(n: int = 12, seed: int = 99) -> pd.DataFrame:
    """Flujos 'crudos' estilo CICIDS: sin derivadas, sin escalar, con etiqueta."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "Destination Port": rng.choice([80.0, 443.0, 22.0], n),
            "Flow Duration": rng.integers(100, 20000, n).astype(float),
            "Total Fwd Packets": rng.integers(1, 60, n).astype(float),
            "Total Backward Packets": rng.integers(0, 60, n).astype(float),
            "Total Length of Fwd Packets": rng.integers(10, 6000, n).astype(float),
            "SYN Flag Count": rng.integers(0, 2, n).astype(float),
            "constante_train": np.ones(n),  # era constante en ENTRENAMIENTO (T08 la elimina)
            "Label": np.where(np.arange(n) % 2, "BENIGN", "PortScan"),
            "label_raw": np.where(np.arange(n) % 2, "BENIGN", "PortScan"),
        }
    )


def _predictor_sintetico() -> dict:
    """Paquete predictor completo construido como en ml.entrenar, pero pequeno."""
    from sklearn.preprocessing import StandardScaler

    def _base(n: int) -> pd.DataFrame:
        rng = np.random.default_rng(7)
        return pd.DataFrame(
            {
                "Destination Port": rng.choice([80.0, 443.0, 22.0], n),
                "Flow Duration": rng.integers(100, 20000, n).astype(float),
                "Total Fwd Packets": rng.integers(1, 60, n).astype(float),
                "Total Backward Packets": rng.integers(0, 60, n).astype(float),
                "Total Length of Fwd Packets": rng.integers(10, 6000, n).astype(float),
                "SYN Flag Count": rng.integers(0, 2, n).astype(float),
                "constante_train": np.ones(n),
                "Label": np.where(np.arange(n) % 2, "BENIGN", "PortScan"),
            }
        )

    factor = 3.0
    features = _COLUMNAS_CRUDAS + [spec["nombre"] for spec in DERIVADAS_T07]

    # T07 (derivadas) -> T06 (winsor fit-on-train) -> T08 (drop constantes) -> T10 (escalado fit-on-train)
    base = _base(150)
    for spec in DERIVADAS_T07:
        base[spec["nombre"]] = crear_derivada(base, spec)

    limites = {}
    for col in features:
        q1, q3 = base[col].quantile(0.25), base[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            limites[col] = [float(q1 - factor * iqr), float(q3 + factor * iqr)]
    for col, (bajo, alto) in limites.items():
        base[col] = base[col].clip(lower=bajo, upper=alto)

    y = base["Label"].astype(str)
    escalador = StandardScaler().fit(base[features])
    escalado = {
        "columnas": list(features),
        "media": {c: float(m) for c, m in zip(features, escalador.mean_)},
        "desviacion": {c: float(s) for c, s in zip(features, escalador.scale_)},
    }
    base[features] = (base[features] - pd.Series(escalado["media"])) / pd.Series(escalado["desviacion"])

    modelo = DecisionTreeClassifier(max_depth=4, random_state=0).fit(base[features], y)
    transformacion = {
        "version": 1,
        "factor_winsor": factor,
        "winsor_limites": limites,
        "columnas_constantes": ["constante_train"],
        "derivadas": [
            {**spec, "formula": spec["nombre"], "orden": i} for i, spec in enumerate(DERIVADAS_T07)
        ],
        "columnas_escalado": list(features),
    }
    return {
        "modelo": modelo,
        "modelo_nombre": "Arbol de Decision",
        "features": list(features),
        "escalado": escalado,
        "transformacion": transformacion,
    }


class _Grabadora:
    """Modelo espurio: graba la X recibida y devuelve una clase constante."""

    def __init__(self) -> None:
        self.X_recibida: pd.DataFrame | None = None

    def predict(self, X):
        self.X_recibida = X
        return np.array(["PortScan"] * len(X))


def _pipeline_manual(crudo: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    """Referencia independiente del preprocesado esperado (sin pasar por ml.predecir)."""
    df = crudo.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        if col not in ("Label", "label_raw"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for spec in DERIVADAS_T07:
        if spec["nombre"] not in df.columns:
            df[spec["nombre"]] = crear_derivada(df, spec)
    for col, (bajo, alto) in paquete["transformacion"]["winsor_limites"].items():
        df[col] = df[col].clip(lower=bajo, upper=alto)
    df = df.drop(columns=[c for c in paquete["transformacion"]["columnas_constantes"] if c in df.columns])
    X = df[paquete["features"]].astype(float)
    return (X - pd.Series(paquete["escalado"]["media"])) / pd.Series(paquete["escalado"]["desviacion"])


def test_predecir_roundtrip_csv_en_disco(tmp_path):
    paquete = _predictor_sintetico()
    ruta = tmp_path / "flujos_crudos.csv"
    _crudo(12).to_csv(ruta, index=False)
    crudo = pd.read_csv(ruta)

    pred = ml.predecir(crudo, paquete)

    assert len(pred) == len(crudo)
    assert list(pred.columns)[-1] == "label_predicho"
    # etiquetas de entrada conservadas sin tocar
    assert (pred["Label"].to_numpy() == crudo["Label"].to_numpy()).all()
    assert (pred["label_raw"].to_numpy() == crudo["label_raw"].to_numpy()).all()
    # prediccion identica a la del preprocesado manual (train-fit)
    manual = _pipeline_manual(crudo, paquete)
    esperado = paquete["modelo"].predict(manual)
    assert list(pred["label_predicho"]) == list(esperado)


def test_predecir_preprocesado_identico_al_entrenamiento():
    paquete = _predictor_sintetico()
    grabadora = _Grabadora()
    paquete = {**paquete, "modelo": grabadora}
    crudo = _crudo(5)

    ml.predecir(crudo, paquete)
    X = grabadora.X_recibida

    assert X is not None
    # (e) reordenada a los features exactos del modelo
    assert list(X.columns) == paquete["features"]
    # (c) constante de train eliminada aunque el CSV la traiga
    assert "constante_train" not in X.columns
    # (a) derivadas presentes (el CSV crudo no las traia)
    for spec in DERIVADAS_T07:
        assert spec["nombre"] in X.columns
    # (b) winsor + (d) escalado: comparacion celda a celda con la referencia
    pd.testing.assert_frame_equal(
        X.reset_index(drop=True),
        _pipeline_manual(crudo, paquete).reset_index(drop=True),
        check_dtype=False,
    )


def test_predecir_aplica_winsor_antes_de_escalar():
    paquete = _predictor_sintetico()
    grabadora = _Grabadora()
    paquete = {**paquete, "modelo": grabadora}
    crudo = _crudo(3)
    crudo.loc[0, "Destination Port"] = 1e12  # muy por encima del limite de train

    ml.predecir(crudo, paquete)
    X = grabadora.X_recibida

    bajo, alto = paquete["transformacion"]["winsor_limites"]["Destination Port"]
    media = paquete["escalado"]["media"]["Destination Port"]
    desv = paquete["escalado"]["desviacion"]["Destination Port"]
    esperado = (alto - media) / desv
    assert X["Destination Port"].iloc[0] == pytest.approx(esperado, rel=1e-6, abs=1e-6)


def test_predecir_reutiliza_derivadas_si_el_csv_ya_las_trae():
    paquete = _predictor_sintetico()
    grabadora = _Grabadora()
    paquete = {**paquete, "modelo": grabadora}
    crudo = _crudo(4)
    # marcador dentro de los limites de winsor de train: si predecir recalculara
    # la derivada desde los componentes crudos el resultado NO seria ~0
    marcador = paquete["escalado"]["media"]["tasa_bytes_fwd"]
    crudo["tasa_bytes_fwd"] = marcador

    ml.predecir(crudo, paquete)
    assert grabadora.X_recibida["tasa_bytes_fwd"].iloc[0] == pytest.approx(0.0, abs=1e-6)


def test_predecir_numero_columnas_crudas_no_afecta_el_orden():
    paquete = _predictor_sintetico()
    crudo = _crudo(6)
    desordenado = crudo[list(reversed(crudo.columns))]
    assert list(ml.predecir(crudo, paquete)["label_predicho"]) == list(
        ml.predecir(desordenado, paquete)["label_predicho"]
    )


def test_predecir_sin_columnas_imprescindibles_error_claro():
    paquete = _predictor_sintetico()
    crudo = _crudo(3).drop(columns=["Flow Duration", "SYN Flag Count"])
    with pytest.raises(KeyError) as exc:
        ml.predecir(crudo, paquete)
    mensaje = str(exc.value)
    assert "Flow Duration" in mensaje
    assert "SYN Flag Count" in mensaje


def test_predecir_nan_en_variable_requerida_error_claro():
    paquete = _predictor_sintetico()
    crudo = _crudo(4)
    crudo.loc[0, "Flow Duration"] = np.nan
    with pytest.raises(ValueError, match="no finitos"):
        ml.predecir(crudo, paquete)


def test_cargar_predictor_desde_disco_y_predecir(tmp_path):
    paquete = _predictor_sintetico()
    ruta = tmp_path / "predictor.joblib"
    joblib.dump(paquete, ruta)
    cargado = ml.cargar_predictor(ruta)
    assert cargado["features"] == paquete["features"]
    crudo = _crudo(2)
    pred_disco = ml.predecir(crudo, cargado)
    assert list(pred_disco["label_predicho"]) == list(ml.predecir(crudo, paquete)["label_predicho"])


def test_cargar_predictor_incompleto_error_claro(tmp_path):
    ruta = tmp_path / "predictor.joblib"
    joblib.dump({"modelo_nombre": "roto"}, ruta)
    with pytest.raises(ValueError, match="incompleto"):
        ml.cargar_predictor(ruta)


def test_predecir_sin_metadatos_transformacion_fallback(tmp_path, monkeypatch):
    paquete = _predictor_sintetico()
    paquete = {k: v for k, v in paquete.items() if k != "transformacion"}
    monkeypatch.setattr(ml, "TRANSFORMACION_JSON", tmp_path / "no_existe.json")
    pred = ml.predecir(_crudo(3), paquete)  # derivadas T07 conocidas + escalado
    assert len(pred) == 3
