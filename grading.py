"""채점 엔진: 정답 PDF 파싱 → OMR 채점 → 통계 계산.

정답/배점은 코드에 하드코딩하지 않고, 업로드된 정답 PDF에서만 추출한다.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pdfplumber

CIRCLED = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}


# ---------------------------------------------------------------------------
# 1. 정답 PDF 파싱
# ---------------------------------------------------------------------------
def parse_answer_pdf(file_bytes: bytes) -> pd.DataFrame:
    """정답표 PDF에서 (문항번호, 정답, 배점)을 추출한다."""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    rows = _extract_key_rows(text)

    if not rows:
        raise ValueError("정답 PDF에서 '문항번호-정답-배점'을 찾지 못했습니다. 정답표 PDF가 맞는지 확인해 주세요.")

    df = pd.DataFrame(
        [(n, a, p) for n, (a, p) in sorted(rows.items())],
        columns=["문항", "정답", "배점"],
    )
    expected = set(range(1, df["문항"].max() + 1))
    missing = sorted(expected - set(df["문항"]))
    if missing:
        raise ValueError(f"정답 PDF에서 일부 문항을 찾지 못했습니다: {missing}")
    return df


def _extract_key_rows(text: str) -> dict[int, tuple[int, int]]:
    """정답표 텍스트에서 {문항: (정답, 배점)}을 뽑는다.
    1순위: 동그라미 숫자(①~⑤) 정답 / 2순위: 일반 숫자(1~5) 정답."""
    circled = re.compile(r"(?<!\d)(\d{1,2})\s*([①②③④⑤])\s*(\d)(?!\d)")
    rows = {int(n): (CIRCLED[a], int(p)) for n, a, p in circled.findall(text)}
    if rows:
        return rows
    # "1 3 2  13 2 3 ..." 처럼 (문항 정답 배점) 세 숫자가 반복되는 줄만 사용
    plain = re.compile(r"(?<!\d)(\d{1,2})\s+([1-5])\s+([1-5])(?!\d)")
    for line in text.splitlines():
        nums = re.findall(r"\d+", line)
        if len(nums) < 3 or len(nums) % 3:
            continue
        for n, a, p in plain.findall(line):
            rows.setdefault(int(n), (int(a), int(p)))
    return rows


# ---------------------------------------------------------------------------
# 2. 문제지 PDF 파싱 (유사 문제 생성용 원문 추출)
# ---------------------------------------------------------------------------
def parse_question_pdf(file_bytes: bytes) -> dict[int, str]:
    """문제지 PDF(2단 편집)를 좌/우 단으로 나눠 읽고 문항별 텍스트를 반환한다."""
    chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            w, h = page.width, page.height
            for box in ((0, 0, w / 2, h), (w / 2, 0, w, h)):
                chunks.append(page.crop(box).extract_text() or "")
    text = "\n".join(chunks)
    text = re.sub(r"이 문제지에 관한 저작권은.*", "", text)

    starts = [(int(m.group(1)), m.start()) for m in re.finditer(r"(?m)^\s*(\d{1,2})\.\s", text)]
    questions: dict[int, str] = {}
    expected = 1
    seq = []
    for num, pos in starts:  # 1,2,3… 순서대로 등장하는 것만 문항 시작으로 인정
        if num == expected:
            seq.append((num, pos))
            expected += 1
    for i, (num, pos) in enumerate(seq):
        end = seq[i + 1][1] if i + 1 < len(seq) else len(text)
        questions[num] = text[pos:end].strip()

    # "[41～42] 다음 글을 읽고…" 처럼 공통 지문이 앞에 있는 세트 문항 처리
    for m in re.finditer(r"\[(\d{1,2})\s*[～~\-]\s*(\d{1,2})\]", text):
        a, b = int(m.group(1)), int(m.group(2))
        if a in questions:
            a_pos = dict(seq).get(a, m.end())
            passage = text[m.start():a_pos].strip()
            for q in range(a, b + 1):
                if q in questions and passage and passage not in questions[q]:
                    questions[q] = passage + "\n\n" + questions[q]
    return questions


# ---------------------------------------------------------------------------
# 3. OMR 결과 읽기
# ---------------------------------------------------------------------------
def read_omr(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
    df.columns = [str(c).strip() for c in df.columns]
    q_cols = [c for c in df.columns if re.fullmatch(r"[Qq]?\s*0*\d{1,2}", c) or re.fullmatch(r"\d{1,2}번", c)]
    name_col = next((c for c in df.columns if c not in q_cols), None)
    if name_col is None or not q_cols:
        raise ValueError("OMR 파일에서 학생명 열과 문항(Q01…) 열을 찾지 못했습니다.")
    rename = {c: int(re.sub(r"\D", "", c)) for c in q_cols}
    out = df[[name_col] + q_cols].rename(columns={name_col: "학생명", **rename})
    out["학생명"] = out["학생명"].astype(str).str.strip()
    return out


# ---------------------------------------------------------------------------
# 4. 채점 + 통계
# ---------------------------------------------------------------------------
@dataclass
class GradingResult:
    answer_key: pd.DataFrame          # 문항, 정답, 배점
    omr: pd.DataFrame                 # 학생명, 1..N (학생 응답)
    correct: pd.DataFrame             # 학생명 × 문항 (bool)
    scores: pd.DataFrame              # 학생명, 점수, 맞은개수, 순위
    item_stats: pd.DataFrame          # 문항별 정답률·오답수·선지분포
    summary: dict
    questions: dict[int, str] = field(default_factory=dict)


def grade(answer_key: pd.DataFrame, omr: pd.DataFrame, questions: dict[int, str] | None = None) -> GradingResult:
    qnums = answer_key["문항"].tolist()
    missing = [q for q in qnums if q not in omr.columns]
    if missing:
        raise ValueError(f"OMR 파일에 없는 문항이 있습니다: {missing}")

    key = answer_key.set_index("문항")
    resp = omr[qnums].apply(pd.to_numeric, errors="coerce")
    correct = resp.eq(key["정답"], axis=1)   # 무응답/중복표기(NaN) → 오답
    correct.insert(0, "학생명", omr["학생명"].values)

    pts = correct[qnums].astype(int).mul(key["배점"], axis=1)
    scores = pd.DataFrame({
        "학생명": omr["학생명"].values,
        "점수": pts.sum(axis=1).astype(int).values,
        "맞은개수": correct[qnums].sum(axis=1).astype(int).values,
    })
    scores["순위"] = scores["점수"].rank(ascending=False, method="min").astype(int)

    n = len(scores)
    wrong_cnt = (~correct[qnums]).sum()
    item = pd.DataFrame({
        "문항": qnums,
        "정답": key["정답"].values,
        "배점": key["배점"].values,
        "정답자수": correct[qnums].sum().values,
        "오답자수": wrong_cnt.values,
    })
    item["정답률(%)"] = (item["정답자수"] / n * 100).round(1)
    for c in range(1, 6):
        item[f"{c}번 선택"] = [(resp[q] == c).sum() for q in qnums]
    item["무응답/기타"] = [resp[q].isna().sum() + (~resp[q].isin([1, 2, 3, 4, 5]) & resp[q].notna()).sum() for q in qnums]

    top_wrong = item.sort_values(["오답자수", "문항"], ascending=[False, True]).head(3)
    s = scores["점수"]
    summary = {
        "응시인원": n,
        "총문항수": len(qnums),
        "만점": int(key["배점"].sum()),
        "평균": round(float(s.mean()), 2),
        "중앙값": float(s.median()),
        "표준편차": round(float(s.std(ddof=0)), 2),           # 모집단 표준편차
        "표준편차_표본": round(float(s.std(ddof=1)), 2) if n > 1 else 0.0,
        "최고점": int(s.max()),
        "최저점": int(s.min()),
        "최다오답문항": [
            {"문항": int(r["문항"]), "오답자수": int(r["오답자수"]), "정답률": float(r["정답률(%)"])}
            for _, r in top_wrong.iterrows()
        ],
    }
    return GradingResult(answer_key, omr, correct, scores, item, summary, questions or {})


# ---------------------------------------------------------------------------
# 5. 학생 찾기 (예: "87번 학생", "87", "900학생")
# ---------------------------------------------------------------------------
def find_student(result: GradingResult, query: str) -> pd.DataFrame:
    q = str(query).strip()
    sc = result.scores
    exact = sc[sc["학생명"] == q]
    if not exact.empty:
        return exact
    digits = re.findall(r"\d+", q)
    if digits:
        target = int(digits[0])
        name_nums = sc["학생명"].str.extract(r"(\d+)")[0]
        hit = sc[pd.to_numeric(name_nums, errors="coerce") == target]
        if not hit.empty:
            return hit
        # 학생명에 해당 번호가 없으면 업로드 순서상 N번째 학생으로 해석 (예: 학생명이 900학생~ 인 경우)
        if 1 <= target <= len(sc):
            return sc.iloc[[target - 1]].assign(조회방식=f"학생명에 {target}이(가) 없어 명단 {target}번째 학생으로 조회")
    return sc[sc["학생명"].str.contains(re.escape(q), na=False)] if q else sc.iloc[0:0]