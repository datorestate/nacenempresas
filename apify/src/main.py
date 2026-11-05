"""Apify Actor: Spain New Companies & Corporate Events (BORME), GDPR-safe."""
import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apify import Actor

from nacenempresas import borme_api, parser
from nacenempresas.provincias import lista_provincias, normaliza

EVENTO = "result"  # evento de cobro por resultado (pay-per-event en Apify Console)

# Sin domicilio ni enlace al PDF del BORME (que lo contiene): eso es lo que se vende en la
# suscripción de NacenEmpresas. El Actor da el resto, más el identificador del BORME.
NUNCA = ("domicilio", "url_pdf")


def _plano(r, ev):
    base = {k: r.get(k) for k in ("fecha_publicacion", "provincia", "provincia_codigo", "denominacion",
                                  "forma_juridica", "borme_id", "hoja_registral", "fecha_inscripcion")}
    base.update({"tipo": ev["tipo"], "senal": ev["senal"], "acto": ev["acto"]})
    for k in ("objeto_social", "municipio", "capital", "cnae", "sector", "comienzo_operaciones",
              "organo_administracion", "unipersonal", "importe", "capital_resultante", "nueva_denominacion", "detalle"):
        if k in ev:
            base[k] = ev[k]
    for k in NUNCA:
        base.pop(k, None)
    return base


async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
        hasta = date.fromisoformat(inp["dateTo"][:10]) if inp.get("dateTo") else hoy
        desde = date.fromisoformat(inp["dateFrom"][:10]) if inp.get("dateFrom") else hasta - timedelta(days=4 if not inp.get("dateTo") else 0)
        desde = max(desde, hasta - timedelta(days=31))
        provs = set(lista_provincias(",".join(inp.get("provinces") or []), 52))
        modo = inp.get("mode", "incorporations")
        secs = set(inp.get("sectors") or [])
        palabras = [normaliza(p) for p in inp.get("keywords") or [] if p.strip()]
        sesion = borme_api._sesion()
        total, solo_ultimo = 0, not inp.get("dateFrom") and not inp.get("dateTo")
        d = hasta
        dias = []
        while d >= desde:
            dias.append(d)
            d -= timedelta(days=1)
        # Sin fechas: el día publicado más reciente (se recorre de hoy hacia atrás)
        for dia in sorted(dias, reverse=solo_ultimo):
            docs = [x for x in borme_api.documentos_seccion_a(dia, sesion) if not provs or x.provincia_codigo in provs]
            if not docs:
                continue
            Actor.log.info(f"{dia}: {len(docs)} provincial PDFs")
            for doc in docs:
                try:
                    res = parser.analizar_pdf(borme_api.descargar_pdf(doc, sesion), doc.identificador,
                                              doc.provincia_codigo, doc.fecha, doc.url_pdf)
                except Exception as e:  # noqa: BLE001
                    Actor.log.warning(f"{doc.identificador}: {e}")
                    continue
                filas = []
                for r in res["registros"]:
                    for ev in r["eventos"]:
                        es_const = ev["tipo"] == "constitucion"
                        if (modo == "incorporations" and not es_const) or (modo == "events" and es_const):
                            continue
                        if ev["tipo"] in ("otro", "cambio_cargos", "unipersonalidad"):
                            continue
                        if secs and es_const and ev.get("sector") not in secs:
                            continue
                        if palabras:
                            texto = normaliza(r["denominacion"] + " " + (ev.get("objeto_social") or ""))
                            if not any(p in texto for p in palabras):
                                continue
                        filas.append(_plano(r, ev))
                if filas:
                    try:
                        await Actor.push_data(filas, charged_event_name=EVENTO)
                    except TypeError:  # SDK sin pay-per-event
                        await Actor.push_data(filas)
                    total += len(filas)
            if solo_ultimo and total:
                break
        Actor.log.info(f"Done: {total} records")


if __name__ == "__main__":
    asyncio.run(main())
