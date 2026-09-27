"""
components/sidebar.py
======================
Renders the dark-navy sidebar: branding, page navigation, live station
list with status dots, and the bottom system-status footer.

Navigation requests from other components are handled through
`pending_nav_page` BEFORE the `nav_page` widget is instantiated.
This avoids StreamlitWidgetAlreadyInstantiatedError.
"""

import streamlit as st

import config
from components import styles


def render_sidebar(stations_status_df, current_station: str):

    # =========================================================
# HANDLE PENDING NAVIGATION
# =========================================================
#
# IMPORTANT:
# This MUST happen BEFORE the widget with
# key="nav_page" is created.
#
# Other components such as injection_panel.py should NEVER
# directly modify nav_page after the radio widget exists.
#
# They should instead set:
#
#     st.session_state["pending_nav_page"] = "Dashboard"
#
# =========================================================

    pending_nav_page = st.session_state.pop(
        "pending_nav_page",
        None,
    )

    # Valid application pages
    pages = [
        "Dashboard",
        "Analytics",
        "Station Details",
        "Settings",
    ]

    # If another component requested navigation,
    # apply it BEFORE creating the nav_page widget.
    if pending_nav_page in pages:
        st.session_state["nav_page"] = pending_nav_page


    with st.sidebar:

        # =====================================================
        # BRANDING
        # =====================================================

        st.markdown(
            "🛡️ **SkyGaurd AI**\n\nAI-Powered AWS Monitoring"
        )

        # =====================================================
        # MAIN NAVIGATION
        # =====================================================

        st.markdown(
            """
            <div style="
                font-size:11px;
                letter-spacing:0.08em;
                color:#64748b;
                font-weight:700;
                margin-bottom:4px;
            ">
                MAIN
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -----------------------------------------------------
        # NAVIGATION WIDGET
        # -----------------------------------------------------

        page = st.radio(
            "nav",
            pages,
            label_visibility="collapsed",
            key="nav_page",
        )

        # =====================================================
        # WEATHER STATIONS
        # =====================================================

        st.markdown(
            """
            <div style="
                font-size:11px;
                letter-spacing:0.08em;
                color:#64748b;
                font-weight:700;
                margin:18px 0 4px 0;
            ">
                WEATHER STATIONS
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_station = current_station

        for _, row in stations_status_df.iterrows():

            color = styles.status_color(
                row["status"]
            )

            alert = (
                " 🔴"
                if row["status"] == "CRITICAL"
                else ""
            )

            cols = st.columns(
                [0.14, 0.86]
            )

            with cols[0]:

                st.markdown(
                    f"""
                    <div style="
                        margin-top:8px;
                        width:9px;
                        height:9px;
                        border-radius:50%;
                        background:{color};
                    "></div>
                    """,
                    unsafe_allow_html=True,
                )

            with cols[1]:

                if st.button(
                    f"{row['station_id']}{alert}",
                    key=f"station_btn_{row['station_id']}",
                    use_container_width=True,
                ):

                    selected_station = (
                        row["station_id"]
                    )

        # =====================================================
        # SIMULATION
        # =====================================================

        st.markdown(
            "<div style='margin-top:24px;'></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="
                font-size:11px;
                letter-spacing:0.08em;
                color:#64748b;
                font-weight:700;
                margin-bottom:4px;
            ">
                SIMULATION
            </div>
            """,
            unsafe_allow_html=True,
        )

        sim_on = st.toggle(
            "Live Simulation",
            value=st.session_state.get(
                "simulation_on",
                False,
            ),
            key="simulation_on",
        )

        refresh_interval = st.select_slider(
            "Refresh interval (s)",
            options=config.REFRESH_INTERVAL_OPTIONS,
            value=st.session_state.get(
                "refresh_interval",
                config.DEFAULT_REFRESH_INTERVAL,
            ),
            key="refresh_interval",
        )

        # =====================================================
        # SYSTEM STATUS
        # =====================================================

        st.markdown(
            "<div style='margin-top:18px;'></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="
                position:relative;
                margin-top:10px;
                padding-top:14px;
                border-top:1px solid #1e293b;
            ">

                <div style="
                    font-size:13px;
                    color:#e2e8f0;
                ">
                    ⚙️ Settings
                </div>

                <div style="
                    margin-top:14px;
                    display:flex;
                    align-items:center;
                    gap:8px;
                ">

                    <div style="
                        width:8px;
                        height:8px;
                        border-radius:50%;
                        background:#22c55e;
                    "></div>

                    <div style="
                        font-size:13px;
                        color:#e2e8f0;
                        font-weight:600;
                    ">
                        System Online
                    </div>

                </div>

                <div style="
                    font-size:11px;
                    color:#64748b;
                    margin-left:16px;
                ">
                    All services operational
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        # =====================================================
        # RETURN VALUES TO app.py
        # =====================================================

        return (
            page,
            selected_station,
            sim_on,
            refresh_interval,
        )