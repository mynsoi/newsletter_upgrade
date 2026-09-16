# 검증 리포트 (실사용 기준) — ai-skill-formation

대상: `content/drafts/ai-skill-formation-layers.md` · 증거: `content/evidence/ai-skill-formation.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[같은 도구를 써도 실력은 갈립니다] 11행** — “- AI가 판단력을 깎는지 키우는지는 도구가 아니라 쓰는 방식이 정합니다.”
- `1A06B272D3FF0D59E39488094BA` · arxiv-cs-cy · T1 · conditional/opinion — AI가 비판적 사고에 미치는 영향은 균일하게 부정적이거나 긍정적이지 않으며, 그것이 사용되는 방식에 따라 달라진다
- `1A0A71F94412287A1C43E27272C` · arxiv-cs-hc · T1 · conditional/theory — AI는 구조화된 일상적 업무에서는 성과 격차를 균등화하지만, 깊이 있는 판단이 필요한 복잡한 업무에서는 기존의 격차를 증폭시킨
- `1A06B272A9EB2798036C2463C95` · arxiv-cs-cy · T1 · cautious/theory — AI에 반복적으로 의존하면 인지적 오프로딩을 조장하고 지속적 노력의 기회를 감소시키며 독립적 비판적 사고를 약화시킬 수 있다

**[같은 도구를 써도 쓰는 습관은 갈립니다] 20행** — “일하는 시간이 줄어든 자리에는 판단이 남습니다.”
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

**[경험이 쌓여도 실력으로 굳지 않을 수 있습니다] 39행** — “사람이 어떻게 배우는지를 오래 연구해 온 분야에서는 학습을 하나의 순환으로 봅니다.”
- `1A0607DAFA4381CBD476204D2BB` · theory-canon · T1 · neutral/theory — 학습은 구체적 경험, 반성적 관찰, 추상적 개념화, 능동적 실험이라는 네 가지 양식이 순환적으로 맞물리는 과정으로 모형화된다(

**[경험이 쌓여도 실력으로 굳지 않을 수 있습니다] 42행** — “조직에도 비슷한 구분이 있습니다.”
- `1A0607DD6D629B8E9AFE611C51C` · theory-canon · T1 · neutral/theory — 단일고리 학습은 오류를 기존의 지배 변수(목표·전제·규범) 안에서 수정하고, 이중고리 학습은 지배 변수 자체를 검토·수정한다
- `1A0607DD70E4413E39868E7F201` · theory-canon · T1 · neutral/theory — 조직에는 당혹·위협을 회피하려는 방어적 루틴이 형성되며, 이것이 이중고리 학습을 체계적으로 억제한다

**[경험이 쌓여도 실력으로 굳지 않을 수 있습니다] 45행** — “여기서 두 가지를 덧붙여야 이야기가 기울지 않습니다.”
- `1A0607DD7B9DC60CECDCB52430C` · theory-canon · T1 · conditional/theory — 이중고리 학습이 항상 우월한 것은 아니다 — 안정적 환경의 반복 과업에서는 단일고리 수정이 더 효율적일 수 있다
- `1A06B0F292B81C85CBD89E0E0ED` · arxiv-cs-cy · T1 · cautious/opinion — 현재의 측정 방법론으로는 인구 규모에서 AI가 역량 형성을 훼손하는지 여부를 결정할 수 없다
- `1A06BACFE1EF4B4C276B532480D` · arxiv-cs-hc · T1 · optimistic/opinion — AI 도구가 인간의 명확화와 정당화를 요구하는 질문 형태의 도발을 통해 비판적 사고를 유도할 수 있다

**[우리 조직에 적용해본다면] 53행** — “**임원에게 이것은 평가와 보상의 문제입니다.** 구성원이 AI를 어떻게 쓰는지는 각자의 습관처럼 보이지만, 그 습관을 만드는 것은 조직이 무엇을 성과로 인정하느…”
- `1A06A1D4580D672D9118667AACB` · ms-worklab · T4 · cautious/opinion — AI는 판단력을 자동으로 높이거나 호기심을 증진시키지 않으며, 오히려 기존 시스템에 내재된 인센티브를 증폭시킨다.
- `1A06B0F281FC1FCB708EEC800B3` · arxiv-cs-cy · T1 · cautious/theory — 현재의 측정 시스템은 기존 전문성의 활용을 미래 전문성의 형성보다 더 용이하게 관찰한다
- `1A06B0F271243090816D3F074CD` · arxiv-cs-cy · T1 · cautious/theory — 대규모 배포 데이터는 사용자가 AI 지원 없이 작업을 독립적으로 수행할 수 있는 능력 발달 여부를 관찰하지 못한다
- `1A06A1F87868470D12C32A98E02` · ms-worklab · T4 · conditional/opinion — AI 시대에 직무 성공을 위해서는 전통적인 기술 학습 방식이 아닌 인간의 본질적 역량이 더 중요하다

**[우리 조직에 적용해본다면] 57행** — “**팀장이 할 일은 팀원들이 AI를 어떻게 쓰는지 아는 데서 시작합니다.** 학부생의 프로그래밍 협업을 살핀 연구는 서로가 상대의 AI 사용을 얼마나 정확히 알고…”
- `1A06ACFA02FB1C65BD1E9F02C11` · arxiv-cs-cy · T1 · cautious/data — AI 사용 인식 불일치의 부정적 영향은 프로그래밍 기초 능력이 낮은 팀에서 더 크다
- `1A073811BE76F31029273D4ED0F` · arxiv-cs-cy · T1 · neutral/case — AI 자문 시점의 타이밍이 학습 성과에 상당한 영향을 미친다
- `1A06BA1597157EA3657ADE992AE` · arxiv-cs-hc · T1 · conditional/theory — 인지적 수동성을 해소하려면 단순히 AI가 숙고적 사고를 촉진하도록 하는 것보다 인지적 정렬을 통한 역동적이고 적응적인 전략이 

**[우리 조직에 적용해본다면] 61행** — “**팀원에게 이것은 자기 점검의 문제입니다.** 앞에서 본 세 갈래 가운데 내가 어디에 있는지는 성과표에 나오지 않습니다.”
- `1A06B272BAA36DA9E7F103C6DCE` · arxiv-cs-cy · T1 · cautious/survey — AI 사용자 중 상당수가 지속적 노력에 대한 인내심 감소를 보고했다
- `1A06B272C32F2DD0AD5A8DE7934` · arxiv-cs-cy · T1 · cautious/experiment — 개인의 배경 특성만으로는 설명할 수 없는 정도로 인내심 감소와 의존성 경향이 낮은 추론 성능과 더 강하게 연관되어 있다
- `1A0A71F9343FF30D7FF7DDA0883` · arxiv-cs-hc · T1 · cautious/case — AI의 출력 품질은 이를 활용하는 인간의 전문성에 근본적으로 의존한다

사용 claim 26건 / evidence 전체 36건 (미사용 10건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 6곳 (arxiv-cs-cy 10, arxiv-cs-hc 8, theory-canon 4, ms-worklab 2, fastcompany-worklife 1, hr-bulletin 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | arxiv-cs-cy 38% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

검사 대상 수치 없음 (참고자료 섹션은 면제).

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 회장과의 대화 (1) AI 네이티브 기업으로의 전환 — 최태원 회장, 2026 이천포럼 | 우리 조직에 적용해본다면 50행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **arxiv-cs-cy**: Critical Thinking in the Age of Artificial Intelligence: A Survey-Based Study with Machine Learning Insights / From Individual Prompts to Collective Intelligence: Mainstreaming Generative AI in the Classroom / Students' Perception Accuracy of Partners' AI Use and its Relation to Collaboration Performance / Toward Measuring AI's Effects on Skill Formation: The Stock-Formation Gap
- **arxiv-cs-hc**: AI as Equalizer or Amplifier? Task Complexity as the Moderating Factor for Human Expertise in Hybrid Intelligence Systems / Disrupting Cognitive Passivity: Rethinking AI-Assisted Data Literacy through Cognitive Alignment / Promoting Critical Thinking With Domain-Specific Generative AI Provocations / Understanding Critical Thinking in Generative Artificial Intelligence Use: Development, Validation, and Correlates of the Critical Thinking in AI Use Scale
- **fastcompany-worklife**: In the age of AI, how much work you do matters less than it used to. Here’s what matters more
- **hr-bulletin**: AI를 통한 지능 확장? AI와의 협업을 최적화하기 위한 4가지 원칙
- **ms-worklab**: AI@Work: Stop blaming AI and start deciding / The essential human skills for AI success? Focus on the 5Cs
- **theory-canon**: 경험학습 사이클 (Experiential Learning Cycle) / 조직학습 — 단일고리/이중고리 학습 (Single-loop / Double-loop Learning)

## 7. 지적 사항

없음.

---

<!-- 아래 8~10장은 draft-layers ⑤의 수기 항목이다. `verify_article.py` 재실행 시 덮어써지므로
     재실행 후에는 이 블록을 다시 붙인다. 판본: v2-layers (2026-09-16, 편집 피드백 21건 반영).
     루브릭 자체 채점은 사람 채점의 독립성을 위해 이 리포트에 싣지 않는다 —
     eval/scores/ai-skill-formation-layers-claude.md (사람 채점 완료 후 열람). -->

## 8. 1차 테스트(D1)와의 비교

| 항목 | 1차 D1 v3-layers | **2차 v2-layers** |
|---|---|---|
| 방식 | 발행본에 레이어를 덧댐 (같은 증거·같은 논지) | **새 주제·새 증거로 처음부터** |
| 코어 | 1,652자 | 1,771자 |
| 레이어 | 임원 356 · 팀장 341 · 팀원 323 | 임원 361 · 팀장 314 · 팀원 300 |
| 독자 열람(코어+레이어 1개) | 최대 2,008자 | 최대 2,132자 (기준 2,200 이내) |
| 사용 claim | 21건 / 출처 7곳 | 26건 / 출처 6곳 |
| 최대 의존 출처 | mckinsey-insights 29% | arxiv-cs-cy 38% |
| 살아남은 레이어 | 3개 (생략 0) | 3개 (생략 0) |
| 채점 전 편집 | 사용자 피드백 2회 반영 | **사용자 피드백 21건 반영** (조건 동일) |
| 검증 | 통과 (실패 0 · 경고 0) | 통과 (실패 0 · 경고 0) |

생략 규칙은 2차에서도 검증되지 않았다. ④-L1에서 임원 층위 claim이 5건으로 확인돼 증거를 따랐다
(`content/angles/ai-skill-formation-layers.md` 2장).

## 9. 내부 자료 대조 (수기)

대상 문서: `internal_docs` `leadership-messages/2026-06-회장과의대화-2-일자리와역량.md`
(제목: 회장과의 대화 (2) AI 시대의 일자리와 역량 — 최태원 회장, 2026 이천포럼 · `api_eligible=1` · `effective_date=2026-06-01`)

| # | 본문 서술 | 원문 근거 | 판정 |
|---|---|---|---|
| 1 | 지금 키워야 할 역량은 대단한 역량이 아니라 내가 하는 일과 우리 팀이 하는 일을 정의하고 정리하는 데서 시작한다 | 답변 — "역량도 아닙니다… 내가 지금 하고 있는 일은 무엇이고 내 팀이 하는 일은 무엇이다라는 거를 정리해 나가는 일" | ✅ 일치 |
| 2 | 그 위에서 시간을 줄이려면 무엇이 필요한지 AI에게 계속 되물으며 반복한다 | 답변 — "내가 시간을 좀 더 줄이려면 어떻게 하면 되겠어?… 결국 이 일을 계속 질문하고 반복해서 하는 겁니다" | ✅ 일치 |

- **형식**: 직접 인용부호 없이 "우리" 시점 간접 서술(article_style 1절), 실명·직책 표기, 2026년 명시(5절).
- **⚠️ 검증기 4장의 시점 표기 행은 오지목이다.** 리포트가 「회장과의 대화 (1) AI 네이티브 기업으로의 전환」을
  가리키지만 본문이 인용한 문서는 **(2) AI 시대의 일자리와 역량**이다. 같은 세션의 6개 조각이 제목 낱말
  ("최태원", "이천포럼")을 공유해 `_declared_internal_docs`가 형제 문서를 구분하지 못한다.
  시점 표기 판정(2026년 ✅) 자체는 유효하다.
- **STT 전사본**이라 원문 표현이 거칠다. 발언 맥락 왜곡 여부는 발행 전 사람 확인 항목이다.
- **의도적 미사용**: AGI 이후 능력 평준화 비유(1,000단위·9% 등 수치), 멀티잡·근무제 구상, 젠슨 황과의 대화.
  claims 밖 수치이거나 확정되지 않은 방향 제시라 본문에 옮기지 않았다(문서 머리말의 취급 지침).

## 10. 테스트 기록 · 확인 사항

- **채점 전 편집(2026-09-16)**: 편집자 피드백 21건을 반영해 v1-layers → v2-layers로 다시 썼다.
  1차 테스트도 채점 전에 피드백을 반영했으므로 두 판본의 비교 조건은 같다. 수정 범위는 문체·전개·설명이며
  구조(코어/레이어 경계, 문단별 claim 인용, 역할별 고유 근거)는 그대로 두었다.
- **사실 정확성 수정 1건**: 「AI as Equalizer or Amplifier?」를 "과업의 복잡도를 나눠 본 실험"으로 적었으나,
  원문은 사내 소프트웨어 제품팀의 사용을 **구조화해 관찰한 분석**이다. "관찰한 분석"으로 고쳤다.
  나머지 인용 연구도 원문에서 조사 성격을 확인해 본문에 밝혔다(설문+추론 과제, 척도 개발·검증,
  학부생 협업 관찰, 공학 수업 사례). 표본 수는 claims 밖 수치라 쓰지 않았다.
- **규칙 개정 ⑤**: 레이어 첫 어절의 고정 문구("○○의 자리에서 보면") 폐지. 세 레이어가 같은 틀로 시작해
  첫 문장이 어색하다는 지적을 반영해, 역할을 첫 문장 안에 담아 굵게 쓰도록 바꿨다(`prompts/segment_layers.md`).
- **출처 편중 관리**: evidence 전체는 arXiv 24/36건으로 쏠려 있다. 본문 인용을 배분해 arxiv-cs-cy 38%로 맞췄다.
- **④-L3에서 evidence claim 1건 추가**: `1A06A1F87868470D12C32A98E02`(ms-worklab). 임원 레이어가 인용했는데
  ② 단계 목록에서 빠져 있었고, 검증기가 "미등록 claim"으로 실패시켜 잡아냈다.
- **1차에서 기록한 검증기 한계 2건**(단위 없는 수치·참고자료 누락)은 이번에 재발하지 않았다.
  새로 확인된 한계는 9장의 형제 내부 문서 구분 문제다.
- 금지 표현 목록 미운용 (2026-09 폐지 · `prompts/banned_phrases.txt` 없음).
