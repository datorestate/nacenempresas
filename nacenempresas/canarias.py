"""Municipios e islas de Canarias.

El BORME corta los nombres largos de municipio ("SANTA MARIA DE GUIA DE GRAN",
"PALMAS DE GRAN CANARIA (LAS") y los escribe sin tildes. municipio() devuelve el
nombre oficial completo y isla() la isla, para filtrar avisos y hacer páginas por isla.
"""
from __future__ import annotations

import unicodedata

ISLAS = {
    "gran-canaria": ("Gran Canaria", "35"),
    "lanzarote": ("Lanzarote y La Graciosa", "35"),
    "fuerteventura": ("Fuerteventura", "35"),
    "tenerife": ("Tenerife", "38"),
    "la-palma": ("La Palma", "38"),
    "la-gomera": ("La Gomera", "38"),
    "el-hierro": ("El Hierro", "38"),
}

_MUNICIPIOS = {
    "gran-canaria": [
        "Agaete", "Agüimes", "Artenara", "Arucas", "Firgas", "Gáldar", "Ingenio",
        "La Aldea de San Nicolás", "Las Palmas de Gran Canaria", "Mogán", "Moya",
        "San Bartolomé de Tirajana", "Santa Brígida", "Santa Lucía de Tirajana",
        "Santa María de Guía de Gran Canaria", "Tejeda", "Telde", "Teror",
        "Valsequillo de Gran Canaria", "Valleseco", "Vega de San Mateo"],
    "lanzarote": ["Arrecife", "Haría", "San Bartolomé", "Teguise", "Tías", "Tinajo", "Yaiza"],
    "fuerteventura": ["Antigua", "Betancuria", "La Oliva", "Pájara", "Puerto del Rosario", "Tuineje"],
    "tenerife": [
        "Adeje", "Arafo", "Arico", "Arona", "Buenavista del Norte", "Candelaria", "El Rosario",
        "El Sauzal", "El Tanque", "Fasnia", "Garachico", "Granadilla de Abona", "Guía de Isora",
        "Güímar", "Icod de los Vinos", "La Guancha", "La Matanza de Acentejo", "La Orotava",
        "La Victoria de Acentejo", "Los Realejos", "Los Silos", "Puerto de la Cruz",
        "San Cristóbal de La Laguna", "San Juan de la Rambla", "San Miguel de Abona",
        "Santa Cruz de Tenerife", "Santa Úrsula", "Santiago del Teide", "Tacoronte", "Tegueste",
        "Vilaflor de Chasna"],
    "la-palma": [
        "Barlovento", "Breña Alta", "Breña Baja", "El Paso", "Fuencaliente de La Palma", "Garafía",
        "Los Llanos de Aridane", "Puntagorda", "Puntallana", "San Andrés y Sauces",
        "Santa Cruz de La Palma", "Tazacorte", "Tijarafe", "Villa de Mazo"],
    "la-gomera": ["Agulo", "Alajeró", "Hermigua", "San Sebastián de La Gomera", "Valle Gran Rey",
                  "Vallehermoso"],
    "el-hierro": ["El Pinar de El Hierro", "Frontera", "Valverde"],
}

# Nombres antiguos o abreviados que aparecen en el BORME
_ALIAS = {
    "san nicolas de tolentino": "La Aldea de San Nicolás",
    "aldea de san nicolas": "La Aldea de San Nicolás",
    "vilaflor": "Vilaflor de Chasna",
    "valsequillo": "Valsequillo de Gran Canaria",
    "el pinar": "El Pinar de El Hierro",
    "pinar de el hierro": "El Pinar de El Hierro",
    "san mateo": "Vega de San Mateo",
    "santa maria de guia": "Santa María de Guía de Gran Canaria",
    "la laguna": "San Cristóbal de La Laguna",
    "fuencaliente": "Fuencaliente de La Palma",
    "mazo": "Villa de Mazo",
    "llanos de aridane": "Los Llanos de Aridane",
}

_ARTICULOS = ("las ", "los ", "la ", "el ")


def _clave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    t = " ".join(t.replace("(", " ").replace(")", " ").replace(",", " ").split())
    for a in _ARTICULOS:
        if t.startswith(a):
            t = t[len(a):]
            break
    # "palmas de gran canaria las" (artículo pospuesto por el BORME)
    for a in ("las", "los", "la", "el"):
        if t.endswith(" " + a):
            t = t[: -len(a) - 1]
    return t


_POR_CLAVE: dict[str, tuple[str, str]] = {}
for _isla, _nombres in _MUNICIPIOS.items():
    for _n in _nombres:
        _POR_CLAVE[_clave(_n)] = (_n, _isla)
for _a, _n in _ALIAS.items():
    _POR_CLAVE[_clave(_a)] = _POR_CLAVE[_clave(_n)]


def _busca(municipio: str, provincia: str | None = None):
    bruto = (municipio or "").strip().lower().strip("()")
    if bruto == "las" and provincia in (None, "35"):
        # El BORME a veces deja solo "(LAS" al cortar "PALMAS DE GRAN CANARIA (LAS)"
        return _POR_CLAVE[_clave("Las Palmas de Gran Canaria")]
    k = _clave(municipio)
    if not k:
        return None
    if k in _POR_CLAVE:
        return _POR_CLAVE[k]
    if len(k) >= 8:  # nombre cortado por el BORME: prefijo único
        cand = {v for c, v in _POR_CLAVE.items() if c.startswith(k)}
        if len(cand) == 1:
            return cand.pop()
    return None


def municipio(nombre: str | None, provincia: str | None = None) -> str | None:
    """Nombre oficial del municipio canario; si no es de Canarias, el original."""
    if provincia not in (None, "35", "38"):
        return nombre
    r = _busca(nombre or "", provincia)
    return r[0] if r else nombre


def isla(nombre: str | None, provincia: str | None = None) -> str | None:
    """Clave de la isla ('lanzarote', 'tenerife'...) o None."""
    if provincia not in (None, "35", "38"):
        return None
    r = _busca(nombre or "", provincia)
    return r[1] if r else None


def nombre_isla(clave: str) -> str:
    return ISLAS[clave][0]


def isla_de_texto(texto: str) -> str | None:
    """'Lanzarote', 'isla de La Palma', 'iLP' -> clave de isla."""
    t = (texto or "").strip()
    codigos = {"iGC": "gran-canaria", "iLZ": "lanzarote", "iFV": "fuerteventura", "iTF": "tenerife",
               "iLP": "la-palma", "iLG": "la-gomera", "iEH": "el-hierro"}
    if t in codigos:
        return codigos[t]
    k = _clave(t.lower().replace("isla de ", "").replace("isla ", ""))
    for clave, (nombre, _) in ISLAS.items():
        if k and (k == _clave(nombre) or k == clave.replace("-", " ") or k == _clave(nombre.split(" y ")[0])):
            return clave
    if k in ("graciosa",):
        return "lanzarote"
    return None


CODIGOS_STRIPE = {"gran-canaria": "iGC", "lanzarote": "iLZ", "fuerteventura": "iFV", "tenerife": "iTF",
                  "la-palma": "iLP", "la-gomera": "iLG", "el-hierro": "iEH"}
