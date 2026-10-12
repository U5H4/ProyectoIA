"""Pruebas del componente de PNL: entidades, sentimiento, representacion y resumen."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pnl  # noqa: E402

TEXTO = (
    "The malware exploited CVE-2021-44228 from 124.248.207.50 and contacted "
    "evil.example.com over https://evil.example.com/payload.exe. "
    "The MD5 hash is d41d8cd98f00b204e9800998ecf8427e. "
    "Contact analyst@corp.com to report the breach."
)


def test_extraer_iocs_detecta_tipos():
    iocs = pnl.extraer_iocs(TEXTO)
    assert "124.248.207.50" in iocs["ipv4"]
    assert any("evil.example.com" in d for d in iocs["dominio"])
    assert any("https://evil.example.com" in u for u in iocs["url"])
    assert "CVE-2021-44228" in iocs["cve"]
    assert "d41d8cd98f00b204e9800998ecf8427e" in iocs["md5"]
    assert "analyst@corp.com" in iocs["email"]


def test_ip_invalida_se_descarta():
    assert pnl._ip_valida("124.248.207.50") is True
    assert pnl._ip_valida("999.1.1.1") is False
    iocs = pnl.extraer_iocs("host 999.1.1.1 no es valida")
    assert iocs["ipv4"] == []


def test_contar_iocs_suma_hash_y_tipos():
    conteo = pnl.contar_iocs(TEXTO)
    assert conteo["ipv4"] == 1
    assert conteo["hash"] >= 1
    assert conteo["cve"] == 1


def test_sentimiento_devuelve_etiqueta_valida():
    compuesto, etiqueta = pnl.sentimiento("critical malware breach vulnerability")
    assert etiqueta in {"positivo", "negativo", "neutro"}
    assert -1.0 <= compuesto <= 1.0


def test_sentimiento_seguro_es_positivo_con_respaldo():
    _, etiqueta = pnl.sentimiento("secure patched resolved verified", analizador=None)
    assert etiqueta == "positivo"


def test_resumir_genera_texto_no_vacio():
    idf = {"malware": 3.0, "attacked": 2.0, "server": 1.0, "report": 0.5}
    texto = (
        "The server was attacked by malware. "
        "Analysts wrote a long report about the incident yesterday afternoon. "
        "The malware encrypted several files across the network."
    )
    resumen = pnl.resumir(texto, idf, n=1)
    assert isinstance(resumen, str) and len(resumen) > 0


def test_top_terminos_global_ordenado():
    corpus = ["malware attack", "malware network", "attack network"]
    vectorizer, matriz = pnl.vectorizar(corpus)
    terminos = pnl.top_terminos_global(matriz, vectorizer, n=3)
    assert len(terminos) == 3
    assert terminos["relevancia"].is_monotonic_decreasing


def test_terminos_clave_doc_devuelve_string():
    corpus = ["malware malware attack", "network security malware"]
    vectorizer, matriz = pnl.vectorizar(corpus)
    clave = pnl.terminos_clave_doc(matriz, vectorizer, 0)
    assert isinstance(clave, str) and "malware" in clave
