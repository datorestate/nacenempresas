"""Envío de avisos a clientes: email HTML + CSV, bienvenida con muestra, fin de prueba
y entrega automática de listas puntuales compradas.

Uso:
    python -m nacenempresas.avisos --fecha 2026-11-03            # envía
    python -m nacenempresas.avisos --fecha 2026-11-03 --prueba   # escribe .eml en out/ sin enviar
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import os
import smtplib
import sys
import time
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path

from . import almacen, config, fiscal, sectores, suscriptores
from .provincias import nombre as nombre_prov, normaliza

SALIDA = config.RAIZ / "out" / "correos"

AVISO_LEGAL_CLIENTE = (
    "Datos procedentes del BORME (Agencia Estatal BOE), reutilizados conforme a sus condiciones. "
    "Solo incluimos datos de sociedades, nunca de personas físicas. Si contactas con estas empresas, "
    "hazlo por correo postal, teléfono o visita: el email comercial sin consentimiento previo está "
    "prohibido por el art. 21 de la LSSI.")


# ------------------------------------------------------------------ filtros

def _const(r):
    return next(e for e in r["eventos"] if e["tipo"] == "constitucion")


def coincide(r: dict, sub) -> bool:
    if r["provincia_codigo"] not in sub.provincias:
        return False
    if not sub.sectores and not sub.palabras:
        return True
    c = _const(r) if r.get("es_constitucion") else {}
    if sub.sectores and set(c.get("sectores") or [c.get("sector")]) & set(sub.sectores):
        return True
    texto = normaliza(" ".join([r["denominacion"], c.get("objeto_social") or "",
                                *[e.get("objeto_social") or "" for e in r["eventos"]]]))
    return any(p in texto for p in sub.palabras)


def seleccion(registros: list[dict], sub) -> dict:
    nuevas = [r for r in registros if r.get("es_constitucion") and coincide(r, sub)]
    senales = []
    if sub.con_eventos:
        for r in registros:
            if r.get("es_constitucion") or r["provincia_codigo"] not in sub.provincias:
                continue
            for e in r["eventos"]:
                if e["tipo"] in ("traslado", "ampliacion_capital", "pagina_web", "cambio_objeto",
                                 "disolucion", "concurso", "extincion", "sucursal"):
                    if (sub.sectores or sub.palabras) and not coincide(
                            {**r, "es_constitucion": False}, sub):
                        continue
                    senales.append((r, e))
    return {"nuevas": nuevas, "senales": senales}


# ------------------------------------------------------------------ formato

def _eur(v):
    if v is None:
        return ""
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def filas_csv(nuevas):
    for r in nuevas:
        c = _const(r)
        yield {
            "denominacion": r["denominacion"], "forma_juridica": r["forma_juridica"],
            "provincia": r["provincia"], "municipio": c.get("municipio") or "",
            "domicilio": c.get("domicilio") or "", "objeto_social": c.get("objeto_social") or "",
            "sector": sectores.nombre_sector(c.get("sector") or "otros"),
            "cnae": c.get("cnae") or "", "capital_eur": c.get("capital") or "",
            "comienzo_operaciones": c.get("comienzo_operaciones") or "",
            "organo_administracion": " / ".join(c.get("organo_administracion") or []),
            "unipersonal": "sí" if c.get("unipersonal") else "no",
            "fecha_publicacion_borme": r["fecha_publicacion"], "hoja_registral": r.get("hoja_registral") or "",
            "fuente_pdf": r["url_pdf"],
        }


def csv_bytes(nuevas) -> bytes:
    buf = io.StringIO()
    filas = list(filas_csv(nuevas))
    campos = list(filas[0].keys()) if filas else ["denominacion"]
    w = csv.DictWriter(buf, fieldnames=campos, delimiter=";")
    w.writeheader()
    w.writerows(filas)
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM para que Excel abra bien los acentos


ETIQUETA_SENAL = {
    "traslado": "Traslado de domicilio", "ampliacion_capital": "Ampliación de capital",
    "pagina_web": "Nueva web", "cambio_objeto": "Nueva actividad", "disolucion": "Disolución",
    "concurso": "Concurso", "extincion": "Extinción", "sucursal": "Nueva sucursal",
}


def html_correo(sub, sel, titulo, intro, cfg, extra_html="") -> str:
    e = html.escape
    filas = []
    for r in sel["nuevas"][:300]:
        c = _const(r)
        filas.append(
            f"<tr><td style='padding:10px 8px;border-bottom:1px solid #D9DEE3'>"
            f"<strong style='color:#14213D'>{e(r['denominacion'])}</strong><br>"
            f"<span style='color:#4A5672;font-size:13px'>{e(c.get('domicilio') or '')}</span><br>"
            f"<span style='font-size:13px'>{e((c.get('objeto_social') or '')[:260])}</span></td>"
            f"<td style='padding:10px 8px;border-bottom:1px solid #D9DEE3;font-size:13px;white-space:nowrap'>"
            f"{e(sectores.nombre_sector(c.get('sector') or 'otros'))}<br>{_eur(c.get('capital'))}<br>"
            f"<a href='{e(r['url_pdf'])}' style='color:#0f6b4f'>BORME</a></td></tr>")
    tabla = ("<table style='width:100%;border-collapse:collapse'>" + "".join(filas) + "</table>") \
        if filas else "<p>Hoy no hay sociedades nuevas que encajen con tu filtro.</p>"
    sen = ""
    if sel["senales"]:
        items = "".join(
            f"<li style='margin-bottom:6px'><strong>{e(ETIQUETA_SENAL.get(ev['tipo'], ev['tipo']))}</strong>: "
            f"{e(r['denominacion'])}"
            f"{(' → ' + e(ev.get('municipio') or '')) if ev.get('municipio') else ''}"
            f"{(' · ' + _eur(ev.get('importe'))) if ev.get('importe') else ''}</li>"
            for r, ev in sel["senales"][:150])
        sen = f"<h3 style='color:#14213D;margin-top:28px'>Señales de empresas existentes</h3><ul>{items}</ul>"
    filtro = ", ".join(nombre_prov(p) for p in sub.provincias)
    if sub.sectores or sub.palabras:
        filtro += " · " + ", ".join([sectores.nombre_sector(s) for s in sub.sectores] + sub.palabras)
    return f"""<!doctype html><html><body style="margin:0;background:#F4F6F5;font-family:Arial,Helvetica,sans-serif;color:#14213D">
<div style="max-width:680px;margin:0 auto;padding:24px 16px">
<p style="font-size:13px;color:#4A5672;margin:0 0 6px">{e(cfg['nombre'])} · {e(filtro)}</p>
<h2 style="margin:0 0 8px;color:#14213D">{e(titulo)}</h2>
<p style="margin:0 0 18px">{intro}</p>
{extra_html}
<div style="background:#fff;border-radius:10px;padding:8px 12px">{tabla}</div>
{sen}
<p style="font-size:12px;color:#4A5672;margin-top:28px">{e(AVISO_LEGAL_CLIENTE)}</p>
<p style="font-size:12px;color:#4A5672">Gestiona tu suscripción, tus facturas o date de baja aquí:
<a href="{e(config.stripe_links().get('portal', cfg['url_base']))}" style="color:#0f6b4f">portal del cliente</a>.
Para cambiar provincias o actividad, responde a este correo.</p>
</div></body></html>"""


def texto_plano(sel) -> str:
    lineas = []
    for r in sel["nuevas"]:
        c = _const(r)
        lineas.append(f"- {r['denominacion']} | {c.get('domicilio') or ''} | {(c.get('objeto_social') or '')[:160]}")
    for r, ev in sel["senales"]:
        lineas.append(f"* {ETIQUETA_SENAL.get(ev['tipo'], ev['tipo'])}: {r['denominacion']}")
    return "\n".join(lineas) + "\n\n" + AVISO_LEGAL_CLIENTE


# ------------------------------------------------------------------ envío

class Cartero:
    def __init__(self, prueba: bool):
        # Sin servidor o sin contraseña, no se envía nada: los correos quedan en out/correos
        self.prueba = prueba or not (os.environ.get("SMTP_HOST") and os.environ.get("SMTP_PASS"))
        self.cfg = config.sitio()
        self.remitente = os.environ.get("FROM_EMAIL", self.cfg["email_contacto"])
        self.enviados = 0
        self._smtp = None

    def _conexion(self):
        if self._smtp is None:
            host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))
            self._smtp = smtplib.SMTP_SSL(host, port, timeout=60) if port == 465 \
                else smtplib.SMTP(host, port, timeout=60)
            if port != 465:
                self._smtp.starttls()
            self._smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        return self._smtp

    def enviar(self, para, asunto, html_, texto, adjuntos=()):
        m = EmailMessage()
        m["From"] = formataddr((self.cfg["nombre"], self.remitente))
        m["To"] = para
        m["Subject"] = asunto
        m["Reply-To"] = os.environ.get("REPLY_TO", self.cfg["email_contacto"])
        m["Message-ID"] = make_msgid(domain=self.remitente.split("@")[-1])
        m["List-Unsubscribe"] = f"<{config.stripe_links().get('portal', self.cfg['url_base'])}>"
        m.set_content(texto)
        m.add_alternative(html_, subtype="html")
        for nombre, datos, tipo in adjuntos:
            mt, st = tipo.split("/")
            m.add_attachment(datos, maintype=mt, subtype=st, filename=nombre)
        if self.prueba:
            SALIDA.mkdir(parents=True, exist_ok=True)
            seguro = "".join(ch if ch.isalnum() else "_" for ch in para)[:40]
            (SALIDA / f"{int(time.time()*1000)}_{seguro}.eml").write_bytes(bytes(m))
        else:
            self._conexion().send_message(m)
            time.sleep(1.5)  # por debajo de los límites de Gmail/Brevo
        self.enviados += 1

    def cerrar(self):
        if self._smtp:
            self._smtp.quit()


def configurar_factura(st, sub, cfg):
    """Al dar la bienvenida: menciones legales en la factura según dónde está el cliente
    e IGIC solo si es canario y el titular no está en el régimen del pequeño empresario."""
    reg = fiscal.region(sub.pais, sub.cp)
    datos = {"metadata": {"rc_bienvenida": "1", "rc_region": reg}}
    if fiscal.aplica_igic(reg, cfg):
        tasa = os.environ.get("STRIPE_TAX_RATE") or config.stripe_links().get("igic_tax_rate")
        if tasa:
            datos["default_tax_rates"] = [tasa]
    st.post(f"subscriptions/{sub.id}", datos)
    pie = fiscal.pie_factura(reg, cfg)
    if sub.customer and pie:
        st.post(f"customers/{sub.customer}", {"invoice_settings": {"footer": pie}})
    return reg


def _laborables_previos(dia: date, n: int) -> tuple[date, date]:
    return dia - timedelta(days=n), dia


def enviar_avisos(dia: date, subs, cartero: Cartero, st=None) -> dict:
    cfg = cartero.cfg
    registros_dia = (almacen.cargar_completo(dia.isoformat()) or {}).get("registros", [])
    es_lunes = dia.weekday() == 0
    semana = almacen.registros_rango(dia - timedelta(days=7), dia) if (es_lunes or any(
        not s.bienvenida_enviada for s in subs)) else []
    stats = {"diarios": 0, "semanales": 0, "bienvenidas": 0, "avisos_prueba": 0, "sin_coincidencias": 0}
    for sub in subs:
        extra = ""
        if sub.estado == "trialing" and sub.fin_prueba and not sub.tiene_pago:
            dias = max(0, int((sub.fin_prueba - time.time()) // 86400))
            if dias <= 3:
                extra = (f"<p style='background:#fff4d6;padding:12px;border-radius:8px'>Tu prueba gratuita termina en "
                         f"<strong>{dias} día{'s' if dias != 1 else ''}</strong>. Para seguir recibiendo los avisos, añade una forma de pago en el "
                         f"<a href='{html.escape(config.stripe_links().get('portal', cfg['url_base']))}'>portal del cliente</a> "
                         f"(entra con tu email). Sin permanencia.</p>")
                stats["avisos_prueba"] += 1
        adj = []
        if not sub.bienvenida_enviada:
            sel = seleccion(semana, sub)
            titulo = f"Bienvenido a {cfg['nombre']}: {len(sel['nuevas'])} sociedades nuevas en tu zona esta semana"
            intro = ("Este es tu primer aviso, con las constituciones de los últimos 7 días. "
                     "A partir de mañana recibirás las del día cada mañana laborable.")
            if sub.con_csv:
                adj.append(("nacenempresas_ultimos_7_dias.csv", csv_bytes(sel["nuevas"]), "text/csv"))
            cartero.enviar(sub.email, titulo, html_correo(sub, sel, titulo, intro, cfg, extra), texto_plano(sel), adj)
            stats["bienvenidas"] += 1
            if st is not None and sub.id.startswith("sub_") and not cartero.prueba:
                # solo se marca la bienvenida cuando el correo sale de verdad
                configurar_factura(st, sub, cfg)
            continue
        if sub.frecuencia == "semanal":
            if not es_lunes:
                continue
            sel = seleccion(semana, sub)
            titulo = f"Tu semana: {len(sel['nuevas'])} sociedades nuevas"
            intro = "Resumen de las constituciones publicadas en el BORME en los últimos 7 días."
            clave = "semanales"
        else:
            sel = seleccion(registros_dia, sub)
            if not sel["nuevas"] and not sel["senales"] and not extra:
                stats["sin_coincidencias"] += 1
                continue
            titulo = f"{len(sel['nuevas'])} sociedades nuevas hoy · BORME {dia.strftime('%d/%m/%Y')}"
            intro = "Constituciones publicadas hoy en el BORME que encajan con tu filtro."
            clave = "diarios"
        if sub.con_csv and sel["nuevas"]:
            adj.append((f"nacenempresas_{dia.isoformat()}.csv", csv_bytes(sel["nuevas"]), "text/csv"))
        cartero.enviar(sub.email, titulo, html_correo(sub, sel, titulo, intro, cfg, extra), texto_plano(sel), adj)
        stats[clave] += 1
    return stats


def entregar_listas(st, cartero: Cartero) -> int:
    """Listas puntuales (pago único): CSV de los últimos 30 días de una provincia."""
    links = config.stripe_links()
    plink = links.get("lista_id")
    if not plink:
        return 0
    entregadas = 0
    hoy = date.today()
    for ses in st.listar("checkout/sessions", payment_link=plink, status="complete", limit=50):
        if ses.get("payment_status") != "paid" or not ses.get("payment_intent"):
            continue
        pi = st.get(f"payment_intents/{ses['payment_intent']}")
        if (pi.get("metadata") or {}).get("rc_entregado") == "1":
            continue
        campos = suscriptores._campos(ses)
        provs = suscriptores.provincias_de_campo(campos.get("provincia") or "", "basico")
        secs, pal = suscriptores.interpreta_actividad(campos.get("actividad", ""))
        email = (ses.get("customer_details") or {}).get("email")
        if not provs or not email:
            continue
        sub = suscriptores.Suscriptor(id=ses["id"], email=email, plan="pro", provincias=provs,
                                      sectores=secs, palabras=pal)
        zona = "Canarias" if len(provs) > 1 else nombre_prov(provs[0])
        regs = almacen.registros_rango(hoy - timedelta(days=31), hoy, solo_constituciones=True)
        sel = {"nuevas": [r for r in regs if coincide(r, sub)], "senales": []}
        titulo = f"Tu lista: {len(sel['nuevas'])} sociedades creadas en {zona} (30 días)"
        cartero.enviar(email, titulo, html_correo(sub, sel, titulo, "Adjuntamos tu lista en CSV (se abre con Excel).",
                                                  cartero.cfg), texto_plano(sel),
                       [(f"lista_{zona}_{hoy.isoformat()}.csv", csv_bytes(sel["nuevas"]), "text/csv")])
        st.post(f"payment_intents/{pi['id']}", {"metadata": {"rc_entregado": "1"}})
        entregadas += 1
    return entregadas


def informe_titular(subs, stats, listas, cartero: Cartero, dia: date):
    destino = os.environ.get("OWNER_EMAIL")
    if not destino:
        return
    p = config.sitio()["precios"]
    activos = [s for s in subs if s.estado == "active"]
    mrr = sum(p["pro_mes"] if s.plan == "pro" else p["basico_mes"] for s in activos)
    pruebas = [s for s in subs if s.estado == "trialing"]
    cuerpo = (f"<h3>Informe {dia.isoformat()}</h3><ul>"
              f"<li>Clientes de pago: <b>{len(activos)}</b> · MRR estimado: <b>{mrr} €</b> (sin impuestos indirectos)</li>"
              f"<li>En prueba: {len(pruebas)} (con forma de pago: {sum(s.tiene_pago for s in pruebas)})</li>"
              f"<li>Envíos: {stats}</li><li>Listas entregadas hoy: {listas}</li></ul>"
              "<p>Pruebas activas:</p><ul>" +
              "".join(f"<li>{html.escape(s.email)} · {s.plan} · {', '.join(nombre_prov(c) for c in s.provincias)}</li>"
                      for s in pruebas) + "</ul>")
    cartero.enviar(destino, f"[NacenEmpresas] {len(activos)} clientes · {mrr} €/mes", cuerpo,
                   f"Clientes {len(activos)} MRR {mrr}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--prueba", action="store_true", help="no envía: escribe .eml en out/correos")
    a = ap.parse_args(argv)
    from .pipeline import hoy_madrid
    dia = date.fromisoformat(a.fecha) if a.fecha else hoy_madrid()
    st = None
    if os.environ.get("STRIPE_SECRET_KEY"):
        from .stripe_api import Stripe
        st = Stripe()
    subs = suscriptores.todos(st)
    cartero = Cartero(a.prueba)
    stats = enviar_avisos(dia, subs, cartero, st)
    listas = entregar_listas(st, cartero) if st and not cartero.prueba else 0
    informe_titular(subs, stats, listas, cartero, dia)
    cartero.cerrar()
    print(f"Suscriptores: {len(subs)} · {stats} · listas: {listas} · correos: {cartero.enviados}"
          f"{' (modo prueba, en out/correos)' if cartero.prueba else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
