# map.py
# 지도와 관련된 연산을 하는 파일

# Open Street Map
from geopy.geocoders import Nominatim
import folium

# OSM 연결을 위한 user_agent 설정 - 없으면 요청 차단
geolocator = Nominatim(user_agent="trip", timeout=10)

# 주소 -> 위도, 경도 출력 
def get_coordinates(place: str):
    """
    주소 혹은 장소를 input으로 받으면 위경도로 변환하여
    지도에서 바로 찾을 수 있는 주소와 위경도를 반환합니다.
    """
    try:
        location = geolocator.geocode(place)
        if location is None:
            return None
        return {
            "address": location.address,
            "lat_lng": (location.latitude, location.longitude)
        }
    except Exception as e:
        print(f"⚠️ geocoding 오류 ({place}): {e}")
        return None

# 세부 일정의 응답으로 온 dict(json에서 변환) 정보를 넘기면
def extract_coordinates(data: dict) -> list:
    """
    세부 일정의 응답으로 온 dict(json에서 변환) 정보에서 주소들을 뽑아내
    get_coordinates 함수를 통해 위, 경도로 변환된 리스트를 출력합니다.
    """
    results = []
    print("----------------------------------------------")
    print(data)
    print("----------------------------------------------")
    for location in data["locations"]:
        coordinate = get_coordinates(location["address"])
        if coordinate is None:
            coordinate = get_coordinates(location["name"])
        if coordinate is None:
            print(f"⚠️ 위경도 변환 실패: {location['name']}")
            continue 
        results.append({
            "day": location['day'],
            "name": location['name'],
            "description": location['description'],
            "lat_lng": coordinate['lat_lng']
        })
    print("*" * 20)
    print(results)
    print("*" * 20)
    return results

# 지도의 중앙 찾기
def get_center(coordinates: list) -> tuple:
    """
    세부 일정으로 만들어진 방문할 장소들의 평균을 구합니다.
    평균 위경도는 지도의 중심이 됩니다.
    """
    lat, lng = zip(*coordinates)  # 반복 안하기
    center = (sum(lat) / len(lat), sum(lng) / len(lng))
    return center

# 지도 반환
def make_map(data: dict):
    """
    세부 일정을 바탕으로 응답과 함께 화면에 표시할 지도 객체를 만듭니다.
    보여줄 지도, 마커, 마커 사이의 연결 선(방문 순서대로)이 포함되어 있습니다.
    """
    geo_locations = extract_coordinates(data)

    if not geo_locations:
        return None

    coords = [loc['lat_lng'] for loc in geo_locations]
    center = get_center(coords)
    
    m = folium.Map(
        location=center,
        zoom_start=14
    )

    folium.PolyLine(
        locations=coords,
        color="red",
        weight=4
    ).add_to(m)

    for i, loc in enumerate(geo_locations):
        folium.Marker(
            location=coords[i],
            popup=folium.Popup(
            f"<b>{loc['name']}</b><br>DAY {loc['day']}<br>{loc['description']}",
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

    return m