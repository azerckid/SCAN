# TASK-013 독립 Verifier 검증 보고서
> Created: 2026-07-29 15:38
> Last Updated: 2026-07-29 15:49
> Status: Passed · 3 Candidates · 13 Evidence Values · 7 Requirements · Fixture Promotion Pending

## 1. 목적과 판정

TASK-013의 ERC-721, ERC-1155, EIP-1967 candidate가 가진 raw replay를
expected와 분리된 계산 경로로 다시 해석한다. Verifier는 raw 계산을 먼저
끝낸 뒤 expected projection, evidence의 13개 scoring 값,
requirement→evidence 연결을 대조한다.

**판정: 세 candidate의 필수 사실·13개 evidence 값·7개 requirement가 두
번의 독립 실행에서 모두 일치했다. fixture는 승격 판단 전까지 계속
`candidate`다.**

## 2. 독립성 경계

- `task_013_replay.py`와 `check_task_013_replay_gate.py`를 import하지 않는다.
- expected는 `recalculate_raw_facts()`의 입력으로 받을 수 없다.
- ERC-1155 Batch는 기존 수동 word helper 대신 설치된 `eth-abi` decoder로
  별도 계산한다.
- raw facts 계산 완료 후에만 expected와 exact 비교한다.
- evidence의 event·state scoring 값은 raw에서 다시 만든 projection과
  evidence ID별로 exact 비교한다.
- Negative Oracle·Verifier 보고서 경로와 계산 fact SHA-256을 fixture
  evidence provenance에서 exact 비교한다.
- expected drift와 raw topic/data/state drift를 각각 주입해 실패를 확인한다.
- evidence value drift와 verification provenance 누락도 주입해 실패를
  확인한다.
- 네트워크·endpoint·credential·제품 analyzer·UI를 사용하지 않는다.

독립성은 다른 공급자를 새로 호출했다는 뜻이 아니다. 기존 두 공급자의
고정 raw replay를 별도 코드 경로로 재계산했다는 뜻이다.

## 3. 검증 결과

| Fixture | 필수 계산 | Evidence 값 | Requirement | Fact SHA-256 | 결과 |
|:---|:---|---:|---:|:---|:---:|
| `FX-EVM-NFT-721-001` | Transfer, ApprovalForAll, Approval reset, token `9110` | 3 | 2 | `a2b879fb7aa9f157168b349875decff86d3a1d685792332c9eff1af8ca0e5e74` | pass |
| `FX-EVM-NFT-1155-001` | Single, Batch arrays, approval true→false | 5 | 2 | `0caf8a09994abbff71cb4afddf9bb6e11fa5411ef0870c27d1a92ea324aade91` | pass |
| `FX-EVM-PROXY-001` | upgrade event, adjacent implementation, admin zero | 5 | 3 | `f0683ef2167e2e7799891a66e0b065300842fd46de5d63b84ebe440ee2f58d93` | pass |
| **합계** | raw-first exact 계산 | **13** | **7** | 두 번 동일 | **pass** |

추가 strict 조건:

- NFT exact block windows와 성공 receipt block이 일치한다.
- selected NFT log는 단일 contract이며 성공 receipt에 연결된다.
- ERC-1155 두 approval의 owner/operator가 같다.
- Proxy receipt·Upgraded event·after state는 같은 block이고 before state는
  정확히 직전 block이다.
- implementation/admin slot 역할과 event/after-state 구현체가 일치한다.

## 4. 산출물

- `src/scan_tool/application/task_013_independent_verifier.py`
  - raw-only 재계산, expected 대조, requirement evidence 검증
- `scripts/verify_task_013_independent_verifier.py`
  - 세 fixture를 두 번 실행하고 결정성·fact hash 출력
- `tests/unit/test_task_013_independent_verifier.py`
  - expected drift, raw topic, truncated ABI, event/state 충돌, evidence
    값 drift, provenance 누락
- `scripts/verify.py`
  - repository-wide offline Gate에 Verifier 연결

## 5. 상태 경계와 다음 Gate

- Fixture: `candidate` 유지
- Analysis I/O: `0.2` 유지
- Benchmark 자동화: 7문항 유지
- 제품 NFT·Proxy decoder: 미구현
- 전용 UI Preview: 미승인

다음 작업은 replay·negative oracle·Verifier 결과를 근거로 세 package의
조건부 fixture 승격 여부를 별도 검토하는 것이다. 승격 후에도 Analysis I/O
대안·UI·Context Receipt·사용자 구현 승인이 있어야 제품 decoder를 시작한다.

## 6. 365 글로벌 평가 기준

| 기준 | 판정 |
|:---|:---|
| Functionality | 세 candidate·13 evidence values·7 requirements의 raw-first exact 재계산 통과 |
| Potential Impact | expected 복사나 단일 decoder 오류로 인한 조용한 오답 차단 |
| Novelty | provider replay와 다른 ABI·정합 경로로 증거를 독립 재계산 |
| UX | N/A — UI 변경 없음 |
| Open-source | 기존 `eth-abi`와 공개 EIP만 사용, 새 dependency 없음 |
| Business Plan | N/A — 대회 준비 fixture Gate |

공개 온체인 raw replay만 사용했으며 제3자 코드를 복제하지 않았다. 주소
소유자, NFT 가치, 거래 의도, upgrade의 악성 여부는 `not_assessed`다.

## 7. Related Documents

- **Technical_Specs**: [TASK-013 분석 계약](../03_Technical_Specs/14_TASK_013_NFT_PROXY_CONTRACT_PROPOSAL.md) - 승격·구현 경계
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - TASK-013 Context Lock
- **QA_Validation**: [TASK-013 Fixture 보고서](./32_TASK_013_FIXTURE_CANDIDATE_REPORT.md) - replay·oracle Gate
- **QA_Validation**: [TASK-013 Negative Oracle](./33_TASK_013_NEGATIVE_ORACLE_REPORT.md) - 16개 반례
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - candidate 상태
