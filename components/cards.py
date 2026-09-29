"""
components/cards.py
====================
Reusable card renderers for the dashboard. Every value displayed here is
passed in from the caller (app.py / pages/*) -- nothing is computed or
hardcoded in this module.
"""

import html

import streamlit as st

from components import styles
from utils import helpers


def escape_html(value):
    return html.escape(str(value), quote=True)


def anomaly_status_card(detection: dict):
    badge_class = styles.severity_badge_class(detection["severity"])
    badge_text = "DETECTED" if detection["anomaly"] else "NORMAL"
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">ANOMALY STATUS</div>
                    <div class="wg-card-title">Weather Anomaly Detection</div>
                </div>
                <span class="wg-badge {badge_class}">{badge_text}</span>
            </div>
            <div style="display:flex;gap:36px;align-items:flex-start;margin-top:6px;">
                <div>
                    <div class="wg-big-number" style="color:{'#dc2626' if detection['anomaly'] else '#16a34a'};">{detection['anomaly_score']}</div>
                    <div class="wg-sub">Anomaly Score</div>
                </div>
                <div>
                    <div class="wg-sub">Detection Confidence</div>
                    <div style="font-size:18px;font-weight:700;">{detection['confidence']}%</div>
                    <div class="wg-sub" style="margin-top:6px;">Severity: <b style="color:{'#dc2626' if detection['severity'] in ('HIGH','CRITICAL') else '#0f172a'};">{detection['severity']}</b></div>
                    <div class="wg-sub">Station: <b>{detection['station_id']}</b></div>
                </div>
            </div>
            <div class="wg-sub" style="margin-top:10px;">{detection['timestamp']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def network_metrics_card(network_health: dict):
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">NETWORK HEALTH</div>
                    <div class="wg-card-title">Station Network Metrics</div>
                </div>
                <div class="wg-big-number" style="font-size:26px;">{network_health['network_health_pct']}%</div>
            </div>
            <div style="background:#e2e8f0;border-radius:999px;height:8px;margin:10px 0 16px 0;overflow:hidden;">
                <div style="background:#16a34a;height:8px;width:{network_health['network_health_pct']}%;"></div>
            </div>
            <div style="display:flex;gap:28px;">
                <div><span class="wg-station-dot" style="background:#22c55e;"></span><b>{network_health['healthy']}</b><div class="wg-sub">Healthy</div></div>
                <div><span class="wg-station-dot" style="background:#f59e0b;"></span><b>{network_health['warning']}</b><div class="wg-sub">Warning</div></div>
                <div><span class="wg-station-dot" style="background:#ef4444;"></span><b>{network_health['critical']}</b><div class="wg-sub">Critical</div></div>
                <div><b>{network_health['total']}</b><div class="wg-sub">Total Stations</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def station_summary_card(station_row, observation: dict, status: str):
    badge_class = styles.severity_badge_class({"HEALTHY": "NORMAL", "WARNING": "WARNING", "CRITICAL": "CRITICAL"}.get(status, "NORMAL"))
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">STATION SUMMARY</div>
                    <div class="wg-card-title">{station_row['station_id']}</div>
                    <div class="wg-sub" style="margin-top:-8px;">{station_row['station_name']}</div>
                </div>
                <span class="wg-badge {badge_class}">{status}</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:14px;">
                <div><div class="wg-sub">Temperature</div><b>{helpers.fmt_unit(observation.get('temperature'), '°C')}</b></div>
                <div><div class="wg-sub">Pressure</div><b>{helpers.fmt_unit(observation.get('pressure'), ' hPa')}</b></div>
                <div><div class="wg-sub">Humidity</div><b>{helpers.fmt_unit(observation.get('humidity'), '%')}</b></div>
                <div><div class="wg-sub">Wind Speed</div><b>{helpers.fmt_unit(observation.get('wind_speed'), ' m/s')}</b></div>
                <div><div class="wg-sub">Rainfall</div><b>{helpers.fmt_unit(observation.get('rainfall'), ' mm')}</b></div>
                <div><div class="wg-sub">Battery</div><b>{helpers.fmt_unit(observation.get('battery_voltage'), ' V')}</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def correction_card(correction: dict, sensor: str):
    if not correction.get("correction_applied"):
        st.markdown(
            """
            <div class="wg-card">
                <div class="wg-card-eyebrow">VALUE CORRECTION</div>
                <div class="wg-card-title">Sensor Data Correction</div>
                <div class="wg-sub">No correction needed -- latest reading is within expected range.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">VALUE CORRECTION</div>
                    <div class="wg-card-title">Sensor Data Correction</div>
                </div>
                <span class="wg-badge wg-badge-healthy">Corrected</span>
            </div>
            <div style="display:flex;align-items:center;gap:24px;margin-top:8px;">
                <div>
                    <div class="wg-sub">Original Value</div>
                    <div style="font-size:22px;font-weight:800;color:#dc2626;">{correction['original_value']}</div>
                </div>
                <div style="font-size:20px;color:#94a3b8;">→</div>
                <div>
                    <div class="wg-sub">Corrected Value</div>
                    <div style="font-size:22px;font-weight:800;color:#16a34a;">{correction['corrected_value']}</div>
                </div>
            </div>
            <div style="margin-top:12px;background:#f8fafc;border-radius:8px;padding:10px 14px;">
                <div class="wg-sub"><b>Sensor:</b> {sensor.replace('_',' ').title()}</div>
                <div class="wg-sub"><b>Reason:</b> {correction['reason']}</div>
                <div class="wg-sub"><b>Correction Confidence:</b> {correction['correction_confidence']}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def explanation_log_card(explanation: dict):
    items_html = "".join(
        f"""
        <div class="wg-explanation-item">
            <div class="wg-explanation-num">{i+1}</div>
            <div style="padding-top:2px;">{escape_html(text)}</div>
        </div>
        """
        for i, text in enumerate(explanation["log"])
    )
    st.markdown(
        f"""
        <div class="wg-card">
            <div class="wg-card-eyebrow">EXPLAINABLE AI</div>
            <div class="wg-card-title">AI Explanation Log</div>
            {items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "AI explanation is based on sensor trends and nearby station comparison."
    )
    if explanation.get("contributions"):
        st.markdown('<div class="wg-card"><div class="wg-card-eyebrow">DETECTION FACTORS</div><div class="wg-card-title">Anomaly Contribution Indicators</div>', unsafe_allow_html=True)
        for label, value in explanation["contributions"].items():
            st.progress(min(max(value / 100, 0.0), 1.0), text=f"{label} — {value:.0f}%")
        st.markdown("</div>", unsafe_allow_html=True)


def root_cause_card(cause: dict):
    badge_class = "wg-badge-critical" if cause["confidence"] > 80 else "wg-badge-high"
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="wg-card-eyebrow">ROOT-CAUSE &amp; PREDICTION</div>
                    <div class="wg-card-title">Root Cause Classification</div>
                </div>
                <span class="wg-badge {badge_class}">{cause['confidence']}%</span>
            </div>
            <div class="wg-sub">Confidence</div>
            <div style="background:#e2e8f0;border-radius:999px;height:8px;margin:4px 0 14px 0;overflow:hidden;">
                <div style="background:#16a34a;height:8px;width:{cause['confidence']}%;"></div>
            </div>
            <div class="wg-sub">Probable Cause</div>
            <div style="font-size:16px;font-weight:700;margin-bottom:4px;">{cause['probable_cause']}</div>
            <div class="wg-sub">Affected Sensor: <b>{cause['affected_sensor']}</b></div>
            <div style="margin-top:12px;background:#fff7ed;border-radius:8px;padding:10px 14px;">
                <div style="font-weight:700;font-size:13px;">🛡️ Recommended Action</div>
                <div class="wg-sub">{cause['recommended_action']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sensor_condition_card(health: dict):
    badge_class = styles.health_badge_class(health["status"])
    descriptions = {
        "HEALTHY": "Sensor performing within normal parameters.",
        "MONITORING": "Minor deviations observed; keep monitoring.",
        "DEGRADING": "Sensor performance declining.",
        "CRITICAL": "Sensor requires immediate attention.",
    }
    st.markdown(
        f"""
        <div class="wg-card">
            <div class="wg-card-eyebrow">PREDICTIVE MAINTENANCE</div>
            <div class="wg-card-title">Sensor Condition</div>
            <div style="display:flex;align-items:center;gap:20px;margin-top:6px;">
                <div style="width:90px;height:90px;border-radius:50%;background:#f1f5f9;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                    <div style="font-size:22px;font-weight:800;">{health['current_health']}%</div>
                    <div style="font-size:10px;color:#94a3b8;">Health</div>
                </div>
                <div>
                    <span class="wg-badge {badge_class}">{health['status']}</span>
                    <div class="wg-sub" style="margin-top:6px;">{descriptions.get(health['status'], '')}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def maintenance_recommendation_card(recommendation: str):
    st.markdown(
        f"""
        <div class="wg-card">
            <div style="font-weight:700;font-size:13px;">Maintenance Recommendation</div>
            <div class="wg-sub" style="margin-top:4px;">{recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
