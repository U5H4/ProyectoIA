# Arquitectura del sistema

Documento de soporte (Tema 3, seccion 9). Describe el flujo completo, desde las
fuentes de datos hasta la verificacion de integridad y la visualizacion.

## Vista general

```
  FUENTES DE DATOS
  +----------------------------+   +-----------------------------+
  | CICIDS2017 (flujos de red) |   | Reportes CTI (texto)        |
  | HuggingFace: bvsam/...     |   | HuggingFace: guychuk/...    |
  +-------------+--------------+   +--------------+--------------+
                |                                 |
                +---------------+-----------------+
                                |
                       1. INGESTA (descarga)
                                |
                       2. ALMACENAMIENTO (data/raw)
                                |
                       3. PREPARACION / ETL (T01..T10)
                                |
             +------------------+------------------+
             |                                     |
        4a. PNL                               4b. ML
   representacion, sentimiento,          entrenamiento y evaluacion
   entidades, resumen                    (Regresion, Arbol, RF, KNN,
             |                            NB, SVM)
             +------------------+------------------+
                                |
                       5. RESULTADOS (data/processed, data/reports)
                                |
                       6. TRAZABILIDAD (SHA-256 -> Blockchain)
                                |
                       7. DASHBOARD (Streamlit) + verifica Blockchain
```

## Flujo por etapas

1. **Ingesta.** Descarga CICIDS2017 (parquet) y los reportes CTI desde
   HuggingFace. Guarda los originales en `data/raw/` sin transformarlos.
2. **Almacenamiento.** Datos crudos separados por fuente; no versionados.
3. **Preparacion (ETL).** `etl_extract` perfila las fuentes, `etl_transform`
   aplica T01..T10 (duplicados, faltantes/infinitos, atipicos, variables
   derivadas, seleccion de caracteristicas, muestreo/balanceo, division y
   estandarizacion) y `etl_load` materializa y valida minimos.
4a. **PNL.** `pnl.py` procesa los textos: TF-IDF, sentimiento (VADER),
   entidades (IOC) y resumen/reporte.
4b. **ML.** `ml.py` entrena varios modelos, los evalua y guarda el mejor.
5. **Resultados.** Datos procesados, metricas, figuras y evidencias en
   `data/processed/`, `data/reports/`, `data/figures/` y `models/`.
6. **Trazabilidad.** `blockchain.py` calcula el SHA-256 de los artefactos clave
   y los registra en una cadena de bloques encadenada; permite verificar que no
   fueron alterados.
7. **Dashboard.** `dashboard.py` (Streamlit) muestra KPIs, graficos, resultados
   de ML y PNL, y permite verificar hashes contra la Blockchain.

## Componentes y responsabilidades

| Modulo | Responsabilidad | Salidas principales |
|---|---|---|
| `config.py` | Rutas, parametros y etiquetas | - |
| `utils.py` | Logging, tracker de calidad, formato de consola | `logs/pipeline.log` |
| `etl_extract.py` | Descarga y perfilado de fuentes | `data/raw/*`, evidencia de extraccion |
| `etl_transform.py` | Limpieza y transformaciones T01..T10 | dataframes en memoria |
| `etl_load.py` | Materializacion y validacion | `data/processed/*`, `data/reports/*` |
| `ml.py` | Entrenamiento/evaluacion y prediccion | `models/*.joblib`, reportes y figuras de ML |
| `pnl.py` | Analisis de texto | reportes y figuras de PNL, textos enriquecidos |
| `blockchain.py` | Registro y verificacion de integridad | `data/blockchain/cadena.json`, evidencia |
| `run_all.py` | Orquestacion del pipeline | resumen de ejecucion |
| `dashboard.py` | Visualizacion e interaccion | interfaz Streamlit |

## Decisiones de diseno

- **Modulos planos en `src/`** ejecutados como scripts (importan `config` y
  `utils` por nombre); simplifica la ejecucion sin instalar el proyecto.
- **Orquestador unico** (`run_all.py`) con etapas seleccionables
  (`--solo`, `--sin-descargar`, `--con-tests`) para reproducir el flujo.
- **Evidencia auditable**: cada etapa escribe CSV/figuras, de modo que el
  resultado pueda revisarse sin volver a ejecutar.
- **Datos no versionados**: los grandes volumenes viven en `data/` y `models/`;
  el repositorio solo guarda codigo, documentacion y `.gitkeep`.
- **Trazabilidad sin dependencias externas**: la Blockchain es propia (SHA-256),
  suficiente para demostrar integridad sin una red distribuida real.
