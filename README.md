# oo 학원 평가 도우미 (Agent 기반 자동 채점 웹 서비스)

- **학번 / 이름**: 202439689 / 서관우
- **배포 URL**:https://academy-agent-202439689.streamlit.app

## 주요 기능
| 요구사항 | 구현 내용 |
|---|---|
| 1. 웹 페이지 구현 및 배포 | Streamlit 2페이지 구성 — `views/home.py`(랜딩), `views/analysis.py`(업로드·분석·채팅), Streamlit Community Cloud 배포 |
| 2. 자동 채점 | 사이드바에 문제지 PDF · OMR 결과(xlsx/csv) · 정답 PDF 업로드 → **분석 시작** 클릭 시 채점. 정답·배점은 정답 PDF에서 정규식으로 자동 추출(하드코딩 없음). 채점 후 엑셀 추출·채팅 활성화 |
| 3. 평가 결과 파일 추출 | `채점 결과` 시트: 전체 성적 개요(평균·중앙값·표준편차·최다 오답 3문항) + 학생별 점수 및 문항별 O/X. 참고용 `문항 분석` 시트 |
| 4. 채팅 기능 | LangChain `create_agent` 기반 에이전트. 세션 내 대화 기억(`st.session_state`), DB 저장 없음 |
| 5. 채팅 세부 기능 | 채점 데이터 조회 도구 6종(통계·학생 조회·순위·최다 오답·문항 상세·점수 분포)으로 수치는 항상 실제 데이터에서 계산. 데이터에 없는 질문은 회피, 시스템 프롬프트/도구 정보 비공개(프롬프트 인젝션 방어), 스트리밍 + 타임아웃으로 20초 이내 응답 |

## 폴더 구조
```
app.py              # 진입점 (st.navigation)
views/home.py       # 페이지 1: 랜딩
views/analysis.py   # 페이지 2: 업로드 · 채점 · 엑셀 · 채팅
grading.py          # 정답 PDF 파싱, 문제지 파싱, OMR 채점, 통계
excel_export.py     # 엑셀 생성
agent.py            # LangChain 에이전트 + 도구 + 시스템 프롬프트
assets/logo.png     # 로고
```

## 로컬 실행
```bash
pip install -r requirements.txt
# .streamlit/secrets.toml 에 OPENAI_API_KEY 입력
streamlit run app.py
```

## 기술 스택
Python 3.12 · Streamlit · pdfplumber · pandas · openpyxl · LangChain / LangGraph · OpenAI (gpt-4.1-mini)

