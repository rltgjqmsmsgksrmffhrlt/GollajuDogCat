# CLAUDE.md

Claude Code가 이 저장소에서 작업할 때 참고하는 컨텍스트입니다.

## 이 저장소는 무엇인가

골라주개냥(우지빌) — KT TechUP 반려동물 D2C 이커머스 프로젝트의 KPI 검증용
**데이터 수집 계획서**와, 그 계획서를 근거로 만든 **90일치 가상 A/B 테스트 운영 데이터**,
그리고 그 데이터로 수행한 **퍼널·코호트 분석**을 담고 있습니다.

실제 서비스 코드는 없습니다. 이 저장소의 산출물은 (1) 데이터 스키마 설계 문서,
(2) 그 스키마를 채우는 시뮬레이션 스크립트, (3) 시뮬레이션 결과 데이터와 분석 리포트입니다.

## 검증 대상 3개 가설 (원본 출처: 골라주개냥 검증 가설 문서)

| # | 가설명 | 핵심 지표 (A vs B 목표치) |
|---|---|---|
| 1 | 선택 피로도 해소 | 장바구니 이탈률(A 40% / B 52.8~56.1%), 추천상품 CVR(A 3.3% / B 3.21%), 상품상세 체류시간(A 60초 / B 43초), 구매결정 소요시간(A 2일 / B 2.4~3.3일) |
| 2 | 서비스 충성도 | NPS(A 55점 이상 / B 20~30점), 맞춤추천 CVR(목표 5%), 상품반응 입력률(목표 10%), N일 재구매율(30일 8~10% / 60일 12~15%), 비교기능 사용률(PDP경유 15~25%, 전체 10~20%), 비교후 전환율(4~6%) |
| 3 | 유저 데이터 확보 | 반응입력 시작률(A 20~30% / B ≤20%), 완료율(A ≥85% / B ≤80%), 퍼널 이탈률(A ≤15% / B ~20%), 재진입률(A ≥5%, A>B), 유효 반응 데이터 확보율(목표 15%) |

실험군(A) = 추천 근거·점수·비교 기능 노출 / 통제군(B) = 미노출.

## data/planning/ — 데이터 수집 계획표를 먼저 읽을 것

`데이터_수집_계획표.xlsx`는 이 저장소의 **스키마 원본(source of truth)**입니다.
새 필드를 추가하거나 시뮬레이션 로직을 바꾸기 전에 반드시 이 파일부터 확인하세요.

- **시트1 "공통 속성표"**: raw 필드 1개당 행 1개로 정의. `event_type`처럼 여러 지표가
  공유하는 필드는 한 번만 정의하고, "고려사항" 컬럼에 어떤 지표들이 이 필드를
  재사용하는지 메모되어 있습니다.
- **시트2 "퍼널 이벤트표"**: `event_type` / `funnel_step` 스키마. 가설별로 별도의
  `funnel_step` 매핑을 가집니다 (상품구매 여정 / 추천재구매 여정 / 반응기록-재진입 여정).

### 이 스키마가 이런 형태가 된 이유 (설계 히스토리)

작업 중 아래 순서로 설계가 바뀌었습니다. 비슷한 요청을 받으면 같은 원칙을 적용하세요.

1. **초기 시도**: 지표 1개당 행 1개(측정항목-태그명-계산식 1:1 매핑) 요약표를 만들었으나,
   한 지표 계산에 필요한 이벤트가 여러 개인데 "태그명" 칸에 슬래시로 나열하는 방식이라
   중복·혼란이 발생함.
2. **중복 제거 원칙 확정**: raw 이벤트(예: `complete_purchase`)와 그 이벤트를 특정 조건으로
   필터링해 계산하는 파생 지표(예: "N일 내 재구매율")를 명확히 구분. **파생 지표는 별도
   행을 만들지 않고, raw 이벤트 필드의 "고려사항"란에 계산 로직을 메모**하는 것으로 정리.
   - 예: `complete_purchase (source:recommendation)`는 raw 필드로 유지. "N일 내 재구매율"이나
     "비교 후 전환율"처럼 여기서 파생되는 지표는 별도 행으로 만들지 않음.
   - 예: `reaction_complete`도 동일 — "퍼널 이탈률" 계산은 이 필드 하나로 충분하므로
     별도 파생 행을 만들지 않음.
3. **Spotify DJX 케이스와 동일한 최종 구조로 수렴**: "공통 속성표"(raw 필드 정의) +
   "퍼널 이벤트표"(event_type/funnel_step 스키마) 2-테이블 구조. 이 구조가 최종본입니다.
4. **원래 요청했던 15컬럼 골격 복원**: 공통 속성표/퍼널 이벤트표 각 행은 다음 컬럼을
   전부 가져야 합니다 — 절대 누락하지 말 것:

   ```
   가설 매핑 | n | 측정 항목 | 태그명 | 데이터 종류 | 운영 정의(경우와 목적) | 측정 방법
   | [DATA 수집 세부사항: 샘플 사이즈 | 샘플 속성 | 기록 방법 | 담당자 | 수집방식 | 수집주기 | 수집 기간]
   | 데이터 수집시 고려사항
   ```

**데이터 종류 분류 기준**: 이벤트 로그(단일 액션 발생) / 세션 로그(세션 시작~종료 단위,
체류시간 등 시간 구간 속성) / 설문 데이터(NPS처럼 사용자 직접 응답) 3종으로 구분합니다.
여러 단계 이동을 함께 보는 지표(예: N일 재구매율, 반응입력 퍼널 이탈률)는
"이벤트 로그(퍼널 지표)"로 별도 표시하고, 전체 단계 흐름은 퍼널 이벤트표에서 관리합니다.

## data/generated/ — 이벤트 스키마 (raw 필드 요약)

`events_log.csv`의 핵심 컬럼:

| 컬럼 | 설명 |
|---|---|
| `event_timestamp` | ISO8601 타임스탬프 |
| `user_id`, `group`(A/B), `session_id` | 공통 식별자 |
| `event_type` | session_start, view_item, match_score_shown, view_item_end, add_to_cart, view_comparison, complete_purchase, recommendation_impression, select_item, delivery_status_complete, purchase_confirm, reaction_require_alarm, reaction_check, reaction_start, reaction_complete, pet_reaction_created, review_created, nps_popup_impression, nps_score, recommendation_view, session_end 등 |
| `product_id`, `category_id`, `order_id`, `pet_id`, `recommendation_id` | 엔티티 식별자 |
| `entry_source` | recommendation / search / gnb / pdp 등 화면 유입 경로 |
| `source` | complete_purchase 이벤트의 유입 경로(recommendation/comparison/direct) — CVR 분석 시 반드시 필터링에 사용 |
| `is_valid` | pet_reaction_created 이벤트에서 필수 항목 검증 통과 여부 |

`orders.csv`, `users_master.csv`, `products_master.csv`, `pet_reactions.csv`는
`events_log.csv`에서 파생/정리된 보조 테이블입니다. 원천 데이터는 `events_log.csv`이며
분석 시 이 파일을 기준으로 삼으세요.

## scripts/ 파이프라인 — 실행 순서 고정

```
01_build_masters.py        → users_master.csv, products_master.csv 생성
02_simulate_events.py      → events_log.csv, orders.csv, pet_reactions.csv 생성 (핵심 로직)
03_validate_metrics.py     → 생성 데이터의 AB 지표를 원본 목표치와 비교 (콘솔 출력만, 파일 생성 안 함)
04_funnel_cohort_analysis.py → 퍼널/코호트 CSV 생성
05_build_report.py         → AB테스트_가상데이터_분석요약.xlsx 생성
```

- 모든 스크립트는 `scripts/` 디렉토리에서 실행한다고 가정한 상대경로(`../data/generated/...`)를 씁니다.
- 난수 시드가 고정되어 있어 **재실행 시 항상 동일한 데이터**가 나옵니다 (`RNG = np.random.default_rng(2026)` 등, 파일마다 시드 값이 다를 수 있으니 각 스크립트 상단 확인).
- `02_simulate_events.py`가 가장 복잡한 파일입니다. `PARAMS` 딕셔너리(A/B 그룹별 목표 확률)를
  바꾸면 생성되는 데이터의 지표 분포가 바뀝니다.

### PARAMS 튜닝 시 주의할 점 (실제로 겪었던 문제)

`장바구니 이탈률`과 `추천상품 CVR`을 동시에 정확히 맞추려다 수학적으로 불가능한
상황에 부딪힌 적이 있습니다 (같은 세션 모집단 안에서 추천 경로 세션 비중이 45%이고
그 CVR이 3.3%로 고정되면, 나머지 55% 세션의 구매율을 100%로 잡아도 전체 이탈률이
40%까지 내려가지 않음). 이런 경우:

1. 어느 지표가 "더 세부적이고 정확해야 하는가"를 판단 (보통 원인이 되는 세부 지표 우선)
2. 나머지 지표는 근사치로 처리하고 그 사실을 리포트에 명시
3. 억지로 파라미터를 조작해 두 값을 동시에 맞추려 하지 말 것 — 원본 문서 자체의
   벤치마크 출처가 다를 수 있음을 인지

`03_validate_metrics.py`를 돌려서 실제 생성된 데이터의 지표가 목표 범위에 드는지
항상 확인한 뒐 다음 단계로 넘어가세요.

## 이 저장소에서 흔히 요청받을 작업 유형

1. **새 지표/필드 추가**: `data/planning/데이터_수집_계획표.xlsx` 공통 속성표에 먼저 필드를
   추가하고, `02_simulate_events.py`에 해당 이벤트 생성 로직을 추가한 뒤,
   `03_validate_metrics.py`에 검증 코드를 추가하는 순서를 따르세요.
2. **가상 데이터 재생성/파라미터 변경**: `02_simulate_events.py`의 `PARAMS` 딕셔너리를
   수정하고 파이프라인을 처음부터(01→05) 재실행하세요.
3. **퍼널/코호트 분석 확장**: `04_funnel_cohort_analysis.py`에 새 퍼널 정의를 추가할 때는
   `data/planning/데이터_수집_계획표.xlsx` 시트2의 `funnel_step` 매핑 로직을 먼저 참고하세요.
4. **실제 공개 데이터셋과의 비교/치환**: README.md의 "참고: 실제 공개 이커머스 이벤트 로그
   데이터셋" 섹션에 후보가 정리되어 있습니다. REES46 계열이 스키마 호환성이 가장 좋습니다.

## 코딩 컨벤션

- 데이터 처리는 pandas, 엑셀 리포트는 openpyxl을 사용합니다 (requirements.txt 참고).
- 한글 컬럼명/문서는 그대로 유지합니다(팀 컨벤션). 코드 내 변수명은 영문 스네이크케이스.
- 엑셀 출력 시 헤더 스타일(진한 남색 배경 `#1F4E78`, 흰 글씨, Arial 폰트)을 일관되게 유지합니다 — `05_build_report.py`의 스타일 함수를 재사용하세요.
- pip 설치 시 `--break-system-packages` 플래그가 필요한 환경일 수 있습니다.
