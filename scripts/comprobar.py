"""Comprobación de que todo está listo para vender (sin enviar nada ni cobrar nada).

- Clientes manuales (SUSCRIPTORES_MANUAL) y de Stripe: cuántos hay y en qué estado.
- Enlaces de pago de Stripe: activos, con prueba de N días y forma de pago obligatoria.
- Datos: último BORME guardado y avisos enviados.

Uso: python scripts/comprobar.py   (en GitHub: Actions > "Comprobar puesta a la venta")
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nacenempresas import almacen, suscriptores  # noqa: E402
from nacenempresas.config import sitio  # noqa: E402
from nacenempresas.stripe_api import Stripe  # noqa: E402

errores, lineas = [], []


def ok(texto):
    lineas.append(f"- ✅ {texto}")


def mal(texto):
    lineas.append(f"- ❌ {texto}")
    errores.append(texto)


def oculta(email):
    u, _, d = email.partition("@")
    return f"{u[:2]}***@{d}"


cfg = sitio()
dias_prueba = cfg["precios"]["dias_prueba"]

# 1. Clientes manuales
try:
    man = suscriptores.manuales()
    if not man:
        lineas.append("- ℹ️ Sin clientes manuales (SUSCRIPTORES_MANUAL vacío)")
    for s in man:
        if s.provincias:
            ok(f"Cliente manual {s.id}: {oculta(s.email)}, plan {s.plan}, estado {s.estado}, "
               f"provincias {', '.join(s.provincias)}, {s.frecuencia}")
        else:
            mal(f"Cliente manual {s.id}: no se reconoce ninguna provincia")
except Exception as e:  # JSON mal escrito
    mal(f"SUSCRIPTORES_MANUAL no se puede leer: {e}")

# 2. Stripe
st = None
if os.environ.get("STRIPE_SECRET_KEY"):
    st = Stripe()
    enlaces = json.loads((RAIZ / "config" / "stripe.json").read_text("utf-8"))
    modo = enlaces.get("modo")
    (ok if modo == "live" else mal)(f"Stripe en modo {modo}")
    vistos = {}
    for pl in st.listar("payment_links", active="true"):
        vistos[pl["url"]] = pl
    for clave in ["basico_mes", "basico_anio", "pro_mes", "pro_anio", "lista"]:
        url = enlaces.get(clave, "").split("?")[0]
        pl = vistos.get(url)
        if not pl:
            mal(f"Enlace {clave}: no está activo en Stripe")
            continue
        if clave == "lista":
            ok(f"Enlace {clave}: activo")
            continue
        sd = pl.get("subscription_data") or {}
        dias = sd.get("trial_period_days")
        cobro = pl.get("payment_method_collection")
        if dias == dias_prueba and cobro == "always":
            ok(f"Enlace {clave}: activo, {dias} días de prueba, tarjeta obligatoria")
        else:
            mal(f"Enlace {clave}: prueba {dias} días, forma de pago {cobro} (se esperaba {dias_prueba} y always)")
    try:
        subs = suscriptores.desde_stripe(st)
        act = sum(s.estado == "active" for s in subs)
        pru = sum(s.estado == "trialing" for s in subs)
        ok(f"Clientes en Stripe: {act} de pago y {pru} en prueba")
    except Exception as e:
        mal(f"No se pueden leer las suscripciones de Stripe: {e}")
else:
    mal("Falta STRIPE_SECRET_KEY")

# 3. Correo
for v in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "FROM_EMAIL", "OWNER_EMAIL"]:
    if not os.environ.get(v):
        mal(f"Falta el secreto {v}")
if not any("secreto" in e for e in errores):
    ok("Secretos de correo presentes")

# 4. Datos
dias = almacen.dias_disponibles()
if dias:
    ultimo = almacen.cargar_publico(dias[-1])
    ok(f"Último BORME guardado: {dias[-1]} ({ultimo.get('total_constituciones', 0)} constituciones); "
       f"{len(dias)} días en total")
else:
    mal("No hay días de BORME guardados")
enviados = sorted(p.name.replace("enviado-", "") for p in (almacen.RAIZ / "publico").glob("enviado-*"))
if enviados:
    ok(f"Últimos avisos enviados: {', '.join(enviados[-3:])}")

texto = "## Comprobación de puesta a la venta\n\n" + "\n".join(lineas) + \
    ("\n\n**Todo correcto.**" if not errores else f"\n\n**{len(errores)} problema(s).**") + "\n"
print(texto)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write(texto)
sys.exit(1 if errores else 0)
