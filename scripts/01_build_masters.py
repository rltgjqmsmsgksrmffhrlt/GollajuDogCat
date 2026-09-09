# -*- coding: utf-8 -*-
"""
골라주개냥 (우지빌) A/B 테스트 가상 운영 데이터 생성기
- 기간: 2026-09-08 ~ 2026-12-06 (90일)
- A/B 각 2,500명, 총 5,000명 (90일간 선형 유입)
- 가설1: 선택 피로도 해소 / 가설2: 서비스 충성도 / 가설3: 유저 데이터 확보
- 원본 문서(우지빌 검증 가설)의 A/B 기준치를 목표로 확률 파라미터 역산
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid

RNG = np.random.default_rng(42)

START_DATE = datetime(2026, 9, 8)
END_DATE = datetime(2026, 12, 6)  # 90일
N_DAYS = (END_DATE - START_DATE).days + 1  # 90

N_PER_GROUP = 2500
N_USERS = N_PER_GROUP * 2

CATEGORIES = [
    ("CAT_FOOD_DRY", "사료(건식)"),
    ("CAT_FOOD_WET", "사료(습식)"),
    ("CAT_SNACK", "간식"),
    ("CAT_SUPPLEMENT", "영양제"),
    ("CAT_GOODS", "용품"),
]
N_PRODUCTS_PER_CAT = 12

# ---------------------------------------------------------------------------
# 0. 상품 마스터
# ---------------------------------------------------------------------------
def build_products():
    rows = []
    pid = 1
    for cat_id, cat_name in CATEGORIES:
        for i in range(N_PRODUCTS_PER_CAT):
            rows.append({
                "product_id": f"P{pid:04d}",
                "category_id": cat_id,
                "category_name": cat_name,
                "product_name": f"{cat_name} 상품 {i+1}",
            })
            pid += 1
    return pd.DataFrame(rows)

products_df = build_products()

# ---------------------------------------------------------------------------
# 1. 유저 마스터 (가입일, 그룹 배정, 반려동물 프로필)
# ---------------------------------------------------------------------------
def build_users():
    rows = []
    # 90일 동안 선형 유입 (약간의 주말 변동 추가)
    signup_days = RNG.integers(0, N_DAYS, size=N_USERS)
    groups = (["A"] * N_PER_GROUP) + (["B"] * N_PER_GROUP)
    RNG.shuffle(groups)

    pet_species = RNG.choice(["dog", "cat"], size=N_USERS, p=[0.55, 0.45])
    pet_ages = RNG.integers(1, 15, size=N_USERS)
    pet_weights = np.round(RNG.uniform(1.5, 35.0, size=N_USERS), 1)
    has_allergy = RNG.choice([True, False], size=N_USERS, p=[0.22, 0.78])

    for i in range(N_USERS):
        signup_dt = START_DATE + timedelta(days=int(signup_days[i]),
                                            seconds=int(RNG.integers(0, 86400)))
        rows.append({
            "user_id": f"U{i+1:05d}",
            "group": groups[i],
            "signup_date": signup_dt,
            "pet_id": f"PET{i+1:05d}",
            "pet_species": pet_species[i],
            "pet_age": int(pet_ages[i]),
            "pet_weight_kg": float(pet_weights[i]),
            "pet_has_allergy": bool(has_allergy[i]),
        })
    return pd.DataFrame(rows)

users_df = build_users()

print("users:", len(users_df), "A:", (users_df.group == "A").sum(), "B:", (users_df.group == "B").sum())
users_df.to_csv("../data/generated/users_master.csv", index=False)
products_df.to_csv("../data/generated/products_master.csv", index=False)
