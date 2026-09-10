# -*- coding: utf-8 -*-
"""
04_funnel_cohort_analysis.py (v2, generated_v2 대상)
- 퍼널 분석: 가설1(구매여정), 가설3(반응입력여정) 단계별 전환
- 코호트 분석: 가입 주차별 코호트의 N주 리텐션(재구매 세션 발생 여부)
"""
import pandas as pd
import numpy as np

events = pd.read_csv("../data/generated_v2/events_log.csv", parse_dates=["event_timestamp"], low_memory=False)
orders = pd.read_csv("../data/generated_v2/orders.csv", parse_dates=["purchase_date"])
users = pd.read_csv("../data/generated_v2/users_master.csv", parse_dates=["signup_date"])

# ===========================================================================
# 퍼널 1: 가설1 구매 여정 (세션 단위) session_start -> view_item -> add_to_cart -> complete_purchase
# ===========================================================================
def funnel_purchase(group):
    sessions = events[events.group == group]["session_id"].unique()
    step_sessions = {
        "1_session_start": set(events[(events.group==group) & (events.event_type=="session_start")]["session_id"]),
        "2_view_item": set(events[(events.group==group) & (events.event_type=="view_item")]["session_id"]),
        "3_add_to_cart": set(events[(events.group==group) & (events.event_type=="add_to_cart")]["session_id"]),
        "4_complete_purchase": set(events[(events.group==group) & (events.event_type=="complete_purchase")]["session_id"]),
    }
    counts = {k: len(v) for k, v in step_sessions.items()}
    return counts

funnel1_A = funnel_purchase("A")
funnel1_B = funnel_purchase("B")

funnel1_df = pd.DataFrame({
    "step": list(funnel1_A.keys()),
    "A_count": list(funnel1_A.values()),
    "B_count": list(funnel1_B.values()),
})
funnel1_df["A_pct_of_start"] = (funnel1_df.A_count / funnel1_df.A_count.iloc[0] * 100).round(1)
funnel1_df["B_pct_of_start"] = (funnel1_df.B_count / funnel1_df.B_count.iloc[0] * 100).round(1)
funnel1_df["A_step_conversion"] = (funnel1_df.A_count / funnel1_df.A_count.shift(1) * 100).round(1)
funnel1_df["B_step_conversion"] = (funnel1_df.B_count / funnel1_df.B_count.shift(1) * 100).round(1)

print("="*70)
print("퍼널1: 선택 피로도 해소 - 구매 여정 (세션 기준)")
print("="*70)
print(funnel1_df.to_string(index=False))
print()

# ===========================================================================
# 퍼널 2: 가설3 반응입력 여정 (주문 단위)
# reaction_require_alarm -> reaction_check -> reaction_start -> reaction_complete -> recommendation_view(재진입)
# ===========================================================================
def funnel_reaction(group):
    orders_g = orders[orders.group == group]["order_id"].unique()
    step_orders = {
        "1_alarm_노출": set(events[(events.group==group) & (events.event_type=="reaction_require_alarm")]["order_id"]),
        "2_알람확인": set(events[(events.group==group) & (events.event_type=="reaction_check")]["order_id"]),
        "3_입력시작": set(events[(events.group==group) & (events.event_type=="reaction_start")]["order_id"]),
        "4_입력완료": set(events[(events.group==group) & (events.event_type=="reaction_complete")]["order_id"]),
        "5_재진입(추천화면)": set(events[(events.group==group) & (events.event_type=="recommendation_view")]["order_id"]),
    }
    counts = {k: len(v) for k, v in step_orders.items()}
    return counts

funnel2_A = funnel_reaction("A")
funnel2_B = funnel_reaction("B")

funnel2_df = pd.DataFrame({
    "step": list(funnel2_A.keys()),
    "A_count": list(funnel2_A.values()),
    "B_count": list(funnel2_B.values()),
})
funnel2_df["A_pct_of_start"] = (funnel2_df.A_count / funnel2_df.A_count.iloc[0] * 100).round(1)
funnel2_df["B_pct_of_start"] = (funnel2_df.B_count / funnel2_df.B_count.iloc[0] * 100).round(1)
funnel2_df["A_step_conversion"] = (funnel2_df.A_count / funnel2_df.A_count.shift(1) * 100).round(1)
funnel2_df["B_step_conversion"] = (funnel2_df.B_count / funnel2_df.B_count.shift(1) * 100).round(1)

print("="*70)
print("퍼널2: 유저 데이터 확보 - 반응입력 여정 (주문 기준)")
print("="*70)
print(funnel2_df.to_string(index=False))
print()

# ===========================================================================
# 코호트 분석: 가입 주차별 코호트 x N주차 재구매(활성) 여부
# ===========================================================================
users["signup_week"] = users["signup_date"].dt.to_period("W").apply(lambda r: r.start_time)
orders_u = orders.merge(users[["user_id", "signup_week"]], on="user_id", how="left")
orders_u["order_week"] = orders_u["purchase_date"].dt.to_period("W").apply(lambda r: r.start_time)
orders_u["week_index"] = ((orders_u["order_week"] - orders_u["signup_week"]).dt.days // 7)

def build_cohort_table(group):
    sub = orders_u[orders_u.group == group]
    cohort_users = users[users.group == group].groupby("signup_week")["user_id"].nunique()
    active = sub.groupby(["signup_week", "week_index"])["user_id"].nunique().reset_index()
    pivot = active.pivot(index="signup_week", columns="week_index", values="user_id").fillna(0)
    pivot_pct = pivot.div(cohort_users, axis=0) * 100
    return pivot.astype(int), pivot_pct.round(1), cohort_users

cohort_A_cnt, cohort_A_pct, cohort_A_size = build_cohort_table("A")
cohort_B_cnt, cohort_B_pct, cohort_B_size = build_cohort_table("B")

print("="*70)
print("코호트 분석 [A그룹]: 가입 주차별 코호트 크기")
print("="*70)
print(cohort_A_size.to_string())
print()
print("코호트 분석 [A그룹]: 주차별 구매 유저 비율(%) - week_index=0은 가입 첫 주")
print(cohort_A_pct.iloc[:, :8].to_string())  # 최대 8주차까지만 표시
print()

print("="*70)
print("코호트 분석 [B그룹]: 가입 주차별 코호트 크기")
print("="*70)
print(cohort_B_size.to_string())
print()
print("코호트 분석 [B그룹]: 주차별 구매 유저 비율(%)")
print(cohort_B_pct.iloc[:, :8].to_string())

# Save all outputs
funnel1_df.to_csv("../data/generated_v2/funnel1_purchase_journey.csv", index=False, encoding="utf-8-sig")
funnel2_df.to_csv("../data/generated_v2/funnel2_reaction_journey.csv", index=False, encoding="utf-8-sig")
cohort_A_pct.to_csv("../data/generated_v2/cohort_A_repurchase_pct.csv", encoding="utf-8-sig")
cohort_B_pct.to_csv("../data/generated_v2/cohort_B_repurchase_pct.csv", encoding="utf-8-sig")
cohort_A_cnt.to_csv("../data/generated_v2/cohort_A_size.csv", encoding="utf-8-sig")
cohort_B_cnt.to_csv("../data/generated_v2/cohort_B_size.csv", encoding="utf-8-sig")

print()
print("Funnel & Cohort analysis saved.")

# ===========================================================================
# 가설별 코호트 분석 (가입 후 경과 주차 기준)
# ---------------------------------------------------------------------------
# 위의 재구매 코호트가 "가입주 x 경과주" 격자라면, 여기서는 같은 격자를
# 가설별 주 지표(분자/분모)에 적용한다. 격자 전체는 세 가설 모두 셀당 표본이
# 판정 불가 수준이므로(density 표 참고), 실제 판정에는 초기/후기 2분할만 쓴다.
# ===========================================================================
PAB_RNG = np.random.default_rng(20260909)

def p_a_better(xa, na, xb, nb, draws=200_000):
    """무정보 사전분포 Beta(1,1)에서 P(A그룹 비율 > B그룹 비율), % 단위."""
    if not na or not nb:
        return None
    sa = PAB_RNG.beta(1 + xa, 1 + na - xa, draws)
    sb = PAB_RNG.beta(1 + xb, 1 + nb - xb, draws)
    return round(100 * float((sa > sb).mean()), 1)

ev = events.merge(users[["user_id", "signup_week", "signup_date"]], on="user_id", how="left")
ev["elapsed_week"] = ((ev.event_timestamp - ev.signup_date).dt.total_seconds() // (7 * 86400)).astype(int)
ev = ev[ev.elapsed_week >= 0]

# 가설2 분모: 추천 클릭(select_item)이 발생한 세션
rec_sessions = set(ev.loc[ev.event_type == "select_item", "session_id"])
in_rec_session = ev.session_id.isin(rec_sessions)

HYPOTHESES = {
    "가설1 구매전환율": (ev.event_type == "complete_purchase",
                        ev.event_type == "session_start"),
    "가설2 추천클릭세션 CVR": ((ev.event_type == "complete_purchase") & in_rec_session,
                              (ev.event_type == "session_start") & in_rec_session),
    "가설3 반응입력완료율": (ev.event_type == "reaction_complete",
                            ev.event_type == "reaction_require_alarm"),
}

def cohort_slice(num_mask, den_mask, key):
    """key(가입주 또는 경과주) 구간별로 A/B 분자·분모와 P(A>B)를 계산."""
    rows = []
    for k in sorted(ev[key].unique()):
        seg = ev[key] == k
        cell = {}
        for g in ("A", "B"):
            m = seg & (ev.group == g)
            cell[g] = (int((num_mask & m).sum()), int((den_mask & m).sum()))
        (xa, na), (xb, nb) = cell["A"], cell["B"]
        if not na and not nb:
            continue  # 관측이 없는 구간(관측창 밖)은 행 자체를 만들지 않는다
        rows.append({
            key: k,
            "A_num": xa, "A_den": na, "A_rate": round(100 * xa / na, 2) if na else None,
            "B_num": xb, "B_den": nb, "B_rate": round(100 * xb / nb, 2) if nb else None,
            "P_A_better": p_a_better(xa, na, xb, nb),
        })
    return pd.DataFrame(rows)

# --- (1) 격자 밀도 진단: 왜 "가입주 x 경과주" 전체 격자를 판정에 쓰지 않는가
density_rows = []
for name, (num_mask, den_mask) in HYPOTHESES.items():
    a = ev.group == "A"
    den_cells = ev[den_mask & a].groupby(["signup_week", "elapsed_week"]).size()
    num_cells = ev[num_mask & a].groupby(["signup_week", "elapsed_week"]).size()
    density_rows.append({
        "가설": name,
        "채워진_셀수": len(den_cells),
        "A_분모_총계": int(den_cells.sum()),
        "A_분자_총계": int(num_cells.sum()),
        "셀당_분모_중앙값": int(den_cells.median()),
        "셀당_분자_중앙값": float(num_cells.median()) if len(num_cells) else 0.0,
    })
density_df = pd.DataFrame(density_rows)

# --- (2) 초기(0~3주) vs 후기(4주+) 2분할 — 판정에 사용하는 절단
EARLY_MAX_WEEK = 3
EARLY_LABEL = f"초기 0~{EARLY_MAX_WEEK}주"
LATE_LABEL = f"후기 {EARLY_MAX_WEEK + 1}주+"
early_late_rows = []
for name, (num_mask, den_mask) in HYPOTHESES.items():
    for label, seg in ((EARLY_LABEL, ev.elapsed_week <= EARLY_MAX_WEEK),
                       (LATE_LABEL, ev.elapsed_week > EARLY_MAX_WEEK)):
        cell = {}
        for g in ("A", "B"):
            m = seg & (ev.group == g)
            cell[g] = (int((num_mask & m).sum()), int((den_mask & m).sum()))
        (xa, na), (xb, nb) = cell["A"], cell["B"]
        early_late_rows.append({
            "가설": name, "구간": label,
            "A_num": xa, "A_den": na, "A_rate": round(100 * xa / na, 2),
            "B_num": xb, "B_den": nb, "B_rate": round(100 * xb / nb, 2),
            "P_A_better": p_a_better(xa, na, xb, nb),
        })
early_late_df = pd.DataFrame(early_late_rows)

# --- (3) 경과 주차별 / 가입 코호트별 (방향 참고용)
elapsed_parts, signup_parts = [], []
for name, (num_mask, den_mask) in HYPOTHESES.items():
    for key, parts in (("elapsed_week", elapsed_parts), ("signup_week", signup_parts)):
        part = cohort_slice(num_mask, den_mask, key)
        part.insert(0, "가설", name)
        parts.append(part)
elapsed_df = pd.concat(elapsed_parts, ignore_index=True)
signup_df = pd.concat(signup_parts, ignore_index=True)

# --- (4) 생존 편향 진단: 경과 주차가 늘수록 남아있는 유저가 줄어든다
starts = ev[ev.event_type == "session_start"]
survivor_df = pd.DataFrame({
    "활동_유저수": starts.groupby("elapsed_week").user_id.nunique(),
    "세션수": starts.groupby("elapsed_week").size(),
}).reset_index()
survivor_df["유저당_세션수"] = (survivor_df.세션수 / survivor_df.활동_유저수).round(2)

print("=" * 70)
print("가설별 코호트: 격자 밀도 진단 (A그룹, 가입주 x 경과주)")
print("=" * 70)
print(density_df.to_string(index=False))
print()
print("=" * 70)
print(f"가설별 코호트: {EARLY_LABEL} vs {LATE_LABEL} — 판정용 절단")
print("=" * 70)
print(early_late_df.to_string(index=False))
print()
print("=" * 70)
print("생존 편향 진단: 경과 주차별 활동 유저수")
print("=" * 70)
print(survivor_df.to_string(index=False))

density_df.to_csv("../data/generated_v2/cohort_hypothesis_grid_density.csv", index=False, encoding="utf-8-sig")
early_late_df.to_csv("../data/generated_v2/cohort_hypothesis_early_late.csv", index=False, encoding="utf-8-sig")
elapsed_df.to_csv("../data/generated_v2/cohort_hypothesis_by_elapsed_week.csv", index=False, encoding="utf-8-sig")
signup_df.to_csv("../data/generated_v2/cohort_hypothesis_by_signup_week.csv", index=False, encoding="utf-8-sig")
survivor_df.to_csv("../data/generated_v2/cohort_survivorship_check.csv", index=False, encoding="utf-8-sig")

print()
print("가설별 코호트 분석 저장 완료 (cohort_hypothesis_*.csv, cohort_survivorship_check.csv)")
