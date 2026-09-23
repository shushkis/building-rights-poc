"""T1.6 - spatial joins producing one master row per building."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config

MASTER_PATH = config.PROCESSED_DIR / "master.parquet"

# Building types that are not candidate residential structures.
NON_BUILDING_TYPES = {"תחנת אוטובוס", "מיכל", "מבנה ארעי"}
MIN_FOOTPRINT_M2 = 40.0


def _largest_overlap_join(
    buildings: gpd.GeoDataFrame,
    other: gpd.GeoDataFrame,
    cols: list[str],
    prefix: str,
) -> pd.DataFrame:
    """Assign each building the feature of `other` it overlaps most by area."""
    if other.empty:
        return pd.DataFrame(index=buildings.index)

    left = buildings[["geometry"]].copy()
    left["_bidx"] = left.index
    right = other[cols + ["geometry"]].copy()
    right["_oidx"] = right.index

    inter = gpd.overlay(
        left.reset_index(drop=True),
        right.reset_index(drop=True),
        how="intersection",
        keep_geom_type=False,
    )
    if inter.empty:
        return pd.DataFrame(index=buildings.index)

    inter["_ov_area"] = inter.geometry.area
    inter = inter.sort_values("_ov_area", ascending=False)
    best = inter.drop_duplicates(subset="_bidx", keep="first")

    out = best.set_index("_bidx")[cols + ["_ov_area"]]
    out = out.rename(columns={c: f"{prefix}_{c}" for c in cols})
    out = out.rename(columns={"_ov_area": f"{prefix}_overlap_m2"})
    return out.reindex(buildings.index)


def build_master(force: bool = False) -> gpd.GeoDataFrame:
    if MASTER_PATH.exists() and not force:
        return gpd.read_parquet(MASTER_PATH)

    P = config.PROCESSED_DIR
    buildings = gpd.read_parquet(P / "buildings.parquet")
    lots = gpd.read_parquet(P / "lots.parquet")
    parcels = gpd.read_parquet(P / "parcels.parquet")
    permits = gpd.read_parquet(P / "permits.parquet")
    preservation = gpd.read_parquet(P / "preservation.parquet")

    b = buildings.copy().reset_index(drop=True)
    b["footprint_m2"] = b.geometry.area

    # Candidacy flags -- never silent drops (honesty rule).
    b["is_non_building_type"] = b["t_sug_mivne"].isin(NON_BUILDING_TYPES)
    b["is_tiny_footprint"] = b["footprint_m2"] < MIN_FOOTPRINT_M2
    b["is_candidate"] = ~(b["is_non_building_type"] | b["is_tiny_footprint"])

    # building -> lot (largest overlap)
    lot_cols = [
        "ms_gush", "ms_migrash", "st_taba", "st_taba_kavaa_yeud",
        "t_yeud_karka", "t_yeud_rashi", "ms_shetach_rashum",
        "ms_shetach_lechishuv_zchuyot", "ms_shetach", "id_taba",
    ]
    b = b.join(_largest_overlap_join(b, lots, lot_cols, "lot"))

    # building -> parcel (gush/helka)
    parcel_cols = ["ms_gush", "ms_chelka", "ms_gush_vechelka", "ms_shetach"]
    b = b.join(_largest_overlap_join(b, parcels, parcel_cols, "parcel"))

    # building -> preservation flag (any intersection)
    if len(preservation):
        pres_idx = gpd.sjoin(
            b[["geometry"]], preservation[["geometry"]],
            how="inner", predicate="intersects",
        ).index.unique()
        b["is_preserved"] = b.index.isin(pres_idx)
    else:
        b["is_preserved"] = False

    # building -> permits (all intersecting, aggregated per building)
    b = b.join(_aggregate_permits(b, permits))

    # building -> street (T1.7)
    from poc.ingest.streets import assign_streets
    b = b.join(assign_streets(b))

    b.to_parquet(MASTER_PATH)
    return b


def _aggregate_permits(b: gpd.GeoDataFrame, permits: gpd.GeoDataFrame) -> pd.DataFrame:
    """Collapse the many-to-many building<->permit relation to one row/building."""
    empty = pd.DataFrame(index=b.index)
    if permits.empty:
        return empty

    pairs = gpd.sjoin(
        b[["geometry"]], permits, how="inner", predicate="intersects"
    )
    if pairs.empty:
        return empty

    pairs["permission_date"] = pd.to_datetime(
        pairs["permission_date"], unit="ms", errors="coerce"
    )

    def _yes(series):
        return series.astype(str).str.strip().isin({"כן", "Y", "yes", "1", "True"})

    pairs["_tama"] = (
        _yes(pairs.get("sw_tama_38", pd.Series(index=pairs.index, dtype=object)))
        | _yes(pairs.get("sw_tama_38_chadash", pd.Series(index=pairs.index, dtype=object)))
        | _yes(pairs.get("sw_tama_38_tosefet", pd.Series(index=pairs.index, dtype=object)))
    )
    hakala_cols = [c for c in ("hakala_tosefet_achuz_shetach", "hakala_yd_mevukash") if c in pairs]
    pairs["_hakala"] = False
    for c in hakala_cols:
        s = pairs[c]
        nonempty = s.notna() & (s.astype(str).str.strip() != "") & (s.astype(str).str.strip() != "0")
        pairs["_hakala"] = pairs["_hakala"] | nonempty

    g = pairs.groupby(level=0)
    out = pd.DataFrame({
        "permit_count": g.size(),
        "permit_last_date": g["permission_date"].max(),
        "permit_any_tama38": g["_tama"].any(),
        "permit_any_hakala": g["_hakala"].any(),
        "permit_stages": g["building_stage"].apply(
            lambda s: "; ".join(sorted({str(x) for x in s.dropna()}))
        ),
        "permit_addresses": g["addresses"].apply(
            lambda s: "; ".join(sorted({str(x) for x in s.dropna() if str(x).strip()}))
        ),
        "permit_last_num": g["permission_num"].apply(
            lambda s: "; ".join(sorted({str(x) for x in s.dropna()})[:3])
        ),
    })
    return out.reindex(b.index)


if __name__ == "__main__":
    m = build_master(force=True)
    print(f"master rows: {len(m)}")
    print(f"joined to lot:    {m['lot_ms_migrash'].notna().mean() * 100:.1f}%")
    print(f"joined to parcel: {m['parcel_ms_chelka'].notna().mean() * 100:.1f}%")
    print(f"preserved:        {int(m['is_preserved'].sum())}")
    print(f"with permits:     {int(m['permit_count'].notna().sum())}")
    print(f"candidates:       {int(m['is_candidate'].sum())}")
    print("street assignment methods:")
    print(m["street_method"].value_counts().to_string())
    print(f"on special streets: {int(m['is_special_street'].sum())}")
