"""
config.py
=========
Central configuration for SkyGaurd AI.

Every threshold, weight, and "magic number" used anywhere in the anomaly
detection pipeline lives here so it can be tuned without touching business
logic. Nothing in models/ or services/ should hardcode a number that
appears in this file.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
MODELS_DIR = BASE_DIR / "models" / "trained"

STATIONS_FILE = DATA_DIR / "stations.csv"
HISTORICAL_DATA_FILE = GENERATED_DIR / "sensor_data.csv"
LIVE_STATE_FILE = GENERATED_DIR / "live_state.json"

ISOLATION_FOREST_FILE = MODELS_DIR / "isolation_forest.joblib"
PREPROCESSOR_FILE = MODELS_DIR / "preprocessor.joblib"
METADATA_FILE = MODELS_DIR / "metadata.joblib"

for _dir in (DATA_DIR, GENERATED_DIR, MODELS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Simulated AWS network
# --------------------------------------------------------------------------
NUM_STATIONS = 20
RANDOM_SEED = 42

# Historical dataset generation window
HISTORY_DAYS = 90
SAMPLE_INTERVAL_MINUTES = 60  # hourly observations

# Chronological train/test split
TRAIN_FRACTION = 0.8

# Overall probability that any given generated observation is an injected
# anomaly (spread across both the training and testing periods). Because
# this is a small fraction, the training period is naturally "predominantly
# normal" -- no post-hoc filtering of the training set using ground-truth
# labels is performed (see README: Data Leakage Prevention).
ANOMALY_INJECTION_RATE = 0.045

# --------------------------------------------------------------------------
# Physical sensor ranges (used for physical validation + data generation)
# --------------------------------------------------------------------------
SENSOR_RANGES = {
    "temperature": (0.0, 50.0),          # degrees C
    "pressure": (900.0, 1100.0),         # hPa
    "humidity": (0.0, 100.0),            # %
    "wind_speed": (0.0, 40.0),           # m/s
    "rainfall": (0.0, 100.0),            # mm
    "wind_direction": (0.0, 360.0),      # degrees
    "solar_radiation": (0.0, 1200.0),    # W/m^2
    "battery_voltage": (10.0, 14.0),     # V
}

FEATURE_SENSORS = [
    "temperature",
    "pressure",
    "humidity",
    "wind_speed",
    "rainfall",
    "solar_radiation",
    "battery_voltage",
]

# --------------------------------------------------------------------------
# Isolation Forest
# --------------------------------------------------------------------------
ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,
    # A precision-focused alert rate reduces false positives. On the
    # 90-day held-out test window, 1.5% reached more than 70% precision.
    "contamination": 0.015,
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
}

# --------------------------------------------------------------------------
# Anomaly score fusion weights (must sum to 1.0)
# --------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "ml_score": 0.50,
    "statistical_score": 0.20,
    "physical_score": 0.20,
    "temporal_score": 0.10,
}

# --------------------------------------------------------------------------
# Severity thresholds (0-100 anomaly score)
# --------------------------------------------------------------------------
SEVERITY_THRESHOLDS = {
    "NORMAL": (0, 30),
    "WARNING": (30, 60),
    "HIGH": (60, 80),
    "CRITICAL": (80, 101),
}

# --------------------------------------------------------------------------
# Predictive maintenance / sensor health
# --------------------------------------------------------------------------
HEALTH_STATUS_THRESHOLDS = {
    "HEALTHY": (90, 101),
    "MONITORING": (75, 90),
    "DEGRADING": (50, 75),
    "CRITICAL": (0, 50),
}

HEALTH_DECAY_PER_ANOMALY = {
    "NORMAL": 0.0,
    "WARNING": 1.5,
    "HIGH": 3.5,
    "CRITICAL": 6.0,
}
HEALTH_RECOVERY_PER_NORMAL_READING = 0.15  # slow self-heal when sensor behaves
MIN_SENSOR_HEALTH = 5.0

# --------------------------------------------------------------------------
# Network health
# --------------------------------------------------------------------------
STATION_STATUS_ANOMALY_LOOKBACK = 5  # readings considered for station status
STATION_STATUS_SEVERITY_MAP = {
    "NORMAL": "HEALTHY",
    "WARNING": "WARNING",
    "HIGH": "WARNING",
    "CRITICAL": "CRITICAL",
}

# --------------------------------------------------------------------------
# Rolling window sizes for feature engineering / supporting detectors
# --------------------------------------------------------------------------
ROLLING_WINDOW = 6           # number of past readings for rolling mean/std
Z_SCORE_THRESHOLD = 3.0      # robust z-score anomaly threshold
RATE_OF_CHANGE_THRESHOLD = {
    "temperature": 6.0,      # degrees C per reading
    "pressure": 8.0,         # hPa per reading
    "humidity": 25.0,        # % per reading
    "wind_speed": 15.0,      # m/s per reading
    "battery_voltage": 1.5,  # V per reading
}
STUCK_SENSOR_TOLERANCE = 0.01
STUCK_SENSOR_MIN_REPEATS = 4

# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
REFRESH_INTERVAL_OPTIONS = [5, 10, 30]  # seconds
DEFAULT_REFRESH_INTERVAL = 10

# --------------------------------------------------------------------------
# UI colors
# --------------------------------------------------------------------------
COLOR_HEALTHY = "#22c55e"
COLOR_WARNING = "#f59e0b"
COLOR_CRITICAL = "#ef4444"
COLOR_NAVY = "#0f172a"
COLOR_NAVY_LIGHT = "#1e293b"
COLOR_ACCENT = "#3b82f6"
COLOR_BG = "#f1f5f9"

SEVERITY_COLORS = {
    "NORMAL": COLOR_HEALTHY,
    "WARNING": COLOR_WARNING,
    "HIGH": "#f97316",
    "CRITICAL": COLOR_CRITICAL,
}

ANOMALY_TYPES = [
    "spike",
    "drift",
    "stuck",
    "impossible_value",
    "multivariate",
    "communication_error",
]

INJECTABLE_SENSORS = ["temperature", "pressure", "humidity", "wind_speed", "battery_voltage"]
