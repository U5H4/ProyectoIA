"""Utilidades comunes: logging, tracker de calidad y formateo de tablas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from config import LOGS, REPORTS

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
def setup_logging(nombre: str = "pipeline") -> logging.Logger:
    """Crea un logger con salida a consola y a logs/pipeline.log."""
    LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    consola = logging.StreamHandler()
    consola.setFormatter(logging.Formatter("%(levelname)-7s | %(message)s"))
    logger.addHandler(consola)

    archivo = logging.FileHandler(LOGS / "pipeline.log", encoding="utf-8")
    archivo.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    logger.addHandler(archivo)
    return logger


LOG = setup_logging()


# --------------------------------------------------------------------------
# Tracker de calidad: deja evidencia auditable de cada transformacion.
# --------------------------------------------------------------------------
@dataclass
class RegistroCalidad:
    orden_ejecucion: int
    paso: int
    transformacion: str
    tabla: str
    filas_antes: int
    filas_despues: int
    registros_afectados: int
    detalle: str
    regla: str = ""


@dataclass
class CalidadTracker:
    registros: list[RegistroCalidad] = field(default_factory=list)
    _contador: int = 0

    def registrar(
        self,
        paso: int,
        transformacion: str,
        tabla: str,
        filas_antes: int,
        filas_despues: int,
        afectados: int,
        detalle: str,
        regla: str = "",
    ) -> None:
        self._contador += 1
        self.registros.append(
            RegistroCalidad(
                orden_ejecucion=self._contador,
                paso=paso,
                transformacion=transformacion,
                tabla=tabla,
                filas_antes=filas_antes,
                filas_despues=filas_despues,
                registros_afectados=afectados,
                detalle=detalle,
                regla=regla,
            )
        )
        LOG.info(
            "  #%-2d [T%02d] %-34s %-22s %7d -> %7d (%+d)",
            self._contador,
            paso,
            transformacion,
            tabla,
            filas_antes,
            filas_despues,
            filas_despues - filas_antes,
        )

    def a_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([r.__dict__ for r in self.registros])

    def guardar(self, ruta: Path | None = None) -> Path:
        destino = ruta or (REPORTS / "calidad_transformaciones.csv")
        asegurar_dir(destino.parent)
        self.a_dataframe().to_csv(destino, index=False, encoding="utf-8-sig")
        return destino


# --------------------------------------------------------------------------
# Formateo
# --------------------------------------------------------------------------
def asegurar_dir(ruta: Path) -> Path:
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def titulo(texto: str, ancho: int = 78) -> str:
    return f"\n{'=' * ancho}\n{texto}\n{'=' * ancho}"


def subtitulo(texto: str, ancho: int = 78) -> str:
    return f"\n{texto}\n{'-' * ancho}"


def numero(valor, dec: int = 0) -> str:
    try:
        return f"{float(valor):,.{dec}f}"
    except (TypeError, ValueError):
        return "N/A"


def tabla(df: pd.DataFrame, decimales: int = 2) -> str:
    if df is None or df.empty:
        return "  (sin datos)"
    columnas = [str(c) for c in df.columns]
    filas = []
    for _, fila in df.iterrows():
        celdas = []
        for valor in fila:
            if isinstance(valor, float):
                celdas.append(f"{valor:,.{decimales}f}")
            else:
                celdas.append(str(valor))
        filas.append(celdas)
    anchos = [
        max(len(columnas[i]), *(len(f[i]) for f in filas))
        for i in range(len(columnas))
    ]
    sep = "-+-".join("-" * a for a in anchos)
    lineas = [" | ".join(c.ljust(anchos[i]) for i, c in enumerate(columnas)), sep]
    lineas += [" | ".join(c.ljust(anchos[i]) for i, c in enumerate(fila)) for fila in filas]
    return "\n".join(lineas)
