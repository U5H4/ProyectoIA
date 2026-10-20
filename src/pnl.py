"""ENTREGABLE 4 - Procesamiento de Lenguaje Natural.

Analiza los reportes de ciber-threat-intelligence (texto) e implementa cuatro
funcionalidades de las que pide el enunciado (se exigen al menos tres):

  1. Representacion del lenguaje ....... TF-IDF (con stopwords y bigramas) + terminos clave.
  2. Analisis de sentimiento ........... VADER (positivo / negativo / neutro).
  3. Reconocimiento de entidades ....... IOCs: IPv4, dominios, URLs, hashes (MD5/SHA1/SHA256),
                                         CVE y correos.
  4. Generacion de lenguaje ............ resumen extractivo por documento y reporte narrativo.

La entidad "codigo" del enunciado corresponde aqui a los CVE; las entidades de
infraestructura (IP, dominio, URL, hash) son las relevantes en ciberseguridad.

Artefactos:
    data/processed/reportes_enriquecidos.parquet
    data/reports/pnl_resumen.csv
    data/reports/pnl_sentimiento.csv
    data/reports/pnl_top_terminos.csv
    data/reports/pnl_iocs.csv
    data/reports/pnl_entidades.csv
    data/reports/pnl_reporte.md              (reporte generado automaticamente)
    data/figures/pnl_sentimiento.html
    data/figures/pnl_top_terminos.html

Uso:
    python src/pnl.py
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from config import (
    FIGURES,
    PNL_MAX_CHARS_SENTIMIENTO,
    PNL_RESUMEN_ORACIONES,
    PNL_TOP_TERMINOS,
    PROCESSED,
    REPORTS,
)
from utils import LOG, asegurar_dir, subtitulo, tabla, titulo

REPORTES = PROCESSED / "reportes_clean.parquet"


# --------------------------------------------------------------------------
# Patrones de entidades (IOCs)
# --------------------------------------------------------------------------
PATRONES = {
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "dominio": re.compile(
        r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|io|ru|cn|"
        r"info|biz|xyz|top|online|site|club|edu|gov|mil)\b",
        re.IGNORECASE,
    ),
    "url": re.compile(r"https?://[^\s\"'<>\)\]]+", re.IGNORECASE),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
    "sha1": re.compile(r"\b[a-fA-F0-9]{40}\b"),
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "cve": re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
}

_SENT_ORACION = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_LEX_NEGATIVO = {
    "attack", "exploit", "malware", "vulnerability", "critical", "severe",
    "threat", "breach", "ransomware", "compromise", "malicious", "risk",
    "danger", "dangerous", "vulnerable", "backdoor", "phishing", "trojan",
}
_LEX_POSITIVO = {
    "secure", "patched", "mitigation", "protected", "safe", "fixed", "resolved",
    "improved", "update", "defense", "protection", "hardening", "verified",
}


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------
def cargar_reportes(ruta=REPORTES) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}. Ejecuta antes:\n  python src/run_all.py --sin-descargar"
        )
    df = pd.read_parquet(ruta)
    df["text"] = df["text"].fillna("").astype(str)
    return df


# --------------------------------------------------------------------------
# 1. Representacion del lenguaje (TF-IDF)
# --------------------------------------------------------------------------
def vectorizar(textos: list[str]) -> tuple[TfidfVectorizer, object]:
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_features=4000,
        sublinear_tf=True,
    )
    matriz = vectorizer.fit_transform(textos)
    return vectorizer, matriz


def top_terminos_global(matriz, vectorizer, n: int = PNL_TOP_TERMINOS) -> pd.DataFrame:
    suma = np.asarray(matriz.sum(axis=0)).ravel()
    terminos = vectorizer.get_feature_names_out()
    orden = suma.argsort()[::-1][:n]
    return pd.DataFrame(
        {"termino": terminos[orden], "relevancia": suma[orden].round(4)}
    )


def terminos_clave_doc(matriz, vectorizer, fila: int, n: int = 6) -> str:
    terminos = vectorizer.get_feature_names_out()
    valores = matriz[fila].toarray().ravel()
    orden = valores.argsort()[::-1][:n]
    return ", ".join(terminos[i] for i in orden if valores[i] > 0)


# --------------------------------------------------------------------------
# 2. Analisis de sentimiento (VADER con respaldo simple)
# --------------------------------------------------------------------------
def _analizador():
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        return SentimentIntensityAnalyzer(), "VADER"
    except Exception:
        return None, "lexico-simple"


def sentimiento(texto: str, analizador=None) -> tuple[float, str]:
    recorte = texto[:PNL_MAX_CHARS_SENTIMIENTO]
    if analizador is not None:
        compuesto = analizador.polarity_scores(recorte)["compound"]
    else:
        palabras = re.findall(r"[a-z]+", recorte.lower())
        pos = sum(p in _LEX_POSITIVO for p in palabras)
        neg = sum(p in _LEX_NEGATIVO for p in palabras)
        total = pos + neg
        compuesto = 0.0 if total == 0 else (pos - neg) / total
    if compuesto >= 0.05:
        etiqueta = "positivo"
    elif compuesto <= -0.05:
        etiqueta = "negativo"
    else:
        etiqueta = "neutro"
    return round(float(compuesto), 4), etiqueta


# --------------------------------------------------------------------------
# 3. Reconocimiento de entidades (IOCs)
# --------------------------------------------------------------------------
def _ip_valida(ip: str) -> bool:
    """IPv4 valida: 4 octetos 0-255 y sin ceros a la izquierda (rechaza '10.2.3.4'
    que en realidad es una version tipo '10.2.3.4'? No: esa ES una IPv4 valida.

    Lo que se rechaza es algo como '1.2.3.4.5' (ya cubierto por el patron) y los
    rangos fuera de 0-255. Ademas se exige que no haya octetos con ceros a la
    izquierda (evita confundir fechas/timestamps tipo '2026.10.1.0' parciales).
    """
    partes = ip.split(".")
    if len(partes) != 4:
        return False
    for parte in partes:
        if not parte.isdigit() or not (0 <= int(parte) <= 255):
            return False
        if len(parte) > 1 and parte[0] == "0":
            return False
    return True


def _es_versionish(ip: str) -> bool:
    """Heuristica: descarta cadenas que parecen versiones de software.

    Una version suele tener numeros pequenos (0-20) en los ultimos octetos y un
    primer octeto pequeno (<10). Ej: 1.2.3.4, 2.0.1.5. Se descarta solo si
    TODOS los octetos son <= 20 (poco probable en una IP real en uso).
    """
    try:
        partes = [int(p) for p in ip.split(".")]
    except ValueError:
        return False
    return all(p <= 20 for p in partes)


def _limpiar_ipv4(ips: list[str]) -> list[str]:
    return [ip for ip in ips if _ip_valida(ip) and not _es_versionish(ip)]


def extraer_iocs(texto: str) -> dict[str, list[str]]:
    """Extrae IOCs evitando solapamientos entre patrones.

    Un dominio que forma parte de una URL o de un correo NO se cuenta tambien
    como dominio suelto: el orden de extraccion garantiza exclusion mutua.
    """
    hallazgos: dict[str, list[str]] = {tipo: [] for tipo in PATRONES}
    restante = texto

    for tipo in ("url", "email", "ipv4", "md5", "sha1", "sha256", "cve", "dominio"):
        patron = PATRONES[tipo]
        encontrados = patron.findall(restante)
        if tipo == "ipv4":
            encontrados = _limpiar_ipv4(encontrados)
        hallazgos[tipo] = encontrados
        for valor in encontrados:
            restante = restante.replace(valor, " ")

    return hallazgos


def contar_iocs(texto: str) -> dict[str, int]:
    iocs = extraer_iocs(texto)
    return {
        "ipv4": len(iocs["ipv4"]),
        "dominio": len(iocs["dominio"]),
        "url": len(iocs["url"]),
        "hash": len(iocs["md5"]) + len(iocs["sha1"]) + len(iocs["sha256"]),
        "cve": len(iocs["cve"]),
        "email": len(iocs["email"]),
    }


# --------------------------------------------------------------------------
# 4. Generacion de lenguaje (resumen extractivo)
# --------------------------------------------------------------------------
def _idf_valores(vectorizer) -> dict[str, float]:
    return dict(zip(vectorizer.get_feature_names_out(), vectorizer.idf_))


def resumir(texto: str, idf: dict[str, float], n: int = PNL_RESUMEN_ORACIONES) -> str:
    oraciones = [o.strip() for o in _SENT_ORACION.split(texto) if len(o.strip()) > 30]
    if len(oraciones) <= n:
        return " ".join(oraciones)
    puntajes = []
    for oracion in oraciones:
        palabras = re.findall(r"[a-z]+", oracion.lower())
        score = sum(idf.get(p, 0.0) for p in palabras) / (len(palabras) + 1)
        puntajes.append(score)
    mejores = sorted(np.argsort(puntajes)[::-1][:n])
    return " ".join(oraciones[i] for i in mejores)


# --------------------------------------------------------------------------
# Figuras (opcionales)
# --------------------------------------------------------------------------
def _guardar_figuras(sentimiento_df: pd.DataFrame, terminos: pd.DataFrame) -> None:
    try:
        import plotly.express as px
    except Exception:
        LOG.warning("  plotly no disponible: se omiten las figuras")
        return
    asegurar_dir(FIGURES)
    px.bar(
        sentimiento_df, x="sentimiento", y="documentos", color="sentimiento",
        title="Documentos por sentimiento", text="documentos",
    ).write_html(FIGURES / "pnl_sentimiento.html", include_plotlyjs="cdn")
    px.bar(
        terminos.sort_values("relevancia"), x="relevancia", y="termino",
        orientation="h", title="Terminos mas relevantes (TF-IDF)",
    ).write_html(FIGURES / "pnl_top_terminos.html", include_plotlyjs="cdn")


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def analizar(reportes: pd.DataFrame | None = None) -> dict:
    if reportes is None:
        reportes = cargar_reportes()
    print(titulo("PNL - ANALISIS DE REPORTES DE AMENAZAS"))

    textos = reportes["text"].tolist()
    vectorizer, matriz = vectorizar(textos)
    terminos = top_terminos_global(matriz, vectorizer)
    idf = _idf_valores(vectorizer)
    analizador, motor = _analizador()

    sentimientos, etiquetas, resumenes, iocs_doc = [], [], [], []
    for i, texto in enumerate(textos):
        compuesto, etiqueta = sentimiento(texto, analizador)
        sentimientos.append(compuesto)
        etiquetas.append(etiqueta)
        resumenes.append(resumir(texto, idf))
        iocs_doc.append(contar_iocs(texto))

    entidades = pd.DataFrame(iocs_doc)
    entidades.insert(0, "id", reportes["id"].to_numpy())
    entidades["terminos_clave"] = [terminos_clave_doc(matriz, vectorizer, i) for i in range(len(textos))]

    enriquecido = pd.DataFrame(
        {
            "id": reportes["id"].to_numpy(),
            "title": reportes.get("title", pd.Series([""] * len(reportes))).to_numpy(),
            "n_chars": [len(t) for t in textos],
            "sentimiento_compound": sentimientos,
            "sentimiento": etiquetas,
            "n_iocs": entidades[["ipv4", "dominio", "url", "hash", "cve", "email"]].sum(axis=1),
            "resumen": resumenes,
            "terminos_clave": entidades["terminos_clave"],
        }
    )

    dist_sent = (
        enriquecido["sentimiento"].value_counts().rename_axis("sentimiento").reset_index(name="documentos")
    )
    dist_sent["porcentaje"] = (dist_sent["documentos"] / len(enriquecido) * 100).round(2)

    iocs_largos = []
    contadores: dict[str, Counter] = {}
    for tipo in ("url", "email", "ipv4", "md5", "sha1", "sha256", "cve", "dominio"):
        contador: Counter = Counter()
        for texto in textos:
            for valor in extraer_iocs(texto).get(tipo, []):
                contador[valor.lower()] += 1
        contadores[tipo] = contador
        for valor, freq in contador.most_common(10):
            iocs_largos.append({"tipo": tipo, "valor": valor, "frecuencia": freq})
    iocs_df = pd.DataFrame(iocs_largos)

    kpis = pd.DataFrame(
        [
            ("Documentos analizados", len(enriquecido), "reportes CTI"),
            ("Sentimiento promedio", round(float(enriquecido["sentimiento_compound"].mean()), 4), "VADER compound"),
            ("% negativo", f"{(enriquecido['sentimiento'] == 'negativo').mean() * 100:.1f}%", "tono de amenaza"),
            ("Total de IOCs", int(entidades[["ipv4", "dominio", "url", "hash", "cve", "email"]].to_numpy().sum()), "entidades detectadas"),
            ("CVE distintos", int(len(contadores["cve"])), "codigos de vulnerabilidad (todos)"),
            ("Dominios distintos", int(len(contadores["dominio"])), "dominios sueltos (todos)"),
            ("IPs distintas", int(len(contadores["ipv4"])), "direcciones IPv4 validas (todas)"),
            ("Terminos en el vocabulario", int(matriz.shape[1]), "TF-IDF (1-2 gramas)"),
            ("Motor de sentimiento", motor, "implementacion usada"),
        ],
        columns=["indicador", "valor", "nota"],
    )

    asegurar_dir(REPORTS)
    asegurar_dir(PROCESSED)
    enriquecido.to_parquet(PROCESSED / "reportes_enriquecidos.parquet", index=False)
    kpis.to_csv(REPORTS / "pnl_resumen.csv", index=False, encoding="utf-8-sig")
    dist_sent.to_csv(REPORTS / "pnl_sentimiento.csv", index=False, encoding="utf-8-sig")
    terminos.to_csv(REPORTS / "pnl_top_terminos.csv", index=False, encoding="utf-8-sig")
    iocs_df.to_csv(REPORTS / "pnl_iocs.csv", index=False, encoding="utf-8-sig")
    entidades.to_csv(REPORTS / "pnl_entidades.csv", index=False, encoding="utf-8-sig")

    _guardar_figuras(dist_sent, terminos)
    _escribir_reporte(kpis, dist_sent, terminos, iocs_df, enriquecido)

    LOG.info("  documentos=%s  vocabulario=%s  IOCs=%s", len(enriquecido), matriz.shape[1], int(entidades[["ipv4", "dominio", "url", "hash", "cve", "email"]].to_numpy().sum()))
    LOG.info("  sentimiento: %s", ", ".join(f"{r.sentimiento}={r.documentos}" for r in dist_sent.itertuples()))
    LOG.info("[ok] PNL guardado en %s", REPORTS)
    return {
        "enriquecido": enriquecido,
        "kpis": kpis,
        "sentimiento": dist_sent,
        "terminos": terminos,
        "iocs": iocs_df,
    }


def _escribir_reporte(kpis, dist_sent, terminos, iocs_df, enriquecido) -> str:
    """Generacion de lenguaje: reporte narrativo a partir de los resultados."""
    lineas = [
        "# Reporte generado de analisis de amenazas",
        "",
        "Generado automaticamente por `src/pnl.py` (componente de PNL).",
        "",
        "## Indicadores",
        "",
        "| Indicador | Valor | Nota |",
        "|---|---|---|",
    ]
    lineas += [f"| {r.indicador} | {r.valor} | {r.nota} |" for r in kpis.itertuples()]
    lineas += ["", "## Distribucion de sentimiento", "", "| Sentimiento | Documentos | % |", "|---|---|---|"]
    lineas += [f"| {r.sentimiento} | {r.documentos} | {r.porcentaje}% |" for r in dist_sent.itertuples()]
    lineas += ["", "## Terminos mas relevantes (TF-IDF)", ""]
    lineas += [f"- {r.termino} ({r.relevancia})" for r in terminos.head(10).itertuples()]
    lineas += ["", "## Entidades mas frecuentes", "", "| Tipo | Valor | Frecuencia |", "|---|---|---|"]
    lineas += [f"| {r.tipo} | {r.valor} | {r.frecuencia} |" for r in iocs_df.head(15).itertuples()]
    lineas += ["", "## Ejemplos de resumenes generados", ""]
    for r in enriquecido.head(3).itertuples():
        lineas += [f"- **Doc {r.id}** ({r.sentimiento}): {r.resumen}"]
    texto = "\n".join(lineas)
    (REPORTS / "pnl_reporte.md").write_text(texto, encoding="utf-8")
    return texto


def main() -> int:
    resultado = analizar()
    print(subtitulo("Indicadores de PNL"))
    print(tabla(resultado["kpis"]))
    print(subtitulo("Sentimiento"))
    print(tabla(resultado["sentimiento"]))
    print(subtitulo("Terminos mas relevantes"))
    print(tabla(resultado["terminos"].head(10)))
    print(subtitulo("Entidades (IOCs) mas frecuentes"))
    print(tabla(resultado["iocs"].head(10)))
    LOG.info("[ok] reporte generado en %s", REPORTS / "pnl_reporte.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
