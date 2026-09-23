"""T5.2 - the model must reproduce the court-quantified case within +/-20%.

Court ruling: a 4-floor building (incl. pillar floor) on a lot < 500 m2
was quantified at roughly 369 m2 of equivalent unexploited rights.
https://storage.nadlancenter.co.il/media/Storage/41328.pdf
"""
import geopandas as gpd
import pytest

from poc import config
from poc.rules.rova3 import allowed_floors

COURT_GAP_M2 = 369.0
TOLERANCE = 0.20
LOW, HIGH = COURT_GAP_M2 * (1 - TOLERANCE), COURT_GAP_M2 * (1 + TOLERANCE)


def _gap_m2(footprint_m2, gap_floors, partial_roof=True):
    roof = config.PARTIAL_ROOF_FACTOR * footprint_m2 if partial_roof else 0.0
    return gap_floors * footprint_m2 + roof


def test_formula_reproduces_court_figure_at_typical_footprint():
    """1 extra floor + partial roof on a ~224 m2 footprint == the court figure."""
    r = allowed_floors("other", current_floors=4, lot_area_m2=480.0)
    gap_floors = r.total_floors - 4
    assert gap_floors == 1

    gap = _gap_m2(223.6, gap_floors, r.partial_roof)
    assert LOW <= gap <= HIGH, gap
    assert gap == pytest.approx(COURT_GAP_M2, rel=0.01)


@pytest.mark.skipif(
    not (config.OUT_DIR / "valued.parquet").exists(),
    reason="pipeline output not built yet",
)
def test_real_cohort_median_matches_court_figure():
    """The real 4-floor / sub-500 m2 cohort must land inside +/-20%."""
    v = gpd.read_parquet(config.OUT_DIR / "valued.parquet")
    cohort = v[
        (v["floors_est"] == 4)
        & (v["in_headline"])
        & (v["lot_ms_shetach"] < 500)
    ]
    assert len(cohort) >= 30, f"cohort too small to be meaningful: {len(cohort)}"

    median_gap = float(cohort["gap_m2"].median())
    assert LOW <= median_gap <= HIGH, (
        f"cohort median {median_gap:.1f} m2 outside "
        f"[{LOW:.1f}, {HIGH:.1f}] around the court figure {COURT_GAP_M2}"
    )


@pytest.mark.skipif(
    not (config.OUT_DIR / "valued.parquet").exists(),
    reason="pipeline output not built yet",
)
def test_all_four_floor_headline_buildings_get_exactly_one_floor():
    v = gpd.read_parquet(config.OUT_DIR / "valued.parquet")
    cohort = v[
        (v["floors_est"] == 4)
        & (v["in_headline"])
        & (v["street_class"] == "other")
    ]
    assert len(cohort) > 0
    assert (cohort["gap_floors"] == 1).all()
    assert (cohort["allowed_floors"] == 5).all()
