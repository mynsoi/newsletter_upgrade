# 검증 리포트 (실사용 기준) — ai-productivity-paradox

대상: `content/drafts/ai-productivity-paradox-v3-layers.md` · 증거: `content/evidence/ai-productivity-paradox.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[아낀 시간에는 다음 자리가 필요합니다] 14행** — “- AI로 개인이 아낀 시간은 실재합니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한

**[개인은 빨라졌는데 성과표는 그대로입니다] 23행** — “체감은 착각이 아닙니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다

**[개인은 빨라졌는데 성과표는 그대로입니다] 26행** — “간극은 좁혀지지도 않습니다.”
- `1A0612A86DC02A2F6A7FAC65756` · josh-bersin · T2 · cautious/opinion — AI 도구의 기술 성능 향상 속도와 조직의 비즈니스 생산성 향상 속도 간에 격차가 증가하고 있다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다

**[개인은 빨라졌는데 성과표는 그대로입니다] 29행** — “그러면 아낀 시간은 어디로 갔을까요.”
- `1A06147EAA51520609B13FD56B2` · worklytics-blog · T4 · conditional/data — 한 배포에서 주간 절감 시간이 약 1,240시간으로 연간 생산성 가치 $2.4M에 해당하며, 자동화 가능한 업무의 68%는 여

**[개인은 빨라졌는데 성과표는 그대로입니다] 32행** — “지침도 없습니다.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 37행** — “이 어긋남에는 이름이 있습니다.”
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 40행** — “후속 연구는 이 역량을 둘로 나눕니다.”
- `1A0607D5137D6B024DB55C20055` · theory-canon · T1 · neutral/theory — (Zahra & George 2002, 재개념화) 흡수역량을 잠재적 흡수역량(획득·동화)과 실현된 흡수역량(변환·활용)의 두 
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[조직의 역량은 개인 역량을 더한 값이 아닙니다] 43행** — “더 오래된 연구도 같은 곳을 가리킵니다.”
- `1A0607DF63454168F88ACB2DAE6` · theory-canon · T1 · neutral/theory — 기술 시스템만 최적화하는 설계는 사회 시스템(협동 구조·역할 관계)을 훼손해 전체 성과를 떨어뜨릴 수 있다 (탄광 장벽식 채탄

**[통로를 먼저 판 조직은 결과가 다릅니다] 48행** — “이론이 맞다면 통로를 만든 조직은 성과가 달라야 합니다.”
- `1A0611FD78092D819824F7C0CD5` · mckinsey-insights · T2 · optimistic/data — AI 도입에 성공한 기업들은 투자 1달러당 평균 3달러의 증분 EBITDA를 실현했다

**[통로를 먼저 판 조직은 결과가 다릅니다] 51행** — “차이는 도입 순서에서 드러납니다.”
- `1A0640B7F8B28E2DE659DBDFA0C` · mckinsey-insights · T2 · optimistic/survey — 프로세스 재설계 후 AI를 도입한 조직이 기존 업무 방식에 AI를 덧붙인 조직보다 생산성 향상이 크다

**[통로를 먼저 판 조직은 결과가 다릅니다] 54행** — “전체 그림은 냉정합니다.”
- `1A0614191F9C213B9A8CE686DFB` · bcg-publications · T2 · optimistic/survey — BCG 2026 AI 레이더 설문에서 CEO들의 AI ROI에 대한 낙관도가 1년 전보다 높아졌다
- `1A061419353AEB682D9B0086FA3` · bcg-publications · T2 · cautious/survey — 실제로 비용 감소나 수익 증가로 측정되는 의미 있는 AI 가치를 얻고 있는 기업의 비중은 매우 낮다
- `1A059B60EA5B8BE66BBA731A360` · bain-insights · T2 · cautious/survey — 산업 분야 CEO의 대다수는 자신들의 AI 프로그램이 기대에 미치지 못하고 있다고 인식하며, 이유는 역량 부족, 확장 실패한 

**[우리 조직에 적용해본다면] 59행** — “통로를 만든다는 말은 거창하지 않습니다.”
- `1A0640CE8D14EF1CF80125300E2` · hr-bulletin · T3 · neutral/theory — 직장의 낮은 생산성은 기술 부족이나 개인의 태만이 아니라 일의 구조와 조직 문화에서 비롯될 수 있다
- `1A061413509032C29FFD314F9FF` · hr-bulletin · T3 · conditional/opinion — 생산성 개선을 위해서는 AI와 기술뿐만 아니라 모든 구성원을 새로운 업무 방식으로 전환하고 업무 흐름에서 숙련도를 높일 수 있

**[우리 조직에 적용해본다면] 65행** — “**임원의 자리에서 보면** 개인의 일은 빨라졌다는데 회사 이익은 달라지지 않았다면 원인을 구성원의 노력 부족에서 찾기는 어렵습니다.”
- `1A0611B62AAAE645DCE4AD5741A` · mckinsey-insights · T2 · cautious/survey — 개별 직원의 생산성 향상 효과에도 불구하고 기업 전체 EBIT 영향은 변화가 없다
- `1A059B749912D2D796717A8764B` · bain-insights · T2 · cautious/opinion — 기능별로 분산된 AI 도입은 각 팀의 생산성을 높이지만 팀 간 업무 연계의 문제는 해결하지 못한다
- `1A059B747B179648F58ABD6145A` · bain-insights · T2 · cautious/opinion — 제약사가 변화에 빠르게 대응할 수 있는 역량을 구축하지 못한 경우, AI 도입이 어제의 업무를 자동화하는 것으로 귀결되어 근본
- `1A0611C09CA8CDC985C4E4BFBE1` · mckinsey-insights · T2 · optimistic/opinion — 에이전틱 기술 도입에 성공하는 조직은 기술 투자 1달러당 프로세스 재설계에 3달러, 역량 구축과 채택에 5달러를 지출하는 1:

**[우리 조직에 적용해본다면] 70행** — “**팀장의 자리에서 보면** 아낀 시간은 팀이 일하는 방식의 문제입니다.”
- `1A06149CEE1D5B06DF881EC0048` · bcg-publications · T2 · cautious/survey — AI 도입으로 시간을 절감한 직원 중 66%가 절감된 시간을 어떻게 사용할지에 대한 지침을 거의 받지 못하거나 전혀 받지 못한
- `1A0607D5104DE01945F5624F6F4` · theory-canon · T1 · neutral/theory — (원개념) 흡수역량은 개인 수준 지식의 단순 합이 아니라 구성원 간 지식이 소통·연결되는 조직 구조에 의존한다
- `1A0607D521FDE54EF67456FFE97` · theory-canon · T1 · conditional/theory — (Zahra & George 후속 논의) 잠재적 흡수역량이 높아도 사회적 통합 기제가 없으면 실현된 흡수역량으로 이어지지 않을

**[우리 조직에 적용해본다면] 75행** — “**팀원의 자리에서 보면** AI로 줄인 시간이 결국 어디에 쓰였는지 가장 먼저 아는 사람은 자기 자신입니다.”
- `1A0611B63577F068A985377A9BE` · mckinsey-insights · T2 · optimistic/survey — AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A0612C89106DA3372FB4B2018E` · josh-bersin · T2 · cautious/opinion — 개인 단위의 생산성 향상은 최대 10~20% 수준에 그친다
- `1A0614933CB7B21D7D00348EFD6` · mckinsey-insights · T2 · conditional/case — 생성형 AI 지원으로 경험 부족한 상담사의 생산성과 서비스 품질이 가장 크게 개선되었으나, 숙련된 상담사의 지표는 개선되지 않

사용 claim 21건 / evidence 전체 40건 (미사용 19건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 7곳 (mckinsey-insights 6, theory-canon 4, bain-insights 3, bcg-publications 3, josh-bersin 2, hr-bulletin 2, worklytics-blog 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | mckinsey-insights 29% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 80% | 개인은 빨라졌는데 성과표는 그대로입니다 23행 | ✅ 사용 claim에 있음 |
| 37% | 개인은 빨라졌는데 성과표는 그대로입니다 23행 | ✅ 사용 claim에 있음 |
| 10~20% | 개인은 빨라졌는데 성과표는 그대로입니다 26행 | ✅ 사용 claim에 있음 |
| 68% | 개인은 빨라졌는데 성과표는 그대로입니다 29행 | ✅ 사용 claim에 있음 |
| 66% | 개인은 빨라졌는데 성과표는 그대로입니다 32행 | ✅ 사용 claim에 있음 |
| 2배 | 통로를 먼저 판 조직은 결과가 다릅니다 51행 | ✅ 사용 claim에 있음 |
| 1년 | 통로를 먼저 판 조직은 결과가 다릅니다 54행 | ✅ 사용 claim에 있음 |
| 6% | 통로를 먼저 판 조직은 결과가 다릅니다 54행 | ✅ 사용 claim에 있음 |
| 90% | 통로를 먼저 판 조직은 결과가 다릅니다 54행 | ✅ 사용 claim에 있음 |

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling | 우리 조직에 적용해본다면 62행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **bain-insights**: Industrial CEOs: Is AI the Least of Their Worries? / Why Pharma Transformations Stall—and How to Fix Them
- **bcg-publications**: BCG AI at Work 2026 (Fourth Edition): Strategy Matters More Than Tools — survey slideshow / Look Past Productivity to Get Real Value from AI
- **hr-bulletin**: “일 할 시간이 없다” / 데이터로 엿보는 구성원의 마음
- **josh-bersin**: The Rise Of The Supermanager (2025-10-20) / The Rise Of The Supermanager: A New Role In The World of AI (2025-09-23)
- **mckinsey-insights**: Beyond the copilot: Scaling the agentic product development life cycle / How to close the agentic adoption gap / The Economic Potential of Generative AI: The Next Productivity Frontier / The new management playbook for AI: How to move faster and create more value / The state of AI in 2026: On the road to ROI
- **theory-canon**: 사회기술시스템 이론 (Sociotechnical Systems Theory) / 흡수역량 (Absorptive Capacity)
- **worklytics-blog**: How to Identify Which Tasks Employees Automate with AI  | Worklytics

## 7. 지적 사항

없음.

---

<!-- 아래 8~10장은 draft-layers ⑤의 수기 항목이다. `verify_article.py` 재실행 시 덮어써지므로
     재실행 후에는 이 블록을 다시 붙인다. 판본: v3-layers (2026-09-15, 세그먼트 레이어 테스트 D1).
     루브릭 자체 채점은 사람 채점의 독립성을 지키려고 이 리포트에 싣지 않는다 —
     eval/scores/ai-productivity-paradox-v3-layers-claude.md (사람 채점 완료 후 열람). -->

## 8. 발행본(v2.2) 리포트와 비교

비교 대상: `content/drafts/ai-productivity-paradox-verification.md` (발행본 v2.2 · 2026-09-08).
코어 문장은 v2.2와 같고, 달라진 것은 적용 섹션의 3문단(리더·실무자 행동 혼재)이 레이어 3개로 바뀐 것뿐이다.

| 항목 | 발행본 v2.2 | v3-layers | 차이와 해석 |
|---|---|---|---|
| 판정 | 통과 (실패 0 · 경고 0) | 통과 (실패 0 · 경고 0) | 같음 |
| 사용 claim | 18건 | 21건 | +3 — `059B747B`(Bain) · `0611C09C`(McKinsey) · `0614933C`(McKinsey), 모두 레이어가 새로 인용 |
| 실사용 출처 수 | 7곳 | 7곳 | 같은 7곳. 레이어가 새 출처를 들이지 않았다 |
| 출처별 claim | mckinsey 4 · theory 4 · bcg 3 · bersin 2 · bain 2 · hr 2 · worklytics 1 | mckinsey 6 · theory 4 · bain 3 · bcg 3 · bersin 2 · hr 2 · worklytics 1 | McKinsey +2, Bain +1 |
| **최대 의존 출처 비율** | **mckinsey-insights 22%** (4/18) | **mckinsey-insights 29%** (6/21) | +7%p, 40% 상한 이내. 비율은 문단 수가 아니라 고유 claim 수 기준이다 |
| stance 분포 | 낙관 4 · 신중 7 · 조건부 3 · 중립 4 | 낙관 5 · 신중 8 · 조건부 4 · 중립 4 | 레이어가 세 방향을 하나씩 더했다. 상반 stance 조건 유지 |
| 수치 대조 | 근거 수치 9건 ✅ + 처방 값 2건(4주·2주) | 근거 수치 9건 ✅ + 처방 값 **0건** | 레이어에 기간·횟수 처방이 없다(가이드 의도대로). 임원 레이어의 1:3:5는 단위가 없어 검증기 정규식 밖 — 10장 수기 대조 |
| 근거 주석 누락 의심 | 0건 | 0건 | 같음 |
| 내부 자료 인용 대조 | 직접 인용 없음 · 시점 표기 ✅ 1건 | 직접 인용 없음 · 시점 표기 ✅ 1건 | 같은 이천포럼 문단(코어 공통 도입). 레이어는 내부 자료를 쓰지 않았다 |
| 참고자료 | 12개 문서 + 이론 카드 + 내부 1건 | +McKinsey 2건 | "How to close the agentic adoption gap", "The Economic Potential of Generative AI" — 본문 참고자료에 반영 |

## 9. 내부 자료 대조 (수기)

코어 공통 도입의 이천포럼 문단은 v2.2와 글자까지 같다. 원문 대조 결과(2건 ✅ 일치)와 발언 맥락
확인 기록은 `content/drafts/ai-productivity-paradox-v2-verification.md` 8장을 그대로 적용한다.
레이어 3개는 내부 자료를 인용하지 않았다.

## 10. 테스트 기록 · 확인 사항

- **코어 불변 확인**: 코어 1,652자(공백 제외) = v2.2 본문 1,824자 − 들어낸 3문단 172자. 코어 문장은 스크립트
  복사로 옮겼고(④-L2), 이후 편집은 레이어 블록과 참고자료 목록에만 했다.
- **분량**: 레이어(첫 어절+본문) 임원 356자 · 팀장 341자 · 팀원 323자. 독자 열람(코어+레이어 1개) 최대 2,008자.
- **수기 수치 대조**: 임원 레이어 "기술에 1을 쓸 때 … 3, … 5를" ↔ `1A0611C09CA8CDC985C4E4BFBE1`
  metric "1:3:5 투자 패턴" ✅. "성공한 사례만 본 결과라 그대로 일반화할 수는 없지만"으로 evidence cautions 3번
  (성공 기업 표본 한정)을 본문에 밝혔다.
- **의도적 미사용**: `0607DAD6`(Kerr, 측정·보상) — 임원은 앵글 A claim만 쓰기로 확정(④-L1).
  `0640EA93`(평균 14%·신입 34%) — `0614933C`와 같은 원연구일 가능성이 있어 인용하지 않았다.
- **④-L3 도중 바뀐 규칙** (`prompts/segment_layers.md` 머리 주석): 맞물림 "↳ 한 줄"과 본문 연결 문장 폐지,
  비유·조어 금지 항목 추가, 추가 검사 L2를 "완결성"으로 재정의. 결과 보고(`eval/layer-test-2026-09.md`)에 기록한다.
- **검증기 한계 2건 (이번에 수기로 메움)**: ① 단위 없는 수치(1:3:5)는 수치 대조 대상에서 빠진다
  ② 참고자료 목록은 출처 이름만 맞으면 문서가 빠져도 경고하지 않는다 — 레이어가 새로 인용한 McKinsey 문서 2건이
  목록에 없었는데 경고 0건이었다.
- 금지 표현 목록 미운용 (2026-09 폐지 · `prompts/banned_phrases.txt` 없음).
