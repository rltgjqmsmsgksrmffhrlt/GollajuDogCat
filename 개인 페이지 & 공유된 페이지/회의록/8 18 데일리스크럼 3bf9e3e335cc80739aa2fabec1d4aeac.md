# 8/18 데일리스크럼

해당 스프린트: Sprint 1
유형: 데일리 스크럼
과정: 백엔드
날짜: 2026년 8월 18일

## 1. 오늘의 목표 및 계획

---

- 멀티모듈 MSA 환경 세팅
- 확정된 경쟁사 기반으로 Phase 1 수정 필요, MSA 등의 변경된 부분도 반영되어야 한다.
1. 댕냥잇
2. 쿠팡
3. 핏펫
4. 어바웃펫
5. Chewy
6. 아마존

### 문시원

- [ ]  멀티 모듈 개발 환경 세팅
- [x]  WBS 옮겨 적기

### 노여진

- [ ]  경쟁사 기반 Phase 1 수정
- [ ]  -

## 2. 문제 상황 공유

---

- WBS 링크: https://rad-babka-6c8427.netlify.app/ (회원가입-로그인-E754ABD4)
- [‣](https://app.notion.com/p/3bf9506663d98066b6facdef6433c1a5?pvs=21) 개념 정리

### 팀장 데일리 스크럼

**진행 전 전달받은 내용**

- AI팀에서 기능에 대한 혼란이 있었던 것 같음. 개인화 상품 추천 vs 수요 예측형 AI

**전달 내용**

- 백엔드 입장: 개발 기간은 줄어드는데 기능은 많아지는 거라서 추가 안하는 쪽이 편하긴 하다.
- 기획 어떻게 진행되고 있는 건지 알 수 있는 방법이 있을지 (구현 가능성 검토 필요할지도 몰라서)
- 인프라팀이랑 미팅 시간을 잡아야 할 것 같다.

**진행 내용**

- 오후 3시까지 필요한 기능 전달 바람 (3시부터 전체 미팅 진행)
- 기획 관련도 3시에 공유 예정, 그때 구현 가능성 등 전체적인 공유 진행
- AI팀에서 구현 전에 설계를 같이 해서 관련 싱크를 맞춰야 될 것 같다.

- 프로젝트 세팅 관련 메모
    
    ```sql
    springCloud = "2025.1.0"    
    # 확인 필요: Spring Boot 4.1.0과 호환되는 Spring Cloud 릴리스 트레인인지
    ```
    
    - 버전 카탈로그 검토 필요
    - init 필요한 경우 사용
    - 인프라 docker-compose 초안
        
        ```sql
        # 로컬 개발 전용 인프라
        
        services:
          postgres:
            image: postgres:16
            profiles: ["infra", "all"]
            environment:
              POSTGRES_USER: postgres
              POSTGRES_PASSWORD: postgres
            ports:
              - "5432:5432"
            volumes:
              - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
              - postgres-data:/var/lib/postgresql/data
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U postgres"]
              interval: 5s
              timeout: 5s
              retries: 10
        
          mongodb:
            image: mongo:7
            profiles: ["infra", "all"]
            ports:
              - "27017:27017"
            volumes:
              - ./mongodb/init:/docker-entrypoint-initdb.d
              - mongo-data:/data/db
        
          redis:
            image: redis:7-alpine
            profiles: ["infra", "all"]
            ports:
              - "6379:6379"
        
          kafka:
            image: apache/kafka:3.9.0
            profiles: ["infra", "all"]
            ports:
              - "9092:9092"
            environment:
              KAFKA_NODE_ID: 1
              KAFKA_PROCESS_ROLES: broker,controller
              KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
              KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
              KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
              KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
              KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
              KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
        
          # --- 아래는 profile: monitoring 에서만 선택적으로 기동 ---
          prometheus:
            image: prom/prometheus:v3.0.1
            profiles: ["monitoring"]
            ports:
              - "9090:9090"
            volumes:
              - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
        
          otel-collector:
            image: otel/opentelemetry-collector-contrib:0.116.1
            profiles: ["monitoring"]
            command: ["--config=/etc/otel-collector-config.yml"]
            ports:
              - "4317:4317"   # OTLP gRPC
              - "4318:4318"   # OTLP HTTP
            volumes:
              - ./monitoring/otel-collector-config.yml:/etc/otel-collector-config.yml
        
        volumes:
          postgres-data:
          mongo-data:
        
        ```
        
    - 도커컴포즈 루트 . 게이트웨이 주의사항
        
        ```sql
              # 컨테이너로 전체 실행할 때는 application-local.yml의 기본값(localhost)을
              # 서비스명(Docker 내부 DNS)으로 오버라이드해야 gateway가 다른 서비스에 도달할 수 있다.
        ```
        
    - 확인할 내용
        - init 방식을 sh로 하는 방법과 제안 방법
    - -
    - ./gradlew wrapper --gradle-version 9.1.0
    - Claude.md 초안 (루트)
        
        ```sql
        # golajugaenyang-server — 루트 컨텍스트
        
        이 문서는 Claude Code가 이 모노레포에서 작업할 때 항상 참고해야 하는 전역 규칙입니다.
        서비스별 세부 규칙은 각 `services/*/CLAUDE.md`를 함께 참고하세요.
        
        ## 아키텍처 개요
        - Java 25 / Spring Boot 4.1.0 / Gradle(Groovy DSL) / YAML
        - 모노레포 + MSA 멀티모듈, 서비스 간 직접 호출 금지 (Kafka 이벤트 또는 Gateway 경유만 허용)
        - DDD 기반, 서비스별로 헥사고날 또는 4-Layer 혼용 가능 (담당자 재량, domain 레이어는 프레임워크 비의존 원칙만 공통)
        
        ## 모듈 경계 규칙 (반드시 지킬 것)
        - `modules/common-core`: 공통 응답 포맷, 예외 처리, 유틸, CORS/인터셉터. 도메인 로직 절대 금지.
        - `modules/common-event`: Kafka 이벤트 payload/enum만. 서비스 내부 도메인 절대 금지 (ADR-0001, ArchUnit으로 강제).
        - `modules/common-security`: 인증/인가 공통 로직. 필요한 서비스만 선택적으로 의존.
        - `modules/common-test`: Testcontainers 등. testImplementation으로만 의존.
        - `platform/*`: 도메인 로직 없는 실행 서비스 (api-gateway 등). `-service` 접미사 사용하지 않음.
        - `services/*`: 도메인 바운디드 컨텍스트. `-service` 접미사 사용.
        
        ## 작업 시 주의사항
        - 공통 모듈(`modules/`) 변경은 여러 서비스에 영향을 주므로, 별도 턴/PR로 분리해서 작업할 것.
        - 특정 서비스 작업을 요청받으면 해당 서비스 디렉토리 밖의 코드는 수정하지 말 것.
        - 서비스 간 통신이 필요하면 직접 호출 코드를 작성하지 말고, Kafka 이벤트 발행/구독 또는
          Gateway 라우팅으로 구현할 것. 확실하지 않으면 먼저 사용자에게 확인할 것.
        - 새 서비스/모듈을 추가할 때는 `docs/architecture.md`의 "패키지 분류 3원칙"을 따를 것.
        
        ## 실행/검증
        - 인프라만 기동: `docker compose -f local-infra/docker-compose.yml up -d`
        - 특정 서비스 실행: `./gradlew :services:{service-name}:bootRun --args='--spring.profiles.active=local'`
        - 공통 모듈 변경 후에는 `./gradlew build`로 전체 영향도를 확인할 것.
        
        ```
        
    - Claude.md 초안 (하위)
        
        ```sql
        # order-service — 서비스 컨텍스트
        
        루트 CLAUDE.md의 전역 규칙을 우선 따르고, 이 파일은 order-service 고유 규칙만 다룹니다.
        
        ## 도메인 상태
        - 기획 확정 전 단계. 현재 코드는 실행 가능 여부 확인을 위한 스캐폴딩이며 비즈니스 로직 없음.
        - domain/Order, application/OrderQueryUseCase 등은 전부 placeholder입니다.
          실제 도메인 설계 전에는 이 클래스들의 "형태"를 그대로 확장하지 말고, 먼저 도메인 설계를 논의할 것.
        
        ## 구조
        - domain/: 프레임워크 비의존 순수 모델
        - application/: 유스케이스 + port(in/out) 인터페이스
        - adapter/in/web, in/messaging, out/persistence, out/messaging
        - config/: 서비스 전용 Bean 설정
        
        ## 이벤트
        - 발행하는 이벤트는 modules/common-event/.../event/order 패키지의 DTO만 사용할 것.
        - 새 이벤트가 필요하면 이 서비스 코드가 아니라 common-event 모듈에 먼저 정의를 추가하고,
          버전(V1, V2...)을 명시할 것.
        ```
        
    - build.gradle 초안
        
        ```sql
        // TODO: 각 플러그인 버전은 반드시 로컬에서 재검증 후 push 하세요.
        //   - Spring Boot 4.1.0 / Java 25 조합은 이 문서 작성 시점 기준 최신 요구사항을 그대로 반영한 것으로,
        //     Maven Central에 실제 배포된 버전인지, io.spring.dependency-management 최신 버전과 호환되는지
        //     이 환경(네트워크 제한)에서는 확인하지 못했습니다.
        plugins {
            id 'java'
            id 'org.springframework.boot' version '4.1.0' apply false
            id 'io.spring.dependency-management' version '1.1.7' apply false
        }
        
        ext {
            // 모든 서브모듈이 참조하는 단일 버전 소스. 값 자체는 로컬에서 반드시 재검증하세요.
            springBootVersion = '4.1.0'
            springCloudVersion = '2025.1.0'   // 확인 필요: spring.io/projects/spring-cloud#overview
        }
        
        allprojects {
            group = 'com.golajugaenyang'
            version = '0.0.1-SNAPSHOT'
        
            repositories {
                mavenCentral()
            }
        }
        
        subprojects {
            apply plugin: 'io.spring.dependency-management'
        
            // [버그 수정] modules/ 하위는 "다른 모듈이 재사용하는 라이브러리"이므로 java-library를 적용해
            // api/implementation 구분(전이 의존성 노출 여부)을 쓸 수 있게 한다.
            // services/, platform/ 하위는 실행되는 리프 앱이므로 plain java로 충분하다
            // (org.springframework.boot 플러그인이 필요 시 자체적으로 java 플러그인을 적용한다).
            if (project.path.startsWith(':modules:')) {
                apply plugin: 'java-library'
            } else {
                apply plugin: 'java'
            }
        
            java {
                toolchain {
                    languageVersion = JavaLanguageVersion.of(25)
                }
            }
        
            // [버그 수정] common-core/common-event/common-security/common-test 처럼
            // org.springframework.boot 플러그인을 적용하지 않는 "라이브러리" 모듈은
            // Boot BOM이 자동으로 import되지 않아 spring-boot-starter-* 버전을 찾지 못했다.
            // io.spring.dependency-management 플러그인만으로도 BOM을 명시적으로 가져올 수 있으므로,
            // bootJar를 만들지 않으면서도 버전 관리 혜택은 모든 서브모듈이 받도록 여기서 일괄 처리한다.
            // (org.springframework.boot 플러그인을 이미 적용한 모듈에도 중복 import되지만 무해하다)
            dependencyManagement {
                imports {
                    mavenBom "org.springframework.boot:spring-boot-dependencies:${springBootVersion}"
                }
            }
        
            tasks.withType(Test).configureEach {
                useJUnitPlatform()
            }
        
            // 공통 테스트 의존성 (JUnit5) - Boot Starter Test를 쓰지 않는 순수 모듈(common-event 등)을 위함
            dependencies {
                testImplementation platform('org.junit:junit-bom:5.11.4')
                testImplementation 'org.junit.jupiter:junit-jupiter'
            }
        }
        
        ```
        
    - 서비스-포트 매핑 메모
    - `- ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql`
    - `- ./mongodb/init:/docker-entrypoint-initdb.d`
    - 프로메테우스
        
        ```sql
        # 주의: host.docker.internal은 Docker Desktop(Mac/Windows) 전용이며 네이티브 Linux Docker Engine에서는
        # 기본 동작하지 않습니다(별도 extra_hosts 설정 필요). 이 monitoring profile은 보통 서비스 전체를
        # 컨테이너로 띄운 통합 테스트 상황(docker compose --profile all --profile monitoring)에서 켜는
        # 것을 전제로, 이식성이 더 좋은 컨테이너 서비스명(Docker 내부 DNS)을 사용합니다.
        # 만약 호스트에서 bootRun으로 띄운 서비스를 스크레이프하고 싶다면, 이 파일의 타겟을
        # host.docker.internal:포트 로 바꾸고, docker-compose.yml의 prometheus 서비스에
        # extra_hosts: ["host.docker.internal:host-gateway"] 를 추가하세요 (Linux 호환을 위해 필요).
        ```
        
    - 핸들러 초안
        
        ```sql
        @RestControllerAdvice
        public class GlobalExceptionHandler {
        
            @ExceptionHandler(Exception.class)
            public ResponseEntity<ApiResponse<Void>> handleException(Exception e) {
                return ResponseEntity
                        .status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body(ApiResponse.failure(e.getMessage()));
            }
        }
        
        ```
        
    - 게이트웨이 라우팅 yml관련
        
        ```sql
        # 로컬 개발용 - local-infra/docker-compose.yml 로 기동한 인프라를 바라봅니다.
        #
        # 라우팅 대상 "호스트"는 실행 방식에 따라 다르지만, 포트는 항상 동일합니다.
        #   - 각 서비스를 호스트에서 ./gradlew bootRun 으로 띄운 경우 (기본 로컬 개발 흐름) -> localhost
        #   - api-gateway까지 포함해 docker compose --profile all 로 전체 컨테이너 실행한 경우
        #     -> 컨테이너 내부의 localhost는 gateway 자신을 가리키므로 서비스명(Docker 내부 DNS)을 써야 함
        # (docker-compose에서도 SPRING_PROFILES_ACTIVE=local을 그대로 쓰므로, 컨테이너 안에서도
        #  application-local.yml의 포트 override(8081 등)가 그대로 적용됩니다. 즉 호스트/컨테이너
        #  어느 쪽이든 포트값은 동일하고, "호스트 이름"만 다릅니다.)
        # 두 경우를 하나의 값으로 만족시킬 수 없어 HOST만 환경변수 기본값 문법으로 처리합니다.
        # 기본값은 localhost(호스트 실행 흐름)이고, 루트 docker-compose.yml의 api-gateway 서비스에서
        # *_HOST 를 서비스명으로 오버라이드합니다.
        #
        # 실제 API 스펙/경로는 도메인 설계 확정 후 재작성하세요. 아래는 실행 확인용 임의 경로입니다.
        ```
        
    - 주의: `testImplementation으로만 의존` (common-module)
    - 이벤트 모듈 ADR 1 ( `0001-common-event-scope` )
        
        ```sql
        # ADR-0001: common-event 모듈 사용 범위 제한
        
        ## 상태
        채택됨
        
        ## 배경
        공통 모듈이 존재하면 개발 편의를 위해 서비스 내부 도메인 엔티티나 내부 DTO를 그대로
        common-event에 넣고 공유하려는 유혹이 생긴다. 이렇게 되면 서비스 간 결합도가 극도로
        높아져 MSA를 도입한 의미가 사라진다.
        
        ## 결정
        - common-event에는 Kafka로 전송되는 **이벤트 payload(DTO)와 그 안에서 쓰이는 enum만** 포함한다.
        - 서비스 내부 도메인 엔티티, 애그리거트, 리포지토리, 서비스 전용 DTO는 절대 포함하지 않는다.
        - 이벤트는 버전을 명시한다 (예: OrderCreatedEventV1). 필드 추가는 하위호환, breaking change는 새 버전으로.
        - common-event의 build.gradle에는 JPA/영속성 프레임워크 의존성을 추가하지 않는다.
        - 위 규칙은 `CommonEventArchitectureTest`(ArchUnit)로 CI에서 자동 검증한다.
        
        ## 결과
        - 장점: 결합도를 낮게 유지하면서도 이벤트 계약을 빠르게 공유할 수 있다.
        - 단점: 이벤트 스키마 변경 시에도 여러 서비스가 함께 재배포되어야 하는 결합은 여전히 남는다.
          서비스 수가 크게 늘어나면(예: 10개 이상) Avro + Schema Registry 등으로 전환을 재검토한다.
        ```
        
        ```sql
        /**
         * [ADR-0001] common-event 모듈 사용 범위 강제 테스트.
         *
         * 이 모듈에는 Kafka 이벤트 payload(DTO)와 enum만 있어야 하며,
         * 아래 두 가지가 절대 섞여 들어가서는 안 됩니다.
         *   1) JPA/영속성 프레임워크 의존 (엔티티가 섞여 들어왔다는 신호)
         *   2) 특정 서비스의 domain 패키지 참조 (도메인 로직 결합)
         *
         * 한계: 이 테스트는 "이 모듈 내부의 클래스"가 금지된 패키지를 참조하는지만 검사합니다.
         * 애초에 common-event의 build.gradle에 JPA 의존성을 추가하지 않는 것이 1차 방어선이고,
         * 이 테스트는 실수로 추가되었을 때 빌드를 실패시키는 2차 방어선입니다.
         */
        class CommonEventArchitectureTest {
        ```
        
    - 로컬 모니터링 구성 ADR 2 (`0002-monitoring-deferred` )
        
        ```sql
        # ADR-0002: 로컬 모니터링 구성과 프로덕션 모니터링 스택 결정의 분리
        
        ## 상태
        채택됨
        
        ## 배경
        인프라팀의 모니터링 스택(Prometheus/Grafana, Datadog 등)이 아직 확정되지 않았다.
        그런데 로컬 개발자가 자신이 작성한 계측 코드(메트릭, 트레이스)가 제대로 동작하는지
        검증할 수단은 필요하다.
        
        ## 결정
        - local-infra/monitoring/ 에는 **로컬 검증 목적**으로 OpenTelemetry Collector 설정과
          Prometheus 스크레이프 설정만 포함한다. (`docker compose --profile monitoring`으로 선택 기동)
        - Grafana 대시보드, 알림 규칙 등 **프로덕션 모니터링 산출물은 포함하지 않는다.**
          이는 인프라팀의 최종 스택 결정 이후, 그리고 "이 레포가 해당 자산의 소유권을 가져야 하는지"
          별도 합의 이후에 논의한다.
        
        ## 결과
        - OpenTelemetry는 벤더 중립 표준이므로, 인프라팀이 어떤 백엔드를 선택하든 계측 코드
          자체는 바뀌지 않아 폐기 리스크가 낮다.
        - Prometheus 스크레이프 설정은 Spring Boot Actuator가 기본 제공하는 포맷을 로컬에서
          확인하는 용도로만 쓰이며, 프로덕션에서 실제 Prometheus를 쓴다는 것을 의미하지 않는다.
        
        ```
        
    
- 논의 필요
    
    ### 인프라팀과 논의 필요
    
    - **서버 간 인증 방식 및 관리 주체**: mTLS(Istio) vs OAuth 2.0 Client Credentials 중 방식 확정 필요. 백엔드 제안: OAuth Client Credentials로 먼저 시작하고, 여유 되면 인프라팀이 mTLS를 얹어 이중 방어로 확장?
    - **k8s 도입 여부 최종 확정**: 도입 시 Eureka/Config Server 대체 가능 → 서비스 디스커버리·설정관리 설계가 갈리므로 우선순위 높음
    - **Redis 도입 여부**: 알림(SSE 다중 인스턴스 공유, 중복발송 방지)과 타임딜(재고 동시성 제어) 두 도메인에서 필요성이 구체적으로 확인됨 — 인프라팀 검토 요청
    
    ### AI팀과 논의 필요
    
    [필요 데이터 스키마 (AI → 백엔드)](https://app.notion.com/p/AI-3bc9e3e335cc80888d23ec5c276f4586?pvs=21) 
    
    - **소비 이력 데이터 연동 방식**: Kafka 이벤트 스트리밍을 처음부터 쓸지, 배치 API로 시작할지 — 8/14에 Kafka 사용 자체는 확정됐으나 AI팀과 정확한 스키마·연동 방식 확인 필요
        - **실시간이 필요하면** → Kafka 이벤트 스트리밍 (구매 발생 즉시 이벤트 발행)
        - **모아서 처리해도 되면** → 배치 API (예: 매일 새벽에 그날 쌓인 데이터를 한 번에 넘겨줌)
    - **AI 데이터 저장 형식**: MongoDB 활용 예정이나, 구체적 스키마는 AI팀 요구사항 확인 필요
    - AI 요구사항
        
        ## 우선순위 요청 사항
        
        1. allergen_ingredient_map 신규 테이블 승인 및 초기 데이터 구축(역추천·대체상품 안전 필터의 선행 조건)
        2. product_master.ingredients / allergen_tags 필드 확정 및 원료 파싱 규칙 합의(1주차 내)
        3. behavior_events.pet_id 연결 정확도(다견·다묘 가정에서 이벤트가 특정 반려동물에 올바르게 귀속되는지) 검증
        4. aafco_compliance / guaranteed_analysis 신규 테이블 승인 및 상품 등록 시 AAFCO 라벨 정보(생애주기, 검증 방식, 보증분석치) 입력 프로세스 확정
        5. aafco_nutrient_profile_reference 시드 데이터 구축(AAFCO 공식 발행 자료 기준값 입력, 개정 버전 관리 방식 합의)
        6. **pet_profile.birth_date** 필수 전환 및 기존 age-only 데이터 마이그레이션 방식 합의
        7. **신규 스키마 확정 및 초기 데이터 적재 방식 합의**
            
            
        
        1,3,4,5: 백엔드와 독립된 테이블이라 문제 없어보임
        
        2: product 테이블 구조 미정
        
        6: pet_profile 테이블 구조 미정
        
    
    ### 백엔드 내부(팀원 간) 정리 필요
    
    - **경쟁사 조사 반영**: 확정 경쟁사(댕냥잇·쿠팡·핏펫·어바웃펫·Chewy·아마존) 기준으로 세 문서(비교분석/도메인모델/차별화전략) 수정 완료
    - **서버 간 인증 담당자**: 방식이 OAuth Client Credentials로 정해지면 백엔드 인증 담당자가 맡는 방향으로 제안 예정
    
    [OAuth 2.0 Client Credentials](8%2018%20%EB%8D%B0%EC%9D%BC%EB%A6%AC%EC%8A%A4%ED%81%AC%EB%9F%BC/OAuth%202%200%20Client%20Credentials%203c09e3e335cc80fc86e2cc4916bbe6b9.md)
    

## 3. 피드백 및 개선 사항

---

- -

## 4. 다음 날 계획

---

- 세팅 이어서 진행