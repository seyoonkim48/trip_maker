import streamlit as st
from streamlit_folium import st_folium
import folium

# 지도 높이 고정값 (이 값을 기준으로 리스트 높이도 맞춤)
MAP_HEIGHT = 500

places = [
    {"day": 1, "name": "경복궁", "duration": "2시간", "desc": "조선 왕조의 법궁",
    "lat": 37.5796, "lon": 126.9770},
    {"day": 1, "name": "광화문", "duration": "1시간", "desc": "경복궁의 남쪽 정문",
    "lat": 37.5759, "lon": 126.9769},
    {"day": 2, "name": "인사동", "duration": "2시간", "desc": "전통 문화 거리",
    "lat": 37.5742, "lon": 126.9850},
]

m = folium.Map(location=[37.5796, 126.9770], zoom_start=14)

for i, p in enumerate(places):
    folium.Marker(
        location=[p["lat"], p["lon"]],
        tooltip=p["name"],
        popup=folium.Popup(
            f"<b>{p['name']}</b><br>DAY {p['day']} · {p['duration']}<br>{p['desc']}",
            max_width=200
        ),
        icon=folium.DivIcon(
            html=f"""
                <div style="
                    background-color: #FF5A5F;
                    color: white;
                    border-radius: 50%;
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 13px;
                    border: 2px solid white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                ">
                    {i+1}
                </div>
            """,
            icon_size=(28, 28),
            icon_anchor=(14, 14),
        )
    ).add_to(m)

col1, col2 = st.columns([4, 1])

with col1:
    st_folium(m, height=MAP_HEIGHT, use_container_width=True)

with col2:
    items_html = ""
    for p in places:
        items_html += f"""
        <div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0;">
            <span style="font-size: 11px; color: #888;">DAY {p["day"]}</span><br>
            <b>📍 {p["name"]}</b><br>
            <span style="font-size: 12px; color: #555;">🕐 {p["duration"]}</span><br>
            <span style="font-size: 12px;">{p["desc"]}</span>
        </div>
        """

    st.markdown(
        f"""
        <div style="
            height: {MAP_HEIGHT}px;
            overflow-y: auto;
            padding: 8px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        ">
            {items_html}
        </div>
        """,
        unsafe_allow_html=True
    )