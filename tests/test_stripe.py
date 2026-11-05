"""Stripe simulado: alta de productos/enlaces y lectura de suscriptores."""
import importlib
import json
import sys
from pathlib import Path

from nacenempresas.stripe_api import _aplanar

RAIZ = Path(__file__).resolve().parent.parent


class FakeStripe:
    def __init__(self, *a, **k):
        self.clave = "sk_test_x"
        self.objetos = {}
        self.posts = []

    def listar(self, ruta, **p):
        return iter(self.objetos.get(ruta, []))

    def get(self, ruta, **p):
        if ruta == "checkout/sessions":
            return {"data": [{"custom_fields": [
                {"key": "provincias", "text": {"value": "Málaga, Sevilla"}},
                {"key": "actividad", "text": {"value": "Hostelería, reformas"}},
                {"key": "frecuencia", "dropdown": {"value": "semanal"}}],
                "customer_details": {"email": "cliente@example.com"}}]}
        return {}

    def post(self, ruta, datos=None):
        self.posts.append((ruta, datos))
        n = len(self.posts)
        obj = {"id": f"{ruta.split('/')[-1]}_{n}", "url": f"https://buy.stripe.com/test_{n}",
               "unit_amount": (datos or {}).get("unit_amount"), "percentage": (datos or {}).get("percentage"),
               "metadata": (datos or {}).get("metadata", {})}
        if ruta == "billing_portal/configurations":
            obj["login_page"] = {"url": "https://billing.stripe.com/p/login/test"}
        return obj


def test_aplanar():
    assert _aplanar({"a": {"b": [1, {"c": True}]}}) == [("a[b][0]", "1"), ("a[b][1][c]", "true")]


def test_setup_stripe(monkeypatch, tmp_path):
    monkeypatch.setenv("SITE_URL", "https://demo.github.io/nacenempresas")
    sys.path.insert(0, str(RAIZ / "scripts"))
    import setup_stripe
    importlib.reload(setup_stripe)
    fake = FakeStripe()
    monkeypatch.setattr(setup_stripe, "Stripe", lambda: fake)
    monkeypatch.setattr(setup_stripe, "RAIZ", tmp_path)
    (tmp_path / "config").mkdir()
    setup_stripe.main()
    salida = json.loads((tmp_path / "config" / "stripe.json").read_text())
    assert salida["portal"].startswith("https://billing.stripe.com")
    assert salida["modo"] == "test"
    # Prestador en Canarias: precios sin impuestos indirectos
    precios = {d["metadata"]["rc_precio"]: (d["unit_amount"], d["tax_behavior"]) for r, d in fake.posts if r == "prices"}
    assert precios == {"basico_mes": (1900, "exclusive"), "basico_anio": (19000, "exclusive"),
                       "pro_mes": (4900, "exclusive"), "pro_anio": (49000, "exclusive"), "lista": (2900, "exclusive")}
    igic = next(d for r, d in fake.posts if r == "tax_rates")
    assert igic["display_name"] == "IGIC" and igic["percentage"] == 7 and igic["inclusive"] is False
    assert salida["igic_tax_rate"] and salida["basico_mes"].endswith("?locale=es")
    links = [d for r, d in fake.posts if r == "payment_links"]
    sub = next(d for d in links if d["metadata"]["rc_link"] == "basico_mes")
    assert sub["payment_method_collection"] == "always"  # prueba con tarjeta
    assert sub["subscription_data"]["trial_period_days"] == 7
    opciones = sub["custom_fields"][0]["dropdown"]["options"]
    assert len(opciones) == 53 and opciones[0]["value"] == "pCN"
    assert len(sub["custom_fields"]) <= 3
    assert sub["tax_id_collection"] == {"enabled": True, "required": "if_supported"}
    assert "inversión del sujeto pasivo" in sub["custom_text"]["submit"]["message"]
    assert "name_collection" not in sub
    lista = next(d for d in links if d["metadata"]["rc_link"] == "lista")
    assert "subscription_data" not in lista and lista["invoice_creation"]["enabled"]
    assert "84.Uno.2.º" in lista["invoice_creation"]["invoice_data"]["footer"]


def test_suscriptores_desde_stripe():
    from nacenempresas import suscriptores
    fake = FakeStripe()
    fake.objetos["subscriptions"] = [{
        "id": "sub_1", "items": {"data": [{"price": {"metadata": {"rc_plan": "pro"}}}]},
        "customer": {"id": "cus_1", "email": "cliente@example.com", "name": "Gestoría Sur SL",
                     "invoice_settings": {}, "address": {"country": "ES", "postal_code": "29001"}},
        "trial_end": 1, "metadata": {}}]
    subs = suscriptores.desde_stripe(fake)
    s = subs[0]  # aparece en active y trialing del fake; basta con el primero
    assert s.plan == "pro" and s.provincias == ["29", "41"]
    assert s.sectores == ["hosteleria", "construccion"] and s.palabras == []  # "reformas" -> Construcción y reformas
    assert s.frecuencia == "semanal" and not s.tiene_pago and not s.bienvenida_enviada
    assert (s.pais, s.cp) == ("ES", "29001")


def test_region_y_factura(monkeypatch):
    from nacenempresas import avisos, config, fiscal, suscriptores
    assert fiscal.region("ES", "35001") == "canarias" and fiscal.region("IC", "") == "canarias"
    assert fiscal.region("ES", "38500") == "canarias" and fiscal.region("ES", "28001") == "peninsula"
    assert fiscal.region("ES", "07001") == "peninsula" and fiscal.region("ES", "51001") == "ceuta_melilla"
    assert fiscal.region("PT", "1000") == "extranjero"
    cfg = config.sitio()
    assert cfg["fiscal"]["igic_pequeno_empresario"] is True
    assert "inversión del sujeto pasivo" in fiscal.pie_factura("peninsula", cfg).lower()
    assert "pequeño empresario" in fiscal.pie_factura("canarias", cfg)
    assert not fiscal.aplica_igic("canarias", cfg)
    # Cliente canario, titular en el régimen del pequeño empresario: sin IGIC
    fake = FakeStripe()
    sub = suscriptores.Suscriptor(id="sub_9", email="a@b.es", plan="basico", customer="cus_9", pais="ES", cp="35002")
    assert avisos.configurar_factura(fake, sub, cfg) == "canarias"
    s_upd = dict(fake.posts)["subscriptions/sub_9"]
    assert "default_tax_rates" not in s_upd and s_upd["metadata"]["rc_region"] == "canarias"
    # Fuera del régimen: IGIC al cliente canario, nunca al peninsular
    cfg2 = {**cfg, "fiscal": {**cfg["fiscal"], "igic_pequeno_empresario": False}}
    monkeypatch.setenv("STRIPE_TAX_RATE", "txr_igic")
    fake = FakeStripe()
    avisos.configurar_factura(fake, sub, cfg2)
    assert dict(fake.posts)["subscriptions/sub_9"]["default_tax_rates"] == ["txr_igic"]
    fake = FakeStripe()
    sub.cp = "28001"
    avisos.configurar_factura(fake, sub, cfg2)
    assert "default_tax_rates" not in dict(fake.posts)["subscriptions/sub_9"]
    assert "84.Uno.2.º" in dict(fake.posts)["customers/cus_9"]["invoice_settings"]["footer"]


def test_provincias_canarias():
    from nacenempresas.suscriptores import provincias_de_campo
    assert provincias_de_campo("pCN", "basico") == ["35", "38"]
    assert provincias_de_campo("p29", "basico") == ["29"]
    assert provincias_de_campo("Canarias, Madrid, Sevilla, Málaga, Cádiz", "pro") == ["35", "38", "28", "41", "29", "11"]


def test_ignora_suscripciones_de_otra_actividad():
    """Cuenta de Stripe compartida: solo cuentan las suscripciones con precios de NacenEmpresas."""
    from nacenempresas import suscriptores
    fake = FakeStripe()
    ajena = {"id": "sub_otro", "items": {"data": [{"price": {"metadata": {}}}]},
             "customer": {"id": "cus_x", "email": "cliente-de-otro-negocio@example.com"}, "metadata": {}}
    propia = {"id": "sub_rc", "items": {"data": [{"price": {"metadata": {"rc_plan": "basico"}}}]},
              "customer": {"id": "cus_rc", "email": "gestoria@example.com", "address": {"country": "ES", "postal_code": "35001"}},
              "metadata": {}}
    fake.objetos["subscriptions"] = [ajena, propia]
    ids = {s.id for s in suscriptores.desde_stripe(fake)}
    assert ids == {"sub_rc"}


def test_actualiza_enlaces_existentes(monkeypatch):
    """Enlaces creados con la prueba antigua (14 días sin tarjeta): se actualizan, sin cambiar la URL."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import setup_stripe
    from nacenempresas.config import sitio
    fake = FakeStripe()
    antiguo = {"id": "plink_viejo", "url": "https://buy.stripe.com/viejo", "metadata": {"rc_link": "basico_mes"},
               "payment_method_collection": "if_required", "subscription_data": {"trial_period_days": 14}}
    fake.objetos["payment_links"] = [antiguo]
    setup_stripe.enlace(fake, {"id": "price_1"}, [], sitio(), True, "basico_mes")
    ruta, datos = fake.posts[-1]
    assert ruta == "payment_links/plink_viejo"
    assert datos["payment_method_collection"] == "always"
    assert datos["subscription_data"]["trial_period_days"] == 7
    # Ya actualizado: no se toca
    fake2 = FakeStripe()
    fake2.objetos["payment_links"] = [{**antiguo, "payment_method_collection": "always",
                                       "subscription_data": {"trial_period_days": 7}}]
    assert setup_stripe.enlace(fake2, {"id": "price_1"}, [], sitio(), True, "basico_mes")["id"] == "plink_viejo"
    assert fake2.posts == []
