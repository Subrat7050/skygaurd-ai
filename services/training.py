"""
services/training.py
=====================
Chronological train/test split, Isolation Forest training, model
persistence, and evaluation on the unseen test set.

Golden rule enforced throughout this file: the test set is NEVER touched
until evaluate_model() is called on an already-trained model.
"""

from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

import config
from services import preprocessing as pp
from utils import metrics as metrics_util


@dataclass
class TrainedArtifacts:
    model: IsolationForest
    preprocessor: object
    feature_columns: list
    train_period: tuple
    test_period: tuple
    n_train: int
    n_test: int


def chronological_split(df: pd.DataFrame, train_fraction: float = config.TRAIN_FRACTION):
    """
    Sort by timestamp (global, across all stations) and split so the
    earliest `train_fraction` of rows form the training set and the most
    recent remainder forms the test set. NO shuffling.
    """
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(df_sorted) * train_fraction)
    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()
    return train_df, test_df


def train_anomaly_model(train_df: pd.DataFrame) -> tuple:
    """
    1. Validate + sort training data
    2. Feature engineering (already expected to be present -- see note)
    3. Fit preprocessing on TRAIN ONLY
    4. Train Isolation Forest on TRAIN ONLY
    5. Persist model + preprocessor
    6. Return trained objects

    NOTE: `train_df` must already contain the engineered feature columns
    (call services.preprocessing.build_features on the FULL dataset before
    splitting, then pass the train slice here -- this keeps rolling
    statistics correct without leaking, since features for the train slice
    only ever depend on rows at or before their own timestamp).
    """
    if train_df.empty:
        raise ValueError("Training data is empty.")

    train_df = train_df.sort_values("timestamp").reset_index(drop=True)

    preprocessor = pp.fit_preprocessor(train_df)
    X_train = pp.transform(preprocessor, train_df)

    model = IsolationForest(**config.ISOLATION_FOREST_PARAMS)
    model.fit(X_train)

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, config.ISOLATION_FOREST_FILE)
    joblib.dump(preprocessor, config.PREPROCESSOR_FILE)

    metadata = {
        "feature_columns": pp.get_feature_columns(),
        "train_period": (str(train_df["timestamp"].min()), str(train_df["timestamp"].max())),
        "n_train": len(train_df),
    }
    joblib.dump(metadata, config.METADATA_FILE)

    return model, preprocessor, metadata


def load_trained_artifacts():
    """Load persisted model/preprocessor/metadata from disk, or None if any
    are missing."""
    if not (
        config.ISOLATION_FOREST_FILE.exists()
        and config.PREPROCESSOR_FILE.exists()
        and config.METADATA_FILE.exists()
    ):
        return None
    model = joblib.load(config.ISOLATION_FOREST_FILE)
    preprocessor = joblib.load(config.PREPROCESSOR_FILE)
    metadata = joblib.load(config.METADATA_FILE)
    return model, preprocessor, metadata


def evaluate_model(model, preprocessor, test_df: pd.DataFrame) -> dict:
    """
    Evaluate an already-trained model on the held-out chronological test
    set. This function must NEVER call .fit() on anything.
    """
    if test_df.empty:
        raise ValueError("Test data is empty.")

    test_df = test_df.sort_values("timestamp").reset_index(drop=True)

    X_test = pp.transform(preprocessor, test_df)

    raw_scores = model.decision_function(X_test)  # higher = more normal
    predictions = model.predict(X_test)  # 1 = normal, -1 = anomaly
    y_pred = np.where(predictions == -1, 1, 0)  # 1 = anomaly, matches ground truth convention
    y_true = test_df["actual_anomaly"].astype(int).values

    report = metrics_util.compute_classification_metrics(y_true, y_pred)
    confusion = metrics_util.compute_confusion_matrix(y_true, y_pred)

    per_type_rows = []
    for anomaly_type in sorted(test_df["anomaly_type"].unique()):
        if anomaly_type == "none":
            continue
        mask = test_df["anomaly_type"] == anomaly_type
        if mask.sum() == 0:
            continue
        detected = (y_pred[mask.values] == 1).sum()
        per_type_rows.append(
            {
                "anomaly_type": anomaly_type,
                "occurrences": int(mask.sum()),
                "detected": int(detected),
                "detection_rate": round(100.0 * detected / mask.sum(), 1),
            }
        )

    return {
        "metrics": report,
        "confusion_matrix": confusion,
        "per_type": per_type_rows,
        "n_test": len(test_df),
        "test_period": (str(test_df["timestamp"].min()), str(test_df["timestamp"].max())),
        "raw_scores": raw_scores,
        "predictions": y_pred,
        "ground_truth": y_true,
    }


def train_and_evaluate_full_pipeline(df_with_features: pd.DataFrame) -> dict:
    """Convenience wrapper used by the app: split -> train -> evaluate."""
    train_df, test_df = chronological_split(df_with_features)
    model, preprocessor, metadata = train_anomaly_model(train_df)
    evaluation = evaluate_model(model, preprocessor, test_df)
    evaluation["train_period"] = metadata["train_period"]
    evaluation["n_train"] = metadata["n_train"]
    return {
        "model": model,
        "preprocessor": preprocessor,
        "metadata": metadata,
        "evaluation": evaluation,
        "train_df": train_df,
        "test_df": test_df,
    }
