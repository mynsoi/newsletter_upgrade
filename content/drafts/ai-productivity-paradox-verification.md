# 검증 리포트 (실사용 기준) — ai-productivity-paradox

대상: `content/published/ai-productivity-paradox.md` · 증거: `content/evidence/ai-productivity-paradox.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[아낀 시간에는 다음 자리가 필요합니다] 16행** — “- AI로 개인이 아낀 시간은 실재합니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한

**[개인은 빨라졌는데 성과표는 그대로입니다] 25행** — “체감은 착각이 아닙니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다

**[개인은 빨라졌는데 성과표는 그대로입니다] 28행** — “간극은 좁혀지지도 않습니다.”
- `1A0612A86DC02A2F6A7FAC65756` · josh-bersin · T2 · cautious/opinion — AI 도구의 기술 성능 향상 속도와 조직의 비즈니스 생산성 향상 속도 간에 격차가 증가하고 있다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다

**[개인은 빨라졌는데 성과표는 그대로입니다] 31행** — “그러면 아낀 시간은 어디로 갔을까요.”
- `1A06147EAA51520609B13FD56B2` · worklytics-blog · T4 · conditional/data — 한 배포에서 주간 절감 시간이 약 1,240시간으로 연간 생산성 가치 $2.4M에 해당하며, 자동화 가능한 업무의 68%는 여

**[개인은 빨라졌는데 성과표는 그대로입니다] 34행** — “지침도 없습니다.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 39행** — “이 어긋남에는 이름이 있습니다.”
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 42행** — “후속 연구는 이 역량을 둘로 나눕니다.”
- `1A0607D5137D6B024DB55C20055` · theory-canon · T1 · neutral/theory — (Zahra & George 2002, 재개념화) 흡수역량을 잠재적 흡수역량(획득·동화)과 실현된 흡수역량(변환·활용)의 두 
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 45행** — “더 오래된 연구도 같은 곳을 가리킵니다.”
- `1A0607DF63454168F88ACB2DAE6` · theory-canon · T1 · neutral/theory — 기술 시스템만 최적화하는 설계는 사회 시스템(협동 구조·역할 관계)을 훼손해 전체 성과를 떨어뜨릴 수 있다 (탄광 장벽식 채탄

**[통로를 먼저 판 조직은 결과가 다릅니다] 50행** — “이론이 맞다면 통로를 만든 조직은 성과가 달라야 합니다.”
- `1A0611FD78092D819824F7C0CD5` · mckinsey-insights · T2 · optimistic/data — AI 도입에 성공한 기업들은 투자 1달러당 평균 3달러의 증분 EBITDA를 실현했다

**[통로를 먼저 판 조직은 결과가 다릅니다] 53행** — “차이는 도입 순서에서 드러납니다.”
- `1A0640B7F8B28E2DE659DBDFA0C` · mckinsey-insights · T2 · optimistic/survey — 프로세스 재설계 후 AI를 도입한 조직이 기존 업무 방식에 AI를 덧붙인 조직보다 생산성 향상이 크다

**[통로를 먼저 판 조직은 결과가 다릅니다] 56행** — “전체 그림은 냉정합니다.”
- `1A0614191F9C213B9A8CE686DFB` · bcg-publications · T2 · optimistic/survey — BCG 2026 AI 레이더 설문에서 CEO들의 AI ROI에 대한 낙관도가 1년 전보다 높아졌다
- `1A061419353AEB682D9B0086FA3` · bcg-publications · T2 · cautious/survey — 실제로 비용 감소나 수익 증가로 측정되는 의미 있는 AI 가치를 얻고 있는 기업의 비중은 매우 낮다
- `1A059B60EA5B8BE66BBA731A360` · bain-insights · T2 · cautious/survey — 산업 분야 CEO의 대다수는 자신들의 AI 프로그램이 기대에 미치지 못하고 있다고 인식하며, 이유는 역량 부족, 확장 실패한 

**[우리 조직에 적용해본다면] 61행** — “통로를 만든다는 말은 거창하지 않습니다.”
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
| 80% | 개인은 빨라졌는데 성과표는 그대로입니다 25행 | ✅ 사용 claim에 있음 |
| 37% | 개인은 빨라졌는데 성과표는 그대로입니다 25행 | ✅ 사용 claim에 있음 |
| 10~20% | 개인은 빨라졌는데 성과표는 그대로입니다 28행 | ✅ 사용 claim에 있음 |
| 68% | 개인은 빨라졌는데 성과표는 그대로입니다 31행 | ✅ 사용 claim에 있음 |
| 66% | 개인은 빨라졌는데 성과표는 그대로입니다 34행 | ✅ 사용 claim에 있음 |
| 2배 | 통로를 먼저 판 조직은 결과가 다릅니다 53행 | ✅ 사용 claim에 있음 |
| 1년 | 통로를 먼저 판 조직은 결과가 다릅니다 56행 | ✅ 사용 claim에 있음 |
| 6% | 통로를 먼저 판 조직은 결과가 다릅니다 56행 | ✅ 사용 claim에 있음 |
| 90% | 통로를 먼저 판 조직은 결과가 다릅니다 56행 | ✅ 사용 claim에 있음 |
| 4주 | 우리 조직에 적용해본다면 66행 | — 해당 없음 · 처방 값(실행 제안) |
| 2주 | 우리 조직에 적용해본다면 66행 | — 해당 없음 · 처방 값(실행 제안) |

처방 값 2건은 근거 대조 대상이 아니다 — 액션에서 제안한 기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다.

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling | 우리 조직에 적용해본다면 64행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **bain-insights**: Industrial CEOs: Is AI the Least of Their Worries? / Why Pharma Transformations Stall—and How to Fix Them
- **bcg-publications**: BCG AI at Work 2026 (Fourth Edition): Strategy Matters More Than Tools — survey slideshow / Look Past Productivity to Get Real Value from AI
- **hr-bulletin**: “일 할 시간이 없다” / 데이터로 엿보는 구성원의 마음
- **josh-bersin**: The Rise Of The Supermanager (2025-10-20) / The Rise Of The Supermanager: A New Role In The World of AI (2025-09-23)
- **mckinsey-insights**: Beyond the copilot: Scaling the agentic product development life cycle / The new management playbook for AI: How to move faster and create more value / The state of AI in 2026: On the road to ROI
- **theory-canon**: 사회기술시스템 이론 (Sociotechnical Systems Theory) / 흡수역량 (Absorptive Capacity)
- **worklytics-blog**: How to Identify Which Tasks Employees Automate with AI  | Worklytics

## 7. 지적 사항

없음.

---

<!-- 수기 메모 (verify_article.py 재실행 시 덮어써진다) -->

## 8. 이 리포트가 가리키는 본문

2026-09-08 발행본 본문을 재작성본 **v2.2**로 교체한 뒤 다시 돌린 결과다.
2026-09-04 승인 시점의 리포트(이전 본문 기준)는 git 이력에 있다 —
`git show 2b21cda:content/drafts/ai-productivity-paradox-verification.md`.

- 상태: **승인**(재승인 완료 · `articles.status='approved'`, `rubric_score=NULL`)
- 루브릭 채점은 생략하기로 했다(2026-09-08 운영 판단). `rubric_score`가 비어 있는 것은
  누락이 아니라 그 결정의 결과다.
- 내부 자료 대조·루브릭 자체 채점·삭제된 고지 기록은
  `content/drafts/ai-productivity-paradox-v2-verification.md` 8~10장에 있다.
- 승인 게이트 ⑥ 4항목(톤·경영층 인용·검증 플래그·저작권) 전건 통과 — 2026-09-08 사람 확인,
  특이사항 없음. 내부 자료 인용의 발언 맥락과 이론 경계 조건·표본 한정 고지를 뺀 판단을
  함께 확인했다.
