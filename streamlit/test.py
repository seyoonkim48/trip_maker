
import streamlit as st

st.title("📦 Streamlit Container 예제")

# 컨테이너 1 - 요약 영역
with st.container():
    st.subheader("1️⃣ KPI 요약")
    col1, col2, col3 = st.columns(3)
    col1.metric("매출", "₩120,000")
    col2.metric("주문", "58건")
    col3.metric("고객 수", "34명")

# 구분선
st.markdown("---")

# 컨테이너 2 - 필터 + 표 영역
with st.container():
    st.subheader("2️⃣ 필터링 & 데이터")

    # 사이드 필터 (예시)
    category = st.selectbox("카테고리 선택", ["전체", "전자", "가구", "사무"])

    # 샘플 데이터 출력
    import pandas as pd
    df = pd.DataFrame({
        "제품명": ["노트북", "책상", "펜"],
        "카테고리": ["전자", "가구", "사무"],
        "매출": [100000, 20000, 3000]
    })

    if category != "전체":
        df = df[df["카테고리"] == category]

    st.dataframe(df)

# 컨테이너 3 - 하단 메모
with st.container():
    st.subheader("3️⃣ 메모 작성")
    st.text_area("학습 또는 회의 메모를 입력하세요")


import streamlit as st

# Using object notation
# add_selectbox = st.sidebar.selectbox(
#     "How would you like to be contacted?",
#     ("Email", "Home phone", "Mobile phone")
# )

# # Using "with" notation
# with st.sidebar:
#     add_radio = st.radio(
#         "Choose a shipping method",
#         ("Standard (5-15 days)", "Express (2-5 days)")
#     )

import streamlit as st
import time

with st.sidebar:
    with st.echo():
        st.write("This code will be printed to the sidebar.")

    with st.spinner("Loading..."):
        time.sleep(5)
    st.success("Done!")