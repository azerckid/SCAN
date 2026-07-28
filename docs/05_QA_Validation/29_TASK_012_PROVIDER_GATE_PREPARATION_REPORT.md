# TASK-012 Provider Gate 준비 보고서
> Created: 2026-07-29 06:14
> Last Updated: 2026-07-29 06:14
> Status: Offline Preparation Passed · Live Gate Not Executed

## 1. 목적

이 보고서는 노출 credential을 재사용하지 않고 TASK-012 독립 Trace와 provider
실패 동작을 검증할 수 있도록 준비한 범위를 기록한다. fixture `confirmed`,
정식 Analysis I/O, 제품 analyzer 구현 성과가 아니다.

## 2. Credential Gate

- `.env.local` 수정 시각은 최초 노출 당시인 2026-07-29 03:28 KST다.
- 회전 완료를 증명할 새 구성 기록은 없다.
- 기존 endpoint 값은 출력·문서·fixture·artifact에 기록하지 않았다.
- 회전 전에는 `--execute`를 실행하지 않는다.

따라서 이 변경의 실제 네트워크 호출은 **0건**이다.

## 3. 독립 Trace dialect

| dialect | RPC | 입력 | 정규화 결과 | 실제 실행 |
|:---|:---|:---|:---|:---:|
| `debug_call_tracer` | `debug_traceTransaction` | TX + `callTracer` + `onlyTopCall: false` | 성공한 내부 native inflow | Not Executed |
| `parity_trace_transaction` | `trace_transaction` | TX | 성공한 내부 native inflow | Not Executed |

두 응답은 `matching_successful_inflows`의 `path·type·from·to·value_hex·value_wei`
형태로 정규화한다. call type은 소문자로 통일하며, 동일 synthetic inflow에서
두 dialect의 전체 정규화 필드가 일치하는지 직접 검증한다. 실패 call과 zero
value는 답에 포함하지 않는다.

공식 문서 기준:

- [QuickNode debug_traceTransaction](https://www.quicknode.com/docs/ethereum/debug_traceTransaction)
- [Alchemy debug_traceTransaction](https://www.alchemy.com/docs/chains/debug-api/debug-api-endpoints/debug-trace-transaction)
- [Alchemy trace_transaction](https://www.alchemy.com/docs/reference/what-is-trace_transaction)

Alchemy `trace_transaction`은 공식 문서상 Pay-as-you-go 또는 Enterprise tier가
필요하다. 문서 존재를 현재 계정의 capability 성공으로 간주하지 않는다.

## 4. 오프라인 failure Gate

주입 가능한 `httpx.MockTransport`로 다음을 검증했다.

| 동작 | 기대 failure_kind | 결과 |
|:---|:---|:---:|
| timeout | `timeout` | Pass |
| HTTP 429 | `rate_limited` | Pass |
| JSON-RPC method not found | `invalid_response` | Pass |
| malformed JSON | `invalid_response` | Pass |

각 경우 network attempt는 1개로 제한되고 status는 `failed`, raw artifact는
생성되지 않으며 endpoint secret canary는 보고서에 남지 않는다. 이는 실제
provider의 live rate limit·timeout 측정을 대신하지 않는다.

## 5. 실행 경계

기본 dry-run:

```bash
uv run python scripts/replay_task_012_trace.py \
  --dialect debug_call_tracer
```

회전·Rules·plan 확인 뒤에만 허용할 형태:

```bash
uv run python scripts/replay_task_012_trace.py \
  --dialect debug_call_tracer \
  --execute \
  --rules-status allowed
```

실행 전 조건:

1. primary·verify·trace credential 회전
2. 새 secret이 로컬 환경에만 있는지 확인
3. 공식 Rules 또는 operator 실행 근거 기록
4. 현재 account plan에서 선택 dialect 지원 확인
5. timeout·호출 수 상한 확인

## 6. 잔여 Gate

- [ ] credential 회전 확인
- [ ] 새 독립 endpoint의 `eth_chainId`
- [ ] 선택 dialect 실제 Trace 성공
- [ ] primary와 독립 trace의 inflow raw 값 일치
- [ ] live timeout·rate-limit·method-not-found(`invalid_response`) 결과 기록
- [ ] TOKEN-002 fixture의 conditional confirmed 판단
- [ ] Context Receipt와 제품 analyzer 구현 승인

## 7. 검증

- trace dialect·정규화·교차 동등성·shape·failure unit: 11 cases
- provider smoke·candidate replay 관련 unit: 21 cases
- 두 dialect dry-run: `not_executed`, `network_calls: 0`
- repository full Gate: `scripts/verify.py`

## 8. Related Documents

- **Technical_Specs**: [Live Provider Readiness](../03_Technical_Specs/10_LIVE_PROVIDER_READINESS.md) - credential·provider Gate
- **Technical_Specs**: [TASK-012 Analysis Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - trace completeness 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-012 Context Lock
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 1 순서
- **QA_Validation**: [Live Provider Capability QA](./25_LIVE_PROVIDER_CAPABILITY_QA.md) - 실제 smoke 기준선
- **QA_Validation**: [Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - verifying 4개와 승격 Gate
