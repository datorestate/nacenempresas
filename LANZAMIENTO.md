# Puesta en marcha

Estado a 5/11/2026: **todo funciona y ya se puede cobrar.** Coste: 0 €.

## Hecho

- Web pública con datos reales del BORME en las 52 provincias: https://datorestate.github.io/nacenempresas (se actualiza sola cada mañana laborable a las 7:20 UTC, con reintento a las 10:30).
- Repositorio `datorestate/nacenempresas`, GitHub Pages y los 8 secretos (`DATA_KEY`, `STRIPE_SECRET_KEY`, `SMTP_*`, `FROM_EMAIL`, `OWNER_EMAIL`).
- Cuenta de Stripe **NacenEmpresas** separada de tu otra actividad, activada, con descriptor NACENEMPRESAS, marca, correos en español, facturas con prefijo NACEN y pie con las menciones fiscales.
- Clave restringida "NacenEmpresas GitHub Actions" (solo los 9 permisos necesarios) y enlaces de pago en modo real: Básico 19 €/mes o 190 €/año, Pro 49 €/mes o 490 €/año, lista puntual 29 €. Prueba de 7 días con tarjeta (primer cobro el día 8) y avisos recortados durante la prueba (5 empresas al día, sin domicilio), NIF/CIF obligatorio, provincia (Canarias primero), actividad y frecuencia. Portal del cliente para darse de baja.
- Aviso legal, privacidad y condiciones con tu nombre, NIF y domicilio en Telde. NIF en las facturas de Stripe.
- Correo: el envío por Gmail funciona (el 5/11 salió el primer informe diario a tu correo).
- Google Search Console verificado (etiqueta meta en la portada), `sitemap.xml` enviado y solicitada la indexación de la portada y de la página de Canarias. Bing recibe las páginas por IndexNow tras cada publicación, sin cuenta.
- Cupón "Colegios: 20 % durante 3 meses" con los códigos `GESTORESCANARIAS` y `COLEGIO20`, válidos en todos los enlaces de pago ("Añadir código").

## Lo que queda (solo tú)

1. **Prueba real de alta.** Abre el plan Básico desde la web, date de alta con otro correo tuyo y comprueba que llegan el correo de bienvenida y, la mañana laborable siguiente, el aviso (los dos recortados: 5 empresas, sin domicilio). Ahora pide tarjeta: **cancela desde el portal del cliente antes del día 8** o se cobrará el primer mes.
2. **Search Console en una semana:** mira Páginas e Indexación; si el sitemap sigue en "No se ha podido obtener", vuelve a enviarlo.

## Antes del primer cobro

3. **Encajar la nueva actividad en tus altas.** Ya estás en el RETA y en el REPEP, así que no hay altas nuevas. Solo hay que comprobar dos cosas:
   - **Epígrafe del IAE.** Si tu epígrafe actual no cubre un servicio de información por suscripción, añade uno con un 036 de modificación ante la Agencia Tributaria y un 400 de modificación ante la Agencia Tributaria Canaria. Conviene que sea **empresarial** (sección primera), no profesional: así tus clientes no tienen que retenerte IRPF y el cobro automático con tarjeta funciona.
   - **Límite de 50.000 € del REPEP.** El límite cuenta el volumen de operaciones de todas tus actividades juntas. Si tu otra actividad ya se acerca a esa cifra, NacenEmpresas puede hacerte salir del régimen. En ese caso, cambia `igic_pequeno_empresario` a `false` en `config/sitio.json` y el sistema sumará el 7 % de IGIC solo a los clientes canarios. A los de la Península no se les cobra IGIC ni IVA en ningún caso.
4. **Una consulta con tu gestoría** (lleva estas preguntas):
    1. ¿Mi epígrafe actual cubre un servicio de información por suscripción, o añado uno empresarial?
    2. ¿Cuentan para los 50.000 € del REPEP las ventas a empresas de la Península, que no llevan IGIC?
    3. ¿Son correctas las menciones de factura que pone el sistema? (están en `nacenempresas/fiscal.py`)
    4. ¿Cómo declaro en IGIC las comisiones de Stripe, Google o Apify, que me facturan desde fuera de Canarias?
    5. ¿Tengo que presentar el modelo 415 de operaciones con terceros?
    6. ¿Qué tengo que cambiar en la facturación de Stripe para cumplir Veri*factu, obligatorio para autónomos desde el 1 de julio de 2027?
5. **Protección de datos.** El sistema excluye a las personas físicas por diseño. Aun así, haz una consulta breve a un experto en protección de datos antes de crecer (el plan lo dejaba pendiente y sigue siendo recomendable).

## Opcional (cuando haya tiempo)

- **Apify:** Actor `nacenempresas/spain-new-companies-borme` creado y probado, privado. Sin domicilio ni enlace al PDF del BORME. Se recompila solo en cada `git push`. Cobro activo: 1,50 $ por 1.000 resultados (evento automático por fila) más el evento de inicio de Apify; el uso de la plataforma lo paga NacenEmpresas (unos 0,04 $ por 1.000). Cobro por PayPal. **Publicado** el 5/11/2026: https://apify.com/nacenempresas/spain-new-companies-borme. Apify lo prueba cada día con la entrada por defecto (toda España, último día: unos 2 min 40 s y 0,01 $ de uso). Lo que te pague Apify (empresa extranjera) no lleva IGIC; coméntalo con la gestoría.
- **Afiliados:** solicita los programas de gestorías online, bancos de empresa y software de facturación, y pega tus enlaces en `config/sitio.json` > `afiliados`.
- **Estadística de visitas:** cuenta gratis en GoatCounter y pon el código en `config/sitio.json` > `analitica`.
- **Dominio propio** (`nacenempresas.es`, unos 10 €/año): el primer gasto que recomiendo, cuando entre el primer cliente.

## Y desde ya: vender

Sigue `ventas/guion_llamada.md`. Las dos primeras semanas, Canarias: visitas a gestorías, asesorías y corredurías de tu isla y llamadas a las demás islas (el plan Básico cubre las dos provincias canarias). Desde la tercera, 20 llamadas al día a las provincias peninsulares con más altas, de 9:00 a 12:00 hora canaria. Es lo que convierte el sistema en ingresos.
