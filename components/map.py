"""
components/map.py
=================
Interactive weather-station map using Folium (+ streamlit-folium).

Marker colors reflect live station status. Clicking a marker shows
a popup with the station's last-known readings.

Uses OpenStreetMap as the basemap so the deployed Streamlit app
does not require a CARTO API key.
"""

import folium
from streamlit_folium import st_folium

import config


def render_station_map(
    stations_df,
    stations_status_df,
    latest_readings: dict,
    height: int = 420
):
    # Remove duplicate status column if it already exists
    base = stations_df.drop(columns=["status"], errors="ignore")

    # Merge station information with current status
    merged = base.merge(
        stations_status_df,
        on="station_id",
        how="left"
    )

    # Default status
    merged["status"] = merged["status"].fillna("HEALTHY")

    # Calculate map center
    center_lat = merged["latitude"].mean()
    center_lon = merged["longitude"].mean()

    # ============================================================
    # MAP
    # ============================================================
    # OpenStreetMap does not require a CARTO API key.
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4.4,
        tiles="OpenStreetMap",
        control_scale=True
    )

    # ============================================================
    # STATUS COLORS
    # ============================================================
    color_map = {
        "HEALTHY": config.COLOR_HEALTHY,
        "WARNING": config.COLOR_WARNING,
        "CRITICAL": config.COLOR_CRITICAL,
    }

    # ============================================================
    # STATION MARKERS
    # ============================================================
    for _, row in merged.iterrows():

        status = row["status"]

        color = color_map.get(
            status,
            config.COLOR_HEALTHY
        )

        # Get latest sensor readings
        reading = latest_readings.get(
            row["station_id"],
            {}
        )

        # Popup content
        popup_html = f"""
        <div style="font-family: Arial; font-size: 13px;">

            <h4 style="margin-bottom: 8px;">
                {row['station_id']}
            </h4>

            <b>Location:</b>
            {row['city']}, {row['state']}<br><br>

            <b>Status:</b>
            {status}<br>

            <b>Temperature:</b>
            {reading.get('temperature', '--')}<br>

            <b>Humidity:</b>
            {reading.get('humidity', '--')}<br>

            <b>Pressure:</b>
            {reading.get('pressure', '--')}

        </div>
        """

        # Create station marker
        folium.CircleMarker(
            location=[
                row["latitude"],
                row["longitude"]
            ],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
            tooltip=(
                f"{row['station_id']} - "
                f"{row['city']}"
            ),
            popup=folium.Popup(
                popup_html,
                max_width=250
            ),
        ).add_to(fmap)

    # ============================================================
    # DISPLAY MAP IN STREAMLIT
    # ============================================================
    return st_folium(
        fmap,
        height=height,
        use_container_width=True,
        returned_objects=[]
    )