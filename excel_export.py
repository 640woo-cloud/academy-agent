"""채점 결과 → 엑셀(xlsx) 바이트 생성."""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from grading import GradingResult

HEAD = PatternFill("solid", fgColor="1F4E79")
SUB = PatternFill("solid", fgColor="DDEBF7")
OK = PatternFill("solid", fgColor="E2EFDA")
NG = PatternFill("solid", fgColor="FCE4D6")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center")


def _hdr(cell, fill=HEAD, color="FFFFFF"):
    cell.fill = fill
    cell.font = Font(bold=True, color=color)
    cell.alignment = CENTER
    cell.border = BOX


def build_excel(r: GradingResult) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "채점 결과"
    s = r.summary
    qnums = r.answer_key["문항"].tolist()

    # ---- 1) 전체 학생 성적 개요 -------------------------------------------
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    ws["A1"] = "전체 학생 성적 개요"
    _hdr(ws["A1"])
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")

    top3 = ", ".join(f"{t['문항']}번" for t in s["최다오답문항"])
    top3_detail = " / ".join(f"{t['문항']}번(오답 {t['오답자수']}명, 정답률 {t['정답률']}%)" for t in s["최다오답문항"])
    overview = [
        ("응시 인원", f"{s['응시인원']}명"),
        ("평균", s["평균"]),
        ("중앙값", s["중앙값"]),
        ("표준편차", s["표준편차"]),
        ("최고점 / 최저점", f"{s['최고점']} / {s['최저점']}"),
        ("가장 많이 틀린 문항 3개", top3),
        ("상세", top3_detail),
    ]
    for i, (k, v) in enumerate(overview, start=2):
        a = ws.cell(row=i, column=1, value=k)
        _hdr(a, SUB, "000000")
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=6)
        b = ws.cell(row=i, column=2, value=v)
        b.border = BOX
        b.alignment = Alignment(horizontal="left", vertical="center")

    # ---- 2) 학생별 점수 및 문항별 정답 여부 ---------------------------------
    start = len(overview) + 4
    ws.cell(row=start - 1, column=1, value="학생별 점수 및 문항별 정답 여부 (O: 정답, X: 오답)").font = Font(bold=True, size=12)
    headers = ["번호", "학생명", "점수", "맞은 개수", "순위"] + [f"{q}번" for q in qnums]
    for j, h in enumerate(headers, start=1):
        _hdr(ws.cell(row=start, column=j, value=h))

    # 정답/배점 참고 행
    ws.cell(row=start + 1, column=2, value="(정답/배점)")
    for j, q in enumerate(qnums, start=6):
        row = r.answer_key[r.answer_key["문항"] == q].iloc[0]
        c = ws.cell(row=start + 1, column=j, value=f"{int(row['정답'])}/{int(row['배점'])}")
        c.alignment = CENTER
        c.font = Font(italic=True, color="7F7F7F")

    corr = r.correct.set_index("학생명")
    for i, srow in enumerate(r.scores.itertuples(index=False), start=1):
        rr = start + 1 + i
        vals = [i, srow.학생명, srow.점수, srow.맞은개수, srow.순위]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=rr, column=j, value=v)
            c.border = BOX
            c.alignment = CENTER
        flags = corr.loc[srow.학생명]
        if hasattr(flags, "ndim") and flags.ndim > 1:  # 동명이인 방어
            flags = flags.iloc[0]
        for j, q in enumerate(qnums, start=6):
            ok = bool(flags[q])
            c = ws.cell(row=rr, column=j, value="O" if ok else "X")
            c.fill = OK if ok else NG
            c.alignment = CENTER
            c.border = BOX

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 14
    for j in range(3, len(headers) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 6 if j > 5 else 10
    ws.freeze_panes = ws.cell(row=start + 1, column=3)

    # ---- 3) 참고 시트: 문항 분석 -------------------------------------------
    ws2 = wb.create_sheet("문항 분석")
    cols = list(r.item_stats.columns)
    for j, h in enumerate(cols, start=1):
        _hdr(ws2.cell(row=1, column=j, value=h))
    for i, row in enumerate(r.item_stats.itertuples(index=False), start=2):
        for j, v in enumerate(row, start=1):
            c = ws2.cell(row=i, column=j, value=v.item() if hasattr(v, "item") else v)
            c.border = BOX
            c.alignment = CENTER
    for j in range(1, len(cols) + 1):
        ws2.column_dimensions[get_column_letter(j)].width = 11

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
