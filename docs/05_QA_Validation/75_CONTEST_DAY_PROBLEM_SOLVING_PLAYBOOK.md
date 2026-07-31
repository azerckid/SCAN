# Contest Day Problem-Solving Playbook

> Created: 2026-08-01 00:10
> Status: Active · Use starting 2026-08-02 09:00 KST

## 1. 목적

대회 중 이 채팅창에 문제가 들어오면, SCAN 코드를 그대로 실행할지, LLM이
직접 조사할지, 아니면 섞어서 할지를 매번 판단해야 한다. 이 문서는 그 판단
기준과, 이미 검증을 거쳐 확정된 "패턴별 함정 목록"을 한 곳에 모은다.

동일 fixture면 `scan analyze --evidence`를 우선한다. 대회 문제는 보통
우리 fixture와 다른 사례이므로, 새 입력은 이 문서의 **패턴별 함정 목록**을
체크리스트로 지키며 조사하고, 원본 확보·패키징이 가능하면 SCAN으로
재검증한다([66 Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md) 참고).
LLM은 분류·경로·해석을 돕되, on-chain 확정 사실을 발명하지 않는다.

## 2. 문제 접수 시 판단 순서

1. **패턴 분류**: 아래 §3 표에서 어느 패턴에 해당하는지 먼저 정한다.
   패턴이 안 보이면 §3.13(미지원 패턴)으로 간다.
2. **경로 선택**:
   - 확정 fixture와 **동일 사례**라면 → `scan analyze --evidence` 그대로 실행
     (드묾, 대회 문제는 우리 fixture와 다른 사례일 것).
   - **같은 프로토콜의 다른 사례**이고 raw 데이터 확보가 빠르면 → 직접
     조사하되 해당 패턴의 함정 목록을 체크리스트로 적용, 시간 남으면
     SCAN 스키마로 패키징해 재검증.
   - 시간이 부족하면 → 직접 조사만 하되, 함정 목록은 반드시 적용하고
     confirmed/heuristic/not_assessed 구분을 명시해 제출.
3. **제출 전 필수 확인**: §4 정직성 체크(공통) 전부 통과.

## 3. 패턴별 함정 목록

### 3.1 BASIC-EVM (주소·TX·블록 식별, 시점 상태)
- 길이만으로 주소/해시 판별 금지 — `eth_getCode`로 EOA/contract 구분
- fee는 `gas_used × effective_gas_price`, **gas_limit 아님**
- state 조회는 요청된 정확한 block에서, `latest`로 대체 금지
- decimals 정밀도 누락 주의

### 3.2 EVM-TOKEN (ERC-20 Transfer, 내부 ETH 이동)
- 다른 자산의 로그를 섞지 않기, 실패한 TX의 로그 채점 금지
- 0-value 이체를 정상 이체로 세지 않기
- pagination 누락으로 일부 로그만 보고 끝내지 않기
- internal call trace 잘림(truncated) 여부 확인, top-level로 대체 금지

### 3.3 EVM-NFT (ERC-721/1155 이동, 승인/운영자 변경)
- 토큰 ID를 topic이 아니라 data에서 잘못 읽지 않기 (721/1155 인코딩 차이)
- 다른 컨트랙트의 이벤트 혼입 금지, log 범위 누락 확인
- ERC-20 Transfer 시그니처와 721/1155 시그니처 혼동 금지
- batch(1155) 길이 불일치 확인

### 3.4 EVM-AUTH (approve/permit 권한 소비)
- allowance 소비를 실제 후속 전송과 연결해서 증명, 탈취 여부는 별도 판정
  (attribution 아님)

### 3.5 EVM-PROXY (구현체·관리자 변경 이력)
- admin 주소를 implementation으로 착각 금지
- beacon과 implementation slot 충돌 확인
- 과거 시점 조회 시 `latest` 상태로 대체 금지 (historical state missing이면 partial)

### 3.6 EVM-FREEZE (스테이블코인 동결)
- 이벤트와 상태(state) 교차 확인 필수, 한쪽만으로 단정 금지

### 3.7 FLOW (자금 흐름 추적, 분산-재병합)
- 시드 무관 edge 포함 금지, cycle 처리, budget truncation 시 partial
- 자산 불일치(asset mismatch) edge를 같은 흐름으로 묶지 않기
- 재병합: 무관한 external inflow를 흐름에 포함 금지, 잔여(residual) 음수 금지
- 다피해자 집계: 가격 데이터 없이 피해액 환산 금지 (assisted 경계)

### 3.8 SVC-DEX (DEX 스왑)
- 멀티홉 스왑의 순자산 변화를 전후 잔액이 아니라 이벤트로 재구성

### 3.9 SVC-BRG (브리지)
- **domain-separated matching 필수** — 금액·10초 시간차만으로 양단 연결 금지
  (domain collision 방지)
- 공식 이벤트 매칭 키 없이 tolerance만으로 매핑 금지
- amount 공식(수수료 차감) 불일치 확인

### 3.10 SVC-CEX (거래소 클러스터링)
- **단일 공통 상대(counterparty)만으로 confirmed 금지** — 최소 2개 입금
  출처가 같은 목적지로 모여야 함
- 라벨은 공식 government registry만, **Etherscan community tag는 label
  truth로 사용 금지**
- hot wallet ownership·criminality는 `not_assessed` 유지
- 두 provider 해시가 동일하면(위장) 거부 — 반드시 실제 다른 endpoint

### 3.11 SVC-MIX (믹서)
- deposit↔withdraw 연결은 **candidate/heuristic만**, 확정 사실로 절대 승격 금지
- single-exit(출금 1건)만으로 promotion 금지
- unlabeled pool은 label assertion 없이 완료 처리 금지

### 3.12 SVC-LEND (플래시론·청산)
- **다중 역할 주소**(예: liquidator이자 flashloan receiver) 처리 시 leg 누락
  금지 — 역할 필터링이 아니라 실제 자금 이동 기준으로 포함
- subject_address의 role 오분류 확인
- wrong protocol(Aave 아닌 다른 프로토콜과 혼동) 확인

### 3.13 BTC-UTXO / BTC-CJ (Bitcoin)
- fee = 합계 input − 합계 output, 불일치면 실패
- 동일 prevout 중복 사용(duplicate outpoint) 거부
- PRIMARY/VERIFY가 **같은 wire projection의 복사본이면 안 됨** — 반드시
  독립된 두 endpoint에서 재조회
- change/CoinJoin은 heuristic candidate만, "동일 금액 출력" 하나로
  확정 금지, "complete control(전체 입력 소유)" 없이 CoinJoin 확정 금지

### 3.14 OSINT-LABEL/SANCTIONS/ENS
- 라벨 충돌 시 자동 병합 금지, 공식 이력 vs 최신 상태 구분
  (`latest`로 과거 시점 대체 금지)
- 제재(SANCTIONS) 이력의 시간 순서 뒤집기 금지, 간접 연루를 직접 제재로
  격상 금지, 범죄성으로 자동 승격 금지
- ENS: 정방향/역방향 조회 불일치 시 subject 바꿔치기 금지, ownership으로
  자동 승격 금지

### 3.15 ACTOR-REL (공통 자금원, 허브)
- 공용 허브(Public hub) 주소를 특정 subject와 병합 금지
- 최소 2명의 non-seed 배제, prehistory(과거 이력) 없이 "첫 자금원" 단정 금지

### 3.16 CRIME-* / MIXED-* (사건 조합)
- 기술 사실(누가 얼마를 언제)과 외부 귀속(누구 소유, 범죄 의도)을 분리
- 서로 다른 사건의 fixture를 억지로 하나의 흐름으로 합성 금지
  (`MIXED-XCHAIN-001`이 unsupported로 남은 이유)
- seed substitution, timeline 재정렬, source hash 변조 거부
- 확정 안 된 부분은 continuous scope 미스캔으로 partial 유지, 전체 사건
  완결로 과장 금지

## 4. 제출 전 공통 정직성 체크

- [ ] 확정 사실(confirmed) / 추정(heuristic·candidate) / 미평가(not_assessed)를
      명확히 구분해서 답했는가
- [ ] ownership·criminality·intent를 증거 없이 단정하지 않았는가
- [ ] 단일 근거(단일 상대, 단일 출력, 단일 provider)만으로 확정하지
      않았는가
- [ ] 라벨을 공식 출처가 아닌 커뮤니티 태그에서 가져오지 않았는가
- [ ] fee/합계 계산 방식(gas_used, input−output 등)이 맞는가

## 5. Related Documents

- [Contest Stabilization Runbook](./66_CONTEST_STABILIZATION_RUNBOOK.md)
- [Reference Fixtures](./01_REFERENCE_FIXTURES.md)
- [Expected Problem Benchmark Report](./22_EXPECTED_PROBLEM_BENCHMARK_REPORT.md)
