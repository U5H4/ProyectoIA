"""ETAPA LOAD del ETL.

Guarda los conjuntos procesados y genera los reportes de calidad finales:
  - data/processed/flujos_clean.parquet      flujos limpios (sin escalar, para EDA)
  - data/processed/flujos_train.parquet      train estandarizado (para ML)
  - data/processed/flujos_test.parquet       test estandarizado (para ML)
  - data/processed/reportes_clean.parquet    textos listos para PNL
  - data/processed/estandarizacion.json      media/desviacion por variable
  - data/reports/perfil_columnas.csv
  - data/reports/validacion_minimos.csv

Uso:
    python src/etl_load.py
"""

from __future__ import annotations

import json

import pandas as pd

from config import (
    MIN_REGISTROS_FLUJOS,
    MIN_REGISTROS_REPORTES,
    PROCESSED,
    REPORTS,
    TARGET_COLUMN,
)
from utils import LOG, asegurar_dir, titulo

TABLA_FLUJOS = "flujos_red"
TABLA_REPORTES = "reportes_cti"

TIPOS = {
    "int64": "entero",
    "float64": "decimal",
    "object": "texto",
    "category": "categoria",
    "bool": "booleano",
}


def _tipo(dtype) -> str:
    return TIPOS.get(str(dtype), str(dtype))


def perfilar(frame: pd.DataFrame, destino: str) -> pd.DataFrame:
    filas = []
    for col in frame.columns:
        serie = frame[col]
        es_num = pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie)
        filas.append(
            {
                "destino": destino,
                "columna": col,
                "tipo": _tipo(serie.dtype),
                "no_nulos": int(serie.notna().sum()),
                "nulos": int(serie.isna().sum()),
                "valores_distintos": int(serie.nunique(dropna=False)),
                "min": str(serie.min())[:40] if es_num else "N/A",
                "max": str(serie.max())[:40] if es_num else "N/A",
            }
        )
    return pd.DataFrame(filas)


def validar_minimos(conteos: dict[str, int]) -> pd.DataFrame:
    filas = []
    incumple = []
    for info, (destino, minimo, final) in conteos.items():
        cumple = "SI" if final >= minimo else "NO"
        if cumple == "NO":
            incumple.append(info)
        filas.append(
            {
                "informacion": info,
                "destino": destino,
                "minimo_requerido": minimo,
                "registros_finales": final,
                "cumple": cumple,
                "holgura": final - minimo,
                "veces_el_minimo": round(final / minimo, 2) if minimo else 0.0,
            }
        )
    if incumple:
        raise RuntimeError(
            "El dataset final NO cumple los minimos del enunciado: " + ", ".join(incumple)
        )
    return pd.DataFrame(filas)


def cargar(resultado: dict) -> dict[str, str]:
    asegurar_dir(PROCESSED)
    asegurar_dir(REPORTS)
    print(titulo("CARGA Y PERFILADO"))

    flujos = resultado[TABLA_FLUJOS]
    train = resultado["train"]
    test = resultado["test"]
    reportes = resultado[TABLA_REPORTES]

    rutas = {
        "flujos_clean": PROCESSED / "flujos_clean.parquet",
        "flujos_train": PROCESSED / "flujos_train.parquet",
        "flujos_test": PROCESSED / "flujos_test.parquet",
        "reportes_clean": PROCESSED / "reportes_clean.parquet",
        "estandarizacion": PROCESSED / "estandarizacion.json",
        "perfil_columnas": REPORTS / "perfil_columnas.csv",
        "validacion_minimos": REPORTS / "validacion_minimos.csv",
    }

    flujos.to_parquet(rutas["flujos_clean"], index=False)
    train.to_parquet(rutas["flujos_train"], index=False)
    test.to_parquet(rutas["flujos_test"], index=False)
    if not reportes.empty:
        reportes.to_parquet(rutas["reportes_clean"], index=False)
    rutas["estandarizacion"].write_text(
        json.dumps(resultado["escalado"], indent=2, ensure_ascii=False), encoding="utf-8"
    )

    perfiles = [
        perfilar(flujos, "flujos_clean.parquet"),
        perfilar(train, "flujos_train.parquet"),
        perfilar(reportes, "reportes_clean.parquet") if not reportes.empty else pd.DataFrame(),
    ]
    perfil = pd.concat([p for p in perfiles if not p.empty], ignore_index=True)
    perfil.to_csv(rutas["perfil_columnas"], index=False, encoding="utf-8-sig")

    conteos = {
        "Flujos de red (ML)": ("flujos_clean.parquet", MIN_REGISTROS_FLUJOS, len(flujos)),
        "Reportes de texto (PNL)": ("reportes_clean.parquet", MIN_REGISTROS_REPORTES, len(reportes)),
    }
    minimos = validar_minimos(conteos)
    minimos.to_csv(rutas["validacion_minimos"], index=False, encoding="utf-8-sig")

    LOG.info("[ok] procesados en %s", PROCESSED)
    LOG.info("[ok] perfil de columnas: %d filas", len(perfil))
    for _, fila in minimos.iterrows():
        LOG.info(
            "  %-26s %6d / %6d  cumple=%s",
            fila["informacion"],
            fila["registros_finales"],
            fila["minimo_requerido"],
            fila["cumple"],
        )
    return {k: str(v) for k, v in rutas.items()}


def main() -> int:
    from etl_extract import extraer
    from etl_transform import transformar

    resultado, tracker = transformar(extraer())
    tracker.guardar()
    cargar(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
