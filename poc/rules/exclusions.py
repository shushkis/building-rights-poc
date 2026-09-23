"""T2.2 - exclusion filters. Every filter produces a NAMED FLAG.

Nothing is silently dropped: excluded buildings stay in the output carrying
their flags, so the demo can show exclusion transparency rather than a
mysteriously shorter list.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from poc import config

EXCL_NEWER_PLAN = "EXCL_NEWER_PLAN"
EXCL_PRESERVATION = "EXCL_PRESERVATION"
EXCL_NON_RESIDENTIAL = "EXCL_NON_RESIDENTIAL"
EXCL_UNDER_CONSTRUCTION = "EXCL_UNDER_CONSTRUCTION"
EXCL_NOT_A_BUILDING = "EXCL_NOT_A_BUILDING"

ALL_EXCLUSIONS = [
    EXCL_NEWER_PLAN,
    EXCL_PRESERVATION,
    EXCL_NON_RESIDENTIAL,
    EXCL_UNDER_CONSTRUCTION,
    EXCL_NOT_A_BUILDING,
]

RESIDENTIAL_USES = {"מגורים", "מגורים-תעסוקה מעורב"}

# Dizengoff and Ben Yehuda are the streets תא/3616א singles out for its most
# generous entitlement (7 floors), and they are overwhelmingly mixed-use:
# commercial at grade with apartments above. Their LOTS are designated מסחר,
# so a naive residential-use filter excludes the single highest-value cohort
# in the neighbourhood. These rows are therefore tracked as a distinct
# MIXED-USE tier rather than either silently dropped or booked as headline:
# per-lot residential eligibility needs confirmation against the plan
# documents before the value can be claimed.
MIXED_USE_CANDIDATE_USES = {"מסחר"}
ACTIVE_WORKS_STAGES = {"בבניה"}


def _newer_plan_ids(taba: gpd.GeoDataFrame) -> set[str]:
    """Plan codes in force that post-date תא/3616א."""
    d = pd.to_datetime(taba["tr_matan_tokef"], unit="ms", errors="coerce")
    cutoff = pd.Timestamp(config.ROVA3_EFFECTIVE_DATE)
    newer = taba.loc[
        d.gt(cutoff) & taba["t_status"].astype(str).str.strip().eq("בתוקף"),
        "taba",
    ]
    codes = {str(x).strip() for x in newer.dropna()}
    codes.discard(config.ROVA3_PLAN_CODE)
    return codes


def apply_exclusions(m: gpd.GeoDataFrame) -> pd.DataFrame:
    """Return a frame of boolean exclusion flags aligned to `m`."""
    taba = gpd.read_parquet(config.PROCESSED_DIR / "taba.parquet")
    newer = _newer_plan_ids(taba)

    lot_plan = m["lot_st_taba"].astype(str).str.strip()
    flags = pd.DataFrame(index=m.index)

    # A site-specific plan newer than Rova 3 supersedes its entitlement.
    flags[EXCL_NEWER_PLAN] = lot_plan.isin(newer)

    flags[EXCL_PRESERVATION] = m["is_preserved"].fillna(False).astype(bool)

    use = m["lot_t_yeud_rashi"].astype(str).str.strip()
    flags[EXCL_NON_RESIDENTIAL] = ~use.isin(RESIDENTIAL_USES)

    stages = m["permit_stages"].fillna("").astype(str)
    flags[EXCL_UNDER_CONSTRUCTION] = stages.apply(
        lambda s: any(t in s for t in ACTIVE_WORKS_STAGES)
    )

    # Bus shelters, tanks, temporary structures and sub-40 m2 annexes are not
    # redevelopment candidates. Flagged, never silently dropped.
    flags[EXCL_NOT_A_BUILDING] = ~m["is_candidate"].fillna(False).astype(bool)

    # Mixed-use carve-out: commercial lot, but on a street the plan names.
    flags["is_mixed_use_candidate"] = (
        use.isin(MIXED_USE_CANDIDATE_USES)
        & m["is_special_street"].fillna(False).astype(bool)
        & ~flags[EXCL_PRESERVATION]
        & ~flags[EXCL_UNDER_CONSTRUCTION]
        & ~flags[EXCL_NOT_A_BUILDING]
        & ~flags[EXCL_NEWER_PLAN]
    )

    flags["excluded_any"] = flags[ALL_EXCLUSIONS].any(axis=1)
    flags["exclusion_reasons"] = flags[ALL_EXCLUSIONS].apply(
        lambda r: "; ".join([c for c in ALL_EXCLUSIONS if r[c]]), axis=1
    )
    return flags


def exclusion_summary(flags: pd.DataFrame) -> str:
    lines = ["| exclusion | buildings |", "|---|---:|"]
    for c in ALL_EXCLUSIONS:
        lines.append(f"| `{c}` | {int(flags[c].sum()):,} |")
    lines.append(f"| **any exclusion** | **{int(flags['excluded_any'].sum()):,}** |")
    return "\n".join(lines)
