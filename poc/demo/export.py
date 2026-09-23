"""T6.1/T6.3 - export buildings.geojson (WGS84) + headline stats for the map."""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np

from poc import config
from poc.value.model import build as build_valued
from poc.value.model import totals

DEMO_DIR = config.POC_DIR / "demo"
GEOJSON_PATH = DEMO_DIR / "buildings.geojson"
STATS_PATH = DEMO_DIR / "stats.json"
TOP50_PATH = DEMO_DIR / "top50.json"

EXPORT_FIELDS = [
    "street", "house_num", "gush_helka", "floors_est", "allowed_floors",
    "gap_floors", "gap_m2", "rule_id", "rule_description", "confidence",
    "net_low", "net_high", "tier", "exclusion_reasons", "rights_consumed",
    "year", "footprint_m2",
]


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if np.isnan(f) else round(f, 1)
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def export(force: bool = False) -> dict:
    v = build_valued(force=force)

    g = v.to_crs(epsg=config.CRS_WGS84).copy()
    # Simplify lightly to keep the payload small; ~0.5 m at this latitude.
    g["geometry"] = g.geometry.simplify(0.000005, preserve_topology=True)

    features = []
    for _, row in g.iterrows():
        if row.geometry is None or row.geometry.is_empty:
            continue
        props = {k: _clean(row.get(k)) for k in EXPORT_FIELDS}
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(gpd.GeoSeries([row.geometry]).to_json())[
                    "features"
                ][0]["geometry"],
                "properties": props,
            }
        )

    fc = {"type": "FeatureCollection", "features": features}
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    with open(GEOJSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))

    # --- headline stats (T6.3) --------------------------------------------
    t = totals(v)
    stats = {
        "neighborhood": config.NEIGHBORHOOD_NAME,
        "buildings_analyzed": t["buildings_analyzed"],
        "buildings_with_gap": t["buildings_headline"],
        "gap_m2_headline": round(t["gap_m2_headline"]),
        "gap_m2_mixed_use": round(t["gap_m2_mixed_use"]),
        "gap_m2_upside": round(t["gap_m2_upside"]),
        "net_low": round(t["net_low"]),
        "net_high": round(t["net_high"]),
        "net_low_mixed_use": round(t["net_low_mixed_use"]),
        "net_high_mixed_use": round(t["net_high_mixed_use"]),
        "pct_high_confidence": round(t["pct_high_confidence"], 1),
        "price_per_m2": config.PRICE_PER_M2,
        "price_is_live": config.PRICE_IS_LIVE,
        "plan_code": config.ROVA3_PLAN_CODE,
        "plan_effective": config.ROVA3_EFFECTIVE_DATE,
    }
    with open(STATS_PATH, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)

    # --- top 50 (T6.2) -----------------------------------------------------
    ranked = (
        v[v["in_headline"] | v["in_mixed_use"]]
        .sort_values("net_low", ascending=False)
        .head(50)
    )
    rows = [
        {k: _clean(r.get(k)) for k in EXPORT_FIELDS}
        for _, r in ranked.iterrows()
    ]
    with open(TOP50_PATH, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)

    return stats


if __name__ == "__main__":
    s = export(force=False)
    size = GEOJSON_PATH.stat().st_size / 1e6
    print(f"buildings.geojson: {size:.1f} MB ({len(s and '') or ''}...)")
    print(json.dumps(s, ensure_ascii=False, indent=2))
