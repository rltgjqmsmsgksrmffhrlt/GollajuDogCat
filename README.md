# 골라주개냥(우지빌) — A/B 테스트 데이터 수집 계획 & 가상 운영 데이터

KT TechUP 골라주개냥(우지빌) 프로젝트의 KPI 검증용 데이터 수집 계획서와,
이를 기반으로 생성한 90일치 가상 A/B 테스트 운영 데이터 및 퍼널·코호트 분석 결과물입니다.

## 프로젝트 배경

골라주개냥은 반려동물 맞춤 상품 추천 D2C 이커머스 서비스입니다.
"추천 근거·점수 노출이 선택 피로도를 줄이고 구매 전환·서비스 충성도·데이터 확보를
개선한다"는 3개 핵심 가설을 검증하기 위한 데이터 설계 및 시뮬레이션을 담고 있습니다.

| 가설 | 요지 |
|---|---|
| 1. 선택 피로도 해소 | 추천 근거·점수 제공(A) 시 장바구니 이탈률↓, 구매전환율↑ |
| 2. 서비스 충성도 | 고도화된 맞춤 추천·비교 경험이 서비스 충성도(NPS)를 높인다 |
| 3. 유저 데이터 확보 | 반응 기록이 추천에 반영됨을 인지하면 반응 기록률이 높아진다 |

## 디렉토리 구조

```
.
├── data/
│   ├── planning/          # 데이터 수집 계획서 (raw 필드 정의, 원본 자료)
│   │   ├── 데이터_수집_계획표.xlsx      # v1(data/generated/) 생성 근거 원본
│   │   └── 데이터_수집_계획표_V1.xlsx   # v2(data/generated_v2/) 생성 근거, 가설별 시트로 재구성된 정식판
│   └── generated/         # 시뮬레이션으로 생성한 가상 운영 데이터 + 분석 결과물
│       ├── users_master.csv
│       ├── products_master.csv
│       ├── orders.csv
│       ├── pet_reactions.csv
│       ├── events_log.csv                    # 통합 이벤트 로그 (약 27만 건)
│       ├── funnel1_purchase_journey.csv       # 가설1 구매 여정 퍼널
│       ├── funnel2_reaction_journey.csv       # 가설3 반응입력 여정 퍼널
│       ├── cohort_A_repurchase_pct.csv        # A그룹 코호트별 재구매율
│       ├── cohort_B_repurchase_pct.csv        # B그룹 코호트별 재구매율
│       └── AB테스트_가상데이터_분석요약.xlsx   # 지표 검증표 + 퍼널 차트 + 코호트 테이블
├── scripts/                # 가상 데이터 생성 파이프라인 (01→05 순서로 실행)
├── docs/                   # 설계 근거, 검증 로그 등 부가 문서
├── CLAUDE.md                # Claude Code가 이 저장소를 이해하기 위한 컨텍스트
├── requirements.txt
├── .gitattributes           # (일반 파일로 관리 - 아래 "Git LFS 대신 일반 파일로 관리하는 이유" 참고)
└── .gitignore
```

## 데이터 생성 파이프라인 재실행

```bash
pip install -r requirements.txt
cd scripts
python3 01_build_masters.py           # 유저/상품 마스터 생성
python3 02_simulate_events.py         # 이벤트 로그 시뮬레이션 (약 1분 소요)
python3 03_validate_metrics.py        # 생성 데이터의 AB 지표를 원본 목표치와 비교 검증
python3 04_funnel_cohort_analysis.py  # 퍼널/코호트 분석
python3 05_build_report.py            # 최종 xlsx 리포트 생성
```

모든 스크립트는 난수 시드(`np.random.default_rng(2026)` 등)가 고정되어 있어
**동일한 입력으로 재실행하면 항상 같은 데이터가 생성**됩니다.

## 가상 데이터 생성 개요

- 기간: 2026-09-08 ~ 2026-12-06 (90일)
- 규모: A/B 각 2,500명 (총 5,000명), 90일간 순차 유입
- 이벤트 로그 약 27만 건, 주문 약 1.2만 건
- 각 지표는 원본 계획서의 A/B 기준치를 목표 확률로 삼아 역산 생성 (검정력 분석 등 정밀 통계는 제외한 근사 시뮬레이션)

### 알려진 한계

`장바구니 이탈률(A 목표 40%)`과 `추천상품 CVR(A 목표 3.3%)`는 원본 문서에서 서로 다른
벤치마크 출처(전자상거래 일반 이탈률 vs 반려동물 카테고리 CVR)를 사용하고 있어, 동일 세션
모집단 안에서 두 값을 동시에 정확히 재현하는 것이 수학적으로 불가능합니다. 본 데이터는
추천상품 CVR·비교 후 전환율 등 세부 지표를 우선 재현했고, 장바구니 이탈률은 그 결과로 나온
근사치(A 56.6%)를 사용했습니다. 자세한 지표별 검증 결과는
`data/generated/AB테스트_가상데이터_분석요약.xlsx`의 "AB지표_검증결과" 시트를 참고하세요.

## data/generated_v2/ — Kaggle 실측 기반 재보정 버전 (신규)

위 `data/generated/`(v1)는 원본 팀 산출물 그대로 보존하고, 아래에서 소개하는 6개
Kaggle 공개 이커머스 데이터셋을 실측 근거로 삼아 핵심 편향(조회 시 100% 장바구니
담기 가정)을 제거하고 다시 생성한 버전을 `data/generated_v2/`에 추가했습니다.
- 조회->장바구니(3.60%), 장바구니->구매(32.83%) 확률을 REES46/Cosmetics Shop/
  RetailRocket 3개 데이터셋에서 직접 집계한 중앙값으로 대체
- A/B 처치 효과는 지표마다 다른 임의의 격차 대신, 업계 개인화 추천 효과 통계 중 가장
  보수적인 값(+15% 상대 개선) 하나로 통일
- 상품 마스터를 사내 반려동물 상품 분류 체계(카테고리/건강기능/원재료·알레르겐/영양성분)
  기반으로 확장(91개 상품 + 정규화된 원재료/영양성분 테이블)
- 계획서 정식판(V1)에서 개정된 가설2 순수 달성 지표(맞춤 추천 CVR, 추천 상품 화면
  진입률, 비교 기능 사용률 — 활성유저 기준)를 검증/리포트 스크립트에 반영
- (v0.4) 통계적 검정력 확보를 위해 표본을 A/B 각 2,500명 → 9,500명(총 19,000명,
  3.8배)으로 확대 — 자세한 배경은 `data/generated_v2/README.md`의 "v0.4 표본 확대"
  절 참고

**파이프라인을 다시 돌리거나 새 실험을 설계한다면 [`docs/데이터_파이프라인_운영_가이드.md`](docs/데이터_파이프라인_운영_가이드.md)를 먼저 읽으세요** — 재생성 시 주의사항, 이미 났던 버그, 표본 설계·판정 기준이 정리돼 있습니다.

자세한 방법론과 "Kaggle 실측 vs 가정(명시)" 구분표는
[`data/generated_v2/README.md`](data/generated_v2/README.md)를 참고하세요.
생성 스크립트는 `scripts_v2/`(01~05, v1과 동일한 순서로 실행).

## 참고: 실제 공개 이커머스 이벤트 로그 데이터셋

이 프로젝트의 이벤트 스키마(`view_item` → `add_to_cart` → `complete_purchase`)와
구조가 유사한 실제 공개 데이터셋:

- [eCommerce behavior data from multi category store (REES46)](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) — `event_type`이 view/cart/purchase로 거의 1:1 매핑. 원본은 커서(월별 5.67~9.01GB) 못 담고, 월별 5만행 무작위 샘플만 `data/reference/rees46_samples/`에 포함
- [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop) — 같은 스키마의 경량 버전(약 2.43GB, 5개월치). 원본은 커서 못 담고, 월별 5만행 무작위 샘플만 `data/reference/cosmetics_shop_samples/`에 포함
- [Retail Rocket E-commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) — 추천 클릭 로그 포함. REES46/Cosmetics와 스키마가 다름(방문 클릭스트림 + 상품 속성 변경 이력). 각 파일 5만행 무작위 샘플(+ 작은 category_tree는 전체)을 `data/reference/retailrocket_samples/`에 포함
- [E-commerce Clickstream and Transaction Dataset](https://www.kaggle.com/datasets/waqi786/e-commerce-clickstream-and-transaction-dataset) — 세션 내 page_view→click→product_view→add_to_cart→purchase 클릭스트림. 용량이 작아(3.93MB) 원본을 `data/reference/ecommerce_clickstream_transactions.csv`에 그대로 포함 (자세한 설명은 `data/reference/README.md` 참고)
- [E-Commerce Sales Analytics Dataset](https://www.kaggle.com/datasets/datascikhan/e-commerce-sales-and-customer-analytics) — 매출·마케팅 채널·물류·반품·리뷰·로열티까지 아우르는 통합 스키마(44개 컬럼). 작은 파일은 전체, 큰 파일 2개는 5만행 샘플로 `data/reference/ecommerce_sales_analytics_samples/`에 포함
- [Amazon_Sales_Dataset](https://www.kaggle.com/datasets/aliiihussain/amazon-sales-dataset) — 가격·할인율·배송지역·결제수단·평점 스키마. 용량이 작아(4.17MB) 원본을 `data/reference/amazon_sales_dataset/`에 그대로 포함 (다만 분포가 인위적으로 균등해 스키마 참고용에 가까움)

원본이 커서 담지 못한 데이터셋(REES46, Cosmetics Shop, Retail Rocket)은 각각 월별/파일별로
무작위 샘플링한 사본을 `data/reference/`에 포함해 두었습니다. 샘플링 방법과 통계는
`data/reference/README.md`를 참고하세요.

## Git LFS 대신 일반 파일로 관리하는 이유

`events_log.csv`(약 23MB)와 `orders.csv`(약 1MB)는 원래 git diff/clone 성능을 위해
Git LFS로 관리할 계획이었고 `.gitattributes`에도 그렇게 지정돼 있었습니다. 다만 이 저장소를
GitHub에 올리는 작업을 수행한 환경의 아웃바운드 네트워크 정책이 GitHub LFS 업로드에 필요한
확인(verify) 엔드포인트(`lfs.github.com`)를 차단하고 있어, 실제 데이터 저장소(S3)까지는
정상 전송되어도 GitHub이 해당 오브젝트를 최종적으로 인식하지 못하는 문제가 있었습니다.

두 파일 모두 GitHub의 하드 제한(100MB)에는 여유 있게 들어가므로, 이번 푸시에서는 LFS 없이
일반 git 파일로 커밋했습니다. `git diff`나 `git clone` 속도에 약간 영향이 있을 수 있지만
기능상 문제는 없습니다. 추후 LFS로 전환하고 싶다면 `.gitattributes`에 LFS 필터를 다시 추가하고
`git lfs migrate import`로 히스토리를 재작성하면 됩니다 (제약이 없는 환경에서 진행 필요).

## 라이선스

내부 프로젝트 자료입니다. 별도 명시 전까지 외부 배포 금지.
