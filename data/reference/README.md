# data/reference/ — 실제 공개 데이터셋 참고 자료

`data/generated/`가 이 프로젝트(골라주개냥/우지빌)의 가상 시뮬레이션 데이터라면,
이 폴더는 이벤트 스키마 설계를 검증하거나 향후 실제 데이터로 치환할 때 참고할
**실제 공개 이커머스 데이터셋**을 모아둡니다.

용량이 큰 데이터셋(REES46, Cosmetics Shop, Retail Rocket)은 저장소에 직접 포함하지 않고
루트 `README.md`의 "참고: 실제 공개 이커머스 이벤트 로그 데이터셋" 절에 Kaggle 링크로만
안내합니다. 이 폴더에는 그중 **용량이 작아 원본 그대로 포함 가능한 데이터셋**만 둡니다.

## ecommerce_clickstream_transactions.csv

- **출처**: [E-commerce Clickstream and Transaction Dataset](https://www.kaggle.com/datasets/waqi786/e-commerce-clickstream-and-transaction-dataset) (Kaggle, WAQAR ALI, Apache 2.0 라이선스)
- **설명**: 이커머스 플랫폼에서의 사용자 상호작용을 시뮬레이션한 데이터. 세션 단위로
  페이지 조회·클릭·상품 조회·장바구니 담기·구매로 이어지는 이벤트 시퀀스를 담고 있어,
  클릭스트림 경로와 구매 전환 패턴 분석에 적합합니다.
- **크기**: 3.93MB, 74,817행, 7컬럼

| 컬럼 | 설명 |
|---|---|
| `UserID` | 유저 식별자 (1~1000, 총 1,000명) |
| `SessionID` | 세션 식별자 |
| `Timestamp` | 이벤트 발생 시각 (2024-01-01 ~ 2024-07-24) |
| `EventType` | `page_view`/`click`/`login`/`logout`/`product_view`/`add_to_cart`/`purchase` 7종, 각 14% 내외로 고르게 분포 |
| `ProductID` | 상품 식별자 (product_view/add_to_cart/purchase에서만 값 존재, 57.1% 결측) |
| `Amount` | 구매 금액 (purchase 건에서만 존재, 5.13~499.98, 평균 253.19, 85.7% 결측) |
| `Outcome` | 목표 이벤트 여부 — `purchase`(14.3%) 또는 결측(85.7%) |

### 데이터 특이사항

- `SessionID`는 유저 1,000명 전체에 걸쳐 **단 10개 값만 존재**합니다. 일반적으로
  세션 ID는 유저·방문마다 고유해야 하는데, 이 데이터셋은 세션을 10개 그룹으로만
  나눈 것으로 보입니다. 실제 세션 단위 분석(체류시간, 세션당 이벤트 수 등)에
  그대로 쓰기보다는 `UserID`와 `Timestamp` 간격으로 세션을 재정의하는 편이
  안전합니다. 골라주개냥 데이터 스키마의 `session_id`(사용자·방문마다 고유)와는
  성격이 다르다는 점에 유의하세요.
- `EventType` 각 값이 거의 균등(14% 내외)하게 분포돼 있어, 실제 서비스에서 흔히 보이는
  깔때기형 감소(조회 > 장바구니 > 구매) 패턴과는 다릅니다. 순수 참고용 스키마 예시로
  활용하고, 비율 자체를 벤치마크로 쓰지는 않는 것을 권장합니다.

## cosmetics_shop_samples/ — eCommerce Events History in Cosmetics Shop (샘플)

- **출처**: [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop) (Kaggle, Michael Kechinov / REES46 Marketing Platform)
- **원본 규모**: 2019-10 ~ 2020-02, 5개월치, 약 2.43GB, 20M 유저 이벤트. 저장소에 담기엔
  너무 커서 **월별 2,000행씩 무작위 샘플**만 포함합니다 (원본은 위 링크에서 받으세요).
- **샘플링 방법**: 파일을 한 줄씩 스트리밍하며 확률적으로 골라내는 방식(pandas
  `skiprows` 콜백 + `random.seed(42)`)으로 추출 후 `event_time` 기준 정렬. 앞부분만
  자르는 방식과 달리 각 월 전체 기간에 걸쳐 고르게 분포합니다.
- **스키마**: `event_time, event_type, product_id, category_id, category_code, brand, price, user_id, user_session`
  (REES46 "eCommerce behavior data from multi category store"와 동일한 스키마)
- **event_type**: `view`(조회) / `cart`(장바구니 담기) / `remove_from_cart`(장바구니 제거) / `purchase`(구매) 4종

| 파일 | 행 수 | 기간 | view | cart | remove_from_cart | purchase | 평균가 | brand 결측 |
|---|---|---|---|---|---|---|---|---|
| 2019-Oct.csv | 2,000 | 10/01~10/31 | 43% | 32% | 20% | 6% | $8.51 | 38% |
| 2019-Nov.csv | 2,000 | 11/01~11/30 | 45% | 27% | 20% | 8% | $7.75 | 43% |
| 2019-Dec.csv | 2,000 | 12/01~12/31 | 49% | 26% | 19% | 6% | $9.09 | 42% |
| 2020-Jan.csv | 2,000 | 01/01~01/31 | 47% | 27% | 20% | 5% | $8.04 | 42% |
| 2020-Feb.csv | 2,000 | 02/01~02/29 | 45% | 30% | 20% | 6% | $7.95 | 44% |

`view → cart → purchase` 순으로 자연스럽게 줄어드는 깔때기 형태를 보여, 골라주개냥
가상 데이터의 이벤트 스키마·퍼널 설계와 비교해 볼 만한 참고 자료입니다. `remove_from_cart`
비중(약 20%)이 꾸준히 높은 것도 특징입니다.
