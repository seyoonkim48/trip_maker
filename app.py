import streamlit as st
from dotenv import load_dotenv
from json_db import (
    load_chat_data,
    save_chat_data,
    clear_thread_id
)
from openai_service import (
    create_agent_executor,
    get_ai_response
)

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
st.title("LangGraph Agent Chat")

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
        with st.spinner("AI가 답변을 생성 중입니다...") :
            response = get_ai_response(
                agent=agent,
                prompt=prompt,
                thread_id=st.session_state["thread_id"]
            )
    except Exception as e:
        response = f"오류가 발생했습니다.: {e}"

    # 결과 출력
    with st.chat_message("assistant"):
        st.markdown(response)

    # AI 응답 저장
    st.session_state["messages"].append({
        "role":"assistant",
        "content":response
    })

    # JSON에도 다시 저장
    save_chat_data(
        st.session_state["thread_id"],
        st.session_state["messages"]
    )
