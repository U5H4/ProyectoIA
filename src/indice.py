"""INDICE DE VISUALIZACIONES (HTML) -> data/reports/indice.html

Reimplementacion propia del patron Proyecto_BigData/src/viz.py:
- una sola pagina con las figuras Plotly incrustadas inline
- sin CDN, sin iframes, sin enlaces ni "recursos" extra: solo las visualizaciones
- comparte una unica copia de plotly.min.js (include_plotlyjs="directory")

Uso:
    python src/indice.py
"""

from __future__ import annotations

from datetime import datetime

from config import FIGURES, REPORTS
from utils import LOG, asegurar_dir, titulo

# (nombre de archivo sin extension, titulo)
FIGURAS = [
    ("comparacion_modelos", "Comparación de modelos (F1-macro)"),
    ("matriz_confusion", "Matriz de confusión (5.945 flujos de test)"),
    ("pnl_top_terminos", "Términos más relevantes (TF-IDF)"),
    ("pnl_sentimiento", "Documentos por sentimiento (VADER)"),
]


def _kb(ruta) -> float:
    return round(ruta.stat().st_size / 1024, 1) if ruta.exists() else 0.0


def _cuerpo_figura_html(ruta) -> str:
    """Extrae el interior de <body> de una figura ya exportada y lo deja listo
    para incrustar inline. Quita su <script src='plotly.min.js'> (lo cargamos
    una sola vez en el <head> de esta pagina)."""
    import re

    texto = ruta.read_text(encoding="utf-8")
    m = re.search(r"<body>(.*)</body>", texto, re.DOTALL | re.IGNORECASE)
    if not m:
        return "<p><em>No se pudo incrustar la figura.</em></p>"
    cuerpo = m.group(1)
    cuerpo = re.sub(r'<script[^>]*src=["\']plotly\.min\.js["\'][^>]*></script>', "", cuerpo, flags=re.IGNORECASE)
    return cuerpo


def generar_indice(figuras=None, reporte=None) -> str:
    asegurar_dir(REPORTS)
    asegurar_dir(FIGURES)
    figuras = figuras or FIGURAS
    reporte = reporte or (REPORTS / "indice.html")

    ordenadas = [(i + 1, n, t) for i, (n, t) in enumerate(figuras)]
    for numero, nombre, titulo_figura in ordenadas:
        ruta = FIGURES / f"{nombre}.html"
        if not ruta.exists():
            LOG.warning("  falta la figura %s", ruta)

    navs = "\n".join(
        f'    <li><a href="#{nombre}">{titulo_figura}</a></li>'
        for numero, nombre, titulo_figura in ordenadas
    )

    secciones = []
    for numero, nombre, titulo_figura in ordenadas:
        ruta = FIGURES / f"{nombre}.html"
        cuerpo = _cuerpo_figura_html(ruta) if ruta.exists() else "<p><em>Figura no generada.</em></p>"
        secciones.append(
            f'<section class="figura" id="{nombre}">\n'
            f'  <h2>{numero}. {titulo_figura}</h2>\n'
            f'  <div class="plot">{cuerpo}</div>\n'
            f'</section>'
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proyecto IA — Visualizaciones</title>
  <script charset="utf-8" src="../figures/plotly.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ margin:0; background:#ffffff; color:#212121; font-family:"Segoe UI", SegoeUI, system-ui, sans-serif; }}
    header {{ background:#263238; color:#eceff1; padding:22px 40px; border-bottom:4px solid #00838f; }}
    header h1 {{ margin:0; font-size:24px; font-weight:500; }}
    nav {{ background:#eceff1; padding:14px 40px; }}
    nav ol {{ margin:0; padding-left:1.2rem; }}
    nav a {{ color:#006064; text-decoration:none; }}
    nav a:hover {{ text-decoration:underline; }}
    main {{ max-width:1100px; margin:auto; padding:24px; }}
    .figura {{ margin-bottom:28px; }}
    .figura h2 {{ margin:0 0 6px; color:#263238; font-size:18px; border-bottom:1px solid #cfd8dc; padding-bottom:6px; }}
    .plot {{ height:480px; width:100%; }}
  </style>
</head>
<body>
  <header><h1>Sistema Inteligente de Incidentes de Ciberseguridad — Visualizaciones</h1></header>
  <nav><ol>
{navs}
  </ol></nav>
  <main>
{''.join(secciones)}
  </main>
</body>
</html>"""
    reporte.write_text(html, encoding="utf-8")
    print(titulo("INDICE DE VISUALIZACIONES"))
    print(f"  -> {reporte} ({len(figuras)} figuras)")
    LOG.info("[ok] indice inline en %s", reporte)
    return str(reporte)


def main() -> int:
    generar_indice()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
