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

## rees46_samples/ — eCommerce behavior data from multi category store (샘플)

- **출처**: [eCommerce behavior data from multi category store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) (Kaggle, Michael Kechinov / REES46 Marketing Platform)
- **원본 규모**: 2019-10 ~ 2020-04, 7개월치, 총 2억 8,500만 건 이벤트. 공개된 2개월치
  (2019-Oct 5.67GB, 2019-Nov 9.01GB)만으로도 저장소에 담기엔 너무 커서, **월별 5만 행
  무작위 샘플**만 포함합니다.
- **샘플링 방법**: Cosmetics Shop과 동일한 스트리밍 확률 샘플링(`random.seed(42)`) 후
  `event_time` 기준 정렬.
- **스키마**: Cosmetics Shop과 동일 (`event_time, event_type, product_id, category_id,
  category_code, brand, price, user_id, user_session`) — 다만 `event_type`에
  `remove_from_cart`가 없고 `view/cart/purchase` 3종만 있습니다.

| 파일 | 행 수 | 기간 | view | cart | purchase |
|---|---|---|---|---|---|
| 2019-Oct.csv | 50,000 | 10/01~10/31 | 95.9% | 2.3% | 1.8% |
| 2019-Nov.csv | 50,000 | 11/01~11/30 | 94.1% | 4.6% | 1.3% |

Cosmetics Shop(`remove_from_cart` 포함, purchase 약 6~8%)보다 구매 전환율이 낮고
장바구니 제거 단계가 아예 없어, 같은 스키마라도 카테고리(멀티카테고리 대형몰 vs
화장품 전문몰)에 따라 퍼널 형태가 꽤 다르다는 걸 보여줍니다.

## cosmetics_shop_samples/ — eCommerce Events History in Cosmetics Shop (샘플)

- **출처**: [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop) (Kaggle, Michael Kechinov / REES46 Marketing Platform)
- **원본 규모**: 2019-10 ~ 2020-02, 5개월치, 약 2.43GB, 20M 유저 이벤트. 저장소에 담기엔
  너무 커서 **월별 5만 행씩 무작위 샘플**만 포함합니다 (원본은 위 링크에서 받으세요).
- **샘플링 방법**: 파일을 한 줄씩 스트리밍하며 확률적으로 골라내는 방식(pandas
  `skiprows` 콜백 + `random.seed(42)`)으로 추출 후 `event_time` 기준 정렬. 앞부분만
  자르는 방식과 달리 각 월 전체 기간에 걸쳐 고르게 분포합니다. (최초에는 2,000행으로
  뽑았다가, 30MB 첨부 한도 대비 용량 여유가 많아 5만 행으로 다시 추출했습니다.)
- **스키마**: `event_time, event_type, product_id, category_id, category_code, brand, price, user_id, user_session`
  (REES46 "eCommerce behavior data from multi category store"와 동일한 스키마)
- **event_type**: `view`(조회) / `cart`(장바구니 담기) / `remove_from_cart`(장바구니 제거) / `purchase`(구매) 4종

| 파일 | 행 수 | 기간 |
|---|---|---|
| 2019-Oct.csv | 50,000 | 10/01~10/31 |
| 2019-Nov.csv | 50,000 | 11/01~11/30 |
| 2019-Dec.csv | 50,000 | 12/01~12/31 |
| 2020-Jan.csv | 50,000 | 01/01~01/31 |
| 2020-Feb.csv | 50,000 | 02/01~02/29 |

`view → cart → purchase` 순으로 자연스럽게 줄어드는 깔때기 형태를 보여, 골라주개냥
가상 데이터의 이벤트 스키마·퍼널 설계와 비교해 볼 만한 참고 자료입니다. `remove_from_cart`
비중(약 20%)이 꾸준히 높은 것도 특징입니다.

## retailrocket_samples/ — Retail Rocket E-commerce Dataset (샘플)

- **출처**: [Retail Rocket E-commerce Dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset) (Kaggle)
- **원본 규모**: 실제 이커머스 방문 로그(2015년 5개월치) + 상품 속성 변경 이력. 스키마가
  REES46/Cosmetics와 완전히 다릅니다.
- **파일 4개**:
  - `events.csv` (5만 행 무작위 샘플): 방문자 클릭스트림. `timestamp`(unix ms), `visitorid`,
    `event`(view/addtocart/transaction), `itemid`, `transactionid`. 기간 2015-05-03~2015-09-18,
    고유 방문자 45,506명·상품 31,312개. event 분포는 view 96.7% / addtocart 2.5% /
    transaction 0.8% — 실제 이커머스에서 흔히 보이는 강한 깔때기 형태(조회 대비 구매 전환이
    1% 미만)를 보여줍니다.
  - `item_properties_part1.csv`, `item_properties_part2.csv` (각 5만 행 무작위 샘플): 상품
    속성이 시간에 따라 바뀐 이력. `timestamp`, `itemid`, `property`, `value`. **유저 행동
    로그가 아니라 상품 속성 스냅샷**이라는 점에서 다른 파일들과 성격이 다릅니다. `property`는
    숫자로 해시된 값(예: `888`, `790`, `6`)과 `available`, `categoryid` 같은 이름 있는 값이
    섞여 있습니다 (원본 데이터셋이 일부 속성을 익명화한 결과). 원본은 시간 순 정렬 후 두
    파일로 분할돼 있어, 샘플도 동일 기간(2015-05-10~2015-09-13)에서 각각 무작위 추출했습니다.
  - `category_tree.csv` (전체, 1,669행): `categoryid`, `parentid` 두 컬럼뿐인 카테고리
    트리입니다. 원본 자체가 작아 샘플링 없이 전체를 그대로 포함했습니다. 최상위(부모 없음)
    카테고리 25개.
- **골라주개냥과의 연결점**: `item_properties`처럼 "상품 속성이 시간에 따라 바뀌는" 구조는
  없지만, `events.csv`의 강한 깔때기 형태(view→addtocart→transaction)는 서비스 초기
  전환율 벤치마크를 잡을 때 참고할 만합니다.

## ecommerce_sales_analytics_samples/ — E-Commerce Sales Analytics Dataset (샘플)

- **출처**: [E-Commerce Sales Analytics Dataset](https://www.kaggle.com/datasets/datascikhan/e-commerce-sales-and-customer-analytics) (Kaggle, Shair Khan, CC0 라이선스)
- **원본 규모**: 2021~2025년 시뮬레이션 거래 15만 건, 고객 25,000명, 상품 1,175개. 5개
  파일 총 88.59MB. `customer_master.csv`·`product_catalog.csv`·`dataset_statistics.csv`는
  작아서 원본 그대로, 큰 파일 2개(`order_items.csv`, `ecommerce_sales_customer_analytics.csv`)는
  각 5만 행 무작위 샘플입니다.
- **골라주개냥과의 연결점**: 이커머스 D2C 서비스가 추적할 법한 지표(마케팅 채널,
  로열티 포인트, 고객생애가치(CLV), 재구매 여부, 배송 상태, 반품 사유, 리뷰 감성)를
  거의 다 포함하고 있어, 매출·마케팅·물류·고객 관점의 스키마 참고 자료로 유용합니다.

| 파일 | 행 수 | 비고 |
|---|---|---|
| `customer_master.csv` | 25,000 (전체) | 고객 기본정보 |
| `product_catalog.csv` | 1,175 (전체) | 상품 카탈로그 |
| `order_items.csv` | 50,000 (샘플) | 주문 상품 라인 아이템 |
| `ecommerce_sales_customer_analytics.csv` | 50,000 (샘플) | 44개 컬럼, 주문+고객+마케팅+물류+리뷰+로열티 통합 |
| `dataset_statistics_original.csv` | 1 | 원본 전체(15만 건) 기준 요약 통계 (아래 표) |

원본 전체(15만 건) 기준 통계 (`dataset_statistics_original.csv`에서):

| 지표 | 값 |
|---|---|
| 총 거래 | 138,116건 |
| 총 고객 | 24,911명 |
| 총 매출 | $177,134,263.74 |
| 총 이익 | $76,146,395.76 |
| 평균 주문금액 | $1,282.50 |
| 평균 평점 | 3.68 |
| 반품률 | 6.85% |
| 취소율 | 6.08% |

5만 행 샘플(`ecommerce_sales_customer_analytics.csv`) 기준 분포:

| 컬럼 | 분포 |
|---|---|
| `order_status` | Completed 81.9% · Returned 6.9% · Cancelled 6.2% · Pending 4.9% |
| `sales_channel` | Mobile App 40.2% · Website 34.5% · Marketplace 15.1% · Social Media 10.2% |
| `marketing_channel` | Organic Search 20.3% · Direct 14.8% · Google Ads 14.7% · Facebook Ads 12.3% · Instagram 10.0% |
| `delivery_status` | On Time 62.8% · Cancelled 18.1% · Delayed 12.1% · Early 7.1% |
| `review_sentiment` | Positive 56.3% · Neutral 25.0% · 결측 18.1% · Negative 0.6% |
| `customer_segment` | Consumer 55.1% · Premium 25.0% · VIP 10.0% · Business 9.9% |

### 데이터 특이사항

- `is_repeat_customer`가 샘플의 **99.8%가 True**입니다. 재구매 고객 비율치고는
  비정상적으로 높아, 이 컬럼이 "이번이 최초 주문인지"가 아니라 다른 정의(예: 활성
  고객 여부)로 채워졌을 가능성이 있습니다. 재구매율 관련 분석에 그대로 쓰기보다는
  `customer_order_count`(주문 횟수) 컬럼으로 직접 재구매 여부를 재정의하는 편이
  안전합니다.
- `review_sentiment`는 부정 리뷰가 0.6%로 극히 적습니다. 평균 평점 3.68점과 비교하면
  감성 라벨이 실제 평점 분포보다 낙관적으로 시뮬레이션된 것으로 보입니다.

## amazon_sales_dataset/ — Amazon_Sales_Dataset

- **출처**: [Amazon_Sales_Dataset](https://www.kaggle.com/datasets/aliiihussain/amazon-sales-dataset) (Kaggle, Ali Hussain, CC0 라이선스)
- **원본 규모**: 50,000행, 13컬럼, 4.17MB — 용량이 작아 샘플링 없이 원본 그대로 포함
- **스키마**: `order_id, order_date, product_id, product_category, price, discount_percent,
  quantity_sold, customer_region, payment_method, rating, review_count, discounted_price,
  total_revenue`
- **기간**: 2022-01-01 ~ 2023-12-31

| 항목 | 값 |
|---|---|
| product_category | Beauty/Fashion/Books/Electronics/Sports/Home & Kitchen 6종, 각 16~17%로 균등 |
| customer_region | Asia/North America/Middle East/Europe 4개 지역, 각 25%로 균등 |
| payment_method | Wallet/UPI/Debit Card/Cash on Delivery/Credit Card 5종, 각 20%로 균등 |
| discount_percent | 0/5/10/15/20/30% 6개 값만 존재 (연속값 아님) |
| price | $5.01~$499.99, 평균 $252.51 |
| rating | 1~5점, 평균 정확히 3.00 |

### 데이터 특이사항

다른 참고 데이터셋들과 달리, 카테고리·지역·결제수단 비율이 전부 인위적으로
균등합니다(예: 4개 지역이 정확히 25%씩). `rating` 평균도 정확히 3.00으로 떨어지고,
`discount_percent`는 6개 값만 이산적으로 존재합니다. 실제 서비스 데이터라기보다는
**완전 무작위 생성 데이터**로 보이며, 특정 세그먼트나 카테고리의 편향된 행동 패턴을
찾는 분석(EDA 연습 이상의 인사이트)에는 적합하지 않을 수 있습니다. 컬럼 스키마
자체(가격·할인율·배송지역·결제수단·평점 조합)를 참고하는 용도로 활용하세요.
