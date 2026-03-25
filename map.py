# map.py
# 지도와 관련된 연산을 하는 파일

# Open Street Map
from geopy.geocoders import Nominatim
import folium

# OSM 연결을 위한 user_agent 설정 - 없으면 요청 차단
geolocator = Nominatim(user_agent="trip_maker")

# 주소 -> 위도, 경도 출력 
def get_coordinates(place: str):
    """
    주소 혹은 장소를 input으로 받으면 위경도로 변환하여
    지도에서 바로 찾을 수 있는 주소와 위경도를 반환합니다.
    """
    location = geolocator.geocode(place)
    return {
        "address" : location.address,
        "lat_lng" : (location.latitude, location.longitude)
    }

# 세부 일정의 응답으로 온 dict(json에서 변환) 정보를 넘기면
def extract_coordinates(data: dict) -> list:
    """
    세부 일정의 응답으로 온 dict(json에서 변환) 정보에서 주소들을 뽑아내
    get_coordinates 함수를 통해 위, 경도로 변환된 리스트를 출력합니다.
    """
    geo_locations = [get_coordinates(location['address']) for location in data['locations']]
    locations = [loc['lat_lng'] for loc in geo_locations]
    return locations

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
    center = get_center(data)
    
    map = folium.Map(
        location=center,
        zoom_start=14
    )

    locations = extract_coordinates(data)

    folium.PolyLine(
        locations=locations,
        color="red",
        weight=4
    )

    for i, loc in data:
        folium.Marker(
            location=locations[i],
            icon=folium.Icon(color="red", icon='star', prefix='fe')
        ).add_to(map)

    return map