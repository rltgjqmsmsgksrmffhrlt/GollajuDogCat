# amazon_pet_reviews/ — Amazon 반려동물 상품 리뷰 (평점 분포 실측)

- **출처**: [Hierarchical text classification](https://www.kaggle.com/datasets/kashnitsky/hierarchical-text-classification)
  (Kaggle, Yury Kashnitsky, CC0: Public Domain)
- **원본**: `train_40k.csv` (22.8MB, 40,000건) — 6개 대분류(toys games / health personal care /
  beauty / baby products / **pet supplies** / grocery gourmet food)의 Amazon 상품 리뷰.
  3단계 계층 분류(Cat1/Cat2/Cat3)와 1~5점 평점(Score)이 함께 들어 있습니다.
- **이 폴더의 파일**: 원본 40,000건 중 `Cat1 == "pet supplies"` **4,862건만 필터**한
  `train_40k_pet_supplies.csv` (2.8MB, 상품 2,067개 / 유저 4,731명).
  원본 전체는 저장소에 넣지 않습니다 — 재현하려면 위 링크에서 받아
  `data/reference/_raw/train_40k.csv`에 두고 `scripts_v2/00_extract_reference_stats.py`를
  실행하세요.

## 왜 참조하는가

시뮬레이션의 `review_created` 이벤트는 **별점 값을 생성하지 않는데**, FE 프로토타입에는
별점 1~5 입력 화면이 있습니다. 그 빈칸을 채울 때 쓸 실측 분포입니다.

## 추출한 실측값

**평점 분포** (`derived/amazon_pet_rating_dist.csv`) — 전형적인 J자 분포입니다.

| 평점 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 비율 | 11.33% | 6.21% | 8.33% | 15.34% | **58.78%** |

평균 **4.040점** / 중앙값 5점.

**우리 카테고리로 매핑한 평점** (`derived/amazon_pet_rating_by_category.csv`) —
Cat3를 `food→FOOD`, `treats→TREAT`, `health supplies→SUPPLEMENT`, 나머지→`GOODS`로 묶고,
개·고양이 상품(4,389건)만 집계했습니다.

| 카테고리 | n | 평균 | 5점 비율 | 1점 비율 |
|---|---|---|---|---|
| TREAT | 281 | **4.409** | 71.9% | 6.0% |
| SUPPLEMENT | 573 | 4.192 | 68.6% | 12.0% |
| FOOD | 128 | 4.125 | 68.8% | 14.8% |
| GOODS | 3,407 | **4.002** | 56.4% | 11.3% |

간식이 가장 높고 용품이 가장 낮습니다.

**종 구성비** (`derived/amazon_pet_species_mix.csv`) — 개 59.5% : 고양이 40.5%.

## ⚠️ 쓸 때 주의할 것

1. **프로토타입 평점이 낙관적입니다.** `prototype/index.html`의 상품 평점은 4.3~4.8
   (평균 약 4.55)인데 실측은 **4.040**입니다. 리뷰 데이터를 생성할 때 프로토타입 값을
   그대로 따르면 0.5점만큼 낙관 편향이 들어갑니다.
2. **카테고리 구성비는 이 데이터로 바꾸면 안 됩니다.** 리뷰 건수 기준으로는
   GOODS가 77.6%인데 우리 카탈로그는 FOOD가 35.2%입니다. 이건 우리 설계가 틀린 게
   아니라 **채널이 다르기 때문**입니다 — 사료는 무겁고 부피가 커서 당시 아마존보다
   마트·펫샵에서 사는 품목이었고, 우리 앱은 애초에 사료 맞춤 추천이 핵심입니다.
   또한 이건 **상품 수가 아니라 리뷰 수** 분포입니다.
3. **오래된 데이터입니다.** `Time` 필드 최댓값이 1.34e9(2012년)입니다. 그 사이
   이커머스 평점 인플레이션이 있었으므로 절대값보다 **분포의 모양**(J자, 카테고리 간
   순서)을 참고하는 쪽이 안전합니다.
4. **종 구성비는 우리 가정과 잘 맞습니다.** 시뮬레이션 유저의 반려동물은
   개 54.7% : 고양이 45.3%로, 실측(59.5:40.5)과 5%p 차이입니다 — 기존 가정이
   합리적이었음을 뒷받침합니다.
