# TASK-015 FX-OSINT-LABEL-CONFLICT-001 확정 승격 Receipt

> Created: 2026-07-30
> Last Updated: 2026-07-30
> Status: Passed · LABEL fixture `verifying → confirmed` · OpenRAIL artifact 삭제 · Benchmark 판정은 별도

## 1. 목적과 판정

`FX-OSINT-LABEL-CONFLICT-001`의 `확정(confirmed)` 승격 심사를 기록한다.
심사 기준은 라이선스·아티팩트 해시·2-provider ENS 재현·negative oracle·
독립 Verifier·analyzer hash의 최종 대조와, 재배포 허가 미확인 OpenRAIL
아티팩트의 처리다.

**판정: 여섯 기준이 모두 통과했고, 유일한 블로커였던 재배포 허가 미확인
OpenRAIL CSV 아티팩트를 삭제(참조 0건)했으므로 fixture를 `확정`으로
승격한다. OSINT-LBL-001의 Benchmark 자동화(11→12) 승격은 이 문서의 범위가
아니며 별도로 판정한다.**

## 2. 심사 기준 대조

| 기준 | 결과 | 근거 |
|:---|:---:|:---|
| 채점 소스 라이선스 | pass | 채점 3소스만 사용: `DS-SANCTIONS-PUBLIC`(OFAC 공개 공식기록 `2ddb426a`, confirmed SANCTIONS fixture 연계) · `DS-OSINT-WEB`(MIT tornado config `84efb043`, evidence `license: MIT`) · `DS-ENS`(온체인 ENS `c5da8824`). 재배포 제약 있는 소스 없음 |
| 아티팩트 해시 | pass | 채점 3개 artifact 모두 content-addressed 자가검증, source-replay `content_sha256`와 `artifact://sha256/<h>` 일치 |
| 2-provider ENS 재현 | pass | `PROVIDER-EVM-VERIFY` + `BLOCKSCOUT-ETH-RPC` decoded 일치(`decoded_match: true`), `PROVIDER-EVM-PRIMARY`(-32003)·`PROVIDER-EVM-TRACE`(403) 실패는 성공 추론 없이 보존 |
| negative oracle | pass | TASK-015 30개 ×2 결정성 |
| 독립 Verifier | pass | LABEL fact hash `972a154d20846478774f9fb7b685f7db1d7c5c8eac37fa1c5cd2cb444514d1a9`, 4 fixture 2회 결정성 |
| analyzer hash | pass | 제품 analyzer `results[0].value` canonical hash가 위 pinned hash와 일치(별도 코드 경로) |

## 3. OpenRAIL 아티팩트 처리

- OpenRAIL 데이터셋(Humanbased-AI/Crypto-Address-Annotation-10K)의 선택 row
  아티팩트(`15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475.csv`)는
  [license-resolution.json](./fixtures/FX-OSINT-LABEL-CONFLICT-001/license-resolution.json)에서
  LICENSE 파일 404·재배포 허가 미확인·`promotion_allowed: false`로 판정됐다.
- migration(PR #91)이 이미 채점·provenance 의존성을 관 소스 3종으로 옮겨
  이 아티팩트는 어떤 채점 경로에서도 참조되지 않는다(source-replay·evidence·
  독립 Verifier·request `source_artifact_refs` 모두 미참조; 테스트는 URI 부재를
  단언만 함).
- 재배포 허가가 확인되지 않은 파일을 confirmed(공개 배포) fixture에 남기는
  것은 license 리스크이므로 **파일을 삭제**했다. SHA-256과 삭제 사유는
  `license-resolution.json`(`historical_artifact_deleted: true`,
  `artifact_deletion`)과 [55 Resolution Receipt](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md)에
  이력으로 보존한다. MIT config `84efb043`은 현재 채점 소스이므로 유지한다.

## 4. 승격 반영

- `input/expected/evidence/provider-replay/source-replay.json`의 fixture
  `status`를 `verifying → confirmed`로 전환.
- fixture README status·잔여 Gate·Superseded Historical Artifacts 목록 갱신.
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md) 레지스트리 LABEL 행 갱신.
- 채점 소스·독립 Verifier·analyzer hash는 불변이므로 pinned
  `calculated_fact_sha256`(`972a154d…`)은 재계산하지 않는다.

## 5. 상태 경계와 다음 Gate

- LABEL: `확정`. SANCTIONS·ENS·RELATION-HUB는 계속 `검증 중`, common-funder는
  `candidate`.
- Benchmark: 11 automated / 4 assisted / 15 unsupported 유지. **OSINT-LBL-001의
  automated 11→12 승격은 별도 판정**(executable benchmark case 등록 필요).
- 전체 게이트: 542 tests PASS, fixture 18, schema 52 probes, TASK-015 negative
  oracle 30×2·독립 Verifier 4×2·analyzer 독립 검증 4 fixtures PASS,
  OpenRAIL CSV 참조 0건.

## 6. Related Documents

- **QA_Validation**: [OpenRAIL License Resolution Receipt](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md) · [Source Replacement Review](./57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md) · [Analyzer 검증 Receipt](./53_TASK_015_ANALYZER_VERIFICATION_RECEIPT.md)
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) · [FX-OSINT-LABEL-CONFLICT-001](./fixtures/FX-OSINT-LABEL-CONFLICT-001/README.md)
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md)
