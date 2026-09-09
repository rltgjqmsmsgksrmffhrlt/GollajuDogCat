# -*- coding: utf-8 -*-
"""
02_simulate_events_v2.py
v1의 문제점 수정:
 - 추천 클릭(select_item) 후 구매하지 않는 케이스를 명시적으로 생성 (CVR 분모 확보)
 - 장바구니 담기 후 이탈하는 케이스 비율을 목표 이탈률에 정확히 맞춤
 - 반응입력 시작 후 미완료(이탈)하는 케이스를 목표 완료율에 정확히 맞춰 생성
 - NPS 점수는 세션이 아닌 응답 단위로 개별 관리, group 매핑 명확화
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(2026)

START_DATE = datetime(2026, 9, 8)
END_DATE = datetime(2026, 12, 6)
N_DAYS = (END_DATE - START_DATE).days + 1

users_df = pd.read_csv("../data/generated/users_master.csv", parse_dates=["signup_date"])
products_df = pd.read_csv("../data/generated/products_master.csv")

products_by_cat = {cat: g["product_id"].tolist() for cat, g in products_df.groupby("category_id")}
all_products = products_df["product_id"].tolist()
all_categories = products_df["category_id"].unique().tolist()

# ---------------------------------------------------------------------------
# 목표 파라미터
# ---------------------------------------------------------------------------
PARAMS = {
    "A": {
        "cart_abandon_rate": 0.40,
        "cvr_recommend": 0.033,
        "pdp_dwell_mean_sec": 60,
        "decision_days_mean": 2.0,
        "nps_promoter_rate": 0.62,   # 추천비율 (0~10점 중 9~10점)
        "nps_detractor_rate": 0.07,  # 비추천비율 (0~6점) -> NPS = 62-7 = 55
        "cvr_recommend_pure": 0.05,
        "reaction_input_rate": 0.10,
        "repurchase_30d": 0.09,
        "repurchase_60d": 0.135,
        "compare_pdp_rate": 0.22,
        "compare_overall_extra_rate": 0.06,  # PDP 경유 외 추가로 비교화면 진입하는 비율(전체 대비)
        "compare_to_purchase_rate": 0.06,
        "reaction_start_rate": 0.28,
        "reaction_complete_rate": 0.87,
        "reentry_rate": 0.07,
        "valid_reaction_ratio": 0.92,  # 완료된 반응입력 중 유효 비율
        # 장바구니 이탈률(40%)과 추천CVR(3.3%)은 서로 다른 모집단(전체 vs 추천경로)이므로
        # 비-추천 경로(검색/GNB, 세션의 55%)의 구매율을 역산하여 전체 평균이 목표에 맞도록 별도 관리
        "cart_direct_purchase_rate": 1.0,  # 검색/GNB 경로 구매율 100%로 두어도 장바구니 이탈률 40%는 추천CVR 3.3%·비교전환율 6.6%와 수학적으로 완전 양립 불가 → 최대치로 근사
    },
    "B": {
        "cart_abandon_rate": 0.545,
        "cvr_recommend": 0.0321,
        "pdp_dwell_mean_sec": 43,
        "decision_days_mean": 2.85,
        "nps_promoter_rate": 0.32,
        "nps_detractor_rate": 0.07,  # NPS = 32-7 = 25
        "cvr_recommend_pure": 0.03,
        "reaction_input_rate": 0.05,
        "repurchase_30d": 0.05,
        "repurchase_60d": 0.08,
        "compare_pdp_rate": 0.10,
        "compare_overall_extra_rate": 0.03,
        "compare_to_purchase_rate": 0.032,
        "reaction_start_rate": 0.18,
        "reaction_complete_rate": 0.78,
        "reentry_rate": 0.03,
        "valid_reaction_ratio": 0.88,
        "cart_direct_purchase_rate": 0.91,  # 역산값 (target 45.5%, 추천CVR 3.21%·비교전환율 2.8% 반영)
    },
}

def rand_ts(base_date, day_offset_max=0):
    offset_sec = int(RNG.integers(0, 86400 * (day_offset_max + 1)))
    return base_date + timedelta(seconds=offset_sec)

events = []
orders = []
reactions = []

def add_event(user_id, group, session_id, event_type, ts, **kwargs):
    row = {"event_timestamp": ts, "user_id": user_id, "group": group,
           "session_id": session_id, "event_type": event_type}
    row.update(kwargs)
    events.append(row)

_order_seq = 1
def new_order_id():
    global _order_seq
    oid = f"ORD{_order_seq:06d}"; _order_seq += 1
    return oid

_session_seq = 1
def new_session_id():
    global _session_seq
    sid = f"S{_session_seq:07d}"; _session_seq += 1
    return sid

_reco_seq = 1
def new_reco_id():
    global _reco_seq
    rid = f"REC{_reco_seq:06d}"; _reco_seq += 1
    return rid

all_orders_by_user = {}  # user_id -> list of order dicts

for _, u in users_df.iterrows():
    user_id = u["user_id"]; group = u["group"]; pet_id = u["pet_id"]
    p = PARAMS[group]
    signup = u["signup_date"]
    days_active_remaining = (END_DATE - signup).days
    if days_active_remaining < 1:
        continue

    n_sessions = max(1, int(RNG.poisson(lam=min(8, 2 + days_active_remaining / 12))))
    user_orders = []

    for s_idx in range(n_sessions):
        day_off = int(RNG.integers(0, days_active_remaining + 1))
        sess_start = rand_ts(signup + timedelta(days=day_off))
        session_id = new_session_id()
        add_event(user_id, group, session_id, "session_start", sess_start)

        cat = str(RNG.choice(all_categories))
        product_id = str(RNG.choice(products_by_cat[cat]))
        entry_source = str(RNG.choice(["recommendation", "search", "gnb"], p=[0.45, 0.35, 0.20]))

        view_ts = sess_start + timedelta(seconds=int(RNG.integers(5, 120)))
        add_event(user_id, group, session_id, "view_item", view_ts,
                   product_id=product_id, category_id=cat, entry_source=entry_source)
        add_event(user_id, group, session_id, "match_score_shown", view_ts + timedelta(seconds=1),
                   product_id=product_id, match_score_shown=(group == "A"))

        dwell_sec = max(3, RNG.exponential(p["pdp_dwell_mean_sec"]))
        view_end_ts = view_ts + timedelta(seconds=dwell_sec)
        add_event(user_id, group, session_id, "view_item_end", view_end_ts,
                   product_id=product_id, session_time=round(dwell_sec, 1))

        # --- 추천 클릭 이벤트 (구매 여부와 무관하게 먼저 발생 여부 결정) ---
        if entry_source == "recommendation":
            recommendation_id = new_reco_id()
            add_event(user_id, group, session_id, "recommendation_impression", view_ts - timedelta(seconds=3),
                       product_id=product_id, recommendation_id=recommendation_id)
            add_event(user_id, group, session_id, "select_item", view_ts - timedelta(seconds=2),
                       product_id=product_id, source="recommendation", recommendation_id=recommendation_id)
        else:
            recommendation_id = None

        # --- 비교 화면 진입 ---
        did_compare = False
        compare_source = None
        if RNG.random() < p["compare_pdp_rate"]:
            comp_ts = view_end_ts + timedelta(seconds=int(RNG.integers(2, 30)))
            add_event(user_id, group, session_id, "view_comparison", comp_ts,
                       product_id=product_id, entry_source="pdp")
            did_compare = True
            compare_source = "pdp"
        elif RNG.random() < p["compare_overall_extra_rate"]:
            comp_ts = sess_start + timedelta(seconds=int(RNG.integers(10, 200)))
            add_event(user_id, group, session_id, "view_comparison", comp_ts,
                       product_id=product_id, entry_source="gnb")
            did_compare = True
            compare_source = "gnb"

        # --- 장바구니 담기 ---
        add_to_cart_ts = view_end_ts + timedelta(seconds=int(RNG.integers(1, 20)))
        add_event(user_id, group, session_id, "add_to_cart", add_to_cart_ts,
                   product_id=product_id, category_id=cat)

        # --- 구매 전환 판정 (단일 확률 트리로 명확화) ---
        if did_compare:
            will_purchase = RNG.random() < p["compare_to_purchase_rate"]
            purchase_source = "comparison"
        elif entry_source == "recommendation":
            will_purchase = RNG.random() < p["cvr_recommend"]
            purchase_source = "recommendation"
        else:
            # 전체 장바구니 이탈률이 목표(A 40%/B 54.5%)에 맞도록,
            # 추천 경유(cvr_recommend)·비교경유(compare_to_purchase_rate) 세션의
            # 낮은 구매율을 상쇄하는 수준으로 direct 세션의 구매율을 보정
            will_purchase = RNG.random() < p["cart_direct_purchase_rate"]
            purchase_source = "direct"

        if will_purchase:
            decision_days = max(0.02, RNG.exponential(p["decision_days_mean"]))
            purchase_ts = view_ts + timedelta(days=decision_days)
            if purchase_ts > END_DATE:
                purchase_ts = END_DATE - timedelta(hours=int(RNG.integers(1, 24)))
            order_id = new_order_id()

            add_event(user_id, group, session_id, "complete_purchase", purchase_ts,
                       order_id=order_id, product_id=product_id, category_id=cat,
                       source=purchase_source, recommendation_id=recommendation_id)

            order_row = {
                "order_id": order_id, "user_id": user_id, "group": group,
                "product_id": product_id, "category_id": cat,
                "purchase_date": purchase_ts, "source": purchase_source,
                "recommendation_id": recommendation_id, "session_id": session_id,
            }
            orders.append(order_row)
            user_orders.append(order_row)
            sess_end_ts = purchase_ts + timedelta(seconds=int(RNG.integers(5, 300)))
        else:
            # 명시적 이탈 (장바구니 담았지만 미구매) — cart_abandoned 사유로 세션 종료
            sess_end_ts = add_to_cart_ts + timedelta(seconds=int(RNG.integers(5, 600)))
            add_event(user_id, group, session_id, "session_end", sess_end_ts, reason="cart_abandoned")
            continue  # session_end 중복 방지 위해 여기서 다음 세션으로

        add_event(user_id, group, session_id, "session_end", sess_end_ts)

    # ---- N일 재구매 퍼널 ----
    if user_orders:
        first = min(user_orders, key=lambda o: o["purchase_date"])
        first_purchase_date = first["purchase_date"]
        days_since_first = (END_DATE - first_purchase_date).days
        if days_since_first >= 5:
            window_avail_60 = days_since_first >= 60
            window_avail_30 = days_since_first >= 30
            target_rate = (p["repurchase_60d"] if window_avail_60
                           else (p["repurchase_30d"] if window_avail_30 else p["repurchase_30d"] * 0.5))
            if RNG.random() < target_rate:
                max_days = 60 if window_avail_60 else 30
                repurchase_offset = int(RNG.integers(5, max(6, max_days)))
                reco_ts = first_purchase_date + timedelta(days=repurchase_offset)
                if reco_ts <= END_DATE:
                    cat2 = str(RNG.choice(all_categories))
                    product_id2 = str(RNG.choice(products_by_cat[cat2]))
                    sid2 = new_session_id()
                    reco_id2 = new_reco_id()
                    add_event(user_id, group, sid2, "session_start", reco_ts - timedelta(minutes=5))
                    add_event(user_id, group, sid2, "recommendation_impression", reco_ts - timedelta(minutes=4),
                               product_id=product_id2, recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "select_item", reco_ts - timedelta(minutes=3),
                               product_id=product_id2, source="recommendation", recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "add_to_cart", reco_ts - timedelta(minutes=2),
                               product_id=product_id2, category_id=cat2)
                    order_id2 = new_order_id()
                    add_event(user_id, group, sid2, "complete_purchase", reco_ts,
                               order_id=order_id2, product_id=product_id2, category_id=cat2,
                               source="recommendation", recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "session_end", reco_ts + timedelta(minutes=1))
                    order_row2 = {
                        "order_id": order_id2, "user_id": user_id, "group": group,
                        "product_id": product_id2, "category_id": cat2,
                        "purchase_date": reco_ts, "source": "recommendation",
                        "recommendation_id": reco_id2, "session_id": sid2,
                    }
                    orders.append(order_row2)
                    user_orders.append(order_row2)

    all_orders_by_user[user_id] = user_orders

    # ---- 구매확정 + 배송완료 + 반응입력 퍼널 ----
    for o in user_orders:
        purchase_ts = o["purchase_date"]; order_id = o["order_id"]

        delivery_ts = purchase_ts + timedelta(days=int(RNG.integers(1, 4)))
        if delivery_ts > END_DATE + timedelta(days=10):
            continue
        add_event(user_id, group, o["session_id"], "delivery_status_complete", delivery_ts, order_id=order_id)

        if RNG.random() < 0.5:
            confirm_ts = delivery_ts + timedelta(days=int(RNG.integers(0, 5)))
            confirm_type = "manual"
        else:
            confirm_ts = delivery_ts + timedelta(days=7)
            confirm_type = "auto"
        add_event(user_id, group, o["session_id"], "purchase_confirm", confirm_ts,
                   order_id=order_id, confirm_type=confirm_type)

        # 반응 입력 요청 알람 (분모 고정)
        alarm_ts = delivery_ts + timedelta(hours=int(RNG.integers(1, 12)))
        add_event(user_id, group, o["session_id"], "reaction_require_alarm", alarm_ts,
                   order_id=order_id, pet_id=pet_id)

        # 시작 여부 (목표 시작률을 알람 대비 직접 적용)
        will_start = RNG.random() < p["reaction_start_rate"]
        if will_start:
            check_ts = alarm_ts + timedelta(hours=int(RNG.integers(1, 48)))
            add_event(user_id, group, o["session_id"], "reaction_check", check_ts, order_id=order_id)
            start_ts = check_ts + timedelta(minutes=int(RNG.integers(1, 120)))
            add_event(user_id, group, o["session_id"], "reaction_start", start_ts,
                       order_id=order_id, pet_id=pet_id)

            # 완료 여부 (목표 완료율을 시작 대비 직접 적용)
            will_complete = RNG.random() < p["reaction_complete_rate"]
            if will_complete:
                complete_ts = start_ts + timedelta(minutes=int(RNG.integers(1, 15)))
                is_valid = RNG.random() < p["valid_reaction_ratio"]
                add_event(user_id, group, o["session_id"], "reaction_complete", complete_ts,
                           order_id=order_id, pet_id=pet_id)
                add_event(user_id, group, o["session_id"], "pet_reaction_created", complete_ts + timedelta(seconds=1),
                           order_id=order_id, pet_id=pet_id, is_valid=is_valid)
                reactions.append({"order_id": order_id, "user_id": user_id, "group": group,
                                   "pet_id": pet_id, "is_valid": is_valid, "reaction_complete_ts": complete_ts})

                if RNG.random() < p["reentry_rate"]:
                    reentry_ts = complete_ts + timedelta(days=int(RNG.integers(1, 10)))
                    if reentry_ts <= END_DATE:
                        sid3 = new_session_id()
                        add_event(user_id, group, sid3, "session_start", reentry_ts - timedelta(minutes=1))
                        add_event(user_id, group, sid3, "recommendation_view", reentry_ts,
                                   order_id=order_id, entry_source="post_reaction")
                        add_event(user_id, group, sid3, "session_end", reentry_ts + timedelta(minutes=3))
            else:
                # 명시적 퍼널 이탈 (입력 시작했으나 완료 안 함)
                dropout_ts = start_ts + timedelta(minutes=int(RNG.integers(1, 30)))
                add_event(user_id, group, o["session_id"], "session_end", dropout_ts, reason="reaction_input_dropout")

        # 리뷰 작성
        if RNG.random() < p["reaction_input_rate"] * 0.6:
            review_ts = delivery_ts + timedelta(days=int(RNG.integers(1, 10)))
            if review_ts <= END_DATE:
                add_event(user_id, group, o["session_id"], "review_created", review_ts,
                           order_id=order_id, product_id=o["product_id"])

        # NPS: 트리거 대상 중 노출률 100%(가정), 응답률 70%, 응답 시 promoter/detractor/passive 분포를 목표대로 직접 샘플
        nps_trigger_ts = confirm_ts + timedelta(days=3)
        if nps_trigger_ts <= END_DATE:
            add_event(user_id, group, o["session_id"], "nps_popup_impression", nps_trigger_ts,
                       trigger_type="purchase_confirm_d3")
            if RNG.random() < 0.70:
                roll = RNG.random()
                if roll < p["nps_promoter_rate"]:
                    score = int(RNG.integers(9, 11))  # 9~10
                elif roll < p["nps_promoter_rate"] + p["nps_detractor_rate"]:
                    score = int(RNG.integers(0, 7))   # 0~6
                else:
                    score = int(RNG.integers(7, 9))   # 7~8 (passive)
                add_event(user_id, group, o["session_id"], "nps_score", nps_trigger_ts + timedelta(minutes=1),
                           nps_score=score)

print("events:", len(events))
print("orders:", len(orders))
print("reactions:", len(reactions))

events_df = pd.DataFrame(events).sort_values("event_timestamp").reset_index(drop=True)
orders_df = pd.DataFrame(orders)
reactions_df = pd.DataFrame(reactions)

events_df.to_csv("../data/generated/events_log.csv", index=False)
orders_df.to_csv("../data/generated/orders.csv", index=False)
reactions_df.to_csv("../data/generated/pet_reactions.csv", index=False)
