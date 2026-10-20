# PRESENTACIÓN - Sistema Inteligente de Análisis, Predicción y Trazabilidad de Incidentes de Ciberseguridad

## DIAPOSITIVA 1: PORTADA
- Tema 3: Sistema Inteligente de Análisis, Predicción y Trazabilidad de Incidentes de Ciberseguridad
- Integrantes: [Nombres]
- Asignatura: Proyecto Integrador IA
- Fecha: Octubre 2026

## DIAPOSITIVA 2: PROBLEMA IDENTIFICADO
- Detección de incidentes requiere integrar tráfico (estructurado) + reportes CTI (no estructurado)
- Necesidad de trazabilidad e integridad de evidencias
- Falta de integración ML+PNL+Blockchain en un prototipo funcional

## DIAPOSITIVA 3: SOLUCIÓN PROPUESTA
Sistema modular que integra:
- ETL (limpieza/validación/auditoría)
- Machine Learning (clasificación multiclase)
- PNL (términos, sentimiento, IOCs/entidades, resumen)
- Blockchain (hash SHA-256 + verificación)
- Dashboard Streamlit (5 pestañas)

## DIAPOSITIVA 4: ARQUITECTURA
Fuentes (CICIDS2017 + CTI) → ETL → ML ∥ PNL → Integración → Resultados → Hash → Blockchain → Dashboard

## DIAPOSITIVA 5: DATOS UTILIZADOS
- CICIDS2017 (UNB, Sharafaldin et al. 2018) - bvsam/cic-ids-2017 (parquet)
- CTI Reports - guychuk/cyber-threat-intelligence-reports
- Tras ETL: 19.815 flujos, 74 features | 978 reportes CTI

## DIAPOSITIVA 6: PROCESAMIENTO REALIZADO (ETL)
- Descarga, consolidación, limpieza (NaN/Inf), normalización etiquetas
- Validación mínimos: >=5000 / >=300
- Estandarización, splits estratificados, auditoría

## DIAPOSITIVA 7: MACHINE LEARNING
- 6 algoritmos, selección del ganador por CV estratificado (5 folds)
- Ganador: Random Forest (ajustado con GridSearchCV: max_depth=20, n_estimators=300)
- F1-macro = 0.9899 | Accuracy = 0.9933 (CV F1-macro = 0.9780)
- Inferencia en vivo: subir CSV de flujos y clasificar
- Matriz confusión + comparación generadas

## DIAPOSITIVA 8: PROCESAMIENTO DE LENGUAJE NATURAL
- TF-IDF (términos relevantes)
- VADER (sentimiento)
- IOCs/Entidades (IPs, dominios, URLs, hashes...) → 33.844 IOCs, 405 CVEs, 1.838 IPs válidas
- Validación de IPs + exclusión mutua (sin doble conteo)
- Resumen extractivo + pnl_reporte.md

## DIAPOSITIVA 9: BLOCKCHAIN
- Cadena SHA-256 propia
- 8 bloques, cadena_valida = True
- Registro de artefactos (incluye reporte integrado ML+PNL) + verificación + detección alteración
- Verificación en vivo en el dashboard
- Evidencias: cadena.json, CSVs

## DIAPOSITIVA 10: DASHBOARD
- Streamlit con 5 pestañas (Resumen, Datos, ML, PNL, Blockchain)
- Gráficas Plotly, tabla predicciones, predicción en vivo y verificador SHA-256
- AppTest: 5 pestañas, sin excepciones

## DIAPOSITIVA 11: RESULTADOS
- ETL OK (19.815 / 978)
- ML excelente (F1-macro 0.9899, RF ajustado)
- PNL funcional (4 features, KPIs reales)
- Integración ML+PNL: nivel de riesgo ALTO
- Blockchain íntegro (8 bloques)
- 46/46 tests OK

## DIAPOSITIVA 12: DEMOSTRACIÓN
- python src/run_all.py --sin-descargar --solo etl ml pnl integrar blockchain
- streamlit run src/dashboard.py
- Verificación tests: python -m pytest -q

## DIAPOSITIVA 13: CONCLUSIONES
- Integración coherente y funcional
- Datos reales, reproducible
- Cumple todos requisitos
- Trazabilidad garantizada

## DIAPOSITIVA 14: TRABAJO FUTURO
- Mejorar clases minoritarias
- NER avanzado
- Despliegue
- Integración SIEM

## DIAPOSITIVA 15: PREGUNTAS
¿Preguntas?
