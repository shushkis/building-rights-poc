# Unused Building Rights — Israel
### Proof of concept: Old North, Tel Aviv · 2,318 buildings · ₪5.8B–11.6B identified

---

## The problem

Tel Aviv's **תא/3616א ("Rova 3")**, in force since **2018-01-09**, granted thousands of
existing buildings the right to add floors. Those rights are public, legally defined,
and written into a rights table.

Nobody knows which buildings hold how much.

Answering it per building means joining seven municipal GIS layers — footprints, land-use
lots, parcels, permits, preservation listings, plan polygons, address points — against a
legal rights table with street-specific branches, then subtracting rights already
exercised. Today that work is done by hand, one address at a time, by appraisers and
developers' analysts.

## What we built

A pipeline that does it for an entire neighbourhood in ten seconds, and shows its work.

| | |
|---|---|
| Buildings analysed | **2,318** (100% of the AOI) |
| With unexploited rights | **931** |
| Unexploited area (cited clauses) | **357,426 m²** |
| Net value to rights-holders | **₪5.81B – ₪11.62B** |
| Analysed at HIGH confidence | **58.8%** |
| Additional tiers, held separate | ₪1.19B–2.37B mixed-use (unconfirmed) · 41,825 m² inferred upside |

Every building carries a `rule_id` tracing it to a specific plan clause. Every value is a
range. Every exclusion is named and visible, never a silent drop.

## Data sources — all public, all official

| Source | Use |
|---|---|
| Tel Aviv-Yafo GIS (`gisn.tel-aviv.gov.il`, ArcGIS REST, no auth) | buildings, lots, parcels, permits, preservation, plans, addresses |
| Plan תא/3616א, verified in force from the live TABA layer | the rights table |
| Published court ruling quantifying a test case | model calibration |
| Published market price research | ₪/m² benchmark (±11% band) |

No scraping of private sources. No licensed data. The same layer structure is published
nationally through GovMap, which is what makes this scale.

## Accuracy — including what's weak

**Calibration: PASS.** A court ruling quantified a 4-floor building on a sub-500 m² lot at
~369 m². Run blind over 290 comparable buildings, the model's median is **319 m² — 13.6%
off**, inside the ±20% gate set in advance.

**Also true, and published in the validation memo:**

- Footprint is used as a proxy for added floor area — biases results **upward 5–15%**.
- The DSM height cross-check carries ±1.7 floors of noise; it corroborates the municipal
  floor count, it cannot replace it.
- Height-model corroboration reaches 76.6% against an 80% target — **below target, stated**.
- The 1-floor entitlement is inferred from the 2-floor clause, not cited. Those buildings
  are **excluded from every headline figure**.
- 97 buildings on Dizengoff/Ben Yehuda sit on commercially-designated lots. The plan grants
  those streets its best terms and they are mixed-use in practice, but per-lot residential
  eligibility is **unconfirmed** — reported as its own tier, never folded in.
- No human appraiser has verified the output yet. A stratified 15-building worksheet is
  built and waiting for that review.

The discipline is the product. A number an investor cannot attack is a number they cannot
trust.

## Competitive context

| | |
|---|---|
| **UpFactor** (France) | €2.5M raised — rooftop/vertical extension potential |
| **Syte** (Germany) | €5M raised — AI property-potential analysis |
| **Spacemaker** (Norway) | $240M exit to Autodesk — generative site design |

Each proves the category. **None operates in Israel** — a market with unusually good public
planning data, a national urban-renewal push, and among the highest ₪/m² values anywhere.

## Roadmap

1. **Now** — Old North validated; appraiser sign-off on the 15-building sample.
2. **Next** — all of Rova 3 + Rova 4 (~5× the buildings, zero new code).
3. **Then** — all of Tel Aviv-Yafo; wire live deal prices from nadlan.
4. **National** — GovMap publishes the TABA layer countrywide. The rule engine is the only
   per-city work, and it is a few hundred lines.

**Product surfaces:** ranked acquisition target lists for developers · instant rights
screening for appraisers and lenders · portfolio-wide latent-value reporting for owners.

---

*Reproduce everything: `python -m poc.run`, then `cd poc/demo && python -m http.server 8000`.
Full method in `data/out/qa_report.md`; every known weakness in `data/out/validation_memo.md`.*
