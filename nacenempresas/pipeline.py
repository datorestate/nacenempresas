"""Tarea diaria: descarga el BORME del día, extrae los actos y guarda los datos.

Uso:
    python -m nacenempresas.pipeline                 # hoy (hora de Madrid)
    python -m nacenempresas.pipeline --fecha 2026-11-03
    python -m nacenempresas.pipeline --ultimos 10     # rellena los últimos 10 días

Códigos de salida: 0 bien; 2 extracción sospechosa (avisa por email de GitHub al fallar).
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import almacen, borme_api, parser

UMBRAL_RECONOCIDO = 85.0


def hoy_madrid() -> date:
    return datetime.now(ZoneInfo("Europe/Madrid")).date()


def procesar_dia(dia: date, sesion=None) -> dict | None:
    docs = borme_api.documentos_seccion_a(dia, sesion)
    if not docs:
        print(f"{dia}: sin BORME (fin de semana o festivo)")
        return None
    registros, calidad = [], {}
    for doc in docs:
        try:
            pdf = borme_api.descargar_pdf(doc, sesion)
            res = parser.analizar_pdf(pdf, doc.identificador, doc.provincia_codigo,
                                      doc.fecha, doc.url_pdf)
        except Exception as e:  # un PDF roto no debe tumbar el día entero
            calidad[doc.identificador] = {"error": str(e)[:300]}
            print(f"  ERROR {doc.identificador}: {e}", file=sys.stderr)
            continue
        registros.extend(res["registros"])
        calidad[doc.identificador] = res["calidad"]
        print(f"  {doc.identificador} {doc.titulo}: {res['calidad']}")

    const = [r for r in registros if r["es_constitucion"]]
    por_prov = collections.Counter(r["provincia_codigo"] for r in const)
    por_sector = collections.Counter(
        next(e for e in r["eventos"] if e["tipo"] == "constitucion")["sector"] for r in const)
    eventos = collections.Counter(e["tipo"] for r in registros for e in r["eventos"])
    publico = {
        "fecha": dia.isoformat(),
        "total_constituciones": len(const),
        "total_actos": len(registros),
        "por_provincia": dict(por_prov),
        "por_sector": dict(por_sector),
        "eventos": dict(eventos),
        "constituciones": [parser.ficha_publica(r) for r in const],
    }
    completo = {"fecha": dia.isoformat(), "registros": registros, "calidad": calidad}
    almacen.guardar_dia(dia.isoformat(), publico, completo)
    return {"publico": publico, "calidad": calidad}


def comprobar_calidad(resultado: dict) -> list[str]:
    avisos = []
    errores = [k for k, v in resultado["calidad"].items() if "error" in v]
    if errores:
        avisos.append(f"{len(errores)} PDF con error: {', '.join(errores[:5])}")
    bajos = [k for k, v in resultado["calidad"].items()
             if "porcentaje_reconocido" in v and v["entradas"] >= 10
             and v["porcentaje_reconocido"] < UMBRAL_RECONOCIDO]
    if bajos:
        avisos.append(f"Reconocimiento bajo (<{UMBRAL_RECONOCIDO}%) en: {', '.join(bajos[:5])}")
    if resultado["publico"]["total_actos"] > 200 and resultado["publico"]["total_constituciones"] == 0:
        avisos.append("Cero constituciones en un día con BORME: posible cambio de formato")
    return avisos


def _resumen_github(lineas):
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--ultimos", type=int, default=0)
    ap.add_argument("--forzar", action="store_true", help="vuelve a procesar días ya guardados")
    a = ap.parse_args(argv)
    fin = date.fromisoformat(a.fecha) if a.fecha else hoy_madrid()
    dias = [fin - timedelta(days=i) for i in range(max(a.ultimos, 1))][::-1]
    sesion = borme_api._sesion()
    fallo = False
    resumen = ["## BORME procesado", ""]
    for d in dias:
        if a.ultimos and not a.forzar and almacen.cargar_publico(d.isoformat()):
            continue
        res = procesar_dia(d, sesion)
        if not res:
            resumen.append(f"- {d}: sin publicación")
            continue
        p = res["publico"]
        avisos = comprobar_calidad(res)
        resumen.append(f"- {d}: **{p['total_constituciones']} constituciones**, {p['total_actos']} actos")
        for av in avisos:
            resumen.append(f"  - ⚠️ {av}")
        fallo = fallo or any("Cero constituciones" in av or "Reconocimiento bajo" in av for av in avisos)
    _resumen_github(resumen)
    print("\n".join(resumen))
    return 2 if fallo else 0


if __name__ == "__main__":
    sys.exit(main())
