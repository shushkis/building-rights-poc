"""T2.1 AC - table-driven coverage of every rights-table branch."""
import pytest

from poc.rules import rova3
from poc.rules.rova3 import allowed_floors

# (street_class, current_floors, expected_total, expected_rule)
CASES = [
    # --- new build / vacant lot ---
    ("other",   0, 6,  rova3.R_NEW_OTHER),
    ("other",   None, 6, rova3.R_NEW_OTHER),
    ("special", 0, 7,  rova3.R_NEW_SPECIAL),
    ("special", None, 7, rova3.R_NEW_SPECIAL),

    # --- existing 2 floors -> complete to 5 (7 on special streets) ---
    ("other",   2, 5,  rova3.R_EX_2FL),
    ("special", 2, 7,  rova3.R_EX_SPECIAL_3P),

    # --- existing 3+ on Dizengoff / Ben Yehuda -> complete to 7 ---
    ("special", 3, 7,  rova3.R_EX_SPECIAL_3P),
    ("special", 4, 7,  rova3.R_EX_SPECIAL_3P),
    ("special", 6, 7,  rova3.R_EX_SPECIAL_3P),

    # --- existing 3-6 other streets -> +1 ---
    ("other",   3, 4,  rova3.R_EX_OTHER_3_6),
    ("other",   4, 5,  rova3.R_EX_OTHER_3_6),
    ("other",   5, 6,  rova3.R_EX_OTHER_3_6),
    ("other",   6, 7,  rova3.R_EX_OTHER_3_6),

    # --- existing 7+ -> +2 (both street classes) ---
    ("other",   7, 9,  rova3.R_EX_7P),
    ("other",  10, 12, rova3.R_EX_7P),
    ("special", 7, 9,  rova3.R_EX_7P),
    ("special", 12, 14, rova3.R_EX_7P),

    # --- 1 floor: extrapolated, distinctly tagged ---
    ("other",   1, 5,  rova3.R_EX_1FL_EXTRAP),
    ("special", 1, 7,  rova3.R_EX_1FL_EXTRAP),
]


@pytest.mark.parametrize("street_class,current,expected_total,expected_rule", CASES)
def test_rights_table(street_class, current, expected_total, expected_rule):
    r = allowed_floors(street_class, current)
    assert r.total_floors == expected_total
    assert r.rule_id == expected_rule
    assert r.partial_roof is True


def test_calibration_case_court_ruling():
    """Published calibration case: 4-floor building (incl. pillar floor) on a
    lot < 500 m2 gets +1 typical floor plus a partial roof floor.

    Source: https://storage.nadlancenter.co.il/media/Storage/41328.pdf
    """
    r = allowed_floors(
        street_class="other",
        current_floors=4,
        lot_area_m2=480.0,
        in_unesco_zone=False,
        permit_pre_1980=True,
    )
    assert r.total_floors == 5, "must be exactly +1 typical floor"
    assert r.total_floors - 4 == 1
    assert r.partial_roof is True
    assert r.rule_id == rova3.R_EX_OTHER_3_6


def test_never_reduces_existing_rights():
    for cf in range(0, 15):
        for sc in ("other", "special"):
            r = allowed_floors(sc, cf)
            assert r.total_floors >= cf, (sc, cf)


def test_unesco_zone_is_out_of_scope():
    r = allowed_floors("other", 4, in_unesco_zone=True)
    assert r.rule_id == rova3.R_UNESCO
    assert r.total_floors == 4
    assert r.partial_roof is False


def test_every_rule_id_has_a_description():
    for rule_id in {c[3] for c in CASES} | {rova3.R_UNESCO}:
        assert rova3.RULE_DESCRIPTIONS.get(rule_id), rule_id


def test_extrapolated_rules_are_flagged():
    """The 1-floor entitlement is not directly cited and must stay labelled."""
    assert rova3.R_EX_1FL_EXTRAP in rova3.EXTRAPOLATED_RULES
    assert rova3.R_EX_2FL not in rova3.EXTRAPOLATED_RULES
    assert allowed_floors("other", 1).rule_id in rova3.EXTRAPOLATED_RULES


def test_float_floor_counts_are_accepted():
    assert allowed_floors("other", 4.0).total_floors == 5


def test_lot_area_does_not_change_floor_entitlement():
    """The published table is not area-conditioned; guard against drift."""
    small = allowed_floors("other", 4, lot_area_m2=200.0)
    large = allowed_floors("other", 4, lot_area_m2=2000.0)
    assert small == large
