import email
import json
from datetime import date
from pathlib import Path

import pytest

F = Path(__file__).parent / "fixtures"


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("DATA_KEY", raising=False)
    import importlib
    from nacenempresas import almacen, avisos, parser
    importlib.reload(almacen)
    importlib.reload(avisos)
    monkeypatch.setattr(avisos, "SALIDA", tmp_path / "out")
    texto = (F / "borme_2026_alicante.txt").read_text(encoding="utf-8")
    ctx = {"identificador": "BORME-A-2026-210-03", "provincia_codigo": "03",
           "fecha": "2026-11-02", "url_pdf": "https://www.boe.es/x.pdf"}
    regs = [r for n, l in parser.separar_entradas(texto) if (r := parser.analizar_entrada(n, l, ctx))]
    const = [r for r in regs if r["es_constitucion"]]
    almacen.guardar_dia("2026-11-02", {"fecha": "2026-11-02", "total_constituciones": len(const),
                                       "por_provincia": {"03": len(const)},
                                       "constituciones": [parser.ficha_publica(r) for r in const]},
                        {"fecha": "2026-11-02", "registros": regs, "calidad": {}})
    return almacen, avisos, tmp_path


def _correos(ruta):
    return [email.message_from_bytes(p.read_bytes()) for p in sorted((ruta / "out").glob("*.eml"))]


def test_filtros_y_envio(entorno, monkeypatch):
    almacen, avisos, tmp = entorno
    from nacenempresas import suscriptores
    monkeypatch.setenv("SUSCRIPTORES_MANUAL", json.dumps([
        {"email": "gestoria@example.com", "plan": "pro", "provincias": "Alicante", "actividad": "hostelería"},
        {"email": "seguros@example.com", "plan": "basico", "provincias": ["Alicante"], "actividad": "reformas, construccion"},
        {"email": "madrid@example.com", "plan": "basico", "provincias": "Madrid"},
    ]))
    subs = suscriptores.todos()
    assert subs[0].sectores == ["hosteleria"]
    cartero = avisos.Cartero(prueba=True)
    stats = avisos.enviar_avisos(date(2026, 11, 2), subs, cartero)
    assert stats["diarios"] == 2 and stats["sin_coincidencias"] == 1
    correos = _correos(tmp)
    assert len(correos) == 2
    pro = next(c for c in correos if c["To"] == "gestoria@example.com")
    partes = list(pro.walk())
    html_ = next(p for p in partes if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    assert "KALADISE SL" in html_ and "SMART BOX" not in html_
    assert any(p.get_filename() and p.get_filename().endswith(".csv") for p in partes)
    basico = next(c for c in correos if c["To"] == "seguros@example.com")
    assert not any(p.get_filename() for p in basico.walk())  # el básico no lleva CSV
    todo = "".join(p.read_text(errors="ignore") for p in (tmp / "out").glob("*.eml"))
    for persona in ["ENGLAND", "NATILE", "RUIZ SOLER", "HUESCA"]:
        assert persona not in todo


def test_csv_excel(entorno):
    almacen, avisos, _ = entorno
    regs = almacen.cargar_completo("2026-11-02")["registros"]
    datos = avisos.csv_bytes([r for r in regs if r["es_constitucion"]]).decode("utf-8")
    assert datos.startswith("﻿denominacion;")
    assert "PTDA LA MARINA 22 (ELCHE/ELX)" in datos


def test_cifrado(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_KEY", Fernet.generate_key().decode())
    import importlib
    from nacenempresas import almacen
    importlib.reload(almacen)
    almacen.guardar_dia("2026-11-03", {"total_constituciones": 0}, {"registros": [{"x": "SECRETO"}]})
    enc = (tmp_path / "privado" / "2026-11-03.json.gz.enc").read_bytes()
    assert b"SECRETO" not in enc
    assert almacen.cargar_completo("2026-11-03")["registros"][0]["x"] == "SECRETO"


def test_prueba_recortada(entorno):
    """En prueba: como mucho N sociedades (5 en producción), sin domicilio, sin enlace al BORME y sin CSV."""
    almacen, avisos, tmp = entorno
    from nacenempresas import suscriptores
    regs = almacen.cargar_completo("2026-11-02")["registros"]
    total = sum(1 for r in regs if r["es_constitucion"])
    assert total == 3
    sub = suscriptores.Suscriptor(id="sub_t", email="prueba@example.com", plan="pro", estado="trialing",
                                  provincias=["03"], bienvenida_enviada=True, tiene_pago=True)
    cartero = avisos.Cartero(prueba=True)
    cartero.cfg = {**cartero.cfg, "precios": {**cartero.cfg["precios"], "empresas_prueba_dia": 2}}
    stats = avisos.enviar_avisos(date(2026, 11, 2), [sub], cartero)
    assert stats["diarios"] == 1
    c = _correos(tmp)[0]
    assert c["Subject"].startswith(f"{total} sociedades")  # el título enseña el total real
    partes = list(c.walk())
    assert not any(p.get_filename() for p in partes)  # sin CSV aunque sea Pro
    html_ = next(p for p in partes if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    assert html_.count("<tr>") == 2
    assert f"2 de {total}" in html_
    assert "PTDA LA MARINA 22" not in html_ and "boe.es/x.pdf" not in html_
    nombres = [r["denominacion"] for r in regs if r["es_constitucion"]]
    assert not any(n in html_ for n in nombres)  # nombre completo oculto
    assert "€" not in html_.split("Gestiona tu suscripción")[0]  # sin capital
    texto = next(p for p in partes if p.get_content_type() == "text/plain").get_payload(decode=True).decode()
    assert not any(n in texto for n in nombres)


def test_nombre_parcial():
    from nacenempresas.ocultar import nombre_parcial
    assert nombre_parcial("CONSTRUCCIONES GARCIA PEREZ SL") == "CONSTRUCCIONES G••• P••• SL"
    assert nombre_parcial("ACMETECH SOCIEDAD LIMITADA") == "ACM••• SOCIEDAD LIMITADA"
    assert nombre_parcial("BAR DE LA PLAZA S.L.") == "BAR DE LA P••• S.L."
    assert nombre_parcial("XY SL") == "X••• SL"
