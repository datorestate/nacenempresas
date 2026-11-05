"""Fiscalidad de un prestador establecido en Canarias que vende a empresas.

Reglas aplicadas (confírmalas con tu gestoría; revisión 5/11/2026):
- Cliente empresario en la Península o Baleares: servicio localizado donde está el
  destinatario (art. 69.Uno.1.º LIVA). No sujeto al IGIC; el IVA lo autoliquida el
  cliente por inversión del sujeto pasivo (art. 84.Uno.2.º LIVA). Factura sin cuota.
- Cliente empresario en Canarias: IGIC al tipo general (7 %), salvo que el prestador
  esté en el régimen especial del pequeño empresario o profesional (hasta 50.000 €).
- Ceuta, Melilla y extranjero: no sujeto al IGIC.
- Solo se vende a empresas y profesionales (NIF obligatorio en el pago): así se evitan
  las reglas especiales de los servicios electrónicos a particulares.
"""
from __future__ import annotations

from . import config

NO_SUJETO_IGIC = "Operación no sujeta al IGIC (art. 17 de la Ley 20/1991, de 7 de junio)."
INVERSION = ("Inversión del sujeto pasivo: el IVA corresponde al destinatario "
             "(arts. 69.Uno.1.º y 84.Uno.2.º de la Ley 37/1992).")
REPEP = ("Operación exenta del IGIC por aplicación del régimen especial del pequeño "
         "empresario o profesional.")
PRESTADOR = "Prestador establecido en Canarias."


def region(pais: str | None, cp: str | None) -> str:
    """'canarias' | 'peninsula' | 'ceuta_melilla' | 'extranjero' | 'desconocida'."""
    pais = (pais or "").upper()
    cp = (cp or "").strip()
    if pais == "IC" or (pais == "ES" and cp[:2] in ("35", "38")):
        return "canarias"
    if pais == "EA" or (pais == "ES" and cp[:2] in ("51", "52")):
        return "ceuta_melilla"
    if pais == "ES":
        return "peninsula" if cp else "desconocida"
    return "extranjero" if pais else "desconocida"


def aplica_igic(reg: str, cfg: dict | None = None) -> bool:
    cfg = cfg or config.sitio()
    return reg == "canarias" and not cfg["fiscal"]["igic_pequeno_empresario"]


def pie_factura(reg: str, cfg: dict | None = None) -> str:
    cfg = cfg or config.sitio()
    repep = cfg["fiscal"]["igic_pequeno_empresario"]
    if reg == "canarias":
        return REPEP if repep else ""
    if reg == "peninsula":
        return f"{PRESTADOR} {NO_SUJETO_IGIC} {INVERSION}"
    if reg in ("ceuta_melilla", "extranjero"):
        return f"{PRESTADOR} {NO_SUJETO_IGIC}"
    return pie_generico(cfg)


def pie_generico(cfg: dict | None = None) -> str:
    """Para pagos únicos, cuando aún no se sabe dónde está el cliente."""
    cfg = cfg or config.sitio()
    texto = (f"{PRESTADOR} Clientes de la Península y Baleares: {NO_SUJETO_IGIC[0].lower()}"
             f"{NO_SUJETO_IGIC[1:]} {INVERSION}")
    if cfg["fiscal"]["igic_pequeno_empresario"]:
        texto += f" Clientes de Canarias: {REPEP[0].lower()}{REPEP[1:]}"
    return texto


def nota_precios(cfg: dict | None = None) -> str:
    """Texto breve para la web bajo las tarifas."""
    cfg = cfg or config.sitio()
    t = ("Precios finales, solo para empresas y profesionales. Facturamos desde Canarias: si tu empresa "
         "está en la Península o Baleares, la factura no lleva IVA ni IGIC y el IVA lo autoliquidas tú por "
         "inversión del sujeto pasivo, así que tu coste neto es el precio indicado.")
    if cfg["fiscal"]["igic_pequeno_empresario"]:
        t += " En Canarias, la operación está exenta de IGIC."
    else:
        t += f" En Canarias se añade el IGIC ({cfg['fiscal']['igic_tipo']} %)."
    return t
