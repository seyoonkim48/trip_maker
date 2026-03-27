from langchain.tools import tool
from ddgs import DDGS
from datetime import datetime
import calendar
import requests
import pytz     # pip install pytz
import yfinance as yf   # pip install yfinance
from geopy.geocoders import Nominatim

import os
os.environ["SSL_CERT_FILE"] = r"C:\cert\cacert.pem"
os.environ["CURL_CA_BUNDLE"] = r"C:\cert\cacert.pem"


# pytz를 사용해 문자열 형식으로 받은 타임존을 파이썬 타임존 인스턴스로 만들고,
# 이를 datetime.now()에 전달해 해당 타임존의 현재 시간을 반환
@tool
def get_current_time(timezone: str = "Asia/Seoul"):
    """타임존의 현재 날짜와 시간을 'YYYY-MM-DD HH:MM:SS' 형식으로 반환합니다."""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S") + f" {timezone}"
    except Exception as e:
        return f"시간 가져오기 오류: {e}"

# 시차 계산 함수
@tool
def get_timezone_diff(target_timezone: str) -> str:
    """한국(Asia/Seoul)과 target_timezone의 시차를 계산합니다."""
    print(f"=== get_timezone_diff 호출: {target_timezone} ===")  # 추가
    seoul_tz = pytz.timezone("Asia/Seoul")
    target_tz = pytz.timezone(target_timezone)
    now = datetime.now(pytz.utc)
    
    seoul_offset = now.astimezone(seoul_tz).utcoffset().total_seconds() / 3600
    target_offset = now.astimezone(target_tz).utcoffset().total_seconds() / 3600
    diff = int(target_offset - seoul_offset)
    
    direction = "느림" if diff < 0 else "빠름"
    return f"한국(UTC+9)과 {target_timezone}의 시차: 한국보다 {abs(diff)}시간 {direction}"

# 웹서치
@tool
def web_search(query:str) -> str:
    """웹에서 최신 정보를 검색함"""

    # DuckDuckGo 검색 실행
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_result=3)    # max_result=3 -> 상위 3개 결과

            if not results:
                return "검색 결과가 없습니다."
            
            output = []
            
            for r in results:
                output.append(f"{r['title']} - {r['href']}")

            return "\n".join(output)
        
    except Exception as e:
        return f"검색 오류 : {e}"
    
# 환율
@tool
def get_exchange_rate(ticker: str):
    """
    야후 파이낸스를 통해 환율 정보를 반환합니다.
    ticker 형식: {출발통화}{도착통화}=X
    예시: USDKRW=X (달러→원), JPYKRW=X (엔→원), EURKRW=X (유로→원)
    """
    try:
        stock = yf.Ticker(ticker)

        info_dict = dict(stock.fast_info)

        # 만약 가져온 정보가 비어있거나 존재하지 않는 경우에 대한 예외 처리
        if not info_dict:
            return "정보를 찾을 수 없습니다."
        
        # 가져온 딕셔너리 형태의 정보를 문자열(str)로 변환하여 반환함
        return str(info_dict)

    # 실행 도중 발생할 수 있는 모든 에러(네트워크 단절, 잘못된 티커 등)를 잡아냄
    except Exception as e:
        # 에러 메시지를 포함하여 사용자에게 알림을 보냄
        return f"환율 정보 가져오기 오류: {e}"
    
# 지난 날씨 가져오고 분석하는 함수
@tool
def get_historical_weather(destination:str, month: int=None) -> str:
    """
    여행지의 최근 3년간 특정 월의 날씨(기온, 강수량)를 조회합니다.
    특정 월에 대한 언급이 없다면 함수를 호출하는 현재 날짜를 기준으로 합니다.
    destination: 여행지 이름 (예: "Tokyo", "도쿄", "Paris", "제주도")
    month: 여행 월 (1~12 정수)
    """

    geolocator = Nominatim(user_agent="trip_weather")
    location = geolocator.geocode(destination)
    if not location:
        return f"{destination} 위치를 찾을 수 없습니다."
    
    lat, lng = location.latitude, location.longitude
    # Open-Meteo 과거 날씨 API (Archive API)
    url = "https://archive-api.open-meteo.com/v1/archive"

    current_year = datetime.now().year
    month = month if month else datetime.now().month
    all_max_temps = []  # 최고 기온
    all_min_temps = []  # 최저 기온
    all_precip = []     # 강수량

    for year in range(current_year - 3, current_year):
        lastday = calendar.monthrange(year, month)
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": f"{year}-{month:02d}-01",  # 해당 달의 1일
            "end_date": f"{year}-{month:02d}-{lastday}", # 해당 달의 말일
            "daily": [
                "temperature_2m_max",   # 일 최고 기온
                "temperature_2m_min",   # 일 최저 기온
                "precipitation_sum",    # 강수량
            ],
            "timezone": "auto"
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
            daily = data.get("daily", {})
        except Exception as e:
            # 에러 메시지를 포함하여 사용자에게 알림을 보냄
            return f"최근 3년의 날씨 가져오기 오류: {e}"
        
        # 혹시 들어가있을지 모를 None 제거
        all_max_temps.extend(
            [temp for temp in daily.get("temperature_2m_max", [])
            if temp is not None])
        all_min_temps.extend(
            [temp for temp in daily.get("temperature_2m_min", [])
            if temp is not None])
        all_precip.extend(
            [temp for temp in daily.get("precipitation_sum", [])
            if temp is not None])
    
    if not all_max_temps:
        return "날씨 데이터를 가져올 수 없습니다."
    
    # 평균 --> 소수점 한자리
    avg_max = round(sum(all_max_temps) / len(all_max_temps), 1)
    avg_min = round(sum(all_min_temps) / len(all_min_temps), 1)
    avg_precip = round(sum(all_precip) / len(all_precip), 1)

    # 비온날 - 강수량 1이상만 모으기 (그 이하는 이슬같은거)
    rainy_days = sum([1 for p in all_precip if p > 1])
    # 강수 확률
    rain_ratio = round(rainy_days / len(all_precip) * 100)

    return (
        f"{destination} {month}월 최근 3년 날씨 평균:\n"
        f"- 평균 최고기온: {avg_max}°C\n"
        f"- 평균 최저기온: {avg_min}°C\n"
        f"- 일 평균 강수량: {avg_precip}mm\n"
        f"- 강수 확률: {rain_ratio}%"
    )