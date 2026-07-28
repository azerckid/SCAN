# SCAN 2026 공식 규정 Register
> Created: 2026-07-26 19:24
> Last Updated: 2026-07-29 03:32
> Status: Baseline Confirmed 1.0 · Active Official-Information Watch

## 1. 문서 목적

이 문서는 SCAN 2026 참가·문제풀이·도구 사용에 영향을 주는 공식 정보를
한곳에서 추적한다. 일정 안내와 실제 경기 규정을 구분하고, 공개되지 않은
항목을 관행이나 추측으로 채우지 않는다.

현재 스냅샷은 사전등록이 열린 뒤인 2026-07-29 03:32 KST 기준이다. CTFd
회원가입과 팀 생성은 정상 작동하고 로그인한 Challenge 화면은 대회 시작 전
상태로 잠겨 있다. 로그인 계정의 Notification, 공개 Rules 페이지와 공식
사이트에서 API·자동화·AI·사전 제작 도구·상용 서비스·제출 형식에 관한
세부 Rules는 확인되지 않았다. 따라서 이 문서는 “알려진 사실과 미확정
항목의 처리 경로가 확정된 기준선”이며, 새 공지를 계속 반영하는 운영
Register다.

## 2. 상태와 출처 원칙

### 2.1 규정 상태

| 상태 | 의미 | 실행 판단 |
|:---|:---|:---|
| `allowed` | 공식 원문이 명시적으로 허용 | 명시된 조건 안에서 사용 가능 |
| `restricted` | 공식 원문이 금지하거나 범위를 제한 | 실행 전 차단 또는 제한 모드 |
| `unclear` | 공식 원문 부재·모호·충돌 | 허용으로 간주하지 않고 확인 필요 |

공식 문서에 금지 문구가 없다는 사실만으로 `allowed`로 판정하지 않는다.
온라인 예선과 오프라인 본선의 규정이 다르면 단계별 상태를 따로 기록한다.

### 2.2 출처 우선순위

1. 공식 Rules·공지·CTFd challenge notice
2. SCAN 공식 이벤트 사이트와 CTFd 운영 페이지
3. 주최사 디애셋의 보도자료
4. 언론 전재·과거 대회 자료

상위 출처와 하위 출처가 충돌하면 상위 출처를 적용하고 변경 이력에 남긴다.
페이지 내용이 바뀔 수 있으므로 URL뿐 아니라 게시 시각·조회 시각·확인
범위도 함께 기록한다.

## 3. 출처 등록부

| ID | 출처 | 권위 | 게시·공개 시각 | 조회 시각 | 확인 범위 |
|:---|:---|:---|:---|:---|:---|
| `SRC-SCAN-SITE` | [SCAN 2026 공식 사이트](https://scan.sx/) | 공식 이벤트 | 페이지에 게시 시각 없음 | 2026-07-29 03:32 KST | 등록 시작, 예선 시작, 본선·시상 일정, 장소, 상금, 주최·파트너; 별도 세부 Rules 미노출 |
| `SRC-SCAN-CTFD` | [SCAN 2026 CTFd](https://scan2026.ctfd.io/) | 공식 운영 플랫폼 | 페이지에 게시 시각 없음 | 2026-07-29 03:32 KST | 공개 home은 2026-08-02 09:00 KST online qualifier만 표시, 공개 Rules 미노출 |
| `SRC-SCAN-CTFD-AUTH` | 로그인한 CTFd 화면 | 공식 운영 플랫폼의 인증 화면 | 해당 없음 | 2026-07-27 12:10 KST | 팀 생성 완료, 팀 최대 4명 안내, Notification 없음, Challenges `has not started yet` |
| `SRC-DA-PRESS` | [디애셋 보도자료](https://www.digitalasset.works/news/articleView.html?idxno=42082) | 주최사 발행 | 2026-07-22 10:15 KST | 2026-07-26 19:23 KST | 24시간 예선, 상위 20팀, 최대 4명, 참가 대상, 대회 성격 |
| `SRC-FN-CROSSCHECK` | [파이낸셜뉴스 전재](https://v.daum.net/v/20260722104928237) | 보조 교차확인 | 2026-07-22 10:49 KST | 2026-07-26 19:23 KST | 주최사 보도자료의 일정·팀·상위 20팀 내용 교차확인 |

`SRC-SCAN-SITE`, `SRC-SCAN-CTFD`와 인증 화면에서 `Rules`, API, AI,
automation 관련 공개 문구를 찾지 못했다. 이는 허용을 뜻하지 않고 “아직
확인할 수 없음”을 뜻한다. 인증 화면 관찰은 플랫폼 동작의 근거이며 규정
원문을 대신하지 않는다.

## 4. 현재 확인된 운영 사실

### 4.1 일정

| 항목 | 확인 내용 | 근거 | 상태 |
|:---|:---|:---|:---|
| 사전등록 시작 | 2026-07-27 12:00 KST | `SRC-SCAN-SITE` | confirmed |
| 사전등록 작동 | 회원가입·로그인·팀 생성 정상 작동 | `SRC-SCAN-CTFD-AUTH` | confirmed |
| 등록 마감 | 공개 정보에서 확인되지 않음 | 등록 페이지 재확인 필요 | unclear |
| 온라인 예선 시작 | 2026-08-02 09:00 KST | `SRC-SCAN-SITE`, `SRC-SCAN-CTFD` | confirmed |
| 온라인 예선 시간 | 24시간 | `SRC-DA-PRESS` | confirmed |
| 본선 | 2026-09-28, 모나코스페이스 서울 | `SRC-SCAN-SITE`, `SRC-DA-PRESS` | confirmed |
| 컨퍼런스·시상 | 2026-10-01, 워커힐호텔 워커홀 서울 | `SRC-SCAN-SITE`, `SRC-DA-PRESS` | confirmed |

24시간을 기계적으로 더한 2026-08-03 09:00 KST를 공식 종료 시각으로
간주하지 않는다. CTFd countdown·공지에서 종료 시각을 별도로 확인한다.

### 4.2 참가와 진출

| 항목 | 확인 내용 | 근거 | 상태 |
|:---|:---|:---|:---|
| 참가 대상 | 디지털자산 추적·블록체인 보안에 관심 있는 사람 | `SRC-DA-PRESS` | confirmed |
| 팀 최대 인원 | 최대 4명 | `SRC-DA-PRESS` | confirmed |
| 팀 최소 인원·개인 참가 | 한 명인 상태로 팀 생성은 작동함; 참가 자격의 공식 최소 인원은 미공개 | `SRC-SCAN-CTFD-AUTH` | operationally confirmed / rule unclear |
| 본선 진출 | 예선 상위 20개 팀 | `SRC-DA-PRESS` | confirmed |
| 팀 생성·합류·변경 마감 | 확인되지 않음 | CTFd 등록 절차 필요 | unclear |
| 본인 확인·현장 참석 의무 | 확인되지 않음 | 본선 Rules 필요 | unclear |
| 국가·연령·소속 제한 | 확인되지 않음 | 참가 자격 원문 필요 | unclear |

### 4.3 대회 성격과 상금

| 항목 | 확인 내용 | 근거 | 상태 |
|:---|:---|:---|:---|
| 형식 | 디지털자산 추적 실전형 경진대회 | `SRC-DA-PRESS` | confirmed |
| 평가 영역 안내 | 온체인 분석, 흐름 추적, 지갑 행동, 포렌식 사고력 | `SRC-DA-PRESS` | confirmed |
| 주최 | 디애셋 | `SRC-SCAN-SITE` | confirmed |
| CTF 파트너 | Chainalysis | `SRC-SCAN-SITE` | confirmed |
| 총상금 | 2 BTC | `SRC-SCAN-SITE` | confirmed |
| 상금표 정합 | 1~20위 합계 2.000 BTC | `SRC-SCAN-SITE` | confirmed |

평가 영역 안내는 실제 문제 수·지원 체인·채점 기준을 확정하지 않는다.

## 5. 도구·데이터·협업 규정 상태

2026-07-29 03:32 KST 기준 아래 항목을 명시적으로 허용하거나 금지하는 공식 Rules를
찾지 못했다. 온라인 예선과 본선 모두 `unclear`로 유지한다.

| 규정 ID | 항목 | 온라인 예선 | 본선 | 확인이 필요한 범위 |
|:---|:---|:---:|:---:|:---|
| `RULE-API-001` | 외부 RPC·탐색기·가격·OSINT API | unclear | unclear | 허용 공급자, 호출 제한, 유료 API |
| `RULE-AUTO-001` | 자체 자동화 스크립트·CLI | unclear | unclear | 수집·분석·시각화 자동화 범위 |
| `RULE-AI-001` | ChatGPT·Codex 등 생성형 AI | unclear | unclear | 질의, 코드 생성, 분석, 답안 작성 |
| `RULE-AGENT-001` | 복수 AI agent·서브에이전트 오케스트레이션 | unclear | unclear | 문제 분배, 병렬 분석, agent 간 결과 공유 |
| `RULE-PREBUILT-TOOL-001` | 대회 전 제작한 자체 도구 | unclear | unclear | 사전 코드·실행 파일 반입 |
| `RULE-PRELOAD-DATA-001` | 사전 적재 fixture·cache·계산 결과 | unclear | unclear | 공개 데이터 캐시와 문제별 사전 계산 데이터 |
| `RULE-OSS-001` | 공개 오픈소스 도구·라이브러리 | unclear | unclear | 허용 라이선스·버전·고지 의무 |
| `RULE-COMMERCIAL-001` | 상용 라벨·포렌식 서비스 | unclear | unclear | 팀 계정 공유, trial, 결과 인용 |
| `RULE-WEB-OSINT-001` | 검색엔진·웹·SNS 수동 조사 | unclear | unclear | 공개 정보 검색·열람·인용 범위 |
| `RULE-EXTERNAL-CONTACT-001` | 외부 개인·기관에 직접 연락 | unclear | unclear | 단서 확인 연락과 답안·도움 요청의 경계 |
| `RULE-COLLAB-001` | 팀 외부 인원과의 협업 | unclear | unclear | 코칭·답안 공유·외부 분석 의뢰 |
| `RULE-AUTO-SUBMIT-001` | CTFd API·스크립트 자동 제출 | unclear | unclear | API 허용, 제출 빈도, 세션 정책 |
| `RULE-BRUTEFORCE-001` | 정답 추측·brute force 제출 | unclear | unclear | 시도 제한, 오답 감점, 실격 조건 |
| `RULE-DATA-001` | 문제 데이터 저장·재배포 | unclear | unclear | 로컬 저장, 팀 공유, 대회 후 공개 |
| `RULE-PROBLEM-EXTERNAL-001` | 문제 원문·첨부·답안 후보의 외부 AI 전송 | unclear | unclear | 외부 처리, 보존 기간, 학습 사용, 국외 전송 |
| `RULE-CREDENTIAL-001` | API 키·계정의 팀 내 공유 | unclear | unclear | 개인·팀 계정, 비밀정보 보관 |

### 5.1 임시 준비 원칙

아래는 공식 규정이 아니라 규정 확인 전 프로젝트 내부 안전 원칙이다.

1. `unclear`를 `allowed`로 표시하지 않는다.
2. AI Planner/Coordinator는 모든 문제에 해결 방법 가설과 leaf job 계획을
   만드는 SCAN의 필수 내부 아키텍처다. 공식 Rules는 AI 사용 여부가 아니라
   허용 provider·model·data boundary·tool mode를 결정한다.
3. 허용 mode가 미확정이면 AI planning job을 제거하지 않고 `rules_gated`로
   대기시키며 외부 호출은 0건으로 유지한다.
4. 요청한 mode가 공식 Rules에 의해 금지·제한되면 해당 호출을 I/O 전에
   `rule_restricted`로 거부한다. 다른 AI mode는 공식적으로 허용된 경우에만
   선택한다.
5. 허용되는 AI mode가 하나도 없으면 AI-native Operations 전체를 완료한
   것으로 표시하지 않고 규정 충돌을 Operator에게 알린다.
6. Python 증거 도구는 허용된 offline 준비·재현을 계속할 수 있지만,
   `TASK-010` 전체 흐름에서 AI Planner를 대신하지 않는다.
7. 분석 도구는 수동 검증·source provenance·원본 증거 보존 경로를 유지한다.
8. 자동 제출, 자격증명 공유, challenge brute force 기능은 준비 범위에서 제외한다.
9. 공개 전 문제·답안·개인정보를 승인되지 않은 외부 AI 서비스에 전송하지 않는다.

## 6. 문제·제출 형식 미확정 등록부

| 규정 ID | 미확정 항목 | 필요한 결정 |
|:---|:---|:---|
| `RULE-CHALLENGE-001` | 지원 체인·자산·사건 범위 | Ethereum, Bitcoin, 기타 체인과 제공 데이터 |
| `RULE-SCORE-001` | 점수·동점·힌트·오답 감점 | dynamic scoring, solve time, penalty |
| `RULE-ANSWER-001` | 정답 제출 형식 | 주소·TX·수량·텍스트·복수 정답 형식 |
| `RULE-EVIDENCE-001` | 증거 제출 형식 | URL·스크린샷·JSON·서술 요구 여부 |
| `RULE-LANGUAGE-001` | 문제·답안 언어 | 한국어·영어 지원과 서술 답안 언어 |
| `RULE-PLATFORM-001` | 제출 플랫폼·API | CTFd UI, API 허용 여부, 세션 정책 |
| `RULE-FINAL-001` | 본선 장비·네트워크 | 개인 장비, 인터넷, 설치, 현장 계정 |

이 항목들이 확정되기 전 예상문제 은행의 정답 형태와 도구의 export 형식은
대회 공식 제출 형식으로 표현하지 않는다.

## 7. 공식 문의 등록부

공식 사이트의 문의 주소는 `scan@digitalasset.works`다. 아직 문의를
발송하지 않았으며, 다음 질문은 등록 페이지와 공개 Rules 확인 후에도
답이 없을 때 보낼 후보 목록이다.

| 문의 ID | 질문 | 상태 | 재확인 시점 |
|:---|:---|:---|:---|
| `Q-REG-001` | 등록 마감·개인 참가·팀 변경 마감은 언제인가? | ready_to_send · 사용자 발송 승인 필요 | 공개 Rules·Notification 재확인 후 |
| `Q-TOOL-001` | 외부 API·자체 자동화·사전 제작 도구와 fixture·cache 반입이 허용되는가? | not_sent | 공개 Rules 확인 후 |
| `Q-AI-001` | 생성형 AI를 코드·분석·답안 작성에 사용할 수 있는가? | not_sent | 공개 Rules 확인 후 |
| `Q-AGENT-001` | 복수 AI agent가 문제를 분배·병렬 분석하고 결과를 공유하는 것이 허용되는가? | not_sent | 공개 Rules 확인 후 |
| `Q-DATA-AI-001` | 문제 원문·첨부·답안 후보를 외부 생성형 AI에 전송할 수 있는가? | not_sent | 공개 Rules 확인 후 |
| `Q-SVC-001` | 상용 포렌식·라벨 서비스와 팀 계정 공유가 허용되는가? | not_sent | 공개 Rules 확인 후 |
| `Q-SUBMIT-001` | 지원 체인과 정답·증거 제출 형식은 무엇인가? | not_sent | challenge notice 확인 후 |
| `Q-SUBMIT-AUTO-001` | CTFd API·자동 제출과 정답 추측의 허용 범위·빈도·감점은 무엇인가? | not_sent | 공개 Rules 확인 후 |
| `Q-OSINT-001` | 웹·SNS OSINT와 외부 개인·기관에 직접 연락하는 행위가 허용되는가? | not_sent | 공개 Rules 확인 후 |
| `Q-FINAL-001` | 본선 참석·신원 확인·장비·인터넷 조건은 무엇인가? | not_sent | 본선 안내 공개 후 |

문의 발송과 외부 상태 변경은 별도 사용자 승인 후에만 수행한다.

## 8. 재확인 Gate

| 시점 | 확인 대상 | 완료 조건 |
|:---|:---|:---|
| 2026-07-27 12:00 KST 직후 | 공식 사이트, CTFd 등록·Rules·약관 | 완료: 등록·팀 생성 작동, Notification·상세 Rules 없음 기록 |
| 2026-07-27~08-01 | 로그인 Notification·이메일·공식 사이트 | 새 공지가 있으면 아래 Intake 절차 실행 |
| 2026-08-02 예선 전 | CTFd 공지·challenge notice | 제출·채점·힌트·종료 시각 확인 |
| 본선 진출 확정 후 | 본선 참가 안내 | 신원·현장·장비·네트워크 규정 확인 |
| 공식 공지 변경 시 | 영향받는 모든 `RULE-*` | 이전 값·새 값·출처·적용 시각 기록 |

세부 정보가 계속 공개되지 않으면 상태를 `restricted`로 바꾸지 않고
`unclear`로 유지한다. Roadmap의 DOC-M2 기준선은 확인 경로와 비활성 Gate가
정의되었으므로 완료 상태를 유지하고, 이 문서만 `Active Official-Information
Watch`로 계속 갱신한다.

### 8.1 Notification Intake 절차

새 Notification·이메일·Rules·challenge notice가 보이면 다음 순서로
처리한다. 공지를 읽었다는 사실만으로 기능을 자동 활성화하지 않는다.

1. 원문 제목·본문·URL·게시 시각·조회 시각과 가능한 경우 화면 캡처를 보존한다.
2. 온라인 예선·본선·공통 중 적용 단계를 분류하고 효력 발생 시각을 기록한다.
3. 영향받는 `RULE-*`의 이전 값과 새 값을 문장 단위 근거와 함께 비교한다.
4. 준비 전략·문제은행·우선순위·소스·요구사항·Backlog·QA 영향표를 작성한다.
5. 제한은 즉시 `restricted` Gate로 반영하되, 허용 기능 활성화는 사용자
   검토와 별도 실행 승인을 거친다.
6. fixture·analysis Schema 검증과 관련 문서 링크 검사를 다시 실행한다.
7. 답이 남지 않은 문의는 `ready_to_send`로 전환하고 발송은 사용자 승인을
   받는다.

| Intake 필드 | 기록 내용 |
|:---|:---|
| `notice_id` | `NOTICE-YYYYMMDD-NNN` |
| `source` | 공식 URL·CTFd Notification·이메일 발신자 |
| `published_at`, `retrieved_at` | 원문 게시·실제 조회 시각 |
| `applies_to` | qualifier/final/both |
| `affected_rule_ids` | 변경되는 `RULE-*` |
| `old_status`, `new_status` | allowed/restricted/unclear |
| `effective_at` | 즉시 또는 지정 시각 |
| `affected_documents` | 역반영 대상 |
| `feature_gate_action` | wait_for_mode/select_allowed_mode/block_restricted_call/approval_required |
| `verification` | 실행한 문서·Schema·fixture 검증 |

### 8.2 미공지 상태의 운영

- Notification이 없다는 이유로 준비 작업을 중단하지 않는다.
- DB Schema·README·OSS 결정·offline fixture 검증은 계속 진행한다.
- AI Planner job은 유지하되 허용 mode가 확정될 때까지 `rules_gated`로
  대기시키며 외부 전송은 0건으로 유지한다.
- 허용된 offline Python 증거 준비는 계속할 수 있지만, 이를 AI-native
  Operations의 완료나 AI Planner 대체로 표시하지 않는다.
- 자동 감시는 현재 구현되어 있지 않으므로 로그인 Notification·가입 이메일·
  공식 사이트를 수동 재확인한다.

## 9. 변경 이력

| 시각 | 변경 | 근거 | 영향 |
|:---|:---|:---|:---|
| 2026-07-26 19:24 KST | 사전등록 전 기준선 생성 | `SRC-SCAN-SITE`, `SRC-SCAN-CTFD`, `SRC-DA-PRESS` | 일정·참가·상금 사실과 미공개 규정 분리 |
| 2026-07-26 19:24 KST | 상금표 1~20위 합계 2.000 BTC 확인 | `SRC-SCAN-SITE` | 기존 1~18위 합계 불일치 관찰 종료 |
| 2026-07-26 20:09 KST | 복합 규정 상태를 원자 정책으로 분리 | 내부 문서 검토 | 도구/사전 데이터, 웹 조사/외부 연락, 자동 제출/brute force 독립 갱신 |
| 2026-07-27 00:54 KST | agent orchestration·외부 AI 문제 데이터 전송 항목 추가 | 내부 운영 설계 | `RULE-AGENT-001`, `RULE-PROBLEM-EXTERNAL-001` 확인 전 비활성 |
| 2026-07-27 12:10 KST | 등록 후 1차 확인 | `SRC-SCAN-SITE`, `SRC-SCAN-CTFD`, `SRC-SCAN-CTFD-AUTH` | 등록·팀 생성 작동, Challenge 잠금, Notification·상세 Rules 없음 |
| 2026-07-27 15:52 KST | Notification Intake와 미공지 운영 절차 확정 | 사용자 승인·내부 문서 검토 | 공지 대응과 독립 문서 작업을 병렬화 |
| 2026-07-28 10:24 KST | AI-native 내부 실행 계약 동기화 (공식 규정 변경 아님) | 사용자 결정·내부 운영 설계 | AI Planner 필수, Rules Gate는 mode 선택, `rules_gated` 대기와 `rule_restricted` 호출 거부 분리 |

변경 이력에는 페이지가 그대로였다는 사실이 아니라, 이전 기준선과 달라진
규정·운영 정보만 추가한다.

## 10. 365 글로벌 평가 기준과 규정 영향

| 기준 | 규정 Register의 역할 |
|:---|:---|
| Functionality | 허용 source·도구 범위를 실행 전 Gate로 연결 |
| Potential Impact | 재사용 가능한 출처·변경·문의 기록으로 준비 오류 감소 |
| Novelty | 자체 분석 방식과 외부 서비스 의존을 구분해 차별성 보존 |
| UX | 규정 차단을 구조화된 오류와 다음 행동으로 안내 |
| Open-source | 사전 코드·OSS·데이터 공개 가능 범위를 확인 |
| Business Plan | 상용 서비스·라이선스·대회 후 활용 가능 범위를 분리 |

## 11. Related Documents

- **Concept_Design**: [참가·분석 도구 준비 전략](./01_SCAN_2026_PREPARATION_STRATEGY.md) - 참가 사실·준비 순서의 기준
- **Concept_Design**: [예상문제 은행](./02_SCAN_2026_EXPECTED_PROBLEM_BANK.md) - 지원 체인·정답 형식·도구 규정 반영 대상
- **Concept_Design**: [기능 우선순위](./04_SCAN_2026_TOOL_PRIORITY.md) - 규정 위험 점수 갱신 대상
- **Technical_Specs**: [데이터 소스 등록부](../03_Technical_Specs/01_DATA_SOURCE_REGISTRY.md) - source별 대회 규정 상태 갱신 대상
- **Technical_Specs**: [P0·V1 도구 요구사항](../03_Technical_Specs/03_SCAN_2026_TOOL_REQUIREMENTS.md) - `rule_restricted`와 규정 준수 계약
- **Technical_Specs**: [Agentic Parallel Solve Flow](../03_Technical_Specs/07_AGENTIC_PARALLEL_SOLVE_FLOW.md) - 서브에이전트·문제 데이터 전송·수동 제출 Rules Gate
- **UI_Screens**: [Competition Operations Board](../02_UI_Screens/04_COMPETITION_OPERATIONS_BOARD.md) - 규정 상태·비활성 worker·fallback 표시
- **Logic_Progress**: [문서 완료 Roadmap](../04_Logic_Progress/00_ROADMAP.md) - DOC-M2 기준선 완료와 Active Watch 분리
- **QA_Validation**: [P0·V1 QA 시나리오](../05_QA_Validation/01_TEST_SCENARIOS.md) - 규정 차단 회귀 기준
