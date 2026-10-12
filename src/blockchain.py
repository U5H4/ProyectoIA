"""ENTREGABLE 5 - Componente Blockchain.

Blockchain propia (no una criptomoneda ni una red comercial) que registra la
huella criptografica (SHA-256) de los resultados relevantes del sistema y
permite verificar despues si fueron alterados.

Que se registra y por que:
    Se registra el SHA-256 de los artefactos que resumen el analisis
    (dataset procesado, reportes enriquecidos, modelo de ML, metricas y
    reporte de PNL). Blockchain es util aqui porque permite demostrar, sin
    confiar en quien custodia los archivos, que el resultado presentado es el
    mismo que se genero: basta recomputar el hash y compararlo.

Estructura de cada bloque:
    indice, timestamp, datos, hash_previo, hash
    hash = SHA-256( indice | timestamp | datos | hash_previo )

Artefactos:
    data/blockchain/cadena.json
    data/reports/blockchain_bloques.csv
    data/reports/blockchain_validacion.csv
    data/reports/blockchain_prueba_alteracion.csv

Uso:
    python src/blockchain.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import (
    BLOCKCHAIN_JSON,
    MODELS,
    PROCESSED,
    REPORTS,
)
from utils import LOG, asegurar_dir, subtitulo, tabla, titulo


# --------------------------------------------------------------------------
# Utilidades de hash
# --------------------------------------------------------------------------
def hash_archivo(ruta: Path) -> str:
    """SHA-256 del contenido de un archivo."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _serializar(datos: dict) -> str:
    return json.dumps(datos, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------
# Bloque y cadena
# --------------------------------------------------------------------------
@dataclass
class Bloque:
    indice: int
    timestamp: str
    datos: dict
    hash_previo: str
    hash: str = ""

    def calcular_hash(self) -> str:
        contenido = f"{self.indice}|{self.timestamp}|{_serializar(self.datos)}|{self.hash_previo}"
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


@dataclass
class Cadena:
    bloques: list[Bloque] = field(default_factory=list)

    def agregar(self, datos: dict, timestamp: str | None = None) -> Bloque:
        indice = len(self.bloques)
        previo = self.bloques[-1].hash if self.bloques else "0" * 64
        ts = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        bloque = Bloque(indice=indice, timestamp=ts, datos=datos, hash_previo=previo)
        bloque.hash = bloque.calcular_hash()
        self.bloques.append(bloque)
        return bloque

    def es_valida(self) -> tuple[bool, list[str]]:
        """Recomputa todos los hashes y encadena; devuelve (ok, errores)."""
        errores: list[str] = []
        previo = "0" * 64
        for bloque in self.bloques:
            if bloque.hash_previo != previo:
                errores.append(f"Bloque {bloque.indice}: hash_previo no coincide con el bloque anterior")
            if bloque.calcular_hash() != bloque.hash:
                errores.append(f"Bloque {bloque.indice}: el hash registrado no coincide (datos alterados)")
            previo = bloque.hash
        return (len(errores) == 0, errores)

    def a_dataframe(self) -> pd.DataFrame:
        filas = []
        for b in self.bloques:
            fila = {
                "indice": b.indice,
                "timestamp": b.timestamp,
                "tipo": b.datos.get("tipo", ""),
                "archivo": b.datos.get("archivo", ""),
                "sha256": b.datos.get("sha256", ""),
                "bytes": b.datos.get("bytes", ""),
                "hash_previo": b.hash_previo,
                "hash": b.hash,
            }
            filas.append(fila)
        return pd.DataFrame(filas)

    def guardar(self, ruta: Path = BLOCKCHAIN_JSON) -> Path:
        asegurar_dir(ruta.parent)
        contenido = {
            "algoritmo_hash": "SHA-256",
            "bloques": [asdict(b) for b in self.bloques],
        }
        ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")
        return ruta

    @classmethod
    def cargar(cls, ruta: Path = BLOCKCHAIN_JSON) -> "Cadena":
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        bloques = [Bloque(**b) for b in contenido["bloques"]]
        return cls(bloques=bloques)


# --------------------------------------------------------------------------
# Registro de artefactos
# --------------------------------------------------------------------------
def artefactos_a_registrar() -> list[tuple[str, Path]]:
    return [
        ("dataset_procesado", PROCESSED / "flujos_clean.parquet"),
        ("reportes_pnl", PROCESSED / "reportes_enriquecidos.parquet"),
        ("modelo_ml", MODELS / "modelo_mejor.joblib"),
        ("metricas_ml", REPORTS / "metricas_modelos.csv"),
        ("reporte_pnl", REPORTS / "pnl_reporte.md"),
    ]


def construir_cadena() -> tuple[Cadena, list[str]]:
    print(titulo("BLOCKCHAIN - REGISTRO DE INTEGRIDAD"))
    cadena = Cadena()
    cadena.agregar(
        {
            "tipo": "genesis",
            "descripcion": "Bloque genesis del sistema de trazabilidad",
            "motivo": "Punto de partida inmutable de la cadena",
        }
    )
    omitidos = []
    for tipo, ruta in artefactos_a_registrar():
        if not ruta.exists():
            omitidos.append(str(ruta))
            continue
        cadena.agregar(
            {
                "tipo": tipo,
                "archivo": ruta.name,
                "sha256": hash_archivo(ruta),
                "bytes": ruta.stat().st_size,
                "motivo": "Resultado cuyo contenido debe poder verificarse",
            }
        )
        LOG.info("  registrado %-20s %s", tipo, ruta.name)
    if omitidos:
        LOG.warning("  artefactos no encontrados (se omiten): %s", ", ".join(omitidos))
    return cadena, omitidos


# --------------------------------------------------------------------------
# Verificacion y prueba de alteracion
# --------------------------------------------------------------------------
def verificar(cadena: Cadena | None = None) -> pd.DataFrame:
    cadena = cadena or Cadena.cargar()
    ok, errores = cadena.es_valida()
    filas = [
        {"bloque": b.indice, "archivo": b.datos.get("archivo", b.datos.get("tipo")),
         "sha256_registrado": b.datos.get("sha256", "-"), "hash_valido": b.calcular_hash() == b.hash}
        for b in cadena.bloques
    ]
    df = pd.DataFrame(filas)
    df.attrs["ok"] = ok
    df.attrs["errores"] = errores
    return df


def prueba_alteracion(cadena: Cadena) -> pd.DataFrame:
    """Modifica un bloque en memoria y comprueba que la cadena lo detecta."""
    filas = []
    if len(cadena.bloques) < 2:
        return pd.DataFrame(columns=["escenario", "detectado", "detalle"])

    objetivo = cadena.bloques[1]
    original = dict(objetivo.datos)

    objetivo.datos["sha256"] = "0" * 64
    ok, errores = cadena.es_valida()
    filas.append(
        {
            "escenario": "Alterar el hash del contenido (sin recomputar)",
            "detectado": not ok,
            "detalle": errores[0] if errores else "no detectado",
        }
    )

    objetivo.datos = original
    ok, _ = cadena.es_valida()
    filas.append(
        {
            "escenario": "Restaurar el contenido original",
            "detectado": not ok,
            "detalle": "cadena intacta tras restaurar",
        }
    )
    return pd.DataFrame(filas)


def _comprobar_integridad_archivos(cadena: Cadena) -> pd.DataFrame:
    """Recomputa el hash real de cada archivo y lo compara con el registrado."""
    filas = []
    for b in cadena.bloques:
        archivo = b.datos.get("archivo")
        if not archivo:
            continue
        ruta = next((p for _, p in artefactos_a_registrar() if p.name == archivo), None)
        if ruta is None or not ruta.exists():
            continue
        actual = hash_archivo(ruta)
        filas.append(
            {
                "archivo": archivo,
                "sha256_registrado": b.datos.get("sha256"),
                "sha256_actual": actual,
                "integridad": "INTACTO" if actual == b.datos.get("sha256") else "MODIFICADO",
            }
        )
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def ejecutar() -> dict:
    cadena, _ = construir_cadena()
    ruta = cadena.guardar()
    ok, errores = cadena.es_valida()
    LOG.info("  cadena valida: %s (%d bloques)", ok, len(cadena.bloques))

    validacion = pd.DataFrame(
        [{"bloques": len(cadena.bloques), "cadena_valida": ok, "errores": "; ".join(errores) or "ninguno"}]
    )
    alteracion = prueba_alteracion(cadena)
    integridad = _comprobar_integridad_archivos(cadena)

    asegurar_dir(REPORTS)
    cadena.a_dataframe().to_csv(REPORTS / "blockchain_bloques.csv", index=False, encoding="utf-8-sig")
    validacion.to_csv(REPORTS / "blockchain_validacion.csv", index=False, encoding="utf-8-sig")
    alteracion.to_csv(REPORTS / "blockchain_prueba_alteracion.csv", index=False, encoding="utf-8-sig")
    if not integridad.empty:
        integridad.to_csv(REPORTS / "blockchain_integridad.csv", index=False, encoding="utf-8-sig")

    LOG.info("[ok] cadena guardada en %s", ruta)
    return {
        "cadena": cadena,
        "validacion": validacion,
        "alteracion": alteracion,
        "integridad": integridad,
    }


def main() -> int:
    resultado = ejecutar()
    print(subtitulo("Bloques registrados"))
    print(tabla(resultado["cadena"].a_dataframe()[["indice", "tipo", "archivo", "bytes"]]))
    print(subtitulo("Verificacion"))
    print(tabla(resultado["validacion"]))
    print(subtitulo("Prueba de alteracion"))
    print(tabla(resultado["alteracion"]))
    if not resultado["integridad"].empty:
        print(subtitulo("Integridad de archivos en disco"))
        print(tabla(resultado["integridad"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
