# derived/ — 원본에서 추출한 참조 통계

원본 데이터셋은 용량이 커서 저장소에 넣지 않습니다. 대신 `scripts_v2/00_extract_reference_stats.py`가
**파이프라인이 실제로 참조하는 집계값만** 이 폴더에 뽑아둡니다(파일당 수백 바이트~수 KB).

| 파일 | 내용 | 원본 |
|---|---|---|
| `amazon_pet_rating_dist.csv` | 반려동물 상품 리뷰 평점 1~5점 분포 | [Hierarchical text classification](https://www.kaggle.com/datasets/kashnitsky/hierarchical-text-classification) |
| `amazon_pet_rating_by_category.csv` | FOOD/TREAT/SUPPLEMENT/GOODS별 평균 평점 | 〃 |
| `amazon_pet_species_mix.csv` | 개:고양이 상품 구성비 | 〃 |
| `petflation_price_stats.csv` | 카테고리별 정규화 가격 분위수·변동계수 | [119K Prices: Petflation 2026](https://www.kaggle.com/datasets/costinflation/119k-prices-petflation-2026) *(미추출)* |

## 재현 방법

원본을 Kaggle에서 받아 `data/reference/_raw/`에 두고(이 폴더는 `.gitignore` 처리됨):

```bash
cd scripts_v2
python3 00_extract_reference_stats.py
```

원본이 없는 데이터셋은 해당 절만 건너뛰므로, 가진 것만으로도 실행됩니다.
