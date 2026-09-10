# -*- coding: utf-8 -*-
"""
00_extract_reference_stats.py — 공개 데이터셋 원본에서 참조 통계만 추출

원본 CSV는 저장소에 넣지 않습니다(용량). Kaggle에서 받아 `data/reference/_raw/`에
두고 이 스크립트를 돌리면, 파이프라인이 실제로 참조하는 작은 집계 파일만
`data/reference/derived/`에 생성됩니다.

  data/reference/_raw/train_40k.csv                                  (22.8MB, 미커밋)
  data/reference/_raw/costinflation-petflation-prices-*.csv          (45.5MB, 미커밋)
      ↓
  data/reference/amazon_pet_reviews/train_40k_pet_supplies.csv       (2.8MB, 커밋)
  data/reference/derived/*.csv                                       (수 KB, 커밋)

원본 출처는 `data/reference/README.md` 참고. 원본이 없으면 해당 절만 건너뜁니다.
"""
import glob
import os

import pandas as pd

RAW = "../data/reference/_raw/"
OUT_DERIVED = "../data/reference/derived/"
OUT_SAMPLE = "../data/reference/amazon_pet_reviews/"

# 우리 카탈로그(category_code)로의 매핑. Cat3에 없는 값은 전부 GOODS로 묶습니다.
CAT3_TO_OURS = {"food": "FOOD", "treats": "TREAT", "health supplies": "SUPPLEMENT"}


def extract_amazon_pet_reviews():
    """Hierarchical text classification (Amazon 리뷰 40k) → 평점 분포·종 구성비."""
    src = os.path.join(RAW, "train_40k.csv")
    if not os.path.exists(src):
        print(f"[건너뜀] {src} 없음")
        return

    df = pd.read_csv(src)
    pet = df[df.Cat1 == "pet supplies"].copy()
    pet.to_csv(OUT_SAMPLE + "train_40k_pet_supplies.csv", index=False, encoding="utf-8-sig")

    # --- 평점 분포 (주 산출물)
    dist = (pet.Score.value_counts().sort_index().rename("건수").to_frame())
    dist["비율_pct"] = (100 * dist.건수 / len(pet)).round(2)
    dist.index.name = "평점"
    dist.to_csv(OUT_DERIVED + "amazon_pet_rating_dist.csv", encoding="utf-8-sig")

    # --- 우리 카테고리로 매핑한 평점 (개/고양이 상품만)
    dogcat = pet[pet.Cat2.isin(["dogs", "cats"])].copy()
    dogcat["our_category"] = dogcat.Cat3.map(CAT3_TO_OURS).fillna("GOODS")
    by_cat = dogcat.groupby("our_category").Score.agg(["count", "mean"]).round(3)
    by_cat["5점_pct"] = dogcat.groupby("our_category").Score.apply(lambda s: 100 * (s == 5).mean()).round(1)
    by_cat["1점_pct"] = dogcat.groupby("our_category").Score.apply(lambda s: 100 * (s == 1).mean()).round(1)
    by_cat.to_csv(OUT_DERIVED + "amazon_pet_rating_by_category.csv", encoding="utf-8-sig")

    # --- 종 구성비 (개:고양이)
    species = dogcat.Cat2.value_counts().rename("건수").to_frame()
    species["비율_pct"] = (100 * species.건수 / len(dogcat)).round(1)
    species.index.name = "species"
    species.to_csv(OUT_DERIVED + "amazon_pet_species_mix.csv", encoding="utf-8-sig")

    print("=" * 64)
    print(f"Amazon pet supplies 리뷰 {len(pet):,}건 (상품 {pet.productId.nunique():,}개)")
    print("=" * 64)
    print(dist.to_string())
    print(f"  평균 {pet.Score.mean():.3f}점")
    print()
    print(by_cat.to_string())
    print()
    print(species.to_string())
    print()


def extract_petflation_prices():
    """119K Prices: Petflation 2026 → 카테고리별 정규화 가격 분포."""
    hits = glob.glob(os.path.join(RAW, "costinflation-petflation-prices-*.csv"))
    if not hits:
        print(f"[건너뜀] {RAW}costinflation-petflation-prices-*.csv 없음")
        return

    df = pd.read_csv(hits[0], dtype={"geography_id": "string"})
    ok = df.dropna(subset=["normalized_price_amount"])

    stats = ok.groupby("series_id").normalized_price_amount.describe(
        percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]
    ).round(2)
    # 분포의 "모양"만 빌려 쓰기 위한 지표: 중앙값 대비 배수
    stats["p90_over_p50"] = (stats["90%"] / stats["50%"]).round(3)
    stats["p10_over_p50"] = (stats["10%"] / stats["50%"]).round(3)
    stats["cv"] = (stats["std"] / stats["mean"]).round(3)
    stats.to_csv(OUT_DERIVED + "petflation_price_stats.csv", encoding="utf-8-sig")

    print("=" * 64)
    print(f"Petflation 정규화 가격 {len(ok):,}행 / 전체 {len(df):,}행")
    print("=" * 64)
    print(stats[["count", "50%", "p10_over_p50", "p90_over_p50", "cv"]].to_string())
    print()


if __name__ == "__main__":
    for d in (OUT_DERIVED, OUT_SAMPLE):
        os.makedirs(d, exist_ok=True)
    extract_amazon_pet_reviews()
    extract_petflation_prices()
    print("참조 통계 추출 완료 → data/reference/derived/")
