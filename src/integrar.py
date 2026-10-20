"""REPORTE INTEGRADO (ML + PNL) con nivel de riesgo global.

El enunciado pide un sistema que integre las dos ramas de analisis (flujos de
red via ML y reportes CTI via PNL) y produzca un resultado unico trazable. Este
modulo combina ambos resultados en un solo reporte con un NIVEL DE RIESGO
GLOBAL (bajo / medio / alto) y lo deja como artefacto hasheable por Blockchain.

Artefactos:
    data/reports/reporte_integrado.md
    data/reports/reporte_integrado.json

Uso:
    python src/integrar.py
"""

from __future__ import annotations

import json

from config import PROCESSED, REPORTS
from utils import LOG, asegurar_dir, titulo

REPORTE_ML = REPORTS / "ml_resumen.json"
REPORTE_PNL = REPORTES_PNL = REPORTS / "pnl_resumen.csv"
REPORTE_OUT = REPORTS / "reporte_integrado.md"
REPORTE_JSON = REPORTS / "reporte_integrado.json"

# Umbrales de riesgo (documentados y ajustables).
UMBRAL_ALTO_F1 = 0.85
UMBRAL_ALTO_NEG = 0.30


def _leer_json(ruta):
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def _leer_csv(ruta):
    import pandas as pd

    return pd.read_csv(ruta) if ruta.exists() else None


def _nivel_riesgo(f1_macro: float | None, pct_negativo: float | None) -> tuple[str, list[str]]:
    """Calcula un nivel de riesgo global a partir de las senales disponibles.

    - Si el clasificador es fiable (F1 alto) y el corpus CTI es mayoritariamente
      negativo, el entorno se considera de riesgo ALTO.
    - Si solo una de las dos senales es fuerte, MEDIO.
    - Si ninguna, BAJO.
    """
    motivos = []
    señal_fuerte = 0
    if f1_macro is not None:
        motivos.append(f"F1-macro del clasificador = {f1_macro:.4f}")
        if f1_macro >= UMBRAL_ALTO_F1:
            señal_fuerte += 1
    if pct_negativo is not None:
        motivos.append(f"documentos CTI negativos = {pct_negativo:.1%}")
        if pct_negativo >= UMBRAL_ALTO_NEG:
            señal_fuerte += 1
    nivel = {0: "BAJO", 1: "MEDIO", 2: "ALTO"}[señal_fuerte]
    return nivel, motivos


def integrar() -> dict:
    print(titulo("REPORTE INTEGRADO (ML + PNL)"))
    ml = _leer_json(REPORTE_ML)
    pnl = _leer_csv(REPORTE_PNL)

    f1 = float(ml["f1_macro"]) if ml else None
    acc = float(ml["accuracy"]) if ml else None
    modelo = ml.get("modelo_mejor") if ml else None

    docs = total_iocs = pct_neg = None
    if pnl is not None and not pnl.empty:
        kpis = dict(zip(pnl["indicador"], pnl["valor"]))
        docs = kpis.get("Documentos analizados")
        total_iocs = kpis.get("Total de IOCs")
        pct_neg = kpis.get("% negativo")
        try:
            pct_neg = float(str(pct_neg).rstrip("%")) / 100.0
        except (TypeError, ValueError):
            pct_neg = None

    nivel, motivos = _nivel_riesgo(f1, pct_neg)

    lineas = [
        "# Reporte integrado del sistema (ML + PNL)",
        "",
        "Generado automaticamente por `src/integrar.py`. Combina la clasificacion",
        "de flujos de red (Machine Learning) con el analisis de reportes de",
        "amenazas (PNL) en un unico resultado trazable.",
        "",
        f"## Nivel de riesgo global: **{nivel}**",
        "",
        "Criterios aplicados:",
    ]
    lineas += [f"- {m}" for m in motivos]
    lineas += [
        "",
        "## Rama de Machine Learning",
        "",
        f"- Modelo ganador: **{modelo}**",
        f"- Accuracy: {acc:.4f}" if acc is not None else "- Accuracy: N/D",
        f"- F1-macro: {f1:.4f}" if f1 is not None else "- F1-macro: N/D",
        "",
        "## Rama de PNL",
        "",
        f"- Documentos analizados: {docs}",
        f"- Total de IOCs detectados: {total_iocs}",
        f"- Porcentaje de documentos negativos: {pct_neg:.1%}" if pct_neg is not None else "- Porcentaje negativos: N/D",
        "",
        "## Interpretacion",
        "",
        "El nivel de riesgo resume, en una sola etiqueta, la fiabilidad del",
        "detector de intrusiones (que tan bien distingue trafico benigno de",
        "ataques) y el tono del corpus de inteligencia (que tan amenazante es el",
        "contexto reportado). Este artefacto es el que se registra en la",
        "Blockchain como resultado integrado del sistema.",
        "",
    ]
    asegurar_dir(REPORTS)
    texto = "\n".join(lineas)
    REPORTE_OUT.write_text(texto, encoding="utf-8")

    resumen = {
        "nivel_riesgo": nivel,
        "motivos": motivos,
        "modelo_ml": modelo,
        "accuracy": acc,
        "f1_macro": f1,
        "documentos_cti": docs,
        "total_iocs": total_iocs,
        "pct_negativo": pct_neg,
    }
    REPORTE_JSON.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG.info("  nivel de riesgo global: %s", nivel)
    LOG.info("[ok] reporte integrado en %s", REPORTE_OUT)
    return resumen


def main() -> int:
    integrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
