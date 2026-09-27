"""
pages/settings.py
==================
Application settings. Values are stored in st.session_state["settings"]
and read by the dashboard / detection pipeline where noted -- they never
trigger a model retrain.
"""

import streamlit as st
import config


def _sync_simulation_setting():
    st.session_state["simulation_on"] = st.session_state[
        "settings_simulation_on"
    ]


def _sync_refresh_interval_setting():
    st.session_state["refresh_interval"] = st.session_state[
        "settings_refresh_interval"
    ]


def render():
    st.markdown(
        '<div class="wg-hero-title">Settings</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="wg-hero-sub">Tune detection sensitivity and toggle system features</div>',
        unsafe_allow_html=True
    )

    # Make sure settings exists
    if "settings" not in st.session_state:
        st.session_state["settings"] = {
            "sensitivity": "Medium",
            "detection_window": "30 minutes",
            "automatic_correction": True,
            "predictive_maintenance": True,
        }

    settings = st.session_state["settings"]

    # ---------------------------------------------------------
    # DETECTION
    # ---------------------------------------------------------

    st.markdown(
        '<div class="wg-card"><div class="wg-card-title">Detection</div>',
        unsafe_allow_html=True
    )

    sensitivity = st.select_slider(
        "Anomaly Sensitivity",
        options=["Low", "Medium", "High"],
        value=settings.get("sensitivity", "Medium"),
        help="Low widens the tolerance before a reading is flagged; High narrows it.",
    )

    detection_window = st.select_slider(
        "Detection Window",
        options=["10 minutes", "30 minutes", "60 minutes"],
        value=settings.get("detection_window", "30 minutes"),
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # FEATURES
    # ---------------------------------------------------------

    st.markdown(
        '<div class="wg-card"><div class="wg-card-title">Features</div>',
        unsafe_allow_html=True
    )

    automatic_correction = st.toggle(
        "Automatic Correction",
        value=settings.get("automatic_correction", True),
        key="automatic_correction_toggle",
    )

    predictive_maintenance = st.toggle(
        "Predictive Maintenance",
        value=settings.get("predictive_maintenance", True),
        key="predictive_maintenance_toggle",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # SIMULATION
    # ---------------------------------------------------------

    st.markdown(
        '<div class="wg-card"><div class="wg-card-title">Simulation</div>',
        unsafe_allow_html=True
    )

    if "settings_simulation_on" not in st.session_state:
        st.session_state["settings_simulation_on"] = st.session_state.get(
            "simulation_on",
            False,
        )

    if "settings_refresh_interval" not in st.session_state:
        st.session_state["settings_refresh_interval"] = st.session_state.get(
            "refresh_interval",
            config.DEFAULT_REFRESH_INTERVAL,
        )

    simulation_on = st.toggle(
        "Simulation",
        key="settings_simulation_on",
        on_change=_sync_simulation_setting,
    )

    refresh_interval = st.select_slider(
        "Refresh Interval (seconds)",
        options=config.REFRESH_INTERVAL_OPTIONS,
        key="settings_refresh_interval",
        on_change=_sync_refresh_interval_setting,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # SAVE SETTINGS
    # ---------------------------------------------------------

    st.session_state["settings"] = {
        "sensitivity": sensitivity,
        "detection_window": detection_window,
        "automatic_correction": automatic_correction,
        "predictive_maintenance": predictive_maintenance,
    }
