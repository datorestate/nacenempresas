"""Ocultación parcial de datos para la prueba gratuita y la web pública.

nombre_parcial("CONSTRUCCIONES GARCIA PEREZ SL") -> "CONSTRUCCIONES G••• P••• SL"
nombre_parcial("ACMETECH SL")                    -> "ACM••• SL"

Se deja ver el tipo de negocio (primera palabra) y la forma jurídica, pero no el nombre
completo: sirve de muestra sin poder usarse para contactar con la sociedad.
"""
import re

PUNTOS = "•••"
_SUFIJO = re.compile(
    r"^(S\.?L\.?(U|L|P|NE)?\.?|S\.?A\.?U?\.?|S\.?COOP\.?|SCOOP|SAT|SOCIEDAD|LIMITADA|AN[OÓ]NIMA|"
    r"UNIPERSONAL|PROFESIONAL|LABORAL|COOPERATIVA|NUEVA|EMPRESA|EN|LIQUIDACION|LIQUIDACIÓN)$", re.I)
_CORTA = re.compile(r"^(DE|DEL|LA|LAS|EL|LOS|Y|E|&|-|\d{1,2})$", re.I)


def nombre_parcial(nombre: str) -> str:
    palabras = (nombre or "").split()
    if not palabras:
        return nombre or ""
    fin = len(palabras)
    while fin > 1 and _SUFIJO.match(palabras[fin - 1]):
        fin -= 1
    cuerpo, sufijo = palabras[:fin], palabras[fin:]
    if len(cuerpo) == 1:
        p = cuerpo[0]
        visibles = [p[:3] + PUNTOS if len(p) > 3 else p[:1] + PUNTOS]
    else:
        visibles = [cuerpo[0]] + [p if _CORTA.match(p) else p[:1] + PUNTOS for p in cuerpo[1:]]
    return " ".join(visibles + sufijo)


def recortar_texto(texto: str, n: int = 110) -> str:
    texto = texto or ""
    return texto if len(texto) <= n else texto[:n].rsplit(" ", 1)[0] + "…"
