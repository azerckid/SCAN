# SCAN 2026 오픈소스 포렌식 사전조사
> Created: 2026-07-26 22:38
> Last Updated: 2026-07-26 22:54
> Status: Draft 1 · Initial Survey

## 1. 문서 목적

이 문서는 SCAN 분석 도구의 기능을 직접 구현하기 전에 GitHub와 공식
프로젝트 문서에서 기존 오픈소스를 조사하고, 재사용 여부를 증거와 함께
결정하기 위한 구현 전 Gate다.

목표는 오픈소스를 많이 채택하는 것이 아니다. 이미 검증된 수집·정규화·추적·
라벨·시각화 기능을 불필요하게 다시 만들지 않고, SCAN에서 직접 만들어야 할
문제별 분석·증거 연결·빠른 CLI·재현 가능한 보고서에 시간을 집중하는 것이다.

이 문서는 코드 채택이나 dependency 추가를 승인하지 않는다. 공식 대회 규정,
라이선스, 고정 commit, 설치 재현과 fixture 검증을 통과한 결정만 구현 입력이
된다.

## 2. 현재 판단

### 2.1 기존 검토의 공백

기존 기술 문서는 HTTPX, web3.py, Blockscout API, SQLite, ABI utility처럼
개별 구성요소를 비교했다. 그러나 범용 블록체인 포렌식·추적 프로젝트를
기능별로 검색하고 `Adopt / Wrap / Borrow / Build / Reject`로 판정한 기록은
없었다.

따라서 현재 기술 선택은 폐기하지 않되, 관련 기능 구현 전에 이 문서의
오픈소스 사전조사 결과로 다시 검증한다.

### 2.2 직접 구현 금지 원칙

아래 조건이 모두 충족되지 않은 기능은 직접 구현을 시작하지 않는다.

1. 기능 코드와 검색 범위가 정의되어 있다.
2. GitHub repository·공식 문서·package registry를 검색했다.
3. 후보를 최소 3개 비교하거나, 후보 부족의 검색어·조회일·부족 사유를 남겼다.
4. 라이선스·유지보수·보안·데이터 의존·설치 비용을 확인했다.
5. 적용 가능한 후보는 confirmed fixture 또는 소규모 공개 사례로 검증했다.
6. 최종 결정과 제외 이유를 `OSSR-*` 기록으로 남겼다.
7. SCAN 공식 규정에서 OSS·사전 제작 도구 사용 범위를 확인했다.

## 3. 상태와 결정 체계

### 3.1 조사 상태

| 상태 | 의미 |
|:---|:---|
| `discovered` | repository 존재와 대략적 기능만 확인 |
| `screened` | 공식 README·활동·라이선스·운영 요구를 확인 |
| `bakeoff_ready` | 고정 commit·설치 절차·검증 입력을 확정 |
| `verified` | fixture 또는 공개 사례 재현을 통과 |
| `deferred` | 현재 단계 밖이거나 규정·데이터·환경을 기다림 |
| `rejected` | 현재 범위에서 사용하지 않는 이유를 확정 |

`screened`는 정확성 검증이 끝났다는 뜻이 아니다. dependency로 채택하려면
원칙적으로 `verified`까지 올라가야 한다.

### 3.2 최종 결정

| 결정 | 적용 의미 |
|:---|:---|
| `ADOPT` | 고정 버전 dependency 또는 실행 도구로 사용 |
| `WRAP` | 외부 API·CLI·library를 port 뒤에 감싸 사용 |
| `BORROW` | 데이터 모델·알고리즘·테스트 아이디어만 참고해 독립 구현 |
| `BUILD` | 적합 후보가 없어 SCAN 요구사항에 맞춰 직접 구현 |
| `REJECT` | 라이선스·정확성·유지보수·운영비·규정 문제로 제외 |

하나의 후보에 기능별로 다른 결정을 내릴 수 있다. 예를 들어 Blockscout
공개 API는 `WRAP`하되, 대회용 로컬 self-host는 `REJECT`할 수 있다.

## 4. 필수 조사 범위

### 4.1 기능 그룹

| 조사 ID | 기능 코드 | 조사 대상 |
|:---|:---|:---|
| `OSSR-P0-COLLECT` | `EVM-TX`, `EVM-LOG`, `EVM-STATE`, `EVM-TRACE` | RPC·explorer·ETL 수집과 raw 보존 |
| `OSSR-P0-CORE` | `RECON`, `BASE-CACHE`, `BASE-PROVENANCE`, `BASE-EXPORT` | 정합·캐시·증거·보고서 |
| `OSSR-P1-PATH` | `PATH` | 다단계 자금 흐름·그래프 탐색 |
| `OSSR-P1-DECODE` | `DECODE`, `AUTH-DECODE`, `FREEZE` | ABI·프로토콜·권한·상태 해석 |
| `OSSR-P1-LABEL` | `LABEL` | 주소 라벨·주체·출처·신뢰도 |
| `OSSR-P1-VIZ` | `VIZ` | 자금 흐름 그래프·타임라인 |
| `OSSR-P2-BTC` | `BTC-UTXO` | UTXO 수집·추적·클러스터 |
| `OSSR-P2-XCHAIN` | `XCHAIN`, `BRIDGE` | 브리지 양단·크로스체인 연결 |
| `OSSR-P2-JUDGMENT` | `OSINT`, `HEUR` | 외부 맥락·휴리스틱·반례 |
| `OSSR-P3-SPECIAL` | `NFT-DECODE`, `PROXY`, `MIXER`, `DEFI-LEND`, `PRICE`, `LP-RUG` | 전문 프로토콜 어댑터 |

### 4.2 검색 증거

각 조사 ID는 다음을 보존한다.

- 검색어와 검색 대상(GitHub repository/code, 공식 문서, package registry)
- 조회 시각과 검색 결과 수
- 후보 repository URL, owner, default branch, 고정 commit SHA
- release·최종 commit·archived 여부
- 공식 README에서 확인한 기능과 제한
- license 파일 URL·SPDX 또는 custom license 판정
- 설치·DB·노드·API key·인덱싱·네트워크 요구
- 채택 후보와 제외 후보

별 개수는 발견 보조 정보일 뿐 채택 기준이 아니다.

### 4.3 AI·ML 추가 조사 범위

GitHub repository 조사와 별도로 Hugging Face의 Models, Datasets, Spaces를
검색한다. “crypto”라는 이름만으로 포렌식 후보로 분류하지 않고 다음 세
유형을 구분한다.

| 유형 | 후보 ID 접두사 | 조사 대상 |
|:---|:---|:---|
| 실행 모델 | `HF-MODEL-*` | 텍스트·거래·주소·그래프 분류 모델과 model card |
| 학습·검증 데이터 | `HF-DATASET-*` | 거래 그래프, 불법 라벨, 주소 주석, 공격 사례 |
| 응용 데모 | `HF-SPACE-*` | AML·사기 탐지·포렌식 UI와 공개 source |

모델·Space의 출력은 온체인 사실과 동일하게 취급하지 않는다. 후보 순위,
이상 점수, 군집·라벨 제안처럼 오탐 가능성이 있는 값은 `heuristic`으로
분류하고, RPC·log·state·trace와 공식 출처로 다시 확인할 수 있어야 한다.

## 5. 평가 기준

후보는 100점 척도로 비교한다. 점수만으로 결정하지 않으며, 라이선스·규정·
정확성 차단 조건을 우선한다.

| 기준 | 가중치 | 판단 질문 |
|:---|---:|:---|
| 기능·fixture 적합성 | 25 | 필요한 입력·출력과 exact-match를 충족하는가 |
| 증거·재현성 | 15 | raw 응답·출처·block tag·hash를 보존하는가 |
| 설치·운영 단순성 | 15 | 대회 전에 설치·복구·이동 가능한가 |
| 유지보수·보안 | 10 | 최근 활동·release·test·보안 정책이 있는가 |
| 라이선스·재배포 | 15 | 사용·수정·배포·고지 조건을 충족하는가 |
| 확장·결합도 | 10 | port 뒤에 격리하고 기능별 교체가 가능한가 |
| 데이터·규정 위험 | 10 | API key·유료 데이터·외부 전송·대회 규정 위험이 낮은가 |

### 5.1 차단 조건

다음 중 하나면 점수와 관계없이 `ADOPT`할 수 없다.

- license가 없거나 사용 조건을 설명할 수 없음
- repository code가 secret·문제 데이터·답안을 외부로 전송
- fixture의 결정적 값과 불일치하거나 원본 근거로 돌아갈 수 없음
- 사전 제작 도구·API·상용 데이터 규정에 위반
- 유지보수 중단 상태인데 호환성·보안 위험을 격리할 수 없음
- 설치·인덱싱 시간이 대회 준비 또는 복구 시간 안에 들어오지 않음

### 5.2 AI·데이터셋 Screening Gate

AI·ML 후보는 공통 평가에 더해 아래 항목을 모두 기록한다.

- model card·dataset card의 의도된 사용·한계·학습 데이터 공개 수준
- repository license와 원천 데이터의 재배포·상업·파생 사용 조건
- 라벨 생성 주체·근거·시점과 `licit / illicit / unknown` 의미
- 주소·거래·시간이 train과 test에 중복되는 데이터 누출 가능성
- 무작위 분할이 아닌 시간 분할 또는 미래 데이터 holdout 가능성
- 클래스 불균형, precision·recall·PR-AUC와 false positive·negative
- 모델·토크나이저·특성 목록·고정 revision·파일 hash
- offline inference 가능 여부, 외부 전송·secret·GPU·메모리 요구
- 같은 입력의 재현성과 출력 score·threshold·모델 버전 보존 여부

다음 조건에서는 정확도 수치와 관계없이 SCAN의 확정 증거 생성에 사용할 수
없다.

- 데이터·라벨 출처를 설명할 수 없음
- license가 없거나 원천 데이터 조건과 충돌
- 평가 분할·표본 수·오탐·미탐 정보를 확인할 수 없음
- 모델 판단에서 원본 거래·주소·근거로 역추적할 수 없음
- 범죄·탈취·제재 여부를 단일 score만으로 확정

## 6. 초기 후보 기준선

조회 시각은 2026-07-26 22:20~22:35 KST다. GitHub API의 repository
metadata와 기본 branch commit, 공식 README를 확인했다. 별 개수와 issue
수는 변동성이 높아 규범 필드로 고정하지 않는다.

### 6.1 검색 기록

| 검색어 | 검색 대상 | 확인 결과 |
|:---|:---|:---|
| `blockchain forensics transaction tracing` | GitHub repository search, 상위 10개 | 소규모 사례·목록형 repository가 많아 성숙 프로젝트 이름을 추가 탐색 |
| `GraphSense cryptocurrency analytics` | GitHub repository search, 1개 | `graphsense-lib`와 조직 내 dashboard 확인 |
| `BlockSci blockchain analysis` | GitHub repository search, 5개 | 원본 `citp/BlockSci`와 fork 구분 |
| `ethereum-etl blockchain data` | GitHub repository search, 5개 | `blockchain-etl` 조직의 EVM·Bitcoin ETL 확인 |
| `Blockscout explorer` | GitHub repository search, 5개 | 원본 `blockscout/blockscout`와 chain별 fork 구분 |

검색 결과 상위 노출만으로 후보를 확정하지 않았다. 원본 조직·공식 README·
license·기본 branch commit을 다시 확인한 프로젝트만 아래 기준선에 넣었다.

### 6.2 후보 등록부

| 후보 ID | Repository·고정 기준 | 활동·라이선스 | 관련 기능 | 초기 상태 |
|:---|:---|:---|:---|:---|
| `OSS-GS-LIB` | [graphsense-lib](https://github.com/graphsense/graphsense-lib), `eb79aa38b98181384fc6716b8dc20f686f6728d2` | 2026-07-14 default branch commit, MIT | ingest, address·tx, tag·cluster, REST·CLI, money-flow watch | screened |
| `OSS-GS-UI` | [graphsense-dashboard](https://github.com/graphsense/graphsense-dashboard), `cea09aeea309655f1b300cc887c9b6f65e064386` | 2026-07-17 commit, MIT | interactive crypto analysis UI·graph | screened |
| `OSS-BLOCKSCI` | [BlockSci](https://github.com/citp/BlockSci), `14ccc9358443b2eb5730bb2902c4b11ab7928abf` | 공식 README가 2020-11 이후 유지보수 중단 명시, GPL-3.0 | Bitcoin 중심 고속 분석·Python binding | rejected |
| `OSS-ETH-ETL` | [ethereum-etl](https://github.com/blockchain-etl/ethereum-etl), `909650d64176fd26a0920fda8884ffc7e8307822` | 2026-01-25 commit, MIT | block·tx·receipt·log·token transfer·trace export | screened |
| `OSS-BTC-ETL` | [bitcoin-etl](https://github.com/blockchain-etl/bitcoin-etl), `9d773d9cf9b297a45e82063e16a094c5b878ec4d` | 2025-05-02 commit, MIT | Bitcoin 계열 UTXO ETL | deferred |
| `OSS-BLOCKSCOUT` | [Blockscout](https://github.com/blockscout/blockscout), `2cbdede30e4b49bfee8cbfa8897d6dab494d84ab` | 2026-07-24 commit, custom Blockscout Software Licence | EVM tx·account·contract·token·internal call API/UI | screened |
| `OSS-SPELLBOOK` | [Dune Spellbook](https://github.com/duneanalytics/spellbook), `f8e655c11eec6d11d2c1a1d3081e8511b9aa0395` | 2026-07-23 commit, GitHub SPDX 자동 판정 없음 | 공개 SQL model·protocol·label 참고 | discovered |

commit 날짜는 GitHub API가 반환한 기본 branch commit 기준이다. repository
페이지의 “updated” 시각이나 별 개수와 혼동하지 않는다.

기본 branch는 GraphSense 2개·BlockSci·Bitcoin ETL·Blockscout가 `master`,
Ethereum ETL이 `develop`, Dune Spellbook이 `main`이다. 채택 검증에서는
branch 이름이 아니라 표의 commit SHA를 사용한다.

### 6.3 Hugging Face 검색 기록

조회 시각은 2026-07-26 22:42~22:52 KST다. Hugging Face 검색과 공개 API,
model·dataset card, Space source tree를 확인했다. 다운로드·like·runtime은
변동 값이므로 후보 성숙도의 보조 정보로만 사용한다.

| 검색어 | 대상 | 확인 결과 |
|:---|:---|:---|
| `blockchain forensics`, `crypto AML` | Models·Spaces | 완성형 모델은 드물고 소규모 AML API·정적 데모가 노출됨 |
| `ethereum fraud`, `wallet fraud` | Models·Datasets·Spaces | 주소 활동 데이터와 CSV 학습 데모 중심 |
| `bitcoin money laundering`, `elliptic bitcoin` | Models·Datasets | Elliptic 계열 graph dataset이 핵심 후보 |
| `illicit transaction`, `transaction graph fraud` | Models·Datasets | 배포 모델보다 multigraph 학습 데이터가 많음 |
| `crypto scam` | Models·Spaces | Discord·URL·문장 분류가 많아 온체인 추적과 분리 필요 |
| `DeFi hack`, `smart contract vulnerability` | Datasets | 공격 사례·contract audit 데이터이며 자금 흐름 포렌식과 인접 영역 |

검색 결과에서 바로 사용할 수 있는 성숙한 온체인 포렌식 foundation model은
확인하지 못했다. 현재 가치가 큰 자산은 실행 모델보다 benchmark·학습용
데이터셋과 설계 참고용 source다.

### 6.4 Hugging Face 후보 등록부

| 후보 ID | 공개 자산·확인 기준 | license·운영 관찰 | 관련 기능 | 초기 상태 |
|:---|:---|:---|:---|:---|
| `HF-SPACE-AML-001` | [Crypto AML Investigator API](https://huggingface.co/spaces/uzairsaleemdev/crypto-aml-api), revision `8a73402939bf791e846dab7bdfb2bfee422f64c7` | card license 미표기·LICENSE 파일 미확인, 조회 시 runtime error, Supabase·Neo4j secret 요구 | Elliptic++ ingest, entity resolution, clustering, logistic·GraphSAGE | screened |
| `HF-DATASET-BTC-001` | [Elliptic Bitcoin Dataset](https://huggingface.co/datasets/yhoma/elliptic-bitcoin-dataset) | card metadata MIT, 원천 데이터 조건·라벨 provenance 재확인 필요 | `BTC-UTXO`, `HEUR`, graph classification | discovered |
| `HF-DATASET-EVM-001` | [Ethereum Fraud Dataset by Activity](https://huggingface.co/datasets/fesevu/ethereum_fraud_dataset_by_activity) | CC-BY-4.0, 대규모 거래 활동과 별도 fraud label pipeline | `EVM-TX`, `PATH`, `HEUR`, `LABEL` | discovered |
| `HF-DATASET-LABEL-001` | [Crypto Address Annotation 10K](https://huggingface.co/datasets/Humanbased-AI/Crypto-Address-Annotation-10K) | OpenRAIL 계열 metadata, 주소별 근거·시점·오탐 검증 필요 | `LABEL`, `OSINT` | discovered |
| `HF-DATASET-GRAPH-001` | [Crypto Illicit Account Detection Multigraphs](https://huggingface.co/datasets/Tommy-DING/crypto-illicit-account-detection-multigraphs) | license metadata `other`, 사용 조건 확인 전 재사용 금지 | `PATH`, `HEUR`, `BTC-UTXO` | discovered |
| `HF-DATASET-DEFI-001` | [DeFiHackLabs Dataset](https://huggingface.co/datasets/akshaynexus/DeFiHackLabs-Dataset) | MIT metadata, 사건·코드·정답 연결 품질 검증 필요 | `DEFI-LEND`, `PRICE`, `LP-RUG` | deferred |
| `HF-MODEL-TEXT-001` | [Discord Crypto Scam Detector](https://huggingface.co/rzeydelis/discord-crypto-scam-detector) | Apache-2.0, self-reported accuracy 0.6667, intended use·training data 설명 미비 | Discord 문장 `OSINT` 보조 | rejected |
| `HF-SPACE-EVM-001` | [Ethereum Fraud Detection](https://huggingface.co/spaces/SujalPatidar24/Ethereum_Fraud_Detection), revision `a20de62016c27dc9e32959335c1c504c0a8a9aee` | license 미표기, CSV upload·SMOTE·Random Forest 교육형 흐름 | tabular `HEUR` 실험 | rejected |
| `HF-SPACE-VIZ-001` | [ChainSleuth Pro](https://huggingface.co/spaces/sirbrentmichaelskoda/chainsleuth-pro-blockchain-forensics), revision `56b7a1f57fd1d938a69142c565b6b1def801a45e` | 정적 DeepSite 프로젝트, 검증된 backend·model card 없음 | 포렌식 화면·`VIZ` 참고 | rejected |

표의 license는 Hugging Face card metadata 또는 공개 source tree의 1차 관찰이다.
dependency·학습·재배포 결정 전 원천 repository와 데이터 제공자의 실제 조건을
별도로 확인한다.

## 7. 초기 기능 분석

### 7.1 GraphSense

GraphSense Library는 Python library, CLI, 데이터 ingest, address·transaction
조회, tag·cluster, REST와 money-flow watch를 제공한다. 기능 범위는 현재
구상한 포렌식 코어와 가장 가깝다.

그러나 전체 backend는 Cassandra, PostgreSQL TagStore와 변환 작업에서
Spark 계열 구성요소를 요구한다. 짧은 대회 준비와 로컬 복구에는 무거울 수
있다.

초기 판단:

- address·cluster·tag·path 모델: `BORROW` 후보
- 원격 또는 준비된 GraphSense API: 규정·가용성 확인 후 `WRAP` 후보
- 전체 stack self-host: V1 `DEFER`
- dashboard graph interaction: P1 `VIZ`의 `BORROW` 후보

### 7.2 BlockSci

BlockSci는 Bitcoin 계열 append-only 분석에 최적화한 C++ core와 Python
binding을 제공한다. 그러나 공식 README가 2020년 11월 이후 적극적인 개발과
지원을 중단했으며 호환성·오류 위험을 직접 경고한다.

초기 판단:

- V1 runtime·dependency: `REJECT`
- UTXO 고속 순회·메모리 모델 연구: `BORROW`
- GPL-3.0 code 복사·결합: Project LICENSE 결정 전 금지

### 7.3 Ethereum ETL

Ethereum ETL은 blocks, transactions, receipts, logs, ERC20·ERC721 transfers,
traces를 CSV와 관계형 형식으로 추출한다. 수집·정규화 코드를 전부 다시
작성하지 않기 위한 유력 비교 대상이다.

초기 판단:

- field mapping·batch export·trace 수집: `BORROW / WRAP` 후보
- 현재 P0 raw body hash·source fallback·historical state 계약: 별도 검증 필요
- `OSS-EVM-COLLECT-001` bake-off 전 core dependency 채택 금지

### 7.4 Blockscout

Blockscout 공개 API는 세 confirmed fixture의 internal transaction, decoded
call과 token transfer 교차검증에 이미 사용했다. 공개 instance API를 port
뒤에서 사용하는 것과 Blockscout 전체 server code를 self-host하는 것은
다른 결정이다.

초기 판단:

- 공개 API adapter: 현재 `WRAP` 유지, provider별 약관·rate limit 확인
- 전체 explorer self-host: V1 `REJECT`
- server source 재사용: custom license 검토 전 금지

### 7.5 Bitcoin ETL·Dune Spellbook

Bitcoin ETL은 `BTC-UTXO`가 P2로 승격될 때 BlockSci 대체 후보로 검증한다.
Dune Spellbook은 protocol SQL과 라벨 taxonomy 참고 가치가 있지만 Dune
실행 환경·외부 서비스·데이터 갱신·라이선스·대회 규정을 분리해야 한다.

두 후보 모두 현재 V1 dependency가 아니다.

### 7.6 Hugging Face AI·데이터셋

`HF-SPACE-AML-001`은 이번 조사에서 SCAN 구상과 가장 가까운 공개 사례다.
FastAPI, Elliptic++ loader, 지갑 군집·entity resolution, hand-aggregated
feature baseline과 PyTorch Geometric GraphSAGE source가 공개되어 있다.
시간 기준 train·test 분할을 고려한 점도 참고 가치가 있다.

그러나 조회 시 Space runtime이 오류 상태였고 card에 license가 표시되지
않았으며, 전체 실행에는 Supabase·Neo4j 설정이 필요하다. 따라서 source
복사나 dependency 채택은 금지하고 다음만 `BORROW` 후보로 둔다.

- transaction graph와 wallet graph를 분리하는 model boundary
- 시간 분할·unknown label 제외·class imbalance 처리 점검 항목
- offline train artifact와 online score 단계를 분리하는 구조
- entity resolution·cluster·risk score를 확정 사실과 분리하는 API 개념

`HF-DATASET-BTC-001`과 `HF-DATASET-EVM-001`은 모델을 가져오기보다 후보
알고리즘의 비교시험과 예상문제 확장에 유용하다. 다만 라벨이 수집 시점 이후의
정보를 포함하거나 같은 주소가 train·test에 함께 들어가면 성능이 과대평가될
수 있다. 시간 분할과 주소·거래 중복 검사를 통과하기 전에는 정확도 수치를
채택 근거로 사용하지 않는다.

`HF-MODEL-TEXT-001`은 Discord 문장 분류기이므로 온체인 path·allowance·freeze
사실을 판정할 수 없다. 공개 성능과 설명 수준도 낮아 V1에서 제외한다.
`HF-SPACE-EVM-001`과 `HF-SPACE-VIZ-001`도 교육·화면 참고 범위를 넘는
증거가 없어 runtime이나 dependency로 사용하지 않는다.

초기 단계별 판단:

- P0·V1 DEX·AUTH·FREEZE: AI dependency 없음, RPC·log·state·공식 출처 우선
- P1 `PATH`·`LABEL`: deterministic graph와 출처 라벨 구현 후 ML 비교 가능
- P2 `HEUR`·`BTC-UTXO`: Elliptic 계열 dataset으로 benchmark 후보
- P3 DeFi 전문 기능: DeFiHackLabs 사건을 fixture 후보 발굴에만 우선 사용

## 8. Fixture Bake-off 규칙

### 8.1 공통 절차

1. 후보 repository와 dependency를 고정 commit 또는 exact version으로 설치한다.
2. 네트워크·API key·DB·인덱싱·디스크 요구를 기록한다.
3. candidate adapter를 SCAN Analysis I/O 바깥에서 격리 실행한다.
4. DEX·AUTH·FREEZE 중 적용 가능한 confirmed fixture를 입력한다.
5. expected의 raw integer·boolean·주소·block·log index를 대조한다.
6. raw response, source, retrieved_at, block tag, hash 보존 여부를 확인한다.
7. cold·warm 실행 시간, 외부 호출 수, 실패·재시도 동작을 기록한다.
8. `ADOPT / WRAP / BORROW / BUILD / REJECT` 결정을 남긴다.

### 8.2 통과 조건

- 결정적 fixture 값 exact match
- 결과에서 원본 evidence와 source로 역추적 가능
- secret·Authorization·사용자 절대 경로 비노출
- fallback·partial·failed를 성공으로 오표시하지 않음
- 설치와 재실행 절차가 clean environment에서 재현
- license·notice·source pin 기록 완료

fixture에 적용할 수 없는 후보는 기능별 공개 사례와 예상 출력 계약을 먼저
만들고 `verified`가 아닌 `deferred`로 유지한다.

### 8.3 AI·ML Bake-off 추가 조건

AI 후보는 공통 절차에 다음을 추가한다.

1. 결정적 규칙 또는 단순 통계 baseline을 먼저 만든다.
2. 주소·거래·시간 중복을 제거한 temporal holdout을 고정한다.
3. precision·recall·PR-AUC와 false positive·negative 사례를 함께 기록한다.
4. 같은 model revision·feature schema·threshold로 재실행한다.
5. 결과에 `classification: heuristic`, score, threshold, model revision,
   feature version과 source dataset revision을 기록한다.
6. 상위 후보에서 원본 transaction·address·evidence로 drill-down 가능한지
   확인한다.
7. AI를 끄거나 사용할 수 없어도 결정적 포렌식 경로가 동작하는지 확인한다.

ML 후보는 baseline 대비 재현 가능한 개선이 있을 때만 `ADOPT / WRAP` 후보가
된다. 개선이 없거나 설명·근거를 보존할 수 없으면 `BORROW / REJECT`로 둔다.

## 9. 초기 결정과 남은 조사

| 결정 ID | 기능 | 현재 결정 | 다음 증거 |
|:---|:---|:---|:---|
| `OSS-EVM-COLLECT-001` | EVM 수집·정규화 | HTTPX 직접 adapter와 Ethereum ETL 비교 필요 | DEX·AUTH·FREEZE 수집 bake-off |
| `OSS-EVM-EXPLORER-001` | explorer 보조 | Blockscout 공개 API `WRAP` 유지 | 공식 API 약관·rate limit·provider fallback |
| `OSS-PATH-001` | 다단계 경로 | GraphSense model·API 우선 조사 | 작은 공개 주소 graph와 PATH fixture |
| `OSS-LABEL-001` | 라벨·클러스터 | GraphSense TagStore·Spellbook 비교 | 출처·신뢰도·주소 명시 fixture |
| `OSS-VIZ-001` | 그래프·타임라인 | GraphSense Dashboard 설계 조사 | 80-column CLI와 graph export 경계 |
| `OSS-BTC-001` | BTC UTXO | Bitcoin ETL 검증, BlockSci runtime 제외 | BTC fixture confirmed 승격 |
| `OSS-XCHAIN-001` | 브리지·크로스체인 | 후보 미조사 | bridge 양단 fixture와 후보 3개 |
| `OSS-DECODE-001` | ABI·프로토콜 해석 | 현재 utility 외 전문 후보 미조사 | DEX·AUTH·FREEZE decoder 비교 |
| `OSS-ML-HEUR-001` | 주소·거래 위험 점수 | P0·V1 제외, HF dataset 비교만 허용 | temporal holdout·baseline·오탐/미탐 |
| `OSS-ML-LABEL-001` | AI 라벨 후보 | 확정 라벨과 분리한 `BORROW` 후보 | 주소별 출처·시점·confidence audit |
| `OSS-ML-DEFI-001` | DeFi 사건·공격 분류 | P3 `DEFER` | 문제은행 사건 mapping과 fixture 후보 |

초기 조사는 후보 발견과 1차 screening이다. 이 표의 “비교 필요”와 “미조사”가
닫히기 전 해당 기능을 직접 구현하지 않는다.

## 10. 구현 전 Gate

### 10.1 전체 Gate

- [x] 범용 포렌식 오픈소스 검토 공백을 문서화했다.
- [x] 초기 후보 7개의 repository·commit·활동·license 기준선을 기록했다.
- [x] Hugging Face 모델·데이터셋·Space 9개의 초기 후보를 분리 기록했다.
- [x] 결정 상태와 `ADOPT / WRAP / BORROW / BUILD / REJECT` 의미를 정의했다.
- [x] AI 결과를 확정 증거와 분리하고 ML Screening Gate를 정의했다.
- [ ] P0·V1 관련 `OSS-*` 결정을 fixture 증거와 함께 확정한다.
- [ ] 공식 규정에서 OSS·사전 제작 도구·외부 API 사용 범위를 확인한다.
- [ ] 채택 dependency의 고정 버전·license notice·설치 명령을 확정한다.
- [ ] Backlog 각 구현 작업의 관련 `OSS-*` 결정을 연결한다.

### 10.2 기능별 완료

- [ ] `OSSR-P0-COLLECT`
- [ ] `OSSR-P0-CORE`
- [ ] `OSSR-P1-PATH`
- [ ] `OSSR-P1-DECODE`
- [ ] `OSSR-P1-LABEL`
- [ ] `OSSR-P1-VIZ`
- [ ] `OSSR-P2-BTC`
- [ ] `OSSR-P2-XCHAIN`
- [ ] `OSSR-P2-JUDGMENT`
- [ ] `OSSR-P3-SPECIAL`

P0·V1 구현 시작에는 P0·V1 관련 조사만 필수다. P2·P3 조사는 해당 단계
승격 전까지 `deferred`로 둘 수 있다.

## 11. 365 글로벌 평가 기준

| 기준 | 이 문서의 기여 |
|:---|:---|
| Functionality | fixture로 오픈소스 정확성과 실패 동작 검증 |
| Potential Impact | 재사용으로 구현 시간을 줄이고 포렌식 코어 범위 확대 |
| Novelty | 범용 수집 재개발 대신 evidence-first 문제 해결에 집중 |
| UX | 설치·복구·cold·warm 시간과 CLI 경계를 평가 |
| Open-source | commit·license·notice·재현 명령을 채택 전 고정 |
| Business Plan | self-host·API·상용 데이터 운영비와 종속 위험 분리 |

## 12. Related Documents

- **Concept_Design**: [예상문제 은행](../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 조사 대상 문제·기능 범위
- **Concept_Design**: [분석 도구 기능 우선순위](../01_Concept_Design/04_SCAN_2026_TOOL_PRIORITY.md) - P0~P3 기능 코드와 단계 제한
- **Concept_Design**: [공식 규정 Register](../01_Concept_Design/03_SCAN_2026_RULES_REGISTER.md) - OSS·사전 도구·API 허용 상태
- **UI_Screens**: [CLI Screen Flow](../02_UI_Screens/00_SCREEN_FLOW.md) - 재사용 도구를 감싸는 사용자 흐름
- **Technical_Specs**: [데이터 소스 등록부](./01_DATA_SOURCE_REGISTRY.md) - API·provider 제약과 provenance
- **Technical_Specs**: [P0·V1 도구 요구사항](./03_SCAN_2026_TOOL_REQUIREMENTS.md) - 후보가 충족해야 할 규범 계약
- **Technical_Specs**: [기술 선택 기록](./04_SCAN_2026_TECHNOLOGY_DECISION.md) - 채택·보류 기술 재검토 대상
- **Technical_Specs**: [Analysis I/O Schema](./05_ANALYSIS_IO_SCHEMA.md) - wrapper 출력·증거 참조 계약
- **Logic_Progress**: [P0·V1 구현 Backlog](../04_Logic_Progress/00_BACKLOG.md) - 구현 전 OSSR Gate
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - 문서 완료·구현 승인 분리
- **QA_Validation**: [Reference Fixtures](../05_QA_Validation/01_REFERENCE_FIXTURES.md) - 후보 bake-off의 confirmed 기준값
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 정확성·보안·회귀 조건
