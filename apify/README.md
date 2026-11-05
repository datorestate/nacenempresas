# Spain New Companies & Corporate Events (BORME) — GDPR-safe

Every working day Spain's Companies Registry Gazette (**BORME**) publishes hundreds of new companies and thousands of corporate acts as PDFs, one per province. This Actor turns them into clean, structured records you can filter, export to CSV/Excel or send to your CRM.

## What you get

- **New companies (incorporations):** name, legal form, province, municipality, corporate purpose, share capital, start of operations, CNAE when published, management type (sole/joint directors) and a **sector classification** (hospitality, construction, real estate, tech, health…).
- **Corporate events:** office moves, capital increases and reductions, name and purpose changes, new websites, mergers, dissolutions, liquidations, insolvency and registry closures, each tagged as an **opportunity** or **risk** signal.
- The official BORME identifier of every record, so you can check it at boe.es.
- Need the registered address for postal mail or visits? It comes in the NacenEmpresas daily alerts: https://datorestate.github.io/nacenempresas

## GDPR-safe by design

The BORME names directors, attorneys and sole shareholders. **This Actor never outputs personal data**: person names are stripped, entries of individual entrepreneurs are skipped, and free-text fields that may name people (insolvency administrators, "other concepts") are dropped. Use it without building a personal-data processing pipeline.

## Typical uses

- Lead lists of brand-new companies for accounting firms, insurance brokers, banks, web agencies and B2B suppliers.
- Credit-risk and KYC monitoring of dissolutions, insolvencies and registry closures.
- Market research on company creation by province and sector.

## Input

| Field | Example |
|---|---|
| From / To date | `2026-11-02` – `2026-11-06` (max 31 days per run) |
| Provinces | `["Madrid", "Málaga", "46"]` (empty = all Spain) |
| What to extract | New companies / events / both |
| Sectors | `["hosteleria", "construccion"]` |
| Keywords | `["restaurante", "fotovoltaica"]` |

Leave dates empty to get the latest publication day.

## Output example

```json
{
  "fecha_publicacion": "2026-11-03", "provincia": "Málaga", "denominacion": "EJEMPLO GASTRO SL",
  "forma_juridica": "SL", "tipo": "constitucion", "senal": "oportunidad",
  "municipio": "Marbella", "capital": 3000.0,
  "objeto_social": "Explotación de bares y restaurantes", "sector": "hosteleria",
  "organo_administracion": ["Adm. Unico"], "borme_id": "BORME-A-2026-211-29"
}
```

## Pricing

Pay per result: **$1.50 per 1,000 records**, with no platform usage on top. A typical day for all of Spain has about 500 new companies (about $0.75); one province is usually a few cents. You can cap the cost of any run with the maximum charge option.

## Notes

Source: BORME, Agencia Estatal Boletín Oficial del Estado (boe.es), reused under its terms. Not an official service. If you contact these companies by email, Spanish law (LSSI art. 21) requires their prior consent; postal mail and phone are the usual channels.

Want it in your inbox every morning instead? See NacenEmpresas.
