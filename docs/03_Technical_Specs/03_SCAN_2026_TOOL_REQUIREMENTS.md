# SCAN 2026 P0·V1 분석 도구 요구사항
> Created: 2026-07-25 23:46
> Last Updated: 2026-07-27 15:52
> Status: Draft 1 · Approved Baseline

## 1. 문서 목적

이 문서는 [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md)의
P0 공통 기반과 DEX·AUTH·FREEZE V1 vertical slice를 구현 가능한 요구사항으로
전환한다.

현재 단계에서는 기술 스택, CLI·노트북·웹 UI, 배포 방식을 확정하지 않는다.
입력·출력·증거·오류·캐시 계약과 fixture 기반 완료 조건을 먼저 고정해 이후
기술 선택을 비교할 기준을 만든다.

## 2. 범위와 경계

### 2.1 포함 범위

| 구분 | 기능 |
|:---|:---|
| P0 공통 기반 | `BASE-PROVENANCE`, `BASE-EXPORT`, `BASE-CACHE` |
| P0 결정적 입력·정합 | `EVM-TX`, `EVM-LOG`, `RECON` |
| V1 DEX | 로그·호출에서 입력, 풀 출력, 사용자 최종 출력을 분리 |
| V1 AUTH | 승인, 과거 allowance, 성공 권한 소비를 연결 |
| V1 FREEZE | 주소별 블랙리스트 이벤트·과거 상태·공식 맥락을 분리 |
| 회귀 검증 | confirmed fixture 3개를 exact-match 입력으로 사용 |

### 2.2 제외 범위

- 일반 N홉 추적, 라벨 탐색, 그래프 시각화는 P1에서 정의한다.
- Bitcoin, 브리지·크로스체인, 일반 OSINT 탐색, 휴리스틱은 P2에서 정의한다.
- NFT·프록시·믹서·대출·가격·LP 러그 전문 어댑터는 P3에서 정의한다.
- 피싱·탈취·범죄 의도, 법적 책임, 현재 제재 상태를 자동 판정하지 않는다.
- 특정 공급자, 데이터베이스, 프로그래밍 언어, UI 프레임워크를 채택하지 않는다.

복수 문제 Queue, 서브에이전트 역할, worker 동시성, 독립 검증과 제출
대기열은 [Agentic Parallel Solve Flow](./07_AGENTIC_PARALLEL_SOLVE_FLOW.md)의
별도 `REQ-OPS-*` 계약이다. 이 문서의 P0·V1 leaf 분석 요구사항과
`TASK-001` 착수 순서를 변경하지 않으며 공식 Rules와 별도 구현 승인을
통과한 뒤 활성화한다.

FREEZE V1에서 허용하는 OSINT 범위는 **입력으로 주어진 발행사·규제기관 공식
출처의 원문, URL, 조회 시각과 주소 명시 여부를 보존하고 온체인 사실과
분리하는 것**뿐이다. 검색엔진·SNS·ENS·도메인에서 새로운 단서를 찾는 일반
OSINT 탐색은 P2이며 V1 완료 조건이 아니다.

### 2.3 오픈소스 사전조사 Gate

P0·V1 요구사항을 직접 구현하기 전에 기능별 공개 repository와 공식 package를
검색하고 [오픈소스 포렌식 사전조사](./06_OPEN_SOURCE_FORENSICS_REVIEW.md)의
`ADOPT / WRAP / BORROW / BUILD / REJECT` 결정을 기록한다.

후보가 요구사항 일부를 충족하더라도 evidence·source·partial·failed 계약을
깨뜨리면 core에 직접 결합하지 않는다. port 뒤에서 격리하거나 해당 부분만
직접 구현한다.

## 3. 요구사항 표기와 우선순위

| 표기 | 의미 |
|:---|:---|
| `MUST` | P0·V1 완료에 필수 |
| `SHOULD` | 특별한 제약이 없으면 구현 |
| `MAY` | 호환성을 깨지 않는 선택 기능 |
| `REQ-COM-*` | 공통 입력·출력 요구사항 |
| `REQ-P0-*` | P0 기반·EVM·정합 요구사항 |
| `REQ-V1-*` | fixture별 vertical slice 요구사항 |
| `REQ-NFR-*` | 보안·재현성·성능 등 비기능 요구사항 |
| `REQ-OPS-*` | 별도 Agentic Parallel Solve Flow의 운영·병렬성·검증·제출 요구사항 |

각 결과는 요구사항 ID와 연결할 수 있어야 한다. fixture의
`expected.json.scoring.requirements[].requirement_id`는 fixture 채점 ID이며,
이 문서의 구현 요구사항 ID와 별도로 유지한다.

## 4. 공통 입력 계약

### 4.1 작업 입력

| 필드 | 형식 | 필수 | 규칙 |
|:---|:---|:---:|:---|
| `analysis_id` | string | MUST | 한 실행 안에서 유일한 작업 ID |
| `analysis_type` | enum | MUST | `dex_swap`, `auth_consumption`, `address_freeze` |
| `chain_id` | integer | MUST | V1은 Ethereum mainnet `1`만 지원 |
| `inputs` | object | MUST | TX·주소·블록 등 유형별 시작점 |
| `source_policy` | object | MUST | 허용 소스 ID, 우선순위, fallback 허용 여부 |
| `fixture_id` | string | MAY | 회귀 검증이면 `FX-...` ID |
| `requested_at` | RFC 3339 | MUST | 실행 요청 시각과 시간대 |

### 4.2 입력 정규화

| ID | 요구사항 |
|:---|:---|
| `REQ-COM-IN-001` | EVM 주소와 TX 해시는 입력 검증 후 소문자 `0x` 형식으로 정규화해야 한다. 원 입력도 provenance에 보존한다. |
| `REQ-COM-IN-002` | 과거 상태 조회는 명시적 블록 번호를 사용해야 하며, `latest`를 과거 상태의 대체값으로 사용하면 안 된다. |
| `REQ-COM-IN-003` | raw 토큰·네이티브 수량은 10진 문자열로 처리해야 한다. IEEE-754 부동소수점으로 변환하면 안 된다. |
| `REQ-COM-IN-004` | 알 수 없는 체인, 잘못된 해시·주소·블록, 중복되거나 모순된 입력은 외부 조회 전에 거부해야 한다. |
| `REQ-COM-IN-005` | 비밀키·서명키·seed phrase를 입력으로 받지 않아야 한다. API 키는 실행 환경의 secret 참조로만 전달한다. |

## 5. 공통 결과와 증거 계약

### 5.1 결과 봉투

모든 분석 유형은 최소한 아래 논리 구조를 출력해야 한다. 실제 JSON 계약은
[공통 분석 I/O Schema 0.1](./05_ANALYSIS_IO_SCHEMA.md)과 세 JSON Schema
파일로 분리해 정의한다.

| 필드 | 형식 | 규칙 |
|:---|:---|:---|
| `analysis_id` | string | 입력과 동일 |
| `analysis_type` | enum | 입력과 동일 |
| `status` | enum | `complete`, `partial`, `failed` |
| `schema_version` | string | 출력 계약 버전 |
| `results` | array | 유형별 결정적 결과 |
| `evidence` | array | 결과를 입증하는 정규화 증거 |
| `sources` | array | 실제 사용한 소스와 역할 |
| `warnings` | array | 결과를 무효화하지 않는 한계 |
| `errors` | array | 구조화된 실패 원인 |
| `run` | object | 시작·종료 시각, cache·retry·fallback 요약 |

### 5.2 결과·증거 필수 규칙

| ID | 요구사항 |
|:---|:---|
| `REQ-COM-OUT-001` | 각 `result_id`는 하나 이상의 `evidence_id`를 참조해야 한다. |
| `REQ-COM-OUT-002` | 각 증거는 `source_id`, 조회 방법, 체인·블록·TX·log/trace 위치 중 적용 가능한 식별자, `retrieved_at`을 가져야 한다. |
| `REQ-COM-OUT-003` | raw 값과 사람이 읽는 값은 분리해야 한다. 수량은 `amount_raw`, `decimals`, `symbol`을 보존하고 표시값은 파생값으로 표시한다. |
| `REQ-COM-OUT-004` | 사실 분류는 `confirmed_fact`, `external_context`, `heuristic`, `not_assessed` 중 하나여야 한다. 서로 다른 분류를 한 필드에 합치면 안 된다. |
| `REQ-COM-OUT-005` | 이벤트·호출·상태·맥락 증거는 각각 `event`, `call`, `state`, `context` 유형으로 구분해야 한다. |
| `REQ-COM-OUT-006` | `partial`과 `failed`에서도 이미 확보한 증거와 실패 지점을 보존해야 한다. |
| `REQ-COM-OUT-007` | 모든 출력은 적용한 도구 요구사항 ID와 fixture 채점 ID를 각각 추적할 수 있어야 한다. |

## 6. P0 공통 기반 요구사항

### 6.1 Provenance

| ID | 요구사항 |
|:---|:---|
| `REQ-P0-PROV-001` | 모든 외부 조회에 등록부의 `DS-...` 소스 ID, 공급자 식별자, 메서드·경로, 조회 시각을 기록해야 한다. |
| `REQ-P0-PROV-002` | 요청의 비밀값을 제거한 정규화 표현과 raw 응답의 SHA-256 또는 저장 artifact 참조를 기록해야 한다. |
| `REQ-P0-PROV-003` | 사용한 블록 번호·해시·finality 상태를 가능한 경우 함께 보존해야 한다. |
| `REQ-P0-PROV-004` | 공식 문서·ABI·배포 주소는 URL, 버전·커밋, 라이선스와 조회 시각을 가능한 범위에서 고정해야 한다. |
| `REQ-P0-PROV-005` | fallback 공급자를 사용하면 최초 실패와 대체 공급자 결과를 모두 남겨야 하며 조용히 교체하면 안 된다. |

### 6.2 Export

| ID | 요구사항 |
|:---|:---|
| `REQ-P0-EXPORT-001` | 기계 판독 가능한 JSON 결과를 반드시 출력해야 한다. |
| `REQ-P0-EXPORT-002` | 사람이 검토할 수 있는 Markdown 증거 표를 반드시 출력해야 한다. |
| `REQ-P0-EXPORT-003` | JSON과 Markdown은 같은 `analysis_id`, 결과 ID, 증거 ID를 사용해야 한다. |
| `REQ-P0-EXPORT-004` | export에는 secret, 인증 헤더, API 키, 로컬 사용자 경로를 포함하면 안 된다. |
| `REQ-P0-EXPORT-005` | CSV는 표 형태 결과에 한해 선택적으로 제공할 수 있으나 JSON을 대체할 수 없다. |

### 6.3 Cache·retry·resume

| ID | 요구사항 |
|:---|:---|
| `REQ-P0-CACHE-001` | 캐시 키는 `chain_id + source capability + method + normalized parameters + block tag`를 포함해야 한다. |
| `REQ-P0-CACHE-002` | 확정된 과거 블록·TX 응답은 immutable로 취급할 수 있다. `latest`·미확정 블록은 별도 TTL과 재검증 정책을 가져야 한다. |
| `REQ-P0-CACHE-003` | 캐시 항목은 원본 hash, source ID, 공급자, 조회 시각, 만료·무효화 상태를 보존해야 한다. |
| `REQ-P0-CACHE-004` | 자동 재시도는 idempotent 읽기 요청의 timeout·429·일시적 5xx에만 적용한다. |
| `REQ-P0-CACHE-005` | 재시도는 최대 횟수, 지수 백오프와 jitter를 사용하고 각 시도를 실행 기록에 남겨야 한다. 구체 수치는 기술 선택 시 정한다. |
| `REQ-P0-CACHE-006` | 중단된 작업은 완료된 조회 단위의 checkpoint에서 재개할 수 있어야 한다. |
| `REQ-P0-CACHE-007` | 캐시·checkpoint에 secret이나 인증 헤더를 저장하면 안 된다. |

## 7. P0 EVM 입력·정합 요구사항

| ID | 기능 | 요구사항 |
|:---|:---|:---|
| `REQ-P0-EVM-001` | EVM-TX | hash로 TX, receipt, status, block number·hash, sender, receiver, value, input, nonce를 수집해야 한다. |
| `REQ-P0-EVM-002` | EVM-TX | receipt `status: 0`인 실패 거래를 성공 자산 이동·상태 변화에서 제외하고 별도 실패 사실로 보존해야 한다. |
| `REQ-P0-EVM-003` | EVM-LOG | address, topics, data, transaction index, log index와 제거 여부를 raw로 보존해야 한다. |
| `REQ-P0-EVM-004` | EVM-LOG | ABI 디코딩값은 raw log와 연결하고, 디코딩 실패 시 raw 증거를 버리지 않아야 한다. |
| `REQ-P0-EVM-005` | RECON | TX·log·call·state를 chain ID, block, TX hash, address, index로 정합해야 한다. |
| `REQ-P0-EVM-006` | RECON | 같은 자산의 raw 수량·decimals·symbol을 분리하고, 서로 다른 자산이나 wrapped/native를 자동 합산하면 안 된다. |
| `REQ-P0-EVM-007` | RECON | UTC timestamp와 block timestamp의 출처를 기록하고 시간 순서를 검증해야 한다. |
| `REQ-P0-EVM-008` | RECON | exact-match 문제에서 반올림된 표시값을 채점값으로 사용하면 안 된다. |

V1에 필요한 과거 state와 trace는 우선순위상 P1 공통 기능이지만 AUTH·FREEZE
fixture를 통과하는 최소 어댑터만 V1에 포함한다. 범용 state 탐색기와 범용
trace 탐색기는 P1 범위다.

## 8. V1 DEX 요구사항

대상 fixture는 `FX-SVC-DEX-001`이며 raw 오차는 0이다.

| ID | 요구사항 |
|:---|:---|
| `REQ-V1-DEX-001` | 입력 TX에서 USDC `25000000000` raw의 풀 입력을 Transfer와 Swap 증거로 복원해야 한다. |
| `REQ-V1-DEX-002` | 풀 출력은 WETH `14449515027026387018` raw로 기록해야 한다. |
| `REQ-V1-DEX-003` | WETH Withdrawal 이후 라우터에서 사용자로 전달된 native ETH `14449515027026387018` wei를 사용자 최종 출력으로 기록해야 한다. |
| `REQ-V1-DEX-004` | `pool_output` WETH와 `user_net_output` ETH를 별도 결과로 출력해야 하며 둘을 같은 자산으로 합치면 안 된다. |
| `REQ-V1-DEX-005` | Transfer·Swap·Withdrawal 이벤트와 internal ETH call을 증거 유형별로 연결해야 한다. |
| `REQ-V1-DEX-006` | 라우터·Factory·pair 메타데이터는 supporting provenance로 분리하고 거래 결과의 원본 증거를 대체하지 않아야 한다. |

## 9. V1 AUTH 요구사항

대상 fixture는 `FX-EVM-AUTH-001`이며 allowance·전송량 raw 오차는 0이다.

| ID | 요구사항 |
|:---|:---|
| `REQ-V1-AUTH-001` | Approval 이벤트와 approve calldata에서 owner, spender, amount가 일치하는지 검증해야 한다. |
| `REQ-V1-AUTH-002` | 승인 직전·직후와 소비 직전·직후 네 블록의 historical allowance를 조회해야 한다. |
| `REQ-V1-AUTH-003` | 성공 trace의 `transferFrom` from, to, amount를 Transfer 이벤트와 연결해야 한다. |
| `REQ-V1-AUTH-004` | allowance 감소량과 성공 `transferFrom`·Transfer 금액 `4500000` raw가 일치해야 한다. |
| `REQ-V1-AUTH-005` | 중간의 receipt status 0 거래 세 건은 소비 결과에서 제외하고 제외 근거를 남겨야 한다. |
| `REQ-V1-AUTH-006` | Approval 이벤트, approve 호출, allowance 상태, transferFrom 호출, Transfer 이벤트를 서로 다른 증거로 보존해야 한다. |
| `REQ-V1-AUTH-007` | 확정 결과는 `권한 소비`로 표현해야 한다. 피싱·탈취·피해자 귀속은 `not_assessed`로 출력해야 한다. |

## 10. V1 FREEZE 요구사항

대상 fixture는 `FX-EVM-FREEZE-001`이며 boolean 상태는 exact match다.

| ID | 요구사항 |
|:---|:---|
| `REQ-V1-FREEZE-001` | blacklist 호출·Blacklisted 이벤트·직전 `false`·직후 `true` 상태를 한 전이로 연결해야 한다. |
| `REQ-V1-FREEZE-002` | unBlacklist 호출·UnBlacklisted 이벤트·직전 `true`·직후 `false` 상태를 한 전이로 연결해야 한다. |
| `REQ-V1-FREEZE-003` | 네 historical `isBlacklisted(address)` 상태 조회의 블록과 raw 반환값을 보존해야 한다. |
| `REQ-V1-FREEZE-004` | 전역 pause와 주소별 blacklist를 구분하고, 이 fixture에서 pause는 적용 대상이 아님을 표시해야 한다. |
| `REQ-V1-FREEZE-005` | 이벤트, calldata, state, Circle·OFAC 맥락을 각각 event·call·state·context 증거로 분리해야 한다. |
| `REQ-V1-FREEZE-006` | Circle 자료의 주소 명시 여부와 OFAC 원문의 주소 명시 여부를 각각 보존해야 한다. |
| `REQ-V1-FREEZE-007` | 온체인 블랙리스트 상태와 범죄 의도·현재 제재 상태를 동일시하면 안 되며 후자는 `not_assessed`로 출력해야 한다. |
| `REQ-V1-FREEZE-008` | V1은 입력으로 주어진 공식 URL의 수집·보존·분리만 수행한다. 새로운 웹 단서를 찾거나 인물·서비스를 귀속하지 않아야 한다. |

## 11. 오류와 부분 성공 계약

### 11.1 오류 코드

| 코드 | 의미 | 기본 상태 |
|:---|:---|:---|
| `invalid_input` | 주소·해시·블록·유형이 잘못됨 | `failed` |
| `unsupported_chain` | 지원하지 않는 chain ID | `failed` |
| `source_unavailable` | 필수 소스에 접근 불가 | `partial` 또는 `failed` |
| `rate_limited` | 호출 제한으로 재시도 소진 | `partial` 또는 `failed` |
| `archive_required` | 과거 상태를 latest로 대체할 수 없음 | `partial` 또는 `failed` |
| `trace_unavailable` | 필수 내부 호출을 확보할 수 없음 | `partial` |
| `decode_failed` | ABI·calldata·log 디코딩 실패 | `partial` |
| `evidence_incomplete` | 결과에 필요한 증거 연결 부족 | `partial` |
| `reconciliation_failed` | 수량·주소·블록·호출 간 불일치 | `failed` |
| `schema_invalid` | 입력·출력 계약 검증 실패 | `failed` |
| `rule_restricted` | 대회 규정이 해당 자동화·소스를 제한 | `failed` |

### 11.2 오류 필드

각 오류는 `code`, `message`, `stage`, `source_id`, `retryable`,
`attempt_count`, `last_attempt_at`, `related_evidence_ids` 중 적용 가능한
필드를 가져야 한다. 인증정보나 공급자 응답의 비밀값을 메시지에 포함하면 안 된다.

필수 채점 요구사항 하나라도 미충족이면 `complete`를 출력할 수 없다. 일부 결과가
증거로 입증되면 `partial`, 유효한 결과가 없거나 정합이 깨지면 `failed`로 둔다.

## 12. 비기능 요구사항

| ID | 구분 | 요구사항 |
|:---|:---|:---|
| `REQ-NFR-001` | 결정성 | 같은 fixture와 같은 고정 소스를 반복 실행하면 모든 채점 raw 값과 boolean이 같아야 한다. |
| `REQ-NFR-002` | 재현성 | export만으로 사용한 입력·소스·블록·증거와 도구 버전을 식별할 수 있어야 한다. |
| `REQ-NFR-003` | 오프라인 재생 | 한 번 성공적으로 저장한 fixture 원본은 네트워크 없이 캐시에서 재검증할 수 있어야 한다. |
| `REQ-NFR-004` | 정밀도 | EVM uint256 범위의 raw 정수에 정밀도 손실이 없어야 한다. |
| `REQ-NFR-005` | 보안 | secret은 로그·캐시·export·오류에 평문으로 나타나면 안 된다. |
| `REQ-NFR-006` | 교체 가능성 | 공급자별 코드는 공통 source capability 뒤에 격리하고 결과 계약은 공급자에 종속되지 않아야 한다. |
| `REQ-NFR-007` | 감사 가능성 | 사람이 결과에서 raw TX·log·call·state 또는 공식 URL로 역추적할 수 있어야 한다. |
| `REQ-NFR-008` | 규정 준수 | 공식 규정 확인 전 자동화·API 허용을 확정으로 표시하면 안 되며 제한 발견 시 실행 전에 차단해야 한다. |

성능 목표는 실제 공급자와 기술 스택 측정 전까지 수치로 확정하지 않는다.
Draft 1의 성능 기준은 “캐시 hit가 외부 호출을 하지 않음”, “rate limit에서
무한 재시도하지 않음”, “중단 후 완료된 조회를 다시 호출하지 않음”이다.

## 13. 완료·부분·실패 판정

### 13.1 공통 완료

- 입력·출력 스키마 검증을 통과한다.
- 필수 결과마다 존재하는 증거 ID와 실제 소스 provenance가 연결된다.
- JSON과 Markdown 증거 표가 동일한 결과를 표현한다.
- cache·retry·fallback 사용 여부가 실행 기록에 남는다.
- secret 검사를 통과한다.

### 13.2 Fixture 완료 행렬

| Fixture | 완료 | 부분 | 실패 |
|:---|:---|:---|:---|
| DEX | USDC 입력, WETH 풀 출력, native ETH 사용자 출력과 모든 증거 exact match | 풀 출력 또는 사용자 출력 한쪽과 근거만 확보 | 자산·수량 오판, WETH를 사용자 최종 자산으로 제출 |
| AUTH | 승인·allowance 4지점·성공 소비·실패 TX 제외가 exact match | 승인 또는 소비 일부만 증거로 연결 | 실패 TX를 소비로 포함, 감소량 불일치, 탈취로 단정 |
| FREEZE | 두 호출·이벤트·네 상태와 공식 맥락 분리가 exact match | 한 전이만 입증하거나 공식 맥락 보존 누락 | 상태 전이 오판, latest로 과거 상태 대체, 맥락을 온체인 사실로 단정 |

## 14. 검증 계획

| 검증 ID | 대상 | 방법 | 통과 기준 |
|:---|:---|:---|:---|
| `TEST-SCHEMA-001` | 기존 fixture 패키지 | 공통 fixture 검증기 실행 | 3개 모두 PASS |
| `TEST-CACHE-001` | immutable 응답 | 동일 요청 2회 실행 | 두 번째 실행 외부 호출 0, 결과 동일 |
| `TEST-RETRY-001` | timeout·429·5xx | 공급자 오류 주입 | 제한된 재시도·backoff 기록 후 성공 또는 구조화 실패 |
| `TEST-FALLBACK-001` | 공급자 장애 | 주 공급자 실패 주입 | 실패와 fallback source가 모두 provenance에 기록 |
| `TEST-EXPORT-001` | JSON·Markdown | 동일 실행 export 비교 | ID·값·증거 참조 일치, secret 0건 |
| `TEST-DEX-001` | DEX fixture | 도구 결과와 expected 비교 | 필수 raw 값·자산·증거 exact match |
| `TEST-AUTH-001` | AUTH fixture | 도구 결과와 expected 비교 | allowance·소비·제외 TX exact match |
| `TEST-FREEZE-001` | FREEZE fixture | 도구 결과와 expected 비교 | 두 전이·네 상태·맥락 분리 exact match |

구현 완료 시 fixture의 기존 `schema_version: 0.1`을 바꾸지 않는다. 도구
출력 계약은 별도 버전을 사용하며, fixture 구조 변경이 실제로 필요할 때만
fixture schema 개정을 제안한다.

## 15. 미결정 사항

- 노트북·웹 UI를 V1 이후 어떤 조건에서 추가할지
- Python dependency의 실제 버전과 lock 결과
- 공급자별 adapter와 fallback 우선순위
- raw artifact 저장 형식·경로·보존 기간·용량
- 구체 retry 횟수·backoff 상한·`latest` TTL
- Pydantic 모델에서 Schema 0.1을 생성·대조하는 명령과 module 경로
- 실제 네트워크·캐시 성능 기준
- 2026년 공식 규정에 따른 자동화·API 허용 범위

## 16. 다음 단계

1. 요구사항별 기술 후보와 공급자 adapter 전략을 기술 선택 기록 Draft 1에서 비교했다.
2. 공통 작업 입력·결과·오류 JSON Schema 0.1과 fixture 변환 예제를 작성했다.
3. Python package 초기화 전에 Python 개발 원칙 Draft 1을 작성했다.
4. CLI command flow와 terminal HTML Preview Draft를 작성했다.
5. 사용자가 Preview를 확인하고 UI-First Gate를 통과시켰다.
6. 승인된 Schema·UI 경계를 구현 backlog와 회귀 QA 시나리오 Draft로 분해했다.
7. P0·V1 오픈소스 `OSS-*` 결정과 SQLite 논리 DB Schema를 확정했다.
8. Document Completion Gate를 통과했다.
9. 공식 규정은 Active Watch로 유지하며 변경 시 `REQ-NFR-008`과 source policy를 갱신한다.
10. 별도 구현 승인 후 Python project 초기화를 시작한다.

## 17. Related Documents

- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0·V1 범위와 단계 제한
- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 30문항과 완료·부분·실패 조건
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 요구사항을 실행하는 명령·상태 흐름
- **UI_Screens**: [HTML Terminal Preview](../02_UI_Screens/previews/01_cli_terminal_preview.html) - complete·partial·failed 화면
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - `DS-...` 소스 능력·제약
- **Technical_Specs**: [SQLite 논리 DB Schema](./01_DB_SCHEMA.md) - cache·artifact·result·evidence 저장 계약
- **Technical_Specs**: [Reference Fixture Schema](./02_REFERENCE_FIXTURE_SCHEMA.md) - fixture JSON·증거 분리 계약
- **Technical_Specs**: [Python 개발 원칙](./00_DEVELOPMENT_PRINCIPLES.md) - 이 요구사항을 구현할 구조·품질·보안 기준
- **Technical_Specs**: [P0·V1 기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md) - 요구사항을 구현할 런타임·adapter·저장·검증 결정
- **Technical_Specs**: [공통 분석 I/O Schema](./05_ANALYSIS_IO_SCHEMA.md) - 이 문서의 입력·결과·오류 요구사항을 고정한 JSON 계약
- **Technical_Specs**: [오픈소스 포렌식 사전조사](./06_OPEN_SOURCE_FORENSICS_REVIEW.md) - 요구사항별 재사용·직접 구현 결정 Gate
- **Technical_Specs**: [Agentic Parallel Solve Flow](./07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - P0·V1 leaf 결과를 병렬 운영하는 별도 Rules-gated 계약
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 여러 문제·worker·검증·제출 상태 UI
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - 요구사항별 구현 책임과 승인 Gate
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - fixture 목록과 승격 기준
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 요구사항별 실행·오류 주입·통과 기준
- **QA_Validation**: [DEX fixture](../05_QA_Validation/fixtures/FX-SVC-DEX-001/README.md) - DEX exact-match 기준
- **QA_Validation**: [AUTH fixture](../05_QA_Validation/fixtures/FX-EVM-AUTH-001/README.md) - AUTH exact-match 기준
- **QA_Validation**: [FREEZE fixture](../05_QA_Validation/fixtures/FX-EVM-FREEZE-001/README.md) - FREEZE exact-match 기준
