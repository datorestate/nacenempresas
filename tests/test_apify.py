"""El Actor de Apify nunca entrega el domicilio ni el enlace al PDF del BORME."""
import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _main():
    sys.modules.setdefault("apify", types.SimpleNamespace(Actor=object))
    spec = importlib.util.spec_from_file_location("actor_main", RAIZ / "apify" / "src" / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sin_domicilio_ni_pdf():
    m = _main()
    r = {"fecha_publicacion": "2026-11-05", "provincia": "Las Palmas", "provincia_codigo": "35",
         "denominacion": "EJEMPLO SL", "forma_juridica": "SL", "borme_id": "BORME-A-2026-213-35",
         "url_pdf": "https://www.boe.es/x.pdf", "hoja_registral": "GC-1"}
    for tipo in ("constitucion", "traslado"):
        ev = {"tipo": tipo, "senal": "oportunidad", "acto": "x", "domicilio": "C/ SECRETA 1",
              "municipio": "Telde", "objeto_social": "Hostelería", "capital": 3000.0}
        fila = m._plano(r, ev)
        assert "domicilio" not in fila and "url_pdf" not in fila
        assert "SECRETA" not in str(fila) and "boe.es" not in str(fila)
        assert fila["municipio"] == "Telde" and fila["borme_id"] == "BORME-A-2026-213-35"
