"""
pages/dashboard.py
===================
Renders the main "Network Overview" dashboard: top anomaly + network cards,
station summary + correction, multivariate chart, explanation log + map,
root cause + sensor condition, and the health timeline -- matching the
layout described in the project spec (section 32).
"""

import pandas as pd
import streamlit as st

from components import cards, charts, map as map_component
from services import monitoring


def render(simulation_state, stations_df, selected_station: str, settings: dict):
    st.markdown('<div class="wg-hero-title">Network Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="wg-hero-sub">Real-time AI-powered Automatic Weather Station Monitoring</div>', unsafe_allow_html=True)

    latest = simulation_state.get_latest(selected_station)
    if latest is None:
        st.info("No detections yet for this station. Use the controls below to generate a reading.")
        return

    detection = latest["detection"]
    network_health = monitoring.get_network_health(simulation_state.station_status)

    col1, col2 = st.columns(2)
    with col1:
        cards.anomaly_status_card(detection)
    with col2:
        cards.network_metrics_card(network_health)

    station_row = stations_df[stations_df["station_id"] == selected_station].iloc[0]
    status_label = simulation_state.station_status.loc[
        simulation_state.station_status["station_id"] == selected_station, "status"
    ].iloc[0]

    col3, col4 = st.columns(2)
    with col3:
        cards.station_summary_card(station_row, detection["observation"], status_label)
    with col4:
        if settings.get("automatic_correction", True):
            cards.correction_card(latest["correction"], detection["affected_sensor"])
        else:
            st.markdown(
                '<div class="wg-card"><div class="wg-card-eyebrow">VALUE CORRECTION</div>'
                '<div class="wg-card-title">Sensor Data Correction</div>'
                '<div class="wg-sub">Automatic correction is disabled in Settings.</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="wg-card">', unsafe_allow_html=True)
    st.markdown('<div class="wg-card-eyebrow">LIVE SENSOR DATA</div>', unsafe_allow_html=True)
    header_cols = st.columns([3, 1])
    with header_cols[0]:
        st.markdown('<div class="wg-card-title">Multivariate Sensor Analysis</div>', unsafe_allow_html=True)
    with header_cols[1]:
        if detection["anomaly"]:
            st.markdown('<div style="text-align:right;color:#dc2626;font-weight:700;">ANOMALY DETECTED</div>', unsafe_allow_html=True)
    history = simulation_state.history.get(selected_station, pd.DataFrame())
    if not history.empty:
        fig = charts.multivariate_sensor_chart(history.tail(30))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col5, col6 = st.columns(2)
    with col5:
        cards.explanation_log_card(latest["explanation"])
    with col6:
        st.markdown('<div class="wg-card">', unsafe_allow_html=True)
        header_cols2 = st.columns([3, 1])
        with header_cols2[0]:
            st.markdown('<div class="wg-card-eyebrow">NETWORK STATION MAP</div><div class="wg-card-title">Weather Station Locations</div>', unsafe_allow_html=True)
        with header_cols2[1]:
            st.markdown('<div style="text-align:right;color:#16a34a;font-weight:700;">● LIVE</div>', unsafe_allow_html=True)
        latest_readings = {
            sid: simulation_state.get_latest(sid)["detection"]["observation"]
            for sid in stations_df["station_id"]
            if simulation_state.get_latest(sid) is not None
        }
        map_component.render_station_map(stations_df, simulation_state.station_status, latest_readings)
        st.markdown(
            '<div style="margin-top:6px;"><span class="wg-station-dot" style="background:#22c55e;"></span>Healthy '
            '&nbsp;&nbsp;<span class="wg-station-dot" style="background:#f59e0b;"></span>Warning '
            '&nbsp;&nbsp;<span class="wg-station-dot" style="background:#ef4444;"></span>Critical</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    col7, col8 = st.columns(2)
    with col7:
        cards.root_cause_card(latest["root_cause"])
        cards.maintenance_recommendation_card(latest["recommendation"])
    with col8:
        if settings.get("predictive_maintenance", True):
            cards.sensor_condition_card(latest["sensor_health"])
        else:
            st.markdown(
                '<div class="wg-card"><div class="wg-card-eyebrow">PREDICTIVE MAINTENANCE</div>'
                '<div class="wg-card-title">Sensor Condition</div>'
                '<div class="wg-sub">Predictive maintenance is disabled in Settings.</div></div>',
                unsafe_allow_html=True,
            )

    if settings.get("predictive_maintenance", True):
        st.markdown('<div class="wg-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="wg-card-eyebrow">SENSOR HEALTH TIMELINE</div>'
            f'<div class="wg-card-title">{detection["affected_sensor"].replace("_"," ").title()} Sensor Condition</div>'
            '<div class="wg-sub">Sensor health degradation monitored over time.</div>',
            unsafe_allow_html=True,
        )
        traj = simulation_state.get_health_trajectory(selected_station, detection["affected_sensor"])
        fig2 = charts.sensor_health_timeline_chart(traj["trajectory"])
        st.plotly_chart(fig2, use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Initial Health", f"{traj['initial_health']}%")
        c2.metric("Current Health", f"{traj['current_health']}%")
        c3.metric("Health Loss", f"{traj['health_loss']}%")
        c4.metric("Status", traj["status"])
        st.markdown("</div>", unsafe_allow_html=True)
