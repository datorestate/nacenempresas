"""Crea en Stripe todo lo necesario para cobrar, en una sola ejecución (idempotente).

- Productos y precios: Básico (1 provincia), Pro (hasta 5 provincias + CSV + señales),
  mensual y anual, y la Lista puntual (pago único, 30 días de una provincia).
- Prestador en Canarias: precios sin impuestos indirectos (tax_behavior exclusive) y un
  tipo de IGIC (7 %) que solo se aplica a clientes canarios si dejas el régimen del
  pequeño empresario (ver nacenempresas/fiscal.py).
- Payment Links con prueba de 7 días CON tarjeta (se cobra el día 8 si no se cancela;
  durante la prueba los avisos van recortados, ver avisos.py), campos para provincia
  (incluida "Canarias", las dos provincias), actividad y frecuencia, y NIF/CIF
  obligatorio: solo se vende a empresas y profesionales.
- Portal del cliente con página de acceso por email (baja, tarjeta, facturas).

Resultado: config/stripe.json con los enlaces (son públicos) que usa la web.

Uso (desde GitHub Actions, workflow "Configurar Stripe", o en local):
    STRIPE_SECRET_KEY=sk_live_... python scripts/setup_stripe.py
Empieza con una clave sk_test_ para probarlo todo sin cobrar.
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nacenempresas import fiscal  # noqa: E402
from nacenempresas.config import sitio  # noqa: E402
from nacenempresas.provincias import PROVINCIAS  # noqa: E402
from nacenempresas.stripe_api import Stripe, StripeError  # noqa: E402


def centimos(euros):
    return round(euros * 100)


def buscar_o_crear_producto(st, clave, nombre, descripcion):
    for p in st.listar("products", active="true"):
        if (p.get("metadata") or {}).get("rc_producto") == clave:
            return p
    return st.post("products", {"name": nombre, "description": descripcion,
                                "metadata": {"rc_producto": clave}})


def buscar_o_crear_precio(st, producto, clave, importe, intervalo=None, plan=None):
    for pr in st.listar("prices", product=producto["id"], active="true"):
        if (pr.get("metadata") or {}).get("rc_precio") == clave and pr["unit_amount"] == importe:
            return pr
    datos = {"product": producto["id"], "currency": "eur", "unit_amount": importe,
             "tax_behavior": "exclusive", "metadata": {"rc_precio": clave, "rc_plan": plan or clave}}
    if intervalo:
        datos["recurring"] = {"interval": intervalo}
    return st.post("prices", datos)


def tipo_igic(st, igic):
    """IGIC (Canarias). Solo se aplica a clientes canarios fuera del régimen del pequeño empresario."""
    for t in st.listar("tax_rates", active="true"):
        if (t.get("metadata") or {}).get("rc") == "igic" and float(t["percentage"]) == float(igic):
            return t
    return st.post("tax_rates", {"display_name": "IGIC", "percentage": igic, "inclusive": False,
                                 "jurisdiction": "Canarias", "description": "Impuesto General Indirecto Canario",
                                 "metadata": {"rc": "igic"}})


def campo_provincia_desplegable():
    opciones = [{"label": "Canarias (Las Palmas y Santa Cruz de Tenerife)", "value": "pCN"}] + \
        [{"label": n[:100], "value": f"p{c}"} for c, n in sorted(PROVINCIAS.items(), key=lambda kv: kv[1])]
    return {"key": "provincia", "type": "dropdown",
            "label": {"type": "custom", "custom": "Provincia"},
            "dropdown": {"options": opciones}}


CAMPO_ACTIVIDAD = {"key": "actividad", "type": "text", "optional": True,
                   "label": {"type": "custom", "custom": "Actividades o palabras clave (opcional)"}}
CAMPO_FRECUENCIA = {"key": "frecuencia", "type": "dropdown",
                    "label": {"type": "custom", "custom": "Frecuencia del aviso"},
                    "dropdown": {"options": [{"label": "Cada mañana laborable", "value": "diaria"},
                                             {"label": "Resumen los lunes", "value": "semanal"}]}}
CAMPO_PROVINCIAS_PRO = {"key": "provincias", "type": "text",
                        "label": {"type": "custom", "custom": "Provincias (hasta 5, separadas por comas)"}}


def datos_prueba(cfg, clave):
    """Prueba con tarjeta obligatoria: al terminar se cobra sola si el cliente no cancela."""
    return {"subscription_data": {
                "trial_period_days": cfg["precios"]["dias_prueba"],
                "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}},
                "metadata": {"rc_link": clave}},
            "payment_method_collection": "always"}


def _necesita_actualizar(pl, deseado):
    sd = pl.get("subscription_data") or {}
    return (pl.get("payment_method_collection") != deseado["payment_method_collection"] or
            sd.get("trial_period_days") != deseado["subscription_data"]["trial_period_days"])


def enlace(st, precio, campos, cfg, suscripcion=True, clave=""):
    for pl in st.listar("payment_links", active="true"):
        if (pl.get("metadata") or {}).get("rc_link") == clave:
            if suscripcion and _necesita_actualizar(pl, datos_prueba(cfg, clave)):
                # Se actualiza el enlace existente: la URL (web, QR, cartas) no cambia
                try:
                    return st.post(f"payment_links/{pl['id']}", datos_prueba(cfg, clave))
                except StripeError as e:
                    print(f"No se pudo actualizar {clave} ({e}); se desactiva y se crea uno nuevo")
                    st.post(f"payment_links/{pl['id']}", {"active": False})
                    break
            else:
                return pl
    datos = {
        "line_items": [{"price": precio["id"], "quantity": 1}],
        "custom_fields": campos,
        # NIF/CIF obligatorio (y razón social): solo empresas y profesionales
        "tax_id_collection": {"enabled": True, "required": "if_supported"},
        "custom_text": {"submit": {"message": fiscal.nota_precios(cfg)}},
        "allow_promotion_codes": True,
        "billing_address_collection": "required",
        "after_completion": {"type": "redirect",
                             "redirect": {"url": cfg["url_base"] + "/gracias.html"}},
        "metadata": {"rc_link": clave},
    }
    if suscripcion:
        datos.update(datos_prueba(cfg, clave))
    else:
        datos["invoice_creation"] = {"enabled": True,
                                     "invoice_data": {"footer": fiscal.pie_generico(cfg)}}
    return st.post("payment_links", datos)


def portal(st, cfg):
    for c in st.listar("billing_portal/configurations", active="true"):
        if (c.get("metadata") or {}).get("rc") == "portal":
            return c
    return st.post("billing_portal/configurations", {
        "business_profile": {"headline": f"{cfg['nombre']}: gestiona tu suscripción",
                             "privacy_policy_url": cfg["url_base"] + "/privacidad.html",
                             "terms_of_service_url": cfg["url_base"] + "/condiciones.html"},
        "features": {"invoice_history": {"enabled": True},
                     "payment_method_update": {"enabled": True},
                     "customer_update": {"enabled": True, "allowed_updates": ["email", "tax_id", "address", "name"]},
                     "subscription_cancel": {"enabled": True, "mode": "at_period_end"}},
        "login_page": {"enabled": True},
        "default_return_url": cfg["url_base"],
        "metadata": {"rc": "portal"},
    })


def main():
    cfg = sitio()
    if "TU-USUARIO" in cfg["url_base"] and not os.environ.get("SITE_URL"):
        sys.exit("Define SITE_URL (la URL de tu web) o edita config/sitio.json antes de crear los enlaces.")
    st = Stripe()
    p = cfg["precios"]
    prod_b = buscar_o_crear_producto(st, "basico", "Avisos de empresas nuevas · Básico",
                                     "1 provincia, filtro por actividad, aviso diario o semanal.")
    prod_p = buscar_o_crear_producto(st, "pro", "Avisos de empresas nuevas · Pro",
                                     "Hasta 5 provincias, CSV para Excel/CRM y señales (traslados, ampliaciones, disoluciones).")
    prod_l = buscar_o_crear_producto(st, "lista", "Lista de empresas nuevas (30 días)",
                                     "CSV con las sociedades constituidas en los últimos 30 días en una provincia.")
    precios = {
        "basico_mes": buscar_o_crear_precio(st, prod_b, "basico_mes", centimos(p["basico_mes"]), "month", "basico"),
        "basico_anio": buscar_o_crear_precio(st, prod_b, "basico_anio", centimos(p["basico_anio"]), "year", "basico"),
        "pro_mes": buscar_o_crear_precio(st, prod_p, "pro_mes", centimos(p["pro_mes"]), "month", "pro"),
        "pro_anio": buscar_o_crear_precio(st, prod_p, "pro_anio", centimos(p["pro_anio"]), "year", "pro"),
        "lista": buscar_o_crear_precio(st, prod_l, "lista", centimos(p["lista"]), None, "lista"),
    }
    tasa = tipo_igic(st, cfg["fiscal"]["igic_tipo"])
    prov = campo_provincia_desplegable()
    links = {
        "basico_mes": enlace(st, precios["basico_mes"], [prov, CAMPO_ACTIVIDAD, CAMPO_FRECUENCIA], cfg, True, "basico_mes"),
        "basico_anio": enlace(st, precios["basico_anio"], [prov, CAMPO_ACTIVIDAD, CAMPO_FRECUENCIA], cfg, True, "basico_anio"),
        "pro_mes": enlace(st, precios["pro_mes"], [CAMPO_PROVINCIAS_PRO, CAMPO_ACTIVIDAD, CAMPO_FRECUENCIA], cfg, True, "pro_mes"),
        "pro_anio": enlace(st, precios["pro_anio"], [CAMPO_PROVINCIAS_PRO, CAMPO_ACTIVIDAD, CAMPO_FRECUENCIA], cfg, True, "pro_anio"),
        "lista": enlace(st, precios["lista"], [prov, CAMPO_ACTIVIDAD], cfg, False, "lista"),
    }
    port = portal(st, cfg)
    salida = {k: v["url"] + "?locale=es" for k, v in links.items()}
    salida["lista_id"] = links["lista"]["id"]
    salida["portal"] = (port.get("login_page") or {}).get("url") or cfg["url_base"]
    salida["igic_tax_rate"] = tasa["id"]
    salida["modo"] = "test" if st.clave.startswith(("sk_test", "rk_test")) else "live"
    (RAIZ / "config" / "stripe.json").write_text(json.dumps(salida, indent=2), "utf-8")
    print(json.dumps(salida, indent=2))
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with open(ruta, "a") as f:
            f.write("## Stripe configurado\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in salida.items()) +
                    "\n\nRevisa en Stripe > Ajustes > Datos públicos y Facturas que figuran tu NIF y tu domicilio en Canarias.\n")


if __name__ == "__main__":
    main()
