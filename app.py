"""oo 학원 평가 도우미 - 진입점 (Streamlit multipage)."""
import streamlit as st

st.set_page_config(page_title="oo 학원 평가 도우미", page_icon="📝", layout="wide")

home = st.Page("views/home.py", title="홈", icon="🏠", default=True)
analysis = st.Page("views/analysis.py", title="채점 · 분석", icon="📊")

# 페이지 이동은 각 페이지 상단의 '페이지 버튼'(st.page_link)으로 한다.
st.navigation([home, analysis], position="hidden").run()
