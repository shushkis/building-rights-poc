"""T3.1 - as-built floor estimate with an honest confidence grade.

Primary source is `ms_komot` (the municipal floor count, 99.4% populated).
Height-derived estimates are CORROBORATORS, not replacements: DSM heights
carry roughly +/-1.7 floors of noise, so they can raise or lower confidence
but only substitute when ms_komot is missing entirely.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from poc import config

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"


def floors_from_height(height_m: pd.Series) -> pd.Series:
    """Invert the fitted gova_simplex model to a floor count."""
    est = (height_m - config.HEIGHT_MODEL_INTERCEPT_M) / config.HEIGHT_MODEL_SLOPE_M
    return est.where(height_m.notna() & (height_m > 0))


def floors_from_dsm(dsm_height_m: pd.Series) -> pd.Series:
    """Invert the separately-fitted DSM model (different vertical datum)."""
    est = (dsm_height_m - config.DSM_MODEL_INTERCEPT_M) / config.DSM_MODEL_SLOPE_M
    return est.where(dsm_height_m.notna() & (dsm_height_m > 0))


def estimate_asbuilt(m: pd.DataFrame) -> pd.DataFrame:
    """Return floors_est + confidence + the corroborating evidence."""
    idx = m.index
    komot = pd.to_numeric(m.get("ms_komot"), errors="coerce")

    height = pd.to_numeric(m.get("gova_simplex_2019"), errors="coerce")
    dsm_height = pd.to_numeric(m.get("dsm_max"), errors="coerce") - pd.to_numeric(
        m.get("min_height"), errors="coerce"
    )

    est_h = floors_from_height(height)
    est_dsm = floors_from_dsm(dsm_height)

    # --- primary estimate --------------------------------------------------
    floors_est = komot.copy()
    used_fallback = komot.isna() & est_h.notna()
    floors_est[used_fallback] = est_h[used_fallback].round()
    # Last resort: the DSM difference.
    still = floors_est.isna() & est_dsm.notna()
    floors_est[still] = est_dsm[still].round()

    floors_est = floors_est.clip(lower=0)

    # --- agreement of the corroborators ------------------------------------
    d_h = (est_h - komot).abs()
    d_dsm = (est_dsm - komot).abs()
    tol = config.AGREEMENT_TOLERANCE_FLOORS
    agree_h = d_h <= tol
    agree_dsm = d_dsm <= tol
    n_checks = d_h.notna().astype(int) + d_dsm.notna().astype(int)
    n_agree = agree_h.fillna(False).astype(int) + agree_dsm.fillna(False).astype(int)

    confidence = pd.Series(MEDIUM, index=idx, dtype=object)
    confidence[komot.notna() & (n_checks > 0) & (n_agree == n_checks)] = HIGH
    confidence[komot.notna() & (n_checks > 0) & (n_agree < n_checks)] = MEDIUM
    # No corroborator available at all -> cannot claim HIGH.
    confidence[komot.notna() & (n_checks == 0)] = MEDIUM
    # ms_komot missing -> estimated from height alone.
    confidence[komot.isna()] = LOW
    confidence[floors_est.isna()] = LOW

    return pd.DataFrame(
        {
            "floors_est": floors_est,
            "floors_source": np.where(
                komot.notna(), "ms_komot",
                np.where(used_fallback, "height_model", "dsm_model"),
            ),
            "floors_est_height": est_h.round(2),
            "floors_est_dsm": est_dsm.round(2),
            "floors_checks": n_checks,
            "floors_checks_agree": n_agree,
            "confidence": confidence,
        }
    )
