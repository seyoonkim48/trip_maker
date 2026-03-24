import sqlite3              # SQLite DB 사용을 위한 표중 라이브러리
import streamlit as st      # Streamlit 캐싱 (Agent 재사용 목적)

from langchain_openai import ChatOpenAI

# 최신 Agent 생성 함수 (LangGraph기반)
from langchain.agents import create_agent

from langgraph.checkpoint.sqlite import SqliteSaver

# 사용자 정의 tool 함수들
from tools import get_current_time, web_search

@st.cache_resource
def create_agent_executor():
    """
    Agent를 생성하고 캐싱함.
    -> Streamlit은 매 실행마다 코드가 재실행되기 때문에 Agent를 매번 만들면 느림
    -> cache_resource로 1번만 생성 후 재사용
    """
    llm = ChatOpenAI(model="gpt-4.1-nano")  # LLM 모델 생성


    conn = sqlite3.connect("agent_memory.db", check_same_thread=False)

    checkpointer = SqliteSaver(conn)


    # Agent 생성
    agent = create_agent(
        model=llm,
        tools=[get_current_time, web_search],
        system_prompt=(
            "당신은 친절한 비서입니다."
            "현재 시간이나 날짜를 물으면 get_current_time을 사용하세요."
            "주식 정보는 get_yf_stock_info를 사용하세요."
            "최신 정보가 필요하면 반드시 web_search 도구를 사용하세요."
            "추측하지말고 도구를 사용하세요."
        ),
        checkpointer=checkpointer
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