# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

events = pd.read_csv("../data/generated/events_log.csv", parse_dates=["event_timestamp"], low_memory=False)
orders = pd.read_csv("../data/generated/orders.csv", parse_dates=["purchase_date"])
reactions = pd.read_csv("../data/generated/pet_reactions.csv", parse_dates=["reaction_complete_ts"])

def pct(a, b):
    return round(100 * a / b, 2) if b else None

purchase_sessions = set(events[events.event_type == "complete_purchase"]["session_id"])

print("="*70)
print("가설1: 선택 피로도 해소")
print("="*70)

# 장바구니 이탈률: add_to_cart 발생 세션 중 구매 없이 종료(reason=cart_abandoned)된 세션 비율
cart_sessions = events[events.event_type == "add_to_cart"][["session_id", "group"]].drop_duplicates()
cart_sessions["purchased"] = cart_sessions["session_id"].isin(purchase_sessions)
for g in ["A", "B"]:
    sub = cart_sessions[cart_sessions.group == g]
    rate = pct((~sub.purchased).sum(), len(sub))
    print(f"  장바구니 이탈률 [{g}]: {rate}%  (목표: A 40% / B 52.8~56.1%)")

# 추천 CVR: view_item(source=recommendation) 세션 중 구매 세션 비율
view_reco = events[(events.event_type == "view_item") & (events.entry_source == "recommendation")][["session_id","group"]].drop_duplicates()
view_reco["purchased"] = view_reco["session_id"].isin(purchase_sessions)
for g in ["A", "B"]:
    sub = view_reco[view_reco.group == g]
    cvr = pct(sub.purchased.sum(), len(sub))
    print(f"  추천 상품 CVR [{g}]: {cvr}%  (목표: A 3.3% / B 3.21%)")

dwell = events[events.event_type == "view_item_end"][["group","session_time"]].dropna()
for g in ["A","B"]:
    m = dwell[dwell.group==g].session_time.mean()
    print(f"  상품상세 체류시간 평균 [{g}]: {round(m,1)}초  (목표: A 60초 / B 43초)")

vi = events[events.event_type=="view_item"][["session_id","group","event_timestamp"]].rename(columns={"event_timestamp":"view_ts"})
cp = events[events.event_type=="complete_purchase"][["session_id","event_timestamp"]].rename(columns={"event_timestamp":"purchase_ts"})
merged = vi.merge(cp, on="session_id", how="inner")
merged["decision_days"] = (merged.purchase_ts - merged.view_ts).dt.total_seconds() / 86400
for g in ["A","B"]:
    m = merged[merged.group==g].decision_days.mean()
    print(f"  구매결정 소요시간 평균 [{g}]: {round(m,2)}일  (목표: A 2일 / B 2.4~3.3일)")

print()
print("="*70)
print("가설2: 서비스 충성도")
print("="*70)

nps_events = events[events.event_type == "nps_score"][["user_id","group","nps_score"]].dropna()
for g in ["A","B"]:
    sub = nps_events[nps_events.group==g]
    total = len(sub)
    promoters = (sub.nps_score >= 9).sum()
    detractors = (sub.nps_score <= 6).sum()
    nps_val = round(100*(promoters/total - detractors/total), 1) if total else None
    print(f"  NPS [{g}]: {nps_val}점 (n={total})  (목표: A 55점 이상 / B 20~30점)")

sel_reco = events[events.event_type=="select_item"][["session_id","group"]].drop_duplicates()
sel_reco["purchased"] = sel_reco["session_id"].isin(events[(events.event_type=="complete_purchase")]["session_id"])
for g in ["A","B"]:
    sub = sel_reco[sel_reco.group==g]
    cvr = pct(sub.purchased.sum(), len(sub))
    print(f"  맞춤 추천 CVR(순수달성) [{g}]: {cvr}%  (목표: 초기 3.3% / 목표 5%)")

delivered_orders = orders.merge(
    events[events.event_type=="delivery_status_complete"][["order_id"]].drop_duplicates(),
    on="order_id", how="inner"
)
review_orders = set(events[events.event_type=="review_created"]["order_id"])
reaction_orders = set(events[events.event_type=="pet_reaction_created"]["order_id"])
for g in ["A","B"]:
    denom_orders = delivered_orders[delivered_orders.group==g]["order_id"]
    denom = len(denom_orders)
    review_cnt = denom_orders.isin(review_orders).sum()
    reaction_cnt = denom_orders.isin(reaction_orders).sum()
    both_cnt = (denom_orders.isin(review_orders) & denom_orders.isin(reaction_orders)).sum()
    rate = pct(review_cnt, denom) + pct(reaction_cnt, denom) - pct(both_cnt, denom) if denom else None
    print(f"  상품 반응 데이터 입력률 [{g}]: {round(rate,2) if rate else None}%  (목표: 초기 5% / 목표 10%)")

first_purchase = orders.sort_values("purchase_date").groupby("user_id").first().reset_index()
orders_by_user = orders.groupby("user_id")
for g in ["A","B"]:
    fp = first_purchase[first_purchase.group==g]
    repurchased_30 = eligible_30 = repurchased_60 = eligible_60 = 0
    for _, row in fp.iterrows():
        uid = row.user_id; fdate = row.purchase_date
        user_orders_g = orders_by_user.get_group(uid)
        later = user_orders_g[(user_orders_g.purchase_date > fdate) & (user_orders_g.source=="recommendation")]
        if (pd.Timestamp("2026-12-06") - fdate).days >= 30:
            eligible_30 += 1
            if ((later.purchase_date - fdate).dt.days <= 30).any():
                repurchased_30 += 1
        if (pd.Timestamp("2026-12-06") - fdate).days >= 60:
            eligible_60 += 1
            if ((later.purchase_date - fdate).dt.days <= 60).any():
                repurchased_60 += 1
    r30 = pct(repurchased_30, eligible_30); r60 = pct(repurchased_60, eligible_60)
    print(f"  N일 재구매율 [{g}]: 30일={r30}% (n={eligible_30}) / 60일={r60}% (n={eligible_60})  (목표: 30일 8~10% / 60일 12~15%)")

view_item_sessions = events[events.event_type=="view_item"][["session_id","group"]].drop_duplicates()
comp_pdp_sessions = events[(events.event_type=="view_comparison") & (events.entry_source=="pdp")][["session_id","group"]].drop_duplicates()
session_start_sessions = events[events.event_type=="session_start"][["session_id","group"]].drop_duplicates()
comp_all_sessions = events[events.event_type=="view_comparison"][["session_id","group"]].drop_duplicates()
comp_all_sessions["purchased"] = comp_all_sessions["session_id"].isin(purchase_sessions)

for g in ["A","B"]:
    denom1 = len(view_item_sessions[view_item_sessions.group==g])
    numer1 = len(comp_pdp_sessions[comp_pdp_sessions.group==g])
    rate1 = pct(numer1, denom1)
    denom2 = len(session_start_sessions[session_start_sessions.group==g])
    numer2 = len(comp_all_sessions[comp_all_sessions.group==g])
    rate2 = pct(numer2, denom2)
    sub3 = comp_all_sessions[comp_all_sessions.group==g]
    rate3 = pct(sub3.purchased.sum(), len(sub3))
    print(f"  PDP경유 비교기능 사용률 [{g}]: {rate1}% (목표 15~25%) | 전체 비교기능 사용률: {rate2}% (목표 10~20%) | 비교후 전환율: {rate3}% (목표 4~6%)")

print()
print("="*70)
print("가설3: 유저 데이터 확보")
print("="*70)

alarm_events = events[events.event_type=="reaction_require_alarm"][["order_id","group"]].drop_duplicates()
start_events = events[events.event_type=="reaction_start"][["order_id","group"]].drop_duplicates()
complete_events = events[events.event_type=="reaction_complete"][["order_id","group"]].drop_duplicates()
pet_reaction_events = events[events.event_type=="pet_reaction_created"][["order_id","group","is_valid"]].drop_duplicates()
reentry_events = events[events.event_type=="recommendation_view"][["order_id","group"]].drop_duplicates()

for g in ["A","B"]:
    n_alarm = len(alarm_events[alarm_events.group==g])
    n_start = len(start_events[start_events.group==g])
    n_complete = len(complete_events[complete_events.group==g])
    n_valid = len(pet_reaction_events[(pet_reaction_events.group==g) & (pet_reaction_events.is_valid==True)])
    n_reentry_orders = len(reentry_events[reentry_events.group==g])

    start_rate = pct(n_start, n_alarm)
    complete_rate = pct(n_complete, n_start)  # 완료율은 "시작 대비 완료" — 원본 정의: 요청노출 대비 완료지만, 시작 대비도 함께 표기
    complete_rate_vs_alarm = pct(n_complete, n_alarm)
    dropout_rate = pct(n_start - n_complete, n_start) if n_start else None
    reentry_rate = pct(n_reentry_orders, n_complete) if n_complete else None
    valid_rate = pct(n_valid, n_alarm)

    print(f"  [{g}] 반응입력 시작률(알람대비): {start_rate}% (목표 A20~30%/B<=20%)")
    print(f"       완료율(시작대비): {complete_rate}% (목표 A>=85%/B<=80%) | 완료율(알람대비): {complete_rate_vs_alarm}%")
    print(f"       퍼널 이탈률(시작대비 미완료): {dropout_rate}% (목표 A<=15%/B~20%)")
    print(f"       재진입률(완료대비): {reentry_rate}% (목표 A>=5%,A>B)")
    print(f"       유효 반응 데이터 확보율(알람대비): {valid_rate}% (목표 초기10%/목표15%)")

print()
print("Validation v2 complete.")
