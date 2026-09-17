# 검증 리포트 (실사용 기준) — ai-skill-formation

대상: `content/drafts/ai-skill-formation-layers-2seg.md` · 증거: `content/evidence/ai-skill-formation.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[같은 도구를 써도 실력은 갈립니다] 11행** — “- AI가 판단력을 깎는지 키우는지는 도구가 아니라 쓰는 방식이 정합니다.”
- `1A06B272D3FF0D59E39488094BA` · arxiv-cs-cy · T1 · conditional/opinion — AI가 비판적 사고에 미치는 영향은 균일하게 부정적이거나 긍정적이지 않으며, 그것이 사용되는 방식에 따라 달라진다
- `1A0A71F94412287A1C43E27272C` · arxiv-cs-hc · T1 · conditional/theory — AI는 구조화된 일상적 업무에서는 성과 격차를 균등화하지만, 깊이 있는 판단이 필요한 복잡한 업무에서는 기존의 격차를 증폭시킨
- `1A06B272A9EB2798036C2463C95` · arxiv-cs-cy · T1 · cautious/theory — AI에 반복적으로 의존하면 인지적 오프로딩을 조장하고 지속적 노력의 기회를 감소시키며 독립적 비판적 사고를 약화시킬 수 있다

**[같은 도구를 써도 쓰는 습관은 갈립니다] 20행** — “AI가 손이 많이 가던 일을 대신하면 사람에게는 판단하는 일이 남습니다.”
- `1A06A1577699DB95A338297E094` · fastcompany-worklife · T3 · neutral/opinion — AI 시대에 직장에서 업무량보다 판단력과 재량이 더 중요한 역할을 한다
- `1A06B272CB8A8A4C12D454CADC9` · arxiv-cs-cy · T1 · neutral/data — AI 사용자는 과도 의존형, 혼합전략형, 균형잡힌 지원추구형 등 서로 다른 행동 프로필을 나타낸다

**[같은 도구를 써도 쓰는 습관은 갈립니다] 23행** — “갈림길은 생각을 어디까지 맡기느냐에 있습니다.”
- `1A06B272A9EB2798036C2463C95` · arxiv-cs-cy · T1 · cautious/theory — AI에 반복적으로 의존하면 인지적 오프로딩을 조장하고 지속적 노력의 기회를 감소시키며 독립적 비판적 사고를 약화시킬 수 있다

**[같은 도구를 써도 쓰는 습관은 갈립니다] 26행** — “그렇다고 AI를 쓸수록 판단력이 준다고 말할 수는 없습니다.”
- `1A06B272D3FF0D59E39488094BA` · arxiv-cs-cy · T1 · conditional/opinion — AI가 비판적 사고에 미치는 영향은 균일하게 부정적이거나 긍정적이지 않으며, 그것이 사용되는 방식에 따라 달라진다
- `1A0A2DACD931C736F45D0252DB6` · arxiv-cs-hc · T1 · optimistic/experiment — AI 사용 시 비판적 사고 성향이 높을수록 검증 전략을 더 자주, 다양하게 사용한다
- `1A0A2DACE3E387129C5561C7BB3` · arxiv-cs-hc · T1 · optimistic/experiment — AI 사용 시 비판적 사고 성향이 높을수록 사실 판단 정확도가 더 높다

**[쉬운 일에서는 좁혀지고 어려운 일에서는 벌어집니다] 31행** — “여기까지가 어떻게 쓰느냐의 이야기라면, 무슨 일에 쓰느냐도 결과를 가릅니다.”
- `1A0A71F9244C2E888A3851F57B1` · arxiv-cs-hc · T1 · neutral/theory — 생성형 AI는 일상적 업무에서 초보자와 전문가 간의 성과 격차를 좁힌다
- `1A0A71F94412287A1C43E27272C` · arxiv-cs-hc · T1 · conditional/theory — AI는 구조화된 일상적 업무에서는 성과 격차를 균등화하지만, 깊이 있는 판단이 필요한 복잡한 업무에서는 기존의 격차를 증폭시킨

**[쉬운 일에서는 좁혀지고 어려운 일에서는 벌어집니다] 34행** — “이 분석은 효과를 가른 것이 프롬프트를 잘 쓰는 기술보다”
- `1A0A71F93C25C6AEAAB346538ED` · arxiv-cs-hc · T1 · neutral/case — AI 활용의 효과성은 프롬프트 작성 능력보다 도메인 전문성에 의해 결정된다
- `1A0613EBC51A501110988C13BEE` · hr-bulletin · T3 · conditional/opinion — AI의 산출물을 무조건적으로 받아들이지 말고 인간의 비판적 사고와 전문성을 발휘하여 검토해야 한다

**[경험이 쌓여도 실력으로 굳지 않을 수 있습니다] 39행** — “일이 끝났다고 배움이 남는 것은 아닙니다.”
- `1A0607DAFA4381CBD476204D2BB` · theory-canon · T1 · neutral/theory — 학습은 구체적 경험, 반성적 관찰, 추상적 개념화, 능동적 실험이라는 네 가지 양식이 순환적으로 맞물리는 과정으로 모형화된다(
- `1A06B272A9EB2798036C2463C95` · arxiv-cs-cy · T1 · cautious/theory — AI에 반복적으로 의존하면 인지적 오프로딩을 조장하고 지속적 노력의 기회를 감소시키며 독립적 비판적 사고를 약화시킬 수 있다

**[경험이 쌓여도 실력으로 굳지 않을 수 있습니다] 42행** — “그렇다고 AI를 덜 쓰라는 이야기는 아닙니다.”
- `1A06BACFE1EF4B4C276B532480D` · arxiv-cs-hc · T1 · optimistic/opinion — AI 도구가 인간의 명확화와 정당화를 요구하는 질문 형태의 도발을 통해 비판적 사고를 유도할 수 있다
- `1A06B0F292B81C85CBD89E0E0ED` · arxiv-cs-cy · T1 · cautious/opinion — 현재의 측정 방법론으로는 인구 규모에서 AI가 역량 형성을 훼손하는지 여부를 결정할 수 없다

**[우리 조직에 적용해본다면] 50행** — “**리더에게 이것은 무엇을 성과로 인정하느냐의 문제입니다.** 구성원이 AI를 어떻게 쓰는지는 각자의 습관처럼 보이지만, 그 습관을 만드는 것은 조직과 팀이 무엇…”
- `1A06A1D4580D672D9118667AACB` · ms-worklab · T4 · cautious/opinion — AI는 판단력을 자동으로 높이거나 호기심을 증진시키지 않으며, 오히려 기존 시스템에 내재된 인센티브를 증폭시킨다.
- `1A06B0F281FC1FCB708EEC800B3` · arxiv-cs-cy · T1 · cautious/theory — 현재의 측정 시스템은 기존 전문성의 활용을 미래 전문성의 형성보다 더 용이하게 관찰한다
- `1A073811A6768C27FEDC7B3CDBC` · arxiv-cs-cy · T1 · cautious/opinion — 개별 프롬프팅 중심의 AI 활용은 이미 특권받거나 동기가 높은 학생들을 더욱 유리하게 하여 형평성 격차를 심화시킬 수 있다
- `1A06A1F87868470D12C32A98E02` · ms-worklab · T4 · conditional/opinion — AI 시대에 직무 성공을 위해서는 전통적인 기술 학습 방식이 아닌 인간의 본질적 역량이 더 중요하다

**[우리 조직에 적용해본다면] 54행** — “**팀원에게 이것은 자기 점검의 문제입니다.** 앞에서 본 세 갈래 가운데 내가 어디에 있는지는 성과표에 나오지 않습니다.”
- `1A06B272BAA36DA9E7F103C6DCE` · arxiv-cs-cy · T1 · cautious/survey — AI 사용자 중 상당수가 지속적 노력에 대한 인내심 감소를 보고했다
- `1A06B272C32F2DD0AD5A8DE7934` · arxiv-cs-cy · T1 · cautious/experiment — 개인의 배경 특성만으로는 설명할 수 없는 정도로 인내심 감소와 의존성 경향이 낮은 추론 성능과 더 강하게 연관되어 있다
- `1A0A71F9343FF30D7FF7DDA0883` · arxiv-cs-hc · T1 · cautious/case — AI의 출력 품질은 이를 활용하는 인간의 전문성에 근본적으로 의존한다

사용 claim 20건 / evidence 전체 39건 (미사용 19건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 6곳 (arxiv-cs-cy 8, arxiv-cs-hc 7, ms-worklab 2, fastcompany-worklife 1, hr-bulletin 1, theory-canon 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | arxiv-cs-cy 40% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

검사 대상 수치 없음 (참고자료 섹션은 면제).

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 회장과의 대화 (1) AI 네이티브 기업으로의 전환 — 최태원 회장, 2026 이천포럼 | 우리 조직에 적용해본다면 47행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **arxiv-cs-cy**: Critical Thinking in the Age of Artificial Intelligence: A Survey-Based Study with Machine Learning Insights / From Individual Prompts to Collective Intelligence: Mainstreaming Generative AI in the Classroom / Toward Measuring AI's Effects on Skill Formation: The Stock-Formation Gap
- **arxiv-cs-hc**: AI as Equalizer or Amplifier? Task Complexity as the Moderating Factor for Human Expertise in Hybrid Intelligence Systems / Promoting Critical Thinking With Domain-Specific Generative AI Provocations / Understanding Critical Thinking in Generative Artificial Intelligence Use: Development, Validation, and Correlates of the Critical Thinking in AI Use Scale
- **fastcompany-worklife**: In the age of AI, how much work you do matters less than it used to. Here’s what matters more
- **hr-bulletin**: AI를 통한 지능 확장? AI와의 협업을 최적화하기 위한 4가지 원칙
- **ms-worklab**: AI@Work: Stop blaming AI and start deciding / The essential human skills for AI success? Focus on the 5Cs
- **theory-canon**: 경험학습 사이클 (Experiential Learning Cycle)

## 7. 지적 사항

없음.
