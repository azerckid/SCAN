# TASK-012 EVM Core UI Preview 보고서
> Created: 2026-07-29 05:08
> Last Updated: 2026-07-29 05:58
> Status: UI Gate Passed · Runtime Not Implemented

## 1. 범위

이 보고서는 `evm_core` `0.2-draft`의 UI-First Gate만 검증한다. 제품 analyzer,
Analysis I/O 정식 `0.2`, live provider, fixture `confirmed`는 범위 밖이다.

검토 대상:

- [EVM Core UI 문서](../02_UI_Screens/05_TASK_012_EVM_CORE_UI.md)
- [EVM Core HTML Preview](../02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html)
- [TASK-012 Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md)
- [Contract Examples](./examples/task-012/README.md)

## 2. 자동 검증

| 항목 | 기대 | 현재 |
|:---|:---|:---:|
| query tabs | 4개 고유 | Pass |
| result states | complete·partial·failed | Pass |
| contract combinations | 12개 | Pass |
| failed null/error | 화면·JSON에 존재 | Pass |
| raw reference values | fee·balance·transfer·inflow | Pass |
| external request | fetch/XHR/WebSocket 0 | Pass |
| duplicate HTML ID | 0 | Pass |
| runtime/source tree | 변경 없음 | Pass |

실행 예정:

```bash
uv run python scripts/check_task_012_ui_preview.py
```

## 3. 브라우저 검증

- [x] Preview가 로컬 브라우저에서 열린다.
- [x] query tab 4개를 클릭해 입력·결과가 전환된다.
- [x] complete·partial·failed를 클릭해 status·data·error가 전환된다.
- [x] 방향키로 query와 state를 이동할 수 있다.
- [x] failed에서 `data: null`과 오류가 보인다.
- [x] mobile 390px 폭에서 가로 스크롤 없이 핵심 정보가 보인다.
- [x] console error가 없다.
- [x] 외부 asset·네트워크 호출 코드가 없다.

브라우저 검증 결과:

- 4 query × 3상태 = 12개 조합 통과
- complete: non-null data·errors 0
- partial: non-null data·errors 1 이상
- failed: null data·errors 1 이상
- query `ArrowRight` wrap과 state `ArrowLeft` 이동 통과
- 390×844 viewport에서 document overflow X 없음
- console warning/error 0, 외부 script/link/image 0

## 4. 사용자 확인

- 확인자: 사용자
- 확인 일시: 2026-07-29 05:58 KST
- 확인 URL:
  `http://127.0.0.1:8766/docs/02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html`
- Gate 상태: Passed

확인 질문:

- [x] 네 query의 차이가 첫 화면에서 이해되는가
- [x] 필수 입력과 고정 block·trace·range 조건이 충분히 보이는가
- [x] partial이 complete로 오해되지 않는가
- [x] failed가 빈 결과가 아니라 구조화 실패로 이해되는가
- [x] raw 값과 evidence/source, 다음 행동의 우선순위가 적절한가
- [x] 정보량이 과하거나 부족하지 않은가

반영 피드백:

| ID | 우선순위 | 피드백 | 반영 |
|:---|:---:|:---|:---|
| UI-FB-012-001 | P2 | fixture `verifying`과 `CONFIRMED RESULT` 혼동 가능 | `COMPLETE RESULT`로 변경 |
| UI-FB-012-002 | P2 | Preview JS와 계약 예제의 값 drift 가능 | checker가 12개 case ID·matrix·raw·오류를 제안 JSON과 직접 대조 |

## 5. 365 글로벌 평가 기준

| 기준 | 판정 | 증거 |
|:---|:---:|:---|
| Functionality | Pass | 브라우저 4 query × 3 상태 전환 |
| Potential Impact | Planned | 범용 EVM 4문항 공통 입력 UX |
| Novelty | Draft | raw proof·completeness·failed null 분리 |
| UX | Pass | 브라우저·모바일·키보드와 사용자 검토 통과 |
| Open-source | Pass | 단일 HTML·외부 dependency 없음 |
| Business Plan | N/A | 대회 준비 QA 범위 |

## 6. Originality·Ethics

- [x] 기존 SCAN CLI 시각 언어를 재사용하고 외부 UI를 복제하지 않는다.
- [x] 주소 소유자·범죄 의도·현재 제재를 추론하지 않는다.
- [x] credential·endpoint·private key 입력을 만들지 않는다.
- [x] Preview data를 실제 analyzer 실행 성과로 표시하지 않는다.

## 7. Related Documents

- **UI_Screens**: [EVM Core UI](../02_UI_Screens/05_TASK_012_EVM_CORE_UI.md) - 입력·상태·동선 명세
- **UI_Screens**: [EVM Core Preview](../02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html) - 브라우저 검토 화면
- **Technical_Specs**: [TASK-012 Contract Proposal](../03_Technical_Specs/11_TASK_012_ANALYSIS_CONTRACT_PROPOSAL.md) - 표시 계약
- **Logic_Progress**: [Backlog](../04_Logic_Progress/00_BACKLOG.md) - UI-First 구현 잠금
- **QA_Validation**: [Contract Examples](./examples/task-012/README.md) - 12개 기준 사례
- **QA_Validation**: [Fixture 후보 보고서](./24_TASK_012_FIXTURE_CANDIDATE_REPORT.md) - Gate 7
