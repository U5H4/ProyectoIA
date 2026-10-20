"""Pruebas del modulo de integracion ML+PNL (reporte con nivel de riesgo)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import integrar  # noqa: E402


def test_nivel_riesgo_alto_con_dos_senales():
    nivel, motivos = integrar._nivel_riesgo(0.95, 0.50)
    assert nivel == "ALTO"
    assert len(motivos) == 2


def test_nivel_riesgo_medio_con_una_senal():
    nivel, _ = integrar._nivel_riesgo(0.95, 0.10)
    assert nivel == "MEDIO"
    nivel2, _ = integrar._nivel_riesgo(0.50, 0.50)
    assert nivel2 == "MEDIO"


def test_nivel_riesgo_bajo_sin_senales():
    nivel, _ = integrar._nivel_riesgo(0.40, 0.05)
    assert nivel == "BAJO"


def test_nivel_riesgo_sin_datos():
    nivel, motivos = integrar._nivel_riesgo(None, None)
    assert nivel == "BAJO"
    assert motivos == []
