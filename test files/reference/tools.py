from langchain.tools import tool
from ddgs import DDGS
from datetime import datetime
import pytz     # pip install pytz

# 파이썬에서 금융 데이터(주가, 재무재표, 환율 등)를 아주 쉽게 가져올 수 있게 해주는 라이브러리를 불러오는 명령어
# 이 라이브러리는 전 세계적인 금융 정보 사이트인 야후 파이낸스(Yahoo Finance)의 공개된 서버와 연결됨
import yfinance as yf   # pip install yfinance

import os
# 파이썬의 표준 라이브러리( 예: urllib, ssl )가 참조할 인증서 파일 경로를 설정함
# "r"은 Raw String으로, 역슬래시(\)를 경로 기호로 그대로 인식하게 함
os.environ["SSL_CERT_FILE"] = r"C:\cert\cacert.pem"

# curl 기반의 라이브러리나 일부 하위 시스템이 참조할 인증서 묶음(Bundle) 경로를 설정함
# 보안 네트워크(방화벽) 환경에서 인증서 오류를 해결하기 위해 자주 사용됨
os.environ["CURL_CA_BUNDLE"] = r"C:\cert\cacert.pem"

@tool
def get_yf_stock_info(ticker: str):
    """야후 파이낸스에 공개된 주식 정보를 반환합니다."""
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
        return f"주식 정보 가져오기 오류: {e}"


# pytz를 사용해 문자열 형식으로 받은 타임존을 파이썬 타임존 인스턴스로 만들고,
# 이를 datetime.now()에 전달해 해당 타임존의 현재 시간을 반환
def get_current_time(timezone: str = "Asia/Seoul"):
    """타임존의 현재 날짜와 시간을 'YYYY-MM-DD HH:MM:SS' 형식으로 반환합니다."""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S") + f" {timezone}"
    except Exception as e:
        return f"시간 가져오기 오류: {e}"


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