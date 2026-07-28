# Live Provider Capability Smoke Runner 준비 보고서
> Created: 2026-07-29 02:56
> Last Updated: 2026-07-29 02:56
> Status: Prepared · Live Not Executed · Rules Unclear

## 1. 목적과 판정

PR #41의 Live Provider Gate를 실제 실행할 최소 runner를 준비하고, 공식
Rules와 endpoint가 없는 현재 상태에서 네트워크 호출이 열리지 않는지
검증했다.

**판정: runner 준비 완료, capability smoke와 provider 채택은 미완료다.**

## 2. 현재 외부 상태

| 항목 | 결과 |
|:---|:---|
| SCAN 공식 사이트 | 2026-07-29 02:50 KST 재확인, 상세 Rules 없음 |
| CTFd 공개 home | 예선 2026-08-02 09:00 KST 표시, 공개 Rules 없음 |
| `RULE-API-001` / `RULE-AI-001` | `unclear` 유지 |
| `SCAN_EVM_PRIMARY_RPC_URL` | 미설정 |
| `SCAN_EVM_VERIFY_RPC_URL` | 미설정 |
| `SCAN_EVM_TRACE_RPC_URL` | 미설정 |
| live EVM calls | 0 |
| live LLM calls | 0 |

secret 값은 조회·출력·문서화하지 않았다.

## 3. 구현 범위

| 파일 | 역할 |
|:---|:---|
| `src/scan_tool/application/provider_smoke.py` | 역할별 read-only 요청·Gate·artifact·bounded report |
| `scripts/smoke_live_provider.py` | 명시적 opt-in composition root |
| `tests/unit/test_provider_smoke.py` | Rules·endpoint·allowlist·secret·artifact·오류 검증 |

새 dependency·Analysis I/O·Operations Schema·SQLite migration·분석 type은
추가하지 않았다. TASK-012 EVM Core analyzer도 시작하지 않았다.

## 4. 안전 계약

- 기본 실행은 `status=not_executed`, `network_calls=0`이다.
- 실제 호출에는 `--execute`와 `--rules-status allowed`가 함께 필요하다.
- 역할별 endpoint는 환경변수에서만 읽고 report에는 논리 provider ID만 남긴다.
- HTTPS endpoint만 허용한다.
- allowlist는 chain ID, TX, receipt, block, filtered logs, historical call,
  trace read method뿐이다.
- raw response는 `.scan/` 아래 content-addressed artifact에 저장한다.
- endpoint path/query의 secret 후보가 raw response에 있으면 저장 전 차단한다.
- terminal에는 endpoint·absolute report path·secret을 출력하지 않는다.
- invalid response는 성공으로 위장하지 않고 `partial/failed` observation으로 남긴다.

## 5. 실행 증거

```text
ruff: PASS
unit: 7 passed
dry-run: status=not_executed
dry-run network_calls=0
primary methods:
  eth_chainId
  eth_getTransactionByHash
  eth_getTransactionReceipt
  eth_getBlockByNumber
  eth_getLogs
  eth_call
  debug_traceTransaction
```

전체 저장소 Gate 결과는 커밋 전 다시 기록한다.

```text
repository tests: 284 passed
fixture Schema: PASS 7
analysis Schema: PASS 3
analysis probes: PASS 35
operations probes: PASS 17
traceability: PASS 1034 links
security scan: PASS 84 files
```

## 6. 미실행·차단 조건

1. 공식 Rules에서 API·AI mode가 허용 또는 조건부 허용으로 확인돼야 한다.
2. primary·verify endpoint를 로컬 secret 환경에 구성해야 한다.
3. trace-dependent `EVM-TOKEN-002`를 위해 독립 trace 역할을 정해야 한다.
4. 실제 계정 plan·rate limit·timeout을 확인해야 한다.
5. 사용자 승인 뒤 `--execute --rules-status allowed`로 역할별 실행한다.

이 조건 전에는 capability 표를 `pass`로 바꾸거나 fixture를 `confirmed`로
승격하지 않는다.

## 7. 코드 품질 검토

| 영역 | 판정 |
|:---|:---|
| 정확성 | PASS - dry-run·Gate·role method·invalid response 테스트 |
| 타입·외부 입력 | PASS - role Literal, argparse choices, HTTPS 검증 |
| YAGNI/KISS/DRY | PASS - 기존 adapter·artifact·guard 재사용, dependency 0 |
| 부작용 | PASS - 기본 network 0, `.scan/` 외 저장 없음 |
| 보안 | PASS - secret 후보·endpoint·absolute path 비출력 |
| UI | N/A - CLI readiness runner, 화면 변경 없음 |

## 8. 365 글로벌 평가 기준

| 기준 | 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Partial | runner offline 검증, 실제 capability 미실행 |
| Potential Impact | Planned | TASK-012와 후속 EVM Work Package 공통 source Gate |
| Novelty | Planned | AI plan·Python proof·독립 provider 검증 구조 |
| UX | Partial | 안전한 dry-run·구조화 상태, live 운영 미실행 |
| Open-source | Pass | read-only method·Gate·테스트 공개 |
| Business Plan | N/A | 계정 plan·비용은 실제 준비 시 기록 |

## 9. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - API·AI 상태
- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - 실행 계약
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 후보 topology
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 잠금
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 1 순서
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 smoke 체크
- **QA_Validation**: [TASK-012 Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - 재현 대상
