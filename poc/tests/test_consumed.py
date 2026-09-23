"""T2.3 AC - unit tests on synthetic permit histories."""
import pandas as pd

from poc.rules.consumed import LIKELY_FULL, NONE, PARTIAL, detect_consumption


def _frame(rows):
    return pd.DataFrame(rows, index=range(len(rows)))


def test_three_synthetic_permit_histories():
    df = _frame([
        # 1. old permit only, no TAMA, no relief -> rights intact
        {"permit_last_date": pd.Timestamp("1998-04-01"),
         "permit_any_tama38": False, "permit_any_hakala": False, "permit_count": 1},
        # 2. relief request on file -> partially consumed
        {"permit_last_date": pd.Timestamp("2005-06-01"),
         "permit_any_tama38": False, "permit_any_hakala": True, "permit_count": 2},
        # 3. TAMA 38 permit -> likely fully consumed
        {"permit_last_date": pd.Timestamp("2015-01-01"),
         "permit_any_tama38": True, "permit_any_hakala": False, "permit_count": 3},
    ])
    out = detect_consumption(df)
    assert list(out["rights_consumed"]) == [NONE, PARTIAL, LIKELY_FULL]
    assert list(out["gap_cap_factor"]) == [1.0, 0.5, 0.0]


def test_recent_permit_alone_consumes_rights():
    df = _frame([{
        "permit_last_date": pd.Timestamp("2021-03-15"),
        "permit_any_tama38": False, "permit_any_hakala": False, "permit_count": 1,
    }])
    out = detect_consumption(df)
    assert out["rights_consumed"].iloc[0] == LIKELY_FULL
    assert out["gap_cap_factor"].iloc[0] == 0.0


def test_no_permits_leaves_rights_intact():
    df = _frame([{
        "permit_last_date": pd.NaT,
        "permit_any_tama38": False, "permit_any_hakala": False, "permit_count": None,
    }])
    out = detect_consumption(df)
    assert out["rights_consumed"].iloc[0] == NONE
    assert out["gap_cap_factor"].iloc[0] == 1.0


def test_tama_overrides_partial_relief():
    """A TAMA 38 permit must win over a mere relief request."""
    df = _frame([{
        "permit_last_date": pd.Timestamp("1990-01-01"),
        "permit_any_tama38": True, "permit_any_hakala": True, "permit_count": 4,
    }])
    out = detect_consumption(df)
    assert out["rights_consumed"].iloc[0] == LIKELY_FULL
    assert "TAMA 38" in out["rights_consumed_reason"].iloc[0]


def test_boundary_date_is_inclusive():
    df = _frame([
        {"permit_last_date": pd.Timestamp("2017-12-31"),
         "permit_any_tama38": False, "permit_any_hakala": False, "permit_count": 1},
        {"permit_last_date": pd.Timestamp("2018-01-01"),
         "permit_any_tama38": False, "permit_any_hakala": False, "permit_count": 1},
    ])
    out = detect_consumption(df)
    assert list(out["rights_consumed"]) == [NONE, LIKELY_FULL]
