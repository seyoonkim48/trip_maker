from langchain.tools import tool
from ddgs import DDGS
from datetime import datetime
import pytz     # pip install pytz


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