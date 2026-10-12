# Guia de carpetas

Detalle de cada carpeta del proyecto y que se guarda en ella.

## `data/` — datos (no versionados)

| Carpeta | Contenido | Origen |
|---|---|---|
| `data/raw/` | Datos crudos tal como se descargan. | EXTRACT |
| `data/raw/cicids2017/` | Los 8 archivos parquet de CICIDS2017 (flujos de red). | Descarga HuggingFace |
| `data/raw/cti_reports/` | `cti_reports.parquet` con los reportes de amenazas (texto). | Descarga HuggingFace |
| `data/processed/` | Datos limpios, divididos y listos para ML/PNL. | LOAD |
| `data/reports/` | Evidencia auditable del ETL (CSV). | EXTRACT + LOAD |
| `data/figures/` | Graficos generados (matriz de confusion, etc.). | ML / dashboard |
| `data/blockchain/` | Cadena de bloques y artefactos de trazabilidad. | Blockchain |

## `src/` — codigo fuente

| Archivo | Rol |
|---|---|
| `config.py` | Rutas, URLs de fuentes, parametros del ETL y mapa de etiquetas (`LABEL_GROUPS`). |
| `utils.py` | Logging (`logs/pipeline.log`), `CalidadTracker`/`RegistroCalidad`, helpers de consola. |
| `etl_extract.py` | EXTRACT: `descargar()` y `extraer()`; genera la evidencia de extraccion. |
| `etl_transform.py` | TRANSFORM: transformaciones T01..T10 y limpieza de textos de reportes. |
| `etl_load.py` | LOAD: escritura de datos procesados, perfil de columnas y validacion de minimos. |
| `ml.py` | ML: entrena y evalua varios modelos, guarda el mejor y genera predicciones. |
| `pnl.py` | PNL: TF-IDF, sentimiento (VADER), entidades (IOC) y resumen/reporte. |
| `blockchain.py` | Blockchain: registra el SHA-256 de los resultados y verifica integridad. |
| `dashboard.py` | Dashboard interactivo en Streamlit. |
| `run_all.py` | Orquestador; ejecuta etapas (descargar, etl, ml, pnl, blockchain, tests) en orden. |

> Los modulos se ejecutan como scripts (`python src/run_all.py`). Importan entre si
> de forma plana (`from config import ...`), por lo que `src/` debe ser el directorio
> del script; no se ejecutan con `python -m src.*`.

## `data/processed/` — salidas del ETL

| Archivo | Contenido |
|---|---|
| `flujos_clean.parquet` | Flujos de red limpios, con label agrupada y balanceada. |
| `flujos_train.parquet` | Particion de entrenamiento (70%). |
| `flujos_test.parquet` | Particion de prueba (30%). |
| `reportes_clean.parquet` | Reportes de amenazas limpios para PNL. |
| `reportes_enriquecidos.parquet` | Reportes con sentimiento, IOCs, terminos clave y resumen. |
| `predicciones_test.parquet` | Prediccion del modelo sobre la particion de prueba. |
| `estandarizacion.json` | Media y desviacion por columna para reutilizar el escalado. |

## `data/reports/` — evidencia auditable

| Archivo | Contenido |
|---|---|
| `evidencia_extraccion.csv` | Perfil por fuente: filas, columnas, nulos, duplicados. |
| `evidencia_extraccion_columnas.csv` | Perfil por columna: tipo inferido y metadatos. |
| `calidad_transformaciones.csv` | Registro de cada transformacion (filas antes/despues). |
| `perfil_columnas.csv` | Diccionario de datos del dataset final. |
| `validacion_minimos.csv` | Cumplimiento de los minimos exigidos por el enunciado. |
| `metricas_modelos.csv`, `metricas_por_clase.csv` | Evaluacion de cada modelo de ML. |
| `matriz_confusion.csv`, `importancia_variables.csv` | Matriz de confusion e importancia (ML). |
| `ml_resumen.json` | Resumen del experimento de ML (modelo ganador). |
| `pnl_top_terminos.csv`, `pnl_sentimiento.csv` | Representacion y sentimiento (PNL). |
| `pnl_iocs.csv`, `pnl_entidades.csv` | Entidades / IOCs por documento (PNL). |
| `pnl_resumen.csv`, `pnl_reporte.md` | Resumenes por documento y reporte narrativo (PNL). |
| `blockchain_*.csv` | Evidencia de bloques, validacion, integridad y prueba de alteracion. |

## Otras carpetas

| Carpeta | Contenido |
|---|---|
| `models/` | Modelos entrenados y artefactos asociados (no versionado). |
| `logs/` | `pipeline.log` con el detalle de cada ejecucion. |
| `tests/` | Pruebas automaticas (`python -m pytest tests -q`). |
