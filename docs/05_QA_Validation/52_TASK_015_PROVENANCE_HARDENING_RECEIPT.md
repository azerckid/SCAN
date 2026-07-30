# TASK-015 Provenance Hardening Receipt
> Created: 2026-07-30 05:05
> Last Updated: 2026-07-30 05:05
> Status: PR #82 P2 Closed · 4 Fixtures Remain Verifying

## 1. 지적

기존 LABEL Verifier는 community config의 `commit`과 `config_sha256`을
evidence에서 읽고 expected projection도 같은 evidence에서 읽었다. 등식 양변이
동일 source여서 해당 두 필드의 독립 검증 효과가 없었다. ENS snapshot도
content-addressed filename을 bytes에서 재검증하지 않았다.

## 2. 보완

- `tornadocash-community/torn-token` commit
  `4dea68f71633dab37e3cb4c8b4d8dca3479891c6`의 `config.js` 원문을 저장했다.
- raw bytes SHA-256
  `84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32`와
  content-addressed filename을 대조한다.
- raw `team4` block에서 ENS name·cliff·duration을 다시 파싱한다.
- fixture input의 pinned commit과 evidence commit을 교차검증한다.
- ENS snapshot `762291...json`도 filename과 bytes SHA-256을 대조한다.
- config drift와 ENS snapshot drift negative test를 추가했다.

## 3. 결과

LABEL calculated facts에서 evidence 유래 `commit/config_sha256` 자체를 제거하고,
raw에서 재유도한 material name/role만 expected와 대조한다. 이에 따라 LABEL
canonical fact hash는 다음으로 갱신됐다.

`4ae17221fe5e0642c588723bd89db1ee6f9e39d19f2d6c1dce85dd2e2990d399`

다른 세 fixture hash는 변하지 않았다. 네 fixture는 계속 `verifying`,
common-funder는 `candidate`, Benchmark는 11이다.

## 4. Related Documents

- [Independent Verifier 보고서](./51_TASK_015_INDEPENDENT_VERIFIER_REPORT.md)
- [LABEL fixture](./fixtures/FX-OSINT-LABEL-CONFLICT-001/README.md)
- [Source Readiness 보고서](./50_TASK_015_SOURCE_READINESS_REPORT.md)
