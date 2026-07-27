# TASK-001 Python Bootstrap 검증 보고서
> Created: 2026-07-27 20:57
> Last Updated: 2026-07-27 20:57
> Status: Passed · QA-BOOT-001

## 1. 판정

`TASK-001`의 Python project 초기화와 offline 품질 Gate는 통과했다.
분석 model·source adapter·SQLite·DEX/AUTH/FREEZE 기능은 구현하지 않았으며,
공식 Rules가 `unclear`인 live API·AI·agent·CTFd 자동화도 활성화하지 않았다.

| 항목 | 결과 |
|:---|:---|
| 기준 commit | `1bfdc63` |
| branch | `codex/task-001-python-bootstrap` |
| Python | `3.13.7` (`>=3.12,<3.15`) |
| uv | `0.11.32` |
| package | `scan-forensics-tool 0.1.0` |
| QA | `QA-BOOT-001` pass |

## 2. 생성된 실행 경계

- `pyproject.toml`, `uv.lock`, `.python-version`
- `src/scan_tool/` package와 `scan --help`, `scan --version`
- `tests/unit`, `tests/integration`, `tests/regression`
- `scripts/verify.py` 단일 offline 품질 Gate
- `.scan/`, `.env*`, test·build cache, 로컬 DB 제외 규칙

현재 승인된 환경변수가 없으므로 `.env.example`은 생성하지 않았다. 실제
source adapter에서 공유할 변수 이름이 승인되면 빈 값과 설명만 가진 예제를
별도 검토한다.

## 3. Dependency Gate

### 3.1 직접 dependency

| 구분 | 선언 | lock 결과 | 사용 이유 | License |
|:---|:---|:---|:---|:---|
| Build | `hatchling==1.31.0` | exact build backend | src layout package 설치 | MIT |
| Runtime | `typer>=0.21.0,<1.0` | `0.27.0` | 승인된 `scan` CLI 진입점 | MIT |
| Dev | `jsonschema>=4.25.1,<5` | `4.26.0` | 기존 Schema 검증기 | MIT |
| Dev | `pytest>=9.0.2,<10` | `9.1.1` | unit·integration·regression | MIT |
| Dev | `ruff>=0.14.14,<1` | `0.16.0` | lint·format 단일 Gate | MIT |

표준 라이브러리로 CLI parsing과 기존 Schema 검증을 대체하면 승인 기술 결정과
검증기를 다시 작성해야 하므로 위 네 project dependency만 채택했다.
HTTPX·Pydantic·eth-abi·eth-utils는 아직 사용 코드가 없어 설치하지 않았다.

### 3.2 간접 dependency와 보안

`uv.lock`은 project를 포함해 20개 package record를 가진다. 현재 macOS
Python 3.13.7 환경에는 project를 포함해 18개가 설치됐다. 간접 dependency의
license는 MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0 또는
BSD-2-Clause, PSF-2.0 범위이며 프로젝트 MIT 배포와 충돌하는 copyleft
dependency는 없다. `markdown-it-py`와 `mdurl`은 metadata classifier의 MIT
표시를 사용했다.

잠금 목록을 `uv export --locked --no-hashes --no-emit-project`로 내보낸 뒤
`pip-audit`로 조회한 결과는 `No known vulnerabilities found`였다.
`pip-audit`은 검증용 임시 도구이며 project dependency에는 추가하지 않았다.

## 4. 실행 증거

| 검증 | 결과 |
|:---|:---|
| 독립 임시 환경 `uv sync --locked` | pass |
| `uv run ruff check .` | pass |
| `uv run ruff format --check .` | pass |
| `uv run pytest` | `5 passed` |
| fixture Schema validator | `PASS 3` |
| analysis Schema validator | `PASS 3` |
| `uv run scan --help` | exit 0 |
| `uv run scan --version` | `0.1.0`, exit 0 |
| package import | `scan_tool.__version__ == "0.1.0"` |

재현 명령:

```bash
uv sync --locked
uv run python scripts/verify.py
uv run scan --help
```

기존 Schema validator 두 파일은 Ruff 기준선에 포함하기 위해 기계적으로
format했고, `zip(..., strict=True)`로 FREEZE 전이 개수 불일치를 조용히
절단하지 않도록 했다. fixture·analysis 결과는 변경되지 않았다.

## 5. 보안·부작용 확인

- 테스트는 저장 fixture만 읽고 외부 네트워크를 호출하지 않는다.
- 사용자 홈 credential과 실제 `.scan/`을 읽거나 변경하지 않는다.
- private key·seed phrase·API key·CTFd credential 입력은 없다.
- 추적 대상에서 `.scan/`, `.env*`, SQLite 파일과 cache를 제외한다.
- CLI는 도움말과 version만 제공하며 분석·제출 동작은 없다.

## 6. 365 글로벌 평가 기준

| 기준 | TASK-001 반영 |
|:---|:---|
| Functionality | 재현 설치·CLI entry point·5개 test·Schema PASS 3 |
| Potential Impact | 후속 분석 기능이 공유할 src layout과 단일 품질 Gate |
| Novelty | 기능 추가보다 evidence-first 계약의 회귀를 초기 Gate에 포함 |
| UX | 설치 직후 `scan --help`와 명확한 version 확인 |
| Open-source | MIT, lockfile, dependency license·취약점 기록 |
| Business Plan | project bootstrap 범위가 아니므로 N/A |

## 7. 남은 경계

- `TASK-002` Analysis I/O Pydantic model과 Schema diff: 별도 승인 필요
- `TASK-003` source port·policy·retry·fallback: 별도 승인 필요
- `TASK-004` 이후 SQLite와 실제 분석 기능: 미구현
- live API·AI·agent·CTFd 자동 제출: Rules 확인과 별도 승인 전 비활성

## 8. Related Documents

- [Python 개발 원칙](../03_Technical_Specs/00_DEVELOPMENT_PRINCIPLES.md)
- [기술 선택 기록](../03_Technical_Specs/04_SCAN_2026_TECHNOLOGY_DECISION.md)
- [P0·V1 Backlog](../04_Logic_Progress/00_BACKLOG.md)
- [P0·V1 QA 시나리오](./01_TEST_SCENARIOS.md)
- [P0·V1 QA Checklist](./02_QA_CHECKLIST.md)
