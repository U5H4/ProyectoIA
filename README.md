# Sistema Inteligente de Analisis, Prediccion y Trazabilidad de Incidentes de Ciberseguridad

Prototipo funcional (Tema 3) que analiza incidentes de ciberseguridad combinando:

- **Machine Learning** para clasificar flujos de red (benigno / tipo de ataque).
- **PNL** para analizar reportes de amenazas (representacion, sentimiento, entidades, resumen).
- **Blockchain** propia para registrar y verificar la integridad de los resultados.
- **Dashboard** en Streamlit para visualizar y verificar.

## Estado del proyecto

| Componente | Estado |
|---|---|
| Estructura del proyecto | Listo |
| ETL (extract / transform / load) | Listo |
| Modelo de Machine Learning | Listo |
| Componente de PNL | Listo |
| Blockchain | Listo |
| Dashboard | Listo |

> Las cifras concretas (registros procesados, F1-macro del modelo ganador, numero
> de bloques y estado de la cadena) se generan al ejecutar el pipeline y quedan en
> `data/reports/` (`validacion_minimos.csv`, `metricas_modelos.csv`,
> `ml_resumen.json`, `blockchain_validacion.csv`).

## Requisitos

- Python 3.10+ (probado con 3.12)
- Windows / Linux / macOS
- Conexion a internet solo para la descarga inicial de datos

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso rapido (pipeline completo)

```powershell
# Descarga los datos crudos y ejecuta el pipeline completo
# (descargar -> etl -> ml -> pnl -> integrar -> blockchain)
python src/run_all.py

# Si ya descargaste los datos, omite la descarga
python src/run_all.py --sin-descargar

# Ejecuta solo algunas etapas, lista las etapas o anade las pruebas
python src/run_all.py --solo etl ml
python src/run_all.py --listar
python src/run_all.py --sin-descargar --con-tests
```

Cada etapa se detiene si la anterior falla. El log queda en `logs/pipeline.log`.

Dashboard interactivo:

```powershell
streamlit run src/dashboard.py
```

## ETL

Los datos **no se versionan**. Se descargan y procesan con los scripts del ETL
(modulos planos dentro de `src/`, se ejecutan como scripts, no como paquete).

### 1. Descargar (EXTRACT)

```powershell
python src/etl_extract.py --accept-license
```

- `--dataset cicids` descarga solo CICIDS2017 (flujos de red).
- `--dataset cti` descarga solo los reportes de amenazas (~16 MB).
- `--files PortScan` descarga un subconjunto de archivos CICIDS (util para pruebas;
  admite varios separados por coma).

CICIDS2017 es un dataset del Canadian Institute for Cybersecurity (UNB). Requiere
aceptar su licencia (`--accept-license`) y citarlo. No se redistribuye. Se descarga
desde un mirror publico en HuggingFace (`bvsam/cic-ids-2017`) en formato parquet.

### 2. Procesar (TRANSFORM + LOAD)

```powershell
python src/etl_transform.py   # opcional: probar solo la transformacion
python src/etl_load.py        # opcional: probar solo la carga
python src/run_all.py --sin-descargar
```

Salidas en `data/processed/`:

- `flujos_clean.parquet` dataset de flujos limpio y balanceado.
- `flujos_train.parquet`, `flujos_test.parquet` division estratificada 70/30.
- `reportes_clean.parquet` textos de reportes listos para PNL.
- `estandarizacion.json` parametros del escalado (media/desviacion) para inferencia.

Evidencia auditable en `data/reports/`:

- `evidencia_extraccion.csv` y `evidencia_extraccion_columnas.csv` (perfil por fuente).
- `calidad_transformaciones.csv` registro de cada transformacion (T01..T10).
- `perfil_columnas.csv` diccionario de datos final.
- `validacion_minimos.csv` control de minimos exigidos por el enunciado.

## Transformaciones aplicadas

| Codigo | Transformacion |
|---|---|
| T01 | Eliminacion de duplicados |
| T02 | Normalizacion de texto / etiquetas |
| T03 | Correccion de tipos |
| T04 | Tratamiento de faltantes e infinitos |
| T05 | Validacion y agrupacion de etiquetas |
| T06 | Tratamiento de valores atipicos (winsorizacion IQR) |
| T07 | Creacion de variables derivadas |
| T08 | Seleccion de caracteristicas |
| T09 | Muestreo y balanceo de clases |
| T10 | Division de datos y estandarizacion |

## Machine Learning

Clasificacion supervisada de flujos de red. Se comparan varios algoritmos del
curso y se conserva el de mejor F1-macro.

```powershell
python src/ml.py
```

- Modelos: Regresion Logistica, Arbol de Decision, Random Forest, KNN,
  Naive Bayes (Gaussiano) y SVM (RBF).
- Division estratificada 70/30 (train/test) y validacion cruzada estratificada
  (`CV_FOLDS=5`); el modelo ganador se elige por la media de F1-macro en la
  validacion cruzada (no mirando el test, para no sesgar la seleccion).
- Salidas: `models/modelo_mejor.joblib`, `data/processed/predicciones_test.parquet`
  y evidencia en `data/reports/` (`metricas_modelos.csv`, `metricas_por_clase.csv`,
  `matriz_confusion.csv`, `importancia_variables.csv`, `ml_resumen.json`).
- Graficos: `data/figures/comparacion_modelos.html`, `data/figures/matriz_confusion.html`.
- **Inferencia:** `models/predictor.joblib` empaqueta el modelo ganador y la
  estandarizacion (de `estandarizacion.json`); el dashboard permite subir un CSV
  de flujos crudos y clasificarlos en vivo.
- **Hiperparametros:** el ganador se reajusta con `GridSearchCV` (F1-macro, CV=5).

## Reporte integrado (ML + PNL)

`python src/integrar.py` combina la clasificacion de flujos y el analisis de
reportes en un unico resultado con **nivel de riesgo global** (BAJO/MEDIO/ALTO),
que es el artefacto integrado que se registra en la Blockchain
(`data/reports/reporte_integrado.{md,json}`).

## PNL

Analisis de los reportes de amenazas. Implementa cuatro funcionalidades:

```powershell
python src/pnl.py
```

1. **Representacion del lenguaje** con TF-IDF (`data/reports/pnl_top_terminos.csv`).
2. **Analisis de sentimiento** con VADER (`data/reports/pnl_sentimiento.csv`).
3. **Reconocimiento de entidades (IOC)**: IPv4, dominios, URLs, correos, hashes,
   CVEs y palabras clave de amenaza (`data/reports/pnl_iocs.csv`,
   `data/reports/pnl_entidades.csv`).
4. **Generacion de lenguaje** extractivo: resumen por documento y reporte
   narrativo (`data/reports/pnl_reporte.md`).

Resultados enriquecidos por documento: `data/processed/reportes_enriquecidos.parquet`.

## Blockchain

Cadena propia (SHA-256) que registra la huella de los resultados clave y permite
verificar su integridad.

```powershell
python src/blockchain.py                  # registra y verifica
python src/blockchain.py --solo-verificar # valida la cadena existente sin reconstruirla
```

- Se registra el SHA-256 de: dataset procesado, reportes enriquecidos, modelo,
  predictor de inferencia, metricas ML, reporte de PNL y **reporte integrado ML+PNL**.
  Se justifica por que esos artefactos permiten demostrar que el resultado
  presentado no fue alterado.
- Verificacion: recomputa cada hash y la cadena completa; prueba de alteracion
  incluida. Antes de reconstruir, la cadena previa en disco se valida y se avisa
  si ya no era integra.
- El **dashboard verifica la cadena en vivo** (recalcula `es_valida()` sobre
  `cadena.json`), no solo lee un CSV previo.
- Salidas: `data/blockchain/cadena.json` y evidencia en
  `data/reports/blockchain_{bloques,validacion,integridad,prueba_alteracion}.csv`.

## Dashboard

Presenta registros analizados, categorias, resultados del modelo, indicadores,
graficas, resultados del analisis de texto, entidades, **prediccion en vivo**
(subir CSV de flujos), nivel de riesgo integrado y la verificacion de la
Blockchain.

```powershell
streamlit run src/dashboard.py
```

## Fuentes de datos

| Fuente | Uso | Enlace |
|---|---|---|
| CICIDS2017 (MachineLearningCVE) | ML: clasificacion de flujos | https://www.unb.ca/cic/datasets/ids-2017.html |
| Cyber Threat Intelligence Reports (guychuk) | PNL: reportes de amenazas | https://huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports |

## Pruebas

```powershell
python -m pytest tests -q
```

## Estructura

```
proyectoIA/
├── data/
│   ├── raw/            Datos crudos descargados (no versionado)
│   ├── processed/      Datos limpios y divididos (no versionado)
│   ├── reports/        Evidencia auditable del ETL (no versionado)
│   ├── figures/        Graficos generados (no versionado)
│   └── blockchain/     Cadena de bloques (no versionado)
├── src/
│   ├── config.py       Configuracion central (rutas, parametros, etiquetas)
│   ├── utils.py        Logging, tracker de calidad y utilidades de consola
│   ├── etl_extract.py  EXTRACT: descarga y perfilado de fuentes
│   ├── etl_transform.py TRANSFORM: T01..T10 + limpieza de textos
│   ├── etl_load.py     LOAD: datos procesados, perfiles y validacion
│   ├── ml.py           ML: entrenamiento, evaluacion y prediccion
│   ├── pnl.py          PNL: representacion, sentimiento, entidades y resumen
│   ├── integrar.py     Reporte integrado ML+PNL (nivel de riesgo)
│   ├── blockchain.py   Blockchain: registro y verificacion de integridad
│   ├── dashboard.py    Dashboard interactivo (Streamlit)
│   └── run_all.py      Orquestador del pipeline
├── models/             Modelos entrenados (no versionado)
├── logs/               Logs de ejecucion (no versionado)
├── tests/              Pruebas
├── ARQUITECTURA.md     Arquitectura del sistema (flujo completo)
└── requirements.txt
```

Ver `README_CARPETAS.md` para el detalle de cada carpeta.

## Licencia

Proyecto academico. El uso de CICIDS2017 se rige por los terminos del Canadian
Institute for Cybersecurity.
