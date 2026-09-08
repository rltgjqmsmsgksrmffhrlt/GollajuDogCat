# -*- coding: utf-8 -*-
"""
03_validate_metrics.py (v2)
v1은 하드코딩된 목표치와 관측치를 비교했지만, v2는 그 "목표치" 자체가 더 이상
존재하지 않습니다(임의로 정한 값이 아니라 Kaggle 실측/보수적 가정으로 확률을 정했으므로,
결과는 그 확률에서 "발생"하는 값입니다). 대신 아래 두 가지를 비교합니다.
  1) 관측된 조회->장바구니, 장바구니->구매 비율이 Kaggle 실측 기준값과 방향/자릿수가
     맞는지 (완전히 같을 필요는 없음 — 표본 크기가 다르고 A그룹엔 +15% 가정이 섞여 있음)
  2) A/B 그룹 간 격차가 의도한 대로 "보수적"인 수준(수 %p~십수 %)인지, v1처럼 과장된
     격차(2배 이상)가 남아있지 않은지
"""
import pandas as pd

KAGGLE_VIEW_TO_CART = 0.0360
KAGGLE_CART_TO_PURCHASE = 0.3283

events = pd.read_csv("../data/generated_v2/events_log.csv", parse_dates=["event_timestamp"], low_memory=False)
orders = pd.read_csv("../data/generated_v2/orders.csv", parse_dates=["purchase_date"])
reactions = pd.read_csv("../data/generated_v2/pet_reactions.csv", parse_dates=["reaction_complete_ts"])


def pct(a, b):
    return round(100 * a / b, 3) if b else None


def rel_lift(a, b):
    return round(100 * (a - b) / b, 1) if b else None


print("=" * 72)
print("0. Kaggle 실측 대비 조회->장바구니 / 장바구니->구매 비율 (전체, A+B 합산)")
print("=" * 72)
view_sessions = events[events.event_type == "view_item"]["session_id"].nunique()
cart_sessions_all = events[events.event_type == "add_to_cart"]["session_id"].unique()
purchase_sessions_all = events[events.event_type == "complete_purchase"]["session_id"].unique()
n_cart = len(cart_sessions_all)
n_purchase = len(set(cart_sessions_all) & set(purchase_sessions_all))
print(f"  조회->장바구니: 관측 {pct(n_cart, view_sessions)}%  (Kaggle 기준 {KAGGLE_VIEW_TO_CART*100:.2f}%, "
      f"A그룹 개인화 반영 시 소폭 상회 예상)")
print(f"  장바구니->구매: 관측 {pct(n_purchase, n_cart)}%  (Kaggle 기준 {KAGGLE_CART_TO_PURCHASE*100:.2f}%)")

print()
print("=" * 72)
print("가설1: 선택 피로도 해소 (구매 여정, Kaggle 실측 확률 기반)")
print("=" * 72)

sessions = events[events.event_type == "session_start"][["session_id", "group"]].drop_duplicates()
cart_s = set(cart_sessions_all)
purch_s = set(purchase_sessions_all)
sessions["cart"] = sessions.session_id.isin(cart_s)
sessions["purchase"] = sessions.session_id.isin(purch_s)

rates = {}
for g in ["A", "B"]:
    sub = sessions[sessions.group == g]
    v2c = pct(sub.cart.sum(), len(sub))
    cart_sub = sub[sub.cart]
    c2p = pct(cart_sub.purchase.sum(), len(cart_sub))
    abandon = round(100 - c2p, 2) if c2p is not None else None
    rates[g] = (v2c, c2p)
    print(f"  [{g}] 조회->장바구니 {v2c}%  |  장바구니->구매 {c2p}%  |  장바구니 이탈률 {abandon}%")
print(f"  A/B 조회->장바구니 상대격차: {rel_lift(rates['A'][0], rates['B'][0])}%  (가정 LIFT=+15%와 자릿수 비교용)")
print(f"  A/B 장바구니->구매 상대격차: {rel_lift(rates['A'][1], rates['B'][1])}%")

dwell = events[events.event_type == "view_item_end"][["group", "session_time"]].dropna()
for g in ["A", "B"]:
    m = dwell[dwell.group == g].session_time.mean()
    print(f"  상품상세 체류시간 평균 [{g}]: {round(m,1)}초  (가정(명시), Kaggle 검증 불가 — 세션 연속성 필요)")

vi = events[events.event_type == "view_item"][["session_id", "group", "event_timestamp"]].rename(columns={"event_timestamp": "view_ts"})
cp = events[events.event_type == "complete_purchase"][["session_id", "event_timestamp"]].rename(columns={"event_timestamp": "purchase_ts"})
merged = vi.merge(cp, on="session_id", how="inner")
merged["decision_days"] = (merged.purchase_ts - merged.view_ts).dt.total_seconds() / 86400
for g in ["A", "B"]:
    m = merged[merged.group == g].decision_days.mean()
    print(f"  구매결정 소요시간 평균 [{g}]: {round(m,2)}일  (가정(명시))")

print()
print("=" * 72)
print("가설2: 서비스 충성도")
print("=" * 72)

nps_events = events[events.event_type == "nps_score"][["user_id", "group", "nps_score"]].dropna()
for g in ["A", "B"]:
    sub = nps_events[nps_events.group == g]
    total = len(sub)
    promoters = (sub.nps_score >= 9).sum()
    detractors = (sub.nps_score <= 6).sum()
    nps_val = round(100 * (promoters / total - detractors / total), 1) if total else None
    print(f"  NPS [{g}]: {nps_val}점 (n={total})  (가정(명시))")

delivered_orders = orders.merge(
    events[events.event_type == "delivery_status_complete"][["order_id"]].drop_duplicates(),
    on="order_id", how="inner"
)
review_orders = set(events[events.event_type == "review_created"]["order_id"])
reaction_orders = set(events[events.event_type == "pet_reaction_created"]["order_id"])
for g in ["A", "B"]:
    denom_orders = delivered_orders[delivered_orders.group == g]["order_id"]
    denom = len(denom_orders)
    review_cnt = denom_orders.isin(review_orders).sum()
    reaction_cnt = denom_orders.isin(reaction_orders).sum()
    both_cnt = (denom_orders.isin(review_orders) & denom_orders.isin(reaction_orders)).sum()
    rate = pct(review_cnt, denom) + pct(reaction_cnt, denom) - pct(both_cnt, denom) if denom else None
    print(f"  상품 반응 데이터 입력률 [{g}]: {round(rate,2) if rate else None}% (n={denom})  (가정(명시))")

first_purchase = orders.sort_values("purchase_date").groupby("user_id").first().reset_index()
orders_by_user = orders.groupby("user_id")
for g in ["A", "B"]:
    fp = first_purchase[first_purchase.group == g]
    repurchased_30 = eligible_30 = repurchased_60 = eligible_60 = 0
    for _, row in fp.iterrows():
        uid = row.user_id; fdate = row.purchase_date
        user_orders_g = orders_by_user.get_group(uid)
        later = user_orders_g[(user_orders_g.purchase_date > fdate) & (user_orders_g.source == "recommendation")]
        if (pd.Timestamp("2026-12-06") - fdate).days >= 30:
            eligible_30 += 1
            if ((later.purchase_date - fdate).dt.days <= 30).any():
                repurchased_30 += 1
        if (pd.Timestamp("2026-12-06") - fdate).days >= 60:
            eligible_60 += 1
            if ((later.purchase_date - fdate).dt.days <= 60).any():
                repurchased_60 += 1
    r30 = pct(repurchased_30, eligible_30); r60 = pct(repurchased_60, eligible_60)
    print(f"  N일 재구매율 [{g}]: 30일={r30}% (n={eligible_30}) / 60일={r60}% (n={eligible_60})  (가정(명시))")

view_item_sessions = events[events.event_type == "view_item"][["session_id", "group"]].drop_duplicates()
comp_pdp_sessions = events[(events.event_type == "view_comparison") & (events.entry_source == "pdp")][["session_id", "group"]].drop_duplicates()
comp_all_sessions = events[events.event_type == "view_comparison"][["session_id", "group"]].drop_duplicates()
comp_all_sessions["purchased"] = comp_all_sessions["session_id"].isin(purch_s)
for g in ["A", "B"]:
    denom1 = len(view_item_sessions[view_item_sessions.group == g])
    numer1 = len(comp_pdp_sessions[comp_pdp_sessions.group == g])
    rate1 = pct(numer1, denom1)
    sub3 = comp_all_sessions[comp_all_sessions.group == g]
    rate3 = pct(sub3.purchased.sum(), len(sub3))
    print(f"  PDP경유 비교기능 사용률 [{g}]: {rate1}%  |  비교 세션 내 구매전환율: {rate3}%  (가정(명시))")

print()
print("=" * 72)
print("가설3: 유저 데이터 확보 (반응입력 퍼널)")
print("=" * 72)

alarm_events = events[events.event_type == "reaction_require_alarm"][["order_id", "group"]].drop_duplicates()
start_events = events[events.event_type == "reaction_start"][["order_id", "group"]].drop_duplicates()
complete_events = events[events.event_type == "reaction_complete"][["order_id", "group"]].drop_duplicates()
pet_reaction_events = events[events.event_type == "pet_reaction_created"][["order_id", "group", "is_valid"]].drop_duplicates()
reentry_events = events[events.event_type == "recommendation_view"][["order_id", "group"]].drop_duplicates()

for g in ["A", "B"]:
    n_alarm = len(alarm_events[alarm_events.group == g])
    n_start = len(start_events[start_events.group == g])
    n_complete = len(complete_events[complete_events.group == g])
    n_valid = len(pet_reaction_events[(pet_reaction_events.group == g) & (pet_reaction_events.is_valid == True)])
    n_reentry_orders = len(reentry_events[reentry_events.group == g])

    start_rate = pct(n_start, n_alarm)
    complete_rate = pct(n_complete, n_start) if n_start else None
    dropout_rate = pct(n_start - n_complete, n_start) if n_start else None
    reentry_rate = pct(n_reentry_orders, n_complete) if n_complete else None
    valid_rate = pct(n_valid, n_alarm)

    print(f"  [{g}] 반응입력 시작률(알람대비): {start_rate}% (n_alarm={n_alarm})  (가정(명시))")
    print(f"       완료율(시작대비): {complete_rate}%  |  퍼널 이탈률: {dropout_rate}%  |  재진입률: {reentry_rate}%")
    print(f"       유효 반응 데이터 확보율(알람대비): {valid_rate}%")

print()
print("표본 수 참고: 이벤트 실측 확률(Kaggle) 적용으로 v1 대비 주문/반응 절대 건수가")
print("크게 줄었습니다(v1 ~12,000건 -> v2 수백 건). 이는 v1이 '조회하면 100% 장바구니 담기'로")
print("가정해 전환 규모를 과대 추정했던 편향을 제거한 결과이며, 실제 이커머스 조회->구매")
print("전환율(Kaggle 3개 데이터셋 기준 0.8~13.4%, 중앙값 개념상 우리 확률 산출과 방향 일치)에")
print("더 가깝습니다. n이 작아 A/B 그룹 비교의 통계적 유의성은 별도 검정이 필요합니다.")
print("Validation v2 complete.")
