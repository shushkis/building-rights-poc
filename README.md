# Unused Building Rights PoC — Old North, Tel Aviv

Identifies unexploited building rights under **תא/3616א (Rova 3)** for every building in
הצפון הישן - החלק הצפוני, and renders the result as an investor-facing map.

**Headline:** 2,318 buildings analysed · 931 with unexploited rights · 357,426 m² ·
₪5.81B–₪11.62B · 58.8% at HIGH confidence.

## Quick start

```bash
pip install -r requirements.txt
python -m poc.run                       # full pipeline (~10s warm, few min cold)
cd poc/demo && python -m http.server 8000   # open http://localhost:8000
pytest                                  # 37 tests
```

> On Windows set `PYTHONIOENCODING=utf-8` — all source data is Hebrew and the default
> console codepage cannot encode it.

## Pipeline stages

| Stage | Module | Output |
|---|---|---|
| 1. Ingest | `poc/ingest/` | AOI + 8 layers from the TLV ArcGIS REST service → `data/processed/*.parquet` |
| 2. Rules | `poc/rules/` | rights table, exclusion flags, consumed-rights detection |
| 3. Gap | `poc/gap/` | as-built floors + confidence, gap_floors/gap_m² → `data/out/gaps.parquet` |
| 4. Value | `poc/value/` | gross / net_low / net_high ranges → `data/out/valued.parquet` |
| 5. Validate | `poc/validate/` | `validate/sample.csv`, `data/out/validation_memo.md` |
| 6. Demo | `poc/demo/` | `buildings.geojson`, `index.html`, `DEMO.md` |

## Design rules

- **All geometry in ITM EPSG:2039**; converted to WGS84 only at GeoJSON export.
- **Every raw API response is cached** to `data/raw/` before parsing and never re-fetched.
  Requests are throttled to ≤2/sec.
- **Every computed number carries a `confidence`**, and every entitlement carries a
  `rule_id` traceable to a plan clause.
- **Nothing is silently dropped.** Excluded buildings stay in the output with named flags.
- **Three tiers, never mixed:** `headline` (cited clauses only) · `mixed_use_unconfirmed`
  (plan's best terms, residential eligibility unproven) · `upside_extrapolated`
  (1-floor entitlement inferred, not cited).

## Notes from the build

Findings that changed the implementation, all documented in code:

- All 8 layer IDs in the spec verified against live service metadata. Layer 682 advertises
  `bitul_logi` but returns HTTP 400 when it is requested.
- `gova_simplex_2019` is exactly `max_height − min_height`, and is **not** floors × 3.0.
  A fitted inverse recovers 59% of floor counts within 1 floor; naive `/3.0` manages 11%.
- `dsm_max` sits in a different vertical datum from `max_height` — reusing one model for
  both biased the second cross-check by a median of 4 floors.
- Official address points (layer 527) give a better street assignment than the OSM/GovMap
  fallback in the spec: 99.8% assigned, 19/20 on manual spot-check.
- A naive residential-use filter excluded **every** Dizengoff/Ben Yehuda building — the
  cohort the plan grants its best terms — because those lots are designated commercial.
  Now a separate, explicitly unconfirmed tier.

## Documents

- `data/out/qa_report.md` — profiling, join rates, gap sanity dashboard, outlier audit
- `data/out/validation_memo.md` — accuracy vs targets, six systematic errors stated plainly
- `data/out/onepager.md` — methodology, sources, competitive context, roadmap
- `demo/DEMO.md` — the 3-minute walkthrough script
