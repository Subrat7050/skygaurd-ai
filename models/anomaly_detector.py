"""
models/anomaly_detector.py
===========================
Combines the primary Isolation Forest model with several lightweight
supporting detectors into one fused, human-readable anomaly assessment.

Supporting detectors (section 16 of the spec):
  1. Robust Z-score
  2. Rolling median deviation
  3. Rate-of-change detector
  4. Physical range validation
  5. Stuck sensor detector
  6. Missing data detector

detect_anomaly() is the single public entry point used by both the
Streamlit UI and (in the future) a FastAPI endpoint -- it returns a plain
dict so it is trivially JSON-serializable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from services import preprocessing as pp


# --------------------------------------------------------------------------
# ML anomaly score (Isolation Forest)
# --------------------------------------------------------------------------
def ml_anomaly_score(model, preprocessor, feature_row_df: pd.DataFrame) -> tuple[float, bool]:
    """Return (0-100 normalized ML anomaly score, raw_is_anomaly_flag)."""
    X = pp.transform(preprocessor, feature_row_df)
    raw_score = model.decision_function(X)[0]  # higher = more normal
    prediction = model.predict(X)[0]  # -1 = anomaly, 1 = normal
    is_anomaly = prediction == -1

    # decision_function is roughly centered at 0; typical range ~[-0.25, 0.25].
    # Map so that more-negative (more anomalous) -> higher 0-100 score.
    normalized = 100.0 / (1.0 + np.exp((raw_score + 0.02) * 18))
    normalized = float(np.clip(normalized, 0, 100))
    return normalized, bool(is_anomaly)


# --------------------------------------------------------------------------
# Supporting detectors
# --------------------------------------------------------------------------
def robust_zscore(value: float, history: pd.Series) -> tuple[float, bool]:
    """Median/MAD-based z-score -- robust to the very outliers we're
    trying to detect."""
    if history.empty or history.isna().all():
        return 0.0, False
    median = history.median()
    mad = (history - median).abs().median()
    mad = mad if mad > 1e-6 else history.std() + 1e-6
    if mad == 0 or np.isnan(mad):
        return 0.0, False
    z = 0.6745 * (value - median) / mad
    return float(z), bool(abs(z) > config.Z_SCORE_THRESHOLD)


def rolling_median_deviation(value: float, history: pd.Series) -> float:
    if history.empty:
        return 0.0
    med = history.tail(config.ROLLING_WINDOW).median()
    if pd.isna(med):
        return 0.0
    return float(value - med)


def rate_of_change_detector(sensor: str, value: float, previous_value: float | None) -> tuple[float, bool]:
    if previous_value is None or pd.isna(previous_value) or pd.isna(value):
        return 0.0, False
    delta = abs(value - previous_value)
    threshold = config.RATE_OF_CHANGE_THRESHOLD.get(sensor)
    if threshold is None:
        return float(delta), False
    return float(delta), bool(delta > threshold)


def physical_range_validation(sensor: str, value: float) -> bool:
    if pd.isna(value):
        return False
    lo, hi = config.SENSOR_RANGES[sensor]
    return not (lo <= value <= hi)


def stuck_sensor_detector(sensor: str, history: pd.Series) -> bool:
    tail = history.tail(config.STUCK_SENSOR_MIN_REPEATS)
    if len(tail) < config.STUCK_SENSOR_MIN_REPEATS:
        return False
    # Rainfall and solar radiation are legitimately flat at zero for long
    # stretches (dry spells / nighttime) -- that is normal, not a stuck
    # sensor, so we don't flag a flat run sitting at the sensor's natural
    # resting value.
    if sensor in ("rainfall", "solar_radiation") and tail.max() <= config.STUCK_SENSOR_TOLERANCE:
        return False
    return bool((tail.max() - tail.min()) <= config.STUCK_SENSOR_TOLERANCE)


def missing_data_detector(value: float) -> bool:
    return bool(pd.isna(value))


def run_supporting_detectors(sensor: str, value: float, station_history: pd.DataFrame) -> dict:
    """Run every supporting detector for the affected sensor and return a
    structured summary used for statistical/physical/temporal scoring."""
    history_series = station_history[sensor] if sensor in station_history else pd.Series(dtype=float)
    previous_value = history_series.iloc[-1] if len(history_series) else None

    z, z_flag = robust_zscore(value, history_series)
    median_dev = rolling_median_deviation(value, history_series)
    roc, roc_flag = rate_of_change_detector(sensor, value, previous_value)
    out_of_range = physical_range_validation(sensor, value)
    stuck = stuck_sensor_detector(sensor, history_series)
    missing = missing_data_detector(value)

    return {
        "z_score": z,
        "z_score_flag": z_flag,
        "median_deviation": median_dev,
        "rate_of_change": roc,
        "rate_of_change_flag": roc_flag,
        "physical_range_flag": out_of_range,
        "stuck_flag": stuck,
        "missing_flag": missing,
    }


# --------------------------------------------------------------------------
# Score fusion
# --------------------------------------------------------------------------
def _statistical_score(detectors: dict) -> float:
    z = min(abs(detectors["z_score"]) / (config.Z_SCORE_THRESHOLD * 2.5), 1.0)
    return float(np.clip(z * 100, 0, 100))


def _physical_score(detectors: dict) -> float:
    if detectors["physical_range_flag"]:
        return 100.0
    if detectors["missing_flag"]:
        return 80.0
    return 0.0


def _temporal_score(detectors: dict) -> float:
    score = 0.0
    if detectors["rate_of_change_flag"]:
        score += 60.0
    if detectors["stuck_flag"]:
        score += 60.0
    return float(np.clip(score, 0, 100))


def combine_scores(ml_score: float, detectors: dict) -> dict:
    stat_score = _statistical_score(detectors)
    phys_score = _physical_score(detectors)
    temp_score = _temporal_score(detectors)

    w = config.SCORE_WEIGHTS
    final_score = (
        w["ml_score"] * ml_score
        + w["statistical_score"] * stat_score
        + w["physical_score"] * phys_score
        + w["temporal_score"] * temp_score
    )
    final_score = float(np.clip(final_score, 0, 100))

    return {
        "ml_score": round(ml_score, 1),
        "statistical_score": round(stat_score, 1),
        "physical_score": round(phys_score, 1),
        "temporal_score": round(temp_score, 1),
        "final_score": round(final_score, 1),
    }


def calculate_confidence(ml_anomaly_flag: bool, detectors: dict) -> float:
    """Confidence = fraction of independent detectors that agree an anomaly
    is present, scaled to 0-100 with a floor from the ML model's own
    certainty."""
    flags = [
        ml_anomaly_flag,
        detectors["z_score_flag"],
        detectors["rate_of_change_flag"],
        detectors["physical_range_flag"] or detectors["missing_flag"],
        detectors["stuck_flag"],
    ]
    agreement = sum(1 for f in flags if f) / len(flags)
    confidence = 55 + agreement * 45  # at least one signal -> 55%+, unanimous -> 100%
    if not any(flags):
        confidence = 15 + min(abs(detectors["z_score"]) * 5, 20)
    return float(np.clip(confidence, 0, 100))


def calculate_severity(score: float) -> str:
    for label, (lo, hi) in config.SEVERITY_THRESHOLDS.items():
        if lo <= score < hi:
            return label
    return "CRITICAL"


# --------------------------------------------------------------------------
# Main inference entry point
# --------------------------------------------------------------------------
def detect_anomaly(
    model,
    preprocessor,
    observation: dict,
    station_history: pd.DataFrame,
) -> dict:
    """
    Run the full detection pipeline on a single live observation.

    Parameters
    ----------
    observation : dict with at least station_id, timestamp, and every raw
        sensor reading (see config.FEATURE_SENSORS).
    station_history : DataFrame of this station's recent prior readings
        (used for rolling/z-score/stuck-sensor context). Must NOT include
        `observation` itself.

    Returns
    -------
    Structured, JSON-serializable dict -- see spec section 43.
    """
    obs_df = pd.DataFrame([observation])
    combined_history = pd.concat([station_history, obs_df], ignore_index=True, sort=False)
    combined_with_features = pp.build_features(combined_history)
    current_row = combined_with_features.iloc[[-1]]

    ml_score, ml_flag = ml_anomaly_score(model, preprocessor, current_row)

    # Determine the "most suspicious" sensor by comparing each sensor's
    # z-score against recent station history, then run full supporting
    # detectors against that sensor.
    best_sensor = None
    best_z = -1.0
    per_sensor_detectors = {}
    for sensor in config.FEATURE_SENSORS:
        value = observation.get(sensor, np.nan)
        det = run_supporting_detectors(sensor, value, station_history)
        per_sensor_detectors[sensor] = det
        score_for_ranking = max(
            abs(det["z_score"]),
            50 if det["physical_range_flag"] else 0,
            45 if det["rate_of_change_flag"] else 0,
            40 if det["stuck_flag"] else 0,
            30 if det["missing_flag"] else 0,
        )
        if score_for_ranking > best_z:
            best_z = score_for_ranking
            best_sensor = sensor

    detectors = per_sensor_detectors[best_sensor]
    fused = combine_scores(ml_score, detectors)
    confidence = calculate_confidence(ml_flag, detectors)
    severity = calculate_severity(fused["final_score"])
    is_anomaly = severity != "NORMAL"

    return {
        "station_id": observation.get("station_id"),
        "timestamp": str(observation.get("timestamp")),
        "anomaly": bool(is_anomaly),
        "anomaly_score": fused["final_score"],
        "score_breakdown": fused,
        "confidence": round(confidence, 1),
        "severity": severity,
        "affected_sensor": best_sensor,
        "affected_value": observation.get(best_sensor),
        "detectors": detectors,
        "per_sensor_detectors": per_sensor_detectors,
        "ml_flag": ml_flag,
        "observation": observation,
    }
