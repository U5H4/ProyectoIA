"""ETAPA EXTRACT del ETL.

Descarga y perfila las dos fuentes de datos del proyecto:
  - CICIDS2017 (flujos de red etiquetados) -> Machine Learning.
  - Reportes Cyber Threat Intelligence (textos) -> PNL.

Produce evidencia auditable en data/reports/:
  - evidencia_extraccion.csv
  - evidencia_extraccion_columnas.csv

Uso:
    python src/etl_extract.py --accept-license
    python src/etl_extract.py --accept-license --files Friday
    python src/etl_extract.py --dataset cti
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import pandas as pd
import requests
from tqdm import tqdm

from config import (
    CHUNK_SIZE,
    CICIDS_DIR,
    CICIDS_FILES,
    CICIDS_HF_BASE,
    CICIDS_LICENSE_URL,
    CICIDS_CITATION,
    CTI_DIR,
    CTI_REPORTS_URL,
    DEFAULT_PER_FILE_CLASS_CAP,
    RAW_LABEL_COLUMN,
    REPORTS,
)
from utils import LOG, asegurar_dir, titulo

NULOS = {"", "n/a", "na", "null", "none", "-", "nan", "#valor!", "#n/a", "nd"}

LICENSE_NOTICE = f"""\
============================================================
CICIDS-2017 - licencia y cita obligatoria
============================================================
Dataset:  CICIDS-2017
Editor:   Canadian Institute for Cybersecurity (UNB)
Terminos: {CICIDS_LICENSE_URL}
Cita:
  {CICIDS_CITATION}

Uso permitido para investigacion/academico. No se redistribuye.
Al usar --accept-license confirmas haber leido los terminos anteriores.
============================================================
"""


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------
def descargar_archivo(url: str, destino, chunk_size: int = 1 << 20) -> None:
    """Descarga `url` a `destino` con barra de progreso. omite si ya existe."""
    asegurar_dir(destino.parent)
    if destino.exists() and destino.stat().st_size > 0:
        LOG.info("[skip] ya existe: %s", destino.name)
        return
    tmp = destino.with_name(destino.name + ".part")
    headers = {"User-Agent": "proyectoIA-ETL/1.0"}
    with requests.get(url, stream=True, timeout=120, headers=headers) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        with open(tmp, "wb") as handle, tqdm(
            total=total, unit="B", unit_scale=True, desc=destino.name
        ) as bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    handle.write(chunk)
                    bar.update(len(chunk))
    tmp.replace(destino)


def descargar(dataset: str = "all", tags: list[str] | None = None, accept_license: bool = False) -> int:
    if dataset in ("all", "cicids") and not accept_license:
        print(LICENSE_NOTICE, file=sys.stderr)
        print("Reejecuta con --accept-license para confirmar los terminos.", file=sys.stderr)
        return 2

    if dataset in ("all", "cicids"):
        print(LICENSE_NOTICE)
        tags = tags or [""]
        archivos = [n for n in CICIDS_FILES if any(t in n for t in tags)]
        if not archivos:
            LOG.error("Ningun archivo CICIDS coincide con %s", tags)
            return 2
        for nombre in archivos:
            descargar_archivo(f"{CICIDS_HF_BASE}/{nombre}", CICIDS_DIR / nombre)
        LOG.info("[ok] %d archivo(s) CICIDS2017 en %s", len(archivos), CICIDS_DIR)

    if dataset in ("all", "cti"):
        descargar_archivo(CTI_REPORTS_URL, CTI_DIR / "cti_reports.parquet")
        LOG.info("[ok] reportes CTI en %s", CTI_DIR)
    return 0


# --------------------------------------------------------------------------
# Perfilado (evidencia de extraccion)
# --------------------------------------------------------------------------
@dataclass
class ResumenFuente:
    fuente: str
    archivo: str
    formato: str
    sistema_origen: str
    ruta: str
    registros: int
    columnas: int
    nulos: int
    duplicados_exactos: int
    muestra_valores_crudos: str = ""
    columnas_detalle: list[dict] = field(default_factory=list)


def inferir_tipo(serie: pd.Series) -> str:
    sin_nulos = serie.dropna()
    if sin_nulos.empty:
        return "vacio"
    muestra = sin_nulos.astype(str).head(200)
    if pd.api.types.is_numeric_dtype(sin_nulos):
        return "entero" if (sin_nulos % 1 == 0).all() else "decimal"
    try:
        muestra.astype(float)
        return "numero_texto"
    except (TypeError, ValueError):
        pass
    if muestra.str.lower().isin({"true", "false"}).all():
        return "booleano_texto"
    return "texto"


def _contar_nulos(frame: pd.DataFrame) -> int:
    total = 0
    for col in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[col]):
            total += int(frame[col].isna().sum())
        else:
            total += int(frame[col].astype(str).str.strip().str.lower().isin(NULOS).sum())
    return total


def perfilar_flujos(path, fuente: str) -> tuple[pd.DataFrame, ResumenFuente]:
    """Lee un archivo de flujos (parquet o CSV), lo perfila y devuelve (frame, resumen)."""
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path)
        formato = "PARQUET"
    else:
        partes = [chunk for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE, low_memory=False)]
        frame = pd.concat(partes, ignore_index=True)
        formato = "CSV"
    frame.columns = [str(c).strip() for c in frame.columns]

    detalle = [
        {
            "fuente": fuente,
            "archivo": path.name,
            "formato": formato,
            "sistema_origen": "CIC-UNB / HuggingFace",
            "registros": len(frame),
            "columnas": len(frame.columns),
            "columna": col,
            "tipo_inferido": inferir_tipo(frame[col]),
        }
        for col in frame.columns
    ]
    resumen = ResumenFuente(
        fuente=fuente,
        archivo=path.name,
        formato=formato,
        sistema_origen="CIC-UNB / HuggingFace",
        ruta=str(path),
        registros=len(frame),
        columnas=len(frame.columns),
        nulos=_contar_nulos(frame),
        duplicados_exactos=int(frame.duplicated().sum()),
        muestra_valores_crudos=" | ".join(
            str(v) for v in frame.iloc[0].head(6).tolist()
        ),
        columnas_detalle=detalle,
    )
    return frame, resumen


def perfilar_parquet(path, fuente: str) -> tuple[pd.DataFrame, ResumenFuente]:
    frame = pd.read_parquet(path)
    detalle = [
        {
            "fuente": fuente,
            "archivo": path.name,
            "formato": "PARQUET",
            "sistema_origen": "HuggingFace",
            "registros": len(frame),
            "columnas": len(frame.columns),
            "columna": col,
            "tipo_inferido": inferir_tipo(frame[col]),
        }
        for col in frame.columns
    ]
    resumen = ResumenFuente(
        fuente=fuente,
        archivo=path.name,
        formato="PARQUET",
        sistema_origen="HuggingFace",
        ruta=str(path),
        registros=len(frame),
        columnas=len(frame.columns),
        nulos=_contar_nulos(frame),
        duplicados_exactos=int(frame.duplicated().sum()),
        muestra_valores_crudos=" | ".join(str(v) for v in frame.iloc[0].head(5).tolist()),
        columnas_detalle=detalle,
    )
    return frame, resumen


# --------------------------------------------------------------------------
# Extraccion
# --------------------------------------------------------------------------
def _muestreo_por_archivo(frame: pd.DataFrame, cap: int) -> pd.DataFrame:
    """Conserva hasta `cap` filas por etiqueta cruda (protege clases raras)."""
    if RAW_LABEL_COLUMN not in frame.columns:
        return frame
    etiqueta = frame[RAW_LABEL_COLUMN].astype(str).str.strip()
    partes = [grupo.head(cap) for _, grupo in frame.groupby(etiqueta, sort=False)]
    return pd.concat(partes, ignore_index=True)


def extraer(tags: list[str] | None = None) -> dict:
    """Lee las fuentes crudas, guarda evidencia y devuelve los datos muestreados."""
    asegurar_dir(REPORTS)
    tags = tags or [""]
    archivos = sorted(CICIDS_DIR.glob("*.parquet"))
    if tags != [""]:
        archivos = [p for p in archivos if any(t in p.name for t in tags)]
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos en {CICIDS_DIR}. Ejecuta: python src/etl_extract.py --accept-license"
        )

    print(titulo("EVIDENCIA DE EXTRACCION - CICIDS2017"))
    resumenes: list[ResumenFuente] = []
    frames = []
    for path in archivos:
        frame, resumen = perfilar_flujos(path, fuente="flujos_red")
        frames.append(_muestreo_por_archivo(frame, DEFAULT_PER_FILE_CLASS_CAP))
        resumenes.append(resumen)
        LOG.info(
            "  %-52s %8d filas | %3d cols | %d duplicados",
            path.name,
            resumen.registros,
            resumen.columnas,
            resumen.duplicados_exactos,
        )

    flujos = pd.concat(frames, ignore_index=True)

    ruta_cti = CTI_DIR / "cti_reports.parquet"
    reportes = pd.DataFrame()
    if ruta_cti.exists():
        reportes, resumen_cti = perfilar_parquet(ruta_cti, fuente="reportes_cti")
        resumenes.append(resumen_cti)
        LOG.info("  %-52s %8d filas | %3d cols", ruta_cti.name, resumen_cti.registros, resumen_cti.columnas)

    filas_resumen = [
        {
            "fuente": r.fuente,
            "archivo": r.archivo,
            "formato": r.formato,
            "sistema_origen": r.sistema_origen,
            "registros": r.registros,
            "columnas": r.columnas,
            "nulos": r.nulos,
            "duplicados_exactos": r.duplicados_exactos,
            "muestra_valores_crudos": r.muestra_valores_crudos,
        }
        for r in resumenes
    ]
    pd.DataFrame(filas_resumen).to_csv(
        REPORTS / "evidencia_extraccion.csv", index=False, encoding="utf-8-sig"
    )
    columnas = [c for r in resumenes for c in r.columnas_detalle]
    pd.DataFrame(columnas).to_csv(
        REPORTS / "evidencia_extraccion_columnas.csv", index=False, encoding="utf-8-sig"
    )
    LOG.info("[ok] evidencia de extraccion guardada en %s", REPORTS)

    return {
        "flujos": flujos,
        "reportes": reportes,
        "rutas": {"cicids": archivos, "cti": ruta_cti},
        "evidencia": filas_resumen,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["all", "cicids", "cti"], default="all")
    parser.add_argument("--files", default="", help="Filtro por texto sobre los CSV de CICIDS.")
    parser.add_argument("--accept-license", action="store_true")
    args = parser.parse_args(argv)

    tags = [t for t in args.files.split(",") if t]
    estado = descargar(args.dataset, tags, args.accept_license)
    if estado != 0:
        return estado
    if args.dataset in ("all", "cicids"):
        extraer(tags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
