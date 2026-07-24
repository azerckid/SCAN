# Fixture: FX-EVM-AUTH-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-24 20:04
> Status: Verifying

## 1. 목적

`approve` 또는 `permit`으로 부여된 토큰 권한과 이후 소비 호출을 연결하고,
이벤트·호출·과거 allowance 상태를 서로 분리해 검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-AUTH-001` |
| 상태 | 검증 중 (`verifying`) |
| 사례 성격 | 공개 온체인 권한 소비 통제 사례. 범죄·피싱·피해 사실은 판정하지 않음 |
| 주소 V | `0x193070aea3df0e8e0436f6ed810fd8bbe687af59` |
| 토큰 | USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` |
| spender | Uniswap V3 `SwapRouter02` `0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45` |
| 승인 TX | `0x3f7037014b8709f02bf2032d70ce4ec6854a53ed141b63d6a7ea359a9dccdabd` |
| 소비 TX | `0x7b888fbf7ee76c99ec1e1a31d8bc1d43806f7f5e7fcfd4121a6a21a768e9af51` |
| 소비량 | USDC `4500000` raw = 4.5 USDC |
| allowance | `0` → `uint256.max` → 소비 후 `uint256.max - 4500000` |
| 주요 소스 | `DS-EVM-RPC-PUBLIC`, `DS-EVM-RPC-ARCHIVE`(dRPC), `DS-EXPLORER-EVM`(Blockscout API), `DS-DEX-META` |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 피해자·토큰·승인·소비 TX와 조회 블록 |
| `expected.json` | 승인 유형별 증거, allowance 전후와 실제 전송 기준 정답 |
| `evidence.json` | 이벤트·calldata·상태 조회 원본과 provenance |

## 4. 검증 절차 (수행 기록)

1. 승인 유형을 `approve`로 확정하고 승인 TX calldata와 `Approval` 로그를 분리 기록했다.
2. 승인 전후 블록 `24500452`/`24500453`의 allowance를 archive `eth_call`로 조회했다.
3. 승인 이후의 세 거래가 모두 revert된 것을 확인해 소비 TX에서 제외했다.
4. 성공 TX `24500505`의 trace에서 Router→USDC `transferFrom` 호출을 확인했다.
5. 소비 직전/직후 블록 `24500504`/`24500505`의 allowance를 비교했다.
6. allowance 감소량 `4500000` raw가 `transferFrom` 인자와 USDC `Transfer` 로그에 모두 일치함을 확인했다.

이 fixture의 확정 사실은 승인과 권한 소비의 연결이다. 주소 V가 피해자라는 주장이나 피싱·탈취 판단은 오프체인 증거가 없으므로 채점 대상에 포함하지 않는다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - AUTH 증거 유형과 승격 기준
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - archive state 필수 소스
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-AUTH-001` 문제·완료 조건
- **Explorer**: [승인 TX](https://etherscan.io/tx/0x3f7037014b8709f02bf2032d70ce4ec6854a53ed141b63d6a7ea359a9dccdabd), [소비 TX](https://etherscan.io/tx/0x7b888fbf7ee76c99ec1e1a31d8bc1d43806f7f5e7fcfd4121a6a21a768e9af51) - UI 교차확인
- **Official metadata**: [Uniswap Deployments](https://developers.uniswap.org/deployments) - Ethereum `SwapRouter02` 주소
