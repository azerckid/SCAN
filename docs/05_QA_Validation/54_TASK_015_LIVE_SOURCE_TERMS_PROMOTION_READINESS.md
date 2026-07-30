# TASK-015 Live Source·Terms·Fixture 승격 Readiness
> Created: 2026-07-30 14:19
> Last Updated: 2026-07-30 15:48
> Status: Applied · 3 Non-Quarantined Confirmed · LABEL Blocked · Common-funder Candidate

## 1. 목적과 현재 판정

이 문서는 `intel_context` analyzer 구현 이후 source 사용 조건과 fixture
승격 조건을 분리해 고정한 readiness 기준선이다. 비격리 세 fixture의 최종
판정은 [승격 Receipt](./56_TASK_015_NON_QUARANTINED_PROMOTION_RECEIPT.md)에
적용했다.

**현재 판정:**

- SANCTIONS·ENS·RELATION-HUB는 analyzer·negative oracle·독립 Verifier와
  fixture별 문서 Gate를 통과해 bounded scope에서 `confirmed`다.
- ENS 관련 fixture는 고정 block artifact로 재현할 수 있다. 새 live RPC 호출은
  승격의 필수 조건이 아니며, 실행할 때만 `RULE-API-001`과 provider Terms를
  다시 확인한다.
- OFAC fixture는 공식 action locator·whole-file hash·bounded match를 유지한다.
  현재 SLS 전체 CSV는 repository에 재배포하지 않는다.
- label fixture의 pinned repository에는 `LICENSE*` 파일이 없고 README가
  OpenRAIL family 식별자만 제공한다. exact license text·version·notice·
  재배포 의무를 특정할 수 없어 selected row를 quarantine하고 최종 승격을
  보류한다([Resolution Receipt](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md)).
- common-funder는 bounded prehistory와 service exclusion이 없으므로
  `candidate`·`partial`만 허용한다.

## 2. Source permission과 사실 정확성의 분리

| Gate | 질문 | 현재 증거 | 실패 시 처리 |
|:---|:---|:---|:---|
| Source permission | 이 원문·선택 행·파생 fact를 저장·재배포·대회 중 사용할 수 있는가 | license/Terms URL, pin, 조회 시각 | source 제외 또는 locator/hash-only |
| Retrieval permission | live API/RPC 호출이 공식 Rules와 provider 조건에 허용되는가 | `RULE-API-001`, provider terms, operator opt-in | `rules_gated`·stored artifact 사용 |
| Artifact integrity | 선택 artifact가 content-addressed이며 변조되지 않았는가 | SHA-256·byte length·독립 재계산 | `decode_failed` / 승격 금지 |
| Fact correctness | analyzer와 독립 Verifier가 같은 raw-first fact를 계산하는가 | canonical hash·2회 결정성 | `reconciliation_failed` / 승격 금지 |
| Claim boundary | source assertion을 소유·범죄·공모 사실로 과장하지 않는가 | `not_assessed`, `auto_merge:false` | `evidence_incomplete` / 승격 금지 |

Source permission을 통과했다고 fact가 정확해지는 것은 아니며, fact가 정확해도
재배포 권한이 자동으로 생기지 않는다.

## 3. Source별 Terms·사용 경계

2026-07-30 기준 공식·first-party 페이지를 재확인했다. 이는 법률 자문이
아니며, 대회 Rules 또는 원문 Terms가 바뀌면 다시 검토한다.

| Source | 공식 근거 | 확인 사실 | SCAN 결정 |
|:---|:---|:---|:---|
| Codatta 10K sample | [Pinned card](https://huggingface.co/datasets/Humanbased-AI/Crypto-Address-Annotation-10K/blob/865b4b7ca276ffa50255f5fa751227b3c666dbf1/README.md) | `openrail` metadata와 OpenRAIL family만 표시; `LICENSE*` 파일·version·notice 없음 | selected row quarantine. publisher exact terms 확보 또는 명확한 license source 교체 전 `확정`·export 금지 |
| Tornado community config | [torn-token repository](https://github.com/tornadocash-community/torn-token) | repository와 README가 MIT를 표시 | pinned commit·config hash·MIT notice를 provenance로 보존. label은 source assertion이며 범죄 사실이 아님 |
| OFAC action·SLS | [Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service) · [2022 action](https://ofac.treasury.gov/recent-actions/20220808) · [2025 removal](https://ofac.treasury.gov/recent-actions/20250321) | SLS는 최신 sanctions data의 다운로드와 archive를 제공 | action URL·hash·bounded address match를 scoring/context로 사용. 현재 full SLS CSV는 locator/hash/metadata-only, repository 재배포 안 함 |
| ENS Protocol | [Reverse resolution](https://docs.ens.domains/web/reverse/) · [ENS Terms](https://ens.domains/legal/terms-of-use) · [ensjs MIT](https://github.com/ensdomains/ensjs) | Interface IP와 공개 Ethereum Protocol을 구분하며 ensjs는 MIT | 웹 Interface 내용을 복제하지 않음. 고정 block onchain raw와 content-addressed artifact만 scoring에 사용 |
| Blockscout | [API documentation](https://docs.blockscout.com/devs/apis) | API·RPC 경로와 별도 PRO key 체계를 제공 | 자동 fallback 금지. stored fixed-block artifact는 재현 근거, 새 호출은 Rules·명시 endpoint·read-only Gate 필요 |
| confirmed local fixture | DEX·AUTH·FLOW package | 이미 pin된 raw/expected hash와 승격 Receipt | relation-hub/common-funder의 입력 provenance로 재사용. 새 소유·공모 사실을 만들지 않음 |

## 4. Fixture별 승격 준비도

| Fixture | 현재 | 허용 승격 입력 | 닫힌 Gate | 남은 Hard Gate | 판정 |
|:---|:---:|:---|:---|:---|:---|
| `FX-OSINT-LABEL-CONFLICT-001` | verifying | quarantine된 기존 artifact; 선택된 replacement는 migration 전 | source 후보 비교·replacement route 선정·기존 30 oracle·Verifier·analyzer·license absence proof | 새 subject의 fixed-block ENS·artifact·oracle·Verifier·analyzer hash 재검증과 OpenRAIL scoring dependency 제거 | MIGRATION PENDING |
| `FX-OSINT-SANCTIONS-HISTORY-001` | confirmed | `provided_artifact`; Rules 허용 시 official locator 재확인 | action timeline·subject-bound SLS context·Verifier·analyzer·미재배포 | 없음(현재 상태·범죄성은 `not_assessed`) | PROMOTED |
| `FX-OSINT-ENS-CONFLICT-001` | confirmed | `provided_artifact`; live는 optional | fixed-block 두 source decoded match·Verifier·analyzer·소유권 분리 | 없음(고정 block 밖은 미확정) | PROMOTED |
| `FX-ACTOR-RELATION-HUB-001` | confirmed | confirmed local fixture | DEX/AUTH hash·hub exclusion·Verifier·analyzer·귀속 분리 | 없음(ownership/coordination `not_assessed`) | PROMOTED |
| `FX-ACTOR-COMMON-FUNDER-001` | candidate | confirmed FLOW + 후속 bounded evidence | oracle·partial analyzer | bounded prehistory·initial inflow completeness·faucet/paymaster/service exclusion·Verifier | BLOCKED |

SANCTIONS·ENS·RELATION-HUB는 별도
[Promotion Receipt](./56_TASK_015_NON_QUARANTINED_PROMOTION_RECEIPT.md)에서
fixture JSON·문서·Benchmark를 함께 동기화해 `confirmed` 승격을 완료했다.
향후 `READY` 판정이 추가되더라도 별도 Promotion Receipt 적용 전에는
`confirmed`로 간주하지 않는다.

## 5. Live source 실행 Gate

새 live 호출은 fixture 승격의 자동 선행 조건이 아니다. 필요할 때만 아래를
모두 만족해야 한다.

- [ ] 공식 대회 Rules에서 해당 API/RPC·외부 전송 mode가 `allowed`다.
- [ ] provider/source Terms와 개인정보 최소 수집 범위를 다시 확인한다.
- [ ] 노출 이력이 있는 credential은 회전하고 local environment에만 둔다.
- [ ] `--execute`와 역할별 HTTPS endpoint를 명시한다.
- [ ] read-only method allowlist 밖의 send/sign/mutation 호출은 0건이다.
- [ ] endpoint·credential·응답 원문 secret은 fixture·SQLite·로그에 저장하지 않는다.
- [ ] 실패·429·timeout은 성공으로 추론하지 않고 structured attempt로 보존한다.

Rules가 `unclear` 또는 `restricted`면 `provided_artifact`·confirmed local
fixture만 사용하고 live adapter 호출은 0건이어야 한다. Explorer는 자동
대안이 아니다.

## 6. Promotion 실행 순서

1. [x] sanctions·ENS·relation-hub의 문서·claim boundary를 닫는다.
2. [x] 세 fixture에서 analyzer·Verifier·negative oracle을 재실행한다.
3. [x] expected/evidence/provider replay의 canonical hash 불변을 확인한다.
4. [x] 세 fixture를 별도 판단해 `confirmed`로 승격하고 Receipt를 쓴다.
5. [x] 세 문제의 미완성 범위를 숨기지 않고 Benchmark `assisted`로 반영한다.
6. [x] label publisher 확인 경로와 대체 후보를 비교해 official OFAC
   historical action + MIT config + fixed-block ENS 교체안을 선정한다.
7. [ ] 새 subject의 replay·oracle·Verifier·analyzer hash를 재검증하고
   OpenRAIL scoring dependency를 제거한다.
8. [ ] common-funder는 bounded evidence 이후 다시 검토한다.

## 7. 실패·중단 조건

| 조건 | 결과 |
|:---|:---|
| exact license text 또는 재배포 의무 불명 | label fixture `verifying` 유지 |
| Rules/API mode 불명 | live 0건, stored artifact 경로만 사용 |
| current snapshot을 historical action으로 대체 | `reconciliation_failed` |
| fixed-block ENS를 현재 ownership으로 승격 | `evidence_incomplete` |
| public hub/common funder로 동일 소유·공모 확정 | `evidence_incomplete` |
| artifact hash·analyzer hash·Verifier hash 불일치 | 승격 금지 |
| common-funder completeness 미증명 | `partial`·candidate 유지 |

## 8. Verification Receipt

- `scripts/verify.py`: **537 tests PASS**
- Reference Fixture Schema: **18 packages PASS**
- Analysis I/O Schema: **52 probes PASS**
- Repository traceability: **1,710 links PASS**
- Security scan: **204 runtime/evidence files PASS**
- TASK-015: negative oracle **30×2**, 독립 Verifier **4×2**, analyzer 독립
  verification **4 fixtures**, common-funder `partial` PASS
- 제품 live adapter 호출은 0건이다. 최종 Promotion Review에서 공식 SLS CSV를
  수동 read-only로 1회 재확인했으며 원문은 임시 파일 삭제 후 metadata/hash만
  보존했다. 세 fixture 상태와 Benchmark 분류 변경은 별도 Receipt에 기록했다.

## 9. 365 글로벌 평가 기준

| 기준 | 적용 |
|:---|:---|
| Functionality | live가 없어도 고정 artifact로 결정적 재현이 가능한지 분리 검증 |
| Potential Impact | 잘못된 label·제재·소유 귀속이 답으로 승격되는 위험을 차단 |
| Novelty | source permission·fact correctness·claim boundary를 독립 Gate로 관리 |
| UX | 상태·남은 Gate·다음 행동을 fixture별 표로 표시 |
| Open-source | license/Terms·pinned source·notice와 파생 fact 경계를 기록 |
| Business Plan | 대회 준비 QA 문서이므로 N/A |

## 10. Related Documents

- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) · [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md)
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) · [intel_context I/O 계약](../03_Technical_Specs/18_TASK_015_INTEL_CONTEXT_IO_CONTRACT.md)
- **Logic_Progress**: [Backlog TASK-015](../04_Logic_Progress/00_BACKLOG.md) · [Coverage Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md)
- **QA_Validation**: [Source Readiness](./50_TASK_015_SOURCE_READINESS_REPORT.md) · [Independent Verifier](./51_TASK_015_INDEPENDENT_VERIFIER_REPORT.md) · [Provenance Hardening](./52_TASK_015_PROVENANCE_HARDENING_RECEIPT.md) · [Analyzer Verification](./53_TASK_015_ANALYZER_VERIFICATION_RECEIPT.md) · [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- **QA_Validation**: [OpenRAIL License Resolution](./55_TASK_015_OPENRAIL_LICENSE_RESOLUTION_RECEIPT.md) - exact text 부재·quarantine·대체 조건
- **QA_Validation**: [LABEL Source Replacement Review](./57_TASK_015_LABEL_SOURCE_REPLACEMENT_REVIEW.md) - upstream provenance 비교·선택 subject·migration Gate
