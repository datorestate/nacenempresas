# Puesta en marcha: lo que solo puedes hacer tú

Todo el producto está construido y probado. Ya eres autónomo en Canarias (RETA, REPEP) y tienes Stripe, así que lo que queda es conectar las piezas: unos 45 minutos, repartidos en dos días. Coste: 0 €, y NacenEmpresas no te añade cuota de autónomos porque ya la pagas.

## Día 1 (30 minutos): la web en marcha con datos reales

1. **Repositorio en GitHub.** Entra en github.com (o crea cuenta gratis) y crea un repositorio **público** llamado `nacenempresas`, vacío. Dime tu usuario de GitHub y lo subo yo; o sube el contenido del zip.
2. **Activar la web.** En el repositorio: Settings > Pages > Source: **GitHub Actions**.
3. **Clave de cifrado.** Settings > Secrets and variables > Actions > New repository secret: `DATA_KEY` con el valor del archivo `SECRETOS_NO_SUBIR.txt`. Añade también `OWNER_EMAIL` con tu email (recibirás el informe diario de clientes).
4. **Primer llenado.** Pestaña Actions > "Diario BORME" > Run workflow, con **dias = 30**. Tarda unos 20 minutos. Al terminar, la web está en `https://TU-USUARIO.github.io/nacenempresas` con las sociedades reales del último mes en las 52 provincias.
5. **Tus datos legales.** Pásame nombre, NIF, domicilio en Canarias y el email de contacto que quieres usar y actualizo `config/sitio.json` (el aviso legal los exige por la LSSI).

A partir de aquí, cada mañana laborable la web se actualiza sola y GitHub te avisa por email si algo falla.

## Día 2 (30 minutos): cobrar y enviar

6. **Correo de envío.** Crea un Gmail dedicado (por ejemplo, `nacenempresas.avisos@gmail.com`), activa la verificación en dos pasos y genera una "contraseña de aplicación". Añade los secretos:
   `SMTP_HOST` = `smtp.gmail.com` · `SMTP_PORT` = `587` · `SMTP_USER` = el Gmail · `SMTP_PASS` = la contraseña de aplicación · `FROM_EMAIL` = el Gmail.
   Gmail admite unos 500 envíos al día; cuando pases de 100 clientes, cambia a Brevo (gratis hasta 300/día) con tus propios datos SMTP.
7. **Stripe (tu cuenta actual).** NacenEmpresas convive con lo que ya tengas: solo toca los productos, precios y enlaces que crea él, marcados con metadatos propios, y solo lee las suscripciones de sus dos planes. No modifica nada de tu otra actividad.
   - **Usa una clave restringida, no la secreta completa.** En Developers > API keys > Create restricted key, llámala "NacenEmpresas" y da permiso de **escritura** a Products, Prices, Payment Links, Tax Rates, Customer portal, Subscriptions, Customers y PaymentIntents, y de **lectura** a Checkout Sessions. Lo demás, sin acceso. Crea una en modo de prueba (`rk_test_…`) y otra en real (`rk_live_…`). Si falta algún permiso, la ejecución de "Configurar Stripe" falla diciendo cuál; añádelo y repite.
   - Pon la de prueba en el secreto `STRIPE_SECRET_KEY` y ejecuta Actions > "Configurar Stripe". Crea los productos, los precios sin impuestos, un tipo de IGIC que no se usa mientras estés en el REPEP, los enlaces de pago con prueba de 14 días sin tarjeta y NIF obligatorio, y una configuración del portal del cliente solo para estos planes. Luego los pone en la web.
   - Haz dos altas de prueba: una con un NIF de persona física (por ejemplo `12345678Z`) y otra con un CIF de sociedad. Comprueba que el pago acepta los dos, porque muchas gestorías son autónomos. Si rechaza el NIF personal, dímelo y lo dejo opcional.
   - Cuando funcione, cambia el secreto por la clave real y vuelve a ejecutar "Configurar Stripe".
   - **Lo que comparte con tu otra actividad:** el nombre público, el logo, el descriptor del extracto bancario y el email de soporte son de toda la cuenta. Si hoy dicen el nombre de tu otro negocio, tus clientes de NacenEmpresas lo verán en el pago, el recibo y el extracto. Ponle un nombre que cubra las dos cosas (por ejemplo tu nombre y "NacenEmpresas") o, si prefieres separarlas del todo, crea una segunda cuenta dentro de Stripe (menú de la cuenta > New account), gratis y con tu mismo NIF.
   - Las menciones legales de cada factura (sin IVA por inversión del sujeto pasivo para la Península, exenta de IGIC para Canarias) las pone el sistema según la dirección del cliente. Comprueba solo que en Settings > Business details figuran tu NIF y tu domicilio en Canarias.
8. **Google Search Console.** Añade la web, verifica con la etiqueta HTML que te den (pásamela y la incluyo) y envía `sitemap.xml`. Es lo que hace que Google indexe las 150+ páginas de provincia y sector.

## Antes del primer cobro

9. **Encajar la nueva actividad en tus altas.** Ya estás en el RETA y en el REPEP, así que no hay altas nuevas. Solo hay que comprobar dos cosas:
   - **Epígrafe del IAE.** Si tu epígrafe actual no cubre un servicio de información por suscripción, añade uno con un 036 de modificación ante la Agencia Tributaria y un 400 de modificación ante la Agencia Tributaria Canaria. Conviene que sea **empresarial** (sección primera), no profesional: así tus clientes no tienen que retenerte IRPF y el cobro automático con tarjeta funciona.
   - **Límite de 50.000 € del REPEP.** El límite cuenta el volumen de operaciones de todas tus actividades juntas. Si tu otra actividad ya se acerca a esa cifra, NacenEmpresas puede hacerte salir del régimen. En ese caso, cambia `igic_pequeno_empresario` a `false` en `config/sitio.json` y el sistema sumará el 7 % de IGIC solo a los clientes canarios. A los de la Península no se les cobra IGIC ni IVA en ningún caso.
10. **Una consulta con tu gestoría** (lleva estas preguntas):
    1. ¿Mi epígrafe actual cubre un servicio de información por suscripción, o añado uno empresarial?
    2. ¿Cuentan para los 50.000 € del REPEP las ventas a empresas de la Península, que no llevan IGIC?
    3. ¿Son correctas las menciones de factura que pone el sistema? (están en `nacenempresas/fiscal.py`)
    4. ¿Cómo declaro en IGIC las comisiones de Stripe, Google o Apify, que me facturan desde fuera de Canarias?
    5. ¿Tengo que presentar el modelo 415 de operaciones con terceros?
    6. ¿Qué tengo que cambiar en la facturación de Stripe para cumplir Veri*factu, obligatorio para autónomos desde el 1 de julio de 2027?
11. **Protección de datos.** El sistema excluye a las personas físicas por diseño. Aun así, haz una consulta breve a un experto en protección de datos antes de crecer (el plan lo dejaba pendiente y sigue siendo recomendable).

## Opcional (cuando haya tiempo)

- **Apify:** crea cuenta, Actors > Create > Link Git repository, carpeta `apify`. Precio: pay-per-event, evento `result`, 2 $ por 1.000. Publícalo en la Store con el README incluido. Lo que te pague Apify (empresa extranjera) no lleva IGIC; coméntalo con la gestoría.
- **Afiliados:** solicita los programas de gestorías online, bancos de empresa y software de facturación, y pega tus enlaces en `config/sitio.json` > `afiliados`.
- **Estadística de visitas:** cuenta gratis en GoatCounter y pon el código en `config/sitio.json` > `analitica`.
- **Dominio propio** (`nacenempresas.es`, unos 10 €/año): el primer gasto que recomiendo, cuando entre el primer cliente.

## Y desde el día 3: vender

Sigue `ventas/guion_llamada.md`. Las dos primeras semanas, Canarias: visitas a gestorías, asesorías y corredurías de tu isla y llamadas a las demás islas (el plan Básico cubre las dos provincias canarias). Desde la tercera, 20 llamadas al día a las provincias peninsulares con más altas, de 9:00 a 12:00 hora canaria. Es lo que convierte el sistema en ingresos.
