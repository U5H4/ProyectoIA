"""ENTREGABLE 3 - Modelo de Machine Learning.

Problema: clasificacion multiclase de flujos de red de CICIDS2017 en su tipo
de riesgo (BENIGN, DoS, DDoS, PortScan, WebAttack, ...).

- Tipo de aprendizaje: supervisado.
- Variable objetivo: `label` (etiqueta de riesgo agrupada en el ETL).
- Variables de entrada: las caracteristicas numericas normalizadas del flujo.
- Algoritmos: se entrenan y comparan varios (los recomendados en el curso) y se
  conserva el de mejor F1-macro medio en validacion cruzada (sobre train), para
  no elegir el modelo mirando el conjunto de prueba (evita fuga de seleccion).

Artefactos:
    models/modelo_mejor.joblib            modelo ganador (reutilizable)
    models/<algoritmo>.joblib             cada candidato entrenado
    data/processed/predicciones_test.parquet
    data/reports/metricas_modelos.csv     comparacion de algoritmos
    data/reports/metricas_por_clase.csv   detalle del modelo ganador
    data/reports/matriz_confusion.csv
    data/reports/importancia_variables.csv
    data/figures/comparacion_modelos.html
    data/figures/matriz_confusion.html

Uso:
    python src/ml.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from config import (
    COLUMNAS_NO_FEATURE,
    CV_FOLDS,
    FIGURES,
    MODELS,
    PROCESSED,
    REPORTS,
    SEED,
    TARGET_COLUMN,
)
from utils import LOG, asegurar_dir, numero, subtitulo, tabla, titulo

TRAIN = PROCESSED / "flujos_train.parquet"
TEST = PROCESSED / "flujos_test.parquet"


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------
def cargar_split(train_path: Path = TRAIN, test_path: Path = TEST) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            f"Faltan {train_path.name}/{test_path.name}. Ejecuta antes:\n"
            r"  python src/run_all.py --sin-descargar"
        )
    return pd.read_parquet(train_path), pd.read_parquet(test_path)


def separar_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Devuelve (X, y). X solo con variables numericas predictoras."""
    features = [
        c
        for c in frame.columns
        if c not in COLUMNAS_NO_FEATURE and pd.api.types.is_numeric_dtype(frame[c])
    ]
    return frame[features].astype(float), frame[TARGET_COLUMN].astype(str)


# --------------------------------------------------------------------------
# Modelos candidatos
# --------------------------------------------------------------------------
def definir_modelos() -> dict[str, dict]:
    """Algoritmos recomendados en el curso, con su justificacion."""
    return {
        "Regresion Logistica": {
            "modelo": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
            "descripcion": "Modelo lineal; referencia simple e interpretable.",
            "hiperparametros": "C=1.0, max_iter=1000, class_weight=balanced",
        },
        "Arbol de Decision": {
            "modelo": DecisionTreeClassifier(max_depth=None, class_weight="balanced", random_state=SEED),
            "descripcion": "Reglas interpretables; sin poda puede sobreajustar.",
            "hiperparametros": "criterion=gini, max_depth=None, class_weight=balanced",
        },
        "Random Forest": {
            "modelo": RandomForestClassifier(
                n_estimators=200, class_weight="balanced", n_jobs=-1, random_state=SEED
            ),
            "descripcion": "Ensamble de arboles; robusto y da importancia de variables.",
            "hiperparametros": "n_estimators=200, class_weight=balanced",
        },
        "KNN": {
            "modelo": KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
            "descripcion": "Basado en vecinos; sensible a la escala (ya estandarizada).",
            "hiperparametros": "n_neighbors=5, distancia=euclidea",
        },
        "Gaussian Naive Bayes": {
            "modelo": GaussianNB(),
            "descripcion": "Probabilistico; muy rapido, supone independencia.",
            "hiperparametros": "var_smoothing por defecto",
        },
        "SVM (kernel RBF)": {
            "modelo": SVC(kernel="rbf", class_weight="balanced", random_state=SEED),
            "descripcion": "Frontera no lineal; potente pero costoso de entrenar.",
            "hiperparametros": "kernel=rbf, class_weight=balanced",
        },
    }


# --------------------------------------------------------------------------
# Ajuste de hiperparametros (GridSearchCV) del modelo ganador
# --------------------------------------------------------------------------
def rejillas_hiperparametros() -> dict[str, dict]:
    """Rejillas pequenas y razonables por algoritmo (busqueda acotada)."""
    return {
        "Arbol de Decision": {
            "max_depth": [None, 10, 20, 30],
            "min_samples_leaf": [1, 2, 5],
            "criterion": ["gini", "entropy"],
        },
        "Random Forest": {
            "n_estimators": [100, 200, 300],
            "max_depth": [None, 20, 30],
        },
        "KNN": {"n_neighbors": [3, 5, 7, 11], "weights": ["uniform", "distance"]},
        "Regresion Logistica": {"C": [0.1, 1.0, 10.0]},
        "SVM (kernel RBF)": {"C": [0.5, 1.0, 2.0], "gamma": ["scale", "auto"]},
        "Gaussian Naive Bayes": {"var_smoothing": [1e-9, 1e-8, 1e-7]},
    }


def ajustar_hiperparametros(
    nombre: str, X_train: pd.DataFrame, y_train: pd.Series
) -> tuple[object, dict, float]:
    """Busca los mejores hiperparametros con validacion cruzada sobre train."""
    rejilla = rejillas_hiperparametros().get(nombre)
    base = definir_modelos()[nombre]["modelo"]
    if not rejilla:
        return base, {}, float("nan")
    busqueda = GridSearchCV(
        base,
        rejilla,
        scoring="f1_macro",
        cv=StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED),
        n_jobs=-1,
    )
    busqueda.fit(X_train, y_train)
    LOG.info(
        "  [grid] %s -> %s (cv_f1_macro=%.4f)", nombre, busqueda.best_params_, busqueda.best_score_
    )
    return busqueda.best_estimator_, busqueda.best_params_, float(busqueda.best_score_)


def _slug(nombre: str) -> str:
    return (
        nombre.lower()
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


# --------------------------------------------------------------------------
# Entrenamiento y evaluacion
# --------------------------------------------------------------------------
def evaluar_modelo(
    nombre: str, meta: dict, X_train: pd.DataFrame, y_train: pd.Series,
    X_test: pd.DataFrame, y_test: pd.Series,
) -> tuple[dict, np.ndarray, object]:
    modelo = meta["modelo"]
    inicio = time.perf_counter()
    modelo.fit(X_train, y_train)
    pred = modelo.predict(X_test)
    segundos = time.perf_counter() - inicio

    acc = accuracy_score(y_test, pred)
    p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(
        y_test, pred, average="macro", zero_division=0
    )
    _, _, f_weighted, _ = precision_recall_fscore_support(
        y_test, pred, average="weighted", zero_division=0
    )
    cv = cross_val_score(
        meta["modelo"], X_train, y_train,
        cv=StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED),
        scoring="f1_macro", n_jobs=-1,
    )

    LOG.info(
        "  %-22s acc=%.3f  f1_macro=%.3f  f1_weighted=%.3f  cv=%.3f  (%.1fs)",
        nombre, acc, f_macro, f_weighted, float(np.mean(cv)), segundos,
    )
    fila = {
        "modelo": nombre,
        "descripcion": meta["descripcion"],
        "hiperparametros": meta["hiperparametros"],
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(p_macro), 4),
        "recall_macro": round(float(r_macro), 4),
        "f1_macro": round(float(f_macro), 4),
        "f1_weighted": round(float(f_weighted), 4),
        "cv_f1_macro": round(float(np.mean(cv)), 4),
        "cv_desviacion": round(float(np.std(cv)), 4),
        "segundos": round(segundos, 2),
    }
    return fila, pred, modelo


def matriz_confusion(y_true: pd.Series, y_pred: np.ndarray) -> pd.DataFrame:
    etiquetas = sorted(set(y_true).union(set(y_pred)))
    matriz = confusion_matrix(y_true, y_pred, labels=etiquetas)
    return pd.DataFrame(matriz, index=etiquetas, columns=etiquetas)


def importancia(modelo, features: list[str], X: pd.DataFrame | None = None, y: pd.Series | None = None) -> pd.DataFrame:
    if hasattr(modelo, "feature_importances_"):
        valores = modelo.feature_importances_
    elif hasattr(modelo, "coef_"):
        valores = np.abs(np.atleast_2d(modelo.coef_)).mean(axis=0)
    else:
        valores = _importancia_por_permutacion(modelo, features, X, y)
    df = pd.DataFrame({"variable": features, "importancia": valores})
    return df.sort_values("importancia", ascending=False).reset_index(drop=True)


def _importancia_por_permutacion(
    modelo, features: list[str], X: pd.DataFrame | None, y: pd.Series | None
) -> np.ndarray:
    """Importancia por permutacion para modelos sin coeficientes (KNN, NB, SVM)."""
    if X is None or y is None or X.empty:
        return np.zeros(len(features))
    from sklearn.inspection import permutation_importance

    resultado = permutation_importance(
        modelo, X, y, n_repeats=5, random_state=SEED, scoring="f1_macro", n_jobs=-1
    )
    return np.clip(resultado.importances_mean, 0, None)


# --------------------------------------------------------------------------
# Figuras (opcionales; no rompen si falta plotly)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Figuras (opcionales; no rompen si falta plotly)
# --------------------------------------------------------------------------
def _guardar_figuras(metricas: pd.DataFrame, matriz: pd.DataFrame, mejor: str) -> None:
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except Exception:
        LOG.warning("  plotly no disponible: se omiten las figuras")
        return
    asegurar_dir(FIGURES)

    figura = px.bar(
        metricas.sort_values("f1_macro"),
        x="f1_macro", y="modelo", orientation="h",
        title="Comparacion de algoritmos (F1-macro en prueba)",
        labels={"f1_macro": "F1-macro", "modelo": ""}, text="f1_macro",
    )
    figura.write_html(FIGURES / "comparacion_modelos.html", include_plotlyjs="cdn")

    heatmap = go.Figure(
        data=go.Heatmap(
            z=matriz.to_numpy(), x=list(matriz.columns), y=list(matriz.index),
            colorscale="Blues", text=matriz.to_numpy(), texttemplate="%{text}",
        )
    )
    heatmap.update_layout(
        title=f"Matriz de confusion - {mejor}", xaxis_title="Predicho", yaxis_title="Real"
    )
    heatmap.write_html(FIGURES / "matriz_confusion.html", include_plotlyjs="cdn")


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def entrenar(
    train: pd.DataFrame | None = None,
    test: pd.DataFrame | None = None,
) -> dict:
    if train is None or test is None:
        train, test = cargar_split()
    X_train, y_train = separar_xy(train)
    X_test, y_test = separar_xy(test)

    print(titulo("MACHINE LEARNING - CLASIFICACION DE FLUJOS DE RED"))
    LOG.info(
        "  train=%s  test=%s  variables=%d  clases=%d",
        numero(len(X_train)), numero(len(X_test)), X_train.shape[1], y_train.nunique(),
    )

    resultados = []
    predicciones: dict[str, np.ndarray] = {}
    entrenados: dict[str, object] = {}
    for nombre, meta in definir_modelos().items():
        fila, pred, modelo = evaluar_modelo(nombre, meta, X_train, y_train, X_test, y_test)
        resultados.append(fila)
        predicciones[nombre] = pred
        entrenados[nombre] = modelo

    metricas = (
        pd.DataFrame(resultados)
        .sort_values(["cv_f1_macro", "f1_macro"], ascending=False)
        .reset_index(drop=True)
    )
    mejor = metricas.iloc[0]["modelo"]
    LOG.info(
        "  modelo ganador: %s (cv_f1_macro=%.4f  f1_macro_test=%.4f)",
        mejor, metricas.iloc[0]["cv_f1_macro"], metricas.iloc[0]["f1_macro"],
    )

    LOG.info("  ajustando hiperparametros del ganador con GridSearchCV...")
    modelo_final, mejores_params, cv_ajustado = ajustar_hiperparametros(mejor, X_train, y_train)
    modelo_final.fit(X_train, y_train)
    predicciones[mejor] = modelo_final.predict(X_test)
    entrenados[mejor] = modelo_final
    fila = metricas.index[metricas["modelo"] == mejor][0]
    metricas.loc[fila, "hiperparametros"] = (
        json.dumps(mejores_params, ensure_ascii=False) if mejores_params else metricas.loc[fila, "hiperparametros"]
    )
    if mejores_params:
        metricas.loc[fila, "cv_f1_macro"] = round(cv_ajustado, 4)

    asegurar_dir(MODELS)
    asegurar_dir(REPORTS)
    for nombre, modelo in entrenados.items():
        joblib.dump(modelo, MODELS / f"{_slug(nombre)}.joblib")
    joblib.dump(entrenados[mejor], MODELS / "modelo_mejor.joblib")
    _guardar_predictor(entrenados[mejor], mejor, X_train)

    matriz = matriz_confusion(y_test, predicciones[mejor])
    reporte = classification_report(y_test, predicciones[mejor], output_dict=True, zero_division=0)
    por_clase = (
        pd.DataFrame(reporte).transpose()
        .reset_index().rename(columns={"index": "clase"})
    )
    imp = importancia(entrenados[mejor], list(X_train.columns), X_test, y_test)

    acc_final = accuracy_score(y_test, predicciones[mejor])
    _, _, f_macro_final, _ = precision_recall_fscore_support(
        y_test, predicciones[mejor], average="macro", zero_division=0
    )
    _, _, f_weighted_final, _ = precision_recall_fscore_support(
        y_test, predicciones[mejor], average="weighted", zero_division=0
    )
    metricas.loc[fila, "accuracy"] = round(float(acc_final), 4)
    metricas.loc[fila, "f1_macro"] = round(float(f_macro_final), 4)
    metricas.loc[fila, "f1_weighted"] = round(float(f_weighted_final), 4)

    metricas.to_csv(REPORTS / "metricas_modelos.csv", index=False, encoding="utf-8-sig")
    por_clase.to_csv(REPORTS / "metricas_por_clase.csv", index=False, encoding="utf-8-sig")
    matriz.to_csv(REPORTS / "matriz_confusion.csv", encoding="utf-8-sig")
    imp.to_csv(REPORTS / "importancia_variables.csv", index=False, encoding="utf-8-sig")

    pred_df = pd.DataFrame(
        {
            "label_real": y_test.to_numpy(),
            "label_predicho": predicciones[mejor],
            "acierto": (y_test.to_numpy() == predicciones[mejor]),
        }
    )
    pred_df.to_parquet(PROCESSED / "predicciones_test.parquet", index=False)

    _guardar_figuras(metricas, matriz, mejor)

    resumen = {
        "modelo_mejor": mejor,
        "accuracy": float(acc_final),
        "f1_macro": float(f_macro_final),
        "cv_f1_macro": float(metricas.loc[fila, "cv_f1_macro"]),
        "hiperparametros": mejores_params,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "variables": int(X_train.shape[1]),
        "clases": sorted(y_train.unique().tolist()),
    }
    (REPORTS / "ml_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"metricas": metricas, "matriz": matriz, "por_clase": por_clase, "importancia": imp, "resumen": resumen}


# --------------------------------------------------------------------------
# Inferencia (modelo reutilizable)
# --------------------------------------------------------------------------
def _guardar_predictor(modelo, nombre: str, X_train: pd.DataFrame) -> Path:
    """Empaqueta el modelo ganador, el orden de variables y los parametros de
    escalado (leidos de estandarizacion.json) en un unico artefacto."""
    escalado = _leer_estandarizacion()
    paquete = {
        "modelo": modelo,
        "modelo_nombre": nombre,
        "features": list(X_train.columns),
        "escalado": escalado,
    }
    ruta = MODELS / "predictor.joblib"
    joblib.dump(paquete, ruta)
    LOG.info("  predictor reutilizable guardado en %s", ruta)
    return ruta


def _leer_estandarizacion() -> dict:
    ruta = PROCESSED / "estandarizacion.json"
    if not ruta.exists():
        return {"columnas": [], "media": {}, "desviacion": {}}
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_predictor(ruta: Path | None = None) -> dict:
    ruta = ruta or (MODELS / "predictor.joblib")
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta.name}. Entrena primero:\n  python src/run_all.py --sin-descargar --solo etl ml"
        )
    return joblib.load(ruta)


def predecir(frame: pd.DataFrame, predictor: dict | None = None) -> pd.DataFrame:
    """Aplica el modelo ganador a flujos crudos (sin escalar).

    Reutiliza los parametros de estandarizacion guardados (media/desviacion) y
    luego el modelo. Devuelve el flujo con la clase predicha.
    """
    predictor = predictor or cargar_predictor()
    escalado = predictor["escalado"]
    media = pd.Series(escalado.get("media", {}))
    desv = pd.Series(escalado.get("desviacion", {}))

    datos = frame.copy()
    for col in escalado.get("columnas", []):
        if col in datos.columns and col in media.index and col in desv.index and desv[col] != 0:
            datos[col] = (datos[col].astype(float) - media[col]) / desv[col]

    features = predictor["features"]
    faltantes = [c for c in features if c not in datos.columns]
    if faltantes:
        raise KeyError(f"Faltan variables requeridas por el modelo: {faltantes[:5]}...")
    X = datos[features].astype(float)
    pred = predictor["modelo"].predict(X)
    datos["label_predicho"] = pred
    return datos


def main() -> int:
    resultado = entrenar()
    metricas = resultado["metricas"]
    print(subtitulo("Comparacion de algoritmos"))
    print(tabla(metricas[["modelo", "accuracy", "f1_macro", "f1_weighted", "cv_f1_macro", "segundos"]]))
    print(subtitulo("Mejores variables del modelo ganador"))
    print(tabla(resultado["importancia"].head(10)))
    LOG.info("[ok] modelo ganador guardado en %s", MODELS / "modelo_mejor.joblib")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
