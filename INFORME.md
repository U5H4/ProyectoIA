# Informe tecnico

## Sistema Inteligente de Analisis, Prediccion y Trazabilidad de Incidentes de Ciberseguridad

Prototipo funcional (Tema 3) que integra preparacion de datos, Machine Learning,
Procesamiento de Lenguaje Natural, una Blockchain propia de trazabilidad y un
dashboard interactivo.

---

## 1. Introduccion y contexto

La deteccion y el analisis de incidentes de ciberseguridad requiere procesar
grandes volumenes de trafico de red y, al mismo tiempo, interpretar reportes
tecnicos escritos en lenguaje natural. Este proyecto construye un prototipo que:

- clasifica flujos de red para distinguir trafico benigno de distintos tipos de ataque;
- analiza reportes de amenazas (sentimiento, entidades, resumen);
- garantiza la integridad y trazabilidad de los resultados mediante una cadena de bloques;
- presenta todo en un dashboard para su consulta y verificacion.

### Objetivos

1. Preparar un dataset de al menos 5.000 registros de red y 300 reportes de texto.
2. Entrenar y evaluar al menos un modelo de clasificacion, comparando algoritmos.
3. Implementar al menos tres funcionalidades de PNL.
4. Registrar los resultados en una Blockchain y verificar su integridad.
5. Ofrecer un dashboard para la consulta y verificacion de los resultados.

---

## 2. Fuentes de datos

| Fuente | Uso | Registros | Enlace |
|---|---|---|---|
| CICIDS2017 (MachineLearningCVE) | ML: clasificacion de flujos de red | 2,8 M (se muestrean) | https://www.unb.ca/cic/datasets/ids-2017.html |
| Cyber Threat Intelligence Reports (guychuk) | PNL: reportes de amenazas | 978 documentos | https://huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports |

CICIDS2017 pertenece al Canadian Institute for Cybersecurity (UNB) y requiere
aceptar su licencia y citarlo; no se redistribuye. Los datos se descargan desde
un mirror publico en HuggingFace en formato parquet (`bvsam/cic-ids-2017`) y los
reportes desde `guychuk/cyber-threat-intelligence-reports`. Los 8 dias de captura
suman 256 MB crudos.

**Cumplimiento del minimo de datos (validacion automatica):**

| Informacion | Minimo | Registros finales | Cumple | Veces el minimo |
|---|---|---|---|---|
| Flujos de red (ML) | 5,000 | 19,810 | SI | 3.96x |
| Reportes de texto (PNL) | 300 | 978 | SI | 3.26x |

---

## 3. Arquitectura del sistema

```
FUENTES (CICIDS2017 + reportes CTI)
      |
  1. INGESTA (descarga)
      |
  2. ALMACENAMIENTO (data/raw)
      |
  3. PREPARACION / ETL (T01..T10)
      |
   +--+--+
   |     |
  PNL    ML
   |     |
   +--+--+
      |
  4. RESULTADOS (data/processed, data/reports)
      |
  5. TRAZABILIDAD (SHA-256 -> Blockchain)
      |
  6. DASHBOARD (Streamlit) + verificacion
```

El detalle completo esta en `ARQUITECTURA.md`. El pipeline se ejecuta con un
unico orquestador:

```powershell
python src/run_all.py
```

Etapas: `descargar -> etl -> ml -> pnl -> blockchain` (y opcionalmente `tests`).
Se ejecutan como scripts planos en `src/`, con evidencia auditable por etapa.

---

## 4. Preparacion de datos (ETL)

El ETL se divide en tres modulos: `etl_extract.py` (EXTRACT), `etl_transform.py`
(TRANSFORM) y `etl_load.py` (LOAD). Se aplican diez transformaciones trazables:

| Codigo | Transformacion |
|---|---|
| T01 | Eliminacion de duplicados |
| T02 | Normalizacion de texto y etiquetas |
| T03 | Correccion de tipos |
| T04 | Tratamiento de faltantes e infinitos |
| T05 | Validacion y agrupacion de etiquetas |
| T06 | Tratamiento de valores atipicos (winsorizacion IQR) |
| T07 | Creacion de variables derivadas |
| T08 | Seleccion de caracteristicas |
| T09 | Muestreo y balanceo de clases |
| T10 | Division de datos y estandarizacion |

Las etiquetas originales de CICIDS2017 (mas de 15, incluyendo variantes de DoS y
WebAttack) se agrupan en 9 categorias de riesgo. El resultado es
`flujos_clean.parquet` (19,810 flujos x 75 columnas, 72 variables predictoras) y
`reportes_clean.parquet` (978 documentos). Se genera ademas la evidencia de
calidad (`calidad_transformaciones.csv`), el diccionario de datos
(`perfil_columnas.csv`) y la validacion de minimos (`validacion_minimos.csv`).

**Distribucion final de clases:**

| Clase | Registros |
|---|---|
| BENIGN | 4,444 |
| DoS | 4,444 |
| BruteForce | 2,829 |
| WebAttack | 2,143 |
| DDoS | 2,000 |
| PortScan | 1,955 |
| Bot | 1,948 |
| Infiltration | 36 |
| Heartbleed | 11 |

---

## 5. Machine Learning

**Problema y tipo de aprendizaje.** Clasificacion supervisada multiclase:
predecir el tipo de trafico (benigno o tipo de ataque) a partir de variables
numericas derivadas del flujo (duracion, paquetes, longitud, banderas, etc.). El
objetivo es apoyar la deteccion automatica de intrusiones.

**Variables.** 72 variables predictoras numericas estandarizadas; la etiqueta es
`label` (9 clases). Se excluyen de las features las columnas de etiqueta
(`label`, `label_raw` y la etiqueta original).

**Algoritmos comparados** (todos del curso): Regresion Logistica, Arbol de
Decision, Random Forest, KNN, Gaussian Naive Bayes y SVM (kernel RBF).

**Entrenamiento y evaluacion.** Division estratificada 70/30 (13,867 train /
5,943 test) y validacion cruzada estratificada de 5 particiones (`CV_FOLDS=5`)
sobre el conjunto de entrenamiento. La seleccion del modelo se hace por
**F1-macro**, mas informativo que la exactitud ante el desbalance de clases.

**Resultados:**

| Modelo | Accuracy | F1-macro | CV F1-macro | Tiempo (s) |
|---|---|---|---|---|
| Arbol de Decision | 0.9870 | **0.9845** | 0.9870 | 0.28 |
| Random Forest | **0.9901** | 0.9812 | 0.9784 | 1.29 |
| KNN | 0.9817 | 0.9447 | 0.9436 | 0.49 |
| Gaussian Naive Bayes | 0.9322 | 0.9380 | 0.9102 | 0.12 |
| Regresion Logistica | 0.9763 | 0.9289 | 0.9268 | 0.84 |
| SVM (kernel RBF) | 0.9734 | 0.9164 | 0.9066 | 2.71 |

**Modelo ganador: Arbol de Decision** (F1-macro 0.9845). Aunque Random Forest
logra una exactitud ligeramente mayor (0.9901), el Arbol de Decision obtiene el
mejor F1-macro y, ademas, es mas rapido e interpretable (permite leer las reglas
y la importancia de variables). Ventajas del enfoque: alto desempeno, bajo costo
de entrenamiento y buena capacidad de generalizacion (desviacion de la validacion
cruzada inferior al 1%).

Artefactos: `models/modelo_mejor.joblib`, `data/processed/predicciones_test.parquet`,
`data/reports/metricas_modelos.csv`, `metricas_por_clase.csv`,
`matriz_confusion.csv`, `importancia_variables.csv`, `ml_resumen.json`.
Graficos: `data/figures/comparacion_modelos.html`, `data/figures/matriz_confusion.html`.

---

## 6. Procesamiento de Lenguaje Natural

Se implementan **cuatro** funcionalidades (el enunciado pide al menos tres):

1. **Representacion del lenguaje (TF-IDF).** Vectorizacion de los 978 reportes
   con unigramas y bigramas (vocabulario de 4,000 terminos). Terminos mas
   relevantes: `malware`, `attack`, `threat`, `security`, `server`, `network`.
2. **Analisis de sentimiento (VADER).** Cada documento recibe una polaridad.
   Resultado: sentimiento promedio **-0.148**; 57.3% negativo, 40.3% positivo,
   2.5% neutro, coherente con un corpus de reportes de amenazas.
3. **Reconocimiento de entidades (IOC).** Se extraen direcciones IPv4
   (validando rangos), dominios, URLs, correos, hashes (MD5/SHA1/SHA256), codigos
   CVE y palabras clave de amenaza. En total se detectan **42,345 IOCs** y 10
   CVEs distintos.
4. **Generacion de lenguaje (resumen extractivo).** Se genera un resumen por
   documento (oraciones de mayor peso TF-IDF) y un reporte narrativo global
   (`data/reports/pnl_reporte.md`).

Artefactos: `data/processed/reportes_enriquecidos.parquet`,
`data/reports/pnl_{top_terminos,sentimiento,iocs,entidades,resumen}.csv`,
`data/reports/pnl_reporte.md`. Graficos: `data/figures/pnl_sentimiento.html`,
`data/figures/pnl_top_terminos.html`.

---

## 7. Blockchain

**Que se registra y por que.** Se registran las huellas SHA-256 de los artefactos
que resumen el analisis: el dataset procesado (`flujos_clean.parquet`), los
reportes enriquecidos, el modelo (`modelo_mejor.joblib`), las metricas de ML y el
reporte de PNL. Tiene sentido registrar estos y no todos los archivos intermedios
porque son los resultados que se presentan: si su hash coincide con el
registrado, se demuestra que el resultado mostrado es el mismo que se genero y no
fue alterado despues.

**Diseno.** Blockchain propia (no una red distribuida real): cada bloque guarda
`indice`, `timestamp`, `datos`, `hash_previo` y su propio `hash`, calculado como
`SHA-256(indice | timestamp | datos | hash_previo)`. El encadenamiento hace que
cualquier cambio en un bloque invalide todos los siguientes.

**Verificacion.** La cadena se recomputa por completo; se comprueba que cada hash
coincida con los datos y que cada `hash_previo` enlace con el bloque anterior. Se
incluye ademas una prueba de alteracion (se modifica un bloque y el sistema lo
detecta) y una comprobacion de la integridad real de los archivos en disco.

**Resultado:** cadena de 6 bloques, **valida**; la prueba de alteracion se
detecta correctamente; todos los archivos en disco estan `INTACTO`.

Artefactos: `data/blockchain/cadena.json`,
`data/reports/blockchain_{bloques,validacion,integridad,prueba_alteracion}.csv`.

---

## 8. Dashboard

Dashboard en Streamlit (`streamlit run src/dashboard.py`) con cinco pestanas:

| Pestana | Contenido |
|---|---|
| Resumen | KPIs (flujos, reportes, clases, bloques), modelo ganador y arquitectura. |
| Datos (ETL) | Distribucion de clases y evidencia de calidad del ETL. |
| Machine Learning | Metricas por modelo, matriz de confusion, importancia y predicciones. |
| PNL | Sentimiento, terminos TF-IDF, IOCs, ejemplos y reporte narrativo. |
| Blockchain | Estado de la cadena, integridad y **verificador de hash** (subir un archivo y comparar su SHA-256). |

El dashboard cubre asi los requisitos: cantidad de registros analizados,
categorias principales, resultados del modelo, indicadores, graficas, resultados
del texto, entidades, predicciones y verificacion de la Blockchain.

---

## 9. Resultados y discusion

- **ETL:** se superaron los minimos exigidos por casi 4x en flujos y 3.3x en
  reportes; se mantiene trazabilidad de las 10 transformaciones.
- **ML:** el Arbol de Decision clasifica con F1-macro 0.9845; las clases con muy
  pocos ejemplos (Heartbleed, Infiltration) son las mas dificiles, lo esperable
  en datasets desbalanceados.
- **PNL:** el corpus es mayoritariamente negativo (57.3%), consistente con su
  naturaleza de amenazas; se extraen decenas de miles de indicadores de
  compromiso utiles para enriquecer el analisis.
- **Blockchain:** demuestra integridad sin depender de terceros; la alteracion se
  detecta de inmediato.
- **Limitaciones:** se trabaja sobre una muestra balanceada de CICIDS2017 (no el
  dataset completo) por costo computacional; la Blockchain es local (no
  distribuida); el resumen de PNL es extractivo.

---

## 10. Conclusiones

Se construyo un prototipo funcional de extremo a extremo que cubre los seis
componentes del proyecto (datos, ETL, ML, PNL, Blockchain y dashboard). El
sistema es reproducible (un solo comando), auditable (evidencia por etapa) y
verificable (trazabilidad criptografica). Los resultados de ML y PNL son buenos y
coherentes con el dominio, y la integracion de las piezas permite presentar una
solucion completa para el analisis de incidentes de ciberseguridad.

---

## 11. Referencias

- Sharafaldin, I., Habibi Lashkari, A., & Ghorbani, A. A. (2018). *Toward
  Generating a New Intrusion Detection Dataset and Intrusion Traffic
  Characterization.* ICISSP 2018. (CICIDS2017)
- Hutto, C. J., & Gilbert, E. (2014). *VADER: A Parsimonious Rule-based Model for
  Sentiment Analysis of Social Media Text.* ICWSM.
- scikit-learn, pandas, Streamlit, Plotly: documentacion oficial.
