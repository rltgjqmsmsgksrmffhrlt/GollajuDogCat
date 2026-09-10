# -*- coding: utf-8 -*-
"""
02_simulate_events.py (v2) — Kaggle 실측 기반, bias 최소화 이벤트 시뮬레이션

v1(scripts/02_simulate_events.py) 핵심 문제와 이번 수정:
  - v1은 "장바구니 담기"를 상품상세 조회 시 100% 고정으로 발생시키고, 이탈은 오직
    "담았지만 구매하지 않음"으로만 표현했습니다. 그 결과 장바구니 이탈률(40%)과
    추천 CVR(3.3%) 두 목표치가 서로 다른 모집단 기준이라 수학적으로 양립 불가능했고,
    v1 코드 주석에도 그 사실이 그대로 남아 있었습니다("최대치로 근사").
  - v2는 "조회 -> 장바구니" 단계와 "장바구니 -> 구매" 단계를 각각 독립 확률로 분리하고,
    두 확률 모두 자체 발명 수치가 아니라 실제 공개 이커머스 이벤트 로그(Kaggle) 3종에서
    직접 집계한 값을 사용합니다. 장바구니 이탈률/추천 CVR은 더 이상 목표로 역산하는 값이
    아니라 이 두 확률의 곱/여집합으로 "발생하는" 값입니다 — 그래서 내부 모순이 없습니다.

Kaggle 실측 근거 (data/reference/, 랜덤 행 샘플 기준. 계산 스크립트: 세션 요약에 기록):
  데이터셋         조회->장바구니   장바구니->구매
  REES46 (2019-10/11 랜덤 샘플)     3.60%           45.96%
  Cosmetics Shop (2019-10~2020-02) 59.87%           22.31%
  RetailRocket (전체)               2.58%           32.83%
  -> 3개 중앙값(median) 채택: 조회->장바구니 = 3.60%, 장바구니->구매 = 32.83%
     (Cosmetics의 59.87%는 뷰티 카테고리 특성상 다른 두 데이터셋과 10배 이상 차이나는
      이상치라 평균 대신 중앙값을 사용해 이상치 영향을 배제했습니다.)
  주의: 이 값은 무작위 "행" 샘플에서 집계한 이벤트 타입 간 비율이라 유효하지만, 세션
  연속성은 샘플링 과정에서 보존되지 않습니다. 그래서 세션 체류시간·구매결정 소요일수·
  N일 재구매 타이밍 등 "세션/유저 단위 시퀀스"가 필요한 지표는 Kaggle로 검증할 수
  없고, 아래 PARAMS 안에 "가정(명시)"로 별도 표시했습니다.

A/B 처치 효과(treatment effect) 가정:
  우리 서비스의 핵심 가설("맞춤 추천 노출이 선택 피로를 줄이고 전환을 높인다")은
  Kaggle의 어떤 데이터셋에도 대응물이 없는, 우리만의 미검증 가설입니다. 이 효과 크기를
  꾸며내는 대신, McKinsey의 개인화 매출(revenue) lift 리서치(평균 10~15%, 기업별
  5~25% -- "The value of getting personalization right-or wrong-is multiplying",
  mckinsey.com)를 참고한 보수적 가정으로 +15% 상대 개선을 채택했습니다. 참고로
  Salesforce가 2017년 1.5억 건의 쇼핑 세션을 분석해 보고한 수치(개인화 추천 노출 시
  전환율 최대 4.6배, 장바구니 담기율 +24% -- practicalecommerce.com)는 훨씬 공격적인
  값이지만 벤더 자체 조사라 선택편향 가능성이 있어 채택하지 않았습니다. (이전 버전
  주석의 "McKinsey/Salesforce 등에서 흔히 인용되는 10~30% 범위"는 서로 다른 지표를
  부정확하게 뭉뚱그린 표현이었어서 정정합니다. 자세한 내용은
  data/generated_v2/README.md의 "A/B 처치 효과 가정" 절 참고.)
  이 수치는 "Kaggle 실측"이 아니라 명시적 "가정"입니다.
  적용 범위: 개인화가 실제로 작동하는 경로, 즉 A그룹의 "추천" 진입 경로에만 적용하고
  (검색/GNB 진입, 또는 B그룹은 우리 앱에서 매치스코어/비교 기능이 노출되지 않으므로
  Kaggle 기준 확률을 그대로 사용), 그 외 앱 고유 기능(반응입력, N일 재구매, NPS 등
  Kaggle에 대응물이 없는 모든 지표)에도 동일한 +15%(또는 방향에 따라 -15%) 하나의
  가정 계수만 일괄 적용해 자의적으로 지표마다 다른 폭의 격차를 만들지 않도록 했습니다.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(2026)

START_DATE = datetime(2026, 9, 8)
END_DATE = datetime(2026, 12, 6)
N_DAYS = (END_DATE - START_DATE).days + 1

users_df = pd.read_csv("../data/generated_v2/users_master.csv", parse_dates=["signup_date"])
products_df = pd.read_csv("../data/generated_v2/products_master.csv")
products_df["allergen_groups"] = products_df["allergen_groups"].fillna("")

products_by_species = {
    sp: products_df[products_df.species.isin(["dog/cat", sp])]["product_id"].tolist()
    for sp in ["dog", "cat"]
}
products_by_id = products_df.set_index("product_id")

# ---------------------------------------------------------------------------
# Kaggle 실측값 (median, 위 docstring 참조)
# ---------------------------------------------------------------------------
KAGGLE_VIEW_TO_CART = 0.0360
KAGGLE_CART_TO_PURCHASE = 0.3283

# 개인화 처치 효과 가정 (보수적 +15% 상대 개선, 명시적 가정)
LIFT = 0.15


def lift_up(base, cap=0.97):
    """가정(명시): 값이 클수록 좋은 지표에 대한 A그룹 보수적 상대 개선."""
    return float(min(base * (1 + LIFT), cap))


def lift_down(base, floor=0.01):
    """가정(명시): 값이 작을수록 좋은 지표에 대한 A그룹 보수적 상대 개선."""
    return float(max(base / (1 + LIFT), floor))


# 앱 고유 기능(가설2/3) — Kaggle 대응물 없음. B값은 v1에서 승계한 "가정(명시)" 값이고,
# A값은 전부 위 LIFT 하나로 일괄 산출(v1처럼 지표별로 임의의 큰 격차를 발명하지 않음).
BASE_B = {
    "pdp_dwell_mean_sec": 43.0,          # 가정(명시): 세션 연속성이 없는 샘플이라 Kaggle로 검증 불가
    "decision_days_mean": 2.85,          # 가정(명시): 상동
    "nps_promoter_rate": 0.32,           # 가정(명시): NPS 응답 분포, Kaggle 대응물 없음
    "nps_detractor_rate": 0.07,
    "reaction_input_rate": 0.05,         # 가정(명시): 우리 앱 고유 기능(반려동물 반응 기록)
    "repurchase_30d": 0.05,              # 가정(명시): N일 재구매 타이밍, 세션 연속성 필요해 검증 불가
    "repurchase_60d": 0.08,
    "compare_pdp_rate": 0.10,            # 가정(명시): 우리 앱 고유 비교 기능
    "compare_overall_extra_rate": 0.03,
    "reaction_start_rate": 0.18,         # 가정(명시): 우리 앱 고유 기능
    "reaction_complete_rate": 0.78,
    "reentry_rate": 0.03,
    "valid_reaction_ratio": 0.88,
}

PARAMS = {
    "B": dict(BASE_B),
    "A": {
        "pdp_dwell_mean_sec": lift_up(BASE_B["pdp_dwell_mean_sec"], cap=200),
        "decision_days_mean": lift_down(BASE_B["decision_days_mean"]),
        "nps_promoter_rate": lift_up(BASE_B["nps_promoter_rate"]),
        "nps_detractor_rate": lift_down(BASE_B["nps_detractor_rate"]),
        "reaction_input_rate": lift_up(BASE_B["reaction_input_rate"]),
        "repurchase_30d": lift_up(BASE_B["repurchase_30d"]),
        "repurchase_60d": lift_up(BASE_B["repurchase_60d"]),
        "compare_pdp_rate": lift_up(BASE_B["compare_pdp_rate"]),
        "compare_overall_extra_rate": lift_up(BASE_B["compare_overall_extra_rate"]),
        "reaction_start_rate": lift_up(BASE_B["reaction_start_rate"]),
        "reaction_complete_rate": lift_up(BASE_B["reaction_complete_rate"]),
        "reentry_rate": lift_up(BASE_B["reentry_rate"]),
        "valid_reaction_ratio": lift_up(BASE_B["valid_reaction_ratio"]),
    },
}


def rand_ts(base_date, day_offset_max=0):
    offset_sec = int(RNG.integers(0, 86400 * (day_offset_max + 1)))
    return base_date + timedelta(seconds=offset_sec)


events, orders, reactions = [], [], []


def add_event(user_id, group, session_id, event_type, ts, funnel_step=None, trigger_type=None, **kwargs):
    row = {"event_timestamp": ts, "user_id": user_id, "group": group,
           "session_id": session_id, "event_type": event_type,
           "funnel_step": funnel_step, "trigger_type": trigger_type}
    row.update(kwargs)
    events.append(row)


_order_seq = _session_seq = _reco_seq = 1


def new_order_id():
    global _order_seq
    oid = f"ORD{_order_seq:06d}"; _order_seq += 1
    return oid


def new_session_id():
    global _session_seq
    sid = f"S{_session_seq:07d}"; _session_seq += 1
    return sid


def new_reco_id():
    global _reco_seq
    rid = f"REC{_reco_seq:06d}"; _reco_seq += 1
    return rid


def pick_product(species, group, entry_source, allergy_group, care_need):
    """상품 선택 로직.

    `personalized`는 **"적합도 점수가 화면에 노출됐는가"가 아니라 "개인화된 상품
    큐레이션을 받았는가"** 를 뜻합니다. 이 구분이 중요합니다 —

    - 프로토타입(`prototype/index.html`)에서 적합도 점수는 상품 카드 컴포넌트
      (`pRow`/`pCard`)와 PDP에 모두 붙어 있고, 조건은 진입 경로가 아니라
      "반려동물 프로필이 있는가"뿐입니다. 즉 **점수 자체는 검색·GNB로 들어와도
      보입니다.**
    - 다만 추천 화면의 `recommend()`는 알레르기 상품(`blocked`)을 필터로 제거하고
      적합도순으로 정렬합니다. 검색·GNB에는 그 필터가 없습니다.

    따라서 두 경로는 "점수를 보느냐"가 아니라 **"어떤 상품을 보느냐"** 에서 갈립니다:

    - 추천 경유(A): 적합도 높은 상품만 노출 → 점수가 구매를 **촉진**
    - 검색·GNB: 무작위 상품 → 낮은 점수·알레르기 경고도 노출 → 점수가 구매를
      **억제**할 수 있음(그리고 그건 의도된 동작입니다 — 알레르기 상품 구매 차단)

    검색·GNB 경로에서 촉진과 억제 중 어느 쪽이 큰지는 **아직 측정된 바 없습니다.**
    그래서 이 시뮬레이션은 그 경로의 순효과를 **0으로 가정**합니다(= LIFT 미적용).
    이는 효과크기를 보수적으로 잡는 선택이며, 실측이 아닌 가정입니다.
    자세한 배경은 리포트 2.1·2.4절 참고."""
    pool = products_by_species[species]
    personalized = (entry_source == "recommendation" and group == "A")
    care_matched = False
    if not personalized:
        return str(RNG.choice(pool)), personalized, care_matched

    safe_pool = [pid for pid in pool
                 if not allergy_group or allergy_group not in
                 (products_by_id.loc[pid, "allergen_groups"] or "").split(",")]
    if not safe_pool:
        safe_pool = pool
    if care_need:
        matched_pool = [pid for pid in safe_pool if products_by_id.loc[pid, "function_code"] == care_need]
        if matched_pool:
            return str(RNG.choice(matched_pool)), personalized, True
    return str(RNG.choice(safe_pool)), personalized, care_matched


for _, u in users_df.iterrows():
    user_id = u["user_id"]; group = u["group"]; pet_id = u["pet_id"]
    species = u["pet_species"]; allergy_group = u["pet_allergy_group"] if pd.notna(u["pet_allergy_group"]) else ""
    care_need = u["pet_care_need"] if pd.notna(u["pet_care_need"]) else ""
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
        add_event(user_id, group, session_id, "session_start", sess_start, funnel_step="진입")

        entry_source = str(RNG.choice(["recommendation", "search", "gnb"], p=[0.45, 0.35, 0.20]))
        product_id, personalized, care_matched = pick_product(species, group, entry_source, allergy_group, care_need)
        cat = products_by_id.loc[product_id, "category_code"]

        view_ts = sess_start + timedelta(seconds=int(RNG.integers(5, 120)))

        recommendation_id = None
        if entry_source == "recommendation":
            recommendation_id = new_reco_id()
            add_event(user_id, group, session_id, "recommendation_impression", view_ts - timedelta(seconds=3),
                       product_id=product_id, recommendation_id=recommendation_id)
            add_event(user_id, group, session_id, "select_item", view_ts - timedelta(seconds=2),
                       product_id=product_id, source="recommendation", recommendation_id=recommendation_id)

        add_event(user_id, group, session_id, "view_item", view_ts, funnel_step="상품탐색",
                   product_id=product_id, category_id=cat, entry_source=entry_source,
                   source=("recommendation" if entry_source == "recommendation" else None))
        # 두 필드는 서로 다른 개념입니다 (v1.6에서 분리 — 그 전에는 하나로 뭉쳐 있었습니다).
        #  - match_score_shown: 계획서 V1의 정의 그대로 "적합도 점수·근거 노출 여부".
        #    프로토타입에서 점수는 상품 카드·PDP에 붙어 있고 조건이 진입 경로가 아니라
        #    반려동물 프로필 유무이므로, 기능을 제공받은 A그룹은 전 경로에서 노출됩니다.
        #  - personalized_curation: 추천 화면의 큐레이션(알레르겐 배제 + 건강기능 매칭)을
        #    받았는가. 검색·GNB에는 이 필터가 없으므로 A그룹 안에서도 갈립니다.
        # LIFT는 후자(personalized)에만 걸립니다 — 전자의 순효과는 미측정이라
        # 0으로 가정하기 때문입니다(리포트 2.1절 박스 참고).
        add_event(user_id, group, session_id, "match_score_shown", view_ts + timedelta(seconds=1),
                   product_id=product_id, match_score_shown=(group == "A"),
                   personalized_curation=personalized, care_need_matched=care_matched)

        dwell_sec = max(3, RNG.exponential(p["pdp_dwell_mean_sec"]))
        view_end_ts = view_ts + timedelta(seconds=dwell_sec)
        add_event(user_id, group, session_id, "view_item_end", view_end_ts,
                   product_id=product_id, session_time=round(dwell_sec, 1))

        # --- 비교 화면 진입 (앱 고유 기능, 가정치) ---
        did_compare = False
        if RNG.random() < p["compare_pdp_rate"]:
            comp_ts = view_end_ts + timedelta(seconds=int(RNG.integers(2, 30)))
            add_event(user_id, group, session_id, "view_comparison", comp_ts,
                       product_id=product_id, entry_source="pdp")
            did_compare = True
        elif RNG.random() < p["compare_overall_extra_rate"]:
            comp_ts = sess_start + timedelta(seconds=int(RNG.integers(10, 200)))
            add_event(user_id, group, session_id, "view_comparison", comp_ts,
                       product_id=product_id, entry_source="gnb")
            did_compare = True

        # --- 장바구니 담기 여부: Kaggle 실측 확률 (더 이상 100% 고정 아님) ---
        cart_prob = KAGGLE_VIEW_TO_CART * (1 + LIFT) if personalized else KAGGLE_VIEW_TO_CART
        cart_prob = min(cart_prob, 0.97)
        will_add_to_cart = RNG.random() < cart_prob

        if not will_add_to_cart:
            sess_end_ts = view_end_ts + timedelta(seconds=int(RNG.integers(2, 120)))
            add_event(user_id, group, session_id, "session_end", sess_end_ts,
                       funnel_step="이탈", reason="no_cart")
            continue

        add_to_cart_ts = view_end_ts + timedelta(seconds=int(RNG.integers(1, 20)))
        add_event(user_id, group, session_id, "add_to_cart", add_to_cart_ts, funnel_step="장바구니담기",
                   product_id=product_id, category_id=cat,
                   source=("recommendation" if entry_source == "recommendation" else None),
                   recommendation_id=recommendation_id)

        # --- 구매 전환 여부: Kaggle 실측 확률 (비교 화면을 본 세션은 결정에 더 가까운
        #     상태로 보아 동일한 처치효과 가정(LIFT)을 적용) ---
        purchase_prob = KAGGLE_CART_TO_PURCHASE * (1 + LIFT) if (personalized or did_compare) else KAGGLE_CART_TO_PURCHASE
        purchase_prob = min(purchase_prob, 0.97)
        will_purchase = RNG.random() < purchase_prob

        if will_purchase:
            decision_days = max(0.02, RNG.exponential(p["decision_days_mean"]))
            purchase_ts = view_ts + timedelta(days=decision_days)
            if purchase_ts > END_DATE:
                purchase_ts = END_DATE - timedelta(hours=int(RNG.integers(1, 24)))
            order_id = new_order_id()
            purchase_source = "comparison" if did_compare else ("recommendation" if entry_source == "recommendation" else "direct")

            add_event(user_id, group, session_id, "complete_purchase", purchase_ts, funnel_step="구매완료",
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
            sess_end_ts = add_to_cart_ts + timedelta(seconds=int(RNG.integers(5, 600)))
            add_event(user_id, group, session_id, "session_end", sess_end_ts,
                       funnel_step="이탈(장바구니)", reason="cart_abandoned")
            continue

        add_event(user_id, group, session_id, "session_end", sess_end_ts, funnel_step="구매완료")

    # ---- N일 재구매 퍼널 (가정치, Kaggle로 검증 불가 — 세션 연속성 필요) ----
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
                    product_id2, _, _ = pick_product(species, group, "recommendation", allergy_group, care_need)
                    cat2 = products_by_id.loc[product_id2, "category_code"]
                    sid2 = new_session_id()
                    reco_id2 = new_reco_id()
                    add_event(user_id, group, sid2, "session_start", reco_ts - timedelta(minutes=5), funnel_step="진입")
                    add_event(user_id, group, sid2, "recommendation_impression", reco_ts - timedelta(minutes=4),
                               product_id=product_id2, recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "select_item", reco_ts - timedelta(minutes=3),
                               product_id=product_id2, source="recommendation", recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "add_to_cart", reco_ts - timedelta(minutes=2), funnel_step="장바구니담기",
                               product_id=product_id2, category_id=cat2)
                    order_id2 = new_order_id()
                    add_event(user_id, group, sid2, "complete_purchase", reco_ts, funnel_step="구매완료",
                               order_id=order_id2, product_id=product_id2, category_id=cat2,
                               source="recommendation", recommendation_id=reco_id2)
                    add_event(user_id, group, sid2, "session_end", reco_ts + timedelta(minutes=1), funnel_step="구매완료")
                    order_row2 = {
                        "order_id": order_id2, "user_id": user_id, "group": group,
                        "product_id": product_id2, "category_id": cat2,
                        "purchase_date": reco_ts, "source": "recommendation",
                        "recommendation_id": reco_id2, "session_id": sid2,
                    }
                    orders.append(order_row2)
                    user_orders.append(order_row2)

    # ---- 구매확정 + 배송완료 + 반응입력 퍼널 (가설3, 앱 고유 기능 — 가정치) ----
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

        alarm_ts = delivery_ts + timedelta(hours=int(RNG.integers(1, 12)))
        add_event(user_id, group, o["session_id"], "reaction_require_alarm", alarm_ts,
                   funnel_step="알람노출", trigger_type="delivery_status_complete_d0",
                   order_id=order_id, pet_id=pet_id)

        will_start = RNG.random() < p["reaction_start_rate"]
        if will_start:
            check_ts = alarm_ts + timedelta(hours=int(RNG.integers(1, 48)))
            add_event(user_id, group, o["session_id"], "reaction_check", check_ts,
                       funnel_step="알람확인", order_id=order_id)
            start_ts = check_ts + timedelta(minutes=int(RNG.integers(1, 120)))
            add_event(user_id, group, o["session_id"], "reaction_start", start_ts,
                       funnel_step="입력시작", order_id=order_id, pet_id=pet_id)

            will_complete = RNG.random() < p["reaction_complete_rate"]
            if will_complete:
                complete_ts = start_ts + timedelta(minutes=int(RNG.integers(1, 15)))
                is_valid = RNG.random() < p["valid_reaction_ratio"]
                fstep = "입력완료(유효)" if is_valid else "입력완료(무효)"
                add_event(user_id, group, o["session_id"], "reaction_complete", complete_ts,
                           funnel_step=fstep, order_id=order_id, pet_id=pet_id)
                add_event(user_id, group, o["session_id"], "pet_reaction_created", complete_ts + timedelta(seconds=1),
                           order_id=order_id, pet_id=pet_id, is_valid=is_valid)
                reactions.append({"order_id": order_id, "user_id": user_id, "group": group,
                                   "pet_id": pet_id, "is_valid": is_valid, "reaction_complete_ts": complete_ts})

                if RNG.random() < p["reentry_rate"]:
                    reentry_ts = complete_ts + timedelta(days=int(RNG.integers(1, 10)))
                    if reentry_ts <= END_DATE:
                        sid3 = new_session_id()
                        add_event(user_id, group, sid3, "session_start", reentry_ts - timedelta(minutes=1), funnel_step="진입")
                        add_event(user_id, group, sid3, "recommendation_view", reentry_ts,
                                   funnel_step="재진입", order_id=order_id, entry_source="post_reaction")
                        add_event(user_id, group, sid3, "session_end", reentry_ts + timedelta(minutes=3))
            else:
                dropout_ts = start_ts + timedelta(minutes=int(RNG.integers(1, 30)))
                add_event(user_id, group, o["session_id"], "session_end", dropout_ts,
                           funnel_step="입력중이탈", reason="reaction_input_dropout")

        if RNG.random() < p["reaction_input_rate"] * 0.6:
            review_ts = delivery_ts + timedelta(days=int(RNG.integers(1, 10)))
            if review_ts <= END_DATE:
                add_event(user_id, group, o["session_id"], "review_created", review_ts,
                           order_id=order_id, product_id=o["product_id"])

        nps_trigger_ts = confirm_ts + timedelta(days=3)
        if nps_trigger_ts <= END_DATE:
            add_event(user_id, group, o["session_id"], "nps_popup_impression", nps_trigger_ts,
                       trigger_type="purchase_confirm_d3")
            if RNG.random() < 0.70:
                roll = RNG.random()
                if roll < p["nps_promoter_rate"]:
                    score = int(RNG.integers(9, 11))
                elif roll < p["nps_promoter_rate"] + p["nps_detractor_rate"]:
                    score = int(RNG.integers(0, 7))
                else:
                    score = int(RNG.integers(7, 9))
                add_event(user_id, group, o["session_id"], "nps_score", nps_trigger_ts + timedelta(minutes=1),
                           nps_score=score)

print("events:", len(events))
print("orders:", len(orders))
print("reactions:", len(reactions))

events_df = pd.DataFrame(events).sort_values("event_timestamp").reset_index(drop=True)
orders_df = pd.DataFrame(orders)
reactions_df = pd.DataFrame(reactions)

events_df.to_csv("../data/generated_v2/events_log.csv", index=False)
orders_df.to_csv("../data/generated_v2/orders.csv", index=False)
reactions_df.to_csv("../data/generated_v2/pet_reactions.csv", index=False)
