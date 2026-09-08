# 검증 리포트 (실사용 기준) — style-test-2

대상: `content/drafts/style-test-2.md` · 증거: `content/evidence/ai-productivity-paradox.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 1건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[세 줄 요약] 16행** — “- 개인이 AI로 빨라졌다는 보고는 넘치는데 회사 전체 손익은 작년과 같습니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[세 줄 요약] 21행** — “McKinsey가 해마다”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다

**[세 줄 요약] 24행** — “협업 데이터를 실제로 들여다보는 Worklytics의 도입 사례 분석에도 비슷한 장면이 있습니다.”
- `1A06147EAA51520609B13FD56B2` · worklytics-blog · T4 · conditional/data — 한 배포에서 주간 절감 시간이 약 1,240시간으로 연간 생산성 가치 $2.4M에 해당하며, 자동화 가능한 업무의 68%는 여

**[개인이 빨라져도 조직은 그만큼 빨라지지 않습니다] 29행** — “두 장면은 예외가 아닙니다.”
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A0612A86DC02A2F6A7FAC65756` · josh-bersin · T2 · cautious/opinion — AI 도구의 기술 성능 향상 속도와 조직의 비즈니스 생산성 향상 속도 간에 격차가 증가하고 있다

**[개인이 빨라져도 조직은 그만큼 빨라지지 않습니다] 32행** — “Bain은 기능별로 흩어진 AI 도입을 이유로 지목합니다.”
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다

**[조직의 실력은 개인 실력의 합이 아닙니다] 37행** — “이 어긋남을 오래전에 정리해 둔 개념이 있습니다.”
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다

**[조직의 실력은 개인 실력의 합이 아닙니다] 40행** — “뒤이은 연구는 흡수역량을 둘로 나눴습니다.”
- `1A0607D5137D6B024DB55C20055` · theory-canon · T1 · neutral/theory — (Zahra & George 2002, 재개념화) 흡수역량을 잠재적 흡수역량(획득·동화)과 실현된 흡수역량(변환·활용)의 두 
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[조직의 실력은 개인 실력의 합이 아닙니다] 45행** — “1951년 영국 탄광 연구에서 나온 사회기술시스템 이론도 같은 자리를 짚습니다.”
- `1A0607DF63454168F88ACB2DAE6` · theory-canon · T1 · neutral/theory — 기술 시스템만 최적화하는 설계는 사회 시스템(협동 구조·역할 관계)을 훼손해 전체 성과를 떨어뜨릴 수 있다 (탄광 장벽식 채탄

**[조직의 실력은 개인 실력의 합이 아닙니다] 48행** — “두 이론 모두 한계가 있습니다.”
- `1A0607D51ED29068A42FB970DB9` · theory-canon · T1 · conditional/theory — 흡수역량은 다수 연구에서 R&D 지출로 대리측정되어 개념과 측정의 괴리가 크다는 비판이 있다(reification 비판, La

**[아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다] 53행** — “그렇다면 실제로 빠져 있는 것은 무엇일까요.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한

**[아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다] 56행** — “오래된 경영학 논문 한 편이 같은 말을 합니다.”
- `1A0607DAD69753F46F212F204D2` · theory-canon · T1 · neutral/theory — 선언된 목표보다 실제로 측정·보상되는 것이 행동을 지배한다

**[아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다] 59행** — “반대편 이야기도 분명히 있습니다.”
- `1A0611FD78092D819824F7C0CD5` · mckinsey-insights · T2 · optimistic/data — AI 도입에 성공한 기업들은 투자 1달러당 평균 3달러의 증분 EBITDA를 실현했다
- `1A0614191F9C213B9A8CE686DFB` · bcg-publications · T2 · optimistic/survey — BCG 2026 AI 레이더 설문에서 CEO들의 AI ROI에 대한 낙관도가 1년 전보다 높아졌다
- `1A061419353AEB682D9B0086FA3` · bcg-publications · T2 · cautious/survey — 실제로 비용 감소나 수익 증가로 측정되는 의미 있는 AI 가치를 얻고 있는 기업의 비중은 매우 낮다

**[아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다] 62행** — “성공한 쪽이 돈을 쓴 자리를 보면 방향이 더 분명해집니다.”
- `1A0611C09CA8CDC985C4E4BFBE1` · mckinsey-insights · T2 · optimistic/opinion — 에이전틱 기술 도입에 성공하는 조직은 기술 투자 1달러당 프로세스 재설계에 3달러, 역량 구축과 채택에 5달러를 지출하는 1:

**[우리 회의실에서는 무엇을 바꿀 수 있을까요] 67행** — “시선을 안으로 돌려 봅니다.”
- `1A0640CE8D14EF1CF80125300E2` · hr-bulletin · T3 · neutral/theory — 직장의 낮은 생산성은 기술 부족이나 개인의 태만이 아니라 일의 구조와 조직 문화에서 비롯될 수 있다
- `1A061413509032C29FFD314F9FF` · hr-bulletin · T3 · conditional/opinion — 생산성 개선을 위해서는 AI와 기술뿐만 아니라 모든 구성원을 새로운 업무 방식으로 전환하고 업무 흐름에서 숙련도를 높일 수 있

**[우리 회의실에서는 무엇을 바꿀 수 있을까요] 70행** — “우리 조직에 적용해 본다면 출발점은 팀입니다.”
- `1A061413509032C29FFD314F9FF` · hr-bulletin · T3 · conditional/opinion — 생산성 개선을 위해서는 AI와 기술뿐만 아니라 모든 구성원을 새로운 업무 방식으로 전환하고 업무 흐름에서 숙련도를 높일 수 있

**[우리 회의실에서는 무엇을 바꿀 수 있을까요] 73행** — “남는 물음도 하나 있습니다.”
- `1A0612F815EE453599BFC7968DD` · charter · T3 · cautious/data — 최근 몇 년간 노동 생산성은 기록적 수준으로 올랐지만 근로자의 GDP 점유율은 기록적 수준으로 내려갔다

사용 claim 20건 / evidence 전체 40건 (미사용 20건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 8곳 (theory-canon 6, mckinsey-insights 4, bcg-publications 3, josh-bersin 2, hr-bulletin 2, worklytics-blog 1, bain-insights 1, charter 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | theory-canon 30% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 20건 | - 1행 | ✅ 사용 claim에 있음 |
| 80% | 세 줄 요약 21행 | ✅ 사용 claim에 있음 |
| 37% | 세 줄 요약 21행 | ✅ 사용 claim에 있음 |
| 68% | 세 줄 요약 24행 | ✅ 사용 claim에 있음 |
| 10~20% | 개인이 빨라져도 조직은 그만큼 빨라지지 않습니다 29행 | ✅ 사용 claim에 있음 |
| 66% | 아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다 53행 | ✅ 사용 claim에 있음 |
| 82% | 아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다 59행 | ✅ 사용 claim에 있음 |
| 6% | 아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다 59행 | ✅ 사용 claim에 있음 |
| 6% | 아낀 시간을 어디에 쓸지 아무도 말해주지 않았습니다 59행 | ✅ 사용 claim에 있음 |
| 4주 | 우리 회의실에서는 무엇을 바꿀 수 있을까요 70행 | — 해당 없음 · 처방 값(실행 제안) |

처방 값 1건은 근거 대조 대상이 아니다 — 액션에서 제안한 기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다.

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

본문에 내부 자료 인용 없음.

## 5. 근거 주석 누락 의심 (사람 검토)

주석 없는 문단 중 정량·인용 표현이 있는 것 — 근거를 달았는지 확인한다.

| 위치 | 사유 | 문장 |
|---|---|---|
| - 1행 | 수치(20건) | --- slug: ai-productivity-paradox angle: B — 아낀 시간이 조직으로 건너갈… |

## 6. 참고자료 (실사용 문서만)

- **bain-insights**: Why Pharma Transformations Stall—and How to Fix Them
- **bcg-publications**: BCG AI at Work 2026 (Fourth Edition): Strategy Matters More Than Tools — survey slideshow / Look Past Productivity to Get Real Value from AI
- **charter**: A new ‘social contract’ that helps all workers benefit from AI
- **hr-bulletin**: “일 할 시간이 없다” / 데이터로 엿보는 구성원의 마음
- **josh-bersin**: The Rise Of The Supermanager / The Rise Of The Supermanager: A New Role In The World of AI
- **mckinsey-insights**: How to close the agentic adoption gap / The new management playbook for AI: How to move faster and create more value / The state of AI in 2026: On the road to ROI
- **theory-canon**: A를 보상하며 B를 바라는 어리석음 (On the Folly of Rewarding A, While Hoping for B) / 사회기술시스템 이론 (Sociotechnical Systems Theory) / 흡수역량 (Absorptive Capacity)
- **worklytics-blog**: How to Identify Which Tasks Employees Automate with AI  | Worklytics

## 7. 지적 사항

- ⚠️ 경고 · **근거 주석 누락 의심** — 수치(20건)이 있는데 `<!-- claims: ... -->` 주석이 없음
  - 위치: (제목 없음) / 1행: “--- slug: ai-productivity-paradox angle: B — 아낀 시간이 조직으로 건너갈 통로가 없다”
