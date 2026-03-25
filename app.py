import streamlit as st
from dotenv import load_dotenv
from json_db import (
    load_chat_data,
    save_chat_data,
    clear_thread_id
)
from openai_service import (
    create_agent_executor,
    get_ai_trip_summary,
    get_ai_trip_detail,
    classify_request
    # get_ai_response
)

from map import make_map

# .env 파일 로드
load_dotenv()

# 브라우저 탭에 표시되는 웹 페이지 제목(title)을 설정함
st.set_page_config(page_title="Trip Maker", page_icon="🌴")

# -----------------------
# 초기화
# -----------------------
if "messages" not in st.session_state or "thread_id" not in st.session_state:
    chat_data = load_chat_data()
    st.session_state["thread_id"] = chat_data["thread_id"]
    st.session_state["messages"] = chat_data["messages"]
    st.session_state["summaries"] = None
    st.session_state["selected_trip"] = None

#----------------------------------
# 사이드바
#----------------------------------
with st.sidebar:
    st.title("설정")

    st.write("현재 thread_id")
    st.code(st.session_state["thread_id"])

    if st.button("대화 초기화"):
        st.session_state["thread_id"] = clear_thread_id()
        st.session_state["messages"] = []
        st.rerun()

# -----------------------------------------
# Agent 설정
# -----------------------------------------
agent = create_agent_executor()
agent_mini = create_agent_executor("gpt-4.1-mini")

# ---------------------------------
# 채팅 UI 출력
# ---------------------------------
st.title("여행을 쉽게, Trip Maker 🌴")

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):  # 메시지의 역할(role:"user" 또는 "assistant")
        st.markdown(msg["content"])     # 해당 메시지의 실제 내용(content)을 마크다운 형식으로 출력


# -----------------------------
# 사용자 입력
# -----------------------------
if prompt := st.chat_input("메시지를 입력하세요"):

    # 사용자 메시지 저장
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # JSON에도 즉시 저장
    save_chat_data(
        st.session_state["thread_id"],
        st.session_state["messages"]
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    # ---------------------------
    # Agent 호출
    # ---------------------------
    try:
        with st.spinner("✈️ 여행 일정을 확인 중이에요...") :
            # 새로운 질문인지 이어가는 질문인지 구분 -- mini
            intent = classify_request(agent=agent_mini, prompt=prompt)
            if intent == "new_trip":
                # 새로운 질문이면 요약 함수 실행 -- 일반
                response_summaries = get_ai_trip_summary(
                    agent=agent,
                    prompt=prompt,
                    thread_id=st.session_state["thread_id"]
                )
    except Exception as e:
        with st.chat_message("assistant"):
            st.markdown(f"오류가 발생했습니다: {e}")
        st.stop()  # 오류 시 이후 출력 블록 실행 안 함

    # 요약 일정 결과 출력
    if intent == "new_trip" and response_summaries:
        st.session_state["summaries"] = response_summaries

        with st.chat_message("assistant"):
            cols = st.columns(len(response_summaries["cases"]))

            for i, case in enumerate(response_summaries["cases"]):
                with cols[i]:
                    st.markdown(f"### {i + 1}. {case['title']}")
                    st.markdown(case['summary'])
                    if st.button("선택", key=f"case_{i}"):
                        st.session_state["summaries"] = None # 선택했으니까 비워주기
                        st.session_state["selected_trip"] = case
            
            try:
                with st.spinner("✈️ 여행 일정 만드는 중..."):
                    response = get_ai_trip_detail(
                        agent=agent,
                        trip_summary=st.session_state["selected_trip"], 
                        thread_id=st.session_state["thread_id"]
                    )
            except Exception as e:
                with st.chat_message("assistant"):
                    st.markdown(f"오류가 발생했습니다: {e}")
                st.stop()  # 오류 시 이후 출력 블록 실행 안 함
    
    # 결과 출력
    # with st.chat_message("assistant"):
    #     st.markdown(response_summaries)

    # AI 응답 저장
    st.session_state["messages"].append({
        "role":"assistant",
        "content":str(response_summaries)
    })

    # JSON에도 다시 저장
    save_chat_data(
        st.session_state["thread_id"],
        st.session_state["messages"]
    )
