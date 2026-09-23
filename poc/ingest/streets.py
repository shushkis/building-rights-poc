"""T1.7 - assign each building its street, with a provenance-tagged method.

Priority:
  1. address point inside the footprint          -> 'address_within'
  2. nearest address point within 30 m           -> 'address_near'
  3. nearest street centerline within 60 m       -> 'centerline'
  4. nothing                                     -> 'none'

Every assignment carries `street_method` and `street_dist_m`, so downstream
confidence can discount weak assignments rather than trusting them silently.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config

MAX_ADDRESS_DIST_M = 30.0
MAX_CENTERLINE_DIST_M = 60.0


def _normalise(name) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return str(name).strip().replace("‏", "").replace("‎", "")


def is_special_street(name) -> bool:
    """Dizengoff / Ben Yehuda get the enhanced rule branch."""
    n = _normalise(name)
    return any(s in n for s in config.SPECIAL_STREETS)


def assign_streets(buildings: gpd.GeoDataFrame) -> pd.DataFrame:
    P = config.PROCESSED_DIR
    addresses = gpd.read_parquet(P / "addresses.parquet")
    lines = gpd.read_parquet(P / "street_lines.parquet")

    b = buildings[["geometry"]].copy()
    result = pd.DataFrame(
        {
            "street": pd.Series([None] * len(b), index=b.index, dtype=object),
            "house_num": pd.Series([None] * len(b), index=b.index, dtype=object),
            "street_method": pd.Series(["none"] * len(b), index=b.index, dtype=object),
            "street_dist_m": pd.Series([float("nan")] * len(b), index=b.index),
        }
    )

    # --- 1. address points inside the footprint ---------------------------
    if len(addresses):
        inside = gpd.sjoin(
            addresses[["t_rechov", "ms_bayit", "geometry"]],
            b.reset_index().rename(columns={"index": "_bidx"}),
            how="inner",
            predicate="within",
        )
        if len(inside):
            # Prefer the lowest house number for determinism.
            inside = inside.sort_values("ms_bayit")
            first = inside.drop_duplicates(subset="_bidx", keep="first")
            idx = first["_bidx"].values
            result.loc[idx, "street"] = first["t_rechov"].values
            result.loc[idx, "house_num"] = first["ms_bayit"].values
            result.loc[idx, "street_method"] = "address_within"
            result.loc[idx, "street_dist_m"] = 0.0

    # --- 2. nearest address point within 30 m -----------------------------
    todo = result.index[result["street"].isna()]
    if len(todo) and len(addresses):
        near = gpd.sjoin_nearest(
            b.loc[todo],
            addresses[["t_rechov", "ms_bayit", "geometry"]],
            how="left",
            max_distance=MAX_ADDRESS_DIST_M,
            distance_col="_dist",
        )
        near = near[near["t_rechov"].notna()]
        near = near.sort_values("_dist").groupby(level=0).first()
        if len(near):
            result.loc[near.index, "street"] = near["t_rechov"].values
            result.loc[near.index, "house_num"] = near["ms_bayit"].values
            result.loc[near.index, "street_method"] = "address_near"
            result.loc[near.index, "street_dist_m"] = near["_dist"].values

    # --- 3. nearest street centerline within 60 m -------------------------
    todo = result.index[result["street"].isna()]
    if len(todo) and len(lines):
        cl = gpd.sjoin_nearest(
            b.loc[todo],
            lines[["t_rechov", "geometry"]],
            how="left",
            max_distance=MAX_CENTERLINE_DIST_M,
            distance_col="_dist",
        )
        cl = cl[cl["t_rechov"].notna()]
        cl = cl.sort_values("_dist").groupby(level=0).first()
        if len(cl):
            result.loc[cl.index, "street"] = cl["t_rechov"].values
            result.loc[cl.index, "street_method"] = "centerline"
            result.loc[cl.index, "street_dist_m"] = cl["_dist"].values

    result["street"] = result["street"].map(_normalise).replace("", None)
    result["is_special_street"] = result["street"].map(is_special_street)
    result["street_class"] = result["is_special_street"].map(
        {True: "special", False: "other"}
    )
    return result
