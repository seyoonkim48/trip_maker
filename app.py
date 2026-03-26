import streamlit as st
from streamlit_folium import st_folium
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
st.set_page_config(page_title="Trip Maker", page_icon="🌴",)

MAP_HEIGHT = 500

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
    st.markdown("### ✈️ 여행 옵션")
    st.write("트립 메이커가 참고할 수 있게 여행에 대한 세부 설정을 선택해주세요.")
    
    if st.button("옵션 초기화"):
        st.session_state["travel_dense"] = None
        st.session_state["travel_style"] = []
        st.session_state["travel_transport"] = None
        st.rerun()

    # 여행 밀도
    st.markdown("**여행 밀도**")
    st.radio(
        "여행 밀도",
        ['⏰ 1분 1초가 아깝다', '🎲 발길 닿는 대로', '🌿 적당히 여유롭게'],
        captions=[
            "시간표 형식, 아침/점심/저녁 식당까지",
            "자유시간이 섞인 시간표",
            "지명 정도만, 즉흥적으로"
        ],
        index=None,
        label_visibility="collapsed",
        key="travel_dense",
        )
    # 여행 스타일
    st.markdown("**여행 스타일**")
    st.multiselect(
        "여행 스타일",
        [
            '🏛️ 유적지·역사', '🏙️ 건물·도시 풍경',
            '🛍️ 시장·쇼핑', '🍜 현지 음식 탐방',
            '👥 현지인 문화', '🏖️ 휴양·자연'
        ],
        label_visibility="collapsed",
        key="travel_style"
        )
    
    # 이동 수단
    st.markdown("**이동 수단**")
    st.radio(
        "이동 수단",
        ['🚶 도보 중심', '🚇 대중교통', '🚕 택시', '🔀 유연하게'],
        index=None,
        label_visibility="collapsed",
        key="travel_transport"
    )

    st.divider()

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

if st.session_state.get("summaries"):
    
    with st.chat_message("assistant"):
        cases = st.session_state["summaries"]["cases"]
        cols = st.columns(len(cases))

        for i, case in enumerate(cases):
            with cols[i]:
                st.markdown(f"### {i + 1}. {case['title']}")
                st.markdown(case['summary'])
                select_btn = st.button("선택", key=f"case_{i}", width="stretch")
                if select_btn:
                    print("button click!")
                    st.session_state["selected_trip"] = {
                        "destination": st.session_state["summaries"]["destination"],
                        "cases":[case]
                    }
                    st.session_state["summaries"] = None # 선택했으니까 비워주기

#--------------------------------------------------------------------------------
# 버튼을 눌러 선택한 요약 일정 -> 세부 일정 호출 -> 화면에 보여주기
#--------------------------------------------------------------------------------
if st.session_state.get("selected_trip"):
    print(st.session_state["selected_trip"])

    # 여행 옵션을 하나라도 선택한 경우
    if st.session_state.get("travel_dense") or st.session_state.get("travel_style") or st.session_state("travel_transport"):
        more_options = {
            "travel_dense": st.session_state.get("travel_dense"),
            "travel_style": st.session_state.get("travel_style"),
            "travel_transport": st.session_state.get("travel_transport")
        }
    try:
        with st.spinner("✈️ 여행 일정 만드는 중..."):
            print("in detail spinner")
            response = get_ai_trip_detail(
                agent=agent,
                trip_summary=st.session_state["selected_trip"], 
                thread_id=st.session_state["thread_id"],
                more_options=more_options
            )
            st.session_state["selected_trip"] = None
        with st.chat_message("assistant"):
            st.markdown(response["user_message"])
            with st.spinner("지도 생성중 ..."):
                map = make_map(response)
                st_folium(
                    map,
                    height=MAP_HEIGHT,
                    use_container_width=True,
                    returned_objects=[]
                )
        
        st.session_state["messages"].append({
            "role":"assistant",
            "content": response["user_message"]
        })
    except Exception as e:
        with st.chat_message("assistant"):
            st.markdown(f"오류가 발생했습니다: {e}")
        st.stop()  # 오류 시 이후 출력 블록 실행 안 함


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
                st.session_state["summaries"] = response_summaries
                st.rerun()
            elif intent == "followup":
                # 이전 여행 결과에 이어가는 질문
                with st.spinner("✈️ 여행 일정 수정 중..."):
                    response = get_ai_trip_detail(
                        agent=agent,
                        thread_id=st.session_state["thread_id"],
                        prompt=prompt
                    )
                with st.chat_message("assistant"):
                    st.markdown(response["user_message"])

                    with st.spinner("지도 생성중 ..."):
                        map = make_map(response)
                        st_folium(
                            map,
                            height=MAP_HEIGHT,
                            use_container_width=True,
                            returned_objects=[]
                        )
                
                st.session_state["messages"].append({
                    "role":"assistant",
                    "content": response["user_message"]
                })
    except Exception as e:
        with st.chat_message("assistant"):
            st.markdown(f"오류가 발생했습니다: {e}")
        st.stop()  # 오류 시 이후 출력 블록 실행 안 함


# JSON에도 다시 저장
save_chat_data(
    st.session_state["thread_id"],
    st.session_state["messages"]
)
