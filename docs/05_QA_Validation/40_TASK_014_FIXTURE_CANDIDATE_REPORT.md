# TASK-014 PATH 공개 Fixture 후보 선정 보고서
> Created: 2026-07-29 23:25
> Last Updated: 2026-07-30 00:08
> Status: Candidate Selection Superseded · Fixture 3 Verifying · Implementation Locked

## 1. 목적

사용자 승인에 따라 TASK-014의 세 proposed fixture에 실제 Ethereum mainnet
공개 사례를 선정한다. 이 보고서는 사례·입력·예상 정답 골격을 고정하지만
`verifying`/`confirmed`, Analysis I/O 승인, Context Receipt, analyzer 구현,
Benchmark 승격을 주장하지 않는다.

## 2. 선정 사건과 사용 경계

Euler Finance가 공개한 2023년 사건 연표의 자금 분기·반환 구간을 사용했다.
공식 글은 후보 발견과 시점 맥락에만 사용하며, 채점 사실은 공개 Ethereum
transaction·receipt·block과 Blockscout internal transaction에서 얻었다.

- 범죄 의도·피해자·주소 소유자·공통 통제: `not_assessed`
- Etherscan/Blockscout label: scoring 근거 아님
- 가격·달러 환산: scoring 밖
- 실행: read-only RPC·공개 Explorer API만 사용, 서명·전송 0건

## 3. 선정 결과

| Fixture | 문제 | 공개 범위 | 고정한 1차 정답 | 상태 |
|:---|:---|:---|:---|:---:|
| `FX-FLOW-PATH-001` | FLOW-EVM-001 | internal 1 + top-level 2, 3홉 | ordered endpoints·TX·raw amount·terminal | verifying |
| `FX-FLOW-REMERGE-001` | FLOW-EVM-002 | seed 1 → branch 4 → merge 1 | split `30953 ETH`, merge `30951.4 ETH`, residual `1.6 ETH`, dust 분리 | verifying |
| `FX-FLOW-MULTI-001` | FLOW-MULTI-001 | origin 4 → exit 1 | origin별 raw contribution·dedup total `30951.4 ETH` | verifying |

세 fixture는 같은 공개 사건을 서로 다른 request scope로 잘랐다. 이는
node/edge 재사용과 query별 정답 차이를 검증하기 위한 선택이다. 사건·자산
다양성은 후속 fixture 또는 negative oracle에서 보강한다.

## 4. 확인된 온체인 사실

### 4.1 단일 3홉

```text
0x036cec...25f1c
  -- 88752697459828535340019 wei, internal, tx 0x298b...db55 -->
0xb66cd9...995db
  -- 7738250000000000000000 wei, tx 0x79c1...aeda -->
0xa1b44d...8e676
  -- 7738050000000000000000 wei, tx 0xe3f6...fd0d -->
0xee009f...c8c5
```

raw 금액이 홉마다 다르므로 “같은 금액” 휴리스틱으로 연결하지 않는다.
주소 endpoint와 명시된 TX 순서로만 경로를 구성한다.

### 4.2 분기·재병합

- seed output: `7738250000000000000000` wei × 4
- merge input: `7737250000000000000000` wei × 1 +
  `7738050000000000000000` wei × 3
- unresolved residual: `1600000000000000000` wei
- 외부 dust: `1000000000000` wei — seed ledger에 더하거나 빼지 않음

residual은 현재 “확인됐지만 분류되지 않은 잔여”다. balance·gas·후속 이동을
연속 범위로 검증하기 전에는 fee로 단정하지 않는다.

### 4.3 다중 origin

네 transaction hash와 네 origin은 모두 고유하고 exit가 동일하다. raw
합계는 `30951400000000000000000` wei다. 가격 누락은 raw 경로 실패가 아니다.

## 5. 공급자 실행 기록

| Source | 결과 | 비고 |
|:---|:---:|:---|
| `PROVIDER-EVM-VERIFY` | complete | TX·receipt·block 10건 조회, 성공 status·주소·value 확인 |
| `PROVIDER-EVM-PRIMARY` | rate_limited | 첫 요청 HTTP 429; 이 보고서에서 재시도·성공을 주장하지 않음 |
| Blockscout Ethereum API | complete / supporting | 첫 internal edge와 주소 거래 후보 조회 |
| Euler Finance official article | complete / context | 분기·반환 chronology만 사용 |

endpoint·credential·환경변수 값은 저장하지 않았다.

## 6. 완료·부분·실패 기준 초안

| 판정 | 조건 |
|:---|:---|
| complete 후보 | 명시 scope의 필수 edge가 모두 있고 endpoint·asset·raw ledger가 exact match |
| partial 후보 | 확인 edge는 유효하지만 trace/range/frontier/한 branch가 누락되며 중단 지점 보존 |
| failed 후보 | edge endpoint 불연속, 다른 asset, 중복 집계, 외부 inflow 오염, source reconciliation 불일치 |

## 7. 승격 Gate 진행

- [x] primary와 verify provider의 두 번째 raw replay
- [x] primary callTracer로 internal edge 재현
- [x] capability별 canonical raw SHA-256
- [x] selected transaction scope만 scoring, continuous gap은 범위 밖으로 결정
- [x] residual을 unresolved로 보존하고 근거 없는 fee 분류 금지
- [x] cycle·중복·unrelated·budget·asset mismatch negative oracle 18개
- [x] 같은 replay 두 번의 canonical hash 일치
- [x] 독립 Verifier의 graph·ledger 재계산
- [ ] `flow_path` Analysis I/O 대안 B 정식 승인
- [ ] Context Receipt `PASS`와 사용자 analyzer 구현 승인

## 8. 365 평가 기준

| 기준 | 현재 판정 | 근거 |
|:---|:---:|:---|
| Functionality | Partial / Candidate | 세 실제 graph scope와 raw 정답 골격 확보 |
| Potential Impact | Planned | PATH 공통 엔진의 세 대표 query 입력 |
| Novelty | Candidate | external inflow·residual·dedup을 정답에 노출 |
| UX | Pass / Docs-only | 승인된 PATH Preview가 같은 세 query를 표현 |
| Open-source | Partial | 공개 온체인·공식 사건 글, replay artifact는 미작성 |
| Business Plan | N/A | 대회 준비 QA |

## 9. 판정

세 공개 사례는 후속 replay·oracle·Verifier를 통과해 **`verifying`**이다.
continuous gap과 완전 사건 ledger는 선택 범위 밖이며, residual은 unresolved로
보존한다. 제품 analyzer·Analysis I/O 정식 승인·Context Receipt가 남았으므로
`confirmed`로 올리지 않고 TASK-014 구현도 계속 잠근다.

## 10. Related Documents

- **Technical_Specs**: [TASK-014 PATH 계약](../03_Technical_Specs/15_TASK_014_PATH_CONTRACT_PROPOSAL.md) - fixture 선정 조건·graph 계약
- **UI_Screens**: [TASK-014 PATH UI](../02_UI_Screens/08_TASK_014_PATH_UI.md) - 사용자 승인된 세 query 화면
- **Logic_Progress**: [Backlog TASK-014](../04_Logic_Progress/00_BACKLOG.md) - Context Lock·구현 승인
- **Logic_Progress**: [Coverage Execution Plan](../04_Logic_Progress/01_EXECUTION_PLAN.md) - Wave 3 순서
- **QA_Validation**: [Reference Fixtures](./01_REFERENCE_FIXTURES.md) - fixture 목록·상세
- **QA_Validation**: [TASK-014 Fixture Gate](./39_TASK_014_FIXTURE_CONTRACT_GATE.md) - 다음 QA 단계
- **External**: [Euler Finance incident timeline](https://www.euler.finance/blog/war-peace-behind-the-scenes-of-eulers-240m-exploit-recovery) - 공개 사건 맥락
