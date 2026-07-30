# TASK-015 Source Readiness 보고서
> Created: 2026-07-30 04:23
> Last Updated: 2026-07-30 04:23
> Status: ENS Replay Passed · OFAC SLS Pinned · Actor Boundary Pending · Verifier Pending

## 1. 목적

TASK-015 독립 Verifier 전에 남아 있던 source 전제 중 ENS 제2 공급자 재현과
OFAC 현재 SLS 스냅샷 고정을 닫는다. Actor common-funder의 bounded prehistory와
service exclusion은 근거가 부족하므로 계속 미완료로 남긴다.

## 2. 변경 범위

- fixed-block ENS read-only replay runner와 unit test
- `PROVIDER-EVM-VERIFY`와 `BLOCKSCOUT-ETH-RPC` decoded 교차검증
- QuickNode HTTP 429와 Chainstack HTTP 403 실패 이력 보존
- OFAC current `SDN.CSV` URL·조회시각·크기·행 수·raw SHA-256 고정
- fixture evidence·README·provider replay 동기화

제품 `intel_context` analyzer, 공개 Analysis I/O Schema, Benchmark, fixture
status는 변경하지 않는다.

## 3. ENS 재현 결과

고정 block은 `25,640,270` (`0x1873d4e`)다.

| Fixture | Alchemy | Blockscout | decoded | 실패 보존 |
|:---|:---:|:---:|:---:|:---|
| `FX-OSINT-LABEL-CONFLICT-001` | complete 2/2 | complete 2/2 | resolver·address 일치 | QuickNode 2×429 · Chainstack 2×403 |
| `FX-OSINT-ENS-CONFLICT-001` | complete 4/4 | complete 4/4 | forward/reverse 일치 | QuickNode 4×429 · Chainstack 4×403 |

공급자별 HTTP 응답 serialization 차이 때문에 raw SHA-256은 다르다. 승격
근거는 동일 요청 범위·고정 block·ABI decoded 값의 일치다. 실패 공급자의
결과를 성공으로 추론하거나 대체하지 않는다.

## 4. OFAC SLS 스냅샷

| 필드 | 값 |
|:---|:---|
| provider | `OFAC-SANCTIONS-LIST-SERVICE` |
| resource | current `SDN.CSV` |
| retrieved_at | `2026-07-29T19:23:30Z` |
| HTTP | `200` |
| byte length | `5,624,423` |
| line count | `19,175` |
| raw SHA-256 | `464a917d662b9de3a26588499a8f1a4cfea341a70f3ace64038a5f8cb2b85b65` |
| target address match | `0` |

현재 CSV의 주소 부재는 context evidence다. 2022 공식 지정과 2025 공식
해제 action을 변경하지 않으며, 현재 범죄성도 판정하지 않는다. 전체 CSV는
repository에 복제하지 않고 content metadata와 bounded match만 보존한다.

## 5. 보안·Rules 경계

- endpoint 값과 credential은 repository·fixture·report에 저장하지 않는다.
- 기본 runner는 dry-run이며 `--execute --rules-status allowed`가 있어야 호출한다.
- `eth_call` 고정 allowlist만 사용하고 send/sign/mutation은 없다.
- Blockscout는 명시한 public read-only RPC이며 Explorer 자동 fallback이 아니다.
- `.scan/`의 실행 report는 gitignore 대상이다.

## 6. 잔여 Gate

| Gate | 상태 | 다음 판단 |
|:---|:---:|:---|
| ENS 두 공급자 고정 block replay | pass | 독립 Verifier 입력으로 사용 |
| OFAC current SLS snapshot pin | pass | 역사 action과 분리해 검증 |
| Actor bounded prehistory | pending | 확인 불가를 `false`로 유지 |
| Actor service/faucet/paymaster exclusion | pending | 근거 없이 complete 승격 금지 |
| 독립 Verifier | pending | 준비된 fixture부터 raw-first 재계산 |
| fixture promotion | blocked | Verifier와 문제별 잔여 Gate 이후 별도 판단 |
| 제품 analyzer | blocked | 계약·Context Receipt·구현 승인 이후 |

## 7. 판정

**GO for independent Verifier on LABEL, SANCTIONS, ENS, and RELATION-HUB.**

`FX-ACTOR-COMMON-FUNDER-001`은 네 direct seed output을 검증할 수 있으나
bounded prehistory와 service exclusion이 계속 `false`다. Verifier는 이
부분 상태를 그대로 검증할 수 있지만 complete/confirmed로 승격해서는 안 된다.

## 8. 검증

- repository Gate: **482 tests PASS**
- fixture Schema 0.1: **18 packages PASS**
- Analysis I/O: **48 probes PASS**
- traceability: **1,609 links PASS**
- security scan: **190 runtime/evidence files PASS**
- TASK-015 source replay unit: **8 tests PASS**
- live 실행 report와 endpoint/credential: repository 미포함

## 9. Related Documents

- [TASK-015 Fixture·Contract Gate](./45_TASK_015_FIXTURE_CONTRACT_GATE.md)
- [TASK-015 Negative Oracle 보고서](./49_TASK_015_NEGATIVE_ORACLE_REPORT.md)
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md)
