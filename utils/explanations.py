"""
utils/explanations.py
======================
Generates human-readable "Detection Factors" (never called SHAP values --
no real SHAP computation is performed here) from the actual detector
outputs of a single detection result. Nothing here is a canned/generic
string unrelated to the current observation.
"""

from __future__ import annotations

SENSOR_DISPLAY = {
    "temperature": "Temperature",
    "pressure": "Pressure",
    "humidity": "Humidity",
    "wind_speed": "Wind speed",
    "rainfall": "Rainfall",
    "solar_radiation": "Solar radiation",
    "battery_voltage": "Battery voltage",
}


def generate_explanation(detection_result: dict, other_stations_stable: bool = True) -> dict:
    if not detection_result["anomaly"]:
        return {
            "log": ["All detectors report values within expected operating ranges."],
            "contributions": {},
        }

    sensor = detection_result["affected_sensor"]
    label = SENSOR_DISPLAY.get(sensor, sensor)
    d = detection_result["detectors"]
    score = detection_result["score_breakdown"]

    log = []
    if d["z_score_flag"] or abs(d["z_score"]) > 2:
        log.append(f"{label} deviated significantly from its recent baseline (robust z-score {d['z_score']:.1f}).")
    if d["rate_of_change_flag"]:
        log.append(f"Rate of change in {label.lower()} exceeded the normal historical range.")
    if d["physical_range_flag"]:
        log.append(f"{label} reading fell outside the physically valid sensor range.")
    if d["stuck_flag"]:
        log.append(f"{label} reported an unchanging (stuck) value across consecutive readings.")
    if d["missing_flag"]:
        log.append(f"{label} reading was missing, suggesting a communication or logging fault.")

    per_sensor = detection_result.get("per_sensor_detectors", {})
    if sensor in ("temperature",) and "humidity" in per_sensor:
        if per_sensor["humidity"]["z_score_flag"]:
            log.append("Temperature-humidity relationship became abnormal relative to typical station behavior.")

    if other_stations_stable:
        log.append("Nearby stations remained stable, suggesting a localized issue.")
    else:
        log.append("Nearby stations also show unusual readings, suggesting a broader environmental cause.")

    if not log:
        log.append("Multiple weak signals combined to raise the overall anomaly score.")

    contributions = {
        "ML model deviation": score["ml_score"],
        "Statistical deviation": score["statistical_score"],
        "Physical validation": score["physical_score"],
        "Temporal behavior": score["temporal_score"],
    }

    return {"log": log, "contributions": contributions}
