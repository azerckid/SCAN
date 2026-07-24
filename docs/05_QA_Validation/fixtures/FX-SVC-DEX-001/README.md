# Fixture: FX-SVC-DEX-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-25 02:49
> Status: Verifying

## 1. 목적

실제 EVM DEX 스왑 한 건을 기준으로 로그 수집, 이벤트 디코딩, 입력·출력
자산 정합, DEX 메타데이터 연결과 증거 출력을 검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `SVC-DEX-001` |
| 상태 | 검증 중 (`verifying`) |
| 체인 | Ethereum (`chain_id` 1) |
| TX | `0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5` |
| 스왑 | Uniswap V2 USDC → WETH (단일 홉) 후 ETH unwrap |
| 입력 | USDC `25000000000` raw (6 decimals = 25000) |
| 풀 출력 | WETH `14449515027026387018` raw |
| 사용자 최종 출력 | ETH `14449515027026387018` wei |
| 라우터 | `0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b` (Universal Router) |
| 풀 | `0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc` |
| 주요 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EXPLORER-EVM`(Blockscout API), `DS-DEX-META` |
| 수동 재현 | 로그·Swap·internal ETH 수량 일치 확인 |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 체인 ID와 스왑 TX |
| `expected.json` | `asset_in` / `pool_output` / `user_net_output` 분리 기준 정답 |
| `evidence.json` | 이벤트·internal call·출처·조회 시각 |

세 JSON은 공통 `schema_version: 0.1`을 따르며, 채점 요구사항은 증거 ID로
이벤트와 internal call을 참조한다.

## 4. 검증 절차 (수행 기록)

1. fee-on-transfer·rebase가 아닌 USDC/WETH Uniswap V2 단일 홉 TX를 선정했다.
2. `https://ethereum.publicnode.com`에서 receipt·TX·block을 조회했다.
3. Transfer·Swap·Withdrawal 로그에서 풀 출력(WETH)을 계산했다.
4. Blockscout internal-transactions API로 라우터→사용자 ETH 전송을 확인했다.
5. Factory `getPair(USDC,WETH)`를 `eth_call`로 재현 가능하게 기록하고, 반환 주소가 풀과 일치하는지 확인했다.
6. Universal Router V1 주소를 공식 `deploy-addresses/mainnet.json`의 `UniversalRouterV1` 값과 대조했다.
7. 풀 출력(WETH)과 사용자 최종 출력(ETH)을 분리해 expected에 기록했다.

채점 시 `pool_output`(WETH)과 `user_net_output`(ETH)을 모두 요구한다. 풀 WETH만 사용자 최종 자산으로 제출하면 실패다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - fixture 필드·허용 오차·승격 기준
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 등록 소스 ID와 제약
- **Technical_Specs**: [Reference Fixture Schema](../../../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) - JSON 0.1 계약
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `SVC-DEX-001` 문제·완료 조건
- **Explorer**: [Etherscan TX](https://etherscan.io/tx/0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5) (UI 교차확인)
- **Explorer API**: [Blockscout internal txs](https://eth.blockscout.com/api/v2/transactions/0xbbdaad89cb0d0d452663b7cb341f642b613d3563411807bcd990d1fffd855fa5/internal-transactions)
