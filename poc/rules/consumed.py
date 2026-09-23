"""T2.3 - consumed-rights detection from permit history.

If a building already exercised its Rova 3 / TAMA 38 entitlement, the
remaining gap must be capped or zeroed. Getting this wrong is the single
fastest way to lose credibility with an investor, so the signals are
deliberately conservative.
"""
from __future__ import annotations

import pandas as pd

from poc import config

NONE = "none"
PARTIAL = "partial"
LIKELY_FULL = "likely_full"

# Fraction of the computed gap that survives each consumption state.
CAP_FACTORS = {NONE: 1.0, PARTIAL: 0.5, LIKELY_FULL: 0.0}


def detect_consumption(permits: pd.DataFrame) -> pd.DataFrame:
    """Classify rights consumption per building.

    Expects the permit-aggregate columns produced by ingest.joins:
      permit_last_date, permit_any_tama38, permit_any_hakala, permit_count

    Rules (any one is sufficient to move off `none`):
      - a TAMA 38 permit of any flavour            -> likely_full
      - a permit dated on/after the plan threshold -> likely_full
      - a non-empty hakala (relief) request        -> partial
    """
    idx = permits.index
    last_date = pd.to_datetime(permits.get("permit_last_date"), errors="coerce")
    tama = permits.get("permit_any_tama38", pd.Series(False, index=idx)).fillna(False).astype(bool)
    hakala = permits.get("permit_any_hakala", pd.Series(False, index=idx)).fillna(False).astype(bool)

    cutoff = pd.Timestamp(config.RIGHTS_CONSUMED_SINCE)
    recent = last_date.notna() & last_date.ge(cutoff)

    state = pd.Series(NONE, index=idx, dtype=object)
    state[hakala] = PARTIAL
    state[recent] = LIKELY_FULL
    state[tama] = LIKELY_FULL

    reason = pd.Series("", index=idx, dtype=object)
    reason[hakala] = "hakala request on file"
    reason[recent] = f"permit dated >= {config.RIGHTS_CONSUMED_SINCE}"
    reason[tama] = "TAMA 38 permit on file"

    return pd.DataFrame(
        {
            "rights_consumed": state,
            "rights_consumed_reason": reason,
            "gap_cap_factor": state.map(CAP_FACTORS).astype(float),
        }
    )
