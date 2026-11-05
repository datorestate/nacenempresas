"""Provincias españolas con su código INE (el sufijo de los PDF del BORME-A)."""
import re
import unicodedata

PROVINCIAS = {
    "01": "Araba/Álava", "02": "Albacete", "03": "Alicante", "04": "Almería",
    "05": "Ávila", "06": "Badajoz", "07": "Illes Balears", "08": "Barcelona",
    "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
    "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña", "16": "Cuenca",
    "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
    "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
    "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
    "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
    "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
    "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
    "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
    "52": "Melilla",
}

# Alias para reconocer lo que escribe un cliente ("vizcaya", "baleares", "tenerife"...)
ALIAS = {
    "alava": "01", "araba": "01", "baleares": "07", "islas baleares": "07",
    "mallorca": "07", "castello": "12", "castellon de la plana": "12",
    "la coruna": "15", "coruna": "15", "guipuzcoa": "20", "rioja": "26",
    "orense": "32", "oviedo": "33", "gran canaria": "35", "tenerife": "38",
    "santander": "39", "vizcaya": "48", "bilbao": "48", "san sebastian": "20",
    "donostia": "20", "valencia/valencia": "46", "alicante/alacant": "03",
    "castellon/castello": "12", "gerona": "17", "lerida": "25",
}


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return t


def normaliza(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.lower()).strip()


_POR_NOMBRE = {}
for _cod, _nom in PROVINCIAS.items():
    _POR_NOMBRE[normaliza(_nom)] = _cod
    for parte in _nom.split("/"):
        _POR_NOMBRE[normaliza(parte)] = _cod
_POR_NOMBRE.update(ALIAS)


def codigo_provincia(texto: str):
    """Devuelve el código INE para un nombre de provincia escrito libremente, o None."""
    if not texto:
        return None
    t = normaliza(texto)
    if t in _POR_NOMBRE:
        return _POR_NOMBRE[t]
    if re.fullmatch(r"\d{1,2}", t) and t.zfill(2) in PROVINCIAS:
        return t.zfill(2)
    for nombre, cod in _POR_NOMBRE.items():
        if len(t) >= 4 and (nombre.startswith(t) or t.startswith(nombre)):
            return cod
    return None


def lista_provincias(texto: str, maximo: int = 5):
    """'Málaga, Sevilla y Cádiz' -> ['29', '41', '11'] (sin duplicados, hasta `maximo`)."""
    partes = re.split(r"[,;/\n]| y |\+", texto or "")
    codigos = []
    for p in partes:
        c = codigo_provincia(p)
        if c and c not in codigos:
            codigos.append(c)
    return codigos[:maximo]


def nombre(codigo: str) -> str:
    return PROVINCIAS.get(codigo, codigo)


def slug_provincia(codigo: str) -> str:
    return slug(PROVINCIAS[codigo].split("/")[0])
