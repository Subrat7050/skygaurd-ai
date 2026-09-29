"""
components/styles.py
=====================
Custom CSS injected once at app startup to move the UI away from default
Streamlit widget styling toward a professional monitoring-platform look:
dark navy sidebar, light gray canvas, white cards, badges, etc.
"""

import streamlit as st

import config


def inject_custom_css():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: Canvas;
        }}

        [data-testid="stMainMenuItem-theme-Dark"] {{
            display: none !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {config.COLOR_NAVY};
        }}
        section[data-testid="stSidebar"] * {{
            color: #cbd5e1 !important;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            background-color: {config.COLOR_NAVY_LIGHT};
            color: #e2e8f0 !important;
            border: 1px solid #334155;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color: {config.COLOR_ACCENT};
            color: white !important;
        }}

        div[data-testid="stMetric"] {{
            background-color: Canvas;
            color: CanvasText;
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid rgba(127, 127, 127, 0.25);
        }}

        .wg-card {{
            background-color: Canvas;
            color: CanvasText;
            border-radius: 12px;
            padding: 20px 22px;
            border: 1px solid rgba(127, 127, 127, 0.25);
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
            margin-bottom: 18px;
        }}
        .wg-card-eyebrow {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: CanvasText;
            opacity: 0.72;
            margin-bottom: 2px;
        }}
        .wg-card-title {{
            font-size: 17px;
            font-weight: 700;
            color: CanvasText;
            margin-bottom: 10px;
        }}
        .wg-big-number {{
            font-size: 34px;
            font-weight: 800;
            color: CanvasText;
            line-height: 1.1;
        }}
        .wg-sub {{
            color: CanvasText;
            opacity: 0.72;
            font-size: 13px;
        }}

        .wg-badge {{
            display: inline-block;
            padding: 3px 11px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.03em;
        }}
        .wg-badge-normal {{ background-color: #dcfce7; color: #15803d; }}
        .wg-badge-warning {{ background-color: #fef3c7; color: #b45309; }}
        .wg-badge-high {{ background-color: #ffedd5; color: #c2410c; }}
        .wg-badge-critical {{ background-color: #fee2e2; color: #b91c1c; }}
        .wg-badge-healthy {{ background-color: #dcfce7; color: #15803d; }}
        .wg-badge-monitoring {{ background-color: #dbeafe; color: #1d4ed8; }}
        .wg-badge-degrading {{ background-color: #fef3c7; color: #b45309; }}

        .wg-explanation-item {{
            display: flex;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid rgba(127, 127, 127, 0.25);
            color: CanvasText;
        }}
        .wg-explanation-num {{
            flex-shrink: 0;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background-color: #eef2ff;
            color: #4338ca;
            font-size: 12px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .wg-station-dot {{
            display: inline-block;
            width: 9px;
            height: 9px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        .wg-hero-title {{
            font-size: 26px;
            font-weight: 800;
            color: CanvasText;
            margin-bottom: 2px;
        }}
        .wg-hero-sub {{
            color: CanvasText;
            opacity: 0.72;
            font-size: 14px;
            margin-bottom: 18px;
        }}

        div[data-baseweb="tab-list"] {{
            gap: 4px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def severity_badge_class(severity: str) -> str:
    return {
        "NORMAL": "wg-badge-normal",
        "WARNING": "wg-badge-warning",
        "HIGH": "wg-badge-high",
        "CRITICAL": "wg-badge-critical",
    }.get(severity, "wg-badge-normal")


def health_badge_class(status: str) -> str:
    return {
        "HEALTHY": "wg-badge-healthy",
        "MONITORING": "wg-badge-monitoring",
        "DEGRADING": "wg-badge-degrading",
        "CRITICAL": "wg-badge-critical",
    }.get(status, "wg-badge-healthy")


def status_color(status: str) -> str:
    return {
        "HEALTHY": config.COLOR_HEALTHY,
        "WARNING": config.COLOR_WARNING,
        "CRITICAL": config.COLOR_CRITICAL,
    }.get(status, config.COLOR_HEALTHY)
