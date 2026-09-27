"""
pages/analytics.py
===================
Model performance, confusion matrix, and operational analytics -- all
computed from the trained model's actual evaluation on the unseen
chronological test set, plus the live detection log accumulated during
this session.
"""

import pandas as pd
import streamlit as st

from components import charts


def render(evaluation: dict, metadata: dict, detection_log: list):
    st.markdown('<div class="wg-hero-title">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="wg-hero-sub">Model performance and network-wide anomaly analytics</div>', unsafe_allow_html=True)

    metrics = evaluation["metrics"]

    st.markdown('<div class="wg-card"><div class="wg-card-eyebrow">MODEL PERFORMANCE</div><div class="wg-card-title">ML Model Performance</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Algorithm", "Isolation Forest")
    c2.metric("Learning", "Unsupervised")
    c3.metric("Train / Test Split", "Chronological 80:20")

    c4, c5, c6 = st.columns(3)
    c4.metric("Training Samples", f"{evaluation['n_train']:,}")
    c5.metric("Testing Samples", f"{evaluation['n_test']:,}")
    c6.metric("Features Used", f"{len(metadata['feature_columns'])}")

    c7, c8, c9, c10 = st.columns(4)
    c7.metric("Precision", f"{metrics['precision']}%")
    c8.metric("Recall", f"{metrics['recall']}%")
    c9.metric("F1 Score", f"{metrics['f1_score']}%")
    c10.metric("False Positive Rate", f"{metrics['false_positive_rate']}%")
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Confusion Matrix (Unseen Test Set)</div>', unsafe_allow_html=True)
        st.plotly_chart(charts.confusion_matrix_chart(metrics["confusion_matrix"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Per-Anomaly-Type Detection Rate</div>', unsafe_allow_html=True)
        if evaluation["per_type"]:
            per_type_df = pd.DataFrame(evaluation["per_type"]).set_index("anomaly_type")
            st.plotly_chart(
                charts.anomalies_by_category_chart(per_type_df["detection_rate"]),
                use_container_width=True,
            )
        else:
            st.info("No labeled anomalies fell in the test window.")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Model Information (training / leakage-protection details)"):
        i1, i2 = st.columns(2)
        with i1:
            st.write("**Dataset**")
            st.write(f"Total observations: {evaluation['n_train'] + evaluation['n_test']:,}")
            st.write(f"Training period: {evaluation['train_period'][0]} → {evaluation['train_period'][1]}")
            st.write(f"Testing period: {evaluation['test_period'][0]} → {evaluation['test_period'][1]}")
        with i2:
            st.write("**Pipeline Safeguards**")
            st.write("Split method: **Chronological** (oldest 80% → newest 20%)")
            st.write("Shuffling: **Disabled**")
            st.write("Data leakage protection: **Enabled** (scaler fit on train only)")
            st.write("Preprocessing: Median imputation + Robust scaling")

    st.markdown("---")
    st.markdown('<div class="wg-card-title">Live Session Analytics</div>', unsafe_allow_html=True)

    if not detection_log:
        st.info("No live detections generated yet this session. Enable Simulation or inject an anomaly from the Dashboard.")
        return

    log_rows = []
    for entry in detection_log:
        d = entry["detection"]
        log_rows.append(
            {
                "timestamp": pd.to_datetime(d["timestamp"]),
                "station_id": d["station_id"],
                "sensor": d["affected_sensor"],
                "severity": d["severity"],
                "anomaly": d["anomaly"],
                "anomaly_score": d["anomaly_score"],
            }
        )
    log_df = pd.DataFrame(log_rows)

    col3, col4, col5 = st.columns(3)
    with col3:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Anomalies Over Time</div>', unsafe_allow_html=True)
        st.plotly_chart(charts.anomalies_over_time_chart(log_df[log_df["anomaly"]]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Anomalies by Sensor</div>', unsafe_allow_html=True)
        by_sensor = log_df[log_df["anomaly"]]["sensor"].value_counts()
        if not by_sensor.empty:
            st.plotly_chart(charts.anomalies_by_category_chart(by_sensor), use_container_width=True)
        else:
            st.info("No anomalies logged yet.")
        st.markdown("</div>", unsafe_allow_html=True)
    with col5:
        st.markdown('<div class="wg-card"><div class="wg-card-title">Severity Distribution</div>', unsafe_allow_html=True)
        severity_counts = log_df["severity"].value_counts()
        st.plotly_chart(charts.severity_distribution_chart(severity_counts), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="wg-card"><div class="wg-card-title">Anomalies by Station</div>', unsafe_allow_html=True)
    by_station = log_df[log_df["anomaly"]]["station_id"].value_counts()
    if not by_station.empty:
        st.plotly_chart(charts.anomalies_by_category_chart(by_station), use_container_width=True)
    else:
        st.info("No anomalies logged yet.")
    st.markdown("</div>", unsafe_allow_html=True)
