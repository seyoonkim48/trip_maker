from htbuilder import div, styles
from htbuilder.units import rem

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# client = OpenAI()


# 추천 검색어 버튼 정의
SUGGESTIONS = {
    "🗼 도쿄 3박 4일": "도쿄 3박 4일 여행 일정을 짜주세요.",
    "🏝️ 발리 5박 6일": "발리 5박 6일 여행 일정을 짜주세요.",
    "🗽 뉴욕 4박 5일": "뉴욕 4박 5일 여행 일정을 짜주세요.",
    "🏯 교토 2박 3일": "교토 2박 3일 여행 일정을 짜주세요.",
    "🌏 서울 1박 2일": "서울 1박 2일 여행 일정을 짜주세요.",
}

st.html(div(style=styles(font_size=rem(5), line_height=1))["✈️"])

st.set_page_config(page_title="여행 플래너", page_icon="✈️")

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        # ":material/cognition_2: Streamlit AI assistant", anchor=False, width="stretch"
        "Streamlit AI assistant",
        anchor=False,
        width="stretch",
    )

with st.container():
    st.chat_input("Ask a question...", key="initial_question")

    selected_suggestion = st.pills(
        label="Examples",
        label_visibility="collapsed",
        options=SUGGESTIONS.keys(),
        key="selected_suggestion",
    )


with st.sidebar:
    st.write("사이드바")