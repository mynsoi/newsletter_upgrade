# 검증 리포트 (실사용 기준) — ai-productivity-paradox

대상: `content/drafts/ai-productivity-paradox-v2.md` · 증거: `content/evidence/ai-productivity-paradox.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[아낀 시간에는 다음 자리가 필요합니다] 13행** — “- AI로 개인이 아낀 시간은 실재합니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한

**[개인은 빨라졌는데 성과표는 그대로입니다] 22행** — “체감이 착각인 것은 아닙니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다

**[개인은 빨라졌는데 성과표는 그대로입니다] 25행** — “간극이 좁혀지는 중도 아닙니다.”
- `1A0612A86DC02A2F6A7FAC65756` · josh-bersin · T2 · cautious/opinion — AI 도구의 기술 성능 향상 속도와 조직의 비즈니스 생산성 향상 속도 간에 격차가 증가하고 있다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다

**[개인은 빨라졌는데 성과표는 그대로입니다] 28행** — “그러면 아낀 시간은 어디로 갔을까요.”
- `1A06147EAA51520609B13FD56B2` · worklytics-blog · T4 · conditional/data — 한 배포에서 주간 절감 시간이 약 1,240시간으로 연간 생산성 가치 $2.4M에 해당하며, 자동화 가능한 업무의 68%는 여

**[개인은 빨라졌는데 성과표는 그대로입니다] 31행** — “자리가 비는 것으로 끝나지 않습니다.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 36행** — “이 어긋남에는 오래전에 붙은 이름이 있습니다.”
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 39행** — “후속 연구는 이 역량을 둘로 나눕니다.”
- `1A0607D5137D6B024DB55C20055` · theory-canon · T1 · neutral/theory — (Zahra & George 2002, 재개념화) 흡수역량을 잠재적 흡수역량(획득·동화)과 실현된 흡수역량(변환·활용)의 두 
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 42행** — “더 오래된 연구도 같은 곳을 가리킵니다.”
- `1A0607DF63454168F88ACB2DAE6` · theory-canon · T1 · neutral/theory — 기술 시스템만 최적화하는 설계는 사회 시스템(협동 구조·역할 관계)을 훼손해 전체 성과를 떨어뜨릴 수 있다 (탄광 장벽식 채탄

**[통로를 먼저 판 조직은 결과가 다릅니다] 47행** — “이론이 맞다면 통로를 만든 조직은 성과가 달라야 합니다.”
- `1A0611FD78092D819824F7C0CD5` · mckinsey-insights · T2 · optimistic/data — AI 도입에 성공한 기업들은 투자 1달러당 평균 3달러의 증분 EBITDA를 실현했다

**[통로를 먼저 판 조직은 결과가 다릅니다] 50행** — “차이는 도입 순서에서 드러납니다.”
- `1A0640B7F8B28E2DE659DBDFA0C` · mckinsey-insights · T2 · optimistic/survey — 프로세스 재설계 후 AI를 도입한 조직이 기존 업무 방식에 AI를 덧붙인 조직보다 생산성 향상이 크다

**[통로를 먼저 판 조직은 결과가 다릅니다] 53행** — “전체 그림은 훨씬 냉정합니다.”
- `1A0614191F9C213B9A8CE686DFB` · bcg-publications · T2 · optimistic/survey — BCG 2026 AI 레이더 설문에서 CEO들의 AI ROI에 대한 낙관도가 1년 전보다 높아졌다
- `1A061419353AEB682D9B0086FA3` · bcg-publications · T2 · cautious/survey — 실제로 비용 감소나 수익 증가로 측정되는 의미 있는 AI 가치를 얻고 있는 기업의 비중은 매우 낮다
- `1A059B60EA5B8BE66BBA731A360` · bain-insights · T2 · cautious/survey — 산업 분야 CEO의 대다수는 자신들의 AI 프로그램이 기대에 미치지 못하고 있다고 인식하며, 이유는 역량 부족, 확장 실패한 

**[우리 조직에 적용해본다면] 58행** — “통로를 만든다는 말은 거창하지 않습니다.”
- `1A0640CE8D14EF1CF80125300E2` · hr-bulletin · T3 · neutral/theory — 직장의 낮은 생산성은 기술 부족이나 개인의 태만이 아니라 일의 구조와 조직 문화에서 비롯될 수 있다
- `1A061413509032C29FFD314F9FF` · hr-bulletin · T3 · conditional/opinion — 생산성 개선을 위해서는 AI와 기술뿐만 아니라 모든 구성원을 새로운 업무 방식으로 전환하고 업무 흐름에서 숙련도를 높일 수 있

사용 claim 18건 / evidence 전체 40건 (미사용 22건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 7곳 (mckinsey-insights 4, theory-canon 4, bcg-publications 3, josh-bersin 2, bain-insights 2, hr-bulletin 2, worklytics-blog 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | mckinsey-insights 22% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 80% | 개인은 빨라졌는데 성과표는 그대로입니다 22행 | ✅ 사용 claim에 있음 |
| 37% | 개인은 빨라졌는데 성과표는 그대로입니다 22행 | ✅ 사용 claim에 있음 |
| 10~20% | 개인은 빨라졌는데 성과표는 그대로입니다 25행 | ✅ 사용 claim에 있음 |
| 68% | 개인은 빨라졌는데 성과표는 그대로입니다 28행 | ✅ 사용 claim에 있음 |
| 66% | 개인은 빨라졌는데 성과표는 그대로입니다 31행 | ✅ 사용 claim에 있음 |
| 2배 | 통로를 먼저 판 조직은 결과가 다릅니다 50행 | ✅ 사용 claim에 있음 |
| 1년 | 통로를 먼저 판 조직은 결과가 다릅니다 53행 | ✅ 사용 claim에 있음 |
| 6% | 통로를 먼저 판 조직은 결과가 다릅니다 53행 | ✅ 사용 claim에 있음 |
| 90% | 통로를 먼저 판 조직은 결과가 다릅니다 53행 | ✅ 사용 claim에 있음 |
| 4주 | 우리 조직에 적용해본다면 63행 | — 해당 없음 · 처방 값(실행 제안) |
| 2주 | 우리 조직에 적용해본다면 63행 | — 해당 없음 · 처방 값(실행 제안) |

처방 값 2건은 근거 대조 대상이 아니다 — 액션에서 제안한 기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다.

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling | 우리 조직에 적용해본다면 61행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **bain-insights**: Industrial CEOs: Is AI the Least of Their Worries? / Why Pharma Transformations Stall—and How to Fix Them
- **bcg-publications**: BCG AI at Work 2026 (Fourth Edition): Strategy Matters More Than Tools — survey slideshow / Look Past Productivity to Get Real Value from AI
- **hr-bulletin**: “일 할 시간이 없다” / 데이터로 엿보는 구성원의 마음
- **josh-bersin**: The Rise Of The Supermanager / The Rise Of The Supermanager: A New Role In The World of AI
- **mckinsey-insights**: Beyond the copilot: Scaling the agentic product development life cycle / The new management playbook for AI: How to move faster and create more value / The state of AI in 2026: On the road to ROI
- **theory-canon**: 사회기술시스템 이론 (Sociotechnical Systems Theory) / 흡수역량 (Absorptive Capacity)
- **worklytics-blog**: How to Identify Which Tasks Employees Automate with AI  | Worklytics

## 7. 지적 사항

없음.

---

<!-- 아래 8~10장은 draft.md ⑤의 수기 항목이다. `verify_article.py` 재실행 시 덮어써지므로
     재실행 후에는 이 블록을 다시 붙인다. 판본: v2.1 (2026-09-08 팀장 피드백 7건 반영) -->

## 8. 내부 자료 대조 (수기 — 간접 서술이라 기계 인용 대조 대상이 아님)

대상 문서: `internal_docs` `leadership-messages/2026-06-이천포럼-패널토의.md`
(제목: 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling · `api_eligible=1` · `effective_date=2026-06-01`)
D1 발행본이 사용한 문서와 동일하다.

| # | 본문 서술 | 원문 근거 | 판정 |
|---|---|---|---|
| 1 | AI로 생기는 여유를 사람이 남는 문제가 아니라 남는 시간을 어디에 쓸 것인가의 문제로 규정 | 답변 ① — Free Human Resource를 '남는 인력'의 문제로 보지 않는다, 남는 시간을 어디에 쓸 것인가의 문제 | ✅ 일치 |
| 2 | 기준과 절차가 정해진 일은 AI에게 넘기고, 불확실한 상황에서 판단하고 협업해야 하는 일에 사람의 시간을 모은다 | 답변 ① — 프로세스·기준이 정해지고 단독 수행 가능한 업무는 AI가 수행 / 복잡한 시나리오 판단·이해관계자 협업·불확실성 높은 업무에 인력과 업무 포트폴리오를 조정 | ✅ 일치 |

**v2.1에서 뺀 것** — Translator·Two-Track 육성·Human-Centered AX를 다룬 두 번째 내부 문단은
팀장 피드백(세부적이라 생략 가능)으로 삭제했다. 남은 내부 서술은 위 2건이다.

**의도적 미사용** — 원문의 수치·계획(세부 Task 건수, 업무 유형별 비중, 업무시간 목표 비중,
AX 인프라 투자 금액, 외부 인재 영입 계획, Citadel 수익 수치)은 본문에 옮기지 않았다.
`claims` 테이블 밖의 수치이므로 CLAUDE.md 절대 규칙 3에 걸리고, 검증기의 수치 대조에서도
근거 없음으로 잡힌다.

**형식 준수** — 내부 발언을 직접 인용부호 없이 "우리" 시점 간접 서술로 녹였고(article_style 1절),
2026년을 표기했다(5절, 기계 검증 4장에서 ✅).

**사람 확인 항목 (기계 검증 밖)** — 발언 맥락 왜곡 여부. 위 2번은 원문이 업무 유형별 비중과
목표치를 근거로 든 대목을 비중 없이 방향만 요약한 것이므로, 원문 취지와 어긋나지 않는지
발행 전 확인이 필요하다.

## 9. 루브릭 자체 채점 (eval/rubric.md · 정본은 사람 채점 · v2.1 기준)

| # | 항목 | 점수 | 사유 |
|---|---|---|---|
| 1 | 논지 선명성 | 2 | "아낀 시간이 조직으로 건너갈 통로가 없다"로 한 문장 요약되지만 반증 조건이 본문에 없다 — 앵글 파일에만 있다 (선례: `eval/scores/ai-productivity-paradox-claude.md` 동일 사유). v2.1에서 이론 유보 문단도 빠져 경계 조건 고지가 없다 |
| 2 | 출처 다양성 | 3 | 독립 출처 7곳, T1 4건·T2 11건 |
| 3 | 상반 관점 처리 | 3 | 낙관 근거(1달러당 3달러·재설계 조직의 2배 확률·CEO 낙관도)와 신중 근거(6%·90%)를 함께 싣고, 갈리는 이유를 도입 순서로 설명했다 |
| 4 | 종합의 독창성 | 3 | 절감 시간의 지침 부재(BCG) × 사회적 통합 기제(흡수역량) × 재설계 선행(McKinsey)을 한 명제로 묶었다. 앵글 B는 발행본에서 이어받았다 |
| 5 | SK 맥락 적합성 | 3 | 이천포럼의 Free Human Resource 규정을 글의 "통로" 논지와 같은 질문으로 해석에 사용했다 (v2.1에서 개념 4개 → 1개로 축소, 발행본과 같은 깊이) |
| 6 | 실행 가능성 | 3 | 리더(이번 달 안에 모으고 쓸 곳 한 가지 선택 · 4주 뒤 이름으로 부를 수 있는가)와 실무자(주 1회 한 줄 기록 · 2주)의 몫이 각각 읽힌다 |
| 7 | 사실 정확성 | 3 | 본문 수치 7건 전부 사용 claim의 metric·text와 일치 (3장) |
| 8 | 문체 | 3 | 발행본의 감점 사유 2건(반복 지시어·결말 단언 공식)이 없고, v2 지적 사항(소제목 의인화·도입 인용절 종결·도입 장면의 구체성)도 v2.1에서 고쳤다 |

**합계 23/24.** 자체 채점이므로 항목 1·3·4는 사람 채점에서 갈릴 수 있다.
발행본과의 항목별 대조는 `eval/scores/ai-productivity-paradox-발행본-v2-비교채점-claude.md`.

## 10. 발행 승인 게이트 전 확인 사항

- 발행본(`content/published/ai-productivity-paradox.md`)은 수정하지 않았다.
- 분량 2,264자(공백 제외) — 지침 1,800~2,500자 범위 안 (v2 2,680자에서 감소).
- 금지 표현 목록 미운용 (2026-09 폐지 · `prompts/banned_phrases.txt` 없음).
- **삭제로 사라진 고지 2건** (팀장 판단으로 뺀 것이며 검증 실패 사유는 아니다)
  - 낙관 수치의 표본 한정 주의 — evidence `cautions` 3번("성공한 기업 표본에 한정된 값,
    전체 평균으로 확대 해석 금지"). 본문에서는 "성공 사례로 고른 기업 20곳"이라는 표현과
    바로 다음 문단의 6%·90%가 그 역할을 대신한다.
  - 흡수역량의 개념-측정 괴리 비판(`1A0607D51ED29068A42FB970DB9`) — 이론 경계 조건 고지가
    본문에 없다. 앵글 파일에는 남아 있다.
