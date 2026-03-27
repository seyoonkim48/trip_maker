import sqlite3              # SQLite DB 사용을 위한 표중 라이브러리
import streamlit as st      # Streamlit 캐싱 (Agent 재사용 목적)

from langchain_openai import ChatOpenAI

# 최신 Agent 생성 함수 (LangGraph기반)
from langchain.agents import create_agent

# 랭그래프는 대화의 맥락(State)를 유지하면서 반복(Loop)과 조건에 따른 정교한 제어가 가능한 에이전트 프레임워크
# SqliteSaver : LangGraph의 상태(State)를 SQLite DB에 영구 저장하기 위한 체크포인터
# 체크포인터는 AI가 대화의 흐름과 맥락을 깜거지 않도록, 그 시점의 기억을 agent_memory.db라는 파일에 실시간으로 "저장(세이브)" 하고 나중에 다시 "불러오기(로드)" 하는 장치임
from langgraph.checkpoint.sqlite import SqliteSaver

# 사용자 정의 tool 함수들
from tools import get_current_time, get_yf_stock_info, web_search

@st.cache_resource
def create_agent_executor():
    """
    Agent를 생성하고 캐싱함.
    -> Streamlit은 매 실행마다 코드가 재실행되기 때문에 Agent를 매번 만들면 느림
    -> cache_resource로 1번만 생성 후 재사용
    """
    llm = ChatOpenAI(model="gpt-4.1-nano")  # LLM 모델 생성

    # 멀티스레드(Multi-threading)란?
    # 하나의 프로그램 안에서 여러 개의 작업(Thread)을 동시에 처리하는 방식을 말함
    # 식당으로 비유하면, 한 명의 요리사가 아니라 "여러 명의 요리사"가 각자 주문을 처리하는 것과 같음

    # Streamlit은 웹 서비스이므로 여러 사용자가 동시에 접속할 수 있음
    # 이때 각 사용자 (세션)의 요청을 독립적으로 처리하기 위해 내부적으로 '새로운 스레드'를 생성하여 코드를 실행함
    # 즉, A사용자의 실행 스레드와 B 사용자의 실행 스레드가 동시에 돌아가는 구조임.

    # SQLite DB 파일 연결
    # 기본적으로 SQLite는 "한 스레드에서 만든 연결은 그 스레드에서만 사용"하도록 제한되어 있음

    # 하지만 Streamlit은 브라우저 세션(상태)이 변하거나 사용자가 상호작용할 때마다
    # 스크립트를 재실행하며, 이때 내부적으로 매번 새로운 스레드를 할당하여 처리할 수 있음

    # 즉, "연결을 만든 스레드"와 "실제 DB를 사용하는 스레드"가 달라질 수 있는 구조임

    # check_same_thread=False 옵션을 주면
    # "다른 스레드에서도 이 DB 연결을 사용해도 된다"고 허용하는 설정

    # 이 옵션이 없으면?
    # "SQLite objects created in a thread can only be used in that same thread" 에러 발생
    
    # 따라서 Stremlit = SQLite 조합에서는 거의 필수 설정
    conn = sqlite3.connect("agent_memory.db", check_same_thread=False)

    # 체크포인터(checkpointer) 생성
    # SqliteSaver는 SQLite DB (agent_memory.db)에 대화 내용을 자동으로 저장하는 역할을 함
    checkpointer = SqliteSaver(conn)


    # Agent 생성
    agent = create_agent(
        model=llm,
        tools=[get_current_time, get_yf_stock_info, web_search],
        system_prompt=(
            "당신은 친절한 비서입니다."
            "현재 시간이나 날짜를 물으면 get_current_time을 사용하세요."
            "주식 정보는 get_yf_stock_info를 사용하세요."
            "최신 정보가 필요하면 반드시 web_search 도구를 사용하세요."
            "추측하지말고 도구를 사용하세요."
        ),
        checkpointer=checkpointer       # Agent가 대화를 기억하도록 만드는 핵심 설정
                                        # checkpointer는 SQLite DB에 대화 내용을 저장/불러오는 역할을 함.
                                        # LangGraph에서는 thread_id(대화 ID)를 기준으로 이전 대화 내용을 DBdptj ckwdkdhrh
                                        # 새 대화도 계속 저장함
                                        # 이 설정이 없으면 매번 새 대화처럼 동작함
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