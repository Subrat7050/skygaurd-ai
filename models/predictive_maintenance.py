"""
models/predictive_maintenance.py
==================================
Tracks a per-(station, sensor) health score that decays with detected
anomalies and slowly recovers with normal behavior, plus maintenance
recommendations derived from the actual root cause.
"""

from __future__ import annotations

import config


def get_health_status(health: float) -> str:
    for label, (lo, hi) in config.HEALTH_STATUS_THRESHOLDS.items():
        if lo <= health < hi:
            return label
    return "HEALTHY" if health >= 90 else "CRITICAL"


def update_sensor_health(current_health: float, severity: str) -> float:
    """Apply one reading's worth of health decay/recovery."""
    decay = config.HEALTH_DECAY_PER_ANOMALY.get(severity, 0.0)
    if decay > 0:
        new_health = current_health - decay
    else:
        new_health = current_health + config.HEALTH_RECOVERY_PER_NORMAL_READING
    return float(max(config.MIN_SENSOR_HEALTH, min(100.0, new_health)))


def calculate_sensor_health_from_history(severity_history: list) -> dict:
    """Recompute health across an entire severity history (used to build
    the health timeline chart from scratch)."""
    health = 100.0
    trajectory = [health]
    for severity in severity_history:
        health = update_sensor_health(health, severity)
        trajectory.append(health)
    return {
        "initial_health": 100.0,
        "current_health": round(trajectory[-1], 1),
        "health_loss": round(100.0 - trajectory[-1], 1),
        "status": get_health_status(trajectory[-1]),
        "trajectory": trajectory,
    }


def generate_recommendation(root_cause_result: dict, sensor: str) -> str:
    cause = root_cause_result.get("probable_cause", "Unknown")
    recommendation_map = {
        "Communication / Data Quality Issue": "Inspect station communication module and connectivity.",
        "Power Supply Instability": "Inspect station power supply and battery connections.",
        "Rain Gauge Anomaly": "Inspect rain gauge and mechanical components.",
        "Multivariate Sensor Fault": "Schedule a full technician inspection of the sensor array.",
        "Possible Environmental Event": "No maintenance required; monitor for confirmation from nearby stations.",
        "Unknown": "Flag station for manual technician review.",
    }
    if cause in recommendation_map:
        return recommendation_map[cause]
    if "Drift" in cause:
        return f"Inspect {sensor} sensor due to repeated drift; recalibration likely required."
    if "Spike" in cause or "Fault" in cause:
        return f"Inspect {sensor} sensor wiring and calibration."
    return "Inspect sensor as part of next scheduled maintenance cycle."
