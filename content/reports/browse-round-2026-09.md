# 월간 브라우저 라운드 결과보고 — 2026-09

- 실행: 2026-09-02 14:15 ~ 14:50 (KST, 약 35분)
- 실행자: Claude Code (/browse-round), 사용자 승인 하 진행
- 사전 점검: Claude in Chrome 연결 확인. 다운로드는 세션 중 mckinsey.com·dbr.donga.com에서
  Chrome의 "동일 오리진 2건째부터 자동 다운로드 차단" 정책에 걸려 사용자가 각각 오리진별로
  다중 다운로드를 허용한 뒤 재개함 (browse-collect.md 사전 조건에 기록된 내용의 실전 확인)

## ① 목록 모드 (browse_mode: list)

| 소스 | 신규 | 격상 | 중복 | 실패 | 발견 적합 vs 수집 | 비고 |
|---|---|---|---|---|---|---|
| deloitte-insights | 0 | 0 | 0 | 0 | 0 vs 0 | 최근 30일 적합 후보 3건 모두 이전 파일럿에서 기등재 |
| bcg-publications | 0 | 0 | 0 | 0 | 0 vs 0 | 목록 7건 중 적합 1건, 이미 기등재 |
| pwc-global-insights | 0 | 0 | 0 | 0 | 0 vs 0 | **막힌 지점**: 일반 피드가 팟캐스트·M&A 동향 위주라 최근 30일 인재·조직·AI 텍스트 기사 미발견. 대표 리포트(Global Workforce Hopes and Fears)는 2025-11-12 발행으로 창 밖. 선택자 미확정(적합 텍스트 기사 부재) |
| lg-business-research | 0 | 0 | 0 | 0 | 0 vs 0 | **막힌 지점**: 공개 목록(business·economy·전체보기·홈) 모두 최신이 2026-02-10에 정체 — "월 수회" 명시와 불일치, 로그인 게이트 의심. `javascript:fnView()` 클릭 기반 구조 재확인 |
| samjong-kpmg | — | — | — | — | — | 라운드 제외(note: 이미지형 PDF·OCR 필요·적합 0/8, 분기 1회 사람 확인) |

## ② McKinsey 격상 (browse 보조, type: rss 유지)

요약뿐(summary_only=1) 문서 51건 중 인재·조직·AI와 일 위주로 12건을 사용자와 함께 선정,
전체 격상을 시도.

**격상 성공 7건** (요약 → 전문 교체, summary_only 0·status new 복귀):

| 발행일 | 제목 | 글자 수 |
|---|---|---|
| 08-28 | The new management playbook for AI | 16,051 |
| 08-25 | The state of AI in 2026: On the road to ROI | 18,595 |
| 08-24 | Where AI agents pay off | 13,899 |
| 08-21 | Beyond the copilot | 27,412 |
| 08-20 | Earning and sustaining trust in the age of AI | 20,747 |
| 08-17 | Governing AI with intention in the social impact sector | 14,221 |
| 08-12 | AI transformations run on trust | 18,772 |

**미완 5건 — McKinsey WAF(Access Denied)가 짧은 간격의 반복 요청에 민감하게 반응해 중단**:
author-talks-the-biggest-misconceptions-about-leadership, how-to-close-the-agentic-adoption-gap,
ai-fluency-the-next-foundation-of-us-economic-competitiveness,
escaping-the-pilot-trap-building-hr-for-the-agentic-era (4건, 재시도 필요),
are-you-settling-for-a-b-plus-life (McKinsey 팟캐스트로 확인됨 — 본문 페이지는 짧은 소개문뿐이라
전문은 별도 트랜스크립트 페이지에 있음. 재추출해도 800자 임계 미달 가능성 높아 격상 제외 유력)

다음 라운드(또는 별도 세션)에서 McKinsey는 **한 번에 2~3건씩, 요청 간 충분한 간격**을 두고
재시도할 것을 권고.

## ③ 유료 건별 보조

### HBR Korea

| 기사 | 발행일 | 글자 수 | 결과 |
|---|---|---|---|
| '재택이냐, 사무실 출근이냐'는 틀린 질문이다 (1688) | 2026-09-02 | 4,421 | 신규 |
| AI의 브랜드 잠식을 막아라 (1685) | 2026-08-28 | 7,109 | 신규 |

→ **신규 2 · 격상 0 · 중복 0 · 실패 0**. 로그인 세션 정상, 유료 잘림 없음 확인,
license_note "구독 계정 열람 — 내부 저장 범위 확인 중" 기재.

**[추기 2026-09-02] 목록 사각지대 진단·수정 후 +3건 재수집**

라운드 당시 HBR Korea를 **홈 1개 화면으로만** 확인한 것이 누락 원인이었다. 홈은 디지털 4건 +
매거진 4건 **총 8건만** 노출하고 **매거진 슬롯이 회전**해(라운드 시점 2474·2443·2425·2437 →
진단 시점 2460·2442·2469·2451), 9-10월호 19건 중 대부분이 홈에 뜨지 않았다.

| 목록 | 범위 | 누락 3건 포함 여부 |
|---|---|---|
| 홈(`/`) | 8건, 매거진 슬롯 회전 | 2469 △(회전 시에만) · 2481 ✗ · 1686 ○ |
| `/article/latest` | 최신 통합 28건 | 3건 전부 ○ |
| `/magazine/view/pub_year/2026/pub_no/9` | 9-10월호 목차 19건 | 2469 ○ · 2481 ○ |
| `/article/topics/category_id/2_1`(인사조직) | 30건/페이지 | 3건 전부 ○ |
| `/article/digital` | 디지털 30건/페이지 | 1686 ○ |

추가 등재 결과 (**HBR Korea +2 신규**):

| 기사 | 발행 | 글자 수 | 결과 |
|---|---|---|---|
| AI 시대, 기업에는 에이전트 매니저가 필요하다 (ma 2469) | 2026. 9-10월호 | 6,813 | 신규 |
| HCL테크 CEO, AI 시대를 위한 전환을 말하다 (ma 2481) | 2026. 9-10월호 | 7,542 | 신규 |
| AI 시대, 시험대에 오른 모듈화 기업 (di 1686, `/page/1` 형태) | 2026-08-31 | 6,729 | **중복** — 파일럿 등재분과 URL은 다르나 content_hash 일치로 이중 등재 차단(중복 규칙 검증) |

수정: sources.yaml의 hbr-korea·dbr에 **`browse_list_urls`** 신설(최신 통합·카테고리·최신호 목차),
browse-round.md ④단계를 "홈에서 확인" → "`browse_list_urls`를 순서대로 확인(제목·URL 수준만)"으로 교체.
DBR도 실측 결과 홈 18건이 여러 호에 걸쳐 회전 노출돼 **호 목차(`/magazine/mcontents/pub_number/448`,
22건 전량)가 정본**임을 확인해 같은 필드를 채움. 매거진 아티클은 발행일 메타가 없어 호 라벨의
첫 달 1일(2026-09-01)로 근사 기재.

### DBR

| 기사 | 발행일 | 글자 수 | 결과 |
|---|---|---|---|
| 근로시간 줄면 '고밀도 노동' 부작용도 (12256) | 2026-08-25 | 7,312 | 신규 |
| '나 없으면 안 된다'는 착각 (12232) | 2026-08-11 | 5,310 | 신규 |
| AI 투자로 수익 높인 기업에 기회 집중 (12253) | 2026-08-25 | 13,194 | 신규 |
| 2027년 경영 화두로 떠오를 12개의 키워드 (12241) | 2026-08-25 | 18,526 | 신규 |
| 서랍 속 기술을 꺼낼 열쇠는? (12219, Issue 인트로) | 2026-08-11 | 1,851 | 신규 |

→ **신규 5 · 격상 0 · 중복 0 · 실패 0**.

## ④ 종합

- **총 유입 문서: 16건** (McKinsey 격상 7 + HBR Korea 신규 4 + DBR 신규 5)
  — 최초 14건, 목록 사각지대 수정 후 HBR Korea +2 (아래 추기 참조)
- 발견 적합 vs 수집: 목록 모드 0 vs 0(전량 기등재 또는 발견 실패), McKinsey 12 vs 7(WAF로 5건 이월),
  유료 건별 7 vs 7(사용자 지정 전량)
- 소요 시간: 약 35분 (McKinsey WAF 대기·재시도 포함)
- 무유입 경보: 현재 열린 inflow-alert 이슈 없음(GitHub 확인) — 해소 대상 없음

## 다음 라운드 전 개선 과제

1. McKinsey 격상은 세션당 2~3건으로 나누어 진행 (WAF 민감도 실측 반영)
2. PwC·LG경영연구원의 목록 발견 방식 재검토 필요 — 현재 방식으로는 월간 라운드 실효성 낮음
3. Chrome 다중 다운로드 허용은 오리진별로 별도 — 새 오리진 도입 시 첫 라운드에서 안내 필요
