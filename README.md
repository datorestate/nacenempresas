# NacenEmpresas

Avisos diarios de sociedades recién creadas en España a partir del BORME, una web con páginas por provincia y sector y calculadoras para crear empresa, y un Actor de Apify. Todo funciona con coste cero sobre GitHub Actions, GitHub Pages, Stripe y un SMTP gratuito.

**Para ponerlo en marcha, sigue [LANZAMIENTO.md](LANZAMIENTO.md).**

## Cómo funciona

```
07:20 lunes-viernes (GitHub Actions)
  API sumario BORME ─► 52 PDFs sección A ─► parser (sin personas físicas)
        │                                      │
        │                    data/publico/AAAA-MM-DD.json   (fichas sin domicilio: web)
        │                    data/privado/AAAA-MM-DD.json.gz.enc (completo, cifrado)
        ▼
  Stripe (suscripciones y campos del alta) ─► avisos.py ─► email HTML + CSV por cliente
        │                                                   bienvenida con muestra de 7 días
        │                                                   aviso de fin de prueba
        │                                                   entrega de listas compradas
        ▼
  sitio_web.py ─► GitHub Pages (portada, 52 provincias, provincia+sector, informe, calculadoras)
```

- **Prueba recortada:** 7 días con tarjeta obligatoria (primer cobro el día 8). Mientras la suscripción está en `trialing`, los avisos llevan como mucho 5 sociedades al día (`precios.empresas_prueba_dia`), sin domicilio, sin enlace al PDF del BORME, sin CSV ni señales.
- **Sin base de datos:** Stripe es la lista de clientes. Cada alta trae provincia, actividad y frecuencia en los campos del Payment Link.
- **Sin personas físicas:** el parser descarta empresarios individuales y nunca guarda nombres de cargos; los textos libres que pueden citar personas no se conservan. Los tests lo comprueban.
- **Repositorio público sin regalar el producto:** la web solo muestra 25 fichas por provincia y sin domicilio; los datos completos van cifrados con `DATA_KEY`.
- **Vigilancia:** si cae el porcentaje de actos reconocidos o un día con BORME sale con cero constituciones, el workflow falla y GitHub te envía un email.

## Estructura

| Ruta | Qué es |
| --- | --- |
| `nacenempresas/borme_api.py` | Cliente de la API de sumarios del BOE (JSON, con respaldo XML) |
| `nacenempresas/parser.py` | PDF → actos estructurados: constituciones y eventos con señal de oportunidad o riesgo |
| `nacenempresas/sectores.py` | Clasificación del objeto social en 19 sectores |
| `nacenempresas/pipeline.py` | Tarea diaria y control de calidad |
| `nacenempresas/suscriptores.py` | Clientes desde Stripe y clientes manuales |
| `nacenempresas/avisos.py` | Correos, CSV, bienvenida, fin de prueba, listas puntuales, informe al titular |
| `nacenempresas/sitio_web.py` | Generador de la web estática |
| `scripts/setup_stripe.py` | Crea productos, precios, IVA, enlaces de pago y portal (idempotente) |
| `apify/` | Actor "Spain New Companies & Corporate Events (BORME)" |
| `ventas/` | Guion de llamada, cartas, plan de LinkedIn, alianzas y hoja de seguimiento |
| `legal/` | Aviso legal, privacidad, condiciones, retirada de datos |

## Desarrollo

```bash
pip install -r requirements-dev.txt
python -m pytest -q                                  # 17 tests, sin red
python -m nacenempresas.pipeline --fecha 2026-11-03  # requiere acceso a boe.es
python -m nacenempresas.avisos --prueba              # deja los correos en out/correos/*.eml
RC_DATA_DIR=/tmp/demo python scripts/datos_ejemplo.py && RC_DATA_DIR=/tmp/demo RC_VISTA_PREVIA=1 python -m nacenempresas.sitio_web
```

## Secretos del repositorio

| Secreto | Para qué |
| --- | --- |
| `DATA_KEY` | Cifrado de los datos completos |
| `STRIPE_SECRET_KEY` | Cobros y lista de clientes |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`, `REPLY_TO` | Envío de correos |
| `OWNER_EMAIL` | Informe diario de clientes y MRR |
| `SUSCRIPTORES_MANUAL` | JSON con clientes piloto: `[{"email": "...", "plan": "pro", "provincias": "Málaga, Sevilla", "actividad": "hostelería"}]` |
| `STRIPE_TAX_RATE` | Opcional: tipo de IGIC de Stripe; por defecto, el creado por `setup_stripe.py` |

Variable opcional `SITE_URL` si usas dominio propio.

## Fiscalidad: prestador en Canarias

El titular está establecido en Canarias (`config/sitio.json` > `fiscal`). Los precios no llevan impuestos indirectos: a empresas de la Península y Baleares, operación no sujeta al IGIC con inversión del sujeto pasivo del IVA; a empresas canarias, exenta de IGIC mientras el titular esté en el régimen del pequeño empresario (hasta 50.000 €). `nacenempresas/fiscal.py` detecta la región del cliente por su dirección de facturación, pone la mención legal en sus facturas y, si el titular sale del régimen, aplica el IGIC del 7 % solo a clientes canarios. Solo se vende a empresas y profesionales (NIF obligatorio).

## Normativa usada en las calculadoras (revisión 5/11/2026)

- RETA 2026: tramos de 2025 prorrogados por el RDL 3/2026, MEI 0,9 %, tipo total 31,5 %; base mínima de societarios 1.424,40 €/mes; tarifa plana 80 €/mes.
- Impuesto sobre Sociedades 2026: 15 % entidades de nueva creación; microempresas 19 % (primeros 50.000 €) y 21 %; general 25 % (DT 44.ª LIS, Ley 7/2024).
- IRPF: escala estatal más autonómica media; ahorro 19-30 %; gastos de difícil justificación 5 % con límite de 2.000 €.
- Canarias: IGIC general 7 % (Ley 20/1991, Ley 4/2012); régimen del pequeño empresario hasta 50.000 € desde el 1/7/2026 (Decreto ley 3/2026); cuota cero del Gobierno de Canarias; RIC hasta el 90 % del beneficio no distribuido (art. 27 Ley 19/1994).

Fuente de datos: BORME, Agencia Estatal BOE. Servicio no oficial.
