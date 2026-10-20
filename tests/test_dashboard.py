"""Prueba de humo del dashboard (Streamlit AppTest): carga sin excepciones."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

DASHBOARD = Path(__file__).resolve().parents[1] / "src" / "dashboard.py"


def test_dashboard_carga_sin_excepciones():
    app = AppTest.from_file(str(DASHBOARD), default_timeout=60)
    app.run()
    assert not app.exception, f"El dashboard lanzó excepciones: {app.exception}"
    assert len(app.tabs) == 5
