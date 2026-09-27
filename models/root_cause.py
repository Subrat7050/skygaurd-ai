"""
models/root_cause.py
=====================
Rule-driven root cause classification built directly from the detector
outputs produced by models.anomaly_detector.detect_anomaly(). Nothing is
chosen randomly -- every branch below is conditioned on the actual
detector signals for the current observation.
"""

from __future__ import annotations

SENSOR_LABELS = {
    "temperature": "Temperature Sensor",
    "pressure": "Pressure Sensor",
    "humidity": "Humidity Sensor",
    "wind_speed": "Wind Sensor",
    "rainfall": "Rain Gauge",
    "solar_radiation": "Solar Radiation Sensor",
    "battery_voltage": "Power Supply",
}


def classify_root_cause(detection_result: dict, other_stations_stable: bool = True) -> dict:
    """
    Parameters
    ----------
    detection_result : the dict returned by detect_anomaly()
    other_stations_stable : whether nearby stations show no simultaneous
        anomaly (used to distinguish a localized sensor fault from a
        genuine, widespread environmental event).

    Returns
    -------
    dict with probable_cause, affected_sensor label, confidence,
    recommended_action.
    """
    if not detection_result["anomaly"]:
        return {
            "probable_cause": "No Anomaly",
            "affected_sensor": "N/A",
            "confidence": 100.0,
            "recommended_action": "No action required. Continue routine monitoring.",
        }

    sensor = detection_result["affected_sensor"]
    detectors = detection_result["detectors"]
    per_sensor = detection_result["per_sensor_detectors"]
    confidence = detection_result["confidence"]
    sensor_label = SENSOR_LABELS.get(sensor, sensor)

    # Count how many other sensors are also flagged -> multivariate signal
    other_flagged = [
        s
        for s, d in per_sensor.items()
        if s != sensor and (d["z_score_flag"] or d["physical_range_flag"] or d["rate_of_change_flag"])
    ]

    if detectors["missing_flag"]:
        cause = "Communication / Data Quality Issue"
        action = "Inspect station communication module and connectivity."
    elif sensor == "battery_voltage" and (detectors["rate_of_change_flag"] or detectors["z_score_flag"]):
        cause = "Power Supply Instability"
        action = "Inspect station power supply and battery connections."
    elif len(other_flagged) >= 2 and not other_stations_stable:
        cause = "Possible Environmental Event"
        action = "Cross-check with regional weather bulletin; no immediate sensor fault suspected."
    elif len(other_flagged) >= 2 and other_stations_stable:
        cause = "Multivariate Sensor Fault"
        action = "Inspect full sensor array wiring and data logger calibration."
    elif detectors["stuck_flag"]:
        cause = f"{sensor_label.split(' Sensor')[0]} Sensor Fault"
        action = f"Inspect {sensor_label.lower()} for a frozen/stuck reading and replace if unresponsive."
    elif detectors["physical_range_flag"]:
        cause = f"{sensor_label.split(' Sensor')[0]} Sensor Spike / Sensor Fault"
        action = f"Inspect {sensor_label.lower()} wiring and calibration."
    elif detectors["rate_of_change_flag"] and abs(detectors["z_score"]) > 4:
        cause = f"{sensor_label.split(' Sensor')[0]} Sensor Spike / Sensor Fault"
        action = f"Inspect {sensor_label.lower()} wiring and calibration."
    elif detectors["z_score_flag"]:
        cause = f"{sensor_label.split(' Sensor')[0]} Sensor Drift"
        action = f"Inspect {sensor_label.lower()} calibration; drift suggests gradual degradation."
    elif sensor == "rainfall":
        cause = "Rain Gauge Anomaly"
        action = "Inspect rain gauge and mechanical components."
    else:
        cause = "Unknown"
        action = "Flag for manual technician review."

    return {
        "probable_cause": cause,
        "affected_sensor": sensor_label,
        "confidence": round(confidence, 1),
        "recommended_action": action,
        "corroborating_sensors": other_flagged,
    }
