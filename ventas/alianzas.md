# Canales que multiplican sin coste

**Empieza por casa.** En Canarias eres local: los colegios y cámaras de las islas son pequeños y se llega a quien decide con una visita.

- **Colegio Oficial de Gestores Administrativos de Las Palmas** y **de Santa Cruz de Tenerife**: propón un descuento para colegiados (código `GESTORESCANARIAS`) y una charla corta sobre captar sociedades recién creadas.
- **Colegios de Mediadores de Seguros de Las Palmas y de Santa Cruz de Tenerife**: mismo esquema, con el filtro de hostelería, turismo y construcción, que pesan mucho en las islas.
- **Cámaras de Comercio de Gran Canaria y de Santa Cruz de Tenerife**: sus servicios de apoyo al emprendedor atienden a quien crea empresa; ofréceles las calculadoras de IGIC, cuota cero y RIC como recurso gratuito con enlace.
- **Prensa económica canaria**: el informe semanal da para una nota mensual del tipo "Canarias creó N sociedades en octubre".

**Después, el resto de España:**

1. **Colegios oficiales de gestores administrativos y asociaciones de asesores fiscales provinciales.** Ofrece a sus colegiados un 20 % de descuento con un código promocional de Stripe (los enlaces de pago ya aceptan códigos). Pide que lo incluyan en su boletín. Un solo boletín llega a cientos de despachos que ya han dado su consentimiento para recibirlo.
2. **Colegios de mediadores de seguros.** Mismo esquema, filtrando por hostelería, construcción y transporte.
3. **Software de despacho (programas de contabilidad para gestorías).** Propón un acuerdo de recomendación mutua: tú les mandas tráfico de las calculadoras y ellos mencionan los avisos.
4. **Prensa local.** El informe semanal (`/informe.html`) es una nota de prensa automática: "Málaga creó 312 empresas en octubre". Envíaselo a la sección de economía; los enlaces desde medios locales son lo que más posiciona las páginas de provincia.
5. **Apify Store.** El Actor lleva al final un enlace a la web; capta a quien quiere los datos por API.

## Código de descuento

En Stripe, Productos > Cupones > Crear (por ejemplo, 20 % durante 3 meses), y después un código de promoción como `COLEGIO20`. Ya funciona en todos los enlaces de pago.
