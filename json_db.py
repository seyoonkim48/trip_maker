# json_db.py

# JSON 파일 입출력을 위한 표준 라이브러리
import json

# 파일 경로를 객체 형태로 다루기 위한 라이브러리
from pathlib import Path

import uuid

# JSON 파일의 경로
DB_FILE = Path("chat_history.json")
TRIP_DB = Path("trip.json")

def _default_data() -> dict:
    """
    기본 저장 구조를 반환함

    구조 예시:
    {
        "thread_id" : "uuid 값",
        "messages" : []
    }
    """
    return {
        "thread_id" : str(uuid.uuid4()),    # 랜덤한 고유 ID (식별자)를 생성하는 함수
        "messages" : []
    }


def load_chat_data() -> dict:
    """
    chat_history.json 전체 데이터를 불러옴.

    동작:
    1. 파일이 없으면 기본 구조 반환
    2. 파일이 있으면 JSON 전체 읽기
    3. 형식이 잘못되었거나 오류가 나면 기본 구조 반환
    """
    if not DB_FILE.exists():
        return _default_data()
    
    try:
        with DB_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # 딕셔너리 형태가 아니면 기본값 반환
        # isinstance(data, dict): data라는 변수가 dict 타입인지 검사함
        if not isinstance(data, dict):
            return _default_data()
        
        # 필수 키가 없으면 값을 설정
        if "thread_id" not in data:
            data["thread_id"] = str(uuid.uuid4())
        if "messages" not in data or not isinstance(data["messages"], list):
            data["messages"] = []
        
        return data
    
    except Exception:
        return _default_data()

def save_chat_data(thread_id:str, messages: list):
    """
    thread_id와 messages를 JSON 파일에 함께 저장함
    
    구조:
    {
        "thread_id": "...",
        "messages": [
            {"role":"user", "content":"..."},
            {"role":"assistant:, "content": "..."}
        ] 
    }    
    """

    data = {
        "thread_id" : thread_id,
        "messages": messages,
    }

    with DB_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_thread_id() -> str:
    """
    새로운 thread_id를 생성하여 저장하고 반환함.
    messages는 비움
    """
    new_thread_id = str(uuid.uuid4())
    save_chat_data(new_thread_id, [])
    return new_thread_id


def load_trips():
    """
    trip.json에 있는 여행 세부 일정들을 불러옵니다.
    사이드바에 나타납니다.
    """

    if not TRIP_DB.exists():
        return []
    
    try:
        with TRIP_DB.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []
    
    except Exception:
        return []


def load_trip(trip_id):
    """
    trip.json에서 trip_id에 해당하는 여행 일정 하나를 반환합니다.
    없는 경우 None 반환
    """
    trips = load_trips()
    for trip in trips:
        if trip.get("id") == trip_id:
            return trip
    return None

def save_trip(title: str, user_message: str, geo_locations: list):
    """
    세부 일정 중 저장하기를 누른 일정을 JSON파일에 저장합니다.
    나중에 화면에 보여줄 수 있도록 마크다운과 지도를 그릴 정보를 저장합니다.
    
    구조:
    {
        "id": 0,
        "saved_at": "2026-03-27T02:00:00",
        "title": "도쿄 3박 4일",
        "user_message": "## DAY 1 - ...",
        "geo_locations": [
            {
                "day": 1,
                "name": "도쿄역",
                "address": "...",
                "description": "...",
                "lat": 35.6762,
                "lng": 139.6503
            }
        ]
    }
    """

    trips = load_trips()

    new_trip = {
        "id": str(uuid.uuid4()),
        "title": title,
        "user_message": user_message,
        "geo_locations": geo_locations,
    }

    trips.append(new_trip)

    with TRIP_DB.open("w", encoding="utf-8") as f:
        json.dump(trips, f, ensure_ascii=False, indent=2)

def delete_trip(trip_id):
    """
    id가 일치하는 여행 일정을 trip.json에서 삭제함
    """

    trips = load_trips()
    trips = [trip for trip in trips if trip.get("id") != trip_id]

    with TRIP_DB.open("w", encoding="utf-8") as f:
        json.dump(trips, f, ensure_ascii=False, indent=2)