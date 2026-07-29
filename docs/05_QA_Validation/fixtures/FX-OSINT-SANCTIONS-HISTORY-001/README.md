# Fixture: FX-OSINT-SANCTIONS-HISTORY-001
> Created: 2026-07-30 03:37
> Last Updated: 2026-07-30 03:37
> Status: Candidate 0.1 · Official HTML hashes recorded · Verifier pending

## 1. 목적

동일 주소를 직접 명시한 OFAC의 2022 지정과 2025 해제를 역사적 timeline으로
보존한다. 현재 제재 상태나 범죄성을 자동 판정하지 않는다.

## 2. 현재 근거

- 2022 designation page SHA-256와 주소 1회 match
- 2025 removal page SHA-256와 주소 1회 match

전체 HTML은 repository에 복제하지 않고 공식 URL·whole-file hash·bounded
address match만 보존한다.

## 3. 남은 Gate

- [ ] 적용 가능한 OFAC SLS version 고정
- [ ] direct/indirect·stale-current negative oracle
- [ ] 독립 Verifier·두 번 결정성
- [ ] `verifying` 승격 검토

## 4. Related Documents

- [Source-resolution report](../../47_TASK_015_SOURCE_RESOLUTION_RAW_SNAPSHOT_REPORT.md)
- [Fixture·Contract Gate](../../45_TASK_015_FIXTURE_CONTRACT_GATE.md)
