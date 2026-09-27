"""
services/simulation.py
========================
Framework-agnostic "live" simulation engine. Streamlit's session_state
holds one instance of SimulationState; every UI refresh calls .step(...)
on it. This module has no Streamlit imports so the same engine could later
back a FastAPI polling/websocket endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config
from models import anomaly_detector, predictive_maintenance, root_cause, value_correction
from services import data_generator, monitoring
from utils import explanations

HISTORY_BUFFER_SIZE = 60  # readings kept in memory per station for rolling context


@dataclass
class SimulationState:
    stations: pd.DataFrame
    model: object
    preprocessor: object
    seed: int = config.RANDOM_SEED

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed + 999)
        self.history: dict[str, pd.DataFrame] = {}
        self.sensor_health: dict[tuple, float] = {}
        self.severity_history: dict[tuple, list] = {}
        self.detection_log: list = []
        self.latest_result: dict | None = None
        self.latest_by_station: dict[str, dict] = {}
        self.station_status = self.stations[["station_id"]].copy()
        self.station_status["status"] = "HEALTHY"
        self.station_status["last_severity"] = "NORMAL"

    def seed_history(self, historical_df: pd.DataFrame):
        """Populate each station's rolling buffer with its most recent real
        historical rows (post-training data is fine to reuse for buffer
        context; this does not affect the already-trained model)."""
        for station_id, g in historical_df.groupby("station_id"):
            self.history[station_id] = g.sort_values("timestamp").tail(HISTORY_BUFFER_SIZE).reset_index(drop=True)
        for sensor in config.FEATURE_SENSORS:
            for station_id in self.stations["station_id"]:
                self.sensor_health[(station_id, sensor)] = 100.0
                self.severity_history[(station_id, sensor)] = []

    def _other_stations_stable(self, station_id: str) -> bool:
        others = [s for s in self.stations["station_id"] if s != station_id]
        sample = self.rng.choice(others, size=min(3, len(others)), replace=False)
        stable_flags = [
            self.station_status.loc[self.station_status["station_id"] == s, "status"].iloc[0] == "HEALTHY"
            for s in sample
        ]
        return all(stable_flags)

    def step(self, station_id: str, inject: tuple | None = None, forced_values: dict | None = None) -> dict:
        """
        Advance one station by one reading.

        inject: optional (sensor, anomaly_type) tuple to deliberately
        corrupt the newly generated reading using the simulator's generic
        anomaly-injection logic (random magnitude/direction).

        forced_values: optional {sensor: value} overrides applied AFTER
        generation/injection -- used by "SIH Demo Mode" to reproduce the
        specific, polished demo scenario (e.g. a ~55C temperature spike)
        deterministically, while still routing the reading through the
        exact same detection pipeline as any other observation.
        """
        history = self.history.get(station_id)
        if history is None or history.empty:
            raise ValueError(f"No history seeded for station {station_id}")

        previous_row = history.iloc[-1]
        observation = data_generator.build_live_observation(station_id, previous_row, self.rng)

        if inject is not None:
            sensor, anomaly_type = inject
            observation = data_generator.inject_live_anomaly(observation, sensor, anomaly_type, self.rng)

        if forced_values:
            for sensor, value in forced_values.items():
                observation[sensor] = value
            observation["actual_anomaly"] = 1
            observation["anomaly_type"] = observation.get("anomaly_type", "spike")
            if observation["anomaly_type"] == "none":
                observation["anomaly_type"] = "spike"

        result = anomaly_detector.detect_anomaly(self.model, self.preprocessor, observation, history)
        other_stable = self._other_stations_stable(station_id)
        cause = root_cause.classify_root_cause(result, other_stations_stable=other_stable)
        correction = value_correction.correct_sensor_value(
            result["affected_sensor"], result["affected_value"], history, result["anomaly"]
        )
        explanation = explanations.generate_explanation(result, other_stations_stable=other_stable)

        sensor = result["affected_sensor"]
        key = (station_id, sensor)
        self.severity_history.setdefault(key, []).append(result["severity"])
        current_health = self.sensor_health.get(key, 100.0)
        new_health = predictive_maintenance.update_sensor_health(current_health, result["severity"])
        self.sensor_health[key] = new_health
        health_status = predictive_maintenance.get_health_status(new_health)
        recommendation = predictive_maintenance.generate_recommendation(cause, sensor)

        # Update rolling history buffer with the *corrected* view for
        # continuity (so a single spike doesn't permanently poison the
        # rolling stats), but keep the raw observation for display/logs.
        new_row = pd.DataFrame([observation])
        self.history[station_id] = pd.concat([history, new_row], ignore_index=True).tail(HISTORY_BUFFER_SIZE)

        self.station_status = monitoring.update_station_status(
            self.station_status, station_id, result["severity"]
        )

        full_result = {
            "detection": result,
            "root_cause": cause,
            "correction": correction,
            "explanation": explanation,
            "sensor_health": {
                "initial_health": 100.0,
                "current_health": round(new_health, 1),
                "health_loss": round(100.0 - new_health, 1),
                "status": health_status,
            },
            "recommendation": recommendation,
            "other_stations_stable": other_stable,
        }
        self.latest_result = full_result
        self.latest_by_station[station_id] = full_result
        self.detection_log.append(full_result)
        self.detection_log = self.detection_log[-200:]
        return full_result

    def get_latest(self, station_id: str) -> dict | None:
        return self.latest_by_station.get(station_id)

    def get_health_trajectory(self, station_id: str, sensor: str) -> dict:
        history = self.severity_history.get((station_id, sensor), [])
        return predictive_maintenance.calculate_sensor_health_from_history(history)
