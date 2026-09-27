"""
components/map.py
==================
Interactive weather-station map using Folium (+ streamlit-folium). Marker
colors reflect live station status; clicking a marker shows a popup with
the station's last-known readings.
"""

import folium
from streamlit_folium import st_folium

import config


def render_station_map(stations_df, stations_status_df, latest_readings: dict, height: int = 420):
    base = stations_df.drop(columns=["status"], errors="ignore")
    merged = base.merge(stations_status_df, on="station_id", how="left")
    merged["status"] = merged["status"].fillna("HEALTHY")

    center_lat = merged["latitude"].mean()
    center_lon = merged["longitude"].mean()
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=4.4, tiles="CartoDB positron")

    color_map = {
        "HEALTHY": config.COLOR_HEALTHY,
        "WARNING": config.COLOR_WARNING,
        "CRITICAL": config.COLOR_CRITICAL,
    }

    for _, row in merged.iterrows():
        color = color_map.get(row["status"], config.COLOR_HEALTHY)
        reading = latest_readings.get(row["station_id"], {})
        popup_html = f"""
        <b>{row['station_id']}</b> &mdash; {row['city']}, {row['state']}<br>
        Status: <b>{row['status']}</b><br>
        Temperature: {reading.get('temperature', '--')}<br>
        Humidity: {reading.get('humidity', '--')}<br>
        Pressure: {reading.get('pressure', '--')}
        """
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
            tooltip=f"{row['station_id']} - {row['city']}",
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(fmap)

    return st_folium(fmap, height=height, use_container_width=True, returned_objects=[])
