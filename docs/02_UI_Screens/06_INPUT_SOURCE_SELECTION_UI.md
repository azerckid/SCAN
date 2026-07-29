# 입력 소스 선택 UI (WP-INPUT-GATE)
> Created: 2026-07-29 12:20
> Last Updated: 2026-07-29 12:54
> Status: Approved 0.1 · UI-First Gate Passed · Runtime Wiring Applied

## 1. 문서 목적

이 문서는 `external_rpc | contest_rpc | provided_artifact` 세 입력 모드와
`evm | bitcoin | non_evm | cross_chain` 체인 범위를 사용자가 선택하고, 입력
출처·오류·partial 상태를 확인하는 화면 계약을 정의한다. 구현 전 UI-First
Gate 문서이며, [WP-INPUT-GATE CLI·Operations 연결 계약](../03_Technical_Specs/13_WP_INPUT_CLI_OPERATIONS_CONTRACT.md)의
화면 부분을 담당한다.

Analysis I/O `0.1`과 기존 CLI V1 화면(SCREEN_FLOW 1.5)은 변경하지 않는다.
입력 모드 표시는 provenance 계층이며 result/evidence 봉투를 확장하지 않는다.

## 2. 화면 범위

| 화면 | 목적 | 표시 데이터 |
|:---|:---|:---|
| Input source selector | 모드·체인 범위·입력 소스 선택 | input_mode, chain_scope, endpoint 환경변수 이름, artifact 파일·형식 |
| CLI 진행·결과 | 입력 출처·record·상태 표시 | STARTING/INPUT progress, complete·partial·failed |
| Operations 입력 배지 | 문제별 입력 모드·체인 표시 | input_mode 배지, chain_scope, source health |

세 모드는 화면에서 서로 다른 명령 체계를 만들지 않는다. 같은 `scan analyze`
진입점에서 `--input-mode`로 전환한다.

## 3. 입력 소스 선택 규칙

- 한 번에 한 입력 모드만 활성화하고, 그 모드에 필요한 입력 소스를 정확히
  하나 요구한다.
- `contest_rpc` endpoint는 HTTPS만 허용한다. 사용자는 CLI에 endpoint 값이
  아니라 환경변수 **이름**을 전달하고, 화면·로그에는 환경변수 이름만
  표시한다. 실제 endpoint·query·API key는 표시하지 않는다.
- `provided_artifact`는 파일명과 형식(JSON/JSONL/CSV)만 표시하고 내용을
  자동 해석해 화면에 노출하지 않는다.
- `chain_scope`가 analyzer 모델과 다르면 실행 전에 `chain_scope_mismatch`를
  표시하고 진행을 막는다.

## 4. 상태 표현

### 4.1 입력 출처

- 진행 첫 줄에 `input_mode` · `chain_scope` · `source_id`를 표시한다.
- `INPUT` 줄에 정규화 record 수, `raw_sha256` 앞 12자, media type을 표시한다.
- endpoint 전체·API key·로컬 절대 경로는 어떤 상태에서도 표시하지 않는다.

### 4.2 오류

- 입력 경계 오류(`invalid_artifact`, `artifact_too_large`, `too_many_records`,
  `chain_scope_mismatch`, `unsupported_input`)는 코드·사유만 표시하고 원본
  artifact 내용을 반사하지 않는다. 네트워크 호출 전에 종료(exit 2)한다.
- allowlist 외 RPC method 요청은 네트워크 호출 전에 차단됨을 표시한다.

### 4.3 partial

- 필수 record(trace·prevout·양단 message) 누락은 오류가 아니라 `PARTIAL`이다.
- 확보 record는 complete와 같은 형식으로 먼저 표시하고, 누락 요구·다음 행동을
  분리해 표시한다. partial을 성공처럼 표시하거나 빈 결과로 숨기지 않는다.

## 5. HTML Preview

[입력 소스 선택 Preview](./previews/05_input_source_selection_preview.html)는
세 입력 모드와 네 체인 범위, 입력 출처·오류·partial 상태를 브라우저에서
확인하는 정적 검토 산출물이다. 실제 RPC·API·DB·파일에 연결하지 않는다.

Preview는 다음을 보여준다.

- 세 입력 모드 탭과 모드별 입력 소스 필드(endpoint 환경변수 이름·artifact 파일·형식)
- 네 체인 범위 선택과 analyzer 불일치 시 자동 `FAILED`·`chain_scope_mismatch` 차단
- CLI 진행(STARTING·INPUT)과 complete·partial·failed 상태 조합
- Operations Queue → Evidence Worker 핸드오프 요약과 입력 배지
- endpoint·secret 비노출과 read-only allowlist 안내

## 6. UI-First Gate 수용 기준

- [x] 세 입력 모드와 네 체인 범위 선택 화면이 정의됨
- [x] 입력 출처(모드·체인·source·record·hash) 표시가 정의됨
- [x] 입력 경계 오류와 종료 코드 매핑이 정의됨
- [x] partial 상태와 확보 증거 보존 표현이 정의됨
- [x] endpoint·API key 비노출과 read-only allowlist 표시가 정의됨
- [x] Operations 입력 배지와 Queue→Worker 핸드오프가 표현됨
- [x] HTML Preview가 문서에 연결됨
- [x] 사용자가 HTML Preview를 확인함
- [x] 사용자 피드백과 보완 결과가 계약·Preview에 기록됨

사용자 승인 뒤 `WP-INPUT-IMPL-02`에서 CLI·Operations wiring을 구현했다.
정적 Preview는 실제 RPC·파일을 호출하지 않는 검토 산출물로 계속 유지한다.

## 7. Related Documents

- **Technical_Specs**: [WP-INPUT-GATE CLI·Operations 연결 계약](../03_Technical_Specs/13_WP_INPUT_CLI_OPERATIONS_CONTRACT.md) - 명령·핸드오프·보안·QA 계약
- **Technical_Specs**: [다중 입력 모드와 체인 범위](../03_Technical_Specs/12_MULTI_SOURCE_INPUT_AND_CHAIN_SCOPE.md) - 입력 모드·체인 상위 설계
- **UI_Screens**: [CLI Screen Flow](./00_SCREEN_FLOW.md) - 공통 명령·상태·종료 코드
- **UI_Screens**: [Competition Operations Board](./04_COMPETITION_OPERATIONS_BOARD.md) - 병렬 운영 화면
- **UI_Screens**: [입력 소스 선택 Preview](./previews/05_input_source_selection_preview.html) - 브라우저 확인용 화면
- **Logic_Progress**: [Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 0 CLI·Operations 선행 순서
- **QA_Validation**: [WP-INPUT-GATE Core 보고서](../05_QA_Validation/30_WP_INPUT_GATE_CORE_REPORT.md) - core library 구현·테스트 경계
