"""ENTREGABLE 7 - Dashboard (Streamlit).

Interfaz para consultar los resultados del sistema sin participar en el
desarrollo. Presenta, como pide el enunciado: cantidad de registros
analizados, principales categorias, resultados del modelo, indicadores,
graficas, resultados del analisis de texto, entidades identificadas,
predicciones y un mecanismo de consulta/verificacion de la Blockchain.

Uso:
    streamlit run src/dashboard.py
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from blockchain import Cadena  # noqa: E402
from config import BLOCKCHAIN_JSON, FIGURES, MODELS, PROCESSED, REPORTS  # noqa: E402
from ml import cargar_predictor, predecir  # noqa: E402

st.set_page_config(page_title="Sistema Inteligente de Ciberseguridad", layout="wide")


# --------------------------------------------------------------------------
# Carga (con cache)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def leer_parquet(ruta: str):
    p = Path(ruta)
    return pd.read_parquet(p) if p.exists() else None


@st.cache_data(show_spinner=False)
def leer_csv(ruta: str):
    p = Path(ruta)
    return pd.read_csv(p) if p.exists() else None


@st.cache_data(show_spinner=False)
def leer_texto(ruta: str) -> str:
    p = Path(ruta)
    return p.read_text(encoding="utf-8") if p.exists() else ""


@st.cache_data(show_spinner=False)
def leer_json(ruta: str):
    p = Path(ruta)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def falta(*rutas) -> bool:
    faltantes = [Path(r).name for r in rutas if not Path(r).exists()]
    if faltantes:
        st.warning("Faltan resultados: " + ", ".join(faltantes) + ". Ejecuta `python src/run_all.py`.")
        return True
    return False


st.title("Sistema Inteligente de Analisis, Prediccion y Trazabilidad")
st.caption("Deteccion y analisis de incidentes de ciberseguridad (Tema 3).")

tabs = st.tabs(["Resumen", "Datos (ETL)", "Machine Learning", "PNL", "Blockchain"])


# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------
with tabs[0]:
    flujos = leer_parquet(str(PROCESSED / "flujos_clean.parquet"))
    reportes = leer_parquet(str(PROCESSED / "reportes_enriquecidos.parquet"))
    metricas = leer_csv(str(REPORTS / "metricas_modelos.csv"))
    bloques = leer_csv(str(REPORTS / "blockchain_bloques.csv"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flujos de red analizados", f"{0 if flujos is None else len(flujos):,}")
    c2.metric("Reportes de texto", f"{0 if reportes is None else len(reportes):,}")
    c3.metric("Clases de riesgo", f"{0 if flujos is None else flujos['label'].nunique()}")
    c4.metric("Bloques en la cadena", f"{0 if bloques is None else len(bloques):,}")

    if metricas is not None and not metricas.empty:
        mejor = metricas.sort_values("cv_f1_macro", ascending=False).iloc[0]
        st.success(
            f"Modelo ganador: **{mejor['modelo']}**  |  "
            f"accuracy = {mejor['accuracy']:.3f}  |  F1-macro = {mejor['f1_macro']:.3f}  |  "
            f"CV F1-macro = {mejor['cv_f1_macro']:.3f}"
        )

    integrado = leer_json(str(REPORTS / "reporte_integrado.json"))
    if integrado:
        nivel = integrado.get("nivel_riesgo", "N/D")
        color = {"ALTO": "🔴", "MEDIO": "🟠", "BAJO": "🟢"}.get(nivel, "⚪")
        st.info(f"Nivel de riesgo global (ML + PNL): {color} **{nivel}**")

    st.subheader("Arquitectura del sistema")
    st.code(
        "FUENTES DE DATOS (CICIDS2017 + reportes CTI)\n"
        "        |\n"
        "   INGESTA (descarga)\n"
        "        |\n"
        "   ALMACENAMIENTO (data/raw)\n"
        "        |\n"
        "   PREPARACION (ETL: T01..T10)\n"
        "        |\n"
        "   +----+----+\n"
        "   |         |\n"
        "  PNL        ML\n"
        "   |         |\n"
        "   +----+----+\n"
        "        |\n"
        "     RESULTADOS\n"
        "        |\n"
        "  REPORTE -> SHA-256 -> BLOCKCHAIN -> VERIFICACION\n"
        "        |\n"
        "     DASHBOARD",
        language="text",
    )

    reporte_integrado = leer_texto(str(REPORTS / "reporte_integrado.md"))
    if reporte_integrado:
        with st.expander("Reporte integrado ML + PNL (nivel de riesgo)"):
            st.markdown(reporte_integrado)


# --------------------------------------------------------------------------
# Datos (ETL)
# --------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Dataset procesado")
    flujos = leer_parquet(str(PROCESSED / "flujos_clean.parquet"))
    if flujos is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros", f"{len(flujos):,}")
        c2.metric("Variables", flujos.shape[1])
        c3.metric("Clases", flujos["label"].nunique())
        conteo = flujos["label"].value_counts().rename_axis("label").reset_index(name="registros")
        st.plotly_chart(
            px.bar(conteo, x="label", y="registros", color="label",
                   title="Distribucion de clases de riesgo"),
            width="stretch",
        )
    else:
        falta(PROCESSED / "flujos_clean.parquet")

    st.subheader("Evidencia de calidad del ETL")
    for nombre, titulo in [
        ("evidencia_extraccion.csv", "Extraccion"),
        ("calidad_transformaciones.csv", "Transformaciones (T01..T10)"),
        ("validacion_minimos.csv", "Validacion de minimos"),
    ]:
        df = leer_csv(str(REPORTS / nombre))
        st.markdown(f"**{titulo}**")
        if df is not None:
            st.dataframe(df, width="stretch")
        else:
            st.info(f"No disponible: {nombre}")


# --------------------------------------------------------------------------
# Machine Learning
# --------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Resultados del modelo")
    metricas = leer_csv(str(REPORTS / "metricas_modelos.csv"))
    if metricas is not None:
        st.dataframe(metricas, width="stretch")
        st.plotly_chart(
            px.bar(metricas.sort_values("f1_macro"), x="f1_macro", y="modelo",
                   orientation="h", title="Comparacion de algoritmos (F1-macro)"),
            width="stretch",
        )
    else:
        falta(REPORTS / "metricas_modelos.csv")

    col1, col2 = st.columns(2)
    with col1:
        matriz = leer_csv(str(REPORTS / "matriz_confusion.csv"))
        if matriz is not None:
            matriz = matriz.set_index(matriz.columns[0])
            st.plotly_chart(
                px.imshow(matriz, text_auto=True, color_continuous_scale="Blues",
                          title="Matriz de confusion"),
                width="stretch",
            )
    with col2:
        imp = leer_csv(str(REPORTS / "importancia_variables.csv"))
        if imp is not None:
            st.plotly_chart(
                px.bar(imp.head(15).sort_values("importancia"), x="importancia", y="variable",
                       orientation="h", title="Variables mas importantes"),
                width="stretch",
            )

    st.subheader("Predicciones sobre el conjunto de prueba")
    pred = leer_parquet(str(PROCESSED / "predicciones_test.parquet"))
    if pred is not None:
        st.dataframe(pred.head(50), width="stretch")
        aciertos = pred["acierto"].mean() * 100
        st.caption(f"Aciertos sobre {len(pred):,} registros: {aciertos:.2f}%")

    st.subheader("Prediccion en vivo (inferencia)")
    st.caption(
        "Sube un CSV con flujos de red crudos (mismas columnas que CICIDS2017, sin escalar). "
        "El sistema aplica la estandarizacion guardada y el modelo ganador."
    )
    archivo_flujos = st.file_uploader("CSV de flujos a clasificar", type=["csv"], key="ml_inferencia")
    if archivo_flujos is not None:
        try:
            crudo = pd.read_csv(io.BytesIO(archivo_flujos.getvalue()))
            predictor = cargar_predictor()
            resultado = predecir(crudo, predictor)
            st.success(
                f"Predicciones generadas con **{predictor['modelo_nombre']}** sobre "
                f"{len(resultado):,} flujos."
            )
            resumen = (
                resultado["label_predicho"].value_counts().rename_axis("clase").reset_index(name="flujos")
            )
            st.plotly_chart(
                px.bar(resumen, x="clase", y="flujos", color="clase",
                       title="Distribucion de clases predichas"),
                width="stretch",
            )
            st.dataframe(resultado[["label_predicho"]].head(50), width="stretch")
        except FileNotFoundError:
            st.warning("Falta `models/predictor.joblib`. Ejecuta `python src/run_all.py --sin-descargar --solo etl ml`.")
        except KeyError as exc:
            st.error(f"El CSV no tiene el formato esperado: {exc}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo procesar el CSV: {exc}")


# --------------------------------------------------------------------------
# PNL
# --------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Analisis de lenguaje")
    dist = leer_csv(str(REPORTS / "pnl_sentimiento.csv"))
    terminos = leer_csv(str(REPORTS / "pnl_top_terminos.csv"))
    iocs = leer_csv(str(REPORTS / "pnl_iocs.csv"))

    if dist is not None:
        st.plotly_chart(
            px.bar(dist, x="sentimiento", y="documentos", color="sentimiento",
                   title="Documentos por sentimiento (VADER)"),
            width="stretch",
        )
    col1, col2 = st.columns(2)
    with col1:
        if terminos is not None:
            st.plotly_chart(
                px.bar(terminos.head(15).sort_values("relevancia"), x="relevancia", y="termino",
                       orientation="h", title="Terminos mas relevantes (TF-IDF)"),
                width="stretch",
            )
    with col2:
        if iocs is not None:
            st.markdown("**Entidades (IOCs) mas frecuentes**")
            st.dataframe(iocs.head(20), width="stretch")

    enr = leer_parquet(str(PROCESSED / "reportes_enriquecidos.parquet"))
    if enr is not None:
        st.subheader("Ejemplos de reportes analizados")
        cols = ["id", "sentimiento", "n_iocs", "resumen", "terminos_clave"]
        st.dataframe(enr[cols].head(15), width="stretch")

    reporte = leer_texto(str(REPORTS / "pnl_reporte.md"))
    if reporte:
        with st.expander("Reporte generado automaticamente (GLN)"):
            st.markdown(reporte)


# --------------------------------------------------------------------------
# Blockchain
# --------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Estado de la cadena")
    bloques = leer_csv(str(REPORTS / "blockchain_bloques.csv"))
    veredicto = None
    if BLOCKCHAIN_JSON.exists():
        try:
            _cadena = Cadena.cargar()
            _ok, _errores = _cadena.es_valida()
            veredicto = (_ok, _errores, len(_cadena.bloques))
        except Exception as exc:  # noqa: BLE001
            veredicto = (False, [f"No se pudo leer {BLOCKCHAIN_JSON.name}: {exc}"], 0)

    if bloques is not None:
        if veredicto is not None:
            _ok, _errores, _n = veredicto
            if _ok:
                st.success(f"Cadena valida: {_n} bloques, sin alteraciones (verificado en vivo desde {BLOCKCHAIN_JSON.name}).")
            else:
                st.error("La cadena NO es valida. Errores: " + "; ".join(_errores))
        else:
            st.warning(f"No existe {BLOCKCHAIN_JSON.name}: se muestra el ultimo reporte guardado.")
        st.dataframe(bloques, width="stretch")
    else:
        falta(REPORTS / "blockchain_bloques.csv")

    integridad = leer_csv(str(REPORTS / "blockchain_integridad.csv"))
    if integridad is not None:
        st.markdown("**Integridad de los archivos en disco**")
        st.dataframe(integridad, width="stretch")

    alteracion = leer_csv(str(REPORTS / "blockchain_prueba_alteracion.csv"))
    if alteracion is not None:
        st.markdown("**Prueba de modificacion y deteccion**")
        st.dataframe(alteracion, width="stretch")

    st.subheader("Verificacion de un archivo")
    st.caption("Sube un archivo y se calculara su SHA-256 para compararlo con el registrado.")
    archivo = st.file_uploader("Archivo a verificar")
    if archivo is not None and bloques is not None:
        sha = hashlib.sha256(archivo.getvalue()).hexdigest()
        st.write(f"SHA-256 calculado: `{sha}`")
        coincide = bloques[bloques["sha256"] == sha]
        if not coincide.empty:
            st.success(f"El hash coincide con el bloque registrado: {coincide.iloc[0]['archivo']}")
        else:
            st.error("El hash NO coincide con ningun bloque registrado (informacion modificada o no registrada).")

    st.caption(f"Archivo de la cadena: {BLOCKCHAIN_JSON.name} | Figuras: {FIGURES.name}/ | Modelo: {MODELS.name}/")
