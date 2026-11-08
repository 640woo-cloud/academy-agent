"""페이지 2: 데이터 업로드 · 자동 채점 · 엑셀 추출 · 채팅."""
import os

import streamlit as st

from agent import build_agent, stream_answer
from excel_export import build_excel
from grading import grade, parse_answer_pdf, parse_question_pdf, read_omr

ss = st.session_state
ss.setdefault("result", None)
ss.setdefault("excel", None)
ss.setdefault("messages", [])
ss.setdefault("agent", None)


def get_secret(name, default=None):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


API_KEY = get_secret("OPENAI_API_KEY")
MODEL = get_secret("OPENAI_MODEL", "gpt-4o-mini")

# ------------------------------------------------------------------ 사이드바
with st.sidebar:
    st.page_link("views/home.py", label="← 홈으로", icon="🏠")
    st.header("데이터 업로드")
    q_file = st.file_uploader("① 문제지 (PDF)", type=["pdf"], key="q")
    o_file = st.file_uploader("② OMR 인식 결과 (xlsx / csv)", type=["xlsx", "xls", "csv"], key="o")
    a_file = st.file_uploader("③ 정답지 (PDF)", type=["pdf"], key="a")

    if not API_KEY:
        API_KEY = st.text_input("OpenAI API Key", type="password", help="배포 시에는 Secrets에 등록하세요.")

    ready = all([q_file, o_file, a_file])
    if st.button("분석 시작", type="primary", use_container_width=True, disabled=not ready):
        try:
            with st.spinner("채점 중입니다..."):
                key = parse_answer_pdf(a_file.getvalue())
                questions = parse_question_pdf(q_file.getvalue())
                omr = read_omr(o_file.getvalue(), o_file.name)
                result = grade(key, omr, questions)
                ss.result = result
                ss.excel = build_excel(result)
                ss.agent = build_agent(result, API_KEY, MODEL) if API_KEY else None
            s = result.summary
            top3 = ", ".join(f"{t['문항']}번" for t in s["최다오답문항"])
            ss.messages = [{
                "role": "assistant",
                "content": (
                    f"✅ 채점이 완료되었습니다. (총 {s['총문항수']}문항, {s['만점']}점 만점, {s['응시인원']}명)\n\n"
                    f"- 평균 **{s['평균']}점**, 중앙값 **{s['중앙값']}점**, 표준편차 {s['표준편차']}\n"
                    f"- 최고점 {s['최고점']}점 / 최저점 {s['최저점']}점\n"
                    f"- 가장 많이 틀린 문항: **{top3}**\n\n"
                    "왼쪽 **엑셀 추출** 버튼으로 결과를 받거나, 아래 채팅창에 궁금한 점을 물어보세요."
                ),
            }]
        except Exception as e:  # 업로드 파일 오류를 사용자에게 안내
            st.error(f"채점 중 오류가 발생했습니다: {e}")

    st.download_button(
        "엑셀 추출",
        data=ss.excel or b"",
        file_name="채점결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=ss.excel is None,
    )
    if ss.result is None:
        st.caption("세 파일을 모두 올리고 **분석 시작**을 누르면 엑셀 추출과 채팅이 활성화됩니다.")

# ------------------------------------------------------------------ 메인: 채팅
st.subheader("💬 평가 도우미 채팅")

if ss.result is None:
    st.info("사이드바에 문제지 · OMR 결과 · 정답지를 업로드한 뒤 **분석 시작**을 눌러 주세요.")

for m in ss.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("채점 결과에 대해 물어보세요 (예: 87번 학생 몇 점이야?)", disabled=ss.result is None)
if prompt:
    ss.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        if ss.agent is None:
            if API_KEY:
                ss.agent = build_agent(ss.result, API_KEY, MODEL)
            else:
                st.warning("OpenAI API 키가 설정되지 않았습니다.")
                st.stop()
        try:
            answer = st.write_stream(stream_answer(ss.agent, ss.messages))
        except Exception as e:
            answer = f"죄송합니다. 답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요. ({type(e).__name__})"
            st.markdown(answer)
    ss.messages.append({"role": "assistant", "content": answer if isinstance(answer, str) else str(answer)})
