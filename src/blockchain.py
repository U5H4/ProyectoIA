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
    data/blockchain/cadena_<YYYYMMDD_HHMMSS>_UTC.backup.json  (copia previa archivada antes de reconstruir)
    data/reports/blockchain_bloques.csv
    data/reports/blockchain_validacion.csv
    data/reports/blockchain_prueba_alteracion.csv

Comportamiento ante una cadena previa existente:
    ANTES de reconstruir se archiva SIEMPRE una copia integra en
    data/blockchain/cadena_<YYYYMMDD_HHMMSS>_UTC.backup.json.
    Si la cadena previa es internamente invalida, NO se reconstruye (la evidencia
    queda archivada e intacta) salvo que se indique --reconstruir-forzadamente.
    Si algun artefacto esperado no existe, la cadena NO se guarda (no crece con
    menos bloques) y el proceso termina con codigo != 0.

Uso:
    python src/blockchain.py
    python src/blockchain.py --solo-verificar            # offline, no escribe ni reconstruye
    python src/blockchain.py --reconstruir-forzadamente  # caso extremo: fuerza reconstruir
"""

from __future__ import annotations

import hashlib
import json
import shutil
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
        ("predictor_ml", MODELS / "predictor.joblib"),
        ("metricas_ml", REPORTS / "metricas_modelos.csv"),
        ("reporte_pnl", REPORTS / "pnl_reporte.md"),
        ("reporte_integrado", REPORTS / "reporte_integrado.json"),
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
        LOG.error("  artefactos esperados NO encontrados (%d):", len(omitidos))
        for ruta in omitidos:
            LOG.error("    - %s", ruta)
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
            "detectado": False,
            "detalle": "cadena intacta tras restaurar (esperado: no hay alteracion)",
        }
    )
    return pd.DataFrame(filas)


def estado_previo(ruta: Path | None = None) -> tuple[bool, list[str], int]:
    """Valida la cadena existente en disco ANTES de reconstruirla."""
    ruta = Path(ruta) if ruta is not None else BLOCKCHAIN_JSON
    if not ruta.exists():
        return (False, [f"No existe {ruta.name}"], 0)
    try:
        cadena = Cadena.cargar(ruta)
    except Exception as exc:  # noqa: BLE001
        return (False, [f"No se pudo leer {ruta.name}: {exc}"], 0)
    ok, errores = cadena.es_valida()
    return (ok, errores, len(cadena.bloques))


def archivar_cadena_previa(ruta: Path | None = None) -> Path | None:
    """Copia integra de la cadena previa a `cadena_<YYYYMMDD_HHMMSS>_UTC.backup.json`.

    Devuelve la ruta del backup, o None si no existia cadena previa.
    """
    ruta = Path(ruta) if ruta is not None else BLOCKCHAIN_JSON
    if not ruta.exists():
        return None
    asegurar_dir(ruta.parent)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = ruta.parent / f"cadena_{ts}_UTC.backup.json"
    n = 1
    while backup.exists():
        backup = ruta.parent / f"cadena_{ts}_UTC_{n}.backup.json"
        n += 1
    shutil.copy2(ruta, backup)
    return backup


def comprobar_integridad_archivos(
    cadena: Cadena,
    artefactos: list[tuple[str, Path]] | None = None,
) -> pd.DataFrame:
    """Recomputa el SHA-256 real de cada archivo registrado y lo compara con el
    sha256 persistido en `cadena`.

    No escribe ni reconstruye nada. Estados por artefacto: OK / MODIFICADO / FALTANTE.
    Devuelve un DataFrame con columnas: archivo, sha256_registrado, sha256_actual, estado, detalle.
    """
    artefactos = artefactos_a_registrar() if artefactos is None else artefactos
    rutas = {p.name: p for _, p in artefactos}
    filas = []
    for b in cadena.bloques:
        archivo = b.datos.get("archivo")
        if not archivo:
            continue
        registrado = b.datos.get("sha256", "")
        ruta = rutas.get(archivo)
        if ruta is None:
            filas.append(
                {
                    "archivo": archivo,
                    "sha256_registrado": registrado,
                    "sha256_actual": "-",
                    "estado": "FALTANTE",
                    "detalle": "artefacto no reconocido en artefactos_a_registrar()",
                }
            )
            continue
        if not ruta.exists():
            filas.append(
                {
                    "archivo": archivo,
                    "sha256_registrado": registrado,
                    "sha256_actual": "-",
                    "estado": "FALTANTE",
                    "detalle": "no encontrado en disco",
                }
            )
            continue
        actual = hash_archivo(ruta)
        estado = "OK" if actual == registrado else "MODIFICADO"
        filas.append(
            {
                "archivo": archivo,
                "sha256_registrado": registrado,
                "sha256_actual": actual,
                "estado": estado,
                "detalle": "" if estado == "OK" else "el contenido difiere del registrado",
            }
        )
    return pd.DataFrame(
        filas, columns=["archivo", "sha256_registrado", "sha256_actual", "estado", "detalle"]
    )


# Alias retrocompatible (nombre historico).
_comprobar_integridad_archivos = comprobar_integridad_archivos


def verificar_offline(
    ruta: Path | None = None,
    artefactos: list[tuple[str, Path]] | None = None,
) -> dict:
    """Verificacion OFFLINE (--solo-verificar): no reconstruye ni escribe nada.

    (a) valida la consistencia interna de la cadena persistida en disco;
    (b) RE-HASHEA cada artefacto registrado contra el sha256 persistido y
        reporta OK / MODIFICADO / FALTANTE por artefacto;
    (c) ok=True solo si la cadena es internamente valida y todos los artefactos
        registrados estan en OK.
    """
    ruta = Path(ruta) if ruta is not None else BLOCKCHAIN_JSON
    columnas = ["archivo", "sha256_registrado", "sha256_actual", "estado", "detalle"]
    resultado = {
        "ruta": ruta,
        "existe": ruta.exists(),
        "bloques": 0,
        "ok_interno": False,
        "errores": [],
        "integridad": pd.DataFrame(columns=columnas),
        "ok": False,
    }
    if not ruta.exists():
        resultado["errores"] = [f"No existe {ruta.name}"]
        return resultado
    try:
        cadena = Cadena.cargar(ruta)
    except Exception as exc:  # noqa: BLE001
        resultado["errores"] = [f"No se pudo leer {ruta.name}: {exc}"]
        return resultado
    ok_interno, errores = cadena.es_valida()
    integridad = comprobar_integridad_archivos(cadena, artefactos)
    ok_artefactos = integridad.empty or bool((integridad["estado"] == "OK").all())
    resultado.update(
        bloques=len(cadena.bloques),
        ok_interno=ok_interno,
        errores=errores,
        integridad=integridad,
        ok=bool(ok_interno and ok_artefactos),
    )
    return resultado


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def _validacion_fallo(bloques: int, errores: list[str], omitidos: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "bloques": bloques,
                "cadena_valida": False,
                "errores": "; ".join(errores) or "fallo",
                "artefactos_omitidos": len(omitidos),
                "omitidos": "; ".join(omitidos) or "ninguno",
            }
        ]
    )


def ejecutar(reconstruir_forzadamente: bool = False) -> dict:
    """Reconstruye y guarda la cadena. NUNCA destruye evidencia en silencio.

    1. Archiva SIEMPRE la cadena previa (si existe) en
       data/blockchain/cadena_<YYYYMMDD_HHMMSS>_UTC.backup.json (copia integra).
    2. Si la cadena previa es internamente invalida: advertencia fuerte; se archiva
       igualmente y NO se reconstruye salvo `reconstruir_forzadamente=True`.
    3. Si falta algun artefacto esperado: la cadena NO se guarda (no crece con menos
       bloques) y ok=False (exit != 0 via main/run_all).
    """
    previo_ok, previo_errores, previo_n = estado_previo()
    backup = archivar_cadena_previa()
    if backup is not None:
        LOG.info("  cadena previa archivada integramente en %s", backup)

    if previo_n and not previo_ok:
        LOG.error("=" * 70)
        LOG.error(
            "ADVERTENCIA FUERTE: la cadena previa (%d bloques) NO es valida internamente: %s",
            previo_n,
            "; ".join(previo_errores),
        )
        LOG.error("La copia integra de la cadena previa quedo archivada en %s", backup)
        LOG.error("=" * 70)
        if not reconstruir_forzadamente:
            LOG.error(
                "NO se reconstruye la cadena para no destruir evidencia. "
                "Revisa el backup; si es un caso extremo, usa --reconstruir-forzadamente."
            )
            validacion = _validacion_fallo(
                previo_n,
                previo_errores + ["cadena previa invalida; reconstruccion abortada"],
                [],
            )
            asegurar_dir(REPORTS)
            validacion.to_csv(REPORTS / "blockchain_validacion.csv", index=False, encoding="utf-8-sig")
            return {
                "cadena": None,
                "validacion": validacion,
                "alteracion": pd.DataFrame(columns=["escenario", "detectado", "detalle"]),
                "ok": False,
                "omitidos": [],
                "guardada": False,
                "backup": backup,
            }
        LOG.warning(
            "--reconstruir-forzadamente activo: se reconstruye pese a la cadena previa "
            "invalida; la evidencia queda preservada en %s",
            backup,
        )
    elif previo_n:
        LOG.info("  cadena previa: %d bloques, valida=%s", previo_n, previo_ok)

    cadena, omitidos = construir_cadena()
    if omitidos:
        LOG.error("  FALLO: la cadena NO se guardara con menos bloques (%d omitido(s)).", len(omitidos))
        LOG.error("  Restaura los artefactos y reintenta.")
        validacion = _validacion_fallo(
            len(cadena.bloques),
            ["artefactos esperados no encontrados: " + "; ".join(omitidos)],
            omitidos,
        )
        asegurar_dir(REPORTS)
        validacion.to_csv(REPORTS / "blockchain_validacion.csv", index=False, encoding="utf-8-sig")
        return {
            "cadena": cadena,
            "validacion": validacion,
            "alteracion": pd.DataFrame(columns=["escenario", "detectado", "detalle"]),
            "ok": False,
            "omitidos": omitidos,
            "guardada": False,
            "backup": backup,
        }

    ruta = cadena.guardar()
    ok, errores = cadena.es_valida()
    LOG.info("  cadena valida: %s (%d bloques)", ok, len(cadena.bloques))

    validacion = pd.DataFrame(
        [
            {
                "bloques": len(cadena.bloques),
                "cadena_valida": ok,
                "errores": "; ".join(errores) or "ninguno",
                "artefactos_omitidos": 0,
                "omitidos": "ninguno",
            }
        ]
    )
    alteracion = prueba_alteracion(cadena)

    asegurar_dir(REPORTS)
    cadena.a_dataframe().to_csv(REPORTS / "blockchain_bloques.csv", index=False, encoding="utf-8-sig")
    validacion.to_csv(REPORTS / "blockchain_validacion.csv", index=False, encoding="utf-8-sig")
    alteracion.to_csv(REPORTS / "blockchain_prueba_alteracion.csv", index=False, encoding="utf-8-sig")

    LOG.info("[ok] cadena guardada en %s", ruta)
    return {
        "cadena": cadena,
        "validacion": validacion,
        "alteracion": alteracion,
        "ok": ok,
        "omitidos": [],
        "guardada": True,
        "backup": backup,
    }


def _imprimir_verificacion_offline(resultado: dict) -> None:
    print(subtitulo("Verificacion offline de la cadena (sin reconstruir, sin escribir)"))
    if not resultado["existe"]:
        for error in resultado["errores"]:
            LOG.error("  %s", error)
        print("\nRESULTADO: FALLO — la cadena no existe.")
        return
    LOG.info("  bloques=%d  valida=%s", resultado["bloques"], resultado["ok_interno"])
    for error in resultado["errores"]:
        LOG.warning("  %s", error)
    integ = resultado["integridad"]
    if integ.empty:
        print("\n  (la cadena no registra artefactos de archivo)")
    else:
        vista = integ.copy()
        vista["sha256_registrado"] = vista["sha256_registrado"].str.slice(0, 16) + "…"
        vista.loc[vista["sha256_actual"] != "-", "sha256_actual"] = (
            vista.loc[vista["sha256_actual"] != "-", "sha256_actual"].str.slice(0, 16) + "…"
        )
        print(subtitulo("Integridad de artefactos (re-hash vs cadena.json persistida)"))
        print(tabla(vista[["archivo", "sha256_registrado", "sha256_actual", "estado"]]))
        cuenta = integ["estado"].value_counts().to_dict()
        print(
            "\n  Resumen: OK={}  MODIFICADO={}  FALTANTE={}".format(
                cuenta.get("OK", 0), cuenta.get("MODIFICADO", 0), cuenta.get("FALTANTE", 0)
            )
        )
    if resultado["ok"]:
        print("\nRESULTADO: OK — cadena internamente valida y todos los artefactos coinciden.")
    else:
        print("\nRESULTADO: FALLO — ver detalles. No se ha modificado ni reconstruido nada.")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Blockchain de trazabilidad.")
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="Verificacion OFFLINE: valida la consistencia interna de cadena.json y "
        "re-hashea cada artefacto registrado (OK/MODIFICADO/FALTANTE). "
        "No reconstruye ni escribe nada. Sale con != 0 si hay fallos.",
    )
    parser.add_argument(
        "--reconstruir-forzadamente",
        action="store_true",
        help="Caso extremo: permite reconstruir la cadena aunque la cadena previa en "
        "disco sea internamente invalida (la previa se archiva siempre antes).",
    )
    args = parser.parse_args(argv)

    if args.solo_verificar:
        resultado = verificar_offline()
        _imprimir_verificacion_offline(resultado)
        return 0 if resultado["ok"] else 1

    resultado = ejecutar(reconstruir_forzadamente=args.reconstruir_forzadamente)
    if resultado["cadena"] is not None:
        print(subtitulo("Bloques registrados" if resultado["guardada"] else "Bloques construidos (NO guardados)"))
        print(tabla(resultado["cadena"].a_dataframe()[["indice", "tipo", "archivo", "bytes"]]))
    else:
        print("\nNo se reconstruyo la cadena (ver mensajes anteriores).")
    print(subtitulo("Verificacion"))
    print(tabla(resultado["validacion"]))
    if not resultado["alteracion"].empty:
        print(subtitulo("Prueba de alteracion"))
        print(tabla(resultado["alteracion"]))
    if resultado["omitidos"]:
        print(subtitulo("Artefactos omitidos"))
        for omitido in resultado["omitidos"]:
            print(f"  - {omitido}")
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
