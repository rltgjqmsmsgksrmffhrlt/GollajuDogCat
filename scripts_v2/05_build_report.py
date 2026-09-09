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
    "- 대상: A/B 각 2,500명 (총 5,000명), 90일간 순차 유입",
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
    "2. 퍼널_구매여정 — 가설1 세션 단위 퍼널 (진입→탐색→장바구니→구매)",
    "3. 퍼널_반응입력여정 — 가설3 주문 단위 퍼널 (알람→확인→시작→완료→재진입)",
    "4. 코호트_재구매율 — 가입 주차별 코호트의 주차별 구매 유저 비율(%)",
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
