"""Lista de clientes a partir de Stripe (fuente única de verdad, sin base de datos).

Cada alta llega por un Payment Link con campos personalizados:
  provincia / provincias  -> provincias a vigilar
  actividad               -> sectores o palabras clave (opcional)
  frecuencia              -> diaria | semanal
Se pueden añadir clientes "manuales" (pilotos, altas por teléfono) con el secreto
SUSCRIPTORES_MANUAL, un JSON con la misma forma que `Suscriptor`.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field

from . import sectores
from .provincias import codigo_provincia, lista_provincias, normaliza

LIMITE_PROVINCIAS = {"basico": 1, "pro": 5, "lista": 1}


@dataclass
class Suscriptor:
    id: str
    email: str
    plan: str                      # basico | pro
    estado: str = "active"         # active | trialing
    nombre: str = ""
    provincias: list = field(default_factory=list)
    sectores: list = field(default_factory=list)
    palabras: list = field(default_factory=list)
    frecuencia: str = "diaria"
    fin_prueba: int | None = None  # timestamp
    tiene_pago: bool = True
    bienvenida_enviada: bool = False
    customer: str | None = None
    pais: str = ""                 # país de facturación (ES, IC...)
    cp: str = ""                   # código postal de facturación

    @property
    def con_csv(self):
        return self.plan == "pro"

    @property
    def con_eventos(self):
        return self.plan == "pro"


def interpreta_actividad(texto: str):
    """'Hostelería, reformas' -> (['hosteleria'], ['reformas'])."""
    secs, palabras = [], []
    nombres = {normaliza(v): k for k, v in sectores.todos()}
    nombres.update({k: k for k, _ in sectores.todos()})
    for t in re.split(r"[,;\n]| y ", texto or ""):
        t = normaliza(t)
        if len(t) < 3:
            continue
        clave = nombres.get(t) or next((k for n, k in nombres.items() if t in n.split(" ")), None)
        if clave and clave not in secs:
            secs.append(clave)
        elif t not in palabras:
            palabras.append(t)
    return secs, palabras


CANARIAS = ["35", "38"]


def provincias_de_campo(texto: str, plan: str) -> list[str]:
    """'p29' -> ['29']; 'pCN' o 'Canarias' -> ['35', '38'] (cuenta como una provincia)."""
    t = (texto or "").strip()
    if t in ("pCN", "CN") or normaliza(t) in ("canarias", "islas canarias"):
        return list(CANARIAS)
    if plan == "basico":
        c = codigo_provincia(t[1:] if t.startswith("p") and t[1:].isdigit() else t)
        return [c] if c else []
    provs = []
    for c in lista_provincias(texto.replace("Canarias", "Las Palmas, Santa Cruz de Tenerife"), 52):
        if c not in provs:
            provs.append(c)
    limite = LIMITE_PROVINCIAS.get(plan, 5) + (1 if set(CANARIAS) <= set(provs) else 0)
    return provs[:limite]


def _direccion(cust: dict, sesion: dict) -> dict:
    d = cust.get("address") or (sesion.get("customer_details") or {}).get("address") or {}
    return {"pais": (d.get("country") or "").upper(), "cp": d.get("postal_code") or ""}


def _campos(session):
    out = {}
    for cf in session.get("custom_fields") or []:
        v = (cf.get("dropdown") or {}).get("value") or (cf.get("text") or {}).get("value") \
            or (cf.get("numeric") or {}).get("value")
        out[cf["key"]] = v or ""
    return out


def desde_stripe(st) -> list[Suscriptor]:
    subs = []
    for estado in ("active", "trialing"):
        for s in st.listar("subscriptions", status=estado, **{"expand[]": "data.customer"}):
            precio = s["items"]["data"][0]["price"]
            plan = (precio.get("metadata") or {}).get("rc_plan")
            if plan not in ("basico", "pro"):
                # Suscripción de otra actividad de la misma cuenta de Stripe: no se toca
                continue
            cust = s["customer"] if isinstance(s["customer"], dict) else {"id": s["customer"]}
            sesiones = st.get("checkout/sessions", subscription=s["id"], limit=1).get("data", [])
            campos = _campos(sesiones[0]) if sesiones else {}
            email = cust.get("email") or (sesiones[0].get("customer_details") or {}).get("email") if sesiones else cust.get("email")
            prov_txt = campos.get("provincia") or campos.get("provincias") or ""
            provs = provincias_de_campo(prov_txt, plan)
            secs, palabras = interpreta_actividad(campos.get("actividad", ""))
            tiene_pago = bool(s.get("default_payment_method") or
                              ((cust.get("invoice_settings") or {}).get("default_payment_method")))
            subs.append(Suscriptor(
                id=s["id"], email=email or "", plan=plan, estado=estado,
                nombre=(cust.get("name") or ""), provincias=provs, sectores=secs,
                palabras=palabras, frecuencia=(campos.get("frecuencia") or "diaria").lower(),
                fin_prueba=s.get("trial_end"), tiene_pago=tiene_pago,
                bienvenida_enviada=(s.get("metadata") or {}).get("rc_bienvenida") == "1",
                customer=cust.get("id"), **_direccion(cust, sesiones[0] if sesiones else {})))
    return subs


def manuales() -> list[Suscriptor]:
    bruto = os.environ.get("SUSCRIPTORES_MANUAL", "").strip()
    if not bruto:
        return []
    out = []
    for i, d in enumerate(json.loads(bruto)):
        provs = d.get("provincias") or []
        txt = ",".join(provs) if isinstance(provs, list) else provs
        provs = lista_provincias(txt.replace("Canarias", "Las Palmas, Santa Cruz de Tenerife"), 52)
        secs, pal = interpreta_actividad(d.get("actividad", ""))
        out.append(Suscriptor(
            id=d.get("id", f"manual-{i}"), email=d["email"], plan=d.get("plan", "pro"),
            estado=d.get("estado", "active"), nombre=d.get("nombre", ""), provincias=provs,
            sectores=d.get("sectores", secs), palabras=d.get("palabras", pal),
            frecuencia=d.get("frecuencia", "diaria"), bienvenida_enviada=True))
    return out


def todos(st=None) -> list[Suscriptor]:
    lista = manuales()
    if st is not None:
        lista += desde_stripe(st)
    return [s for s in lista if s.email and s.provincias]


def a_json(subs):
    return json.dumps([asdict(s) for s in subs], ensure_ascii=False, indent=1)
