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
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

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
_COLA_TOC = re.compile(r"\.{4,}")
# Encabezados de seccion / lineas de sumario que NO son oraciones utiles.
# fullmatch sobre la linea completa para no descartar oraciones reales.
_SECCION_TOC = re.compile(
    r"\s*(executive\s+summary|table\s+of\s+contents|table\s+of\s+figures|contents|"
    r"index|references|bibliography|appendix|acknowledg(e)?ments|about\s+this\s+report)\s*:?\s*(\d{1,3}|page\s*\d{1,3})?\s*$",
    re.IGNORECASE,
)
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
_ENLACE_O_CODIGO = re.compile(
    r"https?://\S+|www\.\S+|\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b|"
    r"\bCVE-\d{4}-\d{4,7}\b|\S+@\S+|\b(?:\d{1,3}\.){3}\d{1,3}\b",
    re.IGNORECASE,
)
_STOPWORDS_DOMINIO = {
    "com", "www", "http", "https", "exe", "figure", "fig", "www", "ftp",
    "report", "research", "analysis", "pdf",
}


def _preprocesar_tfidf(texto: str) -> str:
    """Reduce el ruido de URLs/hashes/CVEs/correos/IPs embebidos en los CTI,
    para que el vocabulario refleje tecnicas y hallazgos, no enlaces."""
    limpio = _desdefanguear(texto)
    limpio = _ENLACE_O_CODIGO.sub(" ", limpio)
    return limpio


def vectorizar(textos: list[str]) -> tuple[TfidfVectorizer, object]:
    saneados = [_preprocesar_tfidf(t) for t in textos]
    vectorizer = TfidfVectorizer(
        stop_words=sorted(set(ENGLISH_STOP_WORDS) | _STOPWORDS_DOMINIO),
        ngram_range=(1, 2),
        min_df=2,
        max_features=4000,
        sublinear_tf=True,
    )
    matriz = vectorizer.fit_transform(saneados)
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
    """IPv4 sintacticamente valida: 4 octetos 0-255, sin ceros a la izquierda.

    No decide por si sola si es un IOC: 10.2.3.4 ES una IPv4 valida. La
    decision de IOC vs version se toma con el contexto (_es_version_contexto).
    Ademas se rechazan direcciones reservadas (_ip_reservada).
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


def _ip_reservada(ip: str) -> bool:
    """Direcciones que no son IOC globales (loopback, enlace local, multicast,
    reservado). Las RFC1918 (10/8, 172.16/12, 192.168/16) SI se conservan: son
    validas y habituales en reportes de incidentes internos."""
    try:
        a, b, c, d = (int(p) for p in ip.split("."))
    except ValueError:
        return True
    if a == 0 or a == 127:
        return True                      # 0.0.0.0/8 y 127.0.0.0/8
    if a == 169 and b == 254:
        return True                      # enlace local
    if a >= 224:
        return True                      # multicast y 240.0.0.0/4
    return False


_CONTEXTO_VERSION = re.compile(
    r"version|release|build|update|\bdot\b|\.js\b|\bv\b|v\d",
    re.IGNORECASE,
)


def _ventana_contexto(texto: str, inicio: int, fin: int, chars: int = 12) -> str:
    """Ventana de ~`chars` caracteres antes y despues del match (sin incluirlo)."""
    return texto[max(0, inicio - chars) : inicio] + " " + texto[fin : fin + chars]


def _es_version_contexto(texto: str, inicio: int, fin: int) -> bool:
    """True si la IPv4 esta pegada a tokens de contexto de version de software
    (version|v|release|build|update|dot|.js o v<digito>) en una ventana de
    ~12 chars antes/despues. Es el UNICO criterio para descartar una IPv4
    por 'parecer version'; 8.8.8.8 y cualquier IPv4 publica se conservan."""
    return bool(_CONTEXTO_VERSION.search(_ventana_contexto(texto, inicio, fin, 12)))


def _es_versionish(ip: str, contexto: str = "") -> bool:
    """Compatibilidad con llamadas aisladas.

    Una IPv4 por si sola NUNCA se descarta como version (los octetos pequenos
    son comunes en IPs reales, p. ej. 8.8.8.8 o 1.1.1.1). Solo se descarta
    cuando `contexto` contiene tokens de version; ver _es_version_contexto.
    """
    if not contexto:
        return False
    return bool(_CONTEXTO_VERSION.search(contexto))


def _limpiar_ipv4(ips: list[str]) -> list[str]:
    return [ip for ip in ips if _ip_valida(ip) and not _ip_reservada(ip)]


def _desdefanguear(texto: str) -> str:
    """Normaliza IOCs con defang para que coincidan.

    hxxp/hXXp -> http, hxxps -> https, [.]/(.)/{.}/[ . ]/[dot] -> '.',
    [at]/(at)/(@) -> '@', [colon] -> ':' (los corchetes toleran espacios
    internos por reflujo de PDF, p. ej. 'github[. ]com'; un '[.' colgante
    seguido de alfanumerico, p. ej. 'kentona[.su', tambien se normaliza).
    Se aplica SOLO a la copia en memoria usada para extraccion y
    vectorizacion; el texto persistido en reportes_enriquecidos (y cualquier
    salida) conserva el original intacto.
    """
    t = re.sub(r"hxxps", "https", texto, flags=re.IGNORECASE)
    t = re.sub(r"hxxp", "http", t, flags=re.IGNORECASE)
    t = re.sub(r"\[\s*\.\s*\]|\(\s*\.\s*\)|\{\s*\.\s*\}|\[\s*(?:dot|dott)\s*\]|\(\s*(?:dot|dott)\s*\)", ".", t, flags=re.IGNORECASE)
    # Defang incompleto del corpus: '[.' seguido directamente de alfanumerico ('kentona[.su').
    t = re.sub(r"\[\.(?=[A-Za-z0-9])", ".", t)
    t = re.sub(r"\[\s*(?:at|att)\s*\]|\(\s*(?:at|att)\s*\)|\(@\)|\[@\]", "@", t, flags=re.IGNORECASE)
    t = re.sub(r"\[\s*(?:colon|co)\s*\]", ":", t, flags=re.IGNORECASE)
    return t


def extraer_iocs(texto: str) -> dict[str, list[str]]:
    """Extrae IOCs evitando solapamientos entre patrones.

    Trabaja sobre una copia desdefangueada en memoria (hxxp->http, [.]->.,
    [at]->@...); el texto original nunca se modifica ni se persiste alterado.
    Los rangos ya ocupados por extracciones previas (url/email antes que el
    resto) se excluyen mutuamente: un dominio dentro de una URL o un correo NO
    se cuenta tambien como dominio suelto. Las IPv4 se descartan si son
    sintacticamente invalidas, reservadas (0/8, 127/8, 169.254/16, 224/4,
    240/4) o si el contexto cercano (~12 chars) indica que son una version de
    software (_es_version_contexto). RFC1918 (10/8, 172.16/12, 192.168/16) y
    cualquier IP publica (p. ej. 8.8.8.8) se conservan.
    """
    hallazgos: dict[str, list[str]] = {tipo: [] for tipo in PATRONES}
    trabajo = _desdefanguear(texto)
    ocupado: list[tuple[int, int]] = []

    for tipo in ("url", "email", "ipv4", "md5", "sha1", "sha256", "cve", "dominio"):
        patron = PATRONES[tipo]
        encontrados: list[str] = []
        for m in patron.finditer(trabajo):
            ini, fin = m.span()
            if any(not (fin <= a or ini >= b) for a, b in ocupado):
                continue
            valor = m.group()
            if tipo == "ipv4":
                if not _ip_valida(valor) or _ip_reservada(valor):
                    continue
                if _es_version_contexto(trabajo, ini, fin):
                    continue
            encontrados.append(valor)
            ocupado.append((ini, fin))
        hallazgos[tipo] = encontrados

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
    def _oracion_util(oracion: str) -> bool:
        palabras = re.findall(r"\w+", oracion)
        if len(palabras) < 8:
            return False
        alfabeticas = sum(1 for c in oracion if c.isalpha())
        return alfabeticas >= 0.6 * max(1, len(oracion))

    oraciones = []
    for cruda in _SENT_ORACION.split(texto):
        oracion = cruda.strip()
        if not oracion or _COLA_TOC.search(oracion) or _SECCION_TOC.match(oracion):
            continue
        if _oracion_util(oracion):
            oraciones.append(oracion)
    if not oraciones:
        # fallback: primera oracion razonable (sin TOC ni cabeceras repetidas)
        for cruda in _SENT_ORACION.split(texto):
            oracion = cruda.strip()
            if (
                oracion
                and not _COLA_TOC.search(oracion)
                and not _SECCION_TOC.match(oracion)
                and len(re.findall(r"[A-Za-z0-9]+", oracion)) >= 4
            ):
                return oracion
        compacto = texto.strip()
        return compacto[:300] if compacto else ""
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
        color_discrete_map={"negativo": "#d32f2f", "positivo": "#2e7d32", "neutro": "#607d8b"},
        title="Documentos por sentimiento (VADER — proxy léxico, truncado 4.000 chars)",
        text="documentos", labels={"documentos": "N.º documentos", "sentimiento": "Sentimiento"},
    ).update_layout(
        title_x=0.5, font=dict(size=13),
        margin=dict(l=70, r=30, t=70, b=60),
    ).update_traces(textposition="outside", showlegend=False).update_yaxes(rangemode="tozero", range=[0, 630]).write_html(
        FIGURES / "pnl_sentimiento.html", include_plotlyjs="directory"
    )
    px.bar(
        terminos.sort_values("relevancia"), x="relevancia", y="termino",
        orientation="h", color_discrete_sequence=["#00838f"],
        labels={"relevancia": "Relevancia TF-IDF (sumatoria)", "termino": "Término"},
        title="Términos más relevantes (TF-IDF)",
    ).update_layout(
        title_x=0.5, font=dict(size=13),
        margin=dict(l=110, r=30, t=70, b=60),
        annotations=[
            dict(
                x=0.99, y=-0.22, xref="paper", yref="paper", showarrow=False,
                text="ngramas (1-2) · 4.000 términos tope · stopwords personalizadas (com, www, http, exe, figure)",
                align="right", font=dict(size=11, color="#37474f"),
            ),
        ],
    ).write_html(
        FIGURES / "pnl_top_terminos.html", include_plotlyjs="directory"
    )


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

    hashes = Counter()
    for tipo in ("md5", "sha1", "sha256"):
        for valor, freq in contadores[tipo].items():
            hashes[valor.lower()] += freq

    iocs_distintos_total = int(sum(len(c) for c in contadores.values()))
    documentos_con_iocs = int((enriquecido["n_iocs"] > 0).sum())
    pct_docs_iocs = documentos_con_iocs / len(enriquecido) * 100 if len(enriquecido) else 0.0
    duplicados_exactos = int(pd.Series(textos).duplicated().sum())
    columnas_iocs = ["ipv4", "dominio", "url", "hash", "cve", "email"]
    total_ocurrencias = int(entidades[columnas_iocs].to_numpy().sum())
    kpis = pd.DataFrame(
        [
            ("Documentos analizados", len(enriquecido), "reportes CTI"),
            ("Documentos con >=1 IOC (%)", f"{pct_docs_iocs:.1f}%", f"{documentos_con_iocs} de {len(enriquecido)} documentos"),
            ("Documentos con texto duplicado exacto", duplicados_exactos, "deduplicados por la ETL antes de PNL (T04)"),
            ("Sentimiento promedio", round(float(enriquecido["sentimiento_compound"].mean()), 4), "VADER compound (truncado a 4k chars)"),
            ("% negativo", f"{(enriquecido['sentimiento'] == 'negativo').mean() * 100:.1f}%", "proxy lexico, no calibrado"),
            ("Total de IOCs", total_ocurrencias, "OCURRENCIAS (menciones), no valores distintos"),
            ("IOCs distintos (total)", iocs_distintos_total, "valores distintos sumados por tipo"),
            ("CVE distintos", int(len(contadores["cve"])), f"ocurrencias: {sum(contadores['cve'].values())}"),
            ("Dominios distintos", int(len(contadores["dominio"])), f"ocurrencias: {sum(contadores['dominio'].values())}"),
            ("IPs distintas", int(len(contadores["ipv4"])), f"ocurrencias: {sum(contadores['ipv4'].values())} (v4 publicas/privadas, sin reservadas)"),
            ("URLs distintas", int(len(contadores["url"])), f"ocurrencias: {sum(contadores['url'].values())}"),
            ("Hashes distintos", int(len(hashes)), f"ocurrencias: {sum(hashes.values())} (md5+sha1+sha256)"),
            ("Emails distintos", int(len(contadores["email"])), f"ocurrencias: {sum(contadores['email'].values())}"),
            ("Terminos en el vocabulario", int(matriz.shape[1]), "TF-IDF (1-2 gramas, tope 4000)"),
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

    LOG.info("  documentos=%s  vocabulario=%s  IOCs=%s", len(enriquecido), matriz.shape[1], total_ocurrencias)
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
    lineas += [
        "",
        "> Nota: «Total de IOCs» son OCURRENCIAS (menciones repetidas por tipo);",
        "> la columna «X distintos» reporta valores diferentes. El corpus ya viene deduplicado por la ETL (T04).",
    ]
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
