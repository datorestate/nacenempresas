"""Almacenamiento de los datos diarios.

- data/publico/: fichas reducidas (sin domicilio) que alimentan la web. Se publican.
- data/privado/: registros completos cifrados con Fernet (clave en el secreto DATA_KEY).
  El repositorio puede ser público sin regalar el producto de pago.
"""
from __future__ import annotations

import gzip
import json
import os
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(os.environ.get("RC_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
PUBLICO = RAIZ / "publico"
PRIVADO = RAIZ / "privado"
LOCAL = RAIZ / "local"  # sin cifrar, ignorado por git (desarrollo)


def _fernet():
    clave = os.environ.get("DATA_KEY")
    if not clave:
        return None
    from cryptography.fernet import Fernet
    return Fernet(clave.encode())


def guardar_dia(dia: str, publico: dict, completo: dict):
    PUBLICO.mkdir(parents=True, exist_ok=True)
    (PUBLICO / f"{dia}.json").write_text(json.dumps(publico, ensure_ascii=False, indent=0), "utf-8")
    datos = gzip.compress(json.dumps(completo, ensure_ascii=False).encode("utf-8"))
    f = _fernet()
    if f:
        PRIVADO.mkdir(parents=True, exist_ok=True)
        (PRIVADO / f"{dia}.json.gz.enc").write_bytes(f.encrypt(datos))
    else:
        LOCAL.mkdir(parents=True, exist_ok=True)
        (LOCAL / f"{dia}.json.gz").write_bytes(datos)
    actualizar_indice()


def cargar_completo(dia: str) -> dict | None:
    enc = PRIVADO / f"{dia}.json.gz.enc"
    loc = LOCAL / f"{dia}.json.gz"
    if enc.exists() and _fernet():
        return json.loads(gzip.decompress(_fernet().decrypt(enc.read_bytes())))
    if loc.exists():
        return json.loads(gzip.decompress(loc.read_bytes()))
    return None


def cargar_publico(dia: str) -> dict | None:
    p = PUBLICO / f"{dia}.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def dias_disponibles() -> list[str]:
    if not PUBLICO.exists():
        return []
    return sorted(p.stem for p in PUBLICO.glob("20??-??-??.json"))


def registros_rango(desde: date, hasta: date, solo_constituciones=False) -> list[dict]:
    """Registros completos entre dos fechas (incluidas)."""
    out = []
    d = desde
    while d <= hasta:
        c = cargar_completo(d.isoformat())
        if c:
            for r in c["registros"]:
                if not solo_constituciones or r.get("es_constitucion"):
                    out.append(r)
        d += timedelta(days=1)
    return out


def actualizar_indice():
    indice = []
    for dia in dias_disponibles():
        p = cargar_publico(dia)
        indice.append({"fecha": dia, "constituciones": p.get("total_constituciones", 0),
                       "por_provincia": p.get("por_provincia", {})})
    (PUBLICO / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), "utf-8")
    return indice
