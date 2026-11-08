"""페이지 1: 랜딩 페이지."""
from pathlib import Path

import streamlit as st

LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.png"

st.page_link("views/analysis.py", label="채점 · 분석 페이지로 이동 →", icon="📊")

st.markdown(
    """
    <style>
      .hero {text-align:center; padding: 2.5rem 0 1rem;}
      .hero h1 {font-size: 2.6rem; margin: .8rem 0 .3rem; color:#1F4E79;}
      .hero p  {font-size: 1.1rem; color:#555;}
      .logo-fallback {display:inline-flex; width:140px; height:140px; border-radius:24px;
                      background:#1F4E79; color:#fff; align-items:center; justify-content:center;
                      font-size:1.4rem; font-weight:700;}
      .card {background:#F2F6FA; border-radius:14px; padding:1.1rem 1.2rem; height:100%;}
      .card h4 {margin:0 0 .4rem; color:#1F4E79;}
    </style>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([2, 1, 2])
with mid:
    if LOGO.exists():
        st.image(str(LOGO), use_container_width=True)
    else:
        st.markdown('<div style="text-align:center"><div class="logo-fallback">가천대<br>로고</div></div>',
                    unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <h1>oo 학원 평가 도우미</h1>
      <p>문제지 · OMR 결과 · 정답표를 올리면 자동으로 채점하고,<br>
      성적 분석과 맞춤 문제 생성까지 AI 에이전트가 도와드립니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
features = [
    ("📥 자동 채점", "정답 PDF에서 문항·정답·배점을 자동으로 읽어 120명 OMR 결과를 즉시 채점합니다."),
    ("📑 엑셀 추출", "평균·중앙값·표준편차·최다 오답 문항과 학생별 문항 정답 여부를 엑셀로 내려받습니다."),
    ("💬 AI 챗봇", "\"87번 학생 몇 점이야?\", \"많이 틀린 문제와 비슷한 문제 만들어줘\" 처럼 물어보세요."),
]
for col, (t, d) in zip((c1, c2, c3), features):
    col.markdown(f'<div class="card"><h4>{t}</h4>{d}</div>', unsafe_allow_html=True)

st.write("")
_, b, _ = st.columns([2, 1, 2])
with b:
    if st.button("시작하기", type="primary", use_container_width=True):
        st.switch_page("views/analysis.py")
