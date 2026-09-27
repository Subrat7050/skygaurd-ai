"""
utils/helpers.py
=================
Small formatting / safety helpers shared across the app.
"""

from __future__ import annotations

import pandas as pd


def safe_round(value, digits=1, default="--"):
    try:
        if value is None or pd.isna(value):
            return default
        return round(float(value), digits)
    except (TypeError, ValueError):
        return default


def fmt_unit(value, unit: str, digits=1, default="--"):
    v = safe_round(value, digits, default=None)
    if v is None:
        return default
    return f"{v}{unit}"


def trend_arrow(current, previous):
    if current is None or previous is None or pd.isna(current) or pd.isna(previous):
        return ""
    if current > previous:
        return "↑"
    if current < previous:
        return "↓"
    return "→"


def pct_change(current, previous):
    if previous in (None, 0) or current is None or pd.isna(previous) or pd.isna(current):
        return None
    try:
        return round((current - previous) / abs(previous) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return None
