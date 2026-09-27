"""
components/injection_panel.py
==============================

Anomaly Injection Control Panel + SIH Demo Mode.

Both paths feed injected readings through the same detection pipeline
used by ordinary live readings.

Navigation is requested through `pending_nav_page`.

IMPORTANT:
This file must NEVER modify:

    st.session_state["nav_page"]

because that key belongs to the sidebar navigation widget.
"""

import streamlit as st

import config

print("LOADED INJECTION PANEL FROM:", __file__)

def render(simulation_state, stations_df, current_selected_station: str):
    station_ids = list(stations_df["station_id"])

    # =========================================================
    # ANOMALY INJECTION CONTROL PANEL
    # =========================================================

    with st.expander(
        "🧪 Anomaly Injection Control Panel",
        expanded=False,
    ):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 0.7])

        # -----------------------------------------------------
        # STATION
        # -----------------------------------------------------

        with c1:
            if current_selected_station in station_ids:
                station_index = station_ids.index(
                    current_selected_station
                )
            else:
                station_index = 0

            station = st.selectbox(
                "Station",
                station_ids,
                index=station_index,
            )

        # -----------------------------------------------------
        # SENSOR
        # -----------------------------------------------------

        with c2:
            sensor = st.selectbox(
                "Sensor",
                config.INJECTABLE_SENSORS,
            )

        # -----------------------------------------------------
        # ANOMALY TYPE
        # -----------------------------------------------------

        with c3:
            anomaly_type = st.selectbox(
                "Anomaly Type",
                [
                    "spike",
                    "drift",
                    "stuck",
                    "impossible_value",
                    "multivariate",
                ],
            )

        # -----------------------------------------------------
        # INJECT BUTTON
        # -----------------------------------------------------

        with c4:
            st.markdown(
                "<div style='height:28px;'></div>",
                unsafe_allow_html=True,
            )

            inject_clicked = st.button(
                "⚡ Inject Anomaly",
                type="primary",
                use_container_width=True,
            )

        # =====================================================
        # NORMAL ANOMALY INJECTION
        # =====================================================

        if inject_clicked:

            simulation_state.step(
                station,
                inject=(sensor, anomaly_type),
            )

            # Keep selected station synchronized.
            st.session_state["selected_station"] = station

            st.success(
                f"Injected {anomaly_type} on {sensor} at {station}. "
                "Dashboard updated below."
            )

            # Rerun so the dashboard immediately displays
            # the updated simulation/detection state.
            st.rerun()

    # =========================================================
    # SIH DEMO MODE
    # =========================================================

    demo_col1, demo_col2 = st.columns([1, 3])

    # ---------------------------------------------------------
    # SIH DEMO CALLBACK
    # ---------------------------------------------------------

    def run_sih_demo():
        """
        Run the complete AWS-001 temperature-spike demo.

        This callback NEVER modifies the nav_page widget state.

        Instead, it creates a navigation request which is consumed
        by sidebar.py before the navigation widget is instantiated.
        """

        # -----------------------------------------------------
        # Step 1: Fresh normal baseline reading
        # -----------------------------------------------------

        simulation_state.step(
            "AWS-001"
        )

        # -----------------------------------------------------
        # Step 2: Deterministic temperature spike
        # -----------------------------------------------------

        simulation_state.step(
            "AWS-001",
            inject=("temperature", "spike"),
            forced_values={
                "temperature": 55.2,
            },
        )

        # -----------------------------------------------------
        # Step 3: Select AWS-001
        # -----------------------------------------------------

        st.session_state["selected_station"] = "AWS-001"

        # -----------------------------------------------------
        # Step 4: Request Dashboard navigation
        #
        # NEVER do:
        #
        # st.session_state["nav_page"] = "Dashboard"
        #
        # -----------------------------------------------------

        st.session_state["pending_nav_page"] = "Dashboard"
        st.rerun()
    # ---------------------------------------------------------
    # DEMO BUTTON
    # ---------------------------------------------------------

    with demo_col1:

        st.button(
            "🚀 SIH Demo Mode",
            type="primary",
            use_container_width=True,
            on_click=run_sih_demo,
        )

    with demo_col2:

        st.caption(
            "Runs the polished AWS-001 temperature-spike scenario "
            "end-to-end through the real detection pipeline."
        )

