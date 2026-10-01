# 검증 리포트 (실사용 기준) — ai-yearend-what-counts

대상: `content/drafts/ai-yearend-what-counts-layers-opus55.md` · 증거: `content/evidence/ai-yearend-what-counts.json`
작성 모델: claude-opus-5-5 (정본은 `config/settings.yaml`의 `write_model`)
생성일: 2026-10-01 · 검증 실행: claude-opus-5-5 세션, 메인 체크아웃 `.venv` 파이썬
판정: **통과** (실패 0건 · 경고 0건)

> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.

## 1. 본문 사용 claim (문장 ↔ claim ID)

**[올해 평가서에는 내가 판단한 자리를 적습니다] 11행** — “- 올해 내 성과를 세는 단위는 AI와 함께 만든 결과물이 아니라 그 안에서 내가 판단한 자리입니다.”
- `1A0E5D3DB79951D5B0FD89699FE` · arxiv-cs-hc · T1 · cautious/opinion — AI 사용 여부, 공개 여부, 숨겨진 사용 탐지 가능성에 대한 질문은 AI 사용 자체를 책임성의 중심에 놓으면서 더 근본적인 
- `1A06A3C383E3775C6A022164A5C` · academic-canon · T1 · cautious/experiment — AI를 사용하여 논리 추론 과제를 수행할 때 사용자의 실제 성과는 향상되지만, 자신의 성과를 과대평가하는 경향이 동시에 나타난
- `1A06AF2CE10E587619E628E48EB` · arxiv-cs-cy · T1 · conditional/experiment — AI 매개 평가 환경에서는 최종 답의 정확성만으로는 이해도를 충분히 증명할 수 없으며, 프롬프트 작성·검증·판단 능력이 학습의

**[AI를 썼다는 한 줄로는 내 몫이 보이지 않습니다] 20행** — “먼저 짚을 것은 성과가 진짜라는 점입니다.”
- `1A06A3BAA95A7915D3FFDBC5524` · academic-canon · T1 · optimistic/experiment — AI 지원이 가능한 업무(frontier 내)에서 GPT-4 사용 시 응답 품질이 통제 집단 대비 33.9% 향상된다.
- `1A06A3BB309863D75BBA46449EF` · academic-canon · T1 · cautious/experiment — AI 능력 범위 밖의 업무에서 AI 사용이 정답률을 19 퍼센트포인트 감소시킨다

**[AI를 썼다는 한 줄로는 내 몫이 보이지 않습니다] 23행** — “그런데 평가서 앞에서 우리가 붙드는 질문은 대개 사용 여부에 머뭅니다.”
- `1A0E5D3DB79951D5B0FD89699FE` · arxiv-cs-hc · T1 · cautious/opinion — AI 사용 여부, 공개 여부, 숨겨진 사용 탐지 가능성에 대한 질문은 AI 사용 자체를 책임성의 중심에 놓으면서 더 근본적인 
- `1A0E5D3DBAE5228FA2997398E2D` · arxiv-cs-hc · T1 · cautious/case — AI 보조 피어 리뷰에서 기여도 해산(contribution dissolution)은 책임성을 약화시킨다

**[혼자 매긴 점수는 누구에게나 크게 나옵니다] 28행** — “판단한 자리를 적어야 하는 이유는 자기평가의 조건에 있습니다.”
- `1A06A3C383E3775C6A022164A5C` · academic-canon · T1 · cautious/experiment — AI를 사용하여 논리 추론 과제를 수행할 때 사용자의 실제 성과는 향상되지만, 자신의 성과를 과대평가하는 경향이 동시에 나타난
- `1A09270426C2548B53EC2326710` · worklytics-blog · T4 · cautious/experiment — 개발자의 자체 평가로 측정한 AI 도구의 생산성 향상 효과는 통제된 조건에서 측정한 실제 효과보다 3~5배 크다

**[혼자 매긴 점수는 누구에게나 크게 나옵니다] 31행** — “판단한 자리는 사정이 다릅니다.”
- `1A0607DA27A9E22BE156637FD46` · theory-canon · T1 · neutral/theory — 기술다양성·과업정체성·과업중요성·자율성·피드백의 5가지 핵심 직무특성이 높은 직무일수록 수행자의 내적 동기와 직무만족이 높다
- `1A0607D7C088056C311399A37DF` · theory-canon · T1 · neutral/theory — 사람은 자신의 투입 대비 산출 비율을 비교 대상(referent other)의 비율과 견주어 공정성을 판단한다

**[판단한 자리는 고르고, 고치고, 뒤집은 곳에 남습니다] 36행** — “적을 것은 **선택, 수정, 기각** 세 유형으로 좁혀집니다.”
- `1A06AF2CE10E587619E628E48EB` · arxiv-cs-cy · T1 · conditional/experiment — AI 매개 평가 환경에서는 최종 답의 정확성만으로는 이해도를 충분히 증명할 수 없으며, 프롬프트 작성·검증·판단 능력이 학습의
- `1A06A16BEBF1A02A2043025D9DC` · dbr · T3 · conditional/opinion — AI가 제시한 결과물에 대해 설명 가능성, 반복 가능성, 전이 가능성의 세 가지 요소를 검증해야만 개인의 실제 역량을 정확히 
- `1A06A16BA8A6407FD4AB5BD513C` · dbr · T3 · cautious/theory — AI를 활용하여 만든 결과물의 완성도가 높아도, 그것이 개인의 실제 직무 역량 발전을 의미하지는 않는다

**[판단한 자리는 고르고, 고치고, 뒤집은 곳에 남습니다] 39행** — “AI를 썼다고 밝히는 일이 부담스러운 것도 사실입니다.”
- `1A06B35FC54F51ABD47D95D21A5` · arxiv-cs-hc · T1 · cautious/opinion — AI 공시는 AI 사용자들을 의심, 낙인(예: 역량 평가 감소), 감시에 노출시킬 수 있으며, 이는 소수 집단에 특히 영향을 
- `1A06B980E1EEB0C8DA267504E03` · arxiv-cs-hc · T1 · optimistic/experiment — AI 자기효능감, 공정성 인식, 사회적 지지 인식이 심리적 안전감을 높이면 AI 사용 은폐 의도가 감소한다

**[판단한 자리는 고르고, 고치고, 뒤집은 곳에 남습니다] 42행** — “다만 판단을 적는다고 평가가 늘 나아지지는 않습니다.”
- `1A0C81B3FB230E015BBD2F64618` · theory-canon · T1 · neutral/theory — 피드백 개입은 평균적으로 성과를 높였지만(평균 d=.41), 전체 분석의 효과크기 중 38% 이상은 음수였다 — 이는 연구에서

**[우리 조직에 적용해본다면] 50행** — “**팀원에게 이것은 기억이 아니라 기록에서 꺼내야 하는 일입니다.** AI를 자주 쓸수록 결과물에서 자기 몫을 가려보기가 어려워집니다.”
- `1A06B4F3542AA2D591093EED06B` · arxiv-cs-hc · T1 · neutral/data — AI 사용 빈도가 낮은 사용자는 자신의 저작권 기여도를 더 정확하게 인식한다
- `1A06A16BCA4C66618833D0CF93C` · dbr · T3 · cautious/opinion — 저연차 직원들은 고연차 직원들과 달리 충분한 업무 경험과 판단 기준이 없는 상태에서 AI를 사용하므로, AI의 결과를 비판적으
- `1A0C7D9461A171A0247B4BFD34B` · hbr-korea · T3 · optimistic/data — 피드백을 적극적으로 구하는 행동은 업무 성과와 매우 강하게 연관되어 있다

**[우리 조직에 적용해본다면] 54행** — “**리더에게 이것은 평가에서 무엇을 묻느냐의 문제입니다.** 몇 건을 했느냐고 물으면 결과물이 올라오고, 어디서 무엇을 정했느냐고 물으면 판단이 올라옵니다.”
- `1A06140251660A5C30DE79BA330` · hr-bulletin · T3 · cautious/survey — 관리자는 주간 피드백 제공, 성과 칭찬, 협력적 팀 구축을 자신 있게 수행한다고 평가하지만, 실제로 이에 동의하는 직원은 많지
- `1A061410B73C0097A2017D587E2` · deloitte-insights · T2 · cautious/survey — 의사결정 시 AI 산출물의 품질을 정기적으로 검증하는 경영진은 절반에 불과하다
- `1A09270472F0EE7C2F42681D48C` · worklytics-blog · T4 · neutral/data — 팀 매니저의 AI 사용 행동이 가시적이고 1:1 면담에서 이를 언급하는지 여부가 팀 채택률의 선행지표가 된다
- `1A0927045D10A41AA91C2378D78` · worklytics-blog · T4 · cautious/case — 코딩 어시스턴트 도입 후 코드 검토 과정에서 발생하는 월간 풀 리퀘스트 되돌림이 4건에서 17건으로 증가했다

사용 claim 21건 / evidence 전체 83건 (미사용 62건)

## 2. 강제 조건 재계산 (사용 claim 기준)

| 조건 | 기준 | 실측 | 판정 |
|---|---|---|---|
| 독립 출처 | 3곳 이상 | 9곳 (arxiv-cs-hc 5, academic-canon 3, worklytics-blog 3, theory-canon 3, dbr 3, arxiv-cs-cy 1, hbr-korea 1, hr-bulletin 1, deloitte-insights 1) | ✅ |
| 상반 stance | optimistic·cautious 각 1건+ | cautious, conditional, neutral, optimistic | ✅ |
| 단일 출처 비중 | 40% 이하 | arxiv-cs-hc 24% | ✅ |

## 3. 수치 대조 (절대 규칙 3)

| 본문 수치 | 위치 | 근거 |
|---|---|---|
| 33.9% | AI를 썼다는 한 줄로는 내 몫이 보이지 않습니다 20행 | ✅ 사용 claim에 있음 |
| 3~5배 | 혼자 매긴 점수는 누구에게나 크게 나옵니다 28행 | ✅ 사용 claim에 있음 |
| 4건 | 우리 조직에 적용해본다면 54행 | — 해당 없음 · 처방 값(실행 제안) |
| 17건 | 우리 조직에 적용해본다면 54행 | — 해당 없음 · 처방 값(실행 제안) |

처방 값 2건은 근거 대조 대상이 아니다 — 액션에서 제안한 기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다.

## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)

본문에 직접 인용 없음.

**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)

| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |
|---|---|---|---|
| 2026년 1인 1 AI Task 수립·운영 안내 | 올해 평가서에는 내가 판단한 자리를 적습니다 16행 | 2026년 | ✅ 있음 |
| 2026 이천포럼 CEO 패널토의 — Free Human Resource·Re-skilling | 우리 조직에 적용해본다면 47행 | 2026년 | ✅ 있음 |

## 5. 근거 주석 누락 의심 (사람 검토)

없음.

## 6. 참고자료 (실사용 문서만)

- **academic-canon**: AI Makes You Smarter, But None The Wiser: The Disconnect Between Performance and Metacognition / Navigating the Jagged Technological Frontier: Field Experimental Evidence of the Effects of AI on Knowledge Worker Productivity and Quality
- **arxiv-cs-cy**: Reimagining Assessment in the Age of Generative AI: Lessons from Open-Book Exams with ChatGPT
- **arxiv-cs-hc**: Enabling and Inhibitory Pathways of Students' AI Use Concealment Intention in Higher Education: Evidence from SEM and fsQCA / When AI Blurs the Boundaries of Contribution: An Empirical Study of Authorship Calibration / When No One Owns the Judgment: Accountability Under Contribution Dissolution in Human-AI Collaboration / Who Bears the Cost of Honesty? A FAccT Workshop Synthesis and Research Agenda for Equitable AI Disclosure
- **dbr**: AI로 달성한 고성과를 실력으로 착각 설명·응용할 수 있는지 역량 검증해야 | DBR
- **deloitte-insights**: AI adoption to adaptation: How a new change approach can build the human behaviors needed for AI
- **hbr-korea**: [HBR]피드백을 먼저 요청하는 조직 문화 만들기
- **hr-bulletin**: 리더십 개발의 시작, 강점, 약점 그리고 맹점
- **theory-canon**: 직무특성모형 (Job Characteristics Model) / 피드백 개입 이론 (Feedback Intervention Theory, FIT) / 형평이론 (Equity Theory)
- **worklytics-blog**: How to Measure Time Saved From Codex (With Real Data) | Worklytics

## 7. 지적 사항

없음.

## 8. 작성자 자체 점검 (사람 확인용 — 검증기 판정과 별개)

**검증기 판정 보충**
- 3절의 "4건·17건"이 처방 값으로 분류된 것은 리더 레이어가 적용 섹션(면제 섹션) 안에 있기 때문이다.
  실제로는 근거 수치이며 `1A0927045D10A41AA91C2378D78`의 metric("monthly PR reverts: 4 to 17")과 일치함을 수동 확인했다.
- 1차 실행 경고 1건(팀원 레이어의 "Task" 낱말이 내부 자료 인용으로 잡힘)은 표현을 "한 일"로 바꿔 해소했다.

**분량(공백 제외)**: 코어 1,800 / 팀원 321 / 리더 340 · 코어+레이어 1개 최대 2,140 (코어+레이어 2개 2,461)

**레이어 점검 (segment_layers.md)**
- 완결성(L2): 두 레이어 모두 다른 레이어를 가리키는 연결 문장 없음
- 기간·횟수·주차 처방 없음 ("대표 사례 한 건"은 범위 지정 — 사용자 지시)
- 비유·조어 대체 없음 ("판단의 소유권" 미사용)
- 레이어 전용 근거: 팀원 `06B4F354`·`06A16BCA`·`0C7D9461` / 리더 `06140251`·`061410B7`·`09270472`·`0927045D`

**작성 조건 점검**
- "A가 아니라 B" 대조 3회 (세 줄 요약 · 공개 비용 전환 · 팀원 레이어 첫 문장) / 엠대시 본문 0회 / 자문 1회(마무리)
- 수치 4개(33.9% · 3~5배 · 절반 · 4건→17건), 통계량 미사용, 출처 병기
- 학습자 표본 표시: 오픈북 시험("대학"), 은폐 의도 연구("대학생을 대상으로 한")
- 면책: 코어 본문 마지막 문장 한 곳 (글의 끝은 지정된 마무리 질문이므로 레이어 앞에 둠)

**사람 확인 필요**
- 2026 이천포럼 패널토의(SK이노베이션 E&S 대표이사) 취지를 "우리" 시점 간접 서술로 옮긴 문장의 맥락 왜곡 여부
- 마무리 질문을 지정 문구 그대로(~는가) 두어 존댓말 본문과 어미가 다름 — 인용된 자문으로 읽히는지

**자체 채점 (루브릭 24점)**: 1 논지 2 · 2 출처 3 · 3 상반 관점 2 · 4 종합 3 · 5 SK 맥락 2 · 6 실행 2 · 7 사실 3 · 8 문체 2 = **19점**
