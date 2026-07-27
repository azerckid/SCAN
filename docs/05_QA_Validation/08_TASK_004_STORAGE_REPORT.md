# TASK-004 Storage·Artifact·Export 검증 보고서
> Created: 2026-07-27 23:02
> Last Updated: 2026-07-27 23:02
> Status: TASK-004 Scope Passed · Cache/Export/Artifact Pass · Security Partial

## 1. 판정

`TASK-004`의 SQLite schema version 1, WAL·transaction, immutable cache,
checkpoint resume, SHA-256 content-addressed artifact, JSON·Markdown export,
backup·restore와 storage secret guard는 승인 범위를 통과했다. 모든 DB와
artifact는 pytest 임시 디렉터리에 생성했으며 사용자 `.scan/`과 기존 DB는
읽거나 변경하지 않았다.

| 항목 | 결과 |
|:---|:---|
| 기준 code commits | `73a4799`, `d1ea6bb` |
| branch | `codex/task-004-storage-artifacts` |
| Python | `3.13.7` |
| SQLite schema | `user_version=1`, STRICT tables 11개 |
| 직접 dependency | 추가 없음 |
| Analysis I/O Schema | `0.1` 유지 |
| QA | cache/export/artifact 3 pass, security 1 partial |

CLI stdout·stderr·exit code, DEX/AUTH/FREEZE 분석기와 실제 사용자 `.scan/`
composition root는 구현하지 않았다.

## 2. 구현 경계

| 영역 | 구현 |
|:---|:---|
| SQLite | run·policy·attempt·cache·source·result·evidence·link·checkpoint·export |
| Pragma | foreign key, WAL, synchronous FULL, busy timeout |
| Cache | chain+canonical request key, fixed block immutable only |
| Attempt | append-only 번호, outcome·failure·wait·raw hash·artifact 연결 |
| Checkpoint | stage별 revision, cursor·완료 evidence canonical hash |
| Artifact | SHA-256 경로, 임시 파일 fsync, create-if-absent hard link |
| Export | 같은 Analysis Result dict에서 JSON과 Markdown 생성 |
| Backup | 새 대상에 SQLite backup API, 완료 후 integrity check |
| Security | explicit canary와 사용자 홈 절대 경로 사전 차단 |

구현 위치:

- `src/scan_tool/adapters/sqlite_storage.py`
- `src/scan_tool/adapters/artifacts.py`
- `src/scan_tool/application/storage_orchestration.py`
- `src/scan_tool/application/export.py`
- `src/scan_tool/application/security.py`
- `tests/integration/test_storage_artifacts.py`

## 3. Storage·constraint 검증

- 새 DB만 schema version 1로 초기화하고 알 수 없는 version은 자동 변경하지
  않는다.
- run+policy와 result+source+evidence+link는 각각 한 transaction으로
  저장한다.
- 모든 값은 parameter binding으로 전달한다. table count의 동적 이름은
  내부 allowlist에 한정한다.
- result와 evidence는 `analysis_id`를 포함한 복합 foreign key로 다른 run과
  연결할 수 없다.
- 종료 run은 `finished_at`이 필요하고 queued/running에는 없어야 한다.
- 같은 요청을 재조회하면 provider별 attempt 번호를 기존 최대값 뒤에
  append하며 실패 이력을 덮어쓰지 않는다.
- 분석 결과 전 attempt에는 임시 source record를 만들지 않고 nullable로
  보존하며, 실제 evidence 생성 시 source attempt를 연결한다.

fixture DEX·AUTH·FREEZE 각각 request, result, source, evidence, checkpoint,
JSON·Markdown export를 저장한 뒤 backup DB를 열어 `integrity_check=ok`와
행 수·checkpoint 동일성을 확인했다.

## 4. Cache·resume 검증

고정 block tag 요청의 첫 실행은 `cache_status=miss`, 두 번째 offline 실행은
`cache_status=hit`였다. 두 번째 실행에서 adapter call count는 증가하지 않았고
raw body·source·provider·request fingerprint가 일치했다.

`latest` 요청은 두 번 모두 source를 호출하고 cache row를 만들지 않았다.
같은 cache key에 다른 artifact를 연결하려는 시도는 provenance conflict로
거부했다.

checkpoint runner는 첫 호출에서 완료 stage를 저장하고 두 번째 호출에서는
operation을 다시 실행하지 않고 `resumed=true`와 같은 revision을 반환했다.

## 5. Artifact·export 검증

- 동일 body 두 개는 같은 SHA-256·상대 경로를 재사용한다.
- 1-byte가 다른 body는 다른 hash를 가진다.
- 기존 hash 파일은 overwrite하지 않고 byte length·hash를 다시 검사한다.
- 변조된 artifact는 읽기 시 integrity error다.
- 최종 경로에 임시 부분 파일이 남지 않는다.
- artifact URI는 `artifact://sha256/<hash>`다.
- JSON export는 `AnalysisResult.to_contract_dict()`와 동일하다.
- Markdown canonical JSON을 역파싱하면 같은 dict다.
- result·evidence·source ID와 raw 값이 Markdown 표에도 유지된다.
- 동일 result 재export는 같은 두 artifact hash를 재사용한다.

## 6. Security 판정

| 검증 | 결과 |
|:---|:---|
| canary API secret | DB·cache·checkpoint·artifact·export 쓰기 전 거부 |
| macOS/Linux/Windows 사용자 홈 | persistence 전 거부 |
| SQL 값 | parameter binding |
| Markdown 외부 문자열 | HTML·pipe·backtick·newline escape |
| 절대 artifact path | DB 저장 금지, `.scan/` 상대 경로만 |
| 기존 backup | overwrite 없이 거부 |
| 삭제·reset·DROP | 구현하지 않음 |

`QA-SEC-001`은 storage 범위를 통과했지만 CLI stdout·stderr·log와 통합 검색이
남아 전체 상태는 `partial`이다.

## 7. 실행 증거

| 검증 | 결과 |
|:---|:---|
| Ruff lint | pass |
| Ruff format | pass |
| pytest | `57 passed` |
| fixture Schema validator | `PASS 3` |
| analysis Schema validator | `PASS 3` |
| generated Schema compatibility | `PASS 3`, 35 probes |
| SQLite backup restore | DEX·AUTH·FREEZE `integrity_check=ok` |
| 사용자 `.scan/` 접근 | 0 |
| `git diff --check` | pass |

재현 명령:

```bash
uv sync --locked
uv run python scripts/verify.py
```

## 8. 코드 품질 검토

| 영역 | 판정 | 근거 |
|:---|:---:|:---|
| 로직 정확성 | Pass | cache miss/hit/latest, resume, conflict, restore 검증 |
| 타입 안전성 | Pass | immutable dataclass·Pydantic model 입력 |
| YAGNI/KISS/DRY | Pass | sqlite3·hashlib·json 표준 API만 사용 |
| 책임 분리 | Pass | SQLite metadata, artifact byte, export renderer 분리 |
| Side effect | Pass | tmp_path만 사용, live network·사용자 DB 0 |
| 가독성 | Pass | 100줄 초과 함수 제거, 단계별 private method |
| 불필요 코드 | Pass | ORM·migration framework·GC·CSV 미구현 |
| UI-First | N/A | CLI 화면 동작 변경 없음 |

## 9. 365 글로벌 평가 기준

| 기준 | 상태 | TASK-004 증거 |
|:---|:---:|:---|
| Functionality | Pass | 57 tests, storage QA 3 pass, security storage scope pass |
| Potential Impact | Pass | 체인·분석기 공통 local provenance·offline replay 기반 |
| Novelty | Pass | evidence-first DB와 content-addressed raw artifact 분리 |
| UX | Pass | cache hit와 checkpoint resume로 반복 조회 제거 |
| Open-source | Pass | Python·SQLite 표준 API, 재현 명령, 공개 DDL 계약 |
| Business Plan | N/A | 로컬 기반 구현 작업이며 수익 모델 범위가 아님 |

## 10. Originality & Ethics Check

- 외부 포렌식 제품의 DB·renderer 코드를 복제하지 않았다.
- 실제 대회 문제·답안·개인정보를 외부 서비스에 전송하지 않았다.
- 사용자 DB·홈 경로·credential을 테스트에 사용하지 않았다.
- secret·사용자 홈 절대 경로를 persistent output 전에 차단했다.
- 서명·거래 전송·자동 제출·brute force 기능을 추가하지 않았다.
- 새 third-party dependency를 추가하지 않았다.

## 11. 남은 경계

- `TASK-005`: 실제 `.scan/` composition root와 CLI stdout·stderr·exit code
- `TASK-006`~`TASK-008`: DEX·AUTH·FREEZE 분석 result 생성
- `TASK-009`: 전체 fixture 회귀와 secret 통합 검색
- schema version 2 migration·garbage collection: 요구 발생 전 미구현
- live API·AI·agent·CTFd 자동 제출: Rules 확인과 별도 승인 전 비활성

## 12. Related Documents

- [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md)
- [SQLite DB Schema](../03_Technical_Specs/01_DB_SCHEMA.md)
- [P0·V1 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md)
- [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md)
- [Analysis I/O Schema](../03_Technical_Specs/05_ANALYSIS_IO_SCHEMA.md)
- [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)
- [P0·V1 QA Checklist](./02_QA_CHECKLIST.md)
