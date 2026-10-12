# Guion de la presentacion

Estructura diapositiva por diapositiva para exponer el proyecto. Duracion
objetivo: 12-15 minutos. Cada diapositiva incluye contenido y notas del orador.

---

## Diapositiva 1 - Portada

- **Titulo:** Sistema Inteligente de Analisis, Prediccion y Trazabilidad de
  Incidentes de Ciberseguridad.
- Tema 3. Nombre del equipo / integrantes. Fecha.

> Notas: saludo breve, presentar el proyecto en una frase: "un prototipo que
> analiza trafico de red y reportes de amenazas, y garantiza que los resultados
> no fueron alterados".

---

## Diapositiva 2 - Problema y motivacion

- El analista de seguridad enfrenta: mucho trafico de red y muchos reportes tecnicos.
- Necesidad: detectar ataques automaticamente e interpretar reportes en texto.
- Necesidad extra: confiar en que el resultado mostrado es autentico (trazabilidad).

> Notas: enlazar con el objetivo del tema: deteccion + analisis + trazabilidad.

---

## Diapositiva 3 - Objetivos

- Dataset: >= 5.000 flujos de red y >= 300 reportes de texto.
- Modelo de ML para clasificar trafico.
- >= 3 funcionalidades de PNL.
- Blockchain para registrar y verificar resultados.
- Dashboard para consulta.

> Notas: mencionar que todos los minimos se cumplieron con holgura.

---

## Diapositiva 4 - Datos utilizados

- **CICIDS2017** (UNB): flujos de red etiquetados; 8 dias de captura; 256 MB crudos.
- **Cyber Threat Intelligence Reports**: 978 reportes de amenazas en texto.
- Resultado tras el ETL: **19,810 flujos** (3.96x el minimo) y **978 reportes** (3.26x).

> Notas: aclarar que CICIDS2017 tiene licencia y se cita; no se redistribuye.

---

## Diapositiva 5 - Arquitectura

- Mostrar el diagrama:
  `Fuentes -> Ingesta -> ETL -> (ML | PNL) -> Resultados -> Blockchain -> Dashboard`.
- Un solo comando reproduce todo: `python src/run_all.py`.

> Notas: destacar el diseno modular y la evidencia auditable por etapa.
> Referenciar ARQUITECTURA.md.

---

## Diapositiva 6 - Preparacion de datos (ETL)

- 10 transformaciones trazables: duplicados, faltantes/infinitos, atipicos (IQR),
  variables derivadas, seleccion de caracteristicas, balanceo, division y escalado.
- Salidas: flujos limpios, reportes limpios, diccionario de datos y validacion de minimos.

> Notas: resaltar la agrupacion de >15 etiquetas originales en 9 clases de riesgo.

---

## Diapositiva 7 - Distribucion de clases

- Grafico de barras con las 9 clases:
  BENIGN 4,444 | DoS 4,444 | BruteForce 2,829 | WebAttack 2,143 | DDoS 2,000 |
  PortScan 1,955 | Bot 1,948 | Infiltration 36 | Heartbleed 11.

> Notas: explicar el desbalance (por eso se usa F1-macro) y que se muestreo para
> hacerlo tratable.

---

## Diapositiva 8 - Machine Learning: modelos

- Seis algoritmos del curso comparados con validacion cruzada (5 particiones).
- Tabla resumida: Arbol de Decision, Random Forest, KNN, Naive Bayes,
  Regresion Logistica y SVM (RBF).

> Notas: mencionar la division estratificada 70/30 y que se estandarizaron las
> variables (necesario para KNN, SVM y Regresion).

---

## Diapositiva 9 - Machine Learning: resultados

- **Modelo ganador: Arbol de Decision** con F1-macro **0.9845** (accuracy 0.987).
- Random Forest logra mayor accuracy (0.9901) pero menor F1-macro.
- Matriz de confusion e importancia de variables.

> Notas: justificar la eleccion por F1-macro (mejor ante desbalance) y por ser
> interpretable y rapido. Mostrar que las clases con pocos ejemplos son las mas
> dificiles.

---

## Diapositiva 10 - PNL

- 4 funcionalidades implementadas (se pedian 3):
  1. Representacion TF-IDF (vocabulario de 4,000 terminos).
  2. Sentimiento VADER: 57.3% negativo, promedio -0.148.
  3. Entidades/IOC: **42,345** indicadores (IPs, dominios, URLs, hashes, CVEs).
  4. Resumen extractivo + reporte narrativo.

> Notas: mostrar 2-3 ejemplos de IOCs y un resumen. Destacar utilidad para un SOC.

---

## Diapositiva 11 - Blockchain

- Que se registra: SHA-256 del dataset procesado, reportes enriquecidos, modelo,
  metricas y reporte de PNL.
- Por que: son los resultados presentados; su hash prueba que no fueron alterados.
- Estructura encadenada; verificacion total; prueba de alteracion detectada.
- Resultado: 6 bloques, cadena **valida**, archivos `INTACTO`.

> Notas: explicar el encadenamiento (cambiar un bloque invalida los siguientes).

---

## Diapositiva 12 - Dashboard

- 5 pestanas: Resumen, Datos (ETL), Machine Learning, PNL y Blockchain.
- Incluye verificador de hash: subir un archivo y comparar su SHA-256.
- Demo en vivo: `streamlit run src/dashboard.py`.

> Notas: tener el dashboard abierto; recorrer las pestanas rapidamente.
> Si no hay internet o tiempo, mostrar capturas.

---

## Diapositiva 13 - Resultados y conclusiones

- Minimos superados (3.96x y 3.26x).
- ML con F1-macro 0.9845; PNL con decenas de miles de IOCs; Blockchain valida.
- Sistema reproducible, auditable y verificable.

> Notas: cerrar con la idea de una solucion completa, no solo un modelo aislado.

---

## Diapositiva 14 - Limitaciones y trabajo futuro

- Muestra balanceada (no el dataset completo) por costo computacional.
- Blockchain local (no distribuida); resumen extractivo.
- Futuro: modelos de deep learning, PNL generativo, integracion con SIEM real.

> Notas: muestra de honestidad tecnica; invitacion a preguntas.

---

## Guion resumido de tiempos

| Bloques | Diapositivas | Tiempo |
|---|---|---|
| Introduccion y objetivos | 1-3 | 2 min |
| Datos y arquitectura | 4-5 | 2 min |
| ETL y ML | 6-9 | 5 min |
| PNL y Blockchain | 10-11 | 4 min |
| Dashboard y cierre | 12-14 | 3 min |

## Preguntas frecuentes para prepararse

- Por que Arbol de Decision y no Random Forest? (mejor F1-macro e interpretabilidad)
- Como manejan el desbalance de clases? (muestreo balanceado + F1-macro + class_weight=balanced)
- Que impide alterar la blockchain? (SHA-256 + encadenamiento; cualquier cambio rompe la cadena)
- Por que no deep learning? (el objetivo era comparar algoritmos del curso; los clasicos ya dan >98%)
