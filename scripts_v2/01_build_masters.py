# -*- coding: utf-8 -*-
"""
골라주개냥 (우지빌) A/B 테스트 가상 운영 데이터 생성기 — v2 (마스터 데이터)

v1(scripts/01_build_masters.py) 대비 변경점:
  - products_master.csv 를 5개 대분류(사료건식/습식/간식/영양제/용품)의 단순 구조에서,
    사내에서 정리한 "반려동물 상품 분류 체계" 참조표(카테고리/서브카테고리, 건강기능,
    원재료/알레르겐, 영양성분 참조 코드)를 반영한 정규화 스키마로 확장.
    -> products_master.csv (상품 1행) + products_ingredients.csv (상품-원재료, long)
       + products_nutrients.csv (상품-영양성분, long) 3개 파일로 분리.
  - users_master.csv 의 pet_has_allergy(Boolean)를 pet_allergy_group(알레르겐 그룹 코드,
    없으면 공백)으로 세분화하고, 개인화 추천의 근거가 되는 pet_care_need(건강기능 코드)를
    추가. 유병률/보유율 수치 자체는 Kaggle로 검증할 수 없는 반려동물 도메인 값이라
    v1과 동일하게 유지(가정, 아래 명시).

  이 단계(마스터 데이터 구성비)는 A/B 두 그룹이 동일한 분포를 공유하는 카탈로그성
  데이터이며, 그룹별 확률적 가정이 아니므로 Kaggle 데이터셋과 직접 비교할 대상이
  아닙니다. 따라서 "Kaggle 실측 vs 가정" 구분은 02번 스크립트(퍼널 확률)에서만 의미가
  있고, 이 스크립트의 카탈로그 구성비는 전부 "가정(카탈로그 실현성 목적)"입니다.

  기간: 2026-09-08 ~ 2026-12-06 (90일)
  (데이터 수집 계획서 v0.1에는 "2026.09.08 ~ 2026.10.07(가상 90일 데이터셋)"으로
  적혀 있어 날짜 범위와 "90일" 라벨이 서로 맞지 않습니다. v1과의 비교 가능성을
  위해 v1과 동일하게 90일 전체 기간을 사용했습니다.)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

RNG = np.random.default_rng(42)

START_DATE = datetime(2026, 9, 8)
END_DATE = datetime(2026, 12, 6)  # 90일
N_DAYS = (END_DATE - START_DATE).days + 1  # 90

N_PER_GROUP = 2500
N_USERS = N_PER_GROUP * 2

# ---------------------------------------------------------------------------
# 1) 상품 분류 체계 (사내 참조표 그대로 반영, "추가 버전" 기준)
#    category_code, subcategory_code, 적용종(species: dog/cat/both)
# ---------------------------------------------------------------------------
SUBCATS = {
    "FOOD": [
        ("DRY_FOOD", "both"), ("WET_FOOD", "both"), ("FREEZE_DRIED_FOOD", "both"),
        ("BAKED_FOOD", "both"), ("AIR_DRIED_FOOD", "both"), ("RAW_FOOD", "both"),
        ("COOKED_FOOD", "both"), ("SEMI_MOIST_FOOD", "both"),
    ],
    "SUPPLEMENT": [
        ("POWDER_SUPPLEMENT", "both"), ("LIQUID_SUPPLEMENT", "both"),
        ("CHEWABLE_SUPPLEMENT", "both"), ("TABLET_SUPPLEMENT", "both"),
        ("CAPSULE_SUPPLEMENT", "both"), ("PASTE_SUPPLEMENT", "both"),
        ("GEL_SUPPLEMENT", "both"),
    ],
    "TREAT": [
        ("JERKY_TREAT", "dog"), ("WET_TREAT", "both"), ("FREEZE_DRIED_TREAT", "both"),
        ("BISCUIT_TREAT", "both"), ("DENTAL_TREAT", "dog"), ("STICK_TREAT", "both"),
        ("PUREE_TREAT", "cat"), ("CHEW_TREAT", "dog"), ("SAUSAGE_TREAT", "both"),
        ("TOPPING_TREAT", "both"), ("TRAINING_TREAT", "dog"), ("DRINK_SOUT_TREAT", "cat"),
        ("CATNIP_GRASS_TREAT", "cat"),
    ],
    "GOODS": [
        # 참조표에 용품 분류는 없어 v1 수준의 단일 서브카테고리로 유지 (가정)
        ("GENERAL_GOODS", "both"),
    ],
}
N_PER_SUBCAT = {"FOOD": 4, "SUPPLEMENT": 3, "TREAT": 2, "GOODS": 12}

CAT_KOR = {"FOOD": "사료", "SUPPLEMENT": "영양제", "TREAT": "간식", "GOODS": "용품"}
SUBCAT_KOR = {
    "DRY_FOOD": "건식 사료", "WET_FOOD": "습식 사료", "FREEZE_DRIED_FOOD": "동결건조 사료",
    "BAKED_FOOD": "베이크드 사료", "AIR_DRIED_FOOD": "에어드라이 사료", "RAW_FOOD": "생식 사료",
    "COOKED_FOOD": "화식/조리식 사료", "SEMI_MOIST_FOOD": "반습식 사료",
    "POWDER_SUPPLEMENT": "파우더형 영양제", "LIQUID_SUPPLEMENT": "액상형 영양제",
    "CHEWABLE_SUPPLEMENT": "츄어블형 영양제", "TABLET_SUPPLEMENT": "정제형 영양제",
    "CAPSULE_SUPPLEMENT": "캡슐형 영양제", "PASTE_SUPPLEMENT": "페이스트형 영양제",
    "GEL_SUPPLEMENT": "젤형 영양제",
    "JERKY_TREAT": "육포형 간식", "WET_TREAT": "습식/파우치형 간식",
    "FREEZE_DRIED_TREAT": "동결건조 간식", "BISCUIT_TREAT": "비스킷/쿠키형 간식",
    "DENTAL_TREAT": "덴탈껌/구강관리 간식", "STICK_TREAT": "스틱형 간식",
    "PUREE_TREAT": "퓨레/츄르형 간식", "CHEW_TREAT": "씹는 간식", "SAUSAGE_TREAT": "소시지형 간식",
    "TOPPING_TREAT": "토핑용 간식", "TRAINING_TREAT": "훈련용 소형 간식",
    "DRINK_SOUT_TREAT": "음료/수프형 간식", "CATNIP_GRASS_TREAT": "캣닙/캣그라스",
    "GENERAL_GOODS": "용품",
}

# 건강기능 코드 (참조표 그대로)
FUNCTIONS = [
    "GENERAL", "JOINT", "SKIN_COAT", "GUT", "WEIGHT_CONTROL", "DENTAL", "KIDNEY",
    "URINARY", "EYE", "HEART", "LIVER", "IMMUNE", "HAIRBALL", "COGNITIVE",
    "RESPIRATORY", "STRESS_CALMING", "HYPOALLERGENIC",
]
# HAIRBALL은 고양이 전용, 그 외 대부분 공통이라고 참조표에 명시됨
FUNCTION_SPECIES = {"HAIRBALL": "cat"}

# 원재료(육류/어류/곡물/기타) + 알레르겐 그룹. 독성 성분(GARLIC/ONION/XYLITOL/GRAPE/
# RAISIN/CACAO 등)은 실제 상품 배합에 쓰이지 않으므로 카탈로그 생성에서 제외하고,
# 유저 알레르기 매칭/배제 로직에서만 참조되는 원재료만 사용.
PROTEIN_INGREDIENTS = [
    ("CHICKEN_MEAT", "CHICKEN"), ("BEEF_MEAT", "BEEF"), ("PORK_MEAT", "PORK"),
    ("LAMB_MEAT", "LAMB"), ("DUCK_MEAT", "DUCK"), ("TURKEY_MEAT", "TURKEY"),
    ("SALMON", "FISH"), ("TUNA", "FISH"), ("VENISON", "VENISON"), ("INSECT", "INSECT"),
]
HYDROLYZED_PROTEIN = ("HYDRO_CHICKEN", "CHICKEN")  # 저알러지(HYPOALLERGENIC) 전용
FILLER_INGREDIENTS = [
    ("RICE", "RICE"), ("OAT", "OAT"), ("SWEET_POTATO", None), ("POTATO", "POTATO"),
    ("PEA", None), ("CORN", "CORN"), ("WHEAT", "WHEAT"),
]
EXTRA_ALLERGEN_INGREDIENTS = [("SOYBEAN", "SOY"), ("EGG", "EGG"), ("MILK", "DAIRY"), ("WHEY", "DAIRY")]

# 건강기능별 연계 영양성분 (참조표의 "주요 연동 대상"/비고 기반)
FUNCTION_NUTRIENTS = {
    "GENERAL": [("VITAMIN_A", "IU", (2000, 8000)), ("VITAMIN_E", "mg", (10, 60)), ("ZINC", "mg", (5, 30))],
    "JOINT": [("GLUCOSAMINE", "mg", (200, 1500)), ("CHONDROITIN", "mg", (100, 800)), ("MSM", "mg", (50, 400))],
    "SKIN_COAT": [("OMEGA3", "mg", (100, 900)), ("OMEGA6", "mg", (100, 700)), ("BIOTIN", "mg", (0.1, 2.0))],
    "GUT": [("PROBIOTICS", "CFU", (1e6, 1e9)), ("PREBIOTICS", "mg", (50, 500)), ("FOS", "mg", (20, 200))],
    "WEIGHT_CONTROL": [("L_CARNITINE", "mg", (50, 300)), ("CRUDE_FIBER", "%", (3.0, 8.0))],
    "DENTAL": [("CRUDE_FIBER", "%", (2.0, 6.0))],
    "KIDNEY": [("PHOSPHORUS", "%", (0.2, 0.5)), ("POTASSIUM", "%", (0.4, 0.9))],
    "URINARY": [("CRANBERRY", "mg", (20, 200)), ("MAGNESIUM", "%", (0.05, 0.12))],
    "EYE": [("LUTEIN", "mg", (1, 20))],
    "HEART": [("COQ10", "mg", (5, 60)), ("TAURINE", "mg", (200, 2000))],
    "LIVER": [("MILK_THISTLE", "mg", (20, 200)), ("SILYMARIN", "mg", (10, 100))],
    "IMMUNE": [("BETA_GLUCAN", "mg", (10, 150)), ("VITAMIN_E", "mg", (10, 80))],
    "HAIRBALL": [("CRUDE_FIBER", "%", (4.0, 10.0)), ("PROBIOTICS", "CFU", (1e6, 5e8))],
    "COGNITIVE": [("OMEGA3", "mg", (100, 600)), ("VITAMIN_E", "mg", (20, 80))],
    "RESPIRATORY": [("L_LYSINE", "mg", (100, 1000))],
    "STRESS_CALMING": [("L_THEANINE", "mg", (10, 150))],
    "HYPOALLERGENIC": [("CRUDE_PROTEIN", "%", (18.0, 26.0))],
}

# 사료/간식 서브카테고리별 일반영양성분 범위: (조단백%, 조지방%, 수분%, 조섬유%, 열량kcal/100g)
FOOD_MACROS = {
    "DRY_FOOD": ((22, 32), (10, 18), (7, 10), (1.5, 4.5), (340, 420)),
    "WET_FOOD": ((7, 12), (3, 8), (75, 82), (0.5, 2.0), (70, 110)),
    "FREEZE_DRIED_FOOD": ((32, 48), (15, 28), (3, 6), (1.0, 3.0), (400, 520)),
    "BAKED_FOOD": ((22, 30), (10, 16), (10, 14), (1.5, 4.0), (330, 400)),
    "AIR_DRIED_FOOD": ((28, 38), (14, 22), (13, 18), (1.0, 3.5), (380, 450)),
    "RAW_FOOD": ((14, 20), (8, 16), (65, 75), (0.3, 1.5), (150, 220)),
    "COOKED_FOOD": ((12, 18), (5, 12), (65, 75), (0.5, 2.0), (120, 180)),
    "SEMI_MOIST_FOOD": ((18, 24), (8, 14), (25, 35), (1.0, 3.0), (260, 320)),
}
TREAT_MACROS_DEFAULT = ((15, 35), (5, 20), (10, 40), (0.5, 4.0), (200, 400))

FUNC_WEIGHTS_FOOD_TREAT = {"GENERAL": 0.65}
NON_GENERAL_FUNCS = [f for f in FUNCTIONS if f != "GENERAL"]


def pick_species_users(subcat_species):
    if subcat_species == "both":
        return "dog/cat"
    return subcat_species


def build_products():
    prod_rows, ing_rows, nut_rows = [], [], []
    pid = 1
    for cat_code, subcats in SUBCATS.items():
        n_each = N_PER_SUBCAT[cat_code]
        for subcat_code, species in subcats:
            for i in range(n_each):
                product_id = f"P{pid:04d}"
                pid += 1

                if cat_code == "GOODS":
                    prod_rows.append({
                        "product_id": product_id, "category_code": cat_code,
                        "subcategory_code": subcat_code,
                        "product_name": f"{SUBCAT_KOR[subcat_code]} 상품 {i+1}",
                        "species": pick_species_users(species),
                        "function_code": "GENERAL", "price_krw": int(RNG.integers(5000, 60000)),
                    })
                    continue

                # 건강기능 배정: FOOD/TREAT는 65% GENERAL, SUPPLEMENT는 15% GENERAL
                if cat_code == "SUPPLEMENT":
                    func = "GENERAL" if RNG.random() < 0.15 else str(RNG.choice(NON_GENERAL_FUNCS))
                else:
                    func = "GENERAL" if RNG.random() < 0.65 else str(RNG.choice(NON_GENERAL_FUNCS))
                # 종 제약이 있는 기능(HAIRBALL 등)은 상품의 적용종에 맞춰 재보정
                if func in FUNCTION_SPECIES and species not in ("both", FUNCTION_SPECIES[func]):
                    func = "GENERAL"
                if func == "HYPOALLERGENIC" and cat_code != "SUPPLEMENT":
                    pass  # FOOD도 저알러지 라인 존재 가능 (가수분해 단백)

                is_hypo = (func == "HYPOALLERGENIC")

                # 카테고리별 실제 시장 가격대(사업팀 제공 기준가)에 맞춘 가격 샘플링.
                # FOOD는 소용량(1~2만)~대용량/기능성(4~6만)을 한 범위로 블렌딩,
                # TREAT는 일반(5천~1만 중심)~프리미엄(1~2만)을 블렌딩, SUPPLEMENT는
                # "2~4만원대 중심" 그대로. RNG.integers() 호출 1회는 기존과 동일하게
                # 유지해(호출 횟수 불변) 이후 유저/펫 속성 생성 스트림에 영향이 없도록 함.
                if cat_code == "SUPPLEMENT":
                    price = int(RNG.integers(20000, 40000))
                elif cat_code == "TREAT":
                    price = int(RNG.integers(5000, 20000))
                else:  # FOOD
                    price = int(RNG.integers(10000, 60000))

                prod_rows.append({
                    "product_id": product_id, "category_code": cat_code,
                    "subcategory_code": subcat_code,
                    "product_name": f"{SUBCAT_KOR[subcat_code]} 상품 {i+1}",
                    "species": pick_species_users(species),
                    "function_code": func,
                    "price_krw": price,
                })

                # --- 원재료 구성 (FOOD/TREAT만; SUPPLEMENT는 활성성분 위주라 생략) ---
                if cat_code in ("FOOD", "TREAT"):
                    if is_hypo:
                        primary = [HYDROLYZED_PROTEIN]
                    else:
                        n_protein = 1 if RNG.random() < 0.7 else 2
                        idx = RNG.choice(len(PROTEIN_INGREDIENTS), size=n_protein, replace=False)
                        primary = [PROTEIN_INGREDIENTS[j] for j in idx]
                    n_filler = int(RNG.integers(1, 3))
                    fidx = RNG.choice(len(FILLER_INGREDIENTS), size=n_filler, replace=False)
                    fillers = [FILLER_INGREDIENTS[j] for j in fidx]
                    extras = []
                    # 저알러지 라인이 아닌 상품 중 8%는 대두/유제품/계란 등 부가 알레르겐 원료 포함(예외 케이스 재현용)
                    if not is_hypo and RNG.random() < 0.08:
                        extras = [EXTRA_ALLERGEN_INGREDIENTS[int(RNG.integers(0, len(EXTRA_ALLERGEN_INGREDIENTS)))]]

                    order = 1
                    for ing_code, allergen in primary + fillers + extras:
                        ing_rows.append({
                            "product_id": product_id, "ingredient_code": ing_code,
                            "allergen_group": allergen if allergen else "",
                            "ingredient_order": order,
                        })
                        order += 1

                    # --- 일반영양성분 ---
                    if cat_code == "FOOD":
                        (p_lo, p_hi), (f_lo, f_hi), (m_lo, m_hi), (fb_lo, fb_hi), (e_lo, e_hi) = FOOD_MACROS[subcat_code]
                    else:
                        (p_lo, p_hi), (f_lo, f_hi), (m_lo, m_hi), (fb_lo, fb_hi), (e_lo, e_hi) = TREAT_MACROS_DEFAULT
                    macro_vals = {
                        "CRUDE_PROTEIN": ("%", round(RNG.uniform(p_lo, p_hi), 1)),
                        "CRUDE_FAT": ("%", round(RNG.uniform(f_lo, f_hi), 1)),
                        "MOISTURE": ("%", round(RNG.uniform(m_lo, m_hi), 1)),
                        "CRUDE_FIBER": ("%", round(RNG.uniform(fb_lo, fb_hi), 1)),
                        "ENERGY": ("kcal/100g", round(RNG.uniform(e_lo, e_hi), 0)),
                        "CALCIUM": ("%", round(RNG.uniform(0.8, 1.8), 2)),
                        "PHOSPHORUS": ("%", round(RNG.uniform(0.6, 1.3), 2)),
                        "SODIUM": ("%", round(RNG.uniform(0.2, 0.6), 2)),
                    }
                    for code, (unit, val) in macro_vals.items():
                        nut_rows.append({"product_id": product_id, "nutrient_code": code,
                                          "unit": unit, "value": val})
                    # 고양이 대상 상품은 타우린 필수 표기 (참조표: "고양이에서 특히 중요")
                    if species in ("cat", "both"):
                        nut_rows.append({"product_id": product_id, "nutrient_code": "TAURINE",
                                          "unit": "mg", "value": round(RNG.uniform(100, 1500), 0)})

                # --- 건강기능 연계 영양성분 (모든 카테고리 공통, GENERAL 포함) ---
                for nut_code, unit, (lo, hi) in FUNCTION_NUTRIENTS.get(func, []):
                    nut_rows.append({"product_id": product_id, "nutrient_code": nut_code,
                                      "unit": unit, "value": round(float(RNG.uniform(lo, hi)), 2)})

    return pd.DataFrame(prod_rows), pd.DataFrame(ing_rows), pd.DataFrame(nut_rows)


products_df, ingredients_df, nutrients_df = build_products()

# 상품이 보유한 알레르겐 그룹 집합 (개인화/배제 로직에서 사용할 파생 컬럼)
allergen_map = (ingredients_df[ingredients_df.allergen_group != ""]
                 .groupby("product_id")["allergen_group"].apply(lambda s: ",".join(sorted(set(s)))))
products_df["allergen_groups"] = products_df["product_id"].map(allergen_map).fillna("")

ALLERGEN_GROUPS_POOL = sorted(set(
    g for cell in products_df["allergen_groups"] for g in cell.split(",") if g
))


def build_users():
    rows = []
    signup_days = RNG.integers(0, N_DAYS, size=N_USERS)
    groups = (["A"] * N_PER_GROUP) + (["B"] * N_PER_GROUP)
    RNG.shuffle(groups)

    pet_species = RNG.choice(["dog", "cat"], size=N_USERS, p=[0.55, 0.45])
    pet_ages = RNG.integers(1, 15, size=N_USERS)
    pet_weights = np.round(RNG.uniform(1.5, 35.0, size=N_USERS), 1)

    # 알레르기 보유율(22%)·건강 관심사 보유율(35%)은 v1과 동일 수치를 유지한 가정입니다.
    # 반려동물 알레르기 유병률/건강기능 관심사 비율에 대응하는 Kaggle 공개 데이터셋이
    # 없어 검증할 수 없으므로, 임의로 바꾸는 대신 기존 가정을 그대로 명시적으로 승계합니다.
    has_allergy = RNG.random(size=N_USERS) < 0.22
    has_care_need = RNG.random(size=N_USERS) < 0.35

    for i in range(N_USERS):
        signup_dt = START_DATE + timedelta(days=int(signup_days[i]),
                                            seconds=int(RNG.integers(0, 86400)))
        allergy_group = str(RNG.choice(ALLERGEN_GROUPS_POOL)) if has_allergy[i] else ""
        # 건강 관심사는 반려동물 종에 맞는 기능 코드 중에서 배정
        if has_care_need[i]:
            candidates = [f for f in NON_GENERAL_FUNCS
                          if f not in FUNCTION_SPECIES or FUNCTION_SPECIES[f] == pet_species[i]]
            care_need = str(RNG.choice(candidates))
        else:
            care_need = ""
        rows.append({
            "user_id": f"U{i+1:05d}",
            "group": groups[i],
            "signup_date": signup_dt,
            "pet_id": f"PET{i+1:05d}",
            "pet_species": pet_species[i],
            "pet_age": int(pet_ages[i]),
            "pet_weight_kg": float(pet_weights[i]),
            "pet_allergy_group": allergy_group,
            "pet_care_need": care_need,
        })
    return pd.DataFrame(rows)


users_df = build_users()

print("users:", len(users_df), "A:", (users_df.group == "A").sum(), "B:", (users_df.group == "B").sum())
print("products:", len(products_df), "ingredients rows:", len(ingredients_df), "nutrients rows:", len(nutrients_df))
print("allergy 보유:", (users_df.pet_allergy_group != "").sum(), "care_need 보유:", (users_df.pet_care_need != "").sum())

users_df.to_csv("../data/generated_v2/users_master.csv", index=False)
products_df.to_csv("../data/generated_v2/products_master.csv", index=False)
ingredients_df.to_csv("../data/generated_v2/products_ingredients.csv", index=False)
nutrients_df.to_csv("../data/generated_v2/products_nutrients.csv", index=False)
