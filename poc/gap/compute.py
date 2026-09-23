"""T3.2 - the gap computation, joining rules + exclusions + consumption."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config
from poc.gap.asbuilt import estimate_asbuilt
from poc.rules import rova3
from poc.rules.consumed import detect_consumption
from poc.rules.exclusions import apply_exclusions
from poc.ingest.joins import build_master

GAPS_PATH = config.OUT_DIR / "gaps.parquet"


def compute_gaps(force: bool = False) -> gpd.GeoDataFrame:
    if GAPS_PATH.exists() and not force:
        return gpd.read_parquet(GAPS_PATH)

    m = build_master()
    out = m.copy()

    # --- as-built ----------------------------------------------------------
    out = out.join(estimate_asbuilt(m))

    # --- exclusions & consumption -----------------------------------------
    out = out.join(apply_exclusions(m))
    out = out.join(detect_consumption(m))

    # --- entitlement per row ----------------------------------------------
    lot_area = pd.to_numeric(out.get("lot_ms_shetach"), errors="coerce")
    results = [
        rova3.allowed_floors(
            street_class=sc if isinstance(sc, str) else "other",
            current_floors=None if pd.isna(cf) else int(cf),
            lot_area_m2=None if pd.isna(la) else float(la),
            in_unesco_zone=False,
        )
        for sc, cf, la in zip(
            out["street_class"].fillna("other"),
            out["floors_est"],
            lot_area,
        )
    ]
    out["allowed_floors"] = [r.total_floors for r in results]
    out["partial_roof"] = [r.partial_roof for r in results]
    out["rule_id"] = [r.rule_id for r in results]
    out["rule_description"] = [r.description for r in results]
    out["rule_is_extrapolated"] = out["rule_id"].isin(rova3.EXTRAPOLATED_RULES)

    # --- the gap -----------------------------------------------------------
    raw_gap = (out["allowed_floors"] - out["floors_est"]).clip(lower=0)
    out["gap_floors_raw"] = raw_gap

    # Exclusions zero the gap; consumption caps it. The mixed-use tier is
    # kept alive here and separated from the headline further down.
    keep = (~out["excluded_any"] | out["is_mixed_use_candidate"]).astype(float)
    out["gap_floors"] = raw_gap * out["gap_cap_factor"] * keep

    footprint = out["footprint_m2"]
    roof_area = out["partial_roof"].astype(float) * config.PARTIAL_ROOF_FACTOR * footprint
    out["gap_m2"] = (
        out["gap_floors"] * footprint
        + roof_area * (out["gap_floors"] > 0).astype(float)
    )

    # Excluded / consumed rows keep a zero gap but retain every flag.
    out.loc[out["gap_floors"] <= 0, "gap_m2"] = 0.0

    # --- headline vs upside -------------------------------------------------
    # The headline figures quote only entitlements traceable to a cited plan
    # clause. Extrapolated rows are carried separately as identified upside so
    # the pitch never books an inference as a fact.
    has_gap = out["gap_m2"] > 0
    cited = config.INCLUDE_EXTRAPOLATED_IN_HEADLINE | ~out["rule_is_extrapolated"]

    out["in_headline"] = has_gap & cited & ~out["is_mixed_use_candidate"]
    # The mixed-use tier carries ONE unproven assumption (residential
    # eligibility). It must not also absorb the extrapolated 1-floor clause --
    # stacking two unproven assumptions produced some of the highest-value rows
    # in the ranked list, which is exactly where scrutiny lands hardest.
    out["in_mixed_use"] = has_gap & out["is_mixed_use_candidate"] & cited
    out["in_upside"] = has_gap & ~cited

    out["tier"] = "none"
    out.loc[out["in_upside"], "tier"] = "upside_extrapolated"
    out.loc[out["in_mixed_use"], "tier"] = "mixed_use_unconfirmed"
    out.loc[out["in_headline"], "tier"] = "headline"

    out["gap_m2_headline"] = out["gap_m2"].where(out["in_headline"], 0.0)
    out["gap_m2_mixed_use"] = out["gap_m2"].where(out["in_mixed_use"], 0.0)
    out["gap_m2_upside"] = out["gap_m2"].where(out["in_upside"], 0.0)

    out["gush_helka"] = (
        out["parcel_ms_gush"].astype("Int64").astype(str)
        + "/"
        + out["parcel_ms_chelka"].astype("Int64").astype(str)
    )

    out.to_parquet(GAPS_PATH)
    return out


COLUMNS_OF_RECORD = [
    "id_binyan", "gush_helka", "street", "house_num", "street_class",
    "floors_est", "floors_source", "allowed_floors", "rule_id",
    "gap_floors", "gap_m2", "confidence",
    "excluded_any", "exclusion_reasons", "rights_consumed",
    "rule_is_extrapolated", "footprint_m2",
]


if __name__ == "__main__":
    g = compute_gaps(force=True)
    print(f"rows: {len(g):,}")
    print(f"columns present: {all(c in g for c in COLUMNS_OF_RECORD)}")
    live = g[g["gap_floors"] > 0]
    print(f"buildings with gap >= 1 floor: {len(live):,}")
    print(f"total gap m2: {g['gap_m2'].sum():,.0f}")
    print()
    print(g["confidence"].value_counts().to_string())
    print()
    print(g["rights_consumed"].value_counts().to_string())
