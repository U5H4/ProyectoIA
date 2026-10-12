"""Orquestador del pipeline.

Ejecuta las etapas en orden y se detiene en la primera que falle.

Uso:
    python src/run_all.py                  # pipeline completo
    python src/run_all.py --listar
    python src/run_all.py --sin-descargar  # reutiliza data/raw ya descargado
    python src/run_all.py --solo ml pnl
    python src/run_all.py --con-tests
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ALL_DIRS  # noqa: E402
from utils import LOG, asegurar_dir, tabla, titulo  # noqa: E402


@dataclass
class Etapa:
    clave: str
    nombre: str
    fn: Callable[[], object]
    obligatoria: bool = True


# --------------------------------------------------------------------------
# Etapas
# --------------------------------------------------------------------------
def etapa_descargar() -> int:
    import etl_extract

    return etl_extract.descargar("all", None, accept_license=True)


def etapa_etl() -> int:
    from etl_extract import extraer
    from etl_load import cargar
    from etl_transform import transformar

    datos = extraer()
    resultado, tracker = transformar(datos)
    tracker.guardar()
    cargar(resultado)
    return 0


def etapa_ml() -> int:
    from ml import entrenar

    entrenar()
    return 0


def etapa_pnl() -> int:
    from pnl import analizar

    analizar()
    return 0


def etapa_blockchain() -> int:
    from blockchain import ejecutar

    ejecutar()
    return 0


def etapa_tests() -> int:
    return subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"]).returncode


ETAPAS = [
    Etapa("descargar", "Descargar datos crudos (CICIDS2017 + reportes CTI)", etapa_descargar),
    Etapa("etl", "ETL: extraer, transformar, cargar", etapa_etl),
    Etapa("ml", "Machine Learning: entrenar y evaluar modelos", etapa_ml),
    Etapa("pnl", "PNL: analizar reportes de amenazas", etapa_pnl),
    Etapa("blockchain", "Blockchain: registrar y verificar resultados", etapa_blockchain),
    Etapa("tests", "Suite de pruebas", etapa_tests, obligatoria=False),
]


# --------------------------------------------------------------------------
# Ejecucion
# --------------------------------------------------------------------------
def _resumen(resultados: list[dict]) -> None:
    print(titulo("RESUMEN DE EJECUCION"))
    print(tabla(pd.DataFrame(resultados)))


def ejecutar(claves: list[str]) -> int:
    elegidas = [e for e in ETAPAS if e.clave in claves]
    if not elegidas:
        LOG.error("No hay etapas que ejecutar")
        return 2

    asegurar_dir(Path(__file__).resolve().parent)  # noqa: F841
    for directorio in ALL_DIRS:
        asegurar_dir(directorio)

    resultados = []
    for etapa in elegidas:
        print(titulo(f"ETAPA: {etapa.nombre}"))
        inicio = time.perf_counter()
        salida = None
        try:
            salida = etapa.fn()
            estado = "OK"
        except Exception:
            traceback.print_exc()
            estado = "FALLO"
        segundos = round(time.perf_counter() - inicio, 2)
        if isinstance(salida, int) and salida != 0 and estado == "OK":
            estado = "FALLO"
        resultados.append({"etapa": etapa.clave, "estado": estado, "segundos": segundos})
        LOG.info("etapa '%s' -> %s (%.2fs)", etapa.clave, estado, segundos)
        if estado == "FALLO":
            _resumen(resultados)
            return 1

    _resumen(resultados)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listar", action="store_true", help="Lista las etapas y sale.")
    parser.add_argument("--solo", nargs="+", default=None, help="Ejecuta solo estas etapas.")
    parser.add_argument("--sin-descargar", action="store_true", help="Omite la etapa de descarga.")
    parser.add_argument("--con-tests", action="store_true", help="Anade la suite de pruebas.")
    args = parser.parse_args(argv)

    if args.listar:
        filas = [
            {"clave": e.clave, "etapa": e.nombre, "obligatoria": e.obligatoria}
            for e in ETAPAS
        ]
        print(tabla(pd.DataFrame(filas)))
        return 0

    if args.solo:
        disponibles = {e.clave for e in ETAPAS}
        desconocidas = [c for c in args.solo if c not in disponibles]
        if desconocidas:
            LOG.error("Etapa(s) desconocida(s): %s", ", ".join(desconocidas))
            return 2
        claves = [e.clave for e in ETAPAS if e.clave in args.solo]
    else:
        claves = [e.clave for e in ETAPAS if e.obligatoria]

    if args.sin_descargar:
        claves = [c for c in claves if c != "descargar"]
    if args.con_tests and "tests" not in claves:
        claves.append("tests")

    return ejecutar(claves)


if __name__ == "__main__":
    raise SystemExit(main())
