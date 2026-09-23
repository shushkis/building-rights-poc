# Validation Memo — Unused Building Rights PoC

Generated: 2026-08-18
AOI: הצפון הישן - החלק הצפוני · 2,318 buildings analysed

## Verdict

- **Calibration case: PASS.** The court-quantified reference is ~369 m² for a 4-floor building (incl. pillar floor) on a lot < 500 m². Our cohort of 290 such buildings has a median gap of **319 m²**, a deviation of **-13.6%** (gate: ±20%).
- **Rule coverage:** every one of the 1,083 buildings with a non-zero gap carries a `rule_id` traceable to a plan clause. Extrapolated entitlements are tagged and excluded from the headline.
- **False positives on excluded lots: 0.** No building carrying an exclusion flag contributes to the headline total.

## Accuracy targets

| metric | target | result | status |
|---|---|---|---|
| As-built floors corroborated by independent height model (±2 fl) | ≥ 80% | 76.6% | BELOW TARGET |
| Rows traceable to a plan clause (`rule_id`) | 100% | 100.0% | PASS |
| Calibration cohort gap_m² within ±20% of court figure | ≥ 70%* | 57.6% | BELOW TARGET |
| False positives on excluded lots | 0 | 0 | PASS |
| Share analysed at HIGH confidence | — | 58.8% | reported |

\* The per-building rate is reported for transparency; the gate the plan specifies is on the cohort median, which passes at -13.6%. Per-building spread is expected: the court figure is one building's footprint, and footprint varies across the cohort.

## Systematic errors — stated plainly

1. **Footprint is not floor area.** `gap_m2` multiplies the building footprint by the added floors. Real added floor-plates are usually smaller than the ground footprint (setbacks, cores, balconies). This biases gap_m² **upward**, likely by 5–15%.
2. **The DSM height cross-check is weak.** `gova_simplex_2019` is `max_height − min_height` and carries ~1.66 floors of noise against the municipal floor count. It can corroborate `ms_komot`; it cannot replace it. Where `ms_komot` is null (14 buildings) the estimate is genuinely weak and is graded LOW.
3. **The 1-floor entitlement is inferred, not cited.** The plan addresses 2-floor buildings explicitly and is silent on single-storey structures. Those 55 buildings (41,825 m²) are held out of the headline entirely.
4. **The mixed-use tier is unconfirmed.** 97 buildings on Dizengoff / Ben Yehuda sit on lots designated מסחר. The plan grants these streets its most generous entitlement (7 floors), and they are in practice commercial-at-grade with apartments above — but per-lot residential eligibility needs confirmation against the plan documents. Worth 66,977 m² if confirmed; reported as its own tier, never folded into the headline.
5. **Consumed-rights detection is permit-shaped.** A building whose rights were exercised without a permit intersecting its footprint in layer 772 will read as un-consumed. This biases the gap **upward**.
6. **The price benchmark is researched, not live.** The nadlan.gov.il REST API returned HTTP 302 to unauthenticated callers at build time, so ₪65,000/m² is carried from published sources with a ±11% sensitivity band rather than computed from deal records.

## What a human still has to check

`validate/sample.csv` holds a stratified 15-building worksheet (5 Dizengoff/Ben Yehuda, 5 side-street 3–4 floor, 5 edge cases) with every model input and output plus blank verification columns. Appraiser-style verification against the plan documents (https://gisn.tel-aviv.gov.il/tabaot/docs.aspx?mode=internet&id_taba=5851) is a **human gate this pipeline does not close**. The numbers above are internally consistent and calibration-checked; they are not yet independently verified.
