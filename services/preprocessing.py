"""
services/preprocessing.py
==========================
Feature engineering and preprocessing for the anomaly detection pipeline.

Leakage safety
--------------
- All rolling statistics are computed PER STATION, sorted chronologically,
  using trailing (past + current) windows only -- never centered, never
  looking forward.
- The imputer/scaler pipeline built here is fit ONLY on the caller-supplied
  training slice (see services/training.py). This module never decides
  what is "train" vs "test"; it only transforms whatever DataFrame it is
  given, using whichever fitted preprocessor is passed in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

import config

RAW_SENSOR_COLUMNS = config.FEATURE_SENSORS

ENGINEERED_FEATURE_COLUMNS = [
    "temperature_delta",
    "pressure_delta",
    "humidity_delta",
    "wind_speed_delta",
    "temperature_rolling_mean",
    "temperature_rolling_std",
    "pressure_rolling_mean",
    "pressure_rolling_std",
    "humidity_rolling_mean",
    "humidity_rolling_std",
    "temperature_deviation_from_baseline",
    "humidity_temperature_ratio",
]

ALL_FEATURE_COLUMNS = RAW_SENSOR_COLUMNS + ENGINEERED_FEATURE_COLUMNS


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add engineered features to a sensor DataFrame.

    Must be called on a DataFrame that already contains every historical
    row that should inform each station's rolling statistics (i.e. call
    this BEFORE splitting off a small live batch, or make sure the batch
    includes enough trailing history). Rolling windows only use past and
    current values within the same station -- never future rows.
    """
    df = df.sort_values(["station_id", "timestamp"]).copy()
    out_frames = []

    for station_id, g in df.groupby("station_id", sort=False):
        g = g.sort_values("timestamp").copy()

        g["temperature_delta"] = g["temperature"].diff().fillna(0.0)
        g["pressure_delta"] = g["pressure"].diff().fillna(0.0)
        g["humidity_delta"] = g["humidity"].diff().fillna(0.0)
        g["wind_speed_delta"] = g["wind_speed"].diff().fillna(0.0)

        win = config.ROLLING_WINDOW
        g["temperature_rolling_mean"] = (
            g["temperature"].rolling(window=win, min_periods=1).mean()
        )
        g["temperature_rolling_std"] = (
            g["temperature"].rolling(window=win, min_periods=1).std().fillna(0.0)
        )
        g["pressure_rolling_mean"] = g["pressure"].rolling(window=win, min_periods=1).mean()
        g["pressure_rolling_std"] = (
            g["pressure"].rolling(window=win, min_periods=1).std().fillna(0.0)
        )
        g["humidity_rolling_mean"] = g["humidity"].rolling(window=win, min_periods=1).mean()
        g["humidity_rolling_std"] = (
            g["humidity"].rolling(window=win, min_periods=1).std().fillna(0.0)
        )

        # Station baseline = expanding mean up to (and including) the current
        # row -- again, strictly backward-looking.
        baseline = g["temperature"].expanding(min_periods=1).mean()
        g["temperature_deviation_from_baseline"] = g["temperature"] - baseline

        g["humidity_temperature_ratio"] = g["humidity"] / g["temperature"].replace(0, np.nan)
        g["humidity_temperature_ratio"] = g["humidity_temperature_ratio"].replace(
            [np.inf, -np.inf], np.nan
        )

        out_frames.append(g)

    result = pd.concat(out_frames, ignore_index=True)
    result = result.sort_values("timestamp").reset_index(drop=True)
    return result


def get_feature_columns() -> list[str]:
    return list(ALL_FEATURE_COLUMNS)


def build_preprocessing_pipeline() -> Pipeline:
    """Imputation + robust scaling. Robust scaling is used because sensor
    anomalies (by definition) contain extreme outliers that would distort a
    standard mean/variance scaler."""
    numeric_features = ALL_FEATURE_COLUMNS
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[("numeric", numeric_pipeline, numeric_features)],
        remainder="drop",
    )
    return preprocessor


def fit_preprocessor(train_df: pd.DataFrame) -> ColumnTransformer:
    """Fit preprocessing ONLY on the training slice. Callers must never
    pass test data here."""
    preprocessor = build_preprocessing_pipeline()
    preprocessor.fit(train_df[ALL_FEATURE_COLUMNS])
    return preprocessor


def transform(preprocessor: ColumnTransformer, df: pd.DataFrame) -> np.ndarray:
    """Transform any DataFrame (train or test or a single live row) using an
    already-fitted preprocessor."""
    return preprocessor.transform(df[ALL_FEATURE_COLUMNS])
