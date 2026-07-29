# TASK-014 PATH Replay·Negative Oracle 보고서
> Created: 2026-07-30 00:08
> Last Updated: 2026-07-30 00:08
> Status: Passed · Fixture 3 Verifying · Product Runtime Not Implemented

## 1. 범위

TASK-014 세 fixture의 선택 transaction·exact block 범위를 primary와 verify
Ethereum RPC로 읽기 전용 재현하고, raw SHA-256과 decoded 일치를 고정했다.
대회 제출·서명·전송·AI 호출은 없었다.

## 2. Provider Replay

| Provider | 요청 | 결과 |
|:---|---:|:---:|
| `PROVIDER-EVM-PRIMARY` | TX 10 + receipt 10 + callTracer 1 | 21/21 complete |
| `PROVIDER-EVM-VERIFY` | TX 10 + receipt 10 | 20/20 complete |

- 실행 시각: primary `2026-07-29T14:58:27Z`~`14:58:32Z`,
  verify `14:58:43Z`~`14:58:46Z`
- 공통 20 capability의 decoded TX·receipt는 전부 일치했다.
- raw 응답은 content-addressed artifact로 로컬 보존하고 fixture에는
  capability별 SHA-256만 기록했다.
- endpoint·credential·로컬 절대 경로는 저장하지 않았다.

## 3. Internal Edge

primary `debug_traceTransaction(callTracer)`에서 path `[0]`의 성공 call 한 건이
다음과 같이 재현됐다.

- from: `0x036cec1a199234fc02f72d29e596a09440825f1c`
- to: `0xb66cd966670d962c227b3eaba30a872dbfb995db`
- value: `88752697459828535340019` wei

독립 두 번째 trace 공급자는 fixture의 선택 TX·receipt 교차검증과 별개다.
이 fixture는 primary raw trace와 고정 artifact를 scoring 근거로 사용하고,
trace 공급자 독립성은 provenance 품질의 후속 항목으로 남긴다.

## 4. Negative Oracle

`task-014-negative-oracles-v0.1.json`의 18개 반례를 두 번 실행했다.

| Query | 반례 수 | 핵심 경계 |
|:---|---:|:---|
| trace_path | 6 | cycle·endpoint·unrelated·budget·trace·asset |
| trace_remerge | 6 | duplicate·external inflow·branch·residual·cycle·budget |
| aggregate_origins | 6 | duplicate·missing·exit·price·raw integer·origin scope |

결과는 두 실행에서 동일했다. 가격 부재는 raw path 실패가 아니며, budget과
source 일부 누락은 확인 edge를 보존한 `partial`로 분리했다.

## 5. 범위 결정

- scoring: 명시된 selected transaction과 해당 exact block
- 미주장: transaction 사이 continuous gap, 사건 전체 flow, seed의 모든 출력
- residual: `1600000000000000000` wei를 unresolved로 보존
- external dust: seed ledger 밖 context로 보존
- attribution·범죄·피해자·공통 통제: `not_assessed`

## 6. 판정

Replay와 negative oracle Gate는 **Pass**다. fixture는 `verifying`으로 올리되,
제품 analyzer와 최종 promotion 전에는 `confirmed`로 올리지 않는다.

## 7. Related Documents

- **QA_Validation**: [Fixture Gate](./39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 전체 Stop/Go
- **QA_Validation**: [독립 Verifier](./42_TASK_014_INDEPENDENT_VERIFIER_REPORT.md) - raw-first 재계산
- **Technical_Specs**: [PATH 계약](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - graph·ledger 계약
