# FLOW 최종 계좌 후보 탐색 — 문제 정의와 해결 방법

> Created: 2026-08-01
> Updated: 2026-08-01 (PR #119 review: residual filter · independent reverse check)
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
- 출발 금액 S (raw 정수 단위로 취급; 표시 ETH는 파생)
- `chain_id`와 `asset_scope` (예: native ETH on chain 1)
- 시간 또는 블록 창 (있을 수 있음)

단서가 보통 **안** 주는 것:

- 중간에 몇 번 갈라졌는지
- 중간 집금점이 어디인지
- “10×10” 같은 구조 힌트

### 2.2 성공 기준 (무엇을 맞히면 되는가)

| 등급 | 의미 | 제출 형태 |
|:---|:---|:---|
| **후보 집합 적중** | 정답 최종 주소가 후보 목록에 포함 | 항상 `heuristic_candidates` + 근거 TX |
| **부분** | 유력 후보는 있으나 scope/budget 미완결 | `partial` + `scope_complete=false` 등 한계 명시 |

**금지:** bounded 탐색에서 후보가 하나라는 이유만으로 “단일 확정” /
`confirmed`로 승격. continuous scope 완결성이 입증되기 전에는
**계속 `heuristic_candidates`**다. ownership·criminality는 항상
`not_assessed`.

**오답에 가까운 행동:** 잔류·종착 조건이 맞는 후보가 여러 개인데
근거 없이 하나만 찍기. 또는 중간 경유 주소(유입≈S이지만 곧 다시
유출)를 최종로 제출하기.

### 2.3 비목표 (이번에 풀지 않는 것)

- 섞인 뒤 “이 wei가 피해자 돈”이라는 **원천 유일 확정**
- 임의 규모(100×100) 그래프의 **무인 complete / Benchmark confirmed**
- production `src/scan_tool/slices/flow_path.py` thaw·교체
- 소유자·서비스·범죄 의도 단정 (`not_assessed` 유지)
- **gross 유입액 ≈ S만으로 최종 후보를 고르는 것** (중간 주소 오염)

### 2.4 기존 SCAN 기능과의 관계

| 기존 | 이 방법 |
|:---|:---|
| `FLOW-EVM-001` / `trace_path` | 짧은 bounded path는 이미 automated. 이 방법은 **더 넓게 최종 후보를 모을 때**의 assisted·헬퍼 기준 |
| `FLOW-EVM-002` / `trace_remerge` | **이미 관측된** 1회 분산→재병합 구간 증명용. 이 방법의 선행 탐색이 아님 |
| Bridge quick-capture | 무관. 브리지 양단 링크 전용 |

## 3. 핵심 가설 (왜 이 방법이 통하는가)

1. 시드 자금이 **최종에 머무르면**, 그 주소의
   **관련 잔류액**(관련 유입 − 관련 후속 유출)이 출발액 S와
   같거나 수수료 등으로 **근접**한 경우가 많다.
2. `A → B → C → D`처럼 중간 주소 B·C도 gross 유입은 약 S일 수 있다.
   따라서 **유입액만 S와 비교하면 중간 주소까지 전부 후보가 된다.**
   후보 기준은 gross inflow가 아니라 **잔류액 + 종착 조건**이다.
3. 잔류액이 S에 가깝고 종착 조건을 만족하며, **독립 검증으로**
   시드와 연결된 주소는 보통 적다. 여러 개면 **전부 용의선**이다.
4. “순방향 그래프 E에서 고른 뒤, 같은 E로 다시 시드 연결을 확인”은
   **항상 참이 되므로 검증이 아니다.** 역방향(또는 연결) 검증은
   **별도 raw TX 재조회·pin 또는 독립 edge 집합**으로만 한다.

## 4. 해결 방법 (Solution Method)

### 4.1 관련 유입·유출·잔류 (정의)

주어진 `asset_scope`·`chain_id`·탐색 창 안에서, 시드 흐름에 묶인
edge만 “관련”으로 센다 (시드 무관 external inflow는 관련 유출/유입에
넣지 않음 — 플레이북 FLOW 함정과 동일).

주소 `v`에 대해:

```text
related_in(v)  = v로 들어오는 관련 edge 금액 합 (raw 정수)
related_out(v) = v에서 나가는 관련 edge 금액 합 (raw 정수)
residual(v)    = related_in(v) - related_out(v)
```

**최종 후보 조건 (모두 만족):**

1. `|residual(v) - S| <= tolerance` (raw 정수 비교)
2. **종착 조건** 중 하나:
   - 이후 **관련 유출이 없음** (`related_out(v) == 0` 또는 창/scope 안에서
     더 이상 시드 흐름 유출이 관측되지 않음), 또는
   - 서비스 종착점으로 **별도 근거**와 함께 확인됨 (라벨은 공식 출처만;
     community tag로 종착 확정 금지). 근거가 약하면 후보에 넣되
     `terminus_kind: suspected_service`로 표시하고 confirmed 금지
3. 아래 §4.3 **독립 연결 검증** 통과

중간 경유 주소는 보통 `residual ≈ 0` (들어와서 다시 나감)이므로
조건 1에서 걸러진다.

### 4.2 단계 요약

```text
(0) 입력 고정
    seed, chain_id, asset_scope, amount_raw(S), tolerance_raw(+근거),
    block/time window, exploration budget, collection_method

(1) 순방향 수집 (discovery graph E_disc)
    시드 A에서 창 안 outbound를 따라가며 도달 주소 V와 edge 집합
    E_disc를 모은다. 수집 방식은 아래 §4.4 중 하나로 고정하고
    출력에 기록한다.
    budget / pagination 한계가 있으면 scope_complete=false.

(2) 잔류액 필터 (최종 후보 초안 C0)
    각 v ∈ V에 대해 residual(v)를 계산한다.
    |residual(v) - S| <= tolerance 이고 종착 조건을 만족하면
    C0에 넣는다.
    ※ gross related_in(v) ≈ S 만으로 C0에 넣지 않는다.

(3) 독립 연결 검증 → 최종 후보 C
    C0의 각 v에 대해, E_disc와 동일 객체/동일 파싱 결과를
    재사용하지 않는 방식으로 “시드→v 연결”을 검증한다 (§4.3).
    통과한 v만 C에 넣고 path 근거(TX hash·artifact pin)를 붙인다.
    실패하면 C0에서 제거하거나 excluded에 사유를 남긴다.

(4) 출력
    C 전부 = heuristic_candidates ( |C|==1 이어도 동일 )
    scope_complete / pagination / budget_exhausted 를 명시
    ownership·criminality = not_assessed
```

### 4.3 독립 연결 검증 (역추적이 중복이 되지 않게)

**금지:** `E_disc`에서 경로를 다시 읽어 “연결됨”이라고 선언하는 것.
그것은 discovery와 같은 증거라 검증이 아니다.

**허용 (하나 이상):**

| 방식 | 요지 |
|:---|:---|
| **A. 독립 raw 재조회·pin** | 후보 path의 각 TX를 별도 RPC(또는 별도 provider)로 재조회하고, 응답을 `artifact://sha256/...`로 pin한 뒤, pin된 raw만으로 from/to/value/asset이 path와 일치하는지 검증 |
| **B. 독립 edge 집합** | discovery와 다른 수집 파이프라인(예: discovery=trace, verify=indexed transfer list)으로 `E_indep`를 만들고, `E_indep` 위에서만 시드→v 경로 존재·금액 정합을 확인 |
| **C. 기존 SCAN bounded replay** | 후보 구간을 좁힌 뒤 기존 `trace_path` / `trace_remerge` offline package로 재실행 (패키지 raw가 discovery 메모리 그래프와 바이트 단위로 동일 복사본이면 안 됨 — Bridge와 같이 identical-bytes 위장 금지에 준함) |

검증 실패·미실시면 해당 주소는 최종 C에 넣지 않거나
`verification: pending_independent_check`로만 표시하고 제출 시
확정 어조를 쓰지 않는다.

### 4.4 수집 방식 고정 (일반 RPC만으로 부족)

일반 `eth_getLogs`/`eth_getBlockByNumber`만으로 임의 주소의
“전체 거래 목록”을 바로 열거할 수 없다. 구현·당일 운영 시
아래 중 **하나를 명시적으로 고르고** 출력 `collection_method`에 기록한다.

| ID | 방법 | 비고 |
|:---|:---|:---|
| `indexed_transfers` | 인덱싱된 transfer/내역 API (허용 Rules·출처 전제) | pagination 필수 기록 |
| `trace_subtree` | 시드 출발 TX/trace 기반 하위 호출·이체 확장 | archive/trace 지원 필요 |
| `block_window_scan` | from..to 블록을 스캔하며 시드 관련 이체만 수집 | 창이 커지면 budget 명확히 |

창을 넘는 미수집·페이지 잘림이 있으면 `scope_complete=false`,
`pagination_truncated=true` 또는 `budget_exhausted=true`.

### 4.5 tolerance 근거와 상한

| 항목 | 규칙 |
|:---|:---|
| 단위 | 항상 **raw 정수** (wei 등). 표시 ETH 부동소수로 비교 금지 |
| 기본 의미 | 동일 asset 이동 시 프로토콜/네트워크 수수료·먼지 상한 |
| 기록 | 출력에 `tolerance_raw`, `tolerance_rationale`(문구), `tolerance_cap_raw`(허용 상한) |
| 상한 | 구현·당일 모두 `tolerance_raw <= tolerance_cap_raw` 강제. cap을 넘는 “느슨한 일치”로 후보를 늘리지 않음 |
| 자산 변경 | 스왑·브리지로 asset이 바뀌면 본 방법의 S 근접 비교를 적용하지 않고 DEX/Bridge 경로로 이관 |

### 4.6 당일(사람+AI) 운영 순서

구현 전이거나 헬퍼 없이도 동일하다.

1. 문제를 채팅에 붙인다. `chain_id`·asset·S(raw)·창을 고정한다.
2. 수집 방식(§4.4)을 하나 고르고 순방향으로 주소·edge를 모은다.
3. **잔류액**과 종착 조건으로 초안 후보를 고른다 (gross 유입≈S 금지).
4. 각 초안 후보에 대해 **독립** raw/edge/SCAN replay로 시드 연결을 검증한다.
5. 남는 주소를 **전부** `heuristic_candidates`로 적는다. `|C|==1`이어도
   scope 완결 전 confirmed 금지.
6. 짧고 깨끗한 구간만 기존 `scan analyze` path/`remerge`로 재검증한다.

## 5. 입·출력 계약 (초안)

### 5.1 입력

| 필드 | 필수 | 설명 |
|:---|:---|:---|
| `seed` | 예 | 출발 주소 A |
| `chain_id` | 예 | 체인 ID |
| `asset_scope` | 예 | 예: `native` 또는 토큰 주소. 본 방법은 동일 asset 잔류 비교 |
| `amount_raw` | 예 | 출발 금액 S (정수 문자열) |
| `tolerance_raw` | 예 | 근접 허용 (정수). `tolerance_cap_raw` 이하여야 함 |
| `tolerance_rationale` | 예 | 수수료/먼지 등 근거 문구 |
| `tolerance_cap_raw` | 예 | 허용 상한 |
| `from_block` / `to_block` 또는 시간창 | 권장 | 탐색 창 |
| `collection_method` | 예 | `indexed_transfers` \| `trace_subtree` \| `block_window_scan` |
| `max_hops` / `max_nodes` / `max_edges` | 예 | 순방향 budget |
| edge/TX 패키지 또는 RPC | 택1 | 오프라인 pin 우선. 라이브는 env 이름·HTTPS·시크릿 리댁션 |

### 5.2 출력

```json
{
  "verification_level": "heuristic_candidates",
  "seed": "0x...",
  "chain_id": 1,
  "asset_scope": "native",
  "amount_target_raw": "...",
  "tolerance_raw": "...",
  "tolerance_cap_raw": "...",
  "tolerance_rationale": "native transfer fee/dust upper bound for this window",
  "collection_method": "trace_subtree",
  "scope_complete": false,
  "pagination_truncated": false,
  "budget_exhausted": false,
  "candidates": [
    {
      "address": "0x...",
      "related_in_raw": "...",
      "related_out_raw": "...",
      "residual_raw": "...",
      "terminus_kind": "no_further_related_outflow",
      "independent_verification": "raw_repin",
      "path_tx_hashes": ["0x..."],
      "path_artifact_pins": ["artifact://sha256/..."]
    }
  ],
  "excluded": [
    {
      "address": "0x...",
      "reason": "intermediate_passthrough_residual_near_zero"
    }
  ],
  "attribution": {
    "ownership": "not_assessed",
    "criminality": "not_assessed"
  }
}
```

`|candidates| == 1`이어도 `verification_level`은 `heuristic_candidates`를
유지한다. `scope_complete == true`이고 독립 검증·종착 근거가 모두
갖춰진 뒤에야 “유력 단일 후보” 정도의 문장을 쓸 수 있으며, 그래도
SCAN Benchmark `confirmed`와 동일시하지 않는다.

## 6. 위험과 한계 (정직하게)

| 위험 | 대응 |
|:---|:---|
| gross inflow ≈ S로 중간 주소 포함 | 잔류액·종착 조건 필수 (§4.1) |
| 같은 그래프 재검사로 “검증” | 독립 raw/edge/replay만 허용 (§4.3) |
| budget·pagination에 정답 미포함 | `budget_exhausted` / `scope_complete=false`, partial |
| 스왑·브리지로 자산·수량 변경 | 본 방법 중단, DEX/Bridge 경로로 이관 |
| 후보 0개 | 오답 단정 금지. 창·tolerance·수집 방식 점검 |
| 후보 여러 개 | **전부 제출**. 임의로 하나 선택 금지 |
| 대규모 그래프 | 완전·확정은 연구 과제. 본 방법은 **최종 후보 recall** 우선 |

## 7. 구현 전 체크리스트

- [ ] 후보 기준이 residual+terminus이며 gross inflow가 아니다
- [ ] 연결 검증이 discovery 그래프와 독립이다
- [ ] `|C|==1`이어도 heuristic_candidates를 유지한다
- [ ] 입력에 chain_id·asset_scope·amount_raw가 있다
- [ ] collection_method와 scope_complete/pagination/budget 필드가 있다
- [ ] tolerance 근거·상한이 기록된다
- [ ] production flow_path를 수정하지 않는다
- [ ] 착수 시 별도 승인 후 `scripts/contest/`에만 추가한다

## 8. Related Documents

- [Contest Day Problem-Solving Playbook](./75_CONTEST_DAY_PROBLEM_SOLVING_PLAYBOOK.md)
- [Contest Stabilization Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
- [Expected Problem Benchmark Report](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md)
- [FLOW path fixture `FX-FLOW-PATH-001`](./fixtures/FX-FLOW-PATH-001/)
- [FLOW remerge fixture `FX-FLOW-REMERGE-001`](./fixtures/FX-FLOW-REMERGE-001/)
