"""Ocultación parcial de datos para la prueba gratuita y la web pública.

nombre_parcial("CONSTRUCCIONES GARCIA PEREZ SL") -> "CON••• G••• P••• SL"
nombre_parcial("TERRITORIO 7 SL")                -> "TER••• ••• SL"

Solo se ven las iniciales y la forma jurídica: sirve de muestra (la actividad y el municipio
van aparte) sin poder usarse para localizar ni contactar con la sociedad.
"""
import re

PUNTOS = "•••"
_SUFIJO = re.compile(
    r"^(S\.?L\.?(U|L|P|NE)?\.?|S\.?A\.?U?\.?|S\.?COOP\.?|SCOOP|SAT|SOCIEDAD|LIMITADA|AN[OÓ]NIMA|"
    r"UNIPERSONAL|PROFESIONAL|LABORAL|COOPERATIVA|NUEVA|EMPRESA|EN|LIQUIDACION|LIQUIDACIÓN)$", re.I)
_CONECTOR = re.compile(r"^(DE|DEL|LA|LAS|EL|LOS|Y|E|&|-)$", re.I)


def _palabra(p: str, letras: int) -> str:
    if _CONECTOR.match(p):
        return p
    if not p[:1].isalpha():
        return PUNTOS
    return (p[:letras] if len(p) > letras else p[:1]) + PUNTOS


def nombre_parcial(nombre: str) -> str:
    palabras = (nombre or "").split()
    if not palabras:
        return nombre or ""
    fin = len(palabras)
    while fin > 1 and _SUFIJO.match(palabras[fin - 1]):
        fin -= 1
    cuerpo, sufijo = palabras[:fin], palabras[fin:]
    visibles = [_palabra(cuerpo[0], 3)] + [_palabra(p, 1) for p in cuerpo[1:]]
    return " ".join(visibles + sufijo)


def recortar_texto(texto: str, n: int = 110) -> str:
    texto = texto or ""
    return texto if len(texto) <= n else texto[:n].rsplit(" ", 1)[0] + "…"
