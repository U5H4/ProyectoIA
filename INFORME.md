# INFORME FINAL DEL PROYECTO INTEGRADOR

## 1. TÍTULO DEL PROYECTO

Sistema Inteligente de Análisis, Predicción y Trazabilidad de Incidentes de Ciberseguridad

## 2. INTEGRANTES

[Nombre del Equipo - Integrantes: 3 estudiantes]

- Asignatura: Proyecto Integrador de IA
- Fecha: Octubre 2026

## 3. PLANTEAMIENTO DEL PROBLEMA

La detección y análisis de incidentes de ciberseguridad requiere integrar información estructurada (registros de tráfico de red) y no estructurada (reportes de inteligencia de amenazas - CTI). Además, resulta fundamental garantizar la integridad y trazabilidad de los artefactos generados (modelos, resultados y evidencias) para su auditoría.

## 4. ANTECEDENTES

El dataset CICIDS2017 (Canadian Institute for Cybersecurity, UNB) ha sido ampliamente utilizado para evaluar sistemas de detección de intrusiones (IDS). Complementariamente, los reportes de Cyber Threat Intelligence contienen información textual relevante sobre tácticas, técnicas, indicadores de compromiso (IOCs) y contexto de ataques.

## 5. JUSTIFICACIÓN

Se justifica el desarrollo de un sistema que integre ETL, Machine Learning, Procesamiento de Lenguaje Natural y Blockchain para ofrecer análisis, predicción y trazabilidad de incidentes, proporcionando evidencias verificables.

## 6. OBJETIVO GENERAL

Diseñar y desarrollar un prototipo funcional de un Sistema Inteligente de Análisis, Predicción y Trazabilidad de Incidentes de Ciberseguridad que procese información estructurada y no estructurada, aplique ML y PNL, y garantice trazabilidad e integridad mediante Blockchain.

## 7. OBJETIVOS ESPECÍFICOS

1. Identificar y delimitar el problema de análisis de incidentes de ciberseguridad.
2. Obtener, organizar y preparar conjuntos de datos reales (CICIDS2017 y CTI Reports).
3. Diseñar la arquitectura con flujo completo de información.
4. Implementar un modelo de Machine Learning para clasificación multiclase de tráfico/ataques.
5. Implementar técnicas de PNL sobre reportes CTI (TF-IDF, sentimiento, entidades/IOCs, resumen).
6. Implementar Blockchain para registro y verificación de integridad de artefactos relevantes.
7. Desarrollar un dashboard interactivo para visualizar e interpretar resultados.
8. Integrar todos los componentes en un prototipo funcional.
9. Evaluar resultados, establecer limitaciones, conclusiones y mejoras.

## 8. ALCANCE Y LIMITACIONES

**Alcance:** Prototipo funcional local que procesa 19.815 flujos y 978 reportes CTI, compara 6 modelos, enriquece texto, registra hashes en cadena de bloques y visualiza resultados.

**Limitaciones:**

- Entorno local (sin despliegue productivo).
- Clases minoritarias (Heartbleed/Infiltration) con bajo soporte.
- Extracción de IOCs basada en reglas (HEX/regex), no en un modelo NER entrenado.
- La Blockchain es propia y de ámbito local: garantiza integridad y detección de alteraciones, no consenso distribuido entre múltiples nodos.

## 9. USUARIOS POTENCIALES

Analistas de SOC, investigadores en ciberseguridad, docentes/estudiantes para demostración académica.

## 10. DESCRIPCIÓN GENERAL DE LA SOLUCIÓN

Pipeline modular: descargar → ETL → ML → PNL → Integración → Blockchain → Visualización (Dashboard). Reproducible con `python src/run_all.py`, probado (46/46 tests).

## 11. FUENTES DE DATOS

- **CICIDS2017:** Canadian Institute for Cybersecurity (UNB), Sharafaldin et al. (ICISSP 2018). Oficial: https://www.unb.ca/cic/datasets/ids-2017.html. Mirror parquet: https://huggingface.co/datasets/bvsam/cic-ids-2017
- **CTI Reports:** https://huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports

**Datos finales:** 19.815 flujos (74 features), 978 reportes CTI.

## 12. DATASET: DESCRIPCIÓN, TRATAMIENTO Y PROCESADO

**Originales:** 8 archivos parquet CICIDS2017, cti_reports.parquet.

**Tratamiento ETL:** validación de columnas, conversión de tipos, eliminación NaN/Inf, normalización de etiquetas (unificación), filtrado, estandarización, splits train/test (estratificado).

**Dataset procesado:** flujos_clean.parquet (19.815 filas, 74 columnas), reportes_clean.parquet (978), reportes_enriquecidos.parquet, predicciones_test.parquet.

**División:** train/test estratificado 70/30 (13.870 / 5.945). Estandarización guardada en estandarizacion.json.

**Muestreo:** balanceo aleatorio por clase (`random_state=SEED`), evitando que cada clase quede concentrada en un único día de captura.

## 13. MACHINE LEARNING

- **Problema:** Clasificación multiclase (9 clases principales tras mapeo).
- **Tipo:** Supervisado.
- **Algoritmos considerados:** Logistic Regression, Decision Tree, Random Forest, KNN, Gaussian NB, SVM (RBF).
- **Selección:** el ganador se elige por la media de F1-macro en validación cruzada estratificada (CV_FOLDS=5) sobre el conjunto de entrenamiento, sin mirar el test (evita sesgo de selección).
- **Ganador:** Random Forest.
- **Ajuste de hiperparámetros:** GridSearchCV (F1-macro, CV=5) → `{max_depth: 20, n_estimators: 300}`.
- **Métricas (test):** F1-macro = 0.9899, Accuracy = 0.9933, F1-weighted = 0.9933.
- **CV F1-macro:** 0.9780, coherente con el resultado de test.
- **Inferencia:** `models/predictor.joblib` empaqueta el modelo ganador y la estandarización; el dashboard clasifica flujos crudos subidos por el usuario.
- **Evidencias:** models/modelo_mejor.joblib, data/reports/ml_resumen.json, figuras comparacion_modelos.html, matriz_confusion.html, predicciones_test.parquet.

## 14. PROCESAMIENTO DE LENGUAJE NATURAL (PNL)

**Textos:** reportes CTI (978).

**Funcionalidades implementadas (>=3):**

- **Representación:** TF-IDF (top términos relevantes).
- **Análisis de sentimiento:** VADER (negativo/neutral/positivo).
- **Reconocimiento de entidades/IOCs:** IPs, dominios/subdominios, URLs, hashes, emails, CVEs y palabras clave. Se validan las IPv4 (se descartan versiones tipo 10.2.3.4) y se evita el doble conteo (un dominio incluido en una URL o email no se cuenta aparte). KPIs calculados sobre todos los documentos: 33.844 IOCs, 405 CVEs distintos, 3.490 dominios distintos, 1.838 IPs válidas distintas.
- **Generación de lenguaje natural:** Resumen extractivo por reporte + reporte global (pnl_reporte.md).

**Evidencias:** data/processed/reportes_enriquecidos.parquet, pnl_*.csv, figuras pnl_top_terminos.html, pnl_sentimiento.html, data/reports/pnl_reporte.md.

## 15. COMPONENTE BLOCKCHAIN

- **Implementación:** Cadena propia con SHA-256 (sin red comercial).
- **Campos:** indice, timestamp, datos, hash_previo, hash.
- **Información registrada:** dataset limpio, reportes enriquecidos, modelo ML, predictor de inferencia, métricas ML, reporte PNL y reporte integrado ML+PNL (7 artefactos + bloque génesis = 8 bloques).
- **Verificación:** recalcula cada hash y el encadenamiento; incluye prueba de alteración y comprobación de integridad de los archivos en disco (todos INTACTO). El modo `--solo-verificar` valida la cadena existente sin reconstruirla.
- **Verificación en vivo en el dashboard:** la pestaña Blockchain carga `cadena.json`, recalcula `es_valida()` y detecta si el archivo fue modificado (no solo lee un CSV previo).
- **Evidencias:** data/blockchain/cadena.json, blockchain_bloques.csv, blockchain_validacion.csv, blockchain_integridad.csv, blockchain_prueba_alteracion.csv.

## 16. ARQUITECTURA DEL SISTEMA

Capas: (1) Ingesta (HuggingFace), (2) ETL (extract/transform/load), (3) Analítica (ML y PNL en paralelo), (4) Trazabilidad (Blockchain), (5) Presentación (Dashboard Streamlit). El orquestador `src/run_all.py` encadena las etapas y detiene el pipeline ante cualquier fallo.

## 17. DASHBOARD

Streamlit con 5 pestañas: Resumen, Datos (ETL), Machine Learning, PNL y Blockchain. Incluye gráficas Plotly, tabla de predicciones, entidades identificadas, **predicción en vivo** (subir CSV de flujos crudos), nivel de riesgo integrado y un verificador de archivos por SHA-256. La pestaña Blockchain muestra el estado recalculado en vivo de la cadena.

## 18. RESULTADOS

- ETL: 19.815 flujos y 978 reportes (cumple mínimos 5.000 / 300).
- ML: Random Forest ajustado, F1-macro 0.9899, Accuracy 0.9933 (CV 0.9780).
- PNL: 4 funcionalidades, 33.844 IOCs y KPIs reales sobre todo el corpus.
- Integración: reporte ML+PNL con nivel de riesgo global (ALTO).
- Blockchain: 8 bloques, `cadena_valida=True`, artefactos INTACTOS.
- Pruebas: 46/46 en verde.

## 19. CONCLUSIONES

Se integró con éxito un prototipo funcional y reproducible que combina ETL, ML, PNL y Blockchain sobre datos reales, con evidencia auditable de cada etapa y un dashboard interactivo para su consulta y verificación.

## 20. TRABAJO FUTURO

- Mejorar el soporte de clases minoritarias.
- Sustituir la extracción de IOCs por reglas por un modelo NER entrenado.
- Despliegue y eventual integración con SIEM.

## 21. BIBLIOGRAFÍA

- Sharafaldin, I., Habibi Lashkari, A., & Ghorbani, A. A. (2018). Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization. ICISSP 2018.
- Canadian Institute for Cybersecurity (UNB). CICIDS2017. https://www.unb.ca/cic/datasets/ids-2017.html
- HuggingFace Datasets: bvsam/cic-ids-2017 y guychuk/cyber-threat-intelligence-reports.
- Hutto, C. J., & Gilbert, E. (2014). VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text.

## 22. ANEXOS

- Código fuente en `src/`; pruebas en `tests/`.
- Evidencia auditable en `data/reports/` y `data/blockchain/`.
- Figuras interactivas en `data/figures/`.
