# 검증 리포트 (실사용 기준) — ai-productivity-paradox

대상: `content/drafts/ai-productivity-paradox-gpt6-comparison.md` · 증거: `content/evidence/ai-productivity-paradox.json`
작성 모델: GPT-6 (현재 Codex 세션; 정확한 배포 모델 ID는 확인되지 않음) (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[AI로 아낀 시간, 다음에 할 일까지 정했습니까] 10행** — “- AI로 개인의 일은 빨라졌지만 회사 성과까지 함께 좋아지지는 않았습니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한

**[개인이 빨라진 만큼 회사도 나아졌을까요] 20행** — “이런 어긋남은 설문에서도 보입니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다

**[개인이 빨라진 만큼 회사도 나아졌을까요] 23행** — “수백 개 기업을 인터뷰한 Josh Bersin도 도구의 발전 속도를 조직의 생산성이 따라가지 못한다고 봅니다.”
- `1A0612A86DC02A2F6A7FAC65756` · josh-bersin · T2 · cautious/opinion — AI 도구의 기술 성능 향상 속도와 조직의 비즈니스 생산성 향상 속도 간에 격차가 증가하고 있다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다

**[개인이 빨라진 만큼 회사도 나아졌을까요] 26행** — “Worklytics가 분석한 도입 사례에서는 주당 약 1,240시간을 아꼈지만 자동화 가능한 업무의 68%는 여전히 AI 없이 처리했습니다.”
- `1A06147EAA51520609B13FD56B2` · worklytics-blog · T4 · conditional/data — 한 배포에서 주간 절감 시간이 약 1,240시간으로 연간 생산성 가치 $2.4M에 해당하며, 자동화 가능한 업무의 68%는 여

**[개인이 빨라진 만큼 회사도 나아졌을까요] 29행** — “아낀 시간의 쓰임도 불분명합니다.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다

**[각자가 배운 것을 함께 쓸 수 있어야 합니다] 34행** — “개인의 변화가 조직 성과로 이어지는 조건을 설명하는 개념이 있습니다.”
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다

**[각자가 배운 것을 함께 쓸 수 있어야 합니다] 37행** — “후속 연구는 지식을 받아들이는 잠재적 흡수역량과 실제 업무에 쓰는 실현된 흡수역량을 구분합니다.”
- `1A0607D5137D6B024DB55C20055` · theory-canon · T1 · neutral/theory — (Zahra & George 2002, 재개념화) 흡수역량을 잠재적 흡수역량(획득·동화)과 실현된 흡수역량(변환·활용)의 두 
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[각자가 배운 것을 함께 쓸 수 있어야 합니다] 40행** — “1951년 영국 탄광 연구에서 출발한 사회기술시스템 이론도 기술과 협업을 함께 살핍니다.”
- `1A0607DF63454168F88ACB2DAE6` · theory-canon · T1 · neutral/theory — 기술 시스템만 최적화하는 설계는 사회 시스템(협동 구조·역할 관계)을 훼손해 전체 성과를 떨어뜨릴 수 있다 (탄광 장벽식 채탄

**[일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다] 45행** — “협업과 업무 구조까지 살피면 다른 결과도 보입니다.”
- `1A0611FD78092D819824F7C0CD5` · mckinsey-insights · T2 · optimistic/data — AI 도입에 성공한 기업들은 투자 1달러당 평균 3달러의 증분 EBITDA를 실현했다

**[일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다] 48행** — “McKinsey의 소프트웨어 개발 조직 분석에서는 **업무 절차부터 바꾸고 AI를 도입한 조직이 뚜렷한 생산성 향상을 거둘 확률이 2배 이상 높았습니다.** 비교…”
- `1A0640B7F8B28E2DE659DBDFA0C` · mckinsey-insights · T2 · optimistic/survey — 프로세스 재설계 후 AI를 도입한 조직이 기존 업무 방식에 AI를 덧붙인 조직보다 생산성 향상이 크다

**[일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다] 51행** — “다만 이런 성과가 널리 나타난 것은 아닙니다.”
- `1A0614191F9C213B9A8CE686DFB` · bcg-publications · T2 · optimistic/survey — BCG 2026 AI 레이더 설문에서 CEO들의 AI ROI에 대한 낙관도가 1년 전보다 높아졌다
- `1A061419353AEB682D9B0086FA3` · bcg-publications · T2 · cautious/survey — 실제로 비용 감소나 수익 증가로 측정되는 의미 있는 AI 가치를 얻고 있는 기업의 비중은 매우 낮다
- `1A059B60EA5B8BE66BBA731A360` · bain-insights · T2 · cautious/survey — 산업 분야 CEO의 대다수는 자신들의 AI 프로그램이 기대에 미치지 못하고 있다고 인식하며, 이유는 역량 부족, 확장 실패한 

**[우리 조직에 적용해본다면] 56행** — “그 출발점은 평소 일이 돌아가는 방식을 살피는 데 있습니다.”
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
| 80% | 개인이 빨라진 만큼 회사도 나아졌을까요 20행 | ✅ 사용 claim에 있음 |
| 37% | 개인이 빨라진 만큼 회사도 나아졌을까요 20행 | ✅ 사용 claim에 있음 |
| 10~20% | 개인이 빨라진 만큼 회사도 나아졌을까요 23행 | ✅ 사용 claim에 있음 |
| 68% | 개인이 빨라진 만큼 회사도 나아졌을까요 26행 | ✅ 사용 claim에 있음 |
| 66% | 개인이 빨라진 만큼 회사도 나아졌을까요 29행 | ✅ 사용 claim에 있음 |
| 2배 | 일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다 48행 | ✅ 사용 claim에 있음 |
| 6% | 일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다 51행 | ✅ 사용 claim에 있음 |
| 90% | 일하는 방식을 먼저 바꾼 조직에서는 성과가 났습니다 51행 | ✅ 사용 claim에 있음 |
| 4주 | 우리 조직에 적용해본다면 62행 | — 해당 없음 · 처방 값(실행 제안) |
| 2주 | 우리 조직에 적용해본다면 62행 | — 해당 없음 · 처방 값(실행 제안) |

처방 값 2건은 근거 대조 대상이 아니다 — 액션에서 제안한 기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다.

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

내부 자료를 읽지 못해 대조하지 못했다 (DB 미연결) — 사람 확인 필요.

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
