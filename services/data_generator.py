"""
services/data_generator.py
===========================
Simulates a network of Automatic Weather Stations (AWS) and generates a
realistic historical sensor dataset entirely offline -- no external
weather APIs, no cloud dependency.

Design goals
------------
1. Sensor readings are NOT independent random draws. Each variable follows
   a baseline + slow trend + diurnal seasonality + small noise, so the
   resulting time series looks like real telemetry (see config-level
   comments and README "Realistic Simulation").
2. A small fraction of observations are deliberately corrupted with one of
   several realistic anomaly types. The ground-truth labels
   (`actual_anomaly`, `anomaly_type`) are stored ONLY for evaluation and
   must never be passed to the model as a feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config

INDIAN_CITIES = [
    ("AWS-001", "Raipur Central AWS", "Raipur", "Chhattisgarh", 21.2514, 81.6296),
    ("AWS-002", "Delhi Ridge AWS", "New Delhi", "Delhi", 28.6139, 77.2090),
    ("AWS-003", "Mumbai Coastal AWS", "Mumbai", "Maharashtra", 19.0760, 72.8777),
    ("AWS-004", "Kolkata Riverside AWS", "Kolkata", "West Bengal", 22.5726, 88.3639),
    ("AWS-005", "Chennai Marina AWS", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
    ("AWS-006", "Bengaluru Tech AWS", "Bengaluru", "Karnataka", 12.9716, 77.5946),
    ("AWS-007", "Hyderabad Hills AWS", "Hyderabad", "Telangana", 17.3850, 78.4867),
    ("AWS-008", "Jaipur Desert AWS", "Jaipur", "Rajasthan", 26.9124, 75.7873),
    ("AWS-009", "Lucknow Plains AWS", "Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    ("AWS-010", "Ahmedabad AWS", "Ahmedabad", "Gujarat", 23.0225, 72.5714),
    ("AWS-011", "Bhopal Lakes AWS", "Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    ("AWS-012", "Patna Riverfront AWS", "Patna", "Bihar", 25.5941, 85.1376),
    ("AWS-013", "Guwahati Valley AWS", "Guwahati", "Assam", 26.1445, 91.7362),
    ("AWS-014", "Bhubaneswar AWS", "Bhubaneswar", "Odisha", 20.2961, 85.8245),
    ("AWS-015", "Chandigarh AWS", "Chandigarh", "Chandigarh", 30.7333, 76.7794),
    ("AWS-016", "Dehradun Foothills AWS", "Dehradun", "Uttarakhand", 30.3165, 78.0322),
    ("AWS-017", "Shimla Highland AWS", "Shimla", "Himachal Pradesh", 31.1048, 77.1734),
    ("AWS-018", "Kochi Coastal AWS", "Kochi", "Kerala", 9.9312, 76.2673),
    ("AWS-019", "Nagpur Central AWS", "Nagpur", "Maharashtra", 21.1458, 79.0882),
    ("AWS-020", "Indore Plateau AWS", "Indore", "Madhya Pradesh", 22.7196, 75.8577),
]


def get_stations() -> pd.DataFrame:
    """Return the static AWS station network as a DataFrame."""
    rows = []
    for station_id, name, city, state, lat, lon in INDIAN_CITIES[: config.NUM_STATIONS]:
        rows.append(
            {
                "station_id": station_id,
                "station_name": name,
                "city": city,
                "state": state,
                "latitude": lat,
                "longitude": lon,
                "status": "HEALTHY",
            }
        )
    return pd.DataFrame(rows)


def _diurnal(hour_of_day: np.ndarray, peak_hour: float, amplitude: float) -> np.ndarray:
    """Smooth 24h cycle peaking at `peak_hour`."""
    return amplitude * np.cos((hour_of_day - peak_hour) / 24.0 * 2 * np.pi)


def _generate_station_series(station_id: str, lat: float, rng: np.random.Generator, n: int, freq_minutes: int) -> pd.DataFrame:
    """Generate a single station's clean (pre-anomaly) sensor time series."""
    timestamps = pd.date_range(
        end=pd.Timestamp.utcnow().floor("h"),
        periods=n,
        freq=f"{freq_minutes}min",
    )
    hour_of_day = timestamps.hour + timestamps.minute / 60.0
    day_index = np.arange(n) / (24 * 60 / freq_minutes)  # days elapsed, fractional

    # Latitude drives a very rough baseline temperature (hotter near equator)
    base_temp = 34.0 - 0.28 * abs(lat)
    seasonal_drift = 1.5 * np.sin(day_index / 30.0 * 2 * np.pi)  # slow ~monthly wobble
    temp_noise = rng.normal(0, 0.4, n)
    temperature = (
        base_temp
        + seasonal_drift
        + _diurnal(hour_of_day, peak_hour=15, amplitude=6.0)
        + np.cumsum(rng.normal(0, 0.05, n))  # gentle random walk for continuity
        + temp_noise
    )
    temperature = np.clip(temperature, 5, 46)

    # Pressure: slow-moving random walk around a station baseline
    base_pressure = 1005 + rng.normal(0, 8)
    pressure = base_pressure + np.cumsum(rng.normal(0, 0.15, n))
    pressure = np.clip(pressure, 950, 1050)

    # Humidity: inversely related to temperature, plus rain bumps
    humidity = np.clip(95 - (temperature - base_temp) * 3.2 + rng.normal(0, 3, n), 15, 100)

    # Rainfall: sparse bursts that push humidity up
    rain_prob = 0.04
    rain_events = rng.random(n) < rain_prob
    rainfall = np.where(rain_events, rng.exponential(6.0, n), 0.0)
    humidity = np.clip(humidity + rainfall * 0.8, 15, 100)
    rainfall = np.clip(rainfall, 0, 95)

    # Wind speed: autocorrelated (AR(1)-like) walk
    wind_speed = np.zeros(n)
    wind_speed[0] = max(0, rng.normal(4, 2))
    for i in range(1, n):
        wind_speed[i] = max(0, 0.85 * wind_speed[i - 1] + rng.normal(1.0, 1.2))
    wind_speed = np.clip(wind_speed, 0, 28)

    wind_direction = (np.cumsum(rng.normal(0, 8, n)) % 360 + 360) % 360

    # Solar radiation: strictly diurnal, zero at night
    daylight = np.clip(np.cos((hour_of_day - 12.5) / 24.0 * 2 * np.pi) * 1.35, -1, 1)
    solar_radiation = np.clip(daylight, 0, None) * 950 + rng.normal(0, 15, n)
    solar_radiation *= (1 - np.clip(rainfall / 40, 0, 0.8))  # clouds/rain dim the sun
    solar_radiation = np.clip(solar_radiation, 0, 1150)

    # Battery voltage: charges with solar, slowly drains overnight
    battery_voltage = 13.0 + 0.9 * (solar_radiation / 950) - 0.35 * (1 - solar_radiation / 950)
    battery_voltage += rng.normal(0, 0.05, n)
    battery_voltage = np.clip(battery_voltage, 11.2, 13.8)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "station_id": station_id,
            "temperature": temperature,
            "pressure": pressure,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "rainfall": rainfall,
            "wind_direction": wind_direction,
            "solar_radiation": solar_radiation,
            "battery_voltage": battery_voltage,
            "actual_anomaly": 0,
            "anomaly_type": "none",
        }
    )


def _apply_anomaly(row: pd.Series, anomaly_type: str, sensor: str, rng: np.random.Generator) -> pd.Series:
    """Corrupt a single already-generated row in place, tagging ground truth."""
    row = row.copy()
    lo, hi = config.SENSOR_RANGES[sensor]

    if anomaly_type == "spike":
        direction = rng.choice([-1, 1])
        row[sensor] = row[sensor] + direction * rng.uniform(0.55, 0.9) * (hi - lo)
    elif anomaly_type == "drift":
        row[sensor] = row[sensor] + rng.uniform(0.25, 0.45) * (hi - lo)
    elif anomaly_type == "stuck":
        row[sensor] = row[sensor]  # value frozen -- handled across consecutive rows by caller
    elif anomaly_type == "impossible_value":
        row[sensor] = hi * rng.uniform(1.15, 1.6)
    elif anomaly_type == "multivariate":
        row["temperature"] = row["temperature"] + rng.uniform(8, 14)
        row["pressure"] = row["pressure"] - rng.uniform(10, 18)
        row["humidity"] = np.clip(row["humidity"] - rng.uniform(20, 35), 0, 100)
    elif anomaly_type == "communication_error":
        row[sensor] = np.nan

    row["actual_anomaly"] = 1
    row["anomaly_type"] = anomaly_type
    return row


def generate_historical_dataset(seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """
    Generate the full multi-station historical dataset used for training
    and evaluation. Includes injected ground-truth-labeled anomalies.
    """
    rng = np.random.default_rng(seed)
    stations = get_stations()
    n_periods = int(config.HISTORY_DAYS * 24 * 60 / config.SAMPLE_INTERVAL_MINUTES)

    frames = []
    for _, s in stations.iterrows():
        df = _generate_station_series(
            s["station_id"], s["latitude"], rng, n_periods, config.SAMPLE_INTERVAL_MINUTES
        )
        frames.append(df)

    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

    # ---- Inject anomalies -------------------------------------------------
    # Choose candidate rows independently at random across the whole dataset.
    n_rows = len(full)
    n_anomalies = int(n_rows * config.ANOMALY_INJECTION_RATE)
    candidate_idx = rng.choice(n_rows, size=n_anomalies, replace=False)

    for idx in candidate_idx:
        anomaly_type = rng.choice(config.ANOMALY_TYPES)
        sensor = rng.choice(config.FEATURE_SENSORS) if anomaly_type != "multivariate" else "temperature"
        full.loc[idx] = _apply_anomaly(full.loc[idx], anomaly_type, sensor, rng)

        if anomaly_type == "stuck":
            # Freeze the next few readings of this station/sensor at the same value
            station_id = full.loc[idx, "station_id"]
            frozen_value = full.loc[idx, sensor]
            station_mask = full["station_id"] == station_id
            station_rows = full[station_mask].index
            pos = list(station_rows).index(idx)
            repeats = rng.integers(config.STUCK_SENSOR_MIN_REPEATS, config.STUCK_SENSOR_MIN_REPEATS + 3)
            for offset in range(1, repeats + 1):
                if pos + offset < len(station_rows):
                    target = station_rows[pos + offset]
                    full.loc[target, sensor] = frozen_value
                    full.loc[target, "actual_anomaly"] = 1
                    full.loc[target, "anomaly_type"] = "stuck"

    # A handful of duplicate rows / irregular gaps to exercise data-quality handling
    dup_idx = rng.choice(n_rows, size=max(1, n_rows // 500), replace=False)
    dup_rows = full.loc[dup_idx].copy()
    full = pd.concat([full, dup_rows], ignore_index=True)
    full = full.sort_values(["station_id", "timestamp"]).reset_index(drop=True)

    return full


def build_live_observation(
    station_id: str,
    previous_row: pd.Series,
    rng: np.random.Generator,
    minute_delta: int = config.SAMPLE_INTERVAL_MINUTES,
) -> dict:
    """Generate the next "live" normal reading for a station based on its
    previous reading, used by the simulation mode."""
    hour_of_day = (previous_row["timestamp"] + pd.Timedelta(minutes=minute_delta)).hour
    new_temp = previous_row["temperature"] + rng.normal(0, 0.3)
    new_pressure = previous_row["pressure"] + rng.normal(0, 0.15)
    new_humidity = np.clip(previous_row["humidity"] + rng.normal(0, 1.2), 10, 100)
    new_wind = max(0, 0.85 * previous_row["wind_speed"] + rng.normal(1.0, 1.0))
    new_rain = max(0.0, previous_row["rainfall"] * 0.5 + (rng.exponential(1.0) if rng.random() < 0.03 else 0))
    new_wind_dir = (previous_row["wind_direction"] + rng.normal(0, 6)) % 360
    daylight = max(0, np.cos((hour_of_day - 12.5) / 24.0 * 2 * np.pi) * 1.35)
    new_solar = np.clip(daylight * 950 + rng.normal(0, 15), 0, 1150)
    new_battery = np.clip(previous_row["battery_voltage"] + rng.normal(0, 0.05), 11.0, 13.8)

    return {
        "timestamp": previous_row["timestamp"] + pd.Timedelta(minutes=minute_delta),
        "station_id": station_id,
        "temperature": float(np.clip(new_temp, 0, 50)),
        "pressure": float(np.clip(new_pressure, 900, 1100)),
        "humidity": float(new_humidity),
        "wind_speed": float(np.clip(new_wind, 0, 40)),
        "rainfall": float(np.clip(new_rain, 0, 100)),
        "wind_direction": float(new_wind_dir),
        "solar_radiation": float(new_solar),
        "battery_voltage": float(new_battery),
        "actual_anomaly": 0,
        "anomaly_type": "none",
    }


def inject_live_anomaly(observation: dict, sensor: str, anomaly_type: str, rng: np.random.Generator) -> dict:
    """Apply an anomaly to a freshly generated live observation (used by the
    UI's 'Inject Anomaly' and 'SIH Demo Mode' controls)."""
    row = pd.Series(observation)
    corrupted = _apply_anomaly(row, anomaly_type, sensor, rng)
    return corrupted.to_dict()
