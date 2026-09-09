# -*- coding: utf-8 -*-
"""
05_build_report.py (v2)
v1은 "원본 문서 목표치"와 "생성 데이터 실측치"를 나란히 비교하는 표를 만들었습니다.
v2는 애초에 그 목표치대로 역산해서 만든 데이터가 아니므로(Kaggle 실측 확률 + 보수적
가정 확률에서 자연 발생한 값), 표의 기준 컬럼을 "Kaggle 실측 기준값 / 가정(명시)값"으로
바꾸고, 실측치는 03_validate_metrics.py와 동일한 방식으로 이 스크립트가 직접 재계산합니다.
"""
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
import pandas as pd
import numpy as np

FONT_NAME = "Arial"
thin = Side(style="thin", color="B7B7B7")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
header_font = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=10)
body_font = Font(name=FONT_NAME, size=9)
title_font = Font(name=FONT_NAME, bold=True, size=13)
section_font = Font(name=FONT_NAME, bold=True, size=11, color="1F4E78")

wb = openpyxl.Workbook()


def style_header_row(ws, row, n_cols):
    for col in range(1, n_cols + 1):
        c = ws.cell(row=row, column=col)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border


def style_body(ws, start_row, end_row, n_cols):
    for r in range(start_row, end_row + 1):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = body_font
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")


def merge_col(ws, col, first_row, last_row):
    r = first_row
    while r <= last_row:
        v = ws.cell(row=r, column=col).value
        r2 = r
        while r2 + 1 <= last_row and ws.cell(row=r2 + 1, column=col).value == v:
            r2 += 1
        if r2 > r:
            ws.merge_cells(start_row=r, start_column=col, end_row=r2, end_column=col)
        r = r2 + 1


def pct(a, b):
    return round(100 * a / b, 2) if b else None


# ===========================================================================
# 데이터 로드 & 지표 재계산 (03_validate_metrics.py와 동일 로직)
# ===========================================================================
events = pd.read_csv("../data/generated_v2/events_log.csv", parse_dates=["event_timestamp"], low_memory=False)
orders = pd.read_csv("../data/generated_v2/orders.csv", parse_dates=["purchase_date"])
users_master = pd.read_csv("../data/generated_v2/users_master.csv")

KAGGLE_VIEW_TO_CART = 0.0360
KAGGLE_CART_TO_PURCHASE = 0.3283

sessions = events[events.event_type == "session_start"][["session_id", "group"]].drop_duplicates()
cart_s = set(events[events.event_type == "add_to_cart"]["session_id"])
purch_s = set(events[events.event_type == "complete_purchase"]["session_id"])
sessions["cart"] = sessions.session_id.isin(cart_s)
sessions["purchase"] = sessions.session_id.isin(purch_s)

M = {}
for g in ["A", "B"]:
    sub = sessions[sessions.group == g]
    v2c = pct(sub.cart.sum(), len(sub))
    cart_sub = sub[sub.cart]
    c2p = pct(cart_sub.purchase.sum(), len(cart_sub))
    abandon = round(100 - c2p, 2) if c2p is not None else None
    dwell = events[(events.event_type == "view_item_end") & (events.group == g)].session_time.mean()

    vi = events[(events.event_type == "view_item") & (events.group == g)][["session_id", "event_timestamp"]]
    cp = events[(events.event_type == "complete_purchase") & (events.group == g)][["session_id", "event_timestamp"]]
    mrg = vi.merge(cp, on="session_id", suffixes=("_v", "_p"))
    decision_days = ((mrg.event_timestamp_p - mrg.event_timestamp_v).dt.total_seconds() / 86400).mean()

    nps_sub = events[(events.event_type == "nps_score") & (events.group == g)].nps_score.dropna()
    nps_val = round(100 * ((nps_sub >= 9).sum() / len(nps_sub) - (nps_sub <= 6).sum() / len(nps_sub)), 1) if len(nps_sub) else None

    alarm_n = len(events[(events.event_type == "reaction_require_alarm") & (events.group == g)])
    start_n = len(events[(events.event_type == "reaction_start") & (events.group == g)])
    complete_n = len(events[(events.event_type == "reaction_complete") & (events.group == g)])

    reco_click = events[(events.event_type == "select_item") & (events.source == "recommendation") & (events.group == g)]["session_id"].unique()
    reco_click_purchase = sum(1 for s in reco_click if s in purch_s)
    reco_cvr = pct(reco_click_purchase, len(reco_click))

    active_u = events[(events.event_type == "session_start") & (events.group == g)]["user_id"].nunique()
    reco_screen_u = events[
        (events.group == g) & (((events.event_type == "view_item") & (events.entry_source == "recommendation")) | (events.event_type == "recommendation_view"))
    ]["user_id"].nunique()
    comp_u = events[(events.event_type == "view_comparison") & (events.group == g)]["user_id"].nunique()

    M[g] = {
        "view_to_cart": v2c, "cart_to_purchase": c2p, "cart_abandon": abandon,
        "dwell": round(dwell, 1) if pd.notna(dwell) else None,
        "decision_days": round(decision_days, 2) if pd.notna(decision_days) else None,
        "nps": nps_val,
        "reaction_start_rate": pct(start_n, alarm_n),
        "reaction_complete_rate": pct(complete_n, start_n),
        "reco_cvr": reco_cvr,
        "reco_screen_entry_rate": pct(reco_screen_u, active_u),
        "compare_usage_rate": pct(comp_u, active_u),
        "n_orders": (orders.group == g).sum(),
        # --- 판정(P(A>B))용 분자/분모 원자료 ---
        "_num_purchase": int(sub.purchase.sum()), "_den_session": int(len(sub)),
        "_num_cart": int(sub.cart.sum()),
        "_num_reco_purchase": int(reco_click_purchase), "_den_reco_click": int(len(reco_click)),
        "_num_react_complete": int(complete_n), "_den_alarm": int(alarm_n),
        "_num_react_check": int(len(events[(events.event_type == "reaction_check") & (events.group == g)])),
        "_num_promoter": int((nps_sub >= 9).sum()), "_den_nps": int(len(nps_sub)),
        "_num_repeat_buyer": int((orders[orders.group == g].groupby("user_id").size() >= 2).sum()),
        "_den_users": int((users_master.group == g).sum()),
    }

# ===========================================================================
# 시트0: 개요
# ===========================================================================
ws0 = wb.active
ws0.title = "개요"
ws0["B2"] = "골라주개냥(우지빌) A/B 테스트 가상 운영 데이터 v2 — 분석 요약"
ws0["B2"].font = title_font

overview_lines = [
    "",
    "생성 개요",
    "- 기간: 2026-09-08 ~ 2026-12-06 (90일)",
    "- 대상: A/B 각 9,500명 (총 19,000명), 90일간 순차 유입",
    f"- 생성된 주문 수: A그룹 {M['A']['n_orders']}건 / B그룹 {M['B']['n_orders']}건",
    "- 검증 가설 3개: 선택 피로도 해소 / 서비스 충성도 / 유저 데이터 확보",
    "",
    "v1 대비 핵심 변경 사항",
    "- 상품 마스터를 사내 '반려동물 상품 분류 체계' 참조표 기반으로 확장",
    "  (category/subcategory, 건강기능 코드, 원재료·알레르겐, 영양성분 정규화 테이블 3종 추가)",
    "- '조회 시 100% 장바구니 담기' 가정을 제거하고, 조회->장바구니 / 장바구니->구매",
    "  두 확률을 공개 이커머스 이벤트 로그(Kaggle: REES46/Cosmetics Shop/RetailRocket)에서",
    "  직접 집계한 중앙값으로 대체 (조회->장바구니 3.60%, 장바구니->구매 32.83%)",
    "- A/B 처치 효과는 꾸며낸 목표치가 아니라, 일반적인 개인화 추천 전환율 개선",
    "  업계 통계 중 가장 보수적인 값(+15% 상대 개선)을 단일 가정 계수로 일괄 적용",
    "- A그룹 '추천' 진입 경로에 한해 알레르겐 배제 + 관심 건강기능 매칭 개인화 로직 반영",
    "",
    "결과 규모에 대한 유의사항",
    "- 위 두 확률을 실측대로 적용한 결과, v1(주문 약 1.2만 건) 대비 v2 생성 주문 수가",
    f"  크게 줄었습니다(v2: A {M['A']['n_orders']}건 / B {M['B']['n_orders']}건). 이는 v1이 전환",
    "  규모를 과대 추정했던 편향을 제거한 결과이며, 실제 이커머스 조회->구매 전환율에",
    "  더 가깝습니다. 다만 표본이 작아 N일 재구매율 등 일부 지표는 변동폭이 큽니다.",
    "",
    "시트 구성",
    "1. AB지표_비교 — Kaggle 실측/가정(명시) 기준값과 실제 생성 데이터 지표 비교",
    "2. 판정결과 — 베이지안 P(A>B) 기준 A/B 판정 (주 지표 3개 + 보조 지표 4개)",
    "3. 퍼널_구매여정 — 가설1 세션 단위 퍼널 (진입→탐색→장바구니→구매)",
    "4. 퍼널_반응입력여정 — 가설3 주문 단위 퍼널 (알람→확인→시작→완료→재진입)",
    "5. 코호트_재구매율 — 가입 주차별 코호트의 주차별 구매 유저 비율(%)",
]
for i, line in enumerate(overview_lines, start=3):
    c = ws0.cell(row=i, column=2, value=line)
    c.font = Font(name=FONT_NAME, size=10, bold=(line in ("생성 개요", "v1 대비 핵심 변경 사항", "결과 규모에 대한 유의사항", "시트 구성")))
ws0.column_dimensions["B"].width = 100

# ===========================================================================
# 시트1: AB지표_비교
# ===========================================================================
ws1 = wb.create_sheet("AB지표_비교")
headers1 = ["가설", "지표", "그룹", "기준값 (출처)", "생성 데이터 실측치", "비고"]
for col, h in enumerate(headers1, start=1):
    ws1.cell(row=1, column=col, value=h)
style_header_row(ws1, 1, len(headers1))

metric_rows = [
    ("가설1: 선택 피로도 해소", "조회->장바구니", "A", "3.60% (Kaggle 3개 데이터셋 중앙값) +15%", f"{M['A']['view_to_cart']}%", "personalized(추천+A) 경로만 +15% 가정 반영"),
    ("가설1: 선택 피로도 해소", "조회->장바구니", "B", "3.60% (Kaggle 3개 데이터셋 중앙값)", f"{M['B']['view_to_cart']}%", "처치 없음, Kaggle 값과 근접"),
    ("가설1: 선택 피로도 해소", "장바구니->구매", "A", "32.83% (Kaggle 중앙값) +15%(개인화/비교 시)", f"{M['A']['cart_to_purchase']}%", "-"),
    ("가설1: 선택 피로도 해소", "장바구니->구매", "B", "32.83% (Kaggle 중앙값)", f"{M['B']['cart_to_purchase']}%", "-"),
    ("가설1: 선택 피로도 해소", "장바구니 이탈률", "A", "위 두 확률의 자연 결과 (목표로 역산하지 않음)", f"{M['A']['cart_abandon']}%", "v1의 40%/56%대 임의 목표치 폐기"),
    ("가설1: 선택 피로도 해소", "장바구니 이탈률", "B", "위 두 확률의 자연 결과", f"{M['B']['cart_abandon']}%", "-"),
    ("가설1: 선택 피로도 해소", "상품상세 체류시간", "A", "43초 x1.15 (가정(명시), Kaggle 검증 불가)", f"{M['A']['dwell']}초", "세션 연속성 없는 샘플이라 실측 불가"),
    ("가설1: 선택 피로도 해소", "상품상세 체류시간", "B", "43초 (가정(명시), v1 승계)", f"{M['B']['dwell']}초", "-"),
    ("가설1: 선택 피로도 해소", "구매결정 소요시간", "A", "2.85일 /1.15 (가정(명시))", f"{M['A']['decision_days']}일", "-"),
    ("가설1: 선택 피로도 해소", "구매결정 소요시간", "B", "2.85일 (가정(명시), v1 승계)", f"{M['B']['decision_days']}일", "-"),
    ("가설2: 서비스 충성도", "NPS", "A", "가정(명시): promoter/detractor 각 +-15%", f"{M['A']['nps']}점", "표본 작음(주문 수에 비례)"),
    ("가설2: 서비스 충성도", "NPS", "B", "가정(명시): promoter 32%/detractor 7%, v1 승계", f"{M['B']['nps']}점", "-"),
    ("가설2: 서비스 충성도", "맞춤 추천 상품 CVR", "A", "계획서 V1 신규: 초기 3.3%/목표 5% (참고치, 역산 목표 아님)", f"{M['A']['reco_cvr']}%", "select_item(reco)->동일세션 결제완료"),
    ("가설2: 서비스 충성도", "맞춤 추천 상품 CVR", "B", "계획서 V1 신규 (참고치)", f"{M['B']['reco_cvr']}%", "-"),
    ("가설2: 서비스 충성도", "추천 상품 화면 진입률", "A", "계획서 V1 신규: 초기 35~40%/목표 60% (참고치)", f"{M['A']['reco_screen_entry_rate']}%", "활성유저 기준, 90일 누적이라 목표 상회"),
    ("가설2: 서비스 충성도", "추천 상품 화면 진입률", "B", "계획서 V1 신규 (참고치)", f"{M['B']['reco_screen_entry_rate']}%", "-"),
    ("가설2: 서비스 충성도", "비교 기능 사용률", "A", "계획서 V1 개정(활성유저 기준): 초기 15~20%/목표 30~35% (참고치)", f"{M['A']['compare_usage_rate']}%", "90일 누적이라 목표 상회"),
    ("가설2: 서비스 충성도", "비교 기능 사용률", "B", "계획서 V1 개정 (참고치)", f"{M['B']['compare_usage_rate']}%", "-"),
    ("가설3: 유저 데이터 확보", "반응입력 시작률", "A", "18% x1.15 (가정(명시))", f"{M['A']['reaction_start_rate']}%", "-"),
    ("가설3: 유저 데이터 확보", "반응입력 시작률", "B", "18% (가정(명시), v1 승계)", f"{M['B']['reaction_start_rate']}%", "-"),
    ("가설3: 유저 데이터 확보", "반응입력 완료율", "A", "78% x1.15, cap 97% (가정(명시))", f"{M['A']['reaction_complete_rate']}%", "-"),
    ("가설3: 유저 데이터 확보", "반응입력 완료율", "B", "78% (가정(명시), v1 승계)", f"{M['B']['reaction_complete_rate']}%", "-"),
]
for r_idx, row in enumerate(metric_rows, start=2):
    for c_idx, val in enumerate(row, start=1):
        ws1.cell(row=r_idx, column=c_idx, value=val)
style_body(ws1, 2, 1 + len(metric_rows), len(headers1))
merge_col(ws1, 1, 2, 1 + len(metric_rows))
merge_col(ws1, 2, 2, 1 + len(metric_rows))
widths1 = {1: 26, 2: 18, 3: 6, 4: 44, 5: 18, 6: 40}
for col, w in widths1.items():
    ws1.column_dimensions[get_column_letter(col)].width = w
ws1.freeze_panes = "A2"

# ===========================================================================
# 시트1-2: 판정결과 (베이지안 P(A>B))
#   docs/가설1_가설2_가설3_퍼널_분석_리포트.md 2.2절 판정 규칙과 동일 기준:
#   - 규칙1: 무정보 사전분포 Beta(1,1) 기준 P(A>B) >= 90% 이면 통과
#   - 규칙3: 가설당 주 지표 1개만 판정에 사용, 나머지는 보조(참고)
# ===========================================================================
_PAB_RNG = np.random.default_rng(20260909)  # 재현성 고정


def p_a_better(xa, na, xb, nb, draws=200_000):
    """Beta(1,1) 사전분포에서 P(A>B)를 몬테카를로로 추정."""
    if not na or not nb:
        return None
    sa = _PAB_RNG.beta(1 + xa, 1 + na - xa, draws)
    sb = _PAB_RNG.beta(1 + xb, 1 + nb - xb, draws)
    return round(100 * float((sa > sb).mean()), 1)


JUDGE_METRICS = [
    ("주 지표", "가설1: 선택 피로도 해소", "구매전환율(진입 대비)", "_num_purchase", "_den_session"),
    ("주 지표", "가설2: 서비스 충성도", "맞춤 추천 재구매 CVR", "_num_reco_purchase", "_den_reco_click"),
    ("주 지표", "가설3: 유저 데이터 확보", "반응 입력완료율(알람 대비)", "_num_react_complete", "_den_alarm"),
    ("보조 지표", "가설1: 선택 피로도 해소", "장바구니전환율(진입 대비)", "_num_cart", "_den_session"),
    ("보조 지표", "가설2: 서비스 충성도", "NPS 추천자 비율", "_num_promoter", "_den_nps"),
    ("보조 지표", "가설2: 서비스 충성도", "2회+ 구매 유저 비율(전체 유저)", "_num_repeat_buyer", "_den_users"),
    ("보조 지표", "가설3: 유저 데이터 확보", "알람 확인율", "_num_react_check", "_den_alarm"),
]

ws1b = wb.create_sheet("판정결과")
ws1b["A1"] = "판정 기준: 베이지안 사후확률 P(A>B) >= 90% (무정보 사전분포 Beta(1,1)) — 주 지표만 판정에 사용, 보조 지표는 방향 참고"
ws1b["A1"].font = Font(name=FONT_NAME, size=9, italic=True, color="555555")
ws1b.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)

headers1b = ["구분", "가설", "지표", "A (전환/모수)", "A 비율", "B (전환/모수)", "B 비율", "P(A>B)", "판정"]
for col, h in enumerate(headers1b, start=1):
    ws1b.cell(row=2, column=col, value=h)
style_header_row(ws1b, 2, len(headers1b))

judge_rows = []
for kind, hypo, label, num_key, den_key in JUDGE_METRICS:
    xa, na = M["A"][num_key], M["A"][den_key]
    xb, nb = M["B"][num_key], M["B"][den_key]
    pab = p_a_better(xa, na, xb, nb)
    if kind == "주 지표":
        verdict = "채택" if (pab is not None and pab >= 90) else "미달"
    else:
        verdict = "방향 일치" if (pab is not None and pab >= 90) else "판단 보류"
    judge_rows.append([kind, hypo, label, f"{xa}/{na}", f"{pct(xa, na)}%",
                        f"{xb}/{nb}", f"{pct(xb, nb)}%",
                        f"{pab}%" if pab is not None else "-", verdict])

for r_idx, row in enumerate(judge_rows, start=3):
    for c_idx, val in enumerate(row, start=1):
        ws1b.cell(row=r_idx, column=c_idx, value=val)
style_body(ws1b, 3, 2 + len(judge_rows), len(headers1b))
merge_col(ws1b, 1, 3, 2 + len(judge_rows))
for col, w in {1: 10, 2: 24, 3: 30, 4: 16, 5: 10, 6: 16, 7: 10, 8: 10, 9: 12}.items():
    ws1b.column_dimensions[get_column_letter(col)].width = w
ws1b.freeze_panes = "A3"

_note_row = 4 + len(judge_rows)
for _i, _line in enumerate([
    "※ 주의사항",
    "- 지표를 여러 개 검정하면 그중 하나가 우연히 기준을 넘을 확률이 올라갑니다(90% 기준 7개 검정 시 최소 1건 거짓양성 확률 52%).",
    "  그래서 가설당 '주 지표' 1개만 판정에 사용하고, 보조 지표는 방향 참고로만 씁니다.",
    "- 가설3은 주 지표 표본(알람노출 주문)이 작아 효과크기 추정 구간이 넓습니다. 매출 임팩트 등 정량 계산에는 구간 하단을 보수적으로 쓰세요.",
    "- 자세한 판정 규칙과 근거는 docs/가설1_가설2_가설3_퍼널_분석_리포트.md 2.2~2.4절 참고.",
], start=0):
    c = ws1b.cell(row=_note_row + _i, column=1, value=_line)
    c.font = Font(name=FONT_NAME, size=9, bold=(_i == 0), color="555555")

# ===========================================================================
# 시트2: 퍼널_구매여정
# ===========================================================================
funnel1 = pd.read_csv("../data/generated_v2/funnel1_purchase_journey.csv")
ws2 = wb.create_sheet("퍼널_구매여정")
for col, h in enumerate(funnel1.columns, start=1):
    ws2.cell(row=1, column=col, value=h)
style_header_row(ws2, 1, len(funnel1.columns))
for r_idx, row in enumerate(funnel1.itertuples(index=False), start=2):
    for c_idx, val in enumerate(row, start=1):
        ws2.cell(row=r_idx, column=c_idx, value=val)
style_body(ws2, 2, 1 + len(funnel1), len(funnel1.columns))
for col in range(1, len(funnel1.columns) + 1):
    ws2.column_dimensions[get_column_letter(col)].width = 18
ws2.column_dimensions["A"].width = 22

chart1 = BarChart()
chart1.title = "구매 여정 퍼널 (세션 수)"
chart1.y_axis.title = "세션 수"
data = Reference(ws2, min_col=2, max_col=3, min_row=1, max_row=1 + len(funnel1))
cats = Reference(ws2, min_col=1, min_row=2, max_row=1 + len(funnel1))
chart1.add_data(data, titles_from_data=True)
chart1.set_categories(cats)
ws2.add_chart(chart1, "H2")

# ===========================================================================
# 시트3: 퍼널_반응입력여정
# ===========================================================================
funnel2 = pd.read_csv("../data/generated_v2/funnel2_reaction_journey.csv")
ws3 = wb.create_sheet("퍼널_반응입력여정")
for col, h in enumerate(funnel2.columns, start=1):
    ws3.cell(row=1, column=col, value=h)
style_header_row(ws3, 1, len(funnel2.columns))
for r_idx, row in enumerate(funnel2.itertuples(index=False), start=2):
    for c_idx, val in enumerate(row, start=1):
        ws3.cell(row=r_idx, column=c_idx, value=val)
style_body(ws3, 2, 1 + len(funnel2), len(funnel2.columns))
for col in range(1, len(funnel2.columns) + 1):
    ws3.column_dimensions[get_column_letter(col)].width = 18
ws3.column_dimensions["A"].width = 18

chart2 = BarChart()
chart2.title = "반응입력 여정 퍼널 (주문 수)"
chart2.y_axis.title = "주문 수"
data2 = Reference(ws3, min_col=2, max_col=3, min_row=1, max_row=1 + len(funnel2))
cats2 = Reference(ws3, min_col=1, min_row=2, max_row=1 + len(funnel2))
chart2.add_data(data2, titles_from_data=True)
chart2.set_categories(cats2)
ws3.add_chart(chart2, "H2")

# ===========================================================================
# 시트4: 코호트_재구매율
# ===========================================================================
cohort_A = pd.read_csv("../data/generated_v2/cohort_A_repurchase_pct.csv")
cohort_B = pd.read_csv("../data/generated_v2/cohort_B_repurchase_pct.csv")

ws4 = wb.create_sheet("코호트_재구매율")
ws4.cell(row=1, column=1, value="A그룹 — 가입 주차별 코호트 x 경과 주차별 구매 유저 비율(%)")
ws4["A1"].font = section_font
for col, h in enumerate(cohort_A.columns, start=1):
    ws4.cell(row=2, column=col, value=h if h != "signup_week" else "가입주차")
style_header_row(ws4, 2, len(cohort_A.columns))
for r_idx, row in enumerate(cohort_A.itertuples(index=False), start=3):
    for c_idx, val in enumerate(row, start=1):
        ws4.cell(row=r_idx, column=c_idx, value=val)
style_body(ws4, 3, 2 + len(cohort_A), len(cohort_A.columns))

start_row_b = 2 + len(cohort_A) + 3
ws4.cell(row=start_row_b, column=1, value="B그룹 — 가입 주차별 코호트 x 경과 주차별 구매 유저 비율(%)")
ws4.cell(row=start_row_b, column=1).font = section_font
for col, h in enumerate(cohort_B.columns, start=1):
    ws4.cell(row=start_row_b + 1, column=col, value=h if h != "signup_week" else "가입주차")
style_header_row(ws4, start_row_b + 1, len(cohort_B.columns))
for r_idx, row in enumerate(cohort_B.itertuples(index=False), start=start_row_b + 2):
    for c_idx, val in enumerate(row, start=1):
        ws4.cell(row=r_idx, column=c_idx, value=val)
style_body(ws4, start_row_b + 2, start_row_b + 1 + len(cohort_B), len(cohort_B.columns))

for col in range(1, len(cohort_A.columns) + 1):
    ws4.column_dimensions[get_column_letter(col)].width = 12
ws4.column_dimensions["A"].width = 14

wb.save("../data/generated_v2/AB테스트_가상데이터_분석요약_v2.xlsx")
print("saved")
