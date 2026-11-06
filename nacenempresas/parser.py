"""Extracción de actos de la sección A del BORME (PDF provincial) a datos estructurados.

Principio de privacidad: la salida NUNCA contiene nombres de personas físicas.
- Los actos sobre cargos (nombramientos, ceses, socio único...) se reducen a la
  lista de cargos afectados ("Adm. Unico"), sin nombres.
- Las inscripciones de empresarios individuales (personas físicas) se descartan.
"""
from __future__ import annotations

import io
import re
from datetime import date

import pdfplumber

from . import canarias, sectores
from .provincias import nombre as nombre_provincia

# ---------------------------------------------------------------- texto del PDF

_CABECERAS = [
    re.compile(r"^BOLET[IÍ]N OFICIAL DEL REGISTRO MERCANTIL\s*$"),
    re.compile(r"^N[úu]m\.\s*\d+\s+\w+\s+\d+\s+de\s+\w+\s+de\s+\d{4}\s+P[áa]g\.\s*\d+"),
    re.compile(r"^SECCI[ÓO]N PRIMERA\s*$"),
    re.compile(r"^Empresarios\s*$"),
    re.compile(r"^Actos inscritos\s*$"),
    re.compile(r"^https?://www\.boe\.es"),
    re.compile(r"D\.L\.:\s*M-5188/1990"),
    re.compile(r"^cve:\s*BORME", re.I),
    re.compile(r"^Verificable en", re.I),
]


def pdf_a_texto(pdf: bytes | str) -> str:
    """Texto limpio: solo caracteres horizontales (quita el CVE vertical) y sin cabeceras."""
    fuente = io.BytesIO(pdf) if isinstance(pdf, (bytes, bytearray)) else pdf
    lineas = []
    with pdfplumber.open(fuente) as doc:
        for pagina in doc.pages:
            horizontal = pagina.filter(
                lambda o: o.get("upright", True) if o.get("object_type") == "char" else True)
            texto = horizontal.extract_text() or ""
            previa_actos = False
            for linea in texto.split("\n"):
                l = linea.strip()
                if not l:
                    continue
                if any(p.search(l) for p in _CABECERAS):
                    previa_actos = l.lower().startswith("actos inscritos")
                    continue
                if previa_actos and not _ENTRADA_RE.match(l):
                    # título de provincia tras "Actos inscritos"
                    previa_actos = False
                    continue
                previa_actos = False
                lineas.append(l)
    return "\n".join(lineas)


# ---------------------------------------------------------------- entradas

_ENTRADA_RE = re.compile(r"^(\d{1,7}) - (.+)$")


def separar_entradas(texto: str) -> list[tuple[int, list[str]]]:
    """Divide el texto en entradas numeradas consecutivas: [(numero, lineas)]."""
    entradas: list[tuple[int, list[str]]] = []
    for linea in texto.split("\n"):
        m = _ENTRADA_RE.match(linea)
        if m:
            n = int(m.group(1))
            if not entradas or n == entradas[-1][0] + 1 or (
                    n > entradas[-1][0] and n - entradas[-1][0] < 50):
                entradas.append((n, [m.group(2)]))
                continue
        if entradas:
            entradas[-1][1].append(linea)
    return entradas


# ---------------------------------------------------------------- actos

ACTOS = [
    "Constitución", "Nombramientos", "Ceses/Dimisiones", "Revocaciones", "Reelecciones",
    "Modificaciones estatutarias", "Cambio de domicilio social", "Cambio de objeto social",
    "Ampliacion del objeto social", "Ampliación del objeto social",
    "Cambio de denominación social", "Ampliación de capital", "Reducción de capital",
    "Disolución", "Extinción", "Declaración de unipersonalidad",
    "Pérdida del caracter de unipersonalidad", "Pérdida del carácter de unipersonalidad",
    "Cambio de identidad del socio único", "Sociedad unipersonal", "Situación concursal",
    "Fusión por absorción", "Fusión por unión", "Escisión parcial", "Escisión total",
    "Segregación", "Cesión global de activo y pasivo", "Transformación de sociedad",
    "Datos registrales", "Otros conceptos", "Cancelaciones de oficio de nombramientos",
    "Cierre provisional hoja registral por baja en el índice de Entidades Jurídicas",
    "Cierre provisional de la hoja registral por revocación del NIF",
    "Cierre provisional hoja registral art. 137.2 Ley 43/1995",
    "Cierre provisional de la hoja registral por revocación del NIF de Entidades Jurídicas",
    "Reapertura hoja registral", "Reactivación de la sociedad", "Depósito de libros",
    "Primera inscripción (O.M. 10/6/1.997)", "Primera inscripcion (O.M. 10/6/1.997)",
    "Fe de erratas", "Página web de la sociedad", "Emisión de obligaciones",
    "Desembolso de dividendos pasivos", "Adaptación Ley 2/95", "Adaptación Ley 44/2015",
    "Modificación de poderes", "Crédito incobrable", "Empresario Individual",
    "Articulo 378.5 del Reglamento del Registro Mercantil",
    "Acuerdo de ampliación de capital social sin ejecutar", "Apertura de sucursal",
    "Cierre de sucursal", "Sucursal", "Unipersonal",
]
ACTOS.sort(key=len, reverse=True)
_ACTO_RE = re.compile(
    r"(?:^|(?<=\.\s)|(?<=\.\.))(" + "|".join(re.escape(a) for a in ACTOS) + r")(?:\.|:)?(?=\s|$)")

CARGOS_ACTOS = {"Nombramientos", "Ceses/Dimisiones", "Revocaciones", "Reelecciones",
                "Cancelaciones de oficio de nombramientos", "Declaración de unipersonalidad",
                "Cambio de identidad del socio único", "Modificación de poderes"}

TIPO_EVENTO = {
    "Constitución": "constitucion",
    "Cambio de domicilio social": "traslado",
    "Ampliación de capital": "ampliacion_capital",
    "Reducción de capital": "reduccion_capital",
    "Disolución": "disolucion",
    "Extinción": "extincion",
    "Situación concursal": "concurso",
    "Cambio de denominación social": "cambio_denominacion",
    "Cambio de objeto social": "cambio_objeto",
    "Ampliacion del objeto social": "cambio_objeto",
    "Ampliación del objeto social": "cambio_objeto",
    "Transformación de sociedad": "transformacion",
    "Fusión por absorción": "fusion", "Fusión por unión": "fusion",
    "Escisión parcial": "escision", "Escisión total": "escision", "Segregación": "escision",
    "Cesión global de activo y pasivo": "fusion",
    "Nombramientos": "cambio_cargos", "Ceses/Dimisiones": "cambio_cargos",
    "Revocaciones": "cambio_cargos",
    "Declaración de unipersonalidad": "unipersonalidad",
    "Cierre provisional hoja registral por baja en el índice de Entidades Jurídicas": "cierre_hoja",
    "Cierre provisional de la hoja registral por revocación del NIF": "cierre_hoja",
    "Cierre provisional de la hoja registral por revocación del NIF de Entidades Jurídicas": "cierre_hoja",
    "Cierre provisional hoja registral art. 137.2 Ley 43/1995": "cierre_hoja",
    "Reapertura hoja registral": "reactivacion", "Reactivación de la sociedad": "reactivacion",
    "Página web de la sociedad": "pagina_web",
    "Apertura de sucursal": "sucursal",
}

SENAL = {  # para clientes: oportunidad comercial o riesgo
    "constitucion": "oportunidad", "traslado": "oportunidad",
    "ampliacion_capital": "oportunidad", "cambio_objeto": "oportunidad",
    "pagina_web": "oportunidad", "sucursal": "oportunidad", "reactivacion": "oportunidad",
    "cambio_denominacion": "neutra", "transformacion": "neutra", "fusion": "neutra",
    "escision": "neutra", "cambio_cargos": "neutra", "unipersonalidad": "neutra",
    "reduccion_capital": "riesgo", "disolucion": "riesgo", "extincion": "riesgo",
    "concurso": "riesgo", "cierre_hoja": "riesgo",
}

# ---------------------------------------------------------------- denominación

_FORMAS = [
    ("SOCIEDAD LIMITADA NUEVA EMPRESA", "SLNE"), ("SOCIEDAD LIMITADA PROFESIONAL", "SLP"),
    ("SOCIEDAD LIMITADA LABORAL", "SLL"), ("SOCIEDAD LIMITADA UNIPERSONAL", "SLU"),
    ("SOCIEDAD LIMITADA", "SL"), ("SOCIEDAD ANONIMA", "SA"), ("SOCIEDAD ANÓNIMA", "SA"),
    ("SOCIEDAD COOPERATIVA", "COOP"), ("SOCIEDAD CIVIL", "SC"),
    ("AGRUPACION DE INTERES ECONOMICO", "AIE"),
]
_SUFIJO_RE = re.compile(
    r"\b(S\.?L\.?N\.?E|S\.?L\.?P|S\.?L\.?L|S\.?L\.?U|S\.?A\.?U|S\.?A\.?L|S\.?A\.?P|"
    r"S\.?\s?COOP\.?(?:\s?\w+)?|S\.?C\.?C\.?L|S\.?C\.?L|A\.?I\.?E|S\.?R\.?L|S\.?L|S\.?A|S\.?C)\.?$")
_EXTRANJERAS = re.compile(
    r"\b(GMBH|LTD|LIMITED|B\.?V|N\.?V|SAS|SARL|S\.?P\.?A|INC|LLC|AG|AB|OY|PLC|CORP|SE|"
    r"LDA|SRO|S\.R\.O|KFT|SPOLKA|SP\. Z O\.O|BVBA|SPRL|APS|ASA|AS|FUNDACION|ASOCIACION|"
    r"COMUNIDAD|UTE|UNION TEMPORAL)\b")


def _forma_juridica(nombre: str):
    n = nombre.upper().rstrip(". ")
    n = re.sub(r"\s+EN LIQUIDACI[OÓ]N$", "", n)
    n = re.sub(r"\s*\(R\.M\.[^)]*\)$", "", n).rstrip(". ")
    for largo, corto in _FORMAS:
        if n.endswith(largo):
            return corto
    m = _SUFIJO_RE.search(n)
    if m:
        f = re.sub(r"[\.\s]", "", m.group(1))
        return "COOP" if f.startswith("SCOOP") else f
    # Formas que no van al final del nombre: "SOCIEDAD COOPERATIVA DE CREDITO", "SOCIEDAD AGRARIA DE TRANSFORMACION N.º 123"...
    for patron, corto in _FORMAS_INTERIORES:
        if re.search(patron, n):
            return corto
    if _EXTRANJERAS.search(n):
        return "EXTRANJERA/OTRA"
    return None


_FORMAS_INTERIORES = [
    (r"\bSOCIEDAD COOPERATIVA\b|\bS\.? ?COOP\b|\bCOOPERATIVA\b", "COOP"),
    (r"\bSOCIEDAD AGRARIA DE TRANSFORMACI[OÓ]N\b|\bS\.?A\.?T\.?\b", "SAT"),
    (r"\bSOCIEDAD DE INVERSI[OÓ]N DE CAPITAL VARIABLE\b|\bSICAV\b", "SICAV"),
    (r"\bSOCIEDAD DE RESPONSABILIDAD LIMITADA\b", "SL"),
    (r"\bSOCIEDAD COMANDITARIA\b|\bS\.? ?EN C\b", "SCOM"),
    (r"\bSOCIEDAD COLECTIVA\b", "SCOL"),
    (r"\bMUTUA\b|\bMUTUALIDAD\b", "MUTUA"),
    (r"\bSOCIEDAD DE GARANT[IÍ]A REC[IÍ]PROCA\b|\bS\.?G\.?R\b", "SGR"),
    (r"\bFONDO DE\b", "FONDO"),
]


# ---------------------------------------------------------------- utilidades

def _num_es(texto: str):
    try:
        return float(texto.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _fecha_corta(texto: str):
    """'1.09.25' -> '2025-09-01'."""
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})", texto or "")
    if not m:
        return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y = y + 2000 if y < 100 else y
    try:
        return date(y, mth, d).isoformat()
    except ValueError:
        return None


def _cargos(contenido: str) -> list[str]:
    """Extrae solo los nombres de cargo (con minúsculas), nunca las personas."""
    roles = []
    for m in re.finditer(r"(?:^|(?<=\.\s)|(?<=;))\s*([A-ZÁÉÍÓÚ][A-Za-záéíóúñÑ\./ ]{1,30}?):", contenido):
        r = m.group(1).strip()
        if re.search(r"[a-záéíóú]", r) and r not in roles:
            roles.append(r)
    return roles


def _detalle_seguro(contenido: str):
    """Solo devuelve textos breves sin mayúsculas sostenidas (los nombres del BORME van en mayúsculas)."""
    t = contenido.split(".")[0].strip()
    if not t or len(t) > 60 or re.search(r"\b[A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,}", t) or \
            re.search(r"\b(don|doña|D\.|Dña)\b", t):
        return None
    return t


_ARTICULO = re.compile(r"^(.*?)\s*\((LAS|LOS|LA|EL|L'|O|A|AS|OS|ELS|ES|SES|SA|LES)\)?$", re.I)


def _municipio(domicilio: str):
    """'C/ X 1 (PALMAS DE GRAN CANARIA (LAS)' -> 'Las Palmas De Gran Canaria'."""
    d = (domicilio or "").strip().rstrip(".")
    # el BORME corta los nombres largos: "(PALMAS DE GRAN CANARIA (LAS" sin cerrar
    m = re.search(r"\(([^()]*(?:\([^()]*\)?)?[^()]*)\)?$", d)
    if not m or not m.group(1).strip():
        return None
    muni = m.group(1).strip()
    a = _ARTICULO.match(muni)
    if a:
        muni = f"{a.group(2)} {a.group(1)}" if not a.group(2).endswith("'") else f"{a.group(2)}{a.group(1)}"
    return muni.title()


def _segmentos(cuerpo: str):
    marcas = list(_ACTO_RE.finditer(cuerpo))
    segs = []
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo)
        segs.append((m.group(1), cuerpo[m.end():fin].strip().rstrip(".").strip()))
    return segs


def _registrales(contenido: str):
    hoja = re.search(r"\bH\s+([A-Z]{1,3}\s*\d+)", contenido)
    insc = re.search(r"\(\s*(\d{1,2}\.\d{1,2}\.\d{2,4})\s*\)", contenido)
    return (hoja.group(1).replace("  ", " ") if hoja else None,
            _fecha_corta(insc.group(1)) if insc else None)


# ---------------------------------------------------------------- análisis

def analizar_entrada(numero: int, lineas: list[str], contexto: dict) -> dict | None:
    """Devuelve un dict sin datos personales, o None si la entrada es de una persona física."""
    nombre_l = [lineas[0]]
    resto = lineas[1:]
    while resto and not nombre_l[-1].rstrip().endswith(".") and not _ACTO_RE.match(resto[0]):
        nombre_l.append(resto.pop(0))
    denominacion = " ".join(nombre_l).strip().rstrip(".").strip()
    registro = re.search(r"\(R\.M\.\s*([^)]*)\)$", denominacion)
    denominacion = re.sub(r"\s*\(R\.M\.[^)]*\)$", "", denominacion).strip()
    cuerpo = re.sub(r"\s+", " ", " ".join(resto)).strip()
    segs = _segmentos(cuerpo)
    tipos_acto = [s[0] for s in segs]

    forma = _forma_juridica(denominacion)
    if "Empresario Individual" in tipos_acto or forma is None:
        return None  # posible persona física: se descarta por diseño

    reg = {
        "numero": numero,
        "denominacion": denominacion,
        "forma_juridica": forma,
        "provincia_codigo": contexto["provincia_codigo"],
        "provincia": nombre_provincia(contexto["provincia_codigo"]),
        "fecha_publicacion": contexto["fecha"],
        "borme_id": contexto["identificador"],
        "url_pdf": contexto["url_pdf"],
        "actos": [a for a in tipos_acto if a != "Datos registrales"],
        "eventos": [],
    }
    for acto, contenido in segs:
        if acto == "Datos registrales":
            reg["hoja_registral"], reg["fecha_inscripcion"] = _registrales(contenido)
            continue
        tipo = TIPO_EVENTO.get(acto)
        ev = {"tipo": tipo or "otro", "acto": acto, "senal": SENAL.get(tipo, "neutra")}
        if acto in CARGOS_ACTOS:
            ev["cargos"] = _cargos(contenido)
        elif acto == "Constitución":
            ev.update(_constitucion(contenido))
            ev["municipio"] = canarias.municipio(ev.get("municipio"), contexto["provincia_codigo"])
        elif tipo == "traslado":
            ev["domicilio"] = contenido
            ev["municipio"] = canarias.municipio(_municipio(contenido), contexto["provincia_codigo"])
        elif tipo in ("ampliacion_capital", "reduccion_capital"):
            imp = re.search(r"(?:Capital|Importe reducción):\s*([\d\.]+,\d{2})", contenido)
            res = re.search(r"Resultante Suscrito:\s*([\d\.]+,\d{2})", contenido)
            ev["importe"] = _num_es(imp.group(1)) if imp else None
            ev["capital_resultante"] = _num_es(res.group(1)) if res else None
        elif tipo == "cambio_denominacion":
            ev["nueva_denominacion"] = contenido
        elif tipo == "cambio_objeto":
            ev["objeto_social"] = contenido
        elif tipo == "pagina_web":
            ev["detalle"] = contenido
        elif tipo in ("disolucion", "transformacion"):
            ev["detalle"] = _detalle_seguro(contenido)
        # concurso, fusión, escisión y "Otros conceptos" pueden citar personas:
        # no se guarda su texto libre.
        reg["eventos"].append(ev)

    const = next((e for e in reg["eventos"] if e["tipo"] == "constitucion"), None)
    if const:
        reg["es_constitucion"] = True
        cargos = next((e["cargos"] for e in reg["eventos"] if e["acto"] == "Nombramientos"), [])
        const["organo_administracion"] = cargos
        const["unipersonal"] = "Declaración de unipersonalidad" in tipos_acto or "Sociedad unipersonal" in tipos_acto
    else:
        reg["es_constitucion"] = False
    return reg


def _constitucion(c: str) -> dict:
    out = {}
    m = re.search(r"Comienzo de operaciones:\s*([\d\.\s]+?)\.?\s+(?=Objeto|Domicilio|Capital|$)", c)
    out["comienzo_operaciones"] = _fecha_corta(m.group(1)) if m else None
    m = re.search(r"Objeto social:\s*(.*?)\s*(?=Domicilio:|Capital:|$)", c, re.S)
    objeto = m.group(1).strip().rstrip(".") if m else None
    out["objeto_social"] = objeto
    m = re.search(r"Domicilio:\s*(.*?)\s*(?=Capital:|$)", c, re.S)
    dom = m.group(1).strip().rstrip(".") if m else None
    out["domicilio"] = dom
    out["municipio"] = _municipio(dom)
    m = re.search(r"Capital:\s*([\d\.]+,\d{2})\s*Euros", c)
    out["capital"] = _num_es(m.group(1)) if m else None
    m = re.search(r"\bC\.?\s?N\.?\s?A\.?\s?E\.?[:\s]*(\d{2,4}(?:\.\d{1,2})?)", c)
    out["cnae"] = m.group(1) if m else None
    sector, todos = sectores.clasifica(objeto or "", out["cnae"])
    out["sector"], out["sectores"] = sector, todos
    return out


def analizar_pdf(pdf: bytes | str, identificador: str, provincia_codigo: str,
                 fecha: str, url_pdf: str = "") -> dict:
    """Analiza un PDF provincial. Devuelve registros y métricas de calidad."""
    texto = pdf_a_texto(pdf)
    entradas = separar_entradas(texto)
    ctx = {"identificador": identificador, "provincia_codigo": provincia_codigo,
           "fecha": fecha, "url_pdf": url_pdf}
    registros, descartadas, individuales, sin_actos = [], 0, 0, 0
    for numero, lineas in entradas:
        r = analizar_entrada(numero, lineas, ctx)
        if r is None:
            descartadas += 1
            if any("Empresario Individual" in l for l in lineas[:3]):
                individuales += 1  # descarte deliberado, no es un fallo de lectura
            continue
        if not r["actos"]:
            sin_actos += 1
        registros.append(r)
    total = len(entradas)
    calidad = {
        "entradas": total,
        "registros": len(registros),
        "descartadas_persona_fisica": descartadas,
        "sin_actos_reconocidos": sin_actos,
        "empresarios_individuales": individuales,
        "porcentaje_reconocido": round(100 * (len(registros) - sin_actos) / (total - individuales), 1)
        if total - individuales > 0 else 100.0,
    }
    return {"registros": registros, "calidad": calidad}


def ficha_publica(r: dict) -> dict:
    """Subconjunto para la web pública (sin domicilio completo)."""
    c = next(e for e in r["eventos"] if e["tipo"] == "constitucion")
    objeto = c.get("objeto_social") or ""
    return {
        "denominacion": r["denominacion"], "forma": r["forma_juridica"],
        "provincia": r["provincia_codigo"], "municipio": c.get("municipio"),
        "sector": c.get("sector"), "capital": c.get("capital"),
        "objeto": (objeto[:140] + "…") if len(objeto) > 140 else objeto,
        "fecha": r["fecha_publicacion"], "borme": r["borme_id"],
    }
