"""Profiling + acceptance-criteria report -> data/out/qa_report.md."""
from __future__ import annotations

import datetime as dt

import geopandas as gpd
import pandas as pd

from poc import config
from poc.ingest.aoi import fetch_aoi

REPORT = config.OUT_DIR / "qa_report.md"


def _pct(n, d):
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def build_report() -> str:
    P = config.PROCESSED_DIR
    aoi = fetch_aoi()
    m = gpd.read_parquet(P / "master.parquet")
    lots = gpd.read_parquet(P / "lots.parquet")

    L = []
    A = L.append
    A("# QA Report — Unused Building Rights PoC")
    A("")
    A(f"Generated: {dt.datetime.now():%Y-%m-%d %H:%M}")
    A(f"AOI: **{config.NEIGHBORHOOD_NAME}**")
    A(f"Source: `{config.BASE_URL}` (public, no auth)")
    A("")

    # --- AOI ---
    area_km2 = float(aoi.geometry.area.iloc[0]) / 1e6
    A("## T1.2 — AOI")
    A("")
    A(f"- Polygons returned: **{len(aoi)}** (AC: exactly 1) — {'PASS' if len(aoi)==1 else 'FAIL'}")
    A(f"- Area: **{area_km2:.3f} km²** (AC: 0.5–2.5) — {'PASS' if 0.5<=area_km2<=2.5 else 'FAIL'}")
    A("")

    # --- Buildings ---
    n = len(m)
    A("## T1.3 — Buildings")
    A("")
    A(f"- Buildings in AOI: **{n:,}** (AC: > 1,000) — {'PASS' if n>1000 else 'FAIL'}")
    A("")
    A("| field | non-null | coverage |")
    A("|---|---:|---:|")
    for c in ["ms_komot", "gova_simplex_2019", "dsm_max", "dsm_mean",
              "min_height", "year", "t_amudim", "t_sug_mivne"]:
        if c in m:
            nn = int(m[c].notna().sum())
            A(f"| `{c}` | {nn:,} | {_pct(nn, n)} |")
    null_komot = int(m["ms_komot"].isna().sum())
    A("")
    A(f"- `ms_komot` null: **{null_komot}** ({_pct(null_komot, n)}) — expected small.")
    A("")
    A("### Floor-count distribution (`ms_komot`)")
    A("")
    A("| floors | buildings |")
    A("|---:|---:|")
    vc = m["ms_komot"].value_counts().sort_index()
    for k, v in vc.items():
        label = f"{int(k)}" if k <= 10 else f"{int(k)}+"
        if k <= 10:
            A(f"| {label} | {v:,} |")
    over10 = int(vc[vc.index > 10].sum())
    A(f"| >10 | {over10:,} |")
    A("")
    A("### Structure types")
    A("")
    A("| type | count |")
    A("|---|---:|")
    for k, v in m["t_sug_mivne"].value_counts().items():
        A(f"| {k} | {v:,} |")
    A("")
    A(f"- Excluded as non-building type: **{int(m['is_non_building_type'].sum())}**")
    A(f"- Excluded as footprint < 40 m²: **{int(m['is_tiny_footprint'].sum())}**")
    A(f"- **Candidate buildings: {int(m['is_candidate'].sum()):,}**")
    A("")

    # --- T1.4 lot coverage ---
    b_union_area = float(m.geometry.area.sum())
    covered = gpd.overlay(
        m[["geometry"]].reset_index(drop=True),
        lots[["geometry"]].reset_index(drop=True),
        how="intersection", keep_geom_type=False,
    )
    covered_area = float(covered.geometry.area.sum()) if len(covered) else 0.0
    cov_pct = 100.0 * covered_area / b_union_area if b_union_area else 0.0
    A("## T1.4 — Land-use lot coverage")
    A("")
    A(f"- Building footprint area: **{b_union_area:,.0f} m²**")
    A(f"- Covered by land-use lots: **{covered_area:,.0f} m²**")
    A(f"- Coverage: **{cov_pct:.1f}%** (AC: ≥ 95%) — {'PASS' if cov_pct>=95 else 'FAIL'}")
    A("")

    # --- T1.6 joins ---
    lot_rate = 100.0 * m["lot_ms_migrash"].notna().mean()
    parcel_rate = 100.0 * m["parcel_ms_chelka"].notna().mean()
    A("## T1.6 — Join rates")
    A("")
    A(f"- Building → lot: **{lot_rate:.1f}%** (AC: ≥ 95%) — {'PASS' if lot_rate>=95 else 'FAIL'}")
    A(f"- Building → parcel: **{parcel_rate:.1f}%**")
    A(f"- Buildings with ≥1 permit: **{int(m['permit_count'].notna().sum()):,}** ({_pct(int(m['permit_count'].notna().sum()), n)})")
    A(f"- Buildings flagged for preservation: **{int(m['is_preserved'].sum())}**")
    A("")

    # --- T1.7 streets ---
    A("## T1.7 — Street assignment")
    A("")
    A("| method | count | share |")
    A("|---|---:|---:|")
    for k, v in m["street_method"].value_counts().items():
        A(f"| {k} | {v:,} | {_pct(v, n)} |")
    assigned = int(m["street"].notna().sum())
    A("")
    A(f"- Assigned a street: **{assigned:,}** ({_pct(assigned, n)})")
    A(f"- On Dizengoff / Ben Yehuda (enhanced rule branch): **{int(m['is_special_street'].sum())}**")
    A("")
    A("### Top streets by building count")
    A("")
    A("| street | buildings |")
    A("|---|---:|")
    for k, v in m["street"].value_counts().head(15).items():
        A(f"| {k} | {v:,} |")
    A("")

    text = "\n".join(L)
    REPORT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    build_report()
    print(f"wrote {REPORT}")
