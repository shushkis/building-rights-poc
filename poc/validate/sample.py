"""T5.1 - stratified 15-building worksheet for appraiser-style verification."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config

SAMPLE_PATH = config.POC_DIR / "validate" / "sample.csv"

WORKSHEET_COLUMNS = [
    "stratum", "id_binyan", "gush_helka", "street", "house_num", "street_class",
    "year", "footprint_m2", "lot_ms_shetach",
    "ms_komot", "floors_est", "floors_source", "floors_est_height",
    "floors_est_dsm", "confidence",
    "allowed_floors", "rule_id", "rule_description", "rule_is_extrapolated",
    "gap_floors", "gap_m2", "net_low", "net_high", "tier",
    "rights_consumed", "rights_consumed_reason",
    "excluded_any", "exclusion_reasons",
    "lot_st_taba", "permit_last_num", "permit_last_date",
]

# Blank columns the human appraiser fills in against the plan documents:
# https://gisn.tel-aviv.gov.il/tabaot/docs.aspx?mode=internet&id_taba=5851
VERIFY_COLUMNS = [
    "verified_allowed_floors",
    "verified_gap_m2",
    "verdict_allowed_floors_ok",
    "verdict_gap_within_20pct",
    "notes",
]


def build_sample(seed: int = 17) -> pd.DataFrame:
    v = gpd.read_parquet(config.OUT_DIR / "valued.parquet")

    special = v[(v["street_class"] == "special") & (v["in_headline"] | v["in_mixed_use"])]
    side = v[
        (v["street_class"] == "other")
        & (v["in_headline"])
        & (v["floors_est"].between(3, 4))
    ]
    edge_7p = v[(v["floors_est"] >= 7) & (v["gap_m2"] > 0)]
    edge_old = v[
        (v["year"].notna()) & (v["year"] < 1980) & (v["in_headline"])
    ]
    edge_excluded = v[v["excluded_any"] & (v["gap_floors_raw"] > 0)]

    picks = [
        ("A_dizengoff_benyehuda", special, 5),
        ("B_side_street_3_4_floors", side, 5),
        ("C_edge_7plus_floors", edge_7p, 2),
        ("D_edge_pre_1980", edge_old, 2),
        ("E_edge_excluded_lot", edge_excluded, 1),
    ]

    frames = []
    for name, frame, k in picks:
        if frame.empty:
            continue
        take = frame.sample(min(k, len(frame)), random_state=seed).copy()
        take["stratum"] = name
        frames.append(take)

    s = pd.concat(frames)
    for c in VERIFY_COLUMNS:
        s[c] = ""

    cols = [c for c in WORKSHEET_COLUMNS if c in s.columns] + VERIFY_COLUMNS
    out = s[cols].copy()
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAMPLE_PATH, index=False, encoding="utf-8-sig")
    return out


if __name__ == "__main__":
    s = build_sample()
    print(f"wrote {SAMPLE_PATH} ({len(s)} rows)")
    print(s["stratum"].value_counts().to_string())
