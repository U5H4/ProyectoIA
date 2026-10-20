# Guia rapida: como funciona y como probar el proyecto

## Que hace cada componente

| Componente | Que hace | Archivos relevantes |
|---|---|---|
| **Ingesta (EXTRACT)** | Descarga CICIDS2017 y reportes CTI desde HuggingFace. | src/etl_extract.py, src/config.py |
| **ETL** | Limpia, transforma (T01-T10), balancea y divide. | src/etl_transform.py, src/etl_load.py |
| **ML** | Entrena 6 modelos, ajusta el ganador y elige el mejor (F1-macro CV). | src/ml.py, models/ |
| **PNL** | Analiza texto: TF-IDF, sentimiento, IOCs, resumen. | src/pnl.py |
| **Integración** | Combina ML+PNL en un reporte con nivel de riesgo. | src/integrar.py |
| **Blockchain** | Registra SHA-256 de artefactos y verifica integridad. | src/blockchain.py, data/blockchain/ |
| **Dashboard** | Visualiza todo y permite verificar hashes. | src/dashboard.py |
| **Orquestador** | Ejecuta etapas en orden. | src/run_all.py |

## Como ejecutar (paso a paso)

### 1) Instalar dependencias (una vez)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Ver etapas disponibles

```powershell
python src/run_all.py --listar
```

### 3) Ejecutar pipeline completo (descarga + todo)

```powershell
python src/run_all.py
```

### 4) Reutilizar datos ya descargados (mas rapido)

```powershell
python src/run_all.py --sin-descargar
```

### 5) Correr pruebas

```powershell
python -m pytest -q
```

### 6) Lanzar dashboard

```powershell
streamlit run src/dashboard.py
```

El navegador abre automaticamente. Navega por las 5 pestañas: Resumen, Datos (ETL), Machine Learning, PNL, Blockchain.
En la pestaña **Machine Learning** puedes subir un CSV de flujos crudos para clasificarlos en vivo.
En la pestaña **Blockchain** puedes subir un archivo para calcular su SHA-256 y comprobar si coincide con alguno registrado.

## Estructura en una mirada

| Carpeta/Archivo | Para que sirve |
|---|---|
| data/raw/ | Datos crudos (no versionados). |
| data/processed/ | Datos limpios, train/test, predicciones, textos enriquecidos. |
| data/reports/ | CSV de evidencia (ETL, ML, PNL, Integración, Blockchain). |
| data/figures/ | Graficas HTML. |
| data/blockchain/ | Cadena JSON + evidencia. |
| models/ | Modelos entrenados (.joblib). |
| src/ | Codigo (modulos ejecutados como scripts). |
| tests/ | Pruebas automaticas (31 passing). |
| README.md | Guia general de uso. |
| README_CARPETAS.md | Explicacion detallada de cada carpeta/archivo. |
| ARQUITECTURA.md | Flujo y arquitectura. |
| INFORME.md | Informe tecnico completo. |
| PRESENTACION.md | Guion diapositiva por diapositiva. |
| GUia_RAPIDA.md | Esta guia. |

## Notas importantes

- Los datos crudos/procesados/modelos **no se versionan** (están en .gitignore).
- Todo se ejecuta desde src/ como scripts: python src/run_all.py.
- Si alguna etapa falla, el pipeline se detiene y deja evidencia en logs/pipeline.log.
- Dashboard requiere que el pipeline ya haya generado los artefactos (al menos ETL/ML/PNL/Blockchain).
