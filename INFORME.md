# INFORME FINAL DEL PROYECTO INTEGRADOR

## 1. TÍTULO DEL PROYECTO

Sistema Inteligente de Análisis, Predicción y Trazabilidad de Incidentes de Ciberseguridad

## 2. INTEGRANTES

[Nombre del Equipo — Integrantes: 3 estudiantes]

- Asignatura: Proyecto Integrador de IA
- Fecha: Octubre 2026

## 3. PLANTEAMIENTO DEL PROBLEMA

Los equipos de seguridad gestionan dos fuentes de información incompatibles entre sí:

1. **Registros estructurados de tráfico de red (NetFlow/pcap derivados):** números tabulares sobre flujos (bytes enviados/recibidos, paquetes, flags, intervalos, etc.) que requieren un modelo de clasificación para separar tráfico legítimo de ataques.
2. **Reportes CTI (cyber threat intelligence) sin estructurar:** texto narrativo con tácticas, técnicas, indicadores de compromiso (IOCs), resúmenes y contexto que normalmente los analistas leen, pero no cruzan con los datos técnicos.

Hoy un analista hace este cruce a mano, y deriva tres problemas:

- **Falta de predicción operativa:** el tráfico se procesa, pero no hay un modelo que lo clasifique por tipo de ataque con precisión medida.
- **Falta de contexto:** aunque un flujo sea "un ataque", no se sabe si está asociado a una campaña descrita en CTI.
- **Falta de trazabilidad:** los artefactos que justifican el análisis (modelo, métricas, indicadores extraídos, reportes) no tienen garantías criptográficas de que no fueron alterados después de generados.

### 3.1 Escenario concreto

Un SOC recibe tráfico malicioso y reportes de amenaza de una misma familia de actividad. Sin un sistema integrado:

- el tráfico queda como "anomalía clasificada" sin saber qué tipo de ataque es,
- los reportes quedan como documentos sueltos sin conexión con el tráfico,
- y no hay evidencia auditable de que el modelo o el reporte no fueron modificados tras el análisis.

### 3.2 Problema que resuelve el prototipo

“¿Puede un sistema local y reproducible analizar casos de tráfico CICIDS2017, clasificarlos por tipo de ataque, extraer los IOCs relevantes de reportes CTI en el mismo entorno, y dejar pruebas verificables de que los artefactos no fueron alterados?”

## 4. ANTECEDENTES

### 4.1 CICIDS2017

El dataset CICIDS2017 (Canadian Institute for Cybersecurity, UNB) es el estándar académico de referencia para evaluar IDS. Contiene tráfico benigno y ataques reales (DoS, DDoS, PortScan, Web Attack, Brute Force, Bot, Heartbleed, Infiltration) capturados durante una semana. Ha sido utilizado para comparar clasificadores clásicos y profundas en intrusiones.

Fuente estructurada, pública y reproducible. Se utiliza el espejo parquet `bvsam/cic-ids-2017` en HuggingFace por comodidad de descarga (mismo I/O que el original, convertido a parquet). Alcance: 8 archivos parquet, ~2,8 M flujos crudos.

### 4.2 Cyber Threat Intelligence (CTI) Reports

Los reportes CTI contienen los IOCs que el modelo no puede "adivinar": dominios de C2, CVEs, hashes y familias de malware. Son el complemento natural del tráfico: uno dice "hay tráfico anómalo", los otros dicen "de qué amenaza se trata".

Se utiliza el corpus público `guychuk/cyber-threat-intelligence-reports` (974 reportes únicos tras deduplicar exactamente 4 textos repetidos por truncamiento).

### 4.3 Organismos y literatura de referencia

- Canadian Institute for Cybersecurity (UNB) — CICIDS2017.
- Sharafaldin, I., Habibi Lashkari, A., & Ghorbani, A. A. (ICISSP 2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization.*
- Hutto, C. J., & Gilbert, E. (2014). *VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text.* (usada como proxy de sentimiento, no como prueba semántica).
- Mirror HuggingFace para descarga reproducible offline: `bvsam/cic-ids-2017` y `guychuk/cyber-threat-intelligence-reports`.

## 5. JUSTIFICACIÓN

### 5.1 Por qué un prototipo y no una plataforma comercial

El enunciado pide un prototipo funcional, no un producto comercial. Por tanto:

- Las decisiones favorecen **reproducibilidad** y **evidencia auditable** sobre escalado.
- Se usan tecnologías del curso (pandas, scikit-learn, VADER, Streamlit, plotly) en vez de frameworks propietarios.
- Se declaran honestamente las limitaciones (muestreo, soporte minoritario, VADER como proxy).

### 5.2 Por qué estas cuatro piezas

| Pieza | Problema que resuelve | Alternativas descartadas |
|---|---|---|
| ETL | Unifica CICIDS2017 y CTI en formatos comparables; limita muestras, documenta calidad | Datos directos sin pipeline |
| ML | Clasifica tipo de ataque sobre tráfico tabulado | Reglas manuales; NDDL/SNORT estáticas |
| PNL | Extrae IOCs y contexto de CTI (IPs, CVEs, hashes, dominios, sentimiento) | Ignorar la rama textual |
| Blockchain | Registro y verificación de integridad sin infraestructura externa | "Archivo en git" sin cadena de hashes |

### 5.3 Valor para un analista SOC

1. Entra un CSV de flujos ⇒ sale "probable tipo de ataque" con métricas verificadas.
2. Se abre un reporte CTI ⇒ sale tabla de IOCs para bloquear C2/infraestructura.
3. La cadena blockchain garantiza que el modelo y los artefactos citados son los que se usaron.

## 6. OBJETIVO GENERAL

Diseñar y desarrollar un prototipo local y reproducible de un Sistema Inteligente que analice incidentes de ciberseguridad desde tráfico estructurado y reportes CTI, clasifique los ataques con un modelo de ML justificado, procese texto con PNL para extraer IOCs y resúmenes, e integre ambos resultados en un reporte con nivel de riesgo verificable mediante Blockchain.

## 7. OBJETIVOS ESPECÍFICOS

1. Delimitar el problema de análisis de incidentes y seleccionar las fuentes de datos.
2. Obtener, organizar y preparar CICIDS2017 y CTI Reports con ETL documentado.
3. Diseñar una arquitectura de extremo a extremo (Ingesta → ETL → ML ∥ PNL → Integración → Blockchain → Dashboard).
4. Implementar y evaluar un modelo de ML de clasificación multiclase.
5. Implementar al menos 3 funcionalidades de PNL (representadas, sentimiento, entidades, resumen).
6. Implementar un mecanismo Blockchain SHA-256 para registrar y verificar artefactos.
7. Desarrollar dashboard interactivo que permita consultar resultados y verificar integridad.
8. Integrar todos los componentes en un prototipo reproducible.
9. Evaluar resultados, documentar limitaciones y proponer mejoras.

## 8. ALCANCE Y LIMITACIONES

### 8.1 Alcance

- Prototipo local, un solo ordenador, sin despliegue productivo.
- Datos reales (CICIDS2017 + CTI Reports).
- 6 algoritmos clásicos de ML comparados con validación cruzada sobre TRAIN.
- 4 funcionalidades PNL implementadas.
- 8 bloques blockchain con verificación offline (`--solo-verificar`) y en vivo (dashboard).

### 8.2 Limitaciones explícitas

| # | Limitación | Mitigación aplicada |
|---|---|---|
| 1 | **Muestreo agresivo** (~0,7 % del crudo sobrevive; DoS y BENIGN quedan fijos en 4.444 cada uno) | ETL documentada en `INFORME.md` §12; métricas sobre test estratificado; alternativas no evaluadas por límites de cómputo |
| 2 | **Clases ínfimas** (Heartbleed n=11, Infiltration n=36 en test: 3 y 11) | Se reportan `metricas_por_clase.csv`; su F1 no es conclusión estadística |
| 3 | **Prevalencia artificial** tras el balanceo ⇒ métricas optimistas vs. producción | Se documenta en `README.md` (§“Problemas encontrados”) y en `INFORME.md` §12/§16; elección de métrica macro sobre ponderada |
| 4 | **VADER en CTI**: proxy léxico, no medida calibrada de amenaza | Se reporta como proxy, no como semántica; disclaimers en `README.md` |
| 5 | **Extracción de IOCs por regex**, no NER entrenado | Se validan IPv4/fechas/versiones y se desdefanguean IOCs antes de extraer; se excluye doble conteo URL/email→dominio |
| 6 | **Blockchain propia sin consenso** | Garantiza detección de alteraciones, no inmutabilidad distribuida; ámbito local |
| 7 | **Sin pinning por revisión** de los datasets en HuggingFace | Se documenta en las condiciones de uso; recomendación de pin por hash en futuras versiones |
| 8 | **Sin tests entre-documentos (near-duplicates)** | Se deduplican los 4 textos exactamente idénticos detectados (tras truncado) |

### 8.3 Supuestos

- los datos CICIDS2017 son representativos de la semana de captura descrita por UNB.
- los reportes CTI contienen información sobre amenazas reales, no datos sensibles de organizaciones concretas.
- no se manejan datos personales identificables en ningún artefacto.

## 9. USUARIOS POTENCIALES

- **Analistas SOC:** clasifican rápidamente tráfico nuevo por tipo de ataque.
- **Investigadores CTI:** extraen IOCs sin leer 974 reportes.
- **Docentes/estudiantes:** demostración académica de integración ETL+ML+PNL+Blockchain.
- **Auditores técnicos:** verifican integridad de artefactos con `--solo-verificar`.

## 10. DESCRIPCIÓN GENERAL DE LA SOLUCIÓN

### 10.1 Principio de diseño

**Todo artefacto relevante es hasheado y verificable.** Los artefactos que justifican el análisis no son archivos sueltos: forman un paquete auditable con hash SHA-256. Quien revise el prototipo puede comprobar que el modelo, el predictor, las métricas, los reportes y el dataset no fueron alterados desde su generación.

### 10.2 Flujo de extremo a extremo

```
ENTRADA (HuggingFace)
  CICIDS2017 (8 parquet)    CTI Reports (1 parquet)
         ↓                        ↓
         └──────────┬─────────────┘
                    ↓
          2. ALMACENAMIENTO (data/raw)
                    ↓
          3. ETL (T01..T10)
                    ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
   4a. PNL sobre textos      4b. ML sobre flujos
   TF-IDF · VADER · IOCs     selección CV · GridSearchCV
   resumen extractivo           6 algoritmos entrenados
        └─────────────┬─────────────┘
                    ↓
         4c. INTEGRACIÓN  ⇒  reporte_integrado.{md,json}
                    ↓
         5. TRAZABILIDAD  ⇒  BLOCKCHAIN (8 bloques, SHA-256)
                    ↓
         6. PRESENTACIÓN  ⇒  DASHBOARD Streamlit (5 pestañas)
```

### 10.3 Orquestador reproducible

`python src/run_all.py --sin-descargar` ejecuta ETL → ML → PNL → Integración → Blockchain de forma secuencial; si cualquier etapa falla, el pipeline se detiene y lo deja en `logs/pipeline.log`. La reproducibilidad está soportada por:

- semilla fija (`SEED=20261007`) en muestreo, split, CV y GridSearchCV;
- parámetros de transformaciones persistidos en `data/processed/estandarizacion.json` (media/desviación) y `data/processed/transformacion.json` (límites winsor, constantes, derivadas T07);
- evidencia generada en disco en cada etapa (`data/reports/`, `data/blockchain/`, `data/figures/`).

## 11. FUENTES DE DATOS

### 11.1 CICIDS2017 (Canadian Institute for Cybersecurity, UNB)

- **Tipo:** flujo de red etiquetado (ataques reales capturados de tráfico e inyectado durante una semana).
- **Origen oficial:** https://www.unb.ca/cic/datasets/ids-2017.html
- **Espejo usado:** `huggingface.co/datasets/bvsam/cic-ids-2017` (parquet convertido por terceros por compatibilidad con pandas).
- **Contenido:** 8 archivos (Monday–Friday, mañana/tarde), ~2,8 M flujos crudos, 79 columnas, 9 clases tras el mapeo a 9 clases.
- **Etiquetas originales:** BENIGN + ataques (DoS, DDoS, PortScan, Web Attack, BruteForce, Bot, Heartbleed, Infiltration) — con encoding de etiquetas con `\ufffd` en algunas filas, por lo que `T02` normaliza unicode antes de agruparlas.
- **Tamaño usado:** 19.815 flujos (tras muestreo → balanceo), 72 predictoras.

### 11.2 Cyber Threat Intelligence Reports (guychuk)

- **Tipo:** reportes de texto sin estructurar (CTI).
- **Origen:** `huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports`
- **Contenido:** técnicas, tácticas, IOCs (IPs, dominios, URLs, hashes, CVEs y correos), resúmenes y contexto de campañas reales.
- **Tamaño:** 978 reportes crudos → 974 tras deduplicar textos exactos (tras truncar a 20 000 chars).
- **Licencia:** no hay licencia explícita publicada; uso restringido a demostración académica.

### 11.3 Condiciones de uso

- **CICIDS2017:** cite a UNB y a Sharafaldin et al. (2018); no redistribuya el dataset; texto libre para investigación. El espejo HuggingFace se usa solo por comodidad de descarga; para publicación formal use UNB oficial.
- **CTI Reports:** uso demostrativo/académico; no redistribuya; sin datos personales identificables (los IOCs son atributos de infraestructura, no datos de personas).
- **Ambos:** sin datos personales identificables de personas físicas; IOCs son de infraestructura (C2, dominios maliciosos, hashes).

### 11.4 Descarga manual (fuentes exactas)

`python src/run_all.py` descarga automáticamente ambos (con aviso de licencia CICIDS2017). Enlaces directos:

- **CICIDS2017 (UNB, requiere aceptar términos):** https://www.unb.ca/cic/datasets/ids-2017.html
- **Espejo parquets (HuggingFace):** https://huggingface.co/datasets/bvsam/cic-ids-2017/tree/main/machine_learning
- **Reportes CTI (parquet directo):** https://huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports/resolve/main/data/train-00000-of-00001.parquet

Archivos del espejo CICIDS2017 (subcarpeta `machine_learning/`):

- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Monday-WorkingHours.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Tuesday-WorkingHours.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Wednesday-workingHours.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet
- https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/machine_learning/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet

### 11.5 Volumen y esfuerzo de datos

| Métrica | Flujos (ML) | CTI (PNL) |
|---|---|---|
| Fuentes crudas | 2.830.743 filas | 978 docs |
| Tras muestreo por archivo | 36.193 | — |
| Tras deduplicado exacto crudo | 34.181 | — |
| Tras faltantes | 34.157 | — |
| **Final ML/PNL** | **19.815** | **974** |
| Mínimo del enunciado | 5.000 | 300 |
| Reproducibilidad | `SEED=20261007` | `SEED=20261007` |

## 12. DATASET: DESCRIPCIÓN, TRATAMIENTO Y PROCESADO

### 12.1 Columnas CICIDS crudas

CICIDS2017 proporciona 79 columnas originales. Tras la selección de características (`T08`) quedan 72 predictoras numéricas. Ejemplos de variables y su significado semántico (apoyado en la documentación UNB):

| Variable | Tipo | Significado |
|---|---|---|
| Destination Port | entero | puerto de destino |
| Flow Duration | entero | duración del flujo en microsegundos |
| Total Fwd/Bwd Packets | entero | paquetes en cada dirección |
| Total Length of Fwd/Bwd Packets | entero | bytes payload en cada dirección |
| Flow IAT Mean/Std/Min/Max | float | media/desv./min/max entre paquetes consecutivos |
| SYN/FIN/RST/PSH/ACK/URG Flag Count | entero | contadores de flags TCP |
| Down/Up Ratio | float | ratio tráfico entrante/saliente |
| Bwd/Fwd Header Length | entero | bytes de cabeceras |
| bytes_por_paquete_fwd | derivada T07 | Total Length Fwd / Total Fwd Packets |
| ratio_paquetes_bwd_fwd | derivada T07 | Total Backward Packets / Total Fwd Packets |
| ratio_flag_syn | derivada T07 | SYN Flag Count / Total Fwd Packets |
| tasa_bytes_fwd | derivada T07 | Total Length Fwd / Flow Duration |

### 12.2 Cadena de transformaciones aplicadas (T01→T10)

El flujo ejecuta `etl_extract` → `etl_transform` → `etl_load`. Las transformaciones están documentadas en `data/reports/calidad_transformaciones.csv`.

| Etapa | Operación | Antes → después | Justificación |
|---|---|---|---|
| T01 | Deduplicado exacto (flujos) | 36.193 → 34.181 | Evita que el mismo paquete aparezca en train y test |
| T01 | Deduplicado exacto (CTI) | 978 → 974 (después del `CTI_MAX_CHARS`) | 4 textos idénticos tras truncado |
| T02 | Unicode (normalización de etiquetas) | normaliza etiquetas con `\ufffd` | Unificar encoding |
| T03 | Coerce numérico | `pd.to_numeric(errors='coerce')` | Forzar tipos sin romper filas |
| T04 | Inf→NaN + `dropna` | 34.181 → 34.157 | 24 filas con NaN/Inf descartadas (43 celdas) |
| T05 | Validación/agrupación etiquetas | mapeo a 9 clases | Estabilizar el número de categorías |
| T07 | Derivadas | 57 columnas brutas → +4 derivadas | Señales que el modelo necesita (tasa, ratio SYN, ratio paquetes/…] |
| T09 | **Muestreo y balanceo** | 34.157 → 19.815 | `random_state=SEED`; máx. 4.444/clase (DoS/BENIGN) |
| T06 | Winsorización IQR×3 | recorte en 120.290 celdas (57 vars), fit en TRAIN | Evita que outliers condicionen el entrenamiento |
| T08 | Constantes fuera | 82 → 72 | Columnas con nunique≤1 en TRAIN |
| T10 | Split train/test | 19.815 → 13.870 / 5.945 | Estratificado, 70/30, `random_state=SEED` |
| T10 | Escalado | media≈0/desv≈1 en train | `StandardScaler`, fit en TRAIN |

### 12.3 muestreo y balanceo (T09)

CICIDS2017 crudo está fuertemente desbalanceado (BENIGN ≈ 80 %). Antes del split se reduce cada clase al mínimo entre `DEFAULT_MAX_PER_CLASS=6000` y `40000/9≈4444`. Outcomes:

- DoS y BENIGN quedan en 4.444 cada uno.
- Heartbleed: 11, Infiltration: 36 (soporte ínfimo).
- Test estratificado refleja la misma proporción muestreada, no la real del dataset crudo.

### 12.4 Particionado

- **Train (70 %): 13.870 filas**
- **Test (30 %): 5.945 filas**
- **Estratificado** por clase con `random_state=SEED`.

### 12.5 Estandarización (fit TRAIN) y persistencia

`StandardScaler.fit_transform(train)`, `.transform(test)`. `data/processed/estandarizacion.json` guarda `media`, `desviacion` y `columnas` (72). `data/processed/transformacion.json` guarda límites winsor (fit), columnas constantes y derivadas T07. `models/predictor.joblib` empaqueta modelo + ambos + orden de features.

### 12.6 Evidencia generada

- `data/reports/evidencia_extraccion.csv` y `evidencia_extraccion_columnas.csv` (perfil por archivo/columna)
- `data/reports/calidad_transformaciones.csv` (línea a línea)
- `data/reports/perfil_columnas.csv` (diccionario de datos automatizado)
- `data/reports/validacion_minimos.csv` (**19.815 ≥ 5.000**, **974 ≥ 300**)
- `logs/pipeline.log`

## 13. MACHINE LEARNING

### 13.1 Definición del problema

- **Problema:** ¿a qué tipo de ataque (o BENIGN) pertenece un flujo de red?
- **Tipo:** clasificación supervisada multiclase (9 clases).
- **Target:** `label` (9 categorías tras mapeo a 9 clases).
- **Métrica objetivo:** **F1-macro** (evaluación sobre todas las clases por igual). Accuracy y F1-weighted se reportan como complemento, pero no sustituyen a F1-macro como criterio de selección.

### 13.2 Variables usadas

Tras `T08`: 72 predictoras numéricas persistentes. Variables derivadas T07 (4) forman parte de las 72 (tras T08 la selección las retiene).

### 13.3 Algoritmos considerados

| Algoritmo | Hiperparámetros principales | Por qué se considera |
|---|---|---|
| Regresión Logística | `C=1.0`, `max_iter=1000`, `class_weight=balanced` | Baseline lineal interpretable |
| Árbol de Decisión | `criterion='gini'`, `max_depth=None`, `class_weight='balanced'` | Reglas explícitas; propenso a sobreajustar |
| Random Forest | `max_depth=20`, `n_estimators=300` (GridSearchCV) | Ensamble robusto; importancia de variables |
| KNN | `n_neighbors=5`, distancia euclídea | Vecinos; requiere escala normalizada |
| Gaussian NB | `var_smoothing` por defecto | Probabilístico rápido; supone independencia |
| SVM (RBF) | `kernel=rbf`, `class_weight=balanced` | Frontera no lineal; costoso en train |

### 13.4 Selección honesta del ganador

Los 6 candidatos se ordenan por la media de F1-macro en validación cruzada estratificada (`StratifiedKFold(5, shuffle, SEED=20261007)`) **sobre el conjunto de entrenamiento**. No se usa el conjunto de test para elegir el ganador. Si hay empate en CV se desempata por `cv_desviacion` (menor varianza entre folds).

Resultado de CV (media ± std):

| Modelo | cv F1-macro | cv std |
|---|---|---|
| Random Forest | 0.976 (→ 0.978 tras grid) | 0.0109 |
| Árbol de Decisión | 0.9745 | 0.0243 |
| KNN | 0.9503 | 0.0124 |
| Regresión Logística | 0.9245 | 0.0093 |
| Gaussian NB | 0.9148 | 0.0170 |
| SVM (RBF) | 0.9133 | 0.0118 |

### 13.5 Ajuste de hiperparámetros

El ganador (Random Forest) se ajusta con `GridSearchCV` (F1-macro, CV=5) sobre:
`{'max_depth': [10, 20], 'n_estimators': [100, 200, 300]}` → **`{'max_depth': 20, 'n_estimators': 300}`**. Sólo el ganador se reajusta; el resto compite con defaults (comparación homogénea en la selección, no en el tuning absoluto — decisión documentada para no inflar el costo).

### 13.6 Resultados por clase (test, 5.945 filas)

| Clase | Precision | Recall | F1 | Soporte |
|---|---|---|---|---|
| BENIGN | 0.9924 | 0.9820 | 0.9872 | 1333 |
| Bot | 0.9766 | 1.0000 | 0.9882 | 585 |
| BruteForce | 0.9988 | 0.9988 | 0.9988 | 845 |
| DDoS | 0.9983 | 0.9983 | 0.9983 | 600 |
| DoS | 0.9955 | 0.9955 | 0.9955 | 1333 |
| Heartbleed | 1.0000 | 1.0000 | 1.0000 | **3** |
| Infiltration | 1.0000 | 0.9091 | 0.9524 | **11** |
| PortScan | 1.0000 | 0.9983 | 0.9992 | 592 |
| WebAttack | 0.9876 | 0.9907 | 0.9891 | 643 |

Heartbleed (3 casos) e Infiltration (11 casos) no son conclusiones estadísticas; se reportan por completitud pero su F1 no es generalizable.

### 13.7 Interpretación

- Random Forest gana por CV (0.978 ± 0.011) aunque Árbol de Decisión tiene F1-macro 1 centésima superior en test (0.9905 vs 0.9899); la diferencia está dentro de la variabilidad de los folds.
- Las **importancias** (feature importances) van en `data/reports/importancia_variables.csv`; las top-10 incluyen Destination Port (≈ 0.089), Init_Win_bytes y Total Length of Fwd Packets.

### 13.8 Evidencia de ejecución real

- `models/modelo_mejor.joblib` (Random Forest)
- `models/predictor.joblib` (modelo + features + `transformacion.json` + `estandarizacion.json`)
- `data/processed/predicciones_test.parquet` (`label`, `prediccion`, `acierto`)
- `data/reports/metricas_modelos.csv`, `metricas_por_clase.csv`, `matriz_confusion.csv`, `importancia_variables.csv`, `ml_resumen.json`
- `data/reports/validacion_minimos.csv` (ML mínimo 5.000 ⇒ 19.815; PNL mínimo 300 ⇒ 974)
- `logs/pipeline.log` (ETL ~115 s, ML ~70 s, PNL ~62 s, Blockchain < 1 s)

### 13.9 Figuras generadas (lectura e interpretación)

**`comparacion_modelos.html`.** Barra horizontal con la métrica de selección: el eje X es F1-macro con CV=5 (sobre train), ordenado por F1-macro en test; cada algoritmo tiene un color distinto. Se eliminaron las etiquetas numéricas externas para evitar saturación; el valor exacto está siempre disponible en el hover y en `metricas_modelos.csv`. La selección real sigue siendo por CV (gana Random Forest por CV=0.978, no por test); por eso la barra representa CV, no el valor de test. Aunque Árbol de Decisión tiene un F1-macro en test ligeramente mayor (0.9905 vs 0.9899), no se elige por test; elegir por test rompería la honestidad de la selección. La figura prueba que se comparan varios modelos, no que se entrena uno solo.

**`matriz_confusion.html`.** Heatmap de la matriz de confusión del ganador sobre el holdout (5.945 flujos). Filas=reales, columnas=predichas. Los bloques en la diagonal son aciertos: BENIGN 1309/1333, BruteForce 844/845, DoS 1327/1333, DDoS 599/600, PortScan 591/592, WebAttack 637/643. Infiltration 10/11, Heartbleed 3/3 (ya declarado ínfimo). La anotación inferior incluye accuracy global y F1-macro. Sirve para ver qué clases confunde el modelo; no como métrica de éxito aislada (la métrica de selección fue CV).

## 14. PROCESAMIENTO DE LENGUAJE NATURAL (PNL)

### 14.1 Objetivo

Demostrar que el prototipo procesa información textual real (CTI) con técnicas clásicas y produce señales útiles (términos, sentimiento, IOCs, resúmenes) integradas en el bloque de trazabilidad.

### 14.2 Conjunto de textos y preparación

- **Corpus:** 978 documentos → **974 únicos** tras deduplicar textos exactos (producidas tras truncar a 20 000 chars).
- **Truncado:** cada reporte se corta a 20 000 caracteres (`CTI_MAX_CHARS`).
- **Enriquecidos por documento:** `data/processed/reportes_enriquecidos.parquet` (974 filas) con sentimiento, IOCs, términos clave y resumen.

### 14.3 Funcionalidad 1 — Representación (TF-IDF)

- Vectorizador: `TfidfVectorizer(stop_words=ENGLISH_STOP_WORDS ∪ {com, www, http, https, exe, figure, ...}, ngram_range=(1,2), min_df=2, max_features=4000, sublinear_tf=True)`.
- Preprocesado en memoria para vectorizar: `hxxp→http`, enmascarar URLs/hashes/CVEs/IPs/correos antes de vectorizar (evita que el vocabulario refleje enlaces, no técnicas).
- 4.000 términos en el vocabulario (tope por diseño). Los top-25 reales van en `pnl_top_terminos.csv`:
  `malware, used, file, data, information, security, threat, attacks, using, attack, ...`
- Reportados artefactos no-listados (`com`, `www`) por eliminación del vocabulario.

### 14.4 Funcionalidad 2 — Análisis de sentimiento (VADER)

- Motor: VADER (Hutto & Gilbert, 2014) vía `vaderSentiment`.
- Truncado a 4.000 chars (`PNL_MAX_CHARS_SENTIMIENTO`); en el corpus truncado el sesgo es marginal (el orden negativo>positivo se mantiene 57.3 % vs 40.3 % full-text vs 40.3 % truncado).
- **Distribución:** 558 negativos (57,3 %), 392 positivos (40,3 %), 24 neutros (2,5 %).
- **Motor reportado como proxy léxico, no como medida calibrada de amenaza.** CTI formal dispara léxicos negativos (attack, malware, exploit, vulnerability) que VADER no considera contextualmente.

### 14.5 Funcionalidad 3 — Reconocimiento de entidades (IOCs/NER por reglas)

#### 14.5.1 Patrones

| Tipo | Patrón | Uso típico |
|---|---|---|
| IPv4 | `\b(?:\d{1,3}\.){3}\d{1,3}\b` con validación `==` 0-255, sin ceros iniciales, sin reservadas | C2, nodos de infraestructura |
| Dominio | TLD whitelist (`com|net|org|io|ru|cn|...`) | Malicious domains |
| URL | `https?://[^\s...]` | Payload URLs |
| MD5/SHA1/SHA256 | `[a-fA-F0-9]{32/40/64}` | hashes |
| CVE | `CVE-\d{4}-\d{4,7}` | vulnerabilidades |
| Email | `[\w.+-]+@[\w-]+\.[\w.-]+` | contacto/fuente |

#### 14.5.2 Reglas de saneo

1. **Desdefangueo**: el corpus contiene IOCs en forma `hxxp://...`, `evil[.]com`; antes de extraer, se normaliza a texto emparejable (`hxxp→http`, `[.]→.`, `hXXp→http`).
2. **Exclusión mutua** (orden url → email → ipv4 → hashes → cve → dominio): un dominio dentro de una URL o email NO se vuelve a contar como dominio suelto.
3. **IPv4 reservadas** excluidas: `0.0.0.0/8`, `127.0.0.0/8`, `169.254.0.0/16`, `224.0.0.0/4`, `240.0.0.0/4`. Las RFC1918 (privada) se conservan porque son relevantes en incidentes internos.
4. **"Versiones"**: una cadena tipo `10.2.3.4` solo se descarta si en ~18 caracteres alrededor hay contexto `version|v1\.|release|build|update|dot`; ya no se descarta 8.8.8.8 por "números pequenos".
5. **Docstring coherente**: `_ip_valida` documenta lo que hace el código (rangos válidos, sin leading zeros, reservadas) y remite a `_es_version_contexto` para la decisión IOC vs versión.

#### 14.5.3 KPIs medidos (974 docs)

| Indicador | Valor |
|---|---|
| Total de IOCs | 38.759 ocurrencias |
| IOCs distintos (sumando por tipo) | 27.261 |
| CVEs distintos | 405 |
| Dominios distintos | 5.912 |
| IPv4 distintas | 2.373 (3.700 ocurrencias) |
| URLs distintas | 7.595 |
| Hashes distintos | 10.840 (md5+sha1+sha256) |
| Correos distintos | 136 |
| Documentos con ≥1 IOC | 906/974 (93,0 %) |

### 14.6 Funcionalidad 4 — Generación de lenguaje (resumen extractivo)

- Por cada reporte: top-2 oraciones por suma de IDF sobre palabras significativas.
- Filtro de TOC/dot-leaders (`/\.{4,}/`), encabezados de sección y oraciones con <8 palabras o no mayoritariamente alfabéticas; fallback a primera oración razonable.
- Reporte narrativo global: `data/reports/pnl_reporte.md` (integrando KPIs, sentimiento, top términos, top IOCs, 3 ejemplos de resumen).
- Limitación explícita: un extractivo sobre texto-PDF-mal-extraído puede devolver oraciones aisladas poco coherentes; mejorar requiere margen + modelo generativo/NER entrenado (trabajo futuro).

### 14.7 Evidencia PNL

- `data/processed/reportes_enriquecidos.parquet` (974 filas)
- `data/reports/pnl_{resumen.csv,sentimiento.csv,top_terminos.csv,iocs.csv,entidades.csv,reporte.md}`
- `data/figures/pnl_sentimiento.html`, `pnl_top_terminos.html`
- `tests/test_pnl.py` (10 tests, incluyendo reglas de desdefangueo y reservadas)

### 14.8 Figuras generadas (lectura e interpretación)

**`pnl_sentimiento.html`.** Conteo de documentos por sentimiento VADER. Los CTI resultan 558 negativos (57,3 %), 392 positivos (40,3 %), 24 neutros (2,5 %). El encabezado del índice lo define como **proxy léxico** (VADER sobre 4.000 chars), no como medida calibrada de "amenaza percibida"; por eso el informe nunca lo usa como prueba de semántica, sino como señal de contexto en la integración ML+PNL. En el acto conviene decirlo así: "la mayoría del corpus habla en vocabulario de ataque, no sobre una escala humana de alegría/tristeza". Cada sentimiento tiene un color distinto (rojo/verde/gris) para lectura inmediata.

**`pnl_top_terminos.html`.** Suma TF-IDF por término del vectorizador (1-2 gramas, tope 4.000, stopwords personalizadas). Muestran los términos con más peso léxico en el corpus (`malware`, `used`, `file`, `data`, `information`, `security`, `threat`, `attacks`, `attack`, ...). Cada término tiene un color distinto y todas las etiquetas son visibles (sin colapso). No son conteo de ocurrencias ni importancia de clase: son relevancia TF-IDF. Útil para saber **de qué habla el corpus** de forma global (malware/APT), no para decidir urgencia de un TOC concreto.

## 15. COMPONENTE BLOCKCHAIN

### 15.1 Qué se registra y por qué

| Artefacto | Bloque | Por qué es relevante |
|---|---|---|
| `flujos_clean.parquet` | bloque 1 | el dataset procesado sobre el que se mide todo |
| `reportes_enriquecidos.parquet` | bloque 2 | PNL con IOCs y sentimiento usados en el reporte |
| `modelo_mejor.joblib` | bloque 3 | el clasificador elegido para el prototipo |
| `predictor.joblib` | bloque 4 | inferencia reproducible en dashboard |
| `metricas_modelos.csv` | bloque 5 | comparación honesta de los 6 algoritmos |
| `pnl_reporte.md` | bloque 6 | reporte de texto generado |
| `reporte_integrado.json` | bloque 7 | nivel de riesgo global ML+PNL |

Justificación: estos son los artefactos que sostienen el flujo completo Entrada→Resultados→Dashboard; si cualquiera cambia después de la entrega, la cadena lo detecta.

### 15.2 Estructura de bloques

Cada bloque contiene: `indice`, `timestamp` (UTC), `datos` (metadatos del artefacto), `hash_previo`, `hash` (SHA-256 del bloque completo). El bloque génesis (`indice=0`) es el punto de partida.

### 15.3 Mecanismo de hash

- SHA-256 sobre el contenido del bloque serializado (sin hash truncado, sin algoritmo propietario).
- `hash_archivo(ruta)`: hash de los bytes del artefacto (SHA-256 por bloque).
- `calcular_hash`: hash del bloque completo enlazando `hash_previo`.

### 15.4 Procedimiento de validación

1. **Interna (`es_valida()`)**: recalcula todos los hashes en orden; verifica que `hash_previo` coincide con el hash del bloque anterior; fallos = cadena inválida.
2. **Externa (`--solo-verificar`)**: sin reconstruir la cadena, re-hashea cada archivo registrado comparándolo con la cadena persistida; reporta OK/MODIFICADO/FALTANTE por artefacto.
3. **Dashboard**: pestaña Blockchain carga `cadena.json`, recalcula `es_valida()`, re-hashea los 7 artefactos en vivo y muestra estado por artefacto.

### 15.5 Prueba de alteración (integración)

`tests/test_blockchain.py` contiene una prueba end-to-end con `tmp_path`: se construye una cadena sobre archivos reales, se modifica 1 byte de uno, y se verifica que `--solo-verificar` reporta MODIFICADO. Simular la alteración en memoria (no disco+cadena) demuestra detección pero no re-hash de artefactos — se corrige con el verificador offline añadido en este entregable.

### 15.6 Archivado de cadena previa

Antes de cada reconstrucción, `ejecutar()` archiva la cadena previa íntegra en `data/blockchain/cadena_<UTC>.backup.json` (no se sobrescribe aquiela sin copia). Si la cadena previa es internamente inválida o falta algún artefacto, la ejecución **archiva y aborta** sin reconstruir (o sólo lo hace si se invoca con `--reconstruir-forzadamente`).

### 15.7 Limitaciones explícitas

- **Sin consenso distribuido**: cadena propia, ámbito local, un único custodio.
- **Sin firma criptográfica**: cualquier actor con acceso al árbol de trabajo puede fabricar una cadena coherente si reconstruye todos los artefactos; para ancla real se necesitaría Git-LFS + hash anclado en un tag externo o notario de timestamp (timestamping público) (trabajo futuro).
- **No es inmutable por construcción**: se protege siendo honesto sobre lo que cubre y verificándola en vivo.

### 15.8 Evidencia

- `data/blockchain/cadena.json` (8 bloques, archivado con backup)
- `data/reports/blockchain_{bloques,validacion,prueba_alteracion}.csv`
- `tests/test_blockchain.py`

## 16. ARQUITECTURA DEL SISTEMA

### 16.1 Capas

1. **Ingesta** (`etl_extract` + `config.py`): descarga desde HuggingFace, perfilado tipado.
2. **Almacenamiento** `data/raw/`: parquet crudos, no versionados.
3. **ETL** (`etl_transform` + `etl_load`): T01..T10 adaptados al Problema; `calidad_transformaciones.csv` con evidencia línea-a-línea; `validacion_minimos.csv`.
4. **Analítica** (en paralelo):
   - `ml.py`: entrenamiento, CV, selección, GridSearchCV, evaluación, guardado de predicciones/modelo/predictor.
   - `pnl.py`: vectorización, sentimiento, IOCs, resúmenes, KPIs.
5. **Integración** (`integrar.py`): reporte único con nivel de riesgo.
6. **Trazabilidad** (`blockchain.py`): hash SHA-256, cadena, verificación offline/en vivo, archivado.
7. **Presentación** (`dashboard.py`): Streamlit 5 pestañas.

### 16.2 Flujo de datos detallado

```
src/etl_extract.py
   ↓ (parquet crudo)
src/etl_transform.py
   ↓ (dataframes limpios + transformacion.json + predicciones)
src/etl_load.py
   ↓ (processed/*.parquet + reports/*.csv)
src/ml.py          src/pnl.py
        ↓                     ↓
        └────► src/integrar.py ◄────┘
                      ↓
             src/blockchain.py   src/dashboard.py
```

### 16.3 Decisiones de diseño y justificación

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Módulos planos en `src/` | Paquete instalable | Simple, sin setup, reproducible para el curso |
| `run_all.py` orquestador con etapas | Scripts separados sin contrato | Detiene ante fallo; reproduce flujo completo |
| `transformacion.json` (winsor/constantes/T07) | Mantener sólo en memoria | Sin él, inferencia ≠ entrenamiento (fuga train→prod) |
| `estandarizacion.json` | Re-escalar en cada ejecución | Determinismo; dashboard no recarga data |
| VADER (proxy) | Modelo de sentimiento entrenado | Tamaño CTI adecuado; honestidad metodológica |
| Regex IOCs | NER entrenado | Reglas limpias, desdefangueo estable, documentadas |
| Blockchain propia (SHA-256) | Red permisionada / Ethereum | Suficiente para integridad; no requiere infraestructura |
| Streamlit dashboard | Flask/Vue custom | Interactividad rápida; AppTest cubierto en tests |
| Selección por CV | Ganador por test | Evita sesgo de selección |
| Archivado backup de cadena | Sobre-escritura limpia | Preserva evidencia antes/después de reconstruir |
| Deduplicar tras truncado | Sólo antes | El error se produce tras `CTI_MAX_CHARS`, no antes |

## 17. DASHBOARD

### 17.1 Contenido

| Pestaña | Qué muestra |
|---|---|
| Resumen | registros analizados, mínimos cumplidos, CV F1-macro del ganador |
| Datos (ETL) | tabla de transformaciones (antes/después/filas), mínimos verde |
| ML | comparación de 6 modelos, matriz de confusión, importancia de variables, uploader de flujos CSV crudo con predicción 1- clic + score |
| PNL | top términos, sentimiento, entidades/IOCs, KPIs, resúmenes |
| Blockchain | validez en vivo de la cadena (`es_valida()`), estado por artefacto re-hasheado (OK/MODIFICADO/FALTANTE), uploader SHA-256 de cualquier archivo |

### 17.2 AppTest

`tests/test_dashboard.py` ejecuta `streamlit.testing.v1.AppTest` sobre el dashboard real: las 5 pestañas renderizan sin excepción y se comprueban contenidos mínimos (por pestaña).

## 18. RESULTADOS

### 18.1 Mínimos del enunciado

| Componente | Mínimo | Valor | Cumple |
|---|---|---|---|
| Registros CICIDS2017 | 5.000 | **19.815** | ✅ |
| Reportes CTI | 300 | **974** | ✅ |

### 18.2 Machine Learning

- Ganador: **Random Forest** (GridSearchCV `{'max_depth': 20, 'n_estimators': 300}`).
- **F1-macro test: 0.9899**, **Accuracy: 0.9933**, **F1-weighted: 0.9933**
- **CV F1-macro: 0.9780 ± 0.0109** (coherente con test)
- Evidencia: `ml_resumen.json`, `metricas_modelos.csv`, `metricas_por_clase.csv`, `predicciones_test.parquet`.

### 18.3 PNL

- **4 funcionalidades** (TF-IDF, sentimiento VADER, entidades/IOCs, resumen extractivo).
- 38.759 IOCs detectados (ocurrencias), 27.261 distintos.
- 906/974 documentos con ≥1 IOC (93,0 %).

### 18.4 Integración ML+PNL

- Nivel de riesgo global: **ALTO** {F1 ≥ 0.85 (señal ML fiable), 57.3 % docs negativos en CTI (señal de contexto)}.

### 18.5 Blockchain

- **8 bloques**, `cadena_valida=True`, **7/7 artefactos OK** verificados en vivo (`--solo-verificar`).
- Archivos registrados: `dataset_procesado`, `reportes_pnl`, `modelo_ml`, `predictor_ml`, `metricas_ml`, `reporte_pnl`, `reporte_integrado` + génesis.

### 18.6 Pruebas

- **64/64** tests en verde (`python -m pytest tests -q`).

## 19. CONCLUSIONES

El prototipo integra con éxito un flujo completo: descarga, ETL honesta, selección justificada de modelo (basada en CV, no en test), PNL con IOCs normalizados, integración ML+PNL en un reporte trazable, y Blockchain verificable tanto offline como en dashboard. Las cifras son reproducibles desde los artefactos del repo (`ml_resumen.json`, `validacion_minimos.csv`, `cadena.json`). Las limitaciones de muestreo y soporte minoritario están declaradas y no invalidan el entregable académico.

## 20. TRABAJO FUTURO

1. **Clases minoritarias:** enriquecer Heartbleed/Infiltration con más datos crudos (no solo submuestreo).
2. **Prevalencia real:** reportar también métricas sobre test con distribución original (~80 % BENIGN) aunque sean más bajas.
3. **NER entrenado:** sustituir reglas por un modelo (p.ej. `d3fender`/spaCy+NER o transformer pequeño).
4. **VADER → modelo de sentimiento CTI:** re-etiquetar 100–200 docs con 2 anotadores y calibrar.
5. **Pinning de datasets:** `huggingface_hub` con `revision=<sha>` y checksums `md5`/`sha256` de parquets.
6. **Ancla externa:** notario de hash (timestamping público) o firma GPG del hash cabeza.
7. **Append-only real:** mutar cadena.json sólo por append, no reconstrucción completa.
8. **Muestreo estratificado:** dedup antes de muestrear por clase (hoy dedup post-muestreo).
9. **Despliegue local reproducible:** `Dockerfile` + `requirements-lock.txt`.

## 21. ANEXOS

### A. Comandos de verificación

```powershell
python src/run_all.py --sin-descargar
python -m pytest tests -q
python src/blockchain.py --solo-verificar
python -c "import pandas as pd; print(pd.read_parquet('data/processed/flujos_test.parquet').shape)"  # (5945, 75)
```

### B. Estándar de evidencia por etapas

| Etapa | Artefacto en disco |
|---|---|
| Extracción | `data/reports/evidencia_extraccion.csv`, `evidencia_extraccion_columnas.csv` |
| Transformación | `data/reports/calidad_transformaciones.csv` |
| Validación mínimos | `data/reports/validacion_minimos.csv` |
| ML | `metricas_modelos.csv`, `metricas_por_clase.csv`, `matriz_confusion.csv`, `importancia_variables.csv`, `ml_resumen.json` |
| PNL | `pnl_*.csv`, `pnl_reporte.md` |
| Integración | `reporte_integrado.{md,json}` |
| Blockchain | `cadena.json`, `blockchain_bloques.csv`, `blockchain_validacion.csv` |
| Dashboard | 5 pestañas, AppTest |

### C. Estructura de código y responsabilidades

```
src/
  config.py         rutas, parámetros, etiquetas, DATA_MIN/MAX
  etl_extract.py    descarga + perfilado
  etl_transform.py  T01..T10 (winsor fit-train, T07 derivadas, T08 constantes, T10 split+scale)
  etl_load.py       validación vs. mínimos
  ml.py             entrenamiento, CV, GridSearchCV, predicción reutilizable
  pnl.py            TF-IDF, VADER, IOCs (desdefangueo), resumen extractivo
  integrar.py       reporte ML+PNL con nivel de riesgo
  blockchain.py     SHA-256, cadena, --solo-verificar, archivado de cadena previa
  dashboard.py      Streamlit 5 pestañas + verificador en vivo
  run_all.py        orquestador (detiene ante fallo)
```

### D. Glosario

- **IOC:** Indicator of Compromise (IP, hash, dominio, URL, CVE, email).
- **CV:** Cross-Validation (validación cruzada estratificada).
- **F1-macro:** media de F1 por clase; no ponderada por tamaño.
- **Desdefangueo:** revertir la ofuscación `hxxp`/`[.]` de los IOCs.
- **Winsorización:** recortar valores extremos a límites IQR×k.
- **Estratificado:** el split mantiene la proporción de clases.

## ANEXO E — ESQUEMA DE PRESENTACIÓN (fuente para el Word)

15 diapositivas propuestas, condensadas a partir de este informe. Úsese como esqueleto para el documento externo (Word/Slides); la redacción formal y el diseño quedan fuera del repo.

1. **Portada** — Tema 3: Sistema Inteligente … Integrantes/Equipo — Asignatura — Fecha.
2. **Problema** — tráfico + CTI; falta de integración; necesidad de trazabilidad.
3. **Solución propuesta** — ETL + ML + PNL + Integración + Blockchain + Dashboard.
4. **Arquitectura** — Fuentes → Ingesta → ETL → ML ∥ PNL → Integración → Blockchain → Dashboard.
5. **Datos usados** — CICIDS2017 (19.815 × 72) + CTI Reports (974 únicos).
6. **ETL ejecutado** — T01..T10; winsor fit-train; mínimos 19.815 / 974.
7. **Machine Learning** — 6 algoritmos; selección por CV; ganador Random Forest; F1-macro 0.9899 (test) / CV 0.9780.
8. **PNL** — TF-IDF · VADER · IOCs (38.759, desdefangueados) · resumen extractivo.
9. **Blockchain** — 8 bloques SHA-256; `--solo-verificar`; verificación en vivo.
10. **Dashboard** — 5 pestañas; predicción CSV en vivo; verificador Blockchain.
11. **Resultados** — F1-macro 0.9899; ALTO riesgo; Mínimos OK
12. **Demostración** — `--sin-descargar` + `streamlit run`.
13. **Conclusiones** — integración coherente; evidencia auditable; datos reales.
14. **Trabajo futuro** — Heartbleed/Infiltration; NER; pinning de datasets; ancla externa.
15. **Q&A**

## 22. BIBLIOGRAFÍA

- Sharafaldin, I., Habibi Lashkari, A., & Ghorbani, A. A. (2018). Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization. ICISSP 2018.
- Canadian Institute for Cybersecurity (UNB). CICIDS2017. https://www.unb.ca/cic/datasets/ids-2017.html
- HuggingFace Datasets: `bvsam/cic-ids-2017` y `guychuk/cyber-threat-intelligence-reports`.
- Hutto, C. J., & Gilbert, E. (2014). VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text.
- Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. JMLR.

## 23. METODOLOGÍA Y ENFOQUE DE DESARROLLO

El equipo siguió un enfoque iterativo basado en CRISP-DM como guía conceptual con prácticas de verificación:

- **Comprensión del problema:** delimitar Tema 3 a incidentes concretos (flujos de red + reportes CTI).
- **Recolección y comprensión de datos:** perfilado completo de CICIDS2017 (2,8 M filas → 19.815 tras muestreo) y CTI 978→974 únicos.
- **Preparación de datos:** T01..T10 con ajustes fit-train (winsor, constantes, escalado) y evidencia auditable.
- **Modelado:** 6 algoritmos, selección por CV sin mirar test.
- **Evaluación:** holdout estratificado, métricas por clase honestas (Heartbleed/Infiltration declaradas no generalizables).
- **Integración y trazabilidad:** ML+PNL → integración; cadena blockchain para artefactos.
- **Revisión:** auditorías multiagente internas (sin modificar) y ejecución del pipeline completo tras cada cambio.
