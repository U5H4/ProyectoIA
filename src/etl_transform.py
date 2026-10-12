"""ETAPA TRANSFORM del ETL.

Aplica las 10 transformaciones obligatorias sobre las fuentes extraidas y
deja evidencia de cada una en el CalidadTracker:

  T01 Eliminacion de duplicados
  T02 Normalizacion de texto
  T03 Correccion de tipos
  T04 Tratamiento de valores faltantes e infinitos
  T05 Validacion y agrupacion de etiquetas (variable objetivo)
  T06 Tratamiento de valores atipicos (winsorizacion IQR)
  T07 Creacion de nuevas variables (campos derivados)
  T08 Seleccion de caracteristicas
  T09 Muestreo y balanceo de clases
  T10 Division de datos y estandarizacion (fit sobre train)

Sobre los reportes de texto se aplica limpieza de texto (mismo tracker).

Uso:
    python src/etl_transform.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import (
    CTI_MAX_CHARS,
    CTI_MIN_TEXT_LEN,
    DEFAULT_MAX_PER_CLASS,
    DEFAULT_SAMPLE_SIZE,
    IQR_FACTOR,
    LABEL_GROUPS,
    RAW_LABEL_COLUMN,
    SEED,
    TARGET_COLUMN,
    TEST_SIZE,
)
from utils import LOG, CalidadTracker, titulo

TABLA_FLUJOS = "flujos_red"
TABLA_REPORTES = "reportes_cti"


# --------------------------------------------------------------------------
# Primitivas reutilizables (probadas en tests/test_transform.py)
# --------------------------------------------------------------------------
def normalizar_etiqueta(valor: object) -> str:
    """Unifica guiones unicode (incluye el caracter de reemplazo U+FFFD) y espacios."""
    texto = str(valor)
    for guion in ("\u2012", "\u2013", "\u2014", "\u2015", "\u2212", "\ufffd"):
        texto = texto.replace(guion, "-")
    return " ".join(texto.split())


def _norm(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()


def _columnas_feature(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in (TARGET_COLUMN, "label_raw", RAW_LABEL_COLUMN)]


def winsorizar(frame: pd.DataFrame, columnas: list[str], factor: float = IQR_FACTOR) -> int:
    """Recorta valores fuera de [Q1 - f*IQR, Q3 + f*IQR]. Devuelve celdas recortadas."""
    afectados = 0
    for col in columnas:
        serie = frame[col].astype(float)
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        bajo, alto = q1 - factor * iqr, q3 + factor * iqr
        fuera = (serie < bajo) | (serie > alto)
        afectados += int(fuera.sum())
        frame[col] = serie.clip(lower=bajo, upper=alto)
    return afectados


# --------------------------------------------------------------------------
# Transformaciones
# --------------------------------------------------------------------------
def t01_eliminar_duplicados(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    frame = frame.drop_duplicates().reset_index(drop=True)
    d[TABLA_FLUJOS] = frame
    t.registrar(
        1, "Eliminacion de duplicados", TABLA_FLUJOS, antes, len(frame),
        antes - len(frame), "Duplicados exactos de flujo", "drop_duplicates()",
    )


def t02_normalizar_texto(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    original = frame[RAW_LABEL_COLUMN].astype(str)
    normalizada = original.map(normalizar_etiqueta)
    d[TABLA_FLUJOS] = frame.assign(label_raw=normalizada)
    cambiados = int((original != normalizada).sum())
    t.registrar(
        2, "Normalizacion de texto", TABLA_FLUJOS, antes, len(frame), cambiados,
        "strip de columnas y espacios; guiones unicode -> ascii en etiquetas",
        "str.strip() / replace('\\u2013','-')",
    )


def t03_corregir_tipos(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    features = _columnas_feature(frame)
    no_numericas = int(
        sum(frame[col].apply(lambda v: pd.to_numeric(v, errors="coerce")).isna().sum()
        for col in features)
    )
    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")
    d[TABLA_FLUJOS] = frame
    t.registrar(
        3, "Correccion de tipos", TABLA_FLUJOS, antes, len(frame), no_numericas,
        f"{len(features)} variables numericas forzadas con pd.to_numeric(errors='coerce')",
        "CAST explicito a float",
    )


def t04_faltantes_inf(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    features = _columnas_feature(frame)
    inf = int(np.isinf(frame[features].to_numpy(dtype=float, na_value=np.nan)).sum())
    frame = frame.replace([np.inf, -np.inf], np.nan)
    despues = frame.dropna(subset=features).reset_index(drop=True)
    d[TABLA_FLUJOS] = despues
    t.registrar(
        4, "Tratamiento de faltantes e infinitos", TABLA_FLUJOS, antes, len(despues),
        antes - len(despues), f"{inf} celdas inf/nan descartadas por flujo incompleto",
        "replace(inf, NaN) + dropna()",
    )


def t05_etiquetas(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    frame = frame.assign(label=frame["label_raw"].map(LABEL_GROUPS))
    desconocidas = int(frame[TARGET_COLUMN].isna().sum())
    frame = frame.dropna(subset=[TARGET_COLUMN]).reset_index(drop=True)
    frame[TARGET_COLUMN] = frame[TARGET_COLUMN].astype("category")
    d[TABLA_FLUJOS] = frame
    d["clases"] = sorted(frame[TARGET_COLUMN].astype(str).unique())
    t.registrar(
        5, "Validacion y agrupacion de etiquetas", TABLA_FLUJOS, antes, len(frame),
        desconocidas, f"{len(d['clases'])} clases objetivo: {', '.join(d['clases'])}",
        "map(LABEL_GROUPS) - codificacion categorica del target",
    )


def t06_atipicos(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    features = _columnas_feature(frame)
    afectados = winsorizar(frame, features)
    d[TABLA_FLUJOS] = frame
    t.registrar(
        6, "Tratamiento de valores atipicos", TABLA_FLUJOS, antes, len(frame), afectados,
        f"winsorizacion IQR factor {IQR_FACTOR} sobre {len(features)} variables",
        "clip([Q1 - f*IQR, Q3 + f*IQR])",
    )


def t07_derivadas(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    nuevas = []

    def _ratio(num: str, den: str, nombre: str) -> None:
        if num in frame.columns and den in frame.columns:
            frame[nombre] = (frame[num] / frame[den].replace(0, np.nan)).fillna(0.0)
            nuevas.append(nombre)

    _ratio("Total Length of Fwd Packets", "Total Fwd Packets", "bytes_por_paquete_fwd")
    _ratio("Total Backward Packets", "Total Fwd Packets", "ratio_paquetes_bwd_fwd")
    _ratio("SYN Flag Count", "Total Fwd Packets", "ratio_flag_syn")
    _ratio("Total Length of Fwd Packets", "Flow Duration", "tasa_bytes_fwd")

    d[TABLA_FLUJOS] = frame
    t.registrar(
        7, "Creacion de variables derivadas", TABLA_FLUJOS, antes, len(frame), len(nuevas),
        f"variables creadas: {', '.join(nuevas) if nuevas else 'ninguna'}",
        "ratios de flujo (bytes/paquete, flags, tasa)",
    )


def t08_seleccion(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    features_antes = _columnas_feature(frame)
    constantes = [c for c in features_antes if frame[c].nunique(dropna=False) <= 1]
    frame = frame.drop(columns=constantes)
    d[TABLA_FLUJOS] = frame
    t.registrar(
        8, "Seleccion de caracteristicas", TABLA_FLUJOS, len(features_antes), len(_columnas_feature(frame)),
        len(constantes), f"{len(constantes)} variables constantes eliminadas",
        "drop columnas con varianza cero",
    )


def t09_muestreo(d: dict, t: CalidadTracker, sample_size: int, max_per_class: int) -> None:
    frame = d[TABLA_FLUJOS]
    antes = len(frame)
    clases = sorted(frame[TARGET_COLUMN].astype(str).unique())
    por_clase = min(max_per_class, max(1, sample_size // max(len(clases), 1)))
    partes = [
        frame.loc[frame[TARGET_COLUMN].astype(str) == c].head(por_clase)
        for c in clases
    ]
    frame = pd.concat(partes, ignore_index=True).sample(frac=1.0, random_state=SEED)
    d[TABLA_FLUJOS] = frame.reset_index(drop=True)
    t.registrar(
        9, "Muestreo y balanceo de clases", TABLA_FLUJOS, antes, len(frame),
        antes - len(frame), f"hasta {por_clase} registros por clase ({len(clases)} clases)",
        "muestreo estratificado por clase",
    )


def t10_division_escalado(d: dict, t: CalidadTracker) -> None:
    frame = d[TABLA_FLUJOS]
    train, test = train_test_split(
        frame, test_size=TEST_SIZE, random_state=SEED, stratify=frame[TARGET_COLUMN]
    )
    features = _columnas_feature(train)
    escalador = StandardScaler()
    columnas = [c for c in features if pd.api.types.is_numeric_dtype(train[c])]
    train = train.copy()
    test = test.copy()
    train[columnas] = escalador.fit_transform(train[columnas])
    test[columnas] = escalador.transform(test[columnas])

    d["train"] = train.reset_index(drop=True)
    d["test"] = test.reset_index(drop=True)
    d["escalado"] = {
        "columnas": columnas,
        "media": dict(zip(columnas, escalador.mean_.round(6).tolist())),
        "desviacion": dict(zip(columnas, escalador.scale_.round(6).tolist())),
    }
    t.registrar(
        10, "Division de datos y estandarizacion", TABLA_FLUJOS, len(frame), len(train) + len(test),
        0, f"train={len(train)} / test={len(test)} (estratificado {int((1-TEST_SIZE)*100)}/{int(TEST_SIZE*100)})",
        "train_test_split(stratify) + StandardScaler.fit_transform(train)",
    )


def limpiar_reportes(d: dict, t: CalidadTracker) -> None:
    frame = d.get(TABLA_REPORTES)
    if frame is None or frame.empty:
        return
    antes = len(frame)
    frame = frame.copy()
    frame["text"] = _norm(frame["text"])
    sin_dup = frame.drop_duplicates(subset=["text"]).reset_index(drop=True)
    t.registrar(
        1, "Eliminacion de duplicados", TABLA_REPORTES, antes, len(sin_dup),
        antes - len(sin_dup), "textos repetidos", "drop_duplicates('text')",
    )
    largos = sin_dup["text"].str.len() > CTI_MIN_TEXT_LEN
    limpio = sin_dup.loc[largos].reset_index(drop=True)
    t.registrar(
        2, "Normalizacion de texto", TABLA_REPORTES, len(sin_dup), len(limpio),
        int((~largos).sum()), "colapso de espacios y descarte de textos muy cortos",
        f"len(text) > {CTI_MIN_TEXT_LEN}",
    )
    limpio["text"] = limpio["text"].str.slice(0, CTI_MAX_CHARS)
    d[TABLA_REPORTES] = limpio
    t.registrar(
        3, "Correccion de tipo / truncado", TABLA_REPORTES, len(limpio), len(limpio),
        int((limpio["text"].str.len() >= CTI_MAX_CHARS).sum()),
        f"textos truncados a {CTI_MAX_CHARS} caracteres", "str.slice()",
    )


# --------------------------------------------------------------------------
# Orquestador de la etapa
# --------------------------------------------------------------------------
def transformar(
    datos: dict,
    tracker: CalidadTracker | None = None,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    max_per_class: int = DEFAULT_MAX_PER_CLASS,
) -> tuple[dict, CalidadTracker]:
    tracker = tracker or CalidadTracker()
    d = {
        TABLA_FLUJOS: datos["flujos"].copy(),
        TABLA_REPORTES: datos.get("reportes", pd.DataFrame()).copy(),
    }
    print(titulo("TRANSFORMACIONES"))
    t01_eliminar_duplicados(d, tracker)
    t02_normalizar_texto(d, tracker)
    t03_corregir_tipos(d, tracker)
    t04_faltantes_inf(d, tracker)
    t05_etiquetas(d, tracker)
    t06_atipicos(d, tracker)
    t07_derivadas(d, tracker)
    t08_seleccion(d, tracker)
    t09_muestreo(d, tracker, sample_size, max_per_class)
    t10_division_escalado(d, tracker)
    limpiar_reportes(d, tracker)
    return d, tracker


def main() -> int:
    from etl_extract import extraer

    datos = extraer()
    resultado, tracker = transformar(datos)
    ruta = tracker.guardar()
    LOG.info("[ok] evidencia de transformaciones en %s", ruta)
    LOG.info(
        "flujos=%d train=%d test=%d reportes=%d",
        len(resultado[TABLA_FLUJOS]),
        len(resultado["train"]),
        len(resultado["test"]),
        len(resultado[TABLA_REPORTES]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
