import sqlite3              # SQLite DB 사용을 위한 표중 라이브러리
import streamlit as st      # Streamlit 캐싱 (Agent 재사용 목적)

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

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
{"intent": "new_trip"} 또는 {"intent": "followup"}
"""

MAIN_PROMPT = """
당신은 친절하고 전문적인 여행 플래너입니다.
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

@st.cache_resource
def create_agent_executor(model_type:str = "gpt-4.1-nano"):
    """
    model_type: "gpt-4.1-nano"(default) | "gpt-4.1-mini"
    """
    llm = ChatOpenAI(model=model_type)  # LLM 모델 생성. 기본은 nano / 대화 분류시 mini


    conn = sqlite3.connect("agent_memory.db", check_same_thread=False)

    checkpointer = SqliteSaver(conn)


    # Agent 생성
    if model_type == "gpt-4.1-nano":
        agent = create_agent(
            model=llm,
            tools=[get_current_time, web_search],
            system_prompt=(
                "당신은 여행 플래너입니다."
                "현재 시간이나 날짜를 물으면 get_current_time을 사용하세요."
                "주식 정보는 get_yf_stock_info를 사용하세요."
                "최신 정보가 필요하면 반드시 web_search 도구를 사용하세요."
                "추측하지말고 도구를 사용하세요."
            ),
            checkpointer=checkpointer
        )
    else:   # mini
        agent = create_agent(
            model=llm,
            tools=[get_current_time, web_search],
            system_prompt=(
                "당신은 친절한 비서입니다."
            )
        )
    return agent

# messages는 내역이 저장된 리스트
def get_ai_response(agent, prompt:str, thread_id:str) -> str:
    """
    현재 사용자 이력 1개만 전달합니다.
    이전 대화는 thread_id를 기준으로 SQLite checkpointer가 복원함
    """
    result = agent.invoke(
        {
            "messages" : [
                {"role": "user", "content": prompt}
            ]
        },
        config={
            "configurable": {
                # thread_id로 대화 구분
                # -> 같은 ID면 이전 대화 이어짐
                # -> 다른 ID면 새로운 대화
                "thread_id": thread_id
            }
        }
    )
    return result["messages"][-1].content

def make_instructions():
    """
    LLM에 전달할 지시사항을 만들어서 반환합니다.
    """
    theme_prompt = f"""
당신은 여행 플래너입니다.
사용자의 여행 요청을 분석해서 여행 테마를 제안하세요.

[응답 규칙]
1. 사용자가 컨셉을 지정하지 않았으면 3개, 지정했으면 1~2개 제안
2. 반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 절대 금지.
3. summary는 markdown 형식으로 작성하세요.
    - 굵은 글씨로 핵심 장소 강조
    - bullet point로 지역/교통/음식 구분
    - 2~4줄 이내로 간결하게

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
"""
    
    detail_prompt = """
당신은 여행 플래너입니다.
사용자가 선택한 테마로 상세 여행 일정을 만드세요.

[응답 규칙]
1. 반드시 아래 JSON 형식으로만 응답하세요.
2. user_message는 markdown 형식으로 작성하세요.
    - DAY별 헤더 (## DAY 1)
    - 각 장소는 bullet point
    - 이동수단, 예상 소요시간 포함
3. locations의 name과 address는 반드시 실제 존재하는 장소로, Nominatim으로 검색 가능해야 합니다.
4. 일정 수정 요청이 들어오면 전체 일정을 반영해서 JSON으로 응답하세요.
5. 일정과 무관한 질문(날씨, 환율 등)은 
6. user_message에만 답변하고 locations는 이전 것을 유지하세요.
{
    "user_message": "markdown 형식의 전체 일정",
    "locations": [
        {
            "day": 1,
            "name": "장소명",
            "address": "Nominatim 검색용 주소",
            "description": "이 장소에서 할 것"
        }
    ]
}
"""

# 요약
def get_ai_trip_summary():
    """
    여행 일정을 요청할 때 1차 답변으로 여행에 대한 1 ~ 3개의 요약 일정을 JSON으로 응답합니다.
    컨셉에 대한 가이드가 없이 질문할 경우 3개의 요약 일정은 각기 다른 컨셉으로 제시됩니다.
    컨셉에 대한 언급이 있다면 해당 컨셉에 맞춰 1 ~ 2개의 요약 일정을 응답합니다.
    """
    pass