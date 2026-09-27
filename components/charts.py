"""
components/charts.py
=====================
All Plotly chart builders used across the Dashboard and Analytics pages.
Each function takes already-computed data and returns a `go.Figure`;
callers render with st.plotly_chart(fig, use_container_width=True).
"""

import pandas as pd
import plotly.graph_objects as go

import config


def multivariate_sensor_chart(history_df: pd.DataFrame, anomaly_mask: pd.Series | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history_df["timestamp"], y=history_df["humidity"], name="Humidity (%)",
            mode="lines+markers", line=dict(color="#22c55e"), yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=history_df["timestamp"], y=history_df["temperature"], name="Temperature (°C)",
            mode="lines+markers", line=dict(color="#ef4444"), yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=history_df["timestamp"], y=history_df["pressure"], name="Pressure (hPa)",
            mode="lines+markers", line=dict(color="#3b82f6"), yaxis="y2",
        )
    )

    if anomaly_mask is not None and anomaly_mask.any():
        anomalous = history_df[anomaly_mask]
        fig.add_trace(
            go.Scatter(
                x=anomalous["timestamp"], y=anomalous["temperature"], name="Anomaly",
                mode="markers", marker=dict(color="#dc2626", size=13, symbol="x"),
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title="Temperature / Humidity"),
        yaxis2=dict(title="Pressure (hPa)", overlaying="y", side="right"),
    )
    return fig


def sensor_health_timeline_chart(trajectory: list, timestamps: list | None = None) -> go.Figure:
    x = timestamps if timestamps is not None and len(timestamps) == len(trajectory) else list(range(len(trajectory)))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=trajectory, mode="lines+markers",
            line=dict(color="#f59e0b", width=3),
            marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(245, 158, 11, 0.08)",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Sensor Health %", range=[0, 105]),
    )
    return fig


def confusion_matrix_chart(confusion: dict) -> go.Figure:
    z = [[confusion["tn"], confusion["fp"]], [confusion["fn"], confusion["tp"]]]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["Predicted Normal", "Predicted Anomaly"],
            y=["Actual Normal", "Actual Anomaly"],
            colorscale="Blues",
            text=z,
            texttemplate="%{text}",
            showscale=False,
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def anomalies_over_time_chart(log_df: pd.DataFrame) -> go.Figure:
    if log_df.empty:
        fig = go.Figure()
        fig.update_layout(template="plotly_white", height=300, annotations=[dict(text="No anomalies logged yet", showarrow=False)])
        return fig
    counts = log_df.set_index("timestamp").resample("1h")["anomaly"].sum().fillna(0)
    fig = go.Figure(go.Bar(x=counts.index, y=counts.values, marker_color="#3b82f6"))
    fig.update_layout(template="plotly_white", height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Anomalies")
    return fig


def anomalies_by_category_chart(counts: pd.Series, title: str = "") -> go.Figure:
    fig = go.Figure(go.Bar(x=counts.index.astype(str), y=counts.values, marker_color="#6366f1"))
    fig.update_layout(template="plotly_white", height=300, margin=dict(l=10, r=10, t=30, b=10), title=title)
    return fig


def severity_distribution_chart(counts: pd.Series) -> go.Figure:
    colors = [config.SEVERITY_COLORS.get(s, "#94a3b8") for s in counts.index]
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values, marker=dict(colors=colors), hole=0.5))
    fig.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=10, b=10))
    return fig
