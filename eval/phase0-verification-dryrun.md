<!-- A2 실사용 기준 검증기(src/verify_article.py)의 출력 형식을 확인하려고 Phase 0 발행분에
     돌린 스냅샷(2026-09-04). 발행분 재판정이 목적이 아니며 발행 상태는 그대로 둔다.
     재생성: python src/verify_article.py content/published/psych-safety-ai-experiment.md \
             --out eval/phase0-verification-dryrun.md -->
# 검증 리포트 (실사용 기준) — psych-safety-ai-experiment

대상: `content/published/psych-safety-ai-experiment.md` · 증거: `content/evidence/psych-safety-ai-experiment.json`
판정: **실패** (실패 3건 · 경고 2건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[관찰된 신호] 13행** — “AI 도입의 성패를 가르는 것이 기술이 아니라는 신호가 여러 출처에서 겹친다.”
- `1A0330A0ACA6187D27D315CD639` · mckinsey-insights · T2 · neutral/opinion — 엔터프라이즈 AI 도입 성공은 기술 구축보다는 조직 인력 관리와 문화 변화가 더 중요한 요소다
- `1A0330C8E32B503932BDDE2207D` · hbr · T3 · conditional/opinion — AI 도입의 성공은 기술 측면만큼이나 업무 재설계, 신뢰 구축, 인재 개발, 인간 판단의 질 보호 같은 조직 차원의 요소에 달
- `1A0330C7DD8FA16CCCA91898DB0` · hbr · T3 · neutral/opinion — IT 팀은 통제, 표준화, 위험 감소를 추구하는 반면 AI 팀은 실험, 유연성, 빠른 학습을 추구한다

**[관찰된 신호] 16행** — “그런데 실험을 장려하는 조직에서도 이상한 간극이 나타난다.”
- `1A0330A8454BABCB1A4E195471D` · hbr · T3 · cautious/data — 근로자들이 생산성 향상을 보고했음에도 불구하고 기업의 실제 수익에는 약속된 이점이 나타나지 않았다
- `1A0330BC7AB775F7FB59B39747D` · hbr · T3 · optimistic/opinion — 생성형 AI의 가장 큰 조직적 수익은 기성 생산성 도구가 아닌 조직 전체 솔루션에서 창출된다
- `1A0330C45EC6C7D9FE3F05A5357` · hbr · T3 · optimistic/opinion — AI 도입으로 인한 생산성 증가와 고객 만족도 향상이 동시에 가능하다

**[통념과의 충돌] 21행** — “통념은 이렇다: "구성원이 실패를 두려워하니, 실패해도 괜찮다는 분위기를 만들면 AI 실험 문화가 생긴다." 심리적 안전감(팀 안에서 질문·실수 인정·이견 제시 …”
- `1A0367ECCCADD33D1B907BA7883` · theory-canon · T1 · neutral/theory — 심리적 안전감 — 대인관계 위험을 감수해도 안전하다는 팀 구성원의 공유된 믿음 — 은 학습 행동을 매개로 팀 성과에 기여한다
- `1A0367ECCCBD77FFC9213452C61` · theory-canon · T1 · neutral/theory — 심리적 안전감은 발언(voice)·정보 공유·실수 보고·도움 요청 행동과 정적으로 연관된다 (메타분석에서 일관되게 지지)

**[통념과의 충돌] 24행** — “그러나 원전은 두 가지 단서를 단다.”
- `1A0367ECCCB9B262609BECC7D47` · theory-canon · T1 · neutral/theory — 심리적 안전감은 기준을 낮추는 관용이나 무조건적 친절이 아니라, 대인관계 리스크에 따르는 발언 비용을 낮추는 조건이다
- `1A0367ECCCB631D3AEEF5E5BD82` · theory-canon · T1 · conditional/theory — 심리적 안전감이 높아도 성과 기준·책무성이 함께 높지 않으면 학습·성과로 이어지지 않는다 (안전감 단독으로는 안주 영역이 될 

**[교차 해석] 29행** — “이 2축 구조로 앞의 간극을 다시 읽을 수 있다.”
- `1A0330A8454BABCB1A4E195471D` · hbr · T3 · cautious/data — 근로자들이 생산성 향상을 보고했음에도 불구하고 기업의 실제 수익에는 약속된 이점이 나타나지 않았다
- `1A0330BC7AB775F7FB59B39747D` · hbr · T3 · optimistic/opinion — 생성형 AI의 가장 큰 조직적 수익은 기성 생산성 도구가 아닌 조직 전체 솔루션에서 창출된다
- `1A0330C8E32B503932BDDE2207D` · hbr · T3 · conditional/opinion — AI 도입의 성공은 기술 측면만큼이나 업무 재설계, 신뢰 구축, 인재 개발, 인간 판단의 질 보호 같은 조직 차원의 요소에 달
- `1A0330AC2D57A625CE54F97ED94` · hbr · T3 · conditional/opinion — AI 기술 도입 시 조직 내 신뢰 구축이 사용자 수용의 가장 중요한 선행 조건이다

**[교차 해석] 32행** — “이론의 경계 조건 하나가 한국 조직에 특히 중요하다.”
- `1A0367ECCCB9868B4BC0F52E812` · theory-canon · T1 · conditional/theory — 발언 행동의 효과는 위계 문화·권력거리 등 조직·국가 맥락에 따라 달라져, 개입 효과의 일반화에 주의가 필요하다
- `1A0367ECCCB6D61B699D3529DBC` · theory-canon · T1 · neutral/theory — 리더의 포용적 행동(질문하기, 자신의 실수 인정, 접근 가능성)은 심리적 안전감 형성의 주요 선행 요인이다

**[다음 주에 시도할 것] 42행** — “**리더용** — 주체: 팀장 / 기간: 2주 1.”
- `1A0367ECCCB631D3AEEF5E5BD82` · theory-canon · T1 · conditional/theory — 심리적 안전감이 높아도 성과 기준·책무성이 함께 높지 않으면 학습·성과로 이어지지 않는다 (안전감 단독으로는 안주 영역이 될 
- `1A0367ECCCB6D61B699D3529DBC` · theory-canon · T1 · neutral/theory — 리더의 포용적 행동(질문하기, 자신의 실수 인정, 접근 가능성)은 심리적 안전감 형성의 주요 선행 요인이다

**[다음 주에 시도할 것] 47행** — “**실무자용** — 주체: 실무 구성원 / 기간: 4주 1.”
- `1A0367ECCCBD77FFC9213452C61` · theory-canon · T1 · neutral/theory — 심리적 안전감은 발언(voice)·정보 공유·실수 보고·도움 요청 행동과 정적으로 연관된다 (메타분석에서 일관되게 지지)

**[남은 쟁점] 53행** — “개인 체감과 조직 성과의 간극에는 경합 설명이 있다.”
- `1A0330E4405EA14D9376DB4154B` · **evidence에 없음(실패)**
- `1A0367ECCCB9868B4BC0F52E812` · theory-canon · T1 · conditional/theory — 발언 행동의 효과는 위계 문화·권력거리 등 조직·국가 맥락에 따라 달라져, 개입 효과의 일반화에 주의가 필요하다

사용 claim 13건 / evidence 전체 19건 (미사용 6건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 3곳 (hbr 6, theory-canon 6, mckinsey-insights 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | hbr 46% | ❌ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 20~30년 | 남은 쟁점 53행 | ❌ 근거 없음 |

## 4. 근거 주석 누락 의심 (사람 검토)

주석 없는 문단 중 정량·인용 표현이 있는 것 — 근거를 달았는지 확인한다.

| 위치 | 사유 | 문장 |
|---|---|---|
| "실패해도 괜찮다"만으로는 부족하다 — AI 실험 문화의 절반짜리 처방 6행 | 인용 표현 | **TL;DR** - AI 실험을 늘리려는 조직이 "실패해도 괜찮다"는 메시지에 집중하지만, 심리적 안전감 … |

## 5. 참고자료 (실사용 문서만)

- **hbr**: 4 Steps to Transform the “Middle Office” with AI / AI Experiments Need Domain Experts. Here’s How to Support Them. / AI and IT Teams Often Clash. But They Don’t Have To. / Can an AI-Powered Scribe Curb Physician Burnout? / The Hidden Realities of AI Adoption / Why Great Turnarounds Start with Culture, Not Strategy
- **mckinsey-insights**: AI transformations: Views from AMD, Dell, Liquid AI, and Mercedes-Benz
- **theory-canon**: 심리적 안전감 (Psychological Safety)

## 6. 지적 사항

- ❌ 실패 · **미등록 claim** — evidence에 없는 claim ID `1A0330E4405EA14D9376DB4154B`를 인용
  - 위치: 남은 쟁점 / 53행: “개인 체감과 조직 성과의 간극에는 경합 설명이 있다.”
- ❌ 실패 · **단일 출처 편중** — `hbr` 6/13건 = 46% — 40% 초과
- ❌ 실패 · **수치 근거 없음** — 본문 수치 “20~30년”가 사용 claim의 metric·text에 없음
  - 위치: 남은 쟁점 / 53행: “개인 체감과 조직 성과의 간극에는 경합 설명이 있다.”
- ⚠️ 경고 · **참고자료 실사용 없음** — 사용 claim과 연결되지 않는 참고자료 항목 — 실사용만 남긴다: “MIT SMR: Creating Shared Prosperity With AI”
- ⚠️ 경고 · **근거 주석 누락 의심** — 인용 표현이 있는데 `<!-- claims: ... -->` 주석이 없음
  - 위치: "실패해도 괜찮다"만으로는 부족하다 — AI 실험 문화의 절반짜리 처방 / 6행: “**TL;DR** - AI 실험을 늘리려는 조직이 "실패해도 괜찮다"는 메시지에 집중하지만, 심리적 안전감 이론의 원전은 안전…”
