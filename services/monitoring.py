"""
services/monitoring.py
=======================
Aggregates per-station status into overall network health. All numbers are
computed from the live station-status table held in session state -- never
hardcoded.
"""

from __future__ import annotations

import pandas as pd

import config


def get_network_health(stations_status: pd.DataFrame) -> dict:
    total = len(stations_status)
    if total == 0:
        return {"healthy": 0, "warning": 0, "critical": 0, "total": 0, "network_health_pct": 100.0}

    counts = stations_status["status"].value_counts()
    healthy = int(counts.get("HEALTHY", 0))
    warning = int(counts.get("WARNING", 0))
    critical = int(counts.get("CRITICAL", 0))

    # Network health formula: healthy stations count fully, warning stations
    # count as half-weight, critical stations count as zero.
    network_health_pct = round(100.0 * (healthy + 0.5 * warning) / total, 1)

    return {
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "total": total,
        "network_health_pct": network_health_pct,
    }


def status_from_severity(severity: str) -> str:
    return config.STATION_STATUS_SEVERITY_MAP.get(severity, "HEALTHY")


def update_station_status(stations_status: pd.DataFrame, station_id: str, severity: str) -> pd.DataFrame:
    new_status = status_from_severity(severity)
    stations_status = stations_status.copy()
    stations_status.loc[stations_status["station_id"] == station_id, "status"] = new_status
    stations_status.loc[stations_status["station_id"] == station_id, "last_severity"] = severity
    return stations_status
