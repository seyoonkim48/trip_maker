import sqlite3
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver

import json

# 사용자 정의 tool 함수들
from tools import get_current_time, web_search, get_timezone_diff

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
반드시 마크다운 코드 블록 없이 순수 JSON만 응답하세요.

================================================================
[요약 요청] 태그가 붙은 경우
================================================================
여행 테마를 JSON 형식으로 제안하세요.

- 사용자의 요청에 맞게 3가지 테마 제안
- 각 테마는 제목과 요약만 포함 (장소 목록은 불필요)
- summary는 markdown 형식으로 작성
    - 핵심 키워드는 **굵게** 표시
    - 지역/이동수단/음식을 bullet point로 구분
    - 2~4줄 이내로 간결하게
    - summary 안에서 줄바꿈은 \\n으로 표현하세요.
    - summary 시작에 ### 를 쓰지 마세요.

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
- [추가 옵션]이 있다면 추가 옵션을 기준으로 일정을 만드세요.
- [추가 옵션]이 없다면 자체적으로 판단하여 일정을 만드세요.
- 요청된 여행 기간 전체 일정을 반드시 작성하세요.
    예: 7박 8일이면 DAY 1부터 DAY 8까지 모두 작성
- 일정을 중간에 생략하거나 요약하지 마세요.

[user_message 작성 규칙]
- DAY별 헤더는 반드시 그날의 컨셉 요약을 포함하세요.
    형식: ## DAY 1 - {그날의 컨셉 한 줄 요약}
    예시: ## DAY 1 - 고궁과 북촌: 조선의 숨결 속으로
    예시: ## DAY 2 - 홍대와 명동: 트렌디한 서울 즐기기
- 각 장소는 bullet point로 작성
- 이동수단과 예상 소요시간 포함
- 추천 음식/식당 포함
- 일정이 모두 끝난 후 ## 여행 준비 섹션 추가
- 요청된 여행 기간 전체 일정을 반드시 작성하세요.
    웹 검색이 실패하더라도 일반 지식으로 전체 일정을 완성하세요.


[여행지가 대한민국 외 국가인 경우 추가 안내]
- 반드시 web_search로 현재 환율을 검색한 후 안내하세요.
- 환율은 반드시 대한민국 화폐인 원화와 비교해서 안내하세요.
    예시: 현재 환율은 1파운드 = 약 1,680원입니다. (검색 기준)
- 반드시 get_current_time으로 현재 시간을 확인한 후 한국과의 시차를 계산하세요.
- 시차 계산 시 get_timezone_diff를 사용하여 한국과의 시차를 계산하세요.
    예시: 런던은 한국보다 9시간 느립니다. (서머타임 적용 시 8시간)
    여행지 현지 표준시 기준이 아닌 반드시 한국과의 시차를 안내하세요.
- 시차와 환율 안내는 ## 여행 준비 섹션에 포함하세요.

[대한민국 내 여행인 경우]
- 시차와 환율 안내를 절대 포함하지 마세요.
- "시차가 없습니다", "환율이 동일합니다" 같은 문구도 쓰지 마세요.

[locations 작성 규칙]
- locations 필드는 반드시 포함해야 합니다. 빠뜨리면 안 됩니다.
- user_message에 언급된 모든 방문 장소를 locations에 포함하세요.
- 반드시 실제 존재하는 장소만 작성
- Nominatim으로 검색 가능한 정확한 장소명과 주소
- 가상의 장소나 불확실한 장소는 절대 포함하지 말 것

[후속 대화 규칙]
- 일정 수정 요청이 들어오면 반드시 DAY 1부터 마지막 날까지
    전체 일정을 포함한 JSON으로 응답하세요.
- 수정된 날만 응답하지 마세요. 항상 전체 일정을 응답하세요.
- 여행과 무관한 질문(날씨 등)은 user_message에만 답변하고
    locations는 이전 것을 그대로 유지

반드시 아래 JSON 형식으로만 응답하세요.
{
    "user_message":  "## DAY 1 - 도착과 첫 번째 탐험: 시내 중심부\\n- **버킹엄 궁전** 방문 (지하철 Circle Line, 약 30분)\\n- 점심: **The Ivy** 레스토랑\\n\\n## DAY 2 - 박물관과 문화: 런던의 역사 속으로\\n- **대영박물관** 방문 (도보 20분)\\n\\n## 여행 준비\\n- 영국 파운드(GBP) 환전\\n- 시차: 한국보다 9시간 느림 (서머타임 적용 시 8시간)",
    "locations": [
        {
            "day": 1,
            "name": "버킹엄 궁전",
            "address": "Buckingham Palace, London, SW1A 1AA",
            "description": "영국 왕실의 공식 거주지"
        }
    ]
}
"""

DEFAULT_MODEL = "gpt-4.1"

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
        tools=[get_current_time, web_search, get_timezone_diff],
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

# 요약 일정
def get_ai_trip_summary(agent, prompt: str, thread_id: str) -> str:
    """
    여행 일정을 요청할 때 1차 답변으로 여행에 대한 1 ~ 3개의 요약 일정을 JSON으로 응답합니다.
    컨셉에 대한 가이드가 없이 질문할 경우 3개의 요약 일정은 각기 다른 컨셉으로 제시됩니다.
    컨셉에 대한 언급이 있다면 해당 컨셉에 맞춰 1 ~ 2개의 요약 일정을 응답합니다.
    """

    data = f"""
[요약 요청] {prompt}

[응답 규칙 - 반드시 준수]
여행 테마를 JSON 형식으로 제안하세요.

- 사용자의 요청에 맞게 3가지 테마 제안
- 각 테마는 제목과 요약만 포함 (장소 목록은 불필요)
- summary는 markdown 형식으로 작성
    - 핵심 키워드는 **굵게** 표시
    - 지역/이동수단/음식을 bullet point로 구분
    - 2~4줄 이내로 간결하게

1. 마크다운 코드 블록 없이 순수 JSON만 응답하세요.
2. 반드시 아래 두 필드를 모두 포함하세요: "destination", "cases"
3. summary 시작에 ### 를 쓰지 마세요.
4. summary 안에서 줄바꿈은 \\n으로 표현하세요.

반드시 아래 JSON 형식으로만 응답하세요.
{{
    "destination": "여행지 및 기간",
    "cases": [
        {{
            "id": 0,
            "title": "테마 제목",
            "summary": "markdown 형식의 요약"
        }}
    ]
}}
"""

    result = agent.invoke(
        {
            "messages" : [
                {"role": "user", "content": data}
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    # raw = result["messages"][-1].content
    # print("=== LLM 원본 응답 ===")
    # print(raw)
    # print("====================")
    return json.loads(result["messages"][-1].content)

# 세부 일정 + 일정 수정 요청
def get_ai_trip_detail(agent, thread_id:str, trip_summary = None, prompt=None, more_options=None) -> str:
    """
    요약 일정 중 하나를 선택한 후 해당 내용을 전달해 세부적인 일정을 JSON으로 응답합니다.
    만들어진 1차 세부 일정에서 유저의 피드백(prompt)이 들어오면 일정을 수정합니다.
    """
    if trip_summary:
        data = f"""
[세부 요청]
여행지: {trip_summary["destination"]}
선택된 테마 제목: {trip_summary["cases"][0]["title"]}
선택된 테마 요약: {trip_summary["cases"][0]["summary"].replace("### ", "").strip()}

[추가 옵션]
여행 일정의 세밀함: {more_options["travel_dense"]}
선호하는 여행 스타일: {more_options["travel_style"]}
선호하는 이동 수단: {more_options["travel_transport"]}

[응답 규칙 - 반드시 준수]
1. 마크다운 코드 블록 없이 순수 JSON만 응답하세요.
2. 반드시 아래 두 필드를 모두 포함하세요: "user_message", "locations"
3. locations 필드는 절대 빠뜨리면 안 됩니다.
4. locations에는 user_message에 언급된 모든 장소를 빠짐없이 포함하세요.
    user_message에 장소가 10개면 locations도 10개여야 합니다.
    1개만 넣거나 대표 장소만 넣으면 안 됩니다.
    - user_message에 언급된 모든 방문 장소를 locations에 포함하세요.
    - 반드시 실제 존재하는 장소만 작성
    - Nominatim으로 검색 가능한 정확한 장소명과 주소
    - 가상의 장소나 불확실한 장소는 절대 포함하지 말 것
5. DAY별 헤더 형식: ## DAY N - 컨셉 요약
6. 요청된 전체 기간 일정을 모두 작성하세요.
7. 대한민국 내 여행이면 시차/환율/화폐 정보를 절대 포함하지 마세요.

반드시 아래 JSON 형식으로만 응답하세요.
{{
    "user_message": "## DAY 1 - 컨셉\\n- 장소 (이동수단, 소요시간)\\n\\n## 여행 준비\\n- 준비물",
    "locations": [
        {{
            "day": 1,
            "name": "장소명",
            "address": "Nominatim 검색 가능한 상세 주소",
            "description": "이 장소에서 할 것"
        }}
    ]
}}
"""
    else:
        data = f"""
[세부 요청] {prompt}

[응답 규칙 - 반드시 준수]
1. 마크다운 코드 블록 없이 순수 JSON만 응답하세요.
2. 반드시 아래 두 필드를 모두 포함하세요: "user_message", "locations"
3. locations 필드는 절대 빠뜨리면 안 됩니다.
4. 일정 수정 시 DAY 1부터 마지막 날까지 전체 일정을 포함하세요.
5. 수정된 날만 응답하지 마세요. 항상 전체 일정을 응답하세요.

반드시 아래 JSON 형식으로만 응답하세요.
{{
    "user_message": "전체 일정",
    "locations": [
        {{
            "day": 1,
            "name": "장소명",
            "address": "Nominatim 검색 가능한 상세 주소",
            "description": "이 장소에서 할 것"
        }}
    ]
}}
"""
    result = agent.invoke(
        {
            "messages" : [
                {"role": "user", "content": data}
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    raw = result["messages"][-1].content
    parsed = json.loads(raw)
    print("=== 세부 일정 LLM 원본 응답 ===")
    print(parsed)
    print("================================")
    # 전체 메시지 흐름 확인
    # for msg in result["messages"]:
    #     print(type(msg).__name__, ":", msg.content[:100] if msg.content else "(tool call)")
    # print("========================")
    return json.loads(result["messages"][-1].content)