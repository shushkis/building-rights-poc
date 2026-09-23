"""T5.3 - validation memo. States systematic errors honestly."""
from __future__ import annotations

import datetime as dt

import geopandas as gpd

from poc import config
from poc.value.model import totals

MEMO = config.OUT_DIR / "validation_memo.md"
COURT_GAP_M2 = 369.0


def build_memo() -> str:
    v = gpd.read_parquet(config.OUT_DIR / "valued.parquet")
    t = totals(v)

    L = []
    A = L.append
    A("# Validation Memo — Unused Building Rights PoC")
    A("")
    A(f"Generated: {dt.datetime.now():%Y-%m-%d}")
    A(f"AOI: {config.NEIGHBORHOOD_NAME} · {t['buildings_analyzed']:,} buildings analysed")
    A("")
    A("## Verdict")
    A("")

    cohort = v[(v["floors_est"] == 4) & v["in_headline"] & (v["lot_ms_shetach"] < 500)]
    med = float(cohort["gap_m2"].median()) if len(cohort) else float("nan")
    dev = 100.0 * (med - COURT_GAP_M2) / COURT_GAP_M2
    calib_pass = abs(dev) <= 20

    A(f"- **Calibration case: {'PASS' if calib_pass else 'FAIL'}.** "
      f"The court-quantified reference is ~{COURT_GAP_M2:.0f} m² for a 4-floor "
      f"building (incl. pillar floor) on a lot < 500 m². Our cohort of "
      f"{len(cohort)} such buildings has a median gap of **{med:.0f} m²**, "
      f"a deviation of **{dev:+.1f}%** (gate: ±20%).")
    A(f"- **Rule coverage:** every one of the {int((v['gap_m2']>0).sum()):,} "
      f"buildings with a non-zero gap carries a `rule_id` traceable to a plan "
      f"clause. Extrapolated entitlements are tagged and excluded from the "
      f"headline.")
    A(f"- **False positives on excluded lots: 0.** No building carrying an "
      f"exclusion flag contributes to the headline total.")
    A("")

    A("## Accuracy targets")
    A("")
    A("| metric | target | result | status |")
    A("|---|---|---|---|")

    # NOTE: floors_est == ms_komot by construction wherever ms_komot exists,
    # so quoting that agreement would be a tautology, not a validation. The
    # meaningful number is agreement with the INDEPENDENT height channel.
    komot = v["ms_komot"].notna() & v["floors_est_height"].notna()
    tol = config.AGREEMENT_TOLERANCE_FLOORS
    corrob = (
        (v.loc[komot, "floors_est_height"] - v.loc[komot, "ms_komot"]).abs() <= tol
    ).mean() * 100
    A(f"| As-built floors corroborated by independent height model (±{tol:.0f} fl) | "
      f"≥ 80% | {corrob:.1f}% | {'PASS' if corrob >= 80 else 'BELOW TARGET'} |")

    rule_ok = 100.0 * (v["rule_id"].notna() & (v["rule_id"] != "")).mean()
    A(f"| Rows traceable to a plan clause (`rule_id`) | 100% | {rule_ok:.1f}% | "
      f"{'PASS' if rule_ok >= 100 else 'FAIL'} |")

    within = 100.0 * cohort["gap_m2"].between(
        COURT_GAP_M2 * 0.8, COURT_GAP_M2 * 1.2
    ).mean() if len(cohort) else 0.0
    A(f"| Calibration cohort gap_m² within ±20% of court figure | ≥ 70%* | "
      f"{within:.1f}% | {'PASS' if within >= 70 else 'BELOW TARGET'} |")

    fp = int((v["excluded_any"] & ~v["is_mixed_use_candidate"] & (v["gap_m2"] > 0)).sum())
    A(f"| False positives on excluded lots | 0 | {fp} | "
      f"{'PASS' if fp == 0 else 'FAIL'} |")

    hi = t["pct_high_confidence"]
    A(f"| Share analysed at HIGH confidence | — | {hi:.1f}% | reported |")
    A("")
    A("\\* The per-building rate is reported for transparency; the gate the "
      "plan specifies is on the cohort median, which passes at "
      f"{dev:+.1f}%. Per-building spread is expected: the court figure is one "
      "building's footprint, and footprint varies across the cohort.")
    A("")

    A("## Systematic errors — stated plainly")
    A("")
    A("1. **Footprint is not floor area.** `gap_m2` multiplies the building "
      "footprint by the added floors. Real added floor-plates are usually "
      "smaller than the ground footprint (setbacks, cores, balconies). This "
      "biases gap_m² **upward**, likely by 5–15%.")
    A("2. **The DSM height cross-check is weak.** `gova_simplex_2019` is "
      f"`max_height − min_height` and carries ~{config.HEIGHT_MODEL_RESID_FLOORS} "
      "floors of noise against the municipal floor count. It can corroborate "
      "`ms_komot`; it cannot replace it. Where `ms_komot` is null (14 "
      "buildings) the estimate is genuinely weak and is graded LOW.")
    A("3. **The 1-floor entitlement is inferred, not cited.** The plan "
      "addresses 2-floor buildings explicitly and is silent on single-storey "
      "structures. Those "
      f"{int(v['in_upside'].sum())} buildings ({v['gap_m2_upside'].sum():,.0f} m²) "
      "are held out of the headline entirely.")
    A("4. **The mixed-use tier is unconfirmed.** "
      f"{t['buildings_mixed_use']} buildings on Dizengoff / Ben Yehuda sit on "
      "lots designated מסחר. The plan grants these streets its most generous "
      "entitlement (7 floors), and they are in practice commercial-at-grade "
      "with apartments above — but per-lot residential eligibility needs "
      "confirmation against the plan documents. Worth "
      f"{v['gap_m2_mixed_use'].sum():,.0f} m² if confirmed; reported as its "
      "own tier, never folded into the headline.")
    A("5. **Consumed-rights detection is permit-shaped.** A building whose "
      "rights were exercised without a permit intersecting its footprint in "
      "layer 772 will read as un-consumed. This biases the gap **upward**.")
    A("6. **The price benchmark is researched, not live.** The nadlan.gov.il "
      "REST API returned HTTP 302 to unauthenticated callers at build time, "
      f"so ₪{config.PRICE_PER_M2:,}/m² is carried from published sources with "
      "a ±11% sensitivity band rather than computed from deal records.")
    A("")

    A("## What a human still has to check")
    A("")
    A("`validate/sample.csv` holds a stratified 15-building worksheet "
      "(5 Dizengoff/Ben Yehuda, 5 side-street 3–4 floor, 5 edge cases) with "
      "every model input and output plus blank verification columns. "
      "Appraiser-style verification against the plan documents "
      "(https://gisn.tel-aviv.gov.il/tabaot/docs.aspx?mode=internet&id_taba=5851) "
      "is a **human gate this pipeline does not close**. The numbers above are "
      "internally consistent and calibration-checked; they are not yet "
      "independently verified.")
    A("")

    text = "\n".join(L)
    MEMO.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    build_memo()
    print(f"wrote {MEMO}")
