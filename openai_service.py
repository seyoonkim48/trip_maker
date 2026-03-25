import sqlite3
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

import json

# 사용자 정의 tool 함수들
from tools import get_current_time, web_search

CLASSIFIER_PROMPT = """
당신은 사용자의 메시지를 분류하는 분류기입니다.

[분류 기준]
- new_trip: 아래 중 하나라도 해당되면 new_trip
    - 새로운 여행지가 언급됨 (예: 도쿄, 파리, 제주도)
    - 새로운 여행 기간이 언급됨 (예: 3박 4일, 2박 3일)
    - "다시", "새로", "다른 곳", "대신" 같은 표현 포함
    - 여행 계획/일정을 새로 요청하는 문장

- followup: 아래 중 하나라도 해당되면 followup
    - 현재 진행 중인 여행 일정을 수정/보완 요청
    - 현재 여행지에 대한 추가 질문 (날씨, 환율, 맛집 등)
    - "바꿔줘", "수정해줘", "추가해줘", "어때?" 같은 표현

[응답 규칙]
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.
마크다운 코드 블록 없이 순수 JSON만 응답하세요.
{"intent": "new_trip"} 또는 {"intent": "followup"}
"""

MAIN_PROMPT = """
당신은 친절하고 전문적인 여행 플래너입니다.
최신 정보가 필요하면 반드시 web_search 도구를 사용하세요.
사용자의 요청 앞에 [요약 요청] 또는 [세부 요청] 태그가 붙습니다.
태그에 따라 아래 지침대로 응답하세요.

================================================================
[요약 요청] 태그가 붙은 경우
================================================================
여행 테마를 JSON 형식으로 제안하세요.

- 사용자가 여행 컨셉을 지정하지 않은 경우: 3가지 테마 제안
- 사용자가 여행 컨셉을 지정한 경우: 1~2가지 테마 제안
- 각 테마는 제목과 요약만 포함 (장소 목록은 불필요)
- summary는 markdown 형식으로 작성
    - 핵심 키워드는 **굵게** 표시
    - 지역/이동수단/음식을 bullet point로 구분
    - 2~4줄 이내로 간결하게

반드시 아래 JSON 형식으로만 응답하세요.
{
    "destination": "여행지 및 기간",
    "cases": [
        {
            "id": 0,
            "title": "테마 제목",
            "summary": "markdown 형식의 요약"
        }
    ]
}

================================================================
[세부 요청] 태그가 붙은 경우
================================================================
선택된 테마를 바탕으로 상세 여행 일정을 JSON 형식으로 만드세요.

- user_message는 markdown 형식으로 작성
    - DAY별 헤더 (## DAY 1)
    - 각 장소는 bullet point
    - 이동수단, 예상 소요시간 포함
    - 추천 음식/식당 포함
    - 일정 안내가 모두 끝난 후 여행 준비 안내 (## 여행 준비)
    - 여행지가 대한민국이 아닌 경우 한국과의 시차가 몇시간인지 안내
        - 현재 시간이나 날짜를 질문하거나 계산해야하는 경우 get_current_time을 사용하세요.
    - 여행지가 대한민국이 아닌 경우 사용하는 화폐와 현재 환율 안내
- locations는 반드시 실제 존재하는 장소로 작성
    - Nominatim으로 검색 가능한 정확한 장소명과 주소
    - 가상의 장소나 불확실한 장소는 절대 포함하지 말 것
- 일정 수정 요청이 들어오면 전체 일정을 반영해서 JSON으로 응답
- 여행과 무관한 질문(날씨, 환율 등)은 user_message에만 답변하고
    locations는 이전 것을 그대로 유지

반드시 아래 JSON 형식으로만 응답하세요.
{
    "user_message": "markdown 형식의 전체 일정",
    "locations": [
        {
            "day": 1,
            "name": "장소명",
            "address": "Nominatim 검색용 상세 주소",
            "description": "이 장소에서 할 것"
        }
    ]
}
"""

DEFAULT_MODEL = "gpt-4.1-nano"

@st.cache_resource # 다른 인자가 들어오면 다시 실행 됨
def create_agent_executor(model_type:str = DEFAULT_MODEL):
    """
    model_type: "gpt-4.1-nano"(default) | "gpt-4.1-mini"
    """
    llm = ChatOpenAI(model=model_type)  # LLM 모델 생성. 기본은 nano / 대화 분류시 mini

    if model_type == DEFAULT_MODEL:
        conn = sqlite3.connect("agent_memory.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    else:
        # mini일 때는 맥락 유지 필요 없음
        checkpointer = None


    agent = create_agent(
        model=llm,
        tools=[get_current_time, web_search],
        system_prompt=MAIN_PROMPT if model_type == DEFAULT_MODEL else CLASSIFIER_PROMPT,
        checkpointer=checkpointer
    )
    return agent

# 지금 이루어진 대화가 요약 일정 요청인지 세부 일정 요청인지 구분하는 함수
def classify_request(agent, prompt:str) -> str:
    """
    사용자의 질문(요청)이 새로운 질문인지 이전의 질문을 이어가는 것인지 구분합니다.
    새로운 질문의 경우 "new_trip"을, 이어가는 질문의 경우 "followup"을 반환합니다.
    """
    # 단순리 질문의 목적을 이해하기만 하면 됨 --> 가벼운 모델 사용
    # 대화를 이어갈 필요 없음 --> thread_id 불필요
    result = agent.invoke(
        {
            "messages" : [
                {"role" : "user", "content" : prompt}
            ]
        }
    )
    content = json.loads(result["messages"][-1].content)
    return content["intent"]

# messages는 내역이 저장된 리스트
# def get_ai_response(agent, prompt:str, thread_id:str) -> str:
#     """
#     현재 사용자 이력 1개만 전달합니다.
#     이전 대화는 thread_id를 기준으로 SQLite checkpointer가 복원함
#     """
#     result = agent.invoke(
#         {
#             "messages" : [
#                 {"role": "user", "content": prompt}
#             ]
#         },
#         config={
#             "configurable": {
#                 # thread_id로 대화 구분
#                 # -> 같은 ID면 이전 대화 이어짐
#                 # -> 다른 ID면 새로운 대화
#                 "thread_id": thread_id
#             }
#         }
#     )
#     return result["messages"][-1].content

# 요약 일정
def get_ai_trip_summary(agent, prompt: str, thread_id: str) -> str:
    """
    여행 일정을 요청할 때 1차 답변으로 여행에 대한 1 ~ 3개의 요약 일정을 JSON으로 응답합니다.
    컨셉에 대한 가이드가 없이 질문할 경우 3개의 요약 일정은 각기 다른 컨셉으로 제시됩니다.
    컨셉에 대한 언급이 있다면 해당 컨셉에 맞춰 1 ~ 2개의 요약 일정을 응답합니다.
    """
    result = agent.invoke(
        {
            "messages" : [
                {"role": "user", "content": f"[요약 요청] {prompt}"}
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    return json.loads(result["messages"][-1].content)

# 세부 일정
def get_ai_trip_detail(agent, trip_summary, thread_id:str) -> str:
    """
    요약 일정 중 하나를 선택한 후 해당 내용을 전달해 세부적인 일정을 JSON으로 응답합니다.
    """
    selected_title = f"""
[세부 요청]
여행지: {trip_summary["destination"]}
선택된 테마 제목: {trip_summary["cases"][0]["title"]}
선택된 테마 요약: {trip_summary["cases"][0]["summary"]}
"""
    result = agent.invoke(
        {
            "messages" : [
                {"role": "user", "content": selected_title}
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    return json.loads(result["messages"][-1].content)