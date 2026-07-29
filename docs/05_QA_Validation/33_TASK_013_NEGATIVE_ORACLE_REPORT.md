# TASK-013 Negative Oracle 검증 보고서
> Created: 2026-07-29 15:17
> Last Updated: 2026-07-29 15:17
> Status: Offline 15 Passed Twice · Fixture Candidate · Verifier Pending

## 1. 목적과 판정

TASK-013 제품 decoder를 구현하기 전에 ERC-721, ERC-1155, EIP-1967의
오분류·누락·충돌 경계를 합성 반례로 고정한다. 이 작업은 live RPC,
Analysis I/O 변경, 제품 analyzer, UI 또는 fixture 승격을 포함하지 않는다.

**판정: 표준별 5개, 총 15개 oracle을 동일 입력으로 두 번 실행해 모두
같은 결과를 얻었다. 세 fixture는 계속 `candidate`다.**

## 2. 실행 범위

| Fixture | Oracle 수 | 검증 범위 | 결과 |
|:---|---:|:---|:---:|
| `FX-EVM-NFT-721-001` | 5 | ERC-20 혼동, 다른 contract, range 누락, tokenId 위치, topic 수 | pass |
| `FX-EVM-NFT-1155-001` | 5 | Batch 길이, ABI truncation, 다른 contract, page·approval 누락 | pass |
| `FX-EVM-PROXY-001` | 5 | latest 오용, admin 혼동, event/state 충돌, state 누락, 비표준 pattern | pass |
| **합계** | **15** | synthetic offline · deterministic 2회 | **pass** |

`complete`는 무관 contract를 정확히 제외한 경우에도 사용한다. `partial`은
확인된 표준 사실은 있으나 지정 범위의 page·approval·historical state가
빠진 경우다. malformed ABI, 잘못된 slot/block, event/state 충돌과
비표준 proxy의 EIP-1967 단정은 `failed`다.

## 3. 산출물

- `fixtures/TASK-013-NEGATIVE-ORACLES.json`
  - 고정된 15개 고유 oracle ID와 expected outcome
- `src/scan_tool/application/task_013_negative_oracles.py`
  - 외부 I/O 없는 strict manifest와 순수 판정기
- `scripts/verify_task_013_negative_oracles.py`
  - 두 번 실행한 결과·순서·expected 일치 검사
- `tests/unit/test_task_013_negative_oracles.py`
  - 필수 ID 집합, 대표 partial/failed/excluded, expected drift 회귀
- `scripts/verify.py`
  - repository-wide offline Gate에 TASK-013 oracle 포함

Proxy fixture 입력은 NFT fixture와 같은 `transactions + block_windows`
scope 골격으로 정규화했다. 의미는 선정 upgrade TX와 adjacent before/after
state로 제한되며 wider history 완전성을 주장하지 않는다.

## 4. 경계

- 네트워크 호출: `0`
- endpoint·credential 사용: 없음
- fixture 상태: 세 package 모두 `candidate`
- Analysis I/O 0.2·Operations Schema·제품 analyzer: 변경 없음
- Benchmark 자동화: 7문항 유지
- 범죄·악성 upgrade·법적 소유권: `not_assessed`

oracle은 synthetic 반례의 결정적 상태 분류만 입증한다. provider replay와
독립 Verifier를 대체하지 않으며 expected 값을 제품 analyzer 입력으로
사용하지 않는다.

## 5. 다음 Gate

1. 독립 Verifier가 raw replay에서 필수 값을 다시 계산한다.
2. provider replay·oracle·Verifier 참조를 fixture evidence에 연결한다.
3. 조건을 모두 만족한 package만 fixture 승격 대상으로 검토한다.
4. Analysis I/O 대안과 전용 UI Preview를 승인한다.
5. Context Receipt와 사용자 구현 승인 뒤 제품 decoder를 시작한다.

## 6. 365 글로벌 평가 기준

| 기준 | 판정 |
|:---|:---|
| Functionality | 15개 표준·범위·slot 반례가 두 번 동일하게 통과 |
| Potential Impact | NFT·Proxy 문제에서 조용한 오답과 과대 완전성 주장을 차단 |
| Novelty | AI 설명이 아니라 표준별 raw 구조·historical state 규칙으로 실증 |
| UX | complete·partial·failed와 제외·충돌 이유를 구조화 |
| Open-source | secret·live 의존 없는 재현 가능한 manifest와 판정기 |
| Business Plan | N/A — 대회 준비용 fixture Gate |

공식 EIP의 event·slot 구조만 구현 규칙으로 사용했으며 제3자 코드를
복제하지 않았다. 주소 주체·거래 의도·upgrade의 악성 여부는 판정하지
않는다.

## 7. Related Documents

- **Technical_Specs**: [TASK-013 분석 계약](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - 표준·상태·오류 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-013 잠금
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - candidate 상태
- **QA_Validation**: [TASK-013 Fixture 보고서](./32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - replay·승격 Gate
