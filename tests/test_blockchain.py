"""Pruebas del componente Blockchain: encadenado, verificacion y alteracion."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import blockchain as bc  # noqa: E402


def _cadena() -> bc.Cadena:
    cadena = bc.Cadena()
    cadena.agregar({"tipo": "genesis"}, timestamp="2026-01-01T00:00:00+00:00")
    cadena.agregar({"tipo": "modelo", "archivo": "modelo.joblib", "sha256": "a" * 64}, timestamp="2026-01-01T00:00:01+00:00")
    cadena.agregar({"tipo": "metricas", "archivo": "metricas.csv", "sha256": "b" * 64}, timestamp="2026-01-01T00:00:02+00:00")
    return cadena


def test_cadena_valida():
    ok, errores = _cadena().es_valida()
    assert ok is True
    assert errores == []


def test_hash_encadena_bloques():
    cadena = _cadena()
    assert cadena.bloques[1].hash_previo == cadena.bloques[0].hash
    assert cadena.bloques[2].hash_previo == cadena.bloques[1].hash


def test_alteracion_de_datos_se_detecta():
    cadena = _cadena()
    cadena.bloques[1].datos["sha256"] = "c" * 64
    ok, errores = cadena.es_valida()
    assert ok is False
    assert any("Bloque 1" in e for e in errores)


def test_hash_determinista():
    datos = {"tipo": "x", "sha256": "a" * 64}
    b1 = bc.Bloque(1, "2026-01-01T00:00:00+00:00", datos, "0" * 64)
    b2 = bc.Bloque(1, "2026-01-01T00:00:00+00:00", dict(datos), "0" * 64)
    assert b1.calcular_hash() == b2.calcular_hash()
    assert len(b1.calcular_hash()) == 64


def test_guardar_y_cargar(tmp_path):
    cadena = _cadena()
    ruta = tmp_path / "cadena.json"
    cadena.guardar(ruta)
    recargada = bc.Cadena.cargar(ruta)
    assert len(recargada.bloques) == 3
    assert recargada.es_valida()[0] is True


def test_hash_archivo(tmp_path):
    archivo = tmp_path / "dato.txt"
    archivo.write_bytes(b"incidente-2026")
    h1 = bc.hash_archivo(archivo)
    h2 = bc.hash_archivo(archivo)
    assert h1 == h2 and len(h1) == 64
    archivo.write_bytes(b"incidente-2026-alterado")
    assert bc.hash_archivo(archivo) != h1


def test_prueba_alteracion_reporta_detectado():
    cadena = _cadena()
    evidencia = bc.prueba_alteracion(cadena)
    assert not evidencia.empty
    assert bool(evidencia.iloc[0]["detectado"]) is True


def test_verificacion_offline_detecta_artefacto_modificado(tmp_path, monkeypatch, capsys):
    """End-to-end: construye cadena.json desde archivos reales y comprueba que
    --solo-verificar (offline) detecta 1 byte alterado y devuelve != 0."""
    artefacto_a = tmp_path / "artefacto_a.txt"
    artefacto_b = tmp_path / "artefacto_b.txt"
    artefacto_a.write_bytes(b"contenido-original-A")
    artefacto_b.write_bytes(b"contenido-original-B")
    artefactos = [("artefacto_a", artefacto_a), ("artefacto_b", artefacto_b)]
    monkeypatch.setattr(bc, "artefactos_a_registrar", lambda: artefactos)

    cadena = bc.Cadena()
    cadena.agregar(
        {"tipo": "genesis", "descripcion": "genesis de prueba"},
        timestamp="2026-01-01T00:00:00+00:00",
    )
    for i, (tipo, ruta) in enumerate(artefactos, start=1):
        cadena.agregar(
            {
                "tipo": tipo,
                "archivo": ruta.name,
                "sha256": bc.hash_archivo(ruta),
                "bytes": ruta.stat().st_size,
            },
            timestamp=f"2026-01-01T00:00:0{i}+00:00",
        )
    ruta_json = tmp_path / "cadena.json"
    cadena.guardar(ruta_json)

    # 1) Estado integro: offline OK y codigo 0.
    res = bc.verificar_offline(ruta_json, artefactos=artefactos)
    assert res["ok"] is True
    assert res["integridad"]["estado"].tolist() == ["OK", "OK"]

    # 2) Se altera 1 byte de un artefacto: offline debe detectar MODIFICADO y != 0.
    datos = artefacto_a.read_bytes()
    artefacto_a.write_bytes(bytes([datos[0] ^ 0x01]) + datos[1:])

    res2 = bc.verificar_offline(ruta_json, artefactos=artefactos)
    assert res2["ok"] is False
    estados = dict(zip(res2["integridad"]["archivo"], res2["integridad"]["estado"]))
    assert estados["artefacto_a.txt"] == "MODIFICADO"
    assert estados["artefacto_b.txt"] == "OK"

    monkeypatch.setattr(bc, "BLOCKCHAIN_JSON", ruta_json)
    assert bc.main(["--solo-verificar"]) != 0
    salida = capsys.readouterr().out
    assert "MODIFICADO" in salida

    # 3) Artefacto ausente en disco: FALTANTE y != 0.
    artefacto_b.unlink()
    res3 = bc.verificar_offline(ruta_json, artefactos=artefactos)
    estados3 = dict(zip(res3["integridad"]["archivo"], res3["integridad"]["estado"]))
    assert estados3["artefacto_b.txt"] == "FALTANTE"
    assert res3["ok"] is False
    assert bc.main(["--solo-verificar"]) != 0
