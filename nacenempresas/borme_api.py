"""Cliente de la API de datos abiertos del BOE para el sumario del BORME.

Documentación: https://www.boe.es/datosabiertos/documentos/APIsumarioBORME.pdf
Endpoint: GET https://www.boe.es/datosabiertos/api/borme/sumario/AAAAMMDD
Cabecera Accept: application/json (o application/xml).

El BORME no se publica sábados, domingos ni festivos en Madrid: en esos días la
API responde 404 y aquí se devuelve una lista vacía.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

import requests

API = "https://www.boe.es/datosabiertos/api/borme/sumario/{fecha}"
LEGACY_XML = "https://www.boe.es/diario_borme/xml.php?id=BORME-S-{fecha}"
BASE = "https://www.boe.es"
USER_AGENT = "NacenEmpresas/1.0 (reutilizacion de datos abiertos del BOE)"


@dataclass
class DocumentoA:
    identificador: str          # BORME-A-2025-169-03
    provincia_codigo: str       # 03
    titulo: str                 # ALICANTE/ALACANT
    url_pdf: str
    fecha: str                  # AAAA-MM-DD


_ID_RE = re.compile(r"^BORME-A-(\d{4})-(\d+)-(\d{2})$")


def _sesion() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _get(sesion, url, accept, intentos=4):
    ultimo = None
    for i in range(intentos):
        try:
            r = sesion.get(url, headers={"Accept": accept}, timeout=60)
            if r.status_code == 404:
                return None
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} en {url}")
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            ultimo = e
            time.sleep(2 ** i * 3)
    raise RuntimeError(f"No se pudo descargar {url}: {ultimo}")


def _url_absoluta(u: str) -> str:
    u = u.strip()
    return u if u.startswith("http") else BASE + u


def _de_json(obj, fecha_iso, salida):
    """Recorre el JSON del sumario y recoge todos los items de la sección A."""
    if isinstance(obj, dict):
        ident = obj.get("identificador") or obj.get("id")
        if isinstance(ident, str) and _ID_RE.match(ident):
            url = obj.get("url_pdf")
            if isinstance(url, dict):
                url = url.get("texto") or url.get("url") or url.get("#text")
            if url:
                salida.append(DocumentoA(ident, _ID_RE.match(ident).group(3),
                                         str(obj.get("titulo", "")).strip(),
                                         _url_absoluta(url), fecha_iso))
        for v in obj.values():
            _de_json(v, fecha_iso, salida)
    elif isinstance(obj, list):
        for v in obj:
            _de_json(v, fecha_iso, salida)


def _de_xml(texto: bytes, fecha_iso, salida):
    raiz = ET.fromstring(texto)
    for el in raiz.iter():
        ident = el.get("id") or (el.findtext("identificador") or "").strip()
        if ident and _ID_RE.match(ident):
            url = (el.findtext("url_pdf") or el.findtext("urlPdf") or "").strip()
            titulo = (el.findtext("titulo") or "").strip()
            if url:
                salida.append(DocumentoA(ident, _ID_RE.match(ident).group(3), titulo,
                                         _url_absoluta(url), fecha_iso))


def documentos_seccion_a(dia: date, sesion=None) -> list[DocumentoA]:
    """Lista de PDFs provinciales de la sección A (actos inscritos) de un día."""
    sesion = sesion or _sesion()
    f = dia.strftime("%Y%m%d")
    fecha_iso = dia.isoformat()
    salida: list[DocumentoA] = []
    r = _get(sesion, API.format(fecha=f), "application/json")
    if r is not None:
        try:
            _de_json(r.json(), fecha_iso, salida)
        except ValueError:
            _de_xml(r.content, fecha_iso, salida)
    if not salida:
        # Respaldo: sumario XML clásico
        r2 = _get(sesion, LEGACY_XML.format(fecha=f), "application/xml")
        if r2 is not None and r2.content.strip().startswith(b"<"):
            try:
                _de_xml(r2.content, fecha_iso, salida)
            except ET.ParseError:
                pass
    vistos, unicos = set(), []
    for d in salida:
        if d.identificador not in vistos:
            vistos.add(d.identificador)
            unicos.append(d)
    return sorted(unicos, key=lambda d: d.identificador)


def descargar_pdf(doc: DocumentoA, sesion=None) -> bytes:
    sesion = sesion or _sesion()
    r = _get(sesion, doc.url_pdf, "application/pdf")
    if r is None:
        raise RuntimeError(f"PDF no encontrado: {doc.url_pdf}")
    time.sleep(0.5)  # cortesía con el servidor del BOE
    return r.content
