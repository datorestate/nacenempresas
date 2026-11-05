"""Pipeline completo sin red: API y PDFs simulados, y construcción de la web."""
import importlib
from datetime import date
from pathlib import Path

F = Path(__file__).parent / "fixtures"


def test_pipeline_y_web(tmp_path, monkeypatch):
    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("DATA_KEY", raising=False)
    from nacenempresas import almacen, borme_api, pipeline, sitio_web
    importlib.reload(almacen); importlib.reload(pipeline); importlib.reload(sitio_web)
    doc = borme_api.DocumentoA("BORME-A-2015-27-10", "10", "CÁCERES", "https://www.boe.es/x.pdf", "2015-02-10")
    monkeypatch.setattr(borme_api, "documentos_seccion_a", lambda dia, s=None: [doc] if dia == date(2015, 2, 10) else [])
    monkeypatch.setattr(borme_api, "descargar_pdf", lambda d, s=None: (F / "BORME-A-2015-27-10.pdf").read_bytes())
    assert pipeline.main(["--fecha", "2015-02-10"]) == 0
    pub = almacen.cargar_publico("2015-02-10")
    assert pub["total_constituciones"] == 8 and pub["por_provincia"] == {"10": 8}
    assert "domicilio" not in str(pub["constituciones"][0])
    assert pipeline.main(["--fecha", "2015-02-11"]) == 0  # día sin BORME
    monkeypatch.setattr(sitio_web, "SALIDA", tmp_path / "_site")
    n = sitio_web.construir(date(2015, 2, 10))
    assert n > 60
    caceres = (tmp_path / "_site" / "provincias" / "caceres.html").read_text("utf-8")
    assert "SERCAR 33 CACERES SL" in caceres and "MOLINO HARINERO" not in caceres
    assert (tmp_path / "_site" / "sitemap.xml").exists()
    for pagina in ["index.html", "calculadoras/autonomo-o-sl.html", "privacidad.html", "informe.html"]:
        assert (tmp_path / "_site" / pagina).stat().st_size > 2000
