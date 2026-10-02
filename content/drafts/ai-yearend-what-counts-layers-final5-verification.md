# 검증 리포트 (실사용 기준) — ai-yearend-what-counts

대상: `content/drafts/ai-yearend-what-counts-layers-final5.md` · 증거: `content/evidence/ai-yearend-what-counts.json`
작성 모델: claude-opus-5 (정본은 `config/settings.yaml`의 `write_model`)
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[올해 본인 평가에는 무엇을 정했는지도 담아 보면 좋겠습니다] 15행** — “- 올해는 AI와 함께 많은 과제를 하고 결과물도 그만큼 많이 낸 해였습니다.”
- `1A06A3BAA95A7915D3FFDBC5524` · academic-canon · T1 · optimistic/experiment — AI 지원이 가능한 업무(frontier 내)에서 GPT-4 사용 시 응답 품질이 통제 집단 대비 33.9% 향상된다.
- `1A0E5D3DB79951D5B0FD89699FE` · arxiv-cs-hc · T1 · cautious/opinion — AI 사용 여부, 공개 여부, 숨겨진 사용 탐지 가능성에 대한 질문은 AI 사용 자체를 책임성의 중심에 놓으면서 더 근본적인 
- `1A06A16BA8A6407FD4AB5BD513C` · dbr · T3 · cautious/theory — AI를 활용하여 만든 결과물의 완성도가 높아도, 그것이 개인의 실제 직무 역량 발전을 의미하지는 않는다

**[결과만 보면 AI가 했는지 사람이 했는지 알기 어렵습니다] 24행** — “사람과 AI가 함께 일할 때의 책임을 다룬 2026년 연구에서 Hengzhi Ye 외 연구진은 우리 질문이 조금 어긋나 있다고 짚습니다.”
- `1A0E5D3DB79951D5B0FD89699FE` · arxiv-cs-hc · T1 · cautious/opinion — AI 사용 여부, 공개 여부, 숨겨진 사용 탐지 가능성에 대한 질문은 AI 사용 자체를 책임성의 중심에 놓으면서 더 근본적인 

**[결과만 보면 AI가 했는지 사람이 했는지 알기 어렵습니다] 27행** — “AI 덕분에 성과가 오른 것은 분명합니다.”
- `1A06A3BAA95A7915D3FFDBC5524` · academic-canon · T1 · optimistic/experiment — AI 지원이 가능한 업무(frontier 내)에서 GPT-4 사용 시 응답 품질이 통제 집단 대비 33.9% 향상된다.

**[결과만 보면 AI가 했는지 사람이 했는지 알기 어렵습니다] 30행** — “다만 자기 기여를 스스로 가늠하기는 쉽지 않습니다.”
- `1A09270426C2548B53EC2326710` · worklytics-blog · T4 · cautious/experiment — 개발자의 자체 평가로 측정한 AI 도구의 생산성 향상 효과는 통제된 조건에서 측정한 실제 효과보다 3~5배 크다

**[무엇을 정했는지까지 정리하면 성과가 더 분명해집니다] 35행** — “비교 기준은 다른 사람이 확인할 근거를 함께 적으면 생깁니다.”
- `1A06A16BA8A6407FD4AB5BD513C` · dbr · T3 · cautious/theory — AI를 활용하여 만든 결과물의 완성도가 높아도, 그것이 개인의 실제 직무 역량 발전을 의미하지는 않는다

**[AI를 썼다는 사실만으로는 차이가 보이지 않습니다] 44행** — “달리 말해, 차이는 그다음에서 생깁니다.”
- `1A061410B73C0097A2017D587E2` · deloitte-insights · T2 · cautious/survey — 의사결정 시 AI 산출물의 품질을 정기적으로 검증하는 경영진은 절반에 불과하다

**[AI를 썼다는 사실만으로는 차이가 보이지 않습니다] 47행** — “Worklytics의 2026년 도입 사례 분석에 소개된 어느 개발 조직은 코딩 도구를 도입한 뒤 월간 되돌림이 4건에서 17건으로 늘었습니다.”
- `1A0927045D10A41AA91C2378D78` · worklytics-blog · T4 · cautious/case — 코딩 어시스턴트 도입 후 코드 검토 과정에서 발생하는 월간 풀 리퀘스트 되돌림이 4건에서 17건으로 증가했다

**[AI를 썼다는 사실만으로는 차이가 보이지 않습니다] 50행** — “Hackman과 Oldham이 1976년에 제시한 직무특성모형은 과업 정체성, 곧 일의 처음부터 끝까지가 내 것이라는 느낌이 책임감과 몰입을 높인다고 봅니다.”
- `1A0607DA27A9E22BE156637FD46` · theory-canon · T1 · neutral/theory — 기술다양성·과업정체성·과업중요성·자율성·피드백의 5가지 핵심 직무특성이 높은 직무일수록 수행자의 내적 동기와 직무만족이 높다

**[우리 조직에 적용해본다면] 58행** — “**리더가 바꿀 수 있는 것은 평가에서 묻는 질문입니다.** 몇 건을 했는지만 물으면 결과물이 올라오고, 어디서 무엇을 정했는지 물으면 판단이 올라옵니다.”
- `1A09270472F0EE7C2F42681D48C` · worklytics-blog · T4 · neutral/data — 팀 매니저의 AI 사용 행동이 가시적이고 1:1 면담에서 이를 언급하는지 여부가 팀 채택률의 선행지표가 된다

**[우리 조직에 적용해본다면] 62행** — “**팀원에게 올해 본인 평가는 기억보다”
- `1A06B4F3542AA2D591093EED06B` · arxiv-cs-hc · T1 · neutral/data — AI 사용 빈도가 낮은 사용자는 자신의 저작권 기여도를 더 정확하게 인식한다

사용 claim 9건 / evidence 전체 83건 (미사용 74건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 6곳 (worklytics-blog 3, arxiv-cs-hc 2, academic-canon 1, dbr 1, deloitte-insights 1, theory-canon 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | worklytics-blog 33% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 4건 | AI를 썼다는 사실만으로는 차이가 보이지 않습니다 47행 | ✅ 사용 claim에 있음 |
| 17건 | AI를 썼다는 사실만으로는 차이가 보이지 않습니다 47행 | ✅ 사용 claim에 있음 |

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 2026년 1인 1 AI Task 수립·운영 안내 | 올해 본인 평가에는 무엇을 정했는지도 담아 보면 좋겠습니다 20행 | 2026년 | ✅ 있음 |
| 2026년 1인 1 AI Task 수립·운영 안내 | AI를 썼다는 사실만으로는 차이가 보이지 않습니다 42행 | 2026년 | ✅ 있음 |
| 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling | 우리 조직에 적용해본다면 55행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **academic-canon**: Navigating the Jagged Technological Frontier: Field Experimental Evidence of the Effects of AI on Knowledge Worker Productivity and Quality
- **arxiv-cs-hc**: When AI Blurs the Boundaries of Contribution: An Empirical Study of Authorship Calibration / When No One Owns the Judgment: Accountability Under Contribution Dissolution in Human-AI Collaboration
- **dbr**: AI로 달성한 고성과를 실력으로 착각 설명·응용할 수 있는지 역량 검증해야 | DBR
- **deloitte-insights**: AI adoption to adaptation: How a new change approach can build the human behaviors needed for AI
- **theory-canon**: 직무특성모형 (Job Characteristics Model)
- **worklytics-blog**: How to Measure Time Saved From Codex (With Real Data) | Worklytics

## 7. 지적 사항

없음.

---

## 11. 추가 손질 (2026-10-02, 같은 판본에 반영)

### 11.1 자문 제거

| 원문 | 수정 |
|---|---|
| 그렇다면 무엇이 차이를 만들까요. | **달리 말해, 차이는 그다음에서 생깁니다.** |

8.4에서 사람 판단으로 남겼던 항목이 지시로 확정됐다. 물음표 문장이 **3개 → 2개**(리더 레이어의
제안형 질문, 마무리의 독자 질문)로 줄었고 자문은 0회가 됐다.

**분량 메모**: 지시의 예상은 −2자였으나 실측은 **+3자**였다("그렇다면 무엇이 차이를 만들까요."
15자 → "달리 말해, 차이는 그다음에서 생깁니다." 18자). 코어가 1,803자로 기준을 넘어
군더더기 3곳을 덜어 1,800자로 맞췄다 — "그 문장만 보고는" → "그 문장만으로는",
"여럿이면 그 차이는" → "여럿이면 차이는", "차이가 벌어집니다" → "차이가 납니다".

### 11.2 `prompts/article_style.md` 6절 ⑶ 규칙 추가

8.4에서 보고한 충돌(반복 지시어 회피 ↔ 레이어 완결성)의 판단 기준을 정본에 남겼다.
반복 회피 규칙 바로 아래 하위 항목으로 넣었다.

> **지시 참조와 반복 회피가 충돌하면 명확성(출처 재명시)을 우선한다.** 레이어처럼
> 코어 없이도 읽혀야 하는 단락, 또는 앞 출처가 멀어 "같은 분석"이 무엇인지 되짚어야
> 하는 자리에서는 출처명을 다시 적는다 (2026-10-02 창간호 final5 판단).

이 규칙에 따라 final5의 Worklytics 3회 명시는 더 이상 상충 사항이 아니다.
`pytest tests` 226건 전부 통과를 확인했다(정본 수정이 코드·테스트에 영향 없음).

### 11.3 갱신된 분량·조건

| 항목 | 기준 | 실측 |
|---|---|---|
| 코어 | 1,500~1,800자 | **1,800자** |
| 레이어 | 각 300~400자 | 리더 311자 · 팀원 324자 |
| 독자 열람 | 2,200자 이내 | **2,124자** |
| 물음표 문장 | — | 2개 (자문 0회) |
| 검증 | 실패 0 | **실패 0 · 경고 0** |

8.4의 "물음표 세 개" 항목은 해소됐다. "Worklytics 세 번 명시"는 11.2의 규칙 추가로
상충이 아니라 규칙에 맞는 처리가 됐다.
