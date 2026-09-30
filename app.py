"""
app.py
======
SkyGaurd AI -- AI-Powered Automatic Weather Station Monitoring.

This file only wires things together:

- Data/model loading
- Session-state bootstrapping
- Navigation
- Live simulation
- Page routing

All ML and business logic lives in models/ and services/.
"""

from __future__ import annotations

import time
from importlib import import_module

import streamlit as st

import config
from components import injection_panel, sidebar, styles
from pages import analytics as analytics_page
from pages import dashboard as dashboard_page
from pages import settings as settings_page
from pages import station_details as station_details_page
from services import data_generator, preprocessing, simulation, training


# ===========================================================================
# OPTIONAL STREAMLIT AUTOREFRESH DEPENDENCY
# ===========================================================================

try:
    st_autorefresh = import_module(
        "streamlit_autorefresh"
    ).st_autorefresh
except ImportError:
    st_autorefresh = None


# ===========================================================================
# PAGE CONFIGURATION
# ===========================================================================

st.set_page_config(
    page_title="SkyGaurd AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject_custom_css()


# ===========================================================================
# CACHED DATA + MODEL LOADING
# ===========================================================================

@st.cache_data(
    show_spinner="Generating simulated AWS network history..."
)
def load_feature_dataset():
    """
    Generate historical data and build model features.
    """
    raw = data_generator.generate_historical_dataset()
    featured = preprocessing.build_features(raw)

    return featured


@st.cache_resource(
    show_spinner="Training / loading Isolation Forest model..."
)
def load_or_train_pipeline(_feat_df):
    """
    Load an existing trained pipeline when available.

    Otherwise train a new pipeline.
    """

    existing = training.load_trained_artifacts()

    if existing is not None:
        model, preprocessor, metadata = existing

        if metadata.get("isolation_forest_params") == config.ISOLATION_FOREST_PARAMS:
            train_df, test_df = training.chronological_split(
                _feat_df
            )

            evaluation = training.evaluate_model(
                model,
                preprocessor,
                test_df,
            )

            evaluation["train_period"] = metadata["train_period"]
            evaluation["n_train"] = metadata["n_train"]

            return {
                "model": model,
                "preprocessor": preprocessor,
                "metadata": metadata,
                "evaluation": evaluation,
            }

    result = training.train_and_evaluate_full_pipeline(
        _feat_df
    )

    return {
        "model": result["model"],
        "preprocessor": result["preprocessor"],
        "metadata": result["metadata"],
        "evaluation": result["evaluation"],
    }


@st.cache_data(show_spinner=False)
def load_stations():
    """
    Load available weather stations.
    """
    return data_generator.get_stations()


# ===========================================================================
# LOAD APPLICATION DATA
# ===========================================================================

feat_df = load_feature_dataset()

pipeline = load_or_train_pipeline(feat_df)

stations_df = load_stations()


# ===========================================================================
# SESSION STATE BOOTSTRAPPING
# ===========================================================================

# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------

if "settings" not in st.session_state:
    st.session_state["settings"] = {
        "sensitivity": "Medium",
        "detection_window": "30 minutes",
        "automatic_correction": True,
        "predictive_maintenance": True,
    }


# ---------------------------------------------------------------------------
# Simulation state
# ---------------------------------------------------------------------------

if "simulation_state" not in st.session_state:

    sim_state = simulation.SimulationState(
        stations=stations_df,
        model=pipeline["model"],
        preprocessor=pipeline["preprocessor"],
    )

    # Seed historical data.
    sim_state.seed_history(feat_df)

    # Warm start:
    # Give every station one live baseline reading so that
    # the dashboard has real data immediately.
    for sid in stations_df["station_id"]:
        sim_state.step(sid)

    st.session_state["simulation_state"] = sim_state


sim_state = st.session_state["simulation_state"]


# ---------------------------------------------------------------------------
# Selected station
# ---------------------------------------------------------------------------

if "selected_station" not in st.session_state:

    st.session_state["selected_station"] = (
        stations_df.iloc[0]["station_id"]
    )


# ===========================================================================
# SIDEBAR + NAVIGATION
# ===========================================================================
#
# IMPORTANT:
#
# Navigation is handled entirely by components/sidebar.py.
#
# The SIH Demo Mode stores a request in:
#
#     st.session_state["pending_nav_page"]
#
# sidebar.py consumes that request BEFORE creating the widget:
#
#     key="nav_page"
#
# We deliberately DO NOT do this in app.py:
#
#     st.session_state["nav_page"] = "Dashboard"
#
# because that can cause:
#
#     StreamlitWidgetAlreadyInstantiatedError
#
# ===========================================================================

page, selected_station, sim_on, refresh_interval = (
    sidebar.render_sidebar(
        sim_state.station_status,
        st.session_state["selected_station"],
    )
)


# ---------------------------------------------------------------------------
# Keep selected station synchronized with sidebar selection.
# ---------------------------------------------------------------------------

st.session_state["selected_station"] = selected_station


# ===========================================================================
# LIVE SIMULATION TICKING
# ===========================================================================
#
# Time-gated so the app behaves consistently whether or not
# streamlit-autorefresh is installed.
# ===========================================================================

if sim_on:

    # -----------------------------------------------------------------------
    # Automatic browser refresh
    # -----------------------------------------------------------------------

    if st_autorefresh is not None:

        st_autorefresh(
            interval=refresh_interval * 1000,
            key="sim_autorefresh",
        )

    # -----------------------------------------------------------------------
    # Simulation tick
    # -----------------------------------------------------------------------

    now = time.time()

    last_tick = st.session_state.get(
        "last_sim_tick",
        0.0,
    )

    if now - last_tick >= refresh_interval:

        for sid in stations_df["station_id"]:
            sim_state.step(sid)

        st.session_state["last_sim_tick"] = now


# ===========================================================================
# TOP BAR
# ===========================================================================

top_col1, top_col2 = st.columns([5, 1])


# ---------------------------------------------------------------------------
# Application title
# ---------------------------------------------------------------------------

with top_col1:

    st.markdown(
        """
        <div style="
            display:flex;
            align-items:baseline;
            gap:10px;
        ">
            <span style="
                font-size:22px;
                font-weight:800;
                color:#0f172a;
            ">
                SkyGaurd AI
            </span>
        </div>

        <div style="
            color:#64748b;
            font-size:13px;
            margin-bottom:6px;
        ">
            AI-Powered Weather Monitoring System
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Top-right icons
# ---------------------------------------------------------------------------

with top_col2:

    st.markdown(
        """
        <div style="
            text-align:right;
            padding-top:10px;
        ">
            🔔&nbsp;&nbsp;⚙️&nbsp;&nbsp;👤
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE ROUTING
# ===========================================================================

if page == "Dashboard":

    # -----------------------------------------------------------------------
    # Anomaly injection controls
    # -----------------------------------------------------------------------

    injection_panel.render(
        sim_state,
        stations_df,
        selected_station,
    )

    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------

    dashboard_page.render(
        sim_state,
        stations_df,
        selected_station,
        st.session_state["settings"],
    )


elif page == "Analytics":

    analytics_page.render(
        pipeline["evaluation"],
        pipeline["metadata"],
        sim_state.detection_log,
    )


elif page == "Station Details":

    station_details_page.render(
        sim_state,
        stations_df,
        selected_station,
    )


elif page == "Settings":

    settings_page.render()


# ===========================================================================
# FOOTER
# ===========================================================================

st.markdown(
    """
    <div style="
        margin-top:24px;
        color:#94a3b8;
        font-size:12px;
    ">
        SkyGaurd AI Monitoring System
        &nbsp;•&nbsp;
        Streamlit Prototype
        &nbsp;•&nbsp;
        Live Simulation
    </div>
    """,
    unsafe_allow_html=True,
)
