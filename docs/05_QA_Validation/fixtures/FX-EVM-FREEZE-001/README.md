# Fixture: FX-EVM-FREEZE-001
> Created: 2026-07-24 19:19
> Last Updated: 2026-07-28 02:22
> Status: Confirmed

## 1. 목적

USDC 주소별 블랙리스트의 설정·해제 생명주기를 이벤트, 과거 상태,
발행사 자료와 규제기관 원문으로 교차검증한다.

## 2. 현재 상태

| 항목 | 값 |
|:---|:---|
| 연결 문제 | `EVM-FREEZE-001` |
| 상태 | 확정 (`confirmed`) |
| Fixture 버전 | `0.2` (`schema_version`은 `0.1`) |
| 체인 | Ethereum (`chain_id` 1) |
| 토큰 | USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` |
| 모드 | 주소별 블랙리스트 생명주기 |
| 대상 | Tornado Cash 주소 `0xd96f2b1c14db8458374d9aca76e26c3d18364307` |
| 설정 TX | `0xc67cf29fc3feb0073e98f5c341671a8e96999854e37fd876f05046f13c53af72` |
| 해제 TX | `0xecf9033c7148239246b312636648774b10fe940489f0d5ca4970677aef241537` |
| 상태 전이 | `false` → `true` (2022) → `false` (2025) |
| 필수 소스 | `DS-EVM-RPC-ARCHIVE`, `DS-EXPLORER-EVM`, `DS-OSINT-WEB` |
| 보조 provenance | `DS-EVM-RPC-PUBLIC`, `DS-SANCTIONS-PUBLIC` |
| 확정 재현 | 2026-07-25 15:25, 두 TX·이벤트·네 상태·공식 맥락·고정 소스 일치 |
| 고정 provenance | Circle `stablecoin-evm` 커밋 `b42cf04...59d9`의 `Blacklistable.sol`과 MIT 라이선스 |

## 3. 파일 역할

| 파일 | 역할 |
|:---|:---|
| `input.json` | 토큰, 모드, 대상 주소, 설정·해제 TX와 상태 블록 |
| `expected.json` | 두 상태 전이와 이벤트·공식 맥락 기준 정답 |
| `evidence.json` | 이벤트·호출·상태·맥락을 분리한 증거와 provenance |
| `raw-replay.json` | TASK-008 offline decoder가 읽는 reviewed transaction·receipt·Public RPC cross-check·state·공식 맥락 |

세 JSON은 공통 `schema_version: 0.1`을 따른다. calldata는
`call_evidence`, 발행사·OFAC 자료는 `context_evidence`에 두며, 채점
요구사항은 각 증거 ID를 참조한다.

## 4. 검증 절차 (수행 기록)

1. 모드를 USDC 주소별 블랙리스트 생명주기로 고정했다.
2. Circle 공식 컨트랙트 자료에서 `Blacklisted`, `UnBlacklisted`,
   `isBlacklisted` 인터페이스를 확인했다.
3. 설정 TX의 `Blacklisted` 로그와 `15302548:false` →
   `15302549:true` 상태 전이를 연결했다.
4. 해제 TX의 `UnBlacklisted` 로그와 `22099071:true` →
   `22099072:false` 상태 전이를 연결했다.
5. 네 상태 조회를 dRPC archive `eth_call`로 각각 두 번 재현했다.
6. Blockscout API의 calldata·로그 디코딩과 RPC 결과를 교차확인했다.
7. OFAC의 2022년 지정과 2025년 해제 원문에서 대상 주소를 확인했다.
8. Circle 자료는 주소별 공지가 아니라 정책·대응 맥락임을 별도로 기록했다.
9. 같은 입력으로 두 TX·receipt·이벤트와 네 과거 상태를 다시 조회해
   boolean 값이 정확히 일치함을 확인했다.
10. Blockscout API의 두 성공 호출·대상 주소를 다시 확인했다.
11. 거래 이전 Circle 공식 커밋
    `b42cf04b31639b8b05d53fea9995954d5f3659d9`의 인터페이스와 MIT
    라이선스를 파일 해시로 고정했다.
12. 2026-07-28 read-only 재확인에서 public RPC의 두 TX·receipt,
    dRPC archive의 네 상태와 Blockscout 메서드·대상 주소가 기존 기준값과
    일치했다.
13. TASK-008 analyzer가 `raw-replay.json`만 읽어 call·event·state·context를
    독립 디코딩하고 complete·partial·failed·restricted 경로를 재현했다.

채점 대상은 이벤트와 상태 전이다. OFAC 지정·해제는 공개 사건 맥락이며,
범죄 의도나 현재 제재 상태를 온체인 사실로 간주하지 않는다. 설정 직전과
직후 USDC 잔액은 모두 `3900000000` raw로 같아, 블랙리스트 설정 자체가
토큰 전송이나 소각은 아니라는 점도 분리한다.

## 5. Related Documents

- **QA_Validation**: [Reference Fixtures](../../01_REFERENCE_FIXTURES.md) - FREEZE 모드·허용 오차·승격 기준
- **QA_Validation**: [TASK-008 FREEZE 보고서](../../12_TASK_008_FREEZE_REPORT.md) - offline raw replay·정합·scope·security 검증
- **Technical_Specs**: [데이터 소스 등록부](../../../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - 상태·로그·OSINT 소스
- **Technical_Specs**: [Reference Fixture Schema](../../../03_Technical_Specs/02_REFERENCE_FIXTURE_SCHEMA.md) - JSON 0.1 계약과 증거 분리
- **Concept_Design**: [예상문제 은행](../../../01_Concept_Design/02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - `EVM-FREEZE-001` 문제·완료 조건
- **Explorer**: [설정 TX](https://etherscan.io/tx/0xc67cf29fc3feb0073e98f5c341671a8e96999854e37fd876f05046f13c53af72), [해제 TX](https://etherscan.io/tx/0xecf9033c7148239246b312636648774b10fe940489f0d5ca4970677aef241537) - UI 교차확인
- **Issuer**: [Circle 대응 맥락](https://www.circle.com/blog/the-responsibility-of-trust), [USDC Terms](https://www.circle.com/legal/usdc-terms) - 주소별 공지가 아닌 발행사 정책·대응 맥락
- **Regulator**: [OFAC 지정](https://ofac.treasury.gov/recent-actions/20220808), [OFAC 해제](https://ofac.treasury.gov/recent-actions/20250321) - 대상 주소를 명시한 공식 원문
- **Official source**: [Circle Blacklistable.sol pinned commit](https://github.com/circlefin/stablecoin-evm/commit/b42cf04b31639b8b05d53fea9995954d5f3659d9) - 거래 이전 인터페이스와 MIT 라이선스의 고정 근거
