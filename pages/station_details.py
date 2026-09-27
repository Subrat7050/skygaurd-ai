"""
pages/station_details.py
=========================
Detailed view for a single selected station: identity, live sensor cards
with trend arrows, and its recent multivariate history.
"""

import streamlit as st

from components import charts, styles
from utils import helpers

SENSOR_DISPLAY = [
    ("temperature", "Temperature", "°C"),
    ("pressure", "Pressure", " hPa"),
    ("humidity", "Humidity", "%"),
    ("wind_speed", "Wind Speed", " m/s"),
    ("rainfall", "Rainfall", " mm"),
    ("wind_direction", "Wind Direction", "°"),
    ("solar_radiation", "Solar Radiation", " W/m²"),
    ("battery_voltage", "Battery Voltage", " V"),
]


def render(simulation_state, stations_df, selected_station: str):
    station_row = stations_df[stations_df["station_id"] == selected_station].iloc[0]
    status_row = simulation_state.station_status[
        simulation_state.station_status["station_id"] == selected_station
    ].iloc[0]

    badge_class = styles.severity_badge_class(
        {"HEALTHY": "NORMAL", "WARNING": "WARNING", "CRITICAL": "CRITICAL"}.get(status_row["status"], "NORMAL")
    )

    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">STATION DETAILS</div>
                    <div class="wg-card-title" style="font-size:22px;">{station_row['station_id']} — {station_row['station_name']}</div>
                    <div class="wg-sub">{station_row['city']}, {station_row['state']} &nbsp;•&nbsp; {station_row['latitude']:.4f}, {station_row['longitude']:.4f}</div>
                </div>
                <span class="wg-badge {badge_class}">{status_row['status']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    history = simulation_state.history.get(selected_station)
    if history is None or history.empty:
        st.info("No data available yet for this station.")
        return

    current = history.iloc[-1]
    previous = history.iloc[-2] if len(history) > 1 else current

    st.markdown('<div class="wg-card"><div class="wg-card-title">Sensor Readings</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (sensor, label, unit) in enumerate(SENSOR_DISPLAY):
        arrow = helpers.trend_arrow(current.get(sensor), previous.get(sensor))
        change = helpers.pct_change(current.get(sensor), previous.get(sensor))
        change_str = f"{arrow} {abs(change)}%" if change is not None else ""
        with cols[i % 4]:
            st.metric(label, helpers.fmt_unit(current.get(sensor), unit), change_str)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="wg-card"><div class="wg-card-title">Recent History</div>', unsafe_allow_html=True)
    fig = charts.multivariate_sensor_chart(history.tail(40))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    latest = simulation_state.get_latest(selected_station)
    if latest is not None:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Last Detection Result</div>', unsafe_allow_html=True)
        d = latest["detection"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Anomaly Score", d["anomaly_score"])
        c2.metric("Confidence", f"{d['confidence']}%")
        c3.metric("Severity", d["severity"])
        c4.metric("Affected Sensor", d["affected_sensor"].replace("_", " ").title())
        st.markdown("</div>", unsafe_allow_html=True)
