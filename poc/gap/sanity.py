"""T3.3 - sanity dashboard appended to data/out/qa_report.md."""
from __future__ import annotations

import geopandas as gpd

from poc import config
from poc.rules.exclusions import ALL_EXCLUSIONS

REPORT = config.OUT_DIR / "qa_report.md"


def build_sanity(g: gpd.GeoDataFrame | None = None) -> str:
    if g is None:
        g = gpd.read_parquet(config.OUT_DIR / "gaps.parquet")

    n = len(g)
    L = []
    A = L.append
    A("")
    A("---")
    A("")
    A("## Phase 3 — Gap sanity dashboard")
    A("")

    # --- confidence ---
    A("### As-built confidence (T3.1)")
    A("")
    A("| confidence | buildings | share |")
    A("|---|---:|---:|")
    for k in ("HIGH", "MEDIUM", "LOW"):
        v = int((g["confidence"] == k).sum())
        A(f"| {k} | {v:,} | {100.0*v/n:.1f}% |")
    A("")
    A(f"Agreement band: ±{config.AGREEMENT_TOLERANCE_FLOORS:.0f} floors "
      f"(~1σ of the DSM cross-checks; a ±1 band would read genuine agreement "
      f"as disagreement).")
    A("")

    # --- exclusions ---
    A("### Exclusions (T2.2) — flagged, not dropped")
    A("")
    A("| exclusion | buildings |")
    A("|---|---:|")
    for c in ALL_EXCLUSIONS:
        A(f"| `{c}` | {int(g[c].sum()):,} |")
    A(f"| **any** | **{int(g['excluded_any'].sum()):,}** |")
    A("")

    # --- consumption ---
    A("### Rights consumption (T2.3)")
    A("")
    A("| state | buildings |")
    A("|---|---:|")
    for k, v in g["rights_consumed"].value_counts().items():
        A(f"| {k} | {v:,} |")
    A("")

    # --- gap distribution ---
    live = g[g["gap_floors"] > 0]
    A("### Gap distribution")
    A("")
    A("| gap_floors | buildings |")
    A("|---:|---:|")
    for k, v in g["gap_floors"].value_counts().sort_index().items():
        A(f"| {int(k)} | {v:,} |")
    A("")
    A(f"- Buildings with gap ≥ 1 floor: **{len(live):,}** ({100.0*len(live)/n:.1f}%)")
    A("")

    # --- by rule ---
    A("### Gap by rule clause")
    A("")
    A("| rule_id | buildings | gap m² | cited? |")
    A("|---|---:|---:|---|")
    for rid, grp in g[g["gap_m2"] > 0].groupby("rule_id"):
        cited = "extrapolated" if grp["rule_is_extrapolated"].iloc[0] else "cited"
        A(f"| `{rid}` | {len(grp):,} | {grp['gap_m2'].sum():,.0f} | {cited} |")
    A("")

    # --- by street class ---
    A("### Mean gap by street class")
    A("")
    A("| street class | buildings | mean gap_floors | mean gap m² |")
    A("|---|---:|---:|---:|")
    for sc, grp in live.groupby("street_class"):
        A(f"| {sc} | {len(grp):,} | {grp['gap_floors'].mean():.2f} | {grp['gap_m2'].mean():,.0f} |")
    A("")

    # --- headline vs upside ---
    hl = g[g["in_headline"]]
    A("### Headline vs identified upside")
    A("")
    A(f"- **Headline** (cited clauses only): **{len(hl):,}** buildings, "
      f"**{g['gap_m2_headline'].sum():,.0f} m²**")
    A(f"- **Upside** (extrapolated 1-floor clause): "
      f"{int((g['gap_m2_upside'] > 0).sum()):,} buildings, "
      f"{g['gap_m2_upside'].sum():,.0f} m²")
    A("")
    A("The 1-floor entitlement is inferred from the 2-floor completion clause "
      "rather than cited from the plan text, and it is where the largest "
      "per-building gaps land. It is excluded from the headline by default "
      "(`config.INCLUDE_EXTRAPOLATED_IN_HEADLINE`).")
    A("")

    # --- outlier audit ---
    A("### Outlier audit")
    A("")
    absurd = hl[(hl["gap_floors"] >= 4) & (hl["street_class"] == "other")]
    A(f"- Headline rows with gap ≥ 4 floors on a non-special street: "
      f"**{len(absurd)}** (target: 0)")
    A(f"- Max headline gap_floors: **{int(hl['gap_floors'].max()) if len(hl) else 0}**")
    tiny = hl[hl["footprint_m2"] < 40]
    A(f"- Headline rows with footprint < 40 m²: **{len(tiny)}** (target: 0)")
    A("")

    text = "\n".join(L)
    with open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(text)
    return text


if __name__ == "__main__":
    build_sanity()
    print(f"appended sanity dashboard to {REPORT}")
