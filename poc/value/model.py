"""T4.2 - valuation. Every figure is a RANGE, never a single number.

The range is driven by the genuinely unresolved betterment-levy question
(היטל השבחה) for תא/3616א:

  net_high -- the levy does NOT apply. Contested; see Globes coverage.
              https://www.globes.co.il/news/article.aspx?did=1001422667
  net_low  -- the levy DOES apply, taking 50% of the betterment.

Neither end is presented as the answer. The spread IS the finding.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config

VALUED_PATH = config.OUT_DIR / "valued.parquet"


def value_frame(
    g: gpd.GeoDataFrame,
    price_per_m2: float | None = None,
    build_cost_ratio: float | None = None,
) -> pd.DataFrame:
    price = config.PRICE_PER_M2 if price_per_m2 is None else price_per_m2
    bcr = config.BUILD_COST_RATIO if build_cost_ratio is None else build_cost_ratio

    gap = g["gap_m2"].fillna(0.0)
    gross = gap * price
    margin = gross * (1.0 - bcr)

    return pd.DataFrame(
        {
            "price_per_m2_used": price,
            "gross_value": gross,
            "net_low": margin * (1.0 - config.LEVY_SHARE),
            "net_high": margin,
        },
        index=g.index,
    )


def add_values(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = g.copy()
    out = out.join(value_frame(g))

    # Price sensitivity band, so the headline can show the effect of the
    # benchmark itself being uncertain -- not just the levy.
    lo = value_frame(g, price_per_m2=config.PRICE_PER_M2_LOW)
    hi = value_frame(g, price_per_m2=config.PRICE_PER_M2_HIGH)
    out["net_low_pricelow"] = lo["net_low"]
    out["net_high_pricehigh"] = hi["net_high"]

    # Headline-only variants (cited clauses, exclusions and consumption applied)
    for tier, mask in (("headline", out["in_headline"]),
                       ("mixed_use", out["in_mixed_use"]),
                       ("upside", out["in_upside"])):
        f = mask.astype(float)
        for c in ("gross_value", "net_low", "net_high",
                  "net_low_pricelow", "net_high_pricehigh"):
            out[f"{c}_{tier}"] = out[c] * f
    return out


def totals(v: pd.DataFrame) -> dict:
    hl = v[v["in_headline"]]
    return {
        "buildings_analyzed": int(len(v)),
        "buildings_with_gap": int((v["gap_m2"] > 0).sum()),
        "buildings_headline": int(len(hl)),
        "gap_m2_headline": float(v["gap_m2_headline"].sum()),
        "buildings_mixed_use": int(v["in_mixed_use"].sum()),
        "gap_m2_mixed_use": float(v["gap_m2_mixed_use"].sum()),
        "gap_m2_upside": float(v["gap_m2_upside"].sum()),
        "net_low_mixed_use": float(v["net_low_mixed_use"].sum()),
        "net_high_mixed_use": float(v["net_high_mixed_use"].sum()),
        "net_low": float(v["net_low_headline"].sum()),
        "net_high": float(v["net_high_headline"].sum()),
        "net_low_pricelow": float(v["net_low_pricelow_headline"].sum()),
        "net_high_pricehigh": float(v["net_high_pricehigh_headline"].sum()),
        "pct_high_confidence": float(100.0 * (v["confidence"] == "HIGH").mean()),
        "pct_high_confidence_headline": float(
            100.0 * (hl["confidence"] == "HIGH").mean()
        ) if len(hl) else 0.0,
    }


def _nis(x: float) -> str:
    if abs(x) >= 1e9:
        return f"₪{x/1e9:.2f}B"
    if abs(x) >= 1e6:
        return f"₪{x/1e6:.1f}M"
    return f"₪{x:,.0f}"


def build(force: bool = False) -> gpd.GeoDataFrame:
    from poc.gap.compute import compute_gaps

    if VALUED_PATH.exists() and not force:
        return gpd.read_parquet(VALUED_PATH)
    v = add_values(compute_gaps())
    v.to_parquet(VALUED_PATH)
    return v


if __name__ == "__main__":
    v = build(force=True)
    t = totals(v)
    print(f"buildings analyzed:      {t['buildings_analyzed']:,}")
    print(f"buildings in headline:   {t['buildings_headline']:,}")
    print(f"headline gap:            {t['gap_m2_headline']:,.0f} m²")
    print(f"identified upside gap:   {t['gap_m2_upside']:,.0f} m²")
    print(f"HIGH confidence:         {t['pct_high_confidence']:.1f}%")
    print()
    print(f"mixed-use buildings:     {t['buildings_mixed_use']:,}  ({t['gap_m2_mixed_use']:,.0f} m²)")
    print()
    print(f"net value range (levy):  {_nis(t['net_low'])} – {_nis(t['net_high'])}")
    print(f"mixed-use tier (unconf): {_nis(t['net_low_mixed_use'])} – {_nis(t['net_high_mixed_use'])}")
    print(f"incl. price sensitivity: {_nis(t['net_low_pricelow'])} – {_nis(t['net_high_pricehigh'])}")
