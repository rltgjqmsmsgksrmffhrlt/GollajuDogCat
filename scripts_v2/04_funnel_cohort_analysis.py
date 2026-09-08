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
