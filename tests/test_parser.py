import json
from pathlib import Path

from nacenempresas import parser
from nacenempresas.provincias import codigo_provincia, lista_provincias

F = Path(__file__).parent / "fixtures"
CTX = {"identificador": "BORME-A-2026-210-03", "provincia_codigo": "03",
       "fecha": "2026-11-03", "url_pdf": "https://www.boe.es/x.pdf"}

NOMBRES_PERSONAS = ["ENGLAND", "NATILE", "HUESCA", "GARCIA LOPEZ", "PEREZ RUIZ",
                    "RUIZ SOLER", "MARTI GIL", "LOPEZ MARTIN", "Pedro Gil"]


def _registros_txt():
    texto = (F / "borme_2026_alicante.txt").read_text(encoding="utf-8")
    out = []
    for n, lineas in parser.separar_entradas(texto):
        r = parser.analizar_entrada(n, lineas, CTX)
        if r:
            out.append(r)
    return out


def test_pdf_real_2015():
    res = parser.analizar_pdf(str(F / "BORME-A-2015-27-10.pdf"), "BORME-A-2015-27-10", "10", "2015-02-10")
    assert res["calidad"]["entradas"] == 30
    assert res["calidad"]["porcentaje_reconocido"] >= 95
    const = [r for r in res["registros"] if r["es_constitucion"]]
    assert len(const) == 8
    sercar = next(r for r in const if r["denominacion"] == "SERCAR 33 CACERES SL")
    c = sercar["eventos"][0]
    assert c["capital"] == 3200.0
    assert c["municipio"] == "Caceres"
    assert c["comienzo_operaciones"] == "2014-12-17"
    assert c["sector"] == "hosteleria"
    assert sercar["hoja_registral"] == "CC 13638"
    texto = json.dumps(res, ensure_ascii=False)
    for persona in ["PANIAGUA", "VILLEGAS", "TERCERO GALEA", "Ramón Jiménez", "GONZALEZ TORRES"]:
        assert persona not in texto


def test_formato_actual_constituciones():
    regs = _registros_txt()
    const = {r["denominacion"]: r for r in regs if r["es_constitucion"]}
    assert set(const) == {"KALADISE SL", "SMART BOX VERGEL SL",
                          "CONSTRUCCIONES Y REFORMAS LEVANTE 2026 SOCIEDAD LIMITADA"}
    k = const["KALADISE SL"]["eventos"][0]
    assert k["sector"] == "hosteleria" and k["capital"] == 3000.0
    assert k["municipio"] == "Alicante/Alacant"
    assert k["comienzo_operaciones"] == "2026-09-01"
    s = const["SMART BOX VERGEL SL"]["eventos"][0]
    assert s["unipersonal"] is True and s["organo_administracion"] == ["Adm. Unico"]
    c = const["CONSTRUCCIONES Y REFORMAS LEVANTE 2026 SOCIEDAD LIMITADA"]
    assert c["forma_juridica"] == "SL"
    ce = c["eventos"][0]
    assert ce["capital"] == 1.0 and ce["cnae"] == "4121" and ce["sector"] == "construccion"
    assert ce["organo_administracion"] == ["Adm. Solid."]


def test_eventos_y_senales():
    regs = {r["numero"]: r for r in _registros_txt()}
    tipos = {e["tipo"] for e in regs[512003]["eventos"]}
    assert {"cambio_denominacion", "traslado", "cambio_objeto"} <= tipos
    tras = next(e for e in regs[512003]["eventos"] if e["tipo"] == "traslado")
    assert tras["municipio"] == "Orihuela"
    liq = regs[512004]
    assert liq["forma_juridica"] == "SL"
    assert {"disolucion", "extincion"} <= {e["tipo"] for e in liq["eventos"]}
    az = regs[512007]
    amp = next(e for e in az["eventos"] if e["tipo"] == "ampliacion_capital")
    assert amp["importe"] == 150000.0 and amp["capital_resultante"] == 210000.0
    assert any(e["tipo"] == "concurso" and e["senal"] == "riesgo" for e in az["eventos"])
    assert any(e["tipo"] == "pagina_web" for e in az["eventos"])


def test_sin_personas_fisicas():
    regs = _registros_txt()
    assert 512005 not in {r["numero"] for r in regs}  # empresario individual descartado
    texto = json.dumps(regs, ensure_ascii=False)
    for persona in NOMBRES_PERSONAS:
        assert persona not in texto, persona


def test_ficha_publica_sin_direccion():
    r = next(r for r in _registros_txt() if r["denominacion"] == "KALADISE SL")
    f = parser.ficha_publica(r)
    assert "SAN FERNANDO" not in json.dumps(f, ensure_ascii=False)
    assert f["municipio"] == "Alicante/Alacant"


def test_provincias():
    assert codigo_provincia("málaga") == "29"
    assert codigo_provincia("Vizcaya") == "48"
    assert codigo_provincia("Tenerife") == "38"
    assert lista_provincias("Sevilla, Cádiz y Huelva; Madrid / Toledo, Ávila") == ["41", "11", "21", "28", "45"]


def test_pdf_formato_actual_con_cve_vertical(tmp_path):
    """PDF sintético con la maqueta actual: cabeceras, CVE vertical y pie."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    ruta = tmp_path / "BORME-A-2026-210-03.pdf"
    c = canvas.Canvas(str(ruta), pagesize=A4)
    lineas = (F / "borme_2026_alicante.txt").read_text(encoding="utf-8").splitlines()
    for bloque in (lineas[:9], lineas[9:]):
        y = 800
        for cab in ["BOLETÍN OFICIAL DEL REGISTRO MERCANTIL",
                    "Núm. 210 Martes 3 de noviembre de 2026 Pág. 50123",
                    "SECCIÓN PRIMERA", "Empresarios", "Actos inscritos", "ALICANTE/ALACANT"]:
            c.drawString(40, y, cab); y -= 14
        for l in bloque:
            c.setFont("Helvetica", 7); c.drawString(40, y, l); y -= 11
        c.saveState(); c.translate(570, 300); c.rotate(90)
        c.drawString(0, 0, "cve: BORME-A-2026-210-03 Verificable en https://www.boe.es")
        c.restoreState()
        c.drawString(40, 30, "https://www.boe.es BOLETÍN OFICIAL DEL REGISTRO MERCANTIL D.L.: M-5188/1990 - ISSN: 0214-9958")
        c.showPage()
    c.save()
    res = parser.analizar_pdf(str(ruta), "BORME-A-2026-210-03", "03", "2026-11-03")
    assert res["calidad"]["entradas"] == 7
    assert res["calidad"]["descartadas_persona_fisica"] == 1
    assert sum(r["es_constitucion"] for r in res["registros"]) == 3
    texto = json.dumps(res, ensure_ascii=False)
    assert "cve" not in texto and "ISSN" not in texto


def test_formato_las_palmas_registro_y_municipio():
    """Formato real de Las Palmas (octubre de 2026): '(R.M. LAS PALMAS)' tras la forma jurídica."""
    texto = (
        "450632 - BULL FILMS 2026, SOCIEDAD LIMITADA(R.M. LAS PALMAS).\n"
        "Constitución. Comienzo de operaciones: 17.09.26. Objeto social: Actividades de producción cinematográfica y de vídeo.\n"
        "Domicilio: C/ EJEMPLO, 1-INFECAR 35012 (PALMAS DE GRAN CANARIA (LAS). Capital: 100,00 Euros. Declaración de\n"
        "unipersonalidad. Socio único: PEREZ GIL ANA. Nombramientos. Adm. Unico: PEREZ GIL ANA. Datos registrales. S 8 , H GC 67044, I/A 1 ( 2.10.26).\n"
        "450633 - SPV EVERTON, SOCIEDAD LIMITADA(R.M. LAS PALMAS).\n"
        "Ampliación de capital. Capital: 402.150,00 Euros. Resultante Suscrito: 3.635.250,00 Euros. Datos registrales. S 8 , H GC 58865, I/A 20 ( 1.10.26).\n"
        "450634 - GUAGUAS MUNICIPALES SOCIEDAD ANONIMA(R.M. LAS PALMAS).\n"
        "Nombramientos. Apo.Sol.: LOPEZ RUIZ ORLANDO. Datos registrales. S 8 , H GC 7323, I/A 107 ( 2.10.26).\n")
    ctx = {"identificador": "BORME-A-2026-196-35", "provincia_codigo": "35", "fecha": "2026-10-09", "url_pdf": ""}
    regs = [parser.analizar_entrada(n, l, ctx) for n, l in parser.separar_entradas(texto)]
    assert all(regs), "ninguna sociedad debe descartarse"
    bull = regs[0]
    assert bull["denominacion"] == "BULL FILMS 2026, SOCIEDAD LIMITADA" and bull["forma_juridica"] == "SL"
    c = bull["eventos"][0]
    assert c["municipio"] == "Las Palmas de Gran Canaria" and c["capital"] == 100.0
    assert regs[1]["forma_juridica"] == "SL" and regs[2]["forma_juridica"] == "SA"
    assert "PEREZ" not in json.dumps(regs, ensure_ascii=False) and "ORLANDO" not in json.dumps(regs, ensure_ascii=False)


def test_formas_juridicas_interiores():
    from nacenempresas.parser import _forma_juridica
    assert _forma_juridica("CAJA RURAL DE JAEN, BARCELONA Y MADRID, SOCIEDAD COOPERATIVA DE CREDITO") == "COOP"
    assert _forma_juridica("SOCIEDAD AGRARIA DE TRANSFORMACION NUM 1234 LOS OLIVOS") == "SAT"
    assert _forma_juridica("INVERSIONES ALFA SICAV SA") == "SA"
    assert _forma_juridica("GARCIA LOPEZ ANTONIO") is None


def test_cnae_con_puntos():
    import re
    from nacenempresas import parser
    for txt, esperado in [("CNAE: 4121", "4121"), ("C.N.A.E. 5611", "5611"), ("C.N.A.E.: 62.01", "62.01")]:
        m = re.search(r"\bC\.?\s?N\.?\s?A\.?\s?E\.?[:\s]*(\d{2,4}(?:\.\d{1,2})?)", txt)
        assert m and m.group(1) == esperado
