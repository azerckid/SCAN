# FLOW 최종 계좌 후보 탐색 — 문제 정의와 해결 방법

> Created: 2026-08-01
> Status: Method draft · Implementation not started
> Related: [Contest Day Playbook](./75_CONTEST_DAY_PROBLEM_SOLVING_PLAYBOOK.md),
> [Expected Problem Bank](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) (`FLOW-EVM-001`)

## 1. 이 문서의 목적

코드에 들어가기 전에, **어떤 문제를 풀려고 하는지**와 **어떻게 풀 것인지**만
고정한다. 구현·CLI·테스트는 이 문서에 합의된 범위 안에서만 후속한다.

이 방법은 production `flow_path` analyzer를 대체하지 않는다.
대회 당일 assisted 경로와, 이후 contest 헬퍼 설계의 공통 기준이다.

## 2. 풀려는 문제 (Problem Definition)

### 2.1 문제 형태

출제·실전에서 자주 나오는 형태:

> 주소 A(시드)에서 금액 S(예: 100 ETH)가 이동했다.
> **최종 계좌(들)를 찾아라.**

단서가 보통 주는 것:

- 시드 주소 A
- 출발 금액 S (또는 출발 TX / 대략 총액)
- 시간 또는 블록 창 (있을 수 있음)

단서가 보통 **안** 주는 것:

- 중간에 몇 번 갈라졌는지
- 중간 집금점이 어디인지
- “10×10” 같은 구조 힌트

### 2.2 성공 기준 (무엇을 맞히면 되는가)

| 등급 | 의미 | 제출 형태 |
|:---|:---|:---|
| **후보 집합 적중** | 정답 최종 주소가 후보 목록에 포함 | `heuristic_candidates` + 근거 TX |
| **단일 확정** | 후보가 하나이고 경로·금액 정합이 깨끗 | 최종 주소 + 근거 (그래도 ownership 단정 금지) |
| **부분** | 유력 후보는 있으나 더 깊은 갈래 미검증 | `partial` + 한계 명시 |

**오답에 가까운 행동:** 경로·금액 정합 후보가 여러 개인데 근거 없이 하나만 찍기.

### 2.3 비목표 (이번에 풀지 않는 것)

- 섞인 뒤 “이 wei가 피해자 돈”이라는 **원천 유일 확정**
- 임의 규모(100×100) 그래프의 **무인 complete / Benchmark confirmed**
- production `src/scan_tool/slices/flow_path.py` thaw·교체
- 소유자·서비스·범죄 의도 단정 (`not_assessed` 유지)

### 2.4 기존 SCAN 기능과의 관계

| 기존 | 이 방법 |
|:---|:---|
| `FLOW-EVM-001` / `trace_path` | 짧은 bounded path는 이미 automated. 이 방법은 **더 넓게 후보를 모을 때**의 assisted·헬퍼 기준 |
| `FLOW-EVM-002` / `trace_remerge` | **이미 관측된** 1회 분산→재병합 구간 증명용. 이 방법의 선행 탐색이 아님 |
| Bridge quick-capture | 무관. 브리지 양단 링크 전용 |

## 3. 핵심 가설 (왜 이 방법이 통하는가)

1. 시드에서 출발한 자금이 최종에 모이면, 최종 유입액은 출발액 S와
   **같거나 수수료 등으로 근접**한 경우가 많다.
2. “금액만 비슷한 주소”는 있을 수 있으나,
   **시드와 온체인 경로로 연결**되고 금액도 근접한 주소는 **보통 적다**.
3. 그런 주소가 여러 개면 우연으로 쳐내지 않고 **전부 용의선**에 올린다.
4. 각 후보에 대해 **역방향**으로 시드까지 이어지는지 확인하면
   후보를 더 줄이거나, 남는 집합의 근거를 강화할 수 있다.

금액 근접은 **후보 포함 조건**이다. 경로 없는 숫자 일치만으로 confirmed 하지 않는다.
경로가 확인된 근접 금액 주소는 우연으로 버리지 않는다.

## 4. 해결 방법 (Solution Method)

### 4.1 단계 요약

```text
(1) 순방향 수집
    시드 A에서 시간/블록 창 안 outbound 이동을 따라가며
    도달 주소 집합 V와 edge(TX) 집합 E를 모은다.
    (깊이·주소 수·edge 수에 탐색 budget을 둔다.)

(2) 금액 필터 (허용 오차)
    V 각 주소 v에 대해, 창 안·관련 edge 기준 유입 합(또는
    해당 유입)이 S에 근접하면 후보 C0에 넣는다.
    근접: |amount - S| <= tolerance
    tolerance는 절대 wei 또는 S의 비율(예: 수수료 상한)로 둔다.

(3) 역방향 연결 검증
    C0의 각 v에 대해, E(또는 필요 시 추가 조회)로
    “A에서 v로 이어지는 경로가 있는가”를 확인한다.
    경로가 있으면 C에 넣고, 근거 TX 목록을 붙인다.
    경로가 없으면 C0에서 제거한다. (금액만 비슷한 무관 주소)

(4) 출력
    C 전부 = suspect_candidates / heuristic_candidates
    |C| == 1 이고 근거가 깨끗해도 ownership·criminality는 not_assessed
    |C| == 0 이면 partial/실패 사유 (budget 부족, 자산 변경, 창 부족 등)
```

### 4.2 당일(사람+AI) 운영 순서

구현 전이거나 헬퍼 없이도 동일하다.

1. 문제를 채팅에 붙인다.
2. 시드 출금과 S를 확인한다.
3. 순방향으로 주소를 모은다 (탐색기·RPC·기존 SCAN path).
4. S 근접 주소만 남긴다.
5. 각각 역으로 시드 연결을 확인한다.
6. 남는 주소를 **전부** 후보로 적는다. 하나만 찍지 않는다.
7. 짧고 깨끗한 구간만 기존 `scan analyze` path/remerge로 재검증한다.

### 4.3 이후 코드로 옮길 때의 경계 (예정)

- 위치: `scripts/contest/` 만 (예: `flow_final_candidates.py`)
- production analyzer·Benchmark·verify 본문 로직 변경 없음
- 출력에 `verification_level: heuristic_candidates` 고정
- confirmed fixture·dual-provider 사칭 금지
- 라이브 RPC를 쓸 경우 Bridge 헬퍼와 같이 **env 이름만**, HTTPS·시크릿 리댁션

(구현은 이 문서 승인·별도 착수 후에만 진행한다.)

## 5. 입·출력 계약 (초안)

### 5.1 입력

| 필드 | 필수 | 설명 |
|:---|:---|:---|
| `seed` | 예 | 출발 주소 A |
| `amount_raw` 또는 `amount_eth` | 예 | 출발 금액 S |
| `tolerance_raw` 또는 `tolerance_bps` | 예 | 근접 허용 (수수료 등) |
| `from_block` / `to_block` 또는 시간창 | 권장 | 탐색 창 |
| `max_hops` / `max_nodes` / `max_edges` | 예 | 순방향 budget |
| edge/TX 패키지 또는 RPC | 택1 | 오프라인 우선, 라이브는 후순위 |

### 5.2 출력

```json
{
  "verification_level": "heuristic_candidates",
  "seed": "0x...",
  "amount_target_raw": "...",
  "tolerance_raw": "...",
  "candidates": [
    {
      "address": "0x...",
      "matched_amount_raw": "...",
      "path_tx_hashes": ["0x..."],
      "forward_hops": 0
    }
  ],
  "excluded_amount_only": [],
  "budget": { "exhausted": false },
  "attribution": {
    "ownership": "not_assessed",
    "criminality": "not_assessed"
  }
}
```

`excluded_amount_only`: 금액은 근접하나 시드 경로가 없는 주소 (있을 때만).

## 6. 위험과 한계 (정직하게)

| 위험 | 대응 |
|:---|:---|
| budget에 정답이 안 들어옴 | `budget.exhausted=true`, partial, 창·budget 확대 후 재실행 |
| 스왑·브리지로 자산·수량이 바뀜 | 본 방법(동일 native 금액 근접)만으로는 부족. Bridge/DEX 경로로 이관 |
| 후보 0개 | 오답 단정 금지. 데이터·tolerance·창을 점검 |
| 후보 여러 개 | **전부 제출**. 임의로 하나 선택 금지 |
| 대규모 그래프 | 정확도·완전성은 연구 과제. 본 방법은 **후보 recall**을 우선 |

## 7. 구현 전 체크리스트

- [ ] 이 문서의 문제 정의·비목표에 합의했다
- [ ] 출력은 heuristic이며 confirmed가 아니다
- [ ] production flow_path를 수정하지 않는다
- [ ] 착수 시 별도 승인 후 `scripts/contest/`에만 추가한다
- [ ] 플레이북 §3.7에 이 문서 링크를 넣는다

## 8. Related Documents

- [Contest Day Problem-Solving Playbook](./75_CONTEST_DAY_PROBLEM_SOLVING_PLAYBOOK.md)
- [Contest Stabilization Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
- [Expected Problem Benchmark Report](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md)
- [FLOW path fixture `FX-FLOW-PATH-001`](./fixtures/FX-FLOW-PATH-001/)
- [FLOW remarge fixture `FX-FLOW-REMERGE-001`](./fixtures/FX-FLOW-REMERGE-001/)
