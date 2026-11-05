"""Cliente mínimo de la API de Stripe (sin dependencias extra)."""
from __future__ import annotations

import os

import requests

API = "https://api.stripe.com/v1"


class StripeError(RuntimeError):
    pass


def _aplanar(datos, prefijo=""):
    """{'a': {'b': [1, 2]}} -> [('a[b][0]', 1), ('a[b][1]', 2)] (codificación de Stripe)."""
    pares = []
    if isinstance(datos, dict):
        for k, v in datos.items():
            pares += _aplanar(v, f"{prefijo}[{k}]" if prefijo else k)
    elif isinstance(datos, (list, tuple)):
        for i, v in enumerate(datos):
            pares += _aplanar(v, f"{prefijo}[{i}]")
    elif isinstance(datos, bool):
        pares.append((prefijo, "true" if datos else "false"))
    elif datos is not None:
        pares.append((prefijo, str(datos)))
    return pares


class Stripe:
    def __init__(self, clave: str | None = None):
        self.clave = clave or os.environ.get("STRIPE_SECRET_KEY")
        if not self.clave:
            raise StripeError("Falta STRIPE_SECRET_KEY")
        self.s = requests.Session()
        self.s.auth = (self.clave, "")
        self.s.headers["Stripe-Version"] = os.environ.get("STRIPE_API_VERSION", "2024-09-30.acacia")

    def _r(self, metodo, ruta, datos=None):
        if metodo == "GET":
            r = self.s.get(f"{API}/{ruta}", params=_aplanar(datos or {}), timeout=60)
        else:
            r = self.s.post(f"{API}/{ruta}", data=_aplanar(datos or {}), timeout=60)
        if r.status_code >= 400:
            raise StripeError(f"{metodo} {ruta}: {r.status_code} {r.text[:500]}")
        return r.json()

    def get(self, ruta, **params):
        return self._r("GET", ruta, params)

    def post(self, ruta, datos=None):
        return self._r("POST", ruta, datos)

    def listar(self, ruta, **params):
        """Itera por todas las páginas de un listado."""
        params.setdefault("limit", 100)
        while True:
            pag = self.get(ruta, **params)
            for obj in pag.get("data", []):
                yield obj
            if not pag.get("has_more") or not pag.get("data"):
                break
            params["starting_after"] = pag["data"][-1]["id"]
