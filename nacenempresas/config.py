import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def sitio() -> dict:
    c = json.loads((RAIZ / "config" / "sitio.json").read_text("utf-8"))
    if os.environ.get("SITE_URL"):
        c["url_base"] = os.environ["SITE_URL"].rstrip("/")
    c["vista_previa"] = os.environ.get("RC_VISTA_PREVIA") == "1"
    return c


def stripe_links() -> dict:
    """Enlaces de pago creados por scripts/setup_stripe.py (son públicos)."""
    p = RAIZ / "config" / "stripe.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else {}
