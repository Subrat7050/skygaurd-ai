"""
models/value_correction.py
============================
Estimates the expected ("corrected") value of a sensor flagged as
anomalous, using a weighted ensemble of:
  - rolling median (recent short-term behavior)
  - local temporal interpolation (neighboring readings)
  - station historical baseline (longer-term expanding mean)

This is a reconstruction heuristic appropriate for a prototype -- not a
fixed offset subtraction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config


def correct_sensor_value(
    sensor: str,
    original_value: float,
    station_history: pd.DataFrame,
    is_anomaly: bool,
) -> dict:
    if not is_anomaly or sensor not in station_history.columns:
        return {
            "original_value": original_value,
            "corrected_value": original_value,
            "correction_confidence": 100.0,
            "correction_applied": False,
            "reason": "Value within expected range; no correction necessary.",
        }

    series = station_history[sensor].dropna()
    if series.empty:
        lo, hi = config.SENSOR_RANGES[sensor]
        fallback = (lo + hi) / 2
        return {
            "original_value": original_value,
            "corrected_value": round(fallback, 2),
            "correction_confidence": 40.0,
            "correction_applied": True,
            "reason": "Insufficient station history; used sensor's physical mid-range as an estimate.",
        }

    rolling_median = series.tail(config.ROLLING_WINDOW).median()
    local_interp = series.tail(3).mean()  # simple local-neighborhood average
    station_baseline = series.mean()  # expanding/historical baseline

    weights = {"rolling_median": 0.45, "local_interp": 0.35, "station_baseline": 0.20}
    corrected = (
        weights["rolling_median"] * rolling_median
        + weights["local_interp"] * local_interp
        + weights["station_baseline"] * station_baseline
    )

    lo, hi = config.SENSOR_RANGES[sensor]
    corrected = float(np.clip(corrected, lo, hi))

    # Correction confidence: higher when the ensemble components agree
    # closely with each other (low spread => more confident reconstruction).
    components = np.array([rolling_median, local_interp, station_baseline])
    spread = float(np.std(components))
    sensor_range = hi - lo
    agreement = 1.0 - min(spread / (sensor_range * 0.15 + 1e-6), 1.0)
    confidence = 60 + agreement * 38

    deviation_pct = (
        abs(original_value - corrected) / (abs(corrected) + 1e-6) * 100
        if not pd.isna(original_value)
        else 100.0
    )
    if deviation_pct > 15:
        reason = "Value significantly deviates from the recent station baseline."
    else:
        reason = "Minor deviation reconstructed using rolling median and local trend."

    return {
        "original_value": None if pd.isna(original_value) else round(float(original_value), 2),
        "corrected_value": round(corrected, 2),
        "correction_confidence": round(float(np.clip(confidence, 0, 100)), 1),
        "correction_applied": True,
        "reason": reason,
    }
