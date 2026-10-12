"""Pruebas de la seleccion de etapas del orquestador (sin ejecutar el pipeline)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import run_all  # noqa: E402


@pytest.fixture
def capturar(monkeypatch):
    capturado = {}

    def fake_ejecutar(claves):
        capturado["claves"] = list(claves)
        return 0

    monkeypatch.setattr(run_all, "ejecutar", fake_ejecutar)
    return capturado


def test_default_ejecuta_etapas_obligatorias(capturar):
    run_all.main([])
    assert capturar["claves"] == ["descargar", "etl", "ml", "pnl", "blockchain"]


def test_sin_descargar(capturar):
    run_all.main(["--sin-descargar"])
    assert capturar["claves"] == ["etl", "ml", "pnl", "blockchain"]


def test_con_tests_anade_al_final(capturar):
    run_all.main(["--con-tests"])
    assert capturar["claves"] == ["descargar", "etl", "ml", "pnl", "blockchain", "tests"]


def test_solo_respeta_orden_del_pipeline(capturar):
    run_all.main(["--solo", "etl", "descargar"])
    assert capturar["claves"] == ["descargar", "etl"]


def test_etapa_desconocida_devuelve_2():
    assert run_all.main(["--solo", "inexistente"]) == 2


def test_tests_es_opcional(capturar):
    run_all.main([])
    assert "tests" not in capturar["claves"]
