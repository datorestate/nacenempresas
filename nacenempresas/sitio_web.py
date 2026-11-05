"""Genera la web estática (GitHub Pages) a partir de data/publico.

    python -m nacenempresas.sitio_web          # escribe en _site/
"""
from __future__ import annotations

import collections
import html
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import almacen, config, fiscal, sectores
from .provincias import PROVINCIAS, slug_provincia

RAIZ = config.RAIZ
SALIDA = RAIZ / "_site"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS_PUBLICOS = 30

FAQ = [
    ("¿De dónde salen los datos?", "Del Boletín Oficial del Registro Mercantil (BORME), sección primera, que la Agencia Estatal BOE publica cada día laborable en sus datos abiertos. Los procesamos cada mañana y enlazamos siempre el PDF oficial."),
    ("¿Incluís nombres de administradores o socios?", "No. Por diseño excluimos los datos de personas físicas: ni administradores, ni apoderados, ni socios únicos, ni empresarios individuales. Solo datos de sociedades."),
    ("¿Puedo enviarles un email comercial a estas empresas?", "No sin su consentimiento previo: el artículo 21 de la LSSI lo prohíbe. Lo habitual y eficaz es el correo postal al domicilio social, la visita o la llamada. Te damos el domicilio completo para eso."),
    ("¿Traéis teléfono o email de las empresas?", "No. El BORME no los publica y no los compramos a terceros. Es la diferencia entre un dato oficial y fresco y una base de datos de contacto."),
    ("¿Cuándo llega el aviso?", "Cada día laborable por la mañana, poco después de que el BOE publique el BORME. Si eliges el resumen semanal, lo recibes los lunes."),
    ("¿Cómo funciona la prueba?", "Te das de alta sin tarjeta y recibes los avisos durante 14 días. Antes del final te recordamos cómo añadir una forma de pago; si no la añades, la prueba termina sola."),
    ("¿Cómo es la factura?", "Al darte de alta indicas tu NIF o CIF y tu razón social, y cada cobro genera su factura, descargable desde el portal del cliente. Facturamos desde Canarias: a empresas de la Península y Baleares la factura va sin IVA ni IGIC, y el IVA lo autoliquidas tú por inversión del sujeto pasivo, con lo que tu coste neto es el precio publicado. A empresas canarias, sin IGIC mientras estemos en el régimen del pequeño empresario."),
    ("¿Puedo contratar como particular?", "No. El servicio es solo para empresas y profesionales, y por eso pedimos el NIF o CIF al darte de alta."),
]

AFILIADO_POR_CALC = {
    "autonomo-o-sl": ["gestoria_online", "banco_empresas"],
    "coste-crear-sl": ["gestoria_online", "banco_empresas"],
    "cuota-autonomos-2026": ["facturacion", "seguros"],
    "factura-irpf-iva": ["facturacion", "gestoria_online"],
    "factura-igic-canarias": ["facturacion", "gestoria_online"],
    "calendario-fiscal-sl": ["gestoria_online", "facturacion"],
}

TRAMOS_TABLA = [
    ("Hasta 670 €", "205,88 €"), ("670,01 – 900 €", "226,47 €"), ("900,01 – 1.166,70 €", "267,65 €"),
    ("1.166,71 – 1.300 €", "299,56 €"), ("1.300,01 – 1.500 €", "302,65 €"), ("1.500,01 – 1.700 €", "302,65 €"),
    ("1.700,01 – 1.850 €", "360,29 €"), ("1.850,01 – 2.030 €", "380,88 €"), ("2.030,01 – 2.330 €", "401,47 €"),
    ("2.330,01 – 2.760 €", "427,21 €"), ("2.760,01 – 3.190 €", "452,94 €"), ("3.190,01 – 3.620 €", "478,68 €"),
    ("3.620,01 – 4.050 €", "504,41 €"), ("4.050,01 – 6.000 €", "545,59 €"), ("Más de 6.000 €", "607,35 €"),
]

CALENDARIO = """
<h2>Al constituirla</h2>
<ul>
<li><strong>Alta censal (modelo 036)</strong> para obtener el NIF definitivo, antes de empezar la actividad.</li>
<li><strong>Alta de los socios administradores en el RETA</strong> (autónomos societarios), en los 30 días anteriores al inicio.</li>
<li><strong>Legalización del libro de actas, socios y, si es unipersonal, de contratos con el socio</strong>, telemáticamente en el Registro Mercantil.</li>
<li><strong>Titularidad real</strong>: se declara en la escritura y en el depósito de cuentas.</li>
</ul>
<h2>Cada trimestre (del 1 al 20 de abril, julio y octubre; en enero hasta el 30)</h2>
<ul>
<li><strong>Modelo 303</strong>: IVA.</li>
<li><strong>Modelo 111</strong>: retenciones de nóminas y profesionales.</li>
<li><strong>Modelo 115</strong>: retenciones del alquiler del local.</li>
<li><strong>Modelo 349</strong>: operaciones intracomunitarias, si las hay.</li>
</ul>
<h2>Cada año</h2>
<ul>
<li><strong>Enero</strong>: resúmenes anuales 390, 190 y 180.</li>
<li><strong>Febrero</strong>: modelo 347 de operaciones con terceros de más de 3.005,06 €.</li>
<li><strong>Abril, octubre y diciembre (1 al 20)</strong>: pagos fraccionados del Impuesto sobre Sociedades (modelo 202), cuando correspondan. En el primer ejercicio no suele haber base del año anterior.</li>
<li><strong>Hasta el 30 de abril</strong>: legalización del libro diario y de inventarios y cuentas anuales del ejercicio cerrado (en un ejercicio natural).</li>
<li><strong>Hasta el 31 de marzo</strong>: formulación de las cuentas anuales; aprobación por la junta antes del 30 de junio.</li>
<li><strong>Del 1 al 25 de julio</strong>: Impuesto sobre Sociedades (modelo 200).</li>
<li><strong>Hasta el 30 de julio</strong> (un mes tras la aprobación): depósito de cuentas en el Registro Mercantil.</li>
</ul>
<h2>Si la SL está en Canarias</h2>
<ul>
<li><strong>Modelo 400</strong> (alta censal ante la Agencia Tributaria Canaria), además del 036 estatal.</li>
<li><strong>IGIC en lugar de IVA</strong>: modelo 420 cada trimestre, en los mismos plazos que el 303, y resumen anual 425 hasta el 30 de enero. La exención del pequeño empresario es solo para personas físicas, no para sociedades.</li>
<li><strong>Modelo 415</strong> de operaciones con terceros ante la Agencia Tributaria Canaria, en lugar del 347.</li>
<li><strong>RIC</strong>: la dotación se decide al aprobar las cuentas y se aplica en el modelo 200; hay que invertirla en Canarias en un plazo de 3 años.</li>
<li>El Impuesto sobre Sociedades (200 y 202) y las retenciones (111 y 115) se presentan en la Agencia Tributaria estatal como en el resto de España.</li>
</ul>
<p class="nota">Las fechas son las habituales para un ejercicio que coincide con el año natural. Si el plazo acaba en festivo, se traslada al siguiente día hábil. Comprueba siempre el calendario del contribuyente de la Agencia Tributaria.</p>
"""


def _fecha_larga(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _fecha_corta(iso):
    d = date.fromisoformat(iso)
    return f"{d.day:02d}/{d.month:02d}"


def _enlaces_pago(cfg):
    links = config.stripe_links()
    respaldo = f"mailto:{cfg['email_contacto']}?subject="
    def l(k, asunto):
        return links.get(k) or respaldo + asunto.replace(" ", "%20")
    return {
        "basico_mes": l("basico_mes", "Quiero la prueba gratuita (plan Básico)"),
        "basico_anio": l("basico_anio", "Quiero el plan Básico anual"),
        "pro_mes": l("pro_mes", "Quiero la prueba gratuita (plan Pro)"),
        "pro_anio": l("pro_anio", "Quiero el plan Pro anual"),
        "lista": l("lista", "Quiero una lista de empresas nuevas"),
        "portal": links.get("portal", ""),
    }


def _afiliados(cfg, claves):
    out = []
    for k in claves:
        a = cfg["afiliados"].get(k)
        if a:
            out.append({"nombre": a["nombre"], "url": a["url"] or a["oficial"],
                        "rel": "sponsored noopener" if a["url"] else "noopener"})
    return out


def _cargar_ventana(dias_hasta: date, n: int):
    fichas, ultimo = [], None
    for dia in almacen.dias_disponibles():
        d = date.fromisoformat(dia)
        if dias_hasta - timedelta(days=n) < d <= dias_hasta:
            p = almacen.cargar_publico(dia)
            fichas.extend(p.get("constituciones", []))
            ultimo = p
    for f in fichas:
        f["provincia_nombre"] = PROVINCIAS.get(f["provincia"], f["provincia"])
        f["fecha_corta"] = _fecha_corta(f["fecha"])
        f["objeto"] = f.get("objeto") or ""
    excl_p = RAIZ / "config" / "excluidas.json"
    excluidas = set(json.loads(excl_p.read_text("utf-8")).get("denominaciones", [])) if excl_p.exists() else set()
    fichas = [f for f in fichas if f["denominacion"] not in excluidas]
    fichas.sort(key=lambda f: (f["fecha"], f["denominacion"]), reverse=True)
    return fichas, ultimo


def _ficticias(n):
    return [{"denominacion": "SOCIEDAD " + "·" * 14 + " SL", "municipio": "·" * 10,
             "objeto": "Actividad disponible para suscriptores " + "·" * 20, "fecha_corta": "··/··"}
            for _ in range(n)]


def construir(hoy: date | None = None):
    cfg = config.sitio()
    links = _enlaces_pago(cfg)
    hoy = hoy or date.today()
    dias = almacen.dias_disponibles()
    if dias and date.fromisoformat(dias[-1]) < hoy - timedelta(days=DIAS_PUBLICOS):
        hoy = date.fromisoformat(dias[-1])  # datos antiguos (pruebas): se centra en el último día
    fichas, ultimo = _cargar_ventana(hoy, DIAS_PUBLICOS)
    ultimo = ultimo or {"fecha": hoy.isoformat(), "total_constituciones": 0}
    env = Environment(loader=FileSystemLoader(RAIZ / "templates"), autoescape=select_autoescape(["html"]))
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    (SALIDA / "provincias").mkdir(parents=True)
    shutil.copytree(RAIZ / "static", SALIDA / "static")
    paginas = []

    def escribe(ruta, plantilla, prioridad="0.6", **ctx):
        profundidad = ruta.count("/")
        ctx.setdefault("jsonld", None)
        out = env.get_template(plantilla).render(cfg=cfg, links=links, ruta=ruta, nota_fiscal=fiscal.nota_precios(cfg),
                                                 raiz="../" * profundidad, **ctx)
        destino = SALIDA / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(out, "utf-8")
        paginas.append((ruta, prioridad))

    # ---------- portada
    ult_fichas = [f for f in fichas if f["fecha"] == ultimo["fecha"]]
    muestra = sorted(ult_fichas, key=lambda f: -(f.get("capital") or 0))[:6] or fichas[:6]
    escribe("index.html", "index.html", "1.0",
            titulo="Empresas recién creadas en España: avisos diarios del BORME | NacenEmpresas",
            descripcion="Recibe cada mañana las sociedades constituidas en tu provincia y sector, con domicilio, actividad y capital. Prueba 14 días gratis, sin tarjeta.",
            ultimo={**ultimo, "fecha_larga": _fecha_larga(ultimo["fecha"])}, muestra=muestra,
            total_30=len(fichas), dias_30=len({f["fecha"] for f in fichas}), faq=FAQ,
            jsonld={"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": p, "acceptedAnswer": {"@type": "Answer", "text": r}} for p, r in FAQ]})

    # ---------- provincias y provincia+sector
    por_prov = collections.defaultdict(list)
    for f in fichas:
        por_prov[f["provincia"]].append(f)
    lista_prov = []
    for cod, nombre in sorted(PROVINCIAS.items(), key=lambda kv: kv[1]):
        sl = slug_provincia(cod)
        fs = por_prov.get(cod, [])
        cuenta = collections.Counter(f.get("sector") or "otros" for f in fs)
        secs = [{"clave": k, "nombre": sectores.nombre_sector(k), "n": n}
                for k, n in cuenta.most_common() if k != "otros" and n >= 2]
        base = dict(provincia=nombre, slug=sl, total_30=len(fs),
                    ultimo_dia=_fecha_larga(fs[0]["fecha"]) if fs else None)
        escribe(f"provincias/{sl}.html", "provincia.html", "0.8",
                titulo=f"Empresas creadas en {nombre} hoy y en los últimos 30 días | NacenEmpresas",
                descripcion=f"Listado de sociedades de nueva creación en {nombre} según el BORME: {len(fs)} en los últimos 30 días, con municipio y actividad. Recíbelas cada mañana.",
                h1=f"Empresas creadas en {nombre}", filas=fs[:25], bloqueadas=_ficticias(min(8, max(0, len(fs) - 25))),
                sectores=secs, sector=None, **base)
        for s in secs:
            fss = [f for f in fs if (f.get("sector") or "otros") == s["clave"]]
            escribe(f"provincias/{sl}/{s['clave']}.html", "provincia.html", "0.5",
                    titulo=f"Nuevas empresas de {s['nombre'].lower()} en {nombre} | NacenEmpresas",
                    descripcion=f"Sociedades de {s['nombre'].lower()} constituidas en {nombre} en los últimos 30 días según el BORME.",
                    h1=f"Nuevas empresas de {s['nombre'].lower()} en {nombre}", filas=fss[:25],
                    bloqueadas=_ficticias(min(6, max(0, len(fss) - 25))), sectores=None,
                    sector=s["clave"], sector_nombre=s["nombre"], **{**base, "total_30": len(fss)})
        lista_prov.append((sl, nombre, len(fs)))
    # ---------- Canarias: las dos provincias juntas (mercado local del titular)
    fs_can = sorted(por_prov.get("35", []) + por_prov.get("38", []), key=lambda f: (f["fecha"], f["denominacion"]), reverse=True)
    escribe("provincias/canarias.html", "provincia.html", "0.9",
            titulo="Empresas creadas en Canarias hoy y en los últimos 30 días | NacenEmpresas",
            descripcion=f"Sociedades de nueva creación en Canarias (Las Palmas y Santa Cruz de Tenerife) según el BORME: {len(fs_can)} en los últimos 30 días. Recíbelas cada mañana.",
            h1="Empresas creadas en Canarias", filas=fs_can[:25], bloqueadas=_ficticias(min(8, max(0, len(fs_can) - 25))),
            sectores=None, sector=None, provincia="Canarias", slug="canarias", total_30=len(fs_can),
            ultimo_dia=_fecha_larga(fs_can[0]["fecha"]) if fs_can else None, mostrar_provincia=True,
            subtitulo_cta=f"Las dos provincias canarias en un solo plan Básico, por {cfg['precios']['basico_mes']} € al mes, con domicilio, actividad y capital.",
            enlaces_extra=[("las-palmas.html", f"Las Palmas ({len(por_prov.get('35', []))})"),
                           ("santa-cruz-de-tenerife.html", f"Santa Cruz de Tenerife ({len(por_prov.get('38', []))})")])
    cuerpo = "<h1>Empresas creadas por provincia</h1><p class='tenue'>Sociedades constituidas en los últimos 30 días según el BORME.</p>" + \
        f"<p><a class='boton secundario' href='canarias.html'>Canarias: las dos provincias ({len(fs_can)})</a></p><ul class='fichas'>" + \
        "".join(f"<li><a href='{sl}.html'>{html.escape(n)} ({c})</a></li>" for sl, n, c in lista_prov) + "</ul>"
    escribe("provincias/index.html", "simple.html", "0.9", titulo="Empresas recién creadas por provincia | NacenEmpresas",
            descripcion="Consulta las sociedades de nueva creación en cada provincia española, actualizadas cada día laborable desde el BORME.",
            cuerpo=cuerpo)

    # ---------- informe semanal (contenido para LinkedIn y prensa local)
    informe, texto_social = _informe(fichas, hoy)
    escribe("informe.html", "simple.html", "0.7", titulo="Informe semanal de creación de empresas en España | NacenEmpresas",
            descripcion="Cuántas sociedades se crean cada semana en España, por provincia y por sector, a partir del BORME.",
            cuerpo=informe)
    (RAIZ / "out").mkdir(exist_ok=True)
    (RAIZ / "out" / "publicacion_semanal.md").write_text(texto_social, "utf-8")

    # ---------- calculadoras
    calcs = [
        ("autonomo-o-sl", "calc_autonomo_o_sl.html", "¿Autónomo o sociedad limitada? Calculadora 2026",
         "Compara cuánto te quedas como autónomo y con una SL según tu beneficio, con las cuotas y tipos de 2026.",
         "Ley 35/2006 del IRPF; Ley 27/2014 del Impuesto sobre Sociedades (DT 44.ª, Ley 7/2024); RDL 3/2026"),
        ("coste-crear-sl", "calc_coste_sl.html", "¿Cuánto cuesta crear una SL en 2026?",
         "Calcula notaría, registro, gestoría y capital mínimo para constituir una sociedad limitada.",
         "Real Decreto Legislativo 1/2010 (Ley de Sociedades de Capital); Ley 18/2022"),
        ("cuota-autonomos-2026", "calc_cuota_autonomos.html", "Cuota de autónomos 2026 por tramos",
         "Calcula tu cuota mensual del RETA en 2026 según tus rendimientos, con tarifa plana y autónomos societarios.",
         "Real Decreto-ley 13/2022; Real Decreto-ley 3/2026; Orden PJC/297/2026"),
        ("factura-irpf-iva", "calc_factura.html", "Calculadora de factura con IVA y retención de IRPF",
         "Calcula el total de una factura de autónomo con IVA y retención, y estima tu modelo 130.",
         "Ley 37/1992 del IVA; Reglamento del IRPF, arts. 95 y 110"),
        ("factura-igic-canarias", "calc_factura.html", "Calculadora de factura con IGIC e IRPF para Canarias",
         "Calcula una factura de autónomo canario con IGIC y retención, o sin impuestos si facturas a una empresa de la Península.",
         "Ley 20/1991 del IGIC; Ley 4/2012; Decreto ley 3/2026 de Canarias; Ley 37/1992, art. 84"),
    ]
    for slug, plantilla, h1, desc, norma in calcs:
        escribe(f"calculadoras/{slug}.html", plantilla, "0.8", titulo=f"{h1} | NacenEmpresas", descripcion=desc,
                h1=h1, entradilla=desc, normativa=norma, siguientes=_afiliados(cfg, AFILIADO_POR_CALC[slug]),
                tramos=TRAMOS_TABLA, territorio_defecto="canarias" if "igic" in slug else "peninsula")
    escribe("calculadoras/calendario-fiscal-sl.html", "simple.html", "0.7",
            titulo="Calendario fiscal del primer año de una SL | NacenEmpresas",
            descripcion="Qué modelos presenta una sociedad limitada recién creada y cuándo: 036, 303, 111, 202, 200 y depósito de cuentas, y sus equivalentes en Canarias (400, 420, 415).",
            cuerpo="<p class='migas'><a href='index.html'>Calculadoras</a></p><h1>Calendario fiscal del primer año de una SL</h1>" + CALENDARIO +
            "".join(f"<div class='siguiente'><strong>Siguiente paso:</strong> <a href='{html.escape(a['url'])}' rel='{a['rel']}'>{html.escape(a['nombre'])}</a></div>"
                    for a in _afiliados(cfg, AFILIADO_POR_CALC["calendario-fiscal-sl"])) +
            f"<p class='peq tenue'>Revisado el {cfg['revision_fiscal']}.</p>")
    items = [(s, h, d) for s, _, h, d, _ in calcs] + [("calendario-fiscal-sl", "Calendario fiscal del primer año de una SL", "Modelos y plazos de una SL recién creada.")]
    escribe("calculadoras/index.html", "simple.html", "0.8", titulo="Calculadoras para crear tu empresa | NacenEmpresas",
            descripcion="Calculadoras gratuitas para decidir entre autónomo o SL, el coste de constituir una sociedad y la cuota de autónomos 2026.",
            cuerpo="<h1>Calculadoras para crear tu empresa</h1><ul class='lista-calc'>" +
            "".join(f"<li><a href='{s}.html'><strong>{html.escape(h)}</strong><span class='tenue'>{html.escape(d)}</span></a></li>" for s, h, d in items) + "</ul>")

    # ---------- legales y utilidades
    for nombre_f in ["aviso-legal", "privacidad", "condiciones", "retirada", "gracias"]:
        bruto = (RAIZ / "legal" / f"{nombre_f}.html").read_text("utf-8")
        for k in ("nombre", "titular", "nif_titular", "domicilio_titular", "email_contacto", "url_base"):
            bruto = bruto.replace("{{" + k + "}}", html.escape(str(cfg[k])))
        bruto = bruto.replace("{{portal}}", html.escape(links["portal"] or f"mailto:{cfg['email_contacto']}"))
        titulo = bruto.split("<h1>")[1].split("</h1>")[0] if "<h1>" in bruto else nombre_f
        escribe(f"{nombre_f}.html", "simple.html", "0.2", titulo=f"{titulo} | NacenEmpresas",
                descripcion=f"{titulo} de {cfg['nombre']}.", cuerpo=bruto)
    escribe("404.html", "simple.html", "0.0", titulo="Página no encontrada | NacenEmpresas", descripcion="Página no encontrada.",
            cuerpo="<h1>Esta página no existe</h1><p>Puede que la provincia o el sector ya no tenga empresas en los últimos 30 días. <a href='/'>Vuelve al inicio</a> o consulta el <a href='provincias/index.html'>listado por provincia</a>.</p>")

    # ---------- sitemap y robots
    url = cfg["url_base"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for ruta, prio in paginas:
        if ruta in ("404.html", "gracias.html"):
            continue
        sm.append(f"<url><loc>{url}/{ruta}</loc><lastmod>{hoy.isoformat()}</lastmod><priority>{prio}</priority></url>")
    sm.append("</urlset>")
    (SALIDA / "sitemap.xml").write_text("\n".join(sm), "utf-8")
    (SALIDA / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /gracias.html\nSitemap: {url}/sitemap.xml\n", "utf-8")
    (SALIDA / ".nojekyll").write_text("", "utf-8")
    print(f"Web generada: {len(paginas)} páginas en {SALIDA}")
    return len(paginas)


def _informe(fichas, hoy):
    hace7, hace14 = hoy - timedelta(days=7), hoy - timedelta(days=14)
    esta = [f for f in fichas if date.fromisoformat(f["fecha"]) > hace7]
    previa = [f for f in fichas if hace14 < date.fromisoformat(f["fecha"]) <= hace7]
    c_esta = collections.Counter(f["provincia"] for f in esta)
    c_prev = collections.Counter(f["provincia"] for f in previa)
    sec = collections.Counter(f.get("sector") or "otros" for f in esta)
    var = (len(esta) - len(previa)) / len(previa) * 100 if previa else None
    filas = "".join(
        f"<tr><td>{html.escape(PROVINCIAS[c])}</td><td>{n}</td><td>{c_prev.get(c, 0)}</td></tr>"
        for c, n in c_esta.most_common(15))
    top_sec = ", ".join(f"{sectores.nombre_sector(k).lower()} ({n})" for k, n in sec.most_common(4) if k != "otros")
    cuerpo = (f"<h1>Informe semanal de creación de empresas</h1>"
              f"<p class='tenue'>Semana hasta el {_fecha_larga(hoy.isoformat())}. Fuente: BORME, sección primera.</p>"
              f"<p>En los últimos 7 días se publicaron <strong>{len(esta)}</strong> constituciones de sociedades"
              f"{f', un {var:+.0f} % respecto a la semana anterior' if var is not None else ''}. "
              f"Los sectores con más altas fueron {top_sec or 'variados'}.</p>"
              f"<div class='desplaza'><table class='tabla'><thead><tr><th>Provincia</th><th>Esta semana</th><th>Semana anterior</th></tr></thead><tbody>{filas}</tbody></table></div>"
              f"<p class='peq tenue'>Puedes citar estos datos enlazando esta página.</p>")
    top3 = ", ".join(f"{PROVINCIAS[c]} ({n})" for c, n in c_esta.most_common(3))
    social = (f"Esta semana se han creado {len(esta)} sociedades en España según el BORME"
              f"{f' ({var:+.0f} % frente a la anterior)' if var is not None else ''}.\n\n"
              f"Provincias con más altas: {top3}.\nSectores: {top_sec}.\n\n"
              f"Si vendes a empresas que acaban de nacer (gestorías, seguros, agencias), recibe las de tu provincia cada mañana: "
              f"{config.sitio()['url_base']}/informe.html\n\n#emprendimiento #pymes #BORME")
    return cuerpo, social


if __name__ == "__main__":
    construir()
    sys.exit(0)
