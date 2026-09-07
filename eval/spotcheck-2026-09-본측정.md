# 스팟체크 본측정 - 층화 표본 10건 claim-원문 대조표

추출일: 2026-09-07  
추출 방법: 층화 무작위(arXiv 7 + non-arXiv 3, arXiv 편중 방지)  
시드: 20260907  
총 claim: 55건

## 층화 배분

| 층 | 모집단(enriched) | 비중 | 배분 |
|---|---|---|---|
| arXiv-cs.CY | 1,225 | 38.9% | 3 |
| arXiv-cs.HC | 829 | 26.3% | 2 |
| arXiv-econ.GN | 182 | 5.8% | 1 |
| arXiv-cs.SI | 34 | 1.1% | 1 (최소 보장) |
| non-arXiv T5-뉴스 | 269 | 8.5% | 1 |
| non-arXiv HR-전문 | 311 | 9.9% | 1 |
| non-arXiv 컨설팅-기타 | 297 | 9.4% | 1 |
| **합계** | **3,147** | **100%** | **10** |

> theory-canon(72), academic-canon(5), manual(11)은 자체 생성 문서이므로 모집단에서 제외.
> arXiv claim은 한국어로 번역 추출됨 - 영어 원문과의 의미 대조가 필요.

---

## 표본 1: arxiv-cs-cy

- **제목**: Toward Personal Intelligence Through Cooperative Observation
- **URL**: https://arxiv.org/abs/2608.17128v1
- **본문 길이**: 1,100자
- **추출 claim**: 5건

### C1-1 [neutral/theory]

- **claim**: 개인용 AI 시스템이 사용자를 대신해 계획을 세우고 행동하려면 사용자의 목표, 제약, 진행 중인 약속에 대한 모델을 필요로 한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C1-2 [cautious/theory]

- **claim**: 개인용 AI 시스템의 관찰 범위가 넓어진다고 해서 반드시 사용자 지원 품질이 향상되지는 않는다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C1-3 [neutral/theory]

- **claim**: 개인용 AI의 관찰 병목 현상은 협력적 구조를 가지고 있으며, 시스템의 유용성 평가, 사용자의 신뢰, 그리고 향후 접근 권한 부여 간의 피드백 루프로 작동한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C1-4 [optimistic/opinion]

- **claim**: AI 시스템의 검사 가능하고 유용한 동작이 사용자로 하여금 관찰 채널을 유지하거나 확대하는 동기를 제공할 수 있다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` X-distortion `

### C1-5 [neutral/case]

- **claim**: Organizm 프로토타입의 6개월 사용 기록은 관찰 품질이 개인 AI의 성능에 미치는 영향을 측정하기 위한 평가 방향을 제시한다
- **metric**: 6개월
- **원문 대응**: We report a preliminary single-subject account from Organizm, a prototype used over six months, and outline evaluation directions for measuring how observation quality shapes personal AI.
- **판정**: ` O `

<details>
<summary>본문 전문 (1,100자)</summary>

```
A personal AI system needs a model of the user's goals, constraints, and ongoing commitments to plan and act on their behalf, and the quality of that model is bounded by what the system can observe. Broader observation does not by itself improve assistance because a bounded system must select and compress information for the task at hand. We argue that this observation bottleneck has a cooperative structure: the system builds a partial model of the user's changing life, the user evaluates its actions, and the user's consent and control shape what it can observe next. Useful and inspectable behavior can give users a reason to maintain or expand the observation channel, while failures can lead them to correct, narrow, revoke, or abandon it. We use the term cooperative observation for this feedback loop among usefulness, trust, and future access, and propose it as a framework for personal intelligence. We report a preliminary single-subject account from Organizm, a prototype used over six months, and outline evaluation directions for measuring how observation quality shapes personal AI.
```

</details>

---

## 표본 2: arxiv-cs-cy

- **제목**: First, do NOHARM: a medical safety benchmark and randomized study of physician and AI teaming on clinical consultations
- **URL**: https://arxiv.org/abs/2512.01241v4
- **본문 길이**: 1,899자
- **추출 claim**: 7건

### C2-1 [cautious/data]

- **claim**: 의료용 대규모 언어모델과 임상 AI 도구들이 의료 상담 권장사항을 직접 적용할 경우 심각한 해를 초래할 가능성이 있다
- **metric**: up to 24.6% of cases
- **원문 대응**: Across 20 notable LLMs and 4 widely used retrieval-augmented generation (RAG) clinical AI tools, direct application of recommendations carried potential for severe harm in up to 24.6% of cases, with errors of omission accounting for more than 80% of severe errors.
- **판정**: ` O `

### C2-2 [cautious/data]

- **claim**: 의료 AI 시스템들이 생성한 오류 중 80% 이상이 누락 오류이다
- **metric**: more than 80% of severe errors
- **원문 대응**: Across 20 notable LLMs and 4 widely used retrieval-augmented generation (RAG) clinical AI tools, direct application of recommendations carried potential for severe harm in up to 24.6% of cases, with errors of omission accounting for more than 80% of severe errors.
- **판정**: ` O `

### C2-3 [optimistic/data]

- **claim**: 임상 AI 도구들이 일반형 대규모 언어모델보다 의료 안전 성능이 우수하다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C2-4 [optimistic/data]

- **claim**: 다중 에이전트 AI 팀 구성이 일반형 모델의 의료 상담 성능을 추가로 개선한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C2-5 [optimistic/experiment]

- **claim**: AI 지원을 받은 의사들이 일반적인 자료만 사용한 경우보다 진료 성능이 향상되었다
- **metric**: 101 U.S.-licensed generalist physicians
- **원문 대응**: In a randomized study of 101 U.S.-licensed generalist physicians, AI assistance improved physician performance compared to conventional resources.
- **판정**: ` O `

### C2-6 [cautious/experiment]

- **claim**: AI 지원을 받은 의사들이 AI가 생성한 가치 있는 권장사항을 빈번하게 채택하지 않았다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C2-7 [conditional/opinion]

- **claim**: 의사가 AI의 모든 권장사항을 채택했다면 인간-AI 결합 응답이 단독으로 사용한 인간과 AI 시스템 모두를 능가했을 것이다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

<details>
<summary>본문 전문 (1,899자)</summary>

```
Large language models (LLMs) and medical AI tools are routinely used by physicians and patients for medical advice, yet their clinical safety profiles remain poorly characterized. We present NOHARM (Numerous Options Harm Assessment for Risk in Medicine), a 1,100-task benchmark of primary care-to-specialist consultation cases to measure the frequency and severity of potentially harmful errors from LLM-generated medical consultation recommendations. NOHARM covers 10 specialties, with 12,747 expert annotations for 4,249 clinical management options. Across 20 notable LLMs and 4 widely used retrieval-augmented generation (RAG) clinical AI tools, direct application of recommendations carried potential for severe harm in up to 24.6% of cases, with errors of omission accounting for more than 80% of severe errors. Harm potential was not uniform across systems, with clinical AI tools outperforming generalist LLMs, and multi-agent AI teaming further improving performance in generalist models. In a randomized study of 101 U.S.-licensed generalist physicians, AI assistance improved physician performance compared to conventional resources. However, AI-assisted physicians frequently omitted valuable AI-generated recommendations and still scored lower than many AI systems alone. Had those recommendations been incorporated, combined human-AI responses would have outperformed both the human and AI system as used, suggesting complementary strengths and unrealized potential in human-AI teaming. Collectively, these results show that despite strong performance on medical knowledge benchmarks, widely used AI tools can produce medical consultation advice with the potential for severe harm, and highlight the need for explicit measurement of clinical safety. The benchmark and leaderboard are publicly available to support ongoing evaluation and improvement of AI systems used for clinical care.
```

</details>

---

## 표본 3: arxiv-cs-cy

- **제목**: A Discipline-Agnostic AI Literacy Course for Academic Research: Architecture, Pedagogy, and Implementation
- **URL**: https://arxiv.org/abs/2604.27225v1
- **본문 길이**: 1,735자
- **추출 claim**: 6건

### C3-1 [neutral/opinion]

- **claim**: 기존의 AI 교육 제공은 기술 개발 중심의 전문가 과정과 단기 일반 소양 프로그램의 양극단으로 나뉘어 있어 학문적 연구에 필요한 지속적이고 실무 기반의 역량을 개발하기에 부족하다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` X-distortion `

### C3-2 [neutral/theory]

- **claim**: AI 보조 문헌 검토에 필요한 역량 개발을 위해 개별 논문 이해, 지식 분류체계 구축·검증, 연구 공백 식별, 문헌 검토 합성이라는 4개의 순차적 모듈로 구성된 교과 설계가 인지적 요구를 효과적으로 충족시킨다
- **원문 대응**: This paper reports the design, theoretical rationale, and implementation of BSTA 495/395: Getting Started with AI-Assisted Research, developed and delivered at Lehigh University (Spring 2026).
- **판정**: ` O `

### C3-3 [optimistic/survey]

- **claim**: AI 동반 연구 교육을 받은 학생들의 환각 탐지 능력에 대한 자신감이 크게 증가했다
- **metric**: d = +1.45
- **원문 대응**: Pre- and post-course survey data from the inaugural offering indicate substantial self-reported confidence gains, with the largest in hallucination detection (d = +1.45), responsible AI use (d = +1.33), and AI attribution practice (d = +2.40), consistent with the course's design emphasis.
- **판정**: ` O `

### C3-4 [optimistic/survey]

- **claim**: AI 동반 연구 교육을 받은 학생들의 책임감 있는 AI 사용에 대한 자신감이 크게 증가했다
- **metric**: d = +1.33
- **원문 대응**: Pre- and post-course survey data from the inaugural offering indicate substantial self-reported confidence gains, with the largest in hallucination detection (d = +1.45), responsible AI use (d = +1.33), and AI attribution practice (d = +2.40), consistent with the course's design emphasis.
- **판정**: ` O `

### C3-5 [optimistic/survey]

- **claim**: AI 동반 연구 교육을 받은 학생들의 AI 출처 표기 실무에 대한 자신감이 크게 증가했다
- **metric**: d = +2.40
- **원문 대응**: Pre- and post-course survey data from the inaugural offering indicate substantial self-reported confidence gains, with the largest in hallucination detection (d = +1.45), responsible AI use (d = +1.33), and AI attribution practice (d = +2.40), consistent with the course's design emphasis.
- **판정**: ` O `

### C3-6 [cautious/opinion]

- **claim**: 학문적 연구에 AI를 책임감 있게 활용하기 위해서는 도구 사용 능력뿐 아니라 비판적 판단력이 필요하다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

<details>
<summary>본문 전문 (1,735자)</summary>

```
The rapid integration of generative AI into academic workflows demands curricula that equip students not only with tool proficiency but with the critical judgment to use those tools responsibly in scholarly work. Existing offerings cluster around two inadequate poles: technical AI development courses serving narrow specialist audiences, and brief general-literacy interventions that cannot develop the sustained, practice-based competencies rigorous research requires. This paper reports the design, theoretical rationale, and implementation of BSTA 495/395: Getting Started with AI-Assisted Research, developed and delivered at Lehigh University (Spring 2026). The course addresses an underserved gap: the competencies required for rigorous AI-assisted literature review. Its architecture organizes instruction into four sequential modules aligned with the cognitive demands of that task: comprehension of individual papers, construction and validation of knowledge taxonomies, identification of research gaps, and synthesis and production of complete literature reviews. Each module embeds an explicit verification discipline and standardized AI attribution practice. Prerequisite-free and discipline-agnostic, the course enrolls upper-level undergraduates and graduate students across all fields with differentiated assessment expectations. Pre- and post-course survey data from the inaugural offering indicate substantial self-reported confidence gains, with the largest in hallucination detection (d = +1.45), responsible AI use (d = +1.33), and AI attribution practice (d = +2.40), consistent with the course's design emphasis. The course constitutes a replicable model for the emerging genre of AI research literacy curricula.
```

</details>

---

## 표본 4: arxiv-cs-hc

- **제목**: CentaurTA Studio: A Self-Improving Human-Agent Collaboration System for Thematic Analysis
- **URL**: https://arxiv.org/abs/2604.18589v1
- **본문 길이**: 1,252자
- **추출 claim**: 5건

### C4-1 [optimistic/experiment]

- **claim**: CentaurTA Studio는 개방형 코딩과 테마 구성 작업에서 기준선 시스템을 지속적으로 능가하는 성능을 달성했다
- **metric**: 최대 92.12% 정확도
- **원문 대응**: We present \textbf{CentaurTA Studio}, a web-based system for self-improving human--agent collaboration in open coding and theme construction.
- **판정**: ` O `

### C4-2 [optimistic/experiment]

- **claim**: 루브릭 기반 LLM 판정자와 인간 주석자 간의 합의 수준은 상당한 신뢰도에 도달했다
- **metric**: 평균 κ = 0.68
- **원문 대응**: Agreement between the rubric-based LLM judge and human annotators reaches substantial reliability (average $κ= 0.68$).
- **판정**: ` O `

### C4-3 [cautious/experiment]

- **claim**: 인간-에이전트 협업 시스템에서 피드백 루프를 제거하면 성능이 감소한다
- **metric**: 90%에서 81%로 감소
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C4-4 [optimistic/experiment]

- **claim**: CentaurTA Studio 시스템은 약 10회의 반복 라운드(약 25분)에서 최고 성능에 도달한다
- **metric**: 10 iterative rounds (약 25분)
- **원문 대응**: The full system reaches peak performance within 10 iterative rounds (about 25 minutes), demonstrating improved efficiency over expert-only refinement.
- **판정**: ` O `

### C4-5 [conditional/experiment]

- **claim**: Critic 컴포넌트나 조기 종료 메커니즘을 제거하면 정확도가 저하되거나 상호작용 비용이 증가한다
- **원문 대응**: Ablation studies show that removing the feedback loop reduces performance from 90\% to 81\%, while eliminating the Critic or early stopping degrades accuracy or increases interaction cost.
- **판정**: ` O `

<details>
<summary>본문 전문 (1,252자)</summary>

```
Thematic analysis is difficult to scale: manual workflows are labor-intensive, while fully automated pipelines often lack controllability and transparent evaluation. We present \textbf{CentaurTA Studio}, a web-based system for self-improving human--agent collaboration in open coding and theme construction. The system integrates (1) a two-stage human feedback pipeline separating simulator drafting and expert validation, (2) persistent prompt optimization that distills validated feedback into reusable alignment principles, and (3) rubric-based evaluation with early stopping for process control.
  Across three domains, CentaurTA achieves the strongest performance in both Open Coding and Theme Construction, reaching up to 92.12\% accuracy and consistently outperforming baseline systems. Agreement between the rubric-based LLM judge and human annotators reaches substantial reliability (average $κ= 0.68$). Ablation studies show that removing the feedback loop reduces performance from 90\% to 81\%, while eliminating the Critic or early stopping degrades accuracy or increases interaction cost. The full system reaches peak performance within 10 iterative rounds (about 25 minutes), demonstrating improved efficiency over expert-only refinement.
```

</details>

---

## 표본 5: arxiv-cs-hc

- **제목**: Biased Error Attribution in Multi-Agent Human-AI Systems Under Delayed Feedback
- **URL**: https://arxiv.org/abs/2603.23419v1
- **본문 길이**: 1,440자
- **추출 claim**: 5건

### C5-1 [cautious/experiment]

- **claim**: 지연된 피드백 환경에서 인간은 실패의 원인이 된 구체적인 행동을 올바르게 식별하지 못한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C5-2 [cautious/experiment]

- **claim**: 다중 AI 에이전트 시스템에서 인간은 책임을 AI 에이전트들 간에 잘못 귀속시킨다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C5-3 [cautious/experiment]

- **claim**: 지연된 피드백 조건에서 인간은 긍정적 결과보다 부정적 결과에 더 강한 행동 조정을 보인다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C5-4 [cautious/experiment]

- **claim**: 인간이 실제 성과 저하의 원인과 약하게 관련된 의사결정을 체계적으로 수정한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C5-5 [cautious/theory]

- **claim**: 지연된 결과를 포함한 다중 자율 에이전트 시스템에서는 인지 편향이 증폭될 수 있다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

<details>
<summary>본문 전문 (1,440자)</summary>

```
Human decision-making is strongly influenced by cognitive biases, particularly under conditions of uncertainty and risk. While prior work has examined bias in single-step decisions with immediate outcomes and in human interaction with a single autonomous agent, comparatively little attention has been paid to decision-making under delayed outcomes involving multiple AI agents, where decisions at each step affect subsequent states. In this work, we study how delayed outcomes shape decision-making and responsibility attribution in a multi-agent human-AI task. Using a controlled game-based experiment, we analyze how participants adjust their behavior following positive and negative outcomes. We observe asymmetric responses to gains and losses, with stronger corrective adjustments after negative outcomes. Importantly, participants often fail to correctly identify the actions that caused failure and misattribute responsibility across AI agents, leading to systematic revisions of decisions that are weakly related to the underlying causes of poor performance. We refer to this phenomenon as a form of attribution bias, manifested as biased error attribution under delayed feedback. Our findings highlight how cognitive biases can be amplified in human-AI systems with delayed outcomes and multiple autonomous agents, underscoring the need for decision-support systems that better support causal understanding and learning over time.
```

</details>

---

## 표본 6: arxiv-econ-gn

- **제목**: Skill vs Education Types of Labour Mismatch and Their Association with Earnings
- **URL**: https://arxiv.org/abs/2606.13506v1
- **본문 길이**: 1,051자
- **추출 claim**: 4건

### C6-1 [neutral/data]

- **claim**: 과다 교육(over-education)과 과다 기술(over-skilling)은 임금 감소와 연관이 있다
- **원문 대응**: Once unobserved heterogeneity is controlled for, over-education and over-skilling are associated with wage penalties, whereas under-education and under-skilling are linked to wage premiums.
- **판정**: ` O `

### C6-2 [neutral/data]

- **claim**: 과소 교육(under-education)과 과소 기술(under-skilling)은 임금 증가와 연관이 있다
- **원문 대응**: Once unobserved heterogeneity is controlled for, over-education and over-skilling are associated with wage penalties, whereas under-education and under-skilling are linked to wage premiums.
- **판정**: ` O `

### C6-3 [neutral/theory]

- **claim**: 교육 유형의 불일치와 기술 유형의 불일치 간에는 개념적·경험적 차이가 존재한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C6-4 [neutral/opinion]

- **claim**: 노동 불일치 분석에서 지표 선택이 결과에 미치는 영향은 중요하다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

<details>
<summary>본문 전문 (1,051자)</summary>

```
This paper analyses the distinction between educational and skill types of labour mismatch and their association with earnings. Drawing on cross-sectional data for 26 countries from the 1st Cycle of the OECD (2012) Survey of Adult Skills (PIAAC), I examine educational and skill mismatch using a comprehensive set of education- and skill-based indicators, explore heterogeneity across worker characteristics, and investigate the sources of conflicting country-level correlations with earnings through an error components model. The results show that country-level unobserved heterogeneity induces endogeneity bias, with both its direction and magnitude varying across mismatch measures. Once unobserved heterogeneity is controlled for, over-education and over-skilling are associated with wage penalties, whereas under-education and under-skilling are linked to wage premiums. These findings highlight both conceptual and empirical distinctions between educational and skill mismatch and demonstrate the importance of indicator choice in the analysis.
```

</details>

---

## 표본 7: arxiv-cs-si

- **제목**: Toward Temporal Realism in City-Scale Crisis Response Simulation using LLM Agents
- **URL**: https://arxiv.org/abs/2606.19904v1
- **본문 길이**: 1,892자
- **추출 claim**: 5건

### C7-1 [cautious/opinion]

- **claim**: 위기 대응 및 커뮤니티 동원 상황에서 LLM 기반 소셜 시뮬레이터는 개별 행동의 타당성에 대해 검증되지만, 현실의 시간적 패턴(버스트성, 헤비테일 분포)을 재현하는지는 검증되지 않는다
- **원문 대응**: Such settings are increasingly modeled with LLM-based social simulators, yet these simulators are validated on whether each action is individually plausible, not on whether actions are timed as in reality.
- **판정**: ` O `

### C7-2 [cautious/experiment]

- **claim**: 표준 LLM 전용 시뮬레이터는 현실의 버스트 타이밍을 거의 재현하지 못하며, 에이전트들이 거의 정기적인 시간 간격으로 행동한다
- **metric**: median burstiness: $B=-0.14$
- **원문 대응**: The LLM-only baseline yields no bursty agents (median burstiness $B=-0.14$); a single data-calibrated gate is then sufficient to lift per-agent timing above the burst threshold (median $B\approx0.37$) without degrading LLM content decisions.
- **판정**: ` O `

### C7-3 [optimistic/experiment]

- **claim**: 데이터 캘리브레이션된 자기자극 채널을 단일 게이트로 추가하면 LLM의 콘텐츠 결정을 저하시키지 않으면서 에이전트 타이밍의 버스트성 기준을 넘길 수 있다
- **metric**: median burstiness: $B\approx0.37$
- **원문 대응**: The LLM-only baseline yields no bursty agents (median burstiness $B=-0.14$); a single data-calibrated gate is then sufficient to lift per-agent timing above the burst threshold (median $B\approx0.37$) without degrading LLM content decisions.
- **판정**: ` O `

### C7-4 [conditional/theory]

- **claim**: LLM 기반 위기 대응 시뮬레이션에서 시간적 현실성은 에이전트가 행동하는 시점(자기자극과 위기 활성화 메커니즘으로 제어)을 에이전트가 무엇을 하는지(LLM으로 제어)로부터 분리함으로써 가장 잘 달성된다
- **원문 대응**: Such settings are increasingly modeled with LLM-based social simulators, yet these simulators are validated on whether each action is individually plausible, not on whether actions are timed as in reality.
- **판정**: ` O `

### C7-5 [neutral/data]

- **claim**: 오프라인 자원봉사의 버스트성 타이밍은 주로 내생적이며 자기자극적이고, COVID-19 팬데믹으로 인해 증폭되지만 일일 활동 주기에 의해 생성되지는 않는다
- **원문 대응**: We examine this gap using a multi-year, city-scale log of offline volunteering in Shenzhen that spans the COVID-19 pandemic.
- **판정**: ` O `

<details>
<summary>본문 전문 (1,892자)</summary>

```
Human collective participation is rarely steady in time: it is bursty, with short episodes of intense activity separated by long quiet intervals. In crisis response and community mobilization, predicting when people act matters as much as predicting whether they act. Such settings are increasingly modeled with LLM-based social simulators, yet these simulators are validated on whether each action is individually plausible, not on whether actions are timed as in reality. Their temporal realism, the degree to which simulated activity reproduces the bursty, heavy-tailed timing of real human systems, thus remains untested. We examine this gap using a multi-year, city-scale log of offline volunteering in Shenzhen that spans the COVID-19 pandemic. Empirically, we establish that bursty timing is common at individual and tracked-group levels, that it is largely endogenous and self-exciting, and that it is amplified by the pandemic rather than produced by daily activity cycles. A standard LLM-only simulator reproduces almost none of this timing: its synchronous schedule has no self-excitation channel, so agents act on a near-regular clock. Guided by these findings, we build a simulator in which a data-calibrated self-excitation channel and a crisis-period regime decide when each agent acts and query the LLM only at those moments, leaving it to decide which task to join and whether to commit. The LLM-only baseline yields no bursty agents (median burstiness $B=-0.14$); a single data-calibrated gate is then sufficient to lift per-agent timing above the burst threshold (median $B\approx0.37$) without degrading LLM content decisions. These results indicate that temporal realism in LLM-based crisis-response simulation is best achieved by decoupling when agents act, governed by an explicit self-excitation and crisis-activation mechanism, from what they do, governed by the LLM.
```

</details>

---

## 표본 8: mk-economy

- **제목**: 신현송 한은 총재 인구위기 경고 ...“한국 상황은 세계의 미래”
- **URL**: https://www.mk.co.kr/news/economy/12142241
- **본문 길이**: 975자
- **추출 claim**: 4건

### C8-1 [neutral/opinion]

- **claim**: 인구구조 변화는 생산성과 잠재성장률, 장기 균형금리에 영향을 미치는 핵심 변수다
- **원문 대응**: 신현송 한국은행 총재가 고령화와 저출산 등 인구구조 변화가 생산성과 잠재성장률, 장기 균형금리를 좌우하는 핵심 변수라고 강조했다.
- **판정**: ` O `

### C8-2 [optimistic/opinion]

- **claim**: 기술 발전과 AI는 감소하는 노동력을 상쇄할 수 있는 가능성이 있다
- **원문 대응**: 그는 “기술이 줄어드는 노동력을 상쇄할 수 있는지를 살펴볼 것”이라며 “AI가 힘을 보태고 있다는 증거를 확인하는 동시에 AI가 만병통치약은 아닐 수 있다는 이야기도 듣게 될 것”이라고 말했다.
- **판정**: ` O `

### C8-3 [optimistic/opinion]

- **claim**: AI가 노동력 감소를 보완하고 있다는 증거가 있다
- **원문 대응**: 그는 “기술이 줄어드는 노동력을 상쇄할 수 있는지를 살펴볼 것”이라며 “AI가 힘을 보태고 있다는 증거를 확인하는 동시에 AI가 만병통치약은 아닐 수 있다는 이야기도 듣게 될 것”이라고 말했다.
- **판정**: ` X-distortion `

### C8-4 [cautious/opinion]

- **claim**: AI는 고령화 대응의 만능 해결책이 아닐 수 있다
- **원문 대응**: 신 총재는 고령화 대응의 기회 요인으로 기술 발전과 AI도 언급했다.
- **판정**: ` O `

<details>
<summary>본문 전문 (975자)</summary>

```
“고령화·저출산, 잠재성장률 좌우
日30년 침체 속 희망적 교훈도 있어
감소하는 노동력, AI로 상쇄 주목”
신현송 한국은행 총재가 고령화와 저출산 등 인구구조 변화가 생산성과 잠재성장률, 장기 균형금리를 좌우하는 핵심 변수라고 강조했다. 그는 인구 변화가 중앙은행이 직면한 가장 중요한 장기 과제 중 하나인 만큼 한국은행이 구조적 이슈 연구에 역량을 집중해야 한다고 설명했다.
신 총재는 이날 오전 콘퍼런스 개회사에서 “중앙은행이 마주한 장기 과제 가운데 인구구조 변화는 가장 중요한 문제 중 하나”라고 강조했다.
이번 콘퍼런스는 ‘고령화와 장수의 경제학’을 주제로 한국은행과 유럽 경제정책연구센터(CEPR), 경제협력개발기구(OECD)가 공동 개최했다. 신 총재는 “오늘 한국에서 일어나고 있는 일은 머지않아 다른 여러 나라가 마주하게 될 일을 미리 보여주는 것”이라며 “인구구조 변화는 만만치 않은 도전이지만, 다가오는 것을 미리 볼 수 있고 그만큼 늦지 않게 대비할 수 있다”고 말했다.
그는 인구구조 변화가 당장의 경기 현안을 넘어 장기 시계에서 접근해야 할 과제라고 진단했다. 신 총재는 “생산성과 장기 성장이 지식의 창출과 확산에 얼마나 크게 좌우되는지를 우리는 알고 있다”며 “AI가 등장한 오늘날 이와 관련한 질문은 그 어느 때보다 날카롭게 제기되고 있다”고 말했다.
이번 콘퍼런스에서는 일본의 장기 침체와 고령화 경험, 초저출산의 배경, 교육 경쟁과 출산율, 고령화 경제의 재정 조정 부담 등이 논의된다. 신 총재는 “일본의 지난 30년 경험에는 피해야 할 중요한 함정이 있는 한편, 인구가 왜 운명이 아닌지를 말해주는 희망적인 교훈도 담겨 있다”고 설명했다.
신 총재는 고령화 대응의 기회 요인으로 기술 발전과 AI도 언급했다. 그는 “기술이 줄어드는 노동력을 상쇄할 수 있는지를 살펴볼 것”이라며 “AI가 힘을 보태고 있다는 증거를 확인하는 동시에 AI가 만병통치약은 아닐 수 있다는 이야기도 듣게 될 것”이라고 말했다.
```

</details>

---

## 표본 9: hrdive

- **제목**: Employees say only 60% of onboarding materials are necessary
- **URL**: https://www.hrdive.com/news/employees-say-only-60-of-onboarding-materials-are-necessary/829526/
- **본문 길이**: 2,363자
- **추출 claim**: 8건

### C9-1 [neutral/survey]

- **claim**: 신입사원들은 온보딩 과정에서 평균 13개의 문서를 받고 첫 주에 약 12시간을 투자하여 자료를 검토한다
- **metric**: 평균 13개 문서, 약 12시간
- **원문 대응**: - Onboarding can sometimes emphasize volume over clarity, according to a new Adobe report that found that employees reported getting an average of 13 onboarding documents and spending about 12 hours looking over materials in their first week at a new job.
- **판정**: ` O `

### C9-2 [cautious/survey]

- **claim**: 신입사원들이 받는 온보딩 자료 중 60%만이 필요하다고 평가된다
- **metric**: 60%
- **원문 대응**: - However, employees said only 60% of the onboarding materials they receive are necessary.
- **판정**: ` O `

### C9-3 [cautious/survey]

- **claim**: 온보딩 중 받은 정보의 50% 이상을 기억하는 직원은 56%에 불과하며, 나머지 44%는 절반 이하만 기억한다
- **metric**: 56%, 44%
- **원문 대응**: Meanwhile, just 56% of employees reported retaining more than half of the information they receive during onboarding, with another 44% saying they retained half or less.
- **판정**: ` O `

### C9-4 [cautious/survey]

- **claim**: 신입사원의 4명 중 1명이 온보딩이 혼란스럽거나 정보 격차가 있었다고 보고했으며, 이것이 업무 성과나 자신감에 중대하거나 중간 정도의 부정적 영향을 미쳤다
- **metric**: 4명 중 1명
- **원문 대응**: When employees did receive AI policy information during their onboarding, 38% said they retained less than half of it, with 14% reporting that they retained “little to none of it.”
- **판정**: ` O `

### C9-5 [cautious/survey]

- **claim**: 5명 중 1명 이상의 직원이 온보딩 경험으로 인해 회사 입사 결정을 재고하게 되었다
- **metric**: 5명 중 1명 이상
- **원문 대응**: In addition, more than 1 in 5 employees said their onboarding experience made them question their decision to join a company.
- **판정**: ` O `

### C9-6 [cautious/survey]

- **claim**: 상위 10% 직원의 경우 온보딩 과정에 30개 이상의 문서가 포함될 수 있으며 검토에 35시간 이상이 소요될 수 있다
- **metric**: 30개 이상 문서, 35시간 이상
- **원문 대응**: For the top 10% of employees, the onboarding process could include more than 30 documents that can take more than 35 hours to review.
- **판정**: ` O `

### C9-7 [cautious/survey]

- **claim**: 직원의 38%는 온보딩 중 기업 AI 정책에 대한 정보를 전혀 받지 못했다
- **metric**: 38%
- **원문 대응**: Meanwhile, 38% of employees said their onboarding didn’t include any information on corporate AI policies at all.
- **판정**: ` O `

### C9-8 [cautious/survey]

- **claim**: AI 정책 정보를 받은 직원 중 38%는 그 중 절반 미만만 기억했으며, 14%는 거의 기억하지 못했다
- **metric**: 38%, 14%
- **원문 대응**: When employees did receive AI policy information during their onboarding, 38% said they retained less than half of it, with 14% reporting that they retained “little to none of it.”
- **판정**: ` O `

<details>
<summary>본문 전문 (2,363자)</summary>

```
Dive Brief:
- Onboarding can sometimes emphasize volume over clarity, according to a new Adobe report that found that employees reported getting an average of 13 onboarding documents and spending about 12 hours looking over materials in their first week at a new job.
- However, employees said only 60% of the onboarding materials they receive are necessary. Meanwhile, just 56% of employees reported retaining more than half of the information they receive during onboarding, with another 44% saying they retained half or less.
- The amount of paperwork, policies, training materials and administrative tasks employees need to navigate when starting a new job can become overwhelming, even as these processes become more digital, per the report.
Dive Insight:
When these systems are disorganized, it can negatively impact employee confidence, clarity and early job performance, according to Adobe, which surveyed more than 1,000 employed people in the U.S. who started a job within the last two years.
One in four employees said their onboarding was confusing or contained gaps, which ended up having “a significant or moderate negative impact on their job performance or confidence,” per the report. In addition, more than 1 in 5 employees said their onboarding experience made them question their decision to join a company.
The results underlined how challenging it can be to process large amounts of information in a short period of time. For the top 10% of employees, the onboarding process could include more than 30 documents that can take more than 35 hours to review.
Role-specific responsibilities and expectations were the most retained topics, while, IT information, legal and compliance requirements, and artificial intelligence use policies were among the least retained.
Meanwhile, 38% of employees said their onboarding didn’t include any information on corporate AI policies at all. When employees did receive AI policy information during their onboarding, 38% said they retained less than half of it, with 14% reporting that they retained “little to none of it.”
In a June interview, the vice president of HR and talent management at ServiceMaster Brands, parent company of Merry Maids, Two Men and a Truck and Two Men and a Junk Trunk, told HR Dive that successful onboarding also includes follow-up, sometimes months or even a year afterward.
```

</details>

---

## 표본 10: mckinsey-insights

- **제목**: Earning and sustaining trust in the age of AI
- **URL**: https://www.mckinsey.com/industries/financial-services/our-insights/earning-and-sustaining-trust-in-the-age-of-ai
- **본문 길이**: 20,747자
- **추출 claim**: 6건

### C10-1 [neutral/opinion]

- **claim**: AI 도입으로 인해 투자자들의 자산관리자에 대한 기대 수준이 상향되었다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C10-2 [optimistic/case]

- **claim**: 직원들에게 AI 도구를 먼저 제공한 후 상향식 활용 사례가 하향식으로 지정된 사용 사례보다 더 효과적이었다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C10-3 [optimistic/case]

- **claim**: 대규모 기관 고객 온보딩 프로세스를 AI와 프로세스 개선을 통해 25단계에서 5단계로 단축할 수 있다
- **metric**: 25단계 → 5단계
- **원문 대응**: - The state of AI in 2025: Agents, innovation, and transformation
- **판정**: ` O `

### C10-4 [optimistic/opinion]

- **claim**: 생성형 AI와 고급 기술을 활용하면 펀드 매니저의 매도 시점 결정에서 감정을 제거하고 객관적인 검토가 가능하다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C10-5 [conditional/opinion]

- **claim**: AI 도입 시 완전히 하향식으로 통제하는 방식과 완전히 상향식 기업가적 방식 모두를 피하고 균형을 맞춰야 한다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

### C10-6 [neutral/opinion]

- **claim**: 신뢰 구축에서 가장 중요한 요소는 일관성이며, 일관성이 깨지면 신뢰를 회복하기 매우 어렵다
- **원문 대응**: (수동 확인 필요)
- **판정**: ` O `

<details>
<summary>본문 전문 (20,747자)</summary>

```
## DOWNLOADS

As artificial intelligence reshapes what investors expect from their advisors, asset managers are being pressed to move faster without eroding the trust that took decades to build. On this episode of The McKinsey Podcast, McKinsey Senior Partner and North America Chair Eric Kutcher speaks with Andrew Schlossberg, president and CEO of Invesco, about navigating market volatility, putting AI directly in employees’ hands rather than dictating its use from the top, and slowing down to speed up.

In this recurring series on The McKinsey Podcast, Kutcher speaks with top CEOs about the practice of leadership.

The McKinsey Podcast is regularly cohosted by Lucia Rahilly and Roberta Fusaro.

To watch the full-length version of this interview, visit The McKinsey Podcast playlist on McKinsey’s YouTube channel.

The following transcript has been edited for clarity and length.

## Navigating volatility

Eric Kutcher: You lead one of the largest asset managers, and there’s a lot going on in the markets right now. How do you think about the role you play for your clients in this volatile world?

Andrew Schlossberg: We have a really wide range of clients. There are a couple of common denominators, but there are also a lot of differences. One thing I’ve found over the last six to 12 months is a comfort level with uncertainty and volatility that we haven’t seen in the past.

Typically, people would run, or a very brave set of people would do something. Now there’s a comfort level with the certainty of things being uncertain. Other things are going on as well, such as people still holding cash. So there’s a fair amount of dry powder to do things like the SpaceX IPO or other things where there’s capital to deploy when there are good opportunities. The other thing I’d say is people have been really concentrated in what they’ve been holding.

One of the big pieces of advice is age-old: Look at your portfolio and make sure it’s diverse. Make sure you look at not just the first derivative but the second derivative of what you hold, so you don’t look like you’re just a US tech portfolio.

Eric Kutcher: You’ve been in this world of asset management and investing for quite some time. How has it evolved up to this point?

## Most Popular Insights

- What to read next: McKinsey’s 2026 annual book recommendations

- Is that AI agent worth it? Agentic economics and the modern operating model

- Building expertise in the age of AI: Who trains the next generation?

- How AI is reshaping the future of the AEC industry

- The state of AI in 2025: Agents, innovation, and transformation

Andrew Schlossberg: The asset management space has changed a lot in the 30 years I’ve been in it. At the same time, it comes back to some basic principles. Trust matters, and integrity matters. At the end of the day, you have to deliver investment quality for people.

Fees are always important. Having great, innovative products is always important. But if you’re not doing it consistently, it doesn’t matter much. The other thing I’ve learned over 30 years in asset management that hasn’t changed much: People like to talk about investing a lot, but they really dread having to work on their portfolio. It ranks down there with planning a funeral and going to the dentist. It’s popular to talk about, but it makes people uneasy to actually think about their investing.

Eric Kutcher: For what it’s worth, I am one of those people. I like to leave it with someone, and then I generally don’t want to touch it or be bothered. It’s much simpler.

## Putting AI to work

Eric Kutcher: How is AI going to change the world of asset management and wealth management more broadly?

Andrew Schlossberg: We can talk about it from an investment standpoint, but from a client standpoint, it’s raised the bar of expectations. People want everything, and they want it now. They want it to be hyperpersonalized and customized—and that’s not just asset management; that’s almost every industry. The tools are empowering us to do it. We’re a people business, so we’re not looking at this as replacing people. We’re looking at this as augmenting and making us better as investors and at engaging clients. I don’t think people are looking to replace their wealth manager or asset manager with AI. But their expectations of what those folks should achieve have gone up. So that’s how we have to embed it into what we’re doing, to stay ahead.

## Want to subscribe to The McKinsey Podcast?

Eric Kutcher: I’m going to date myself, but when we had this thing called WebMD and I, as a consumer, could self-diagnose—which, by the way, I think everyone is now doing even more with the various frontier models—I have to believe people are doing the same thing as you, coming in with a view of “this is what I should be doing.” How has the consumer changed in terms of education, expectations, and how they’re using the tools?

Andrew Schlossberg: Your analogy is perfect. They come more informed, and that often helps further the conversation to get into what they need personally in their portfolios. I think they also show up with some of the wrong diagnoses, to torture the analogy, so we have to spend time reeducating.

But by and large, it’s better. The need for advice has never been higher. And while we’re not the advisor ourselves, we work with advisors who help individual investors; we’ve only seen more demand for more product, not less.

Eric Kutcher: One of the things I talk a lot about with other CEOs is the individual level of productivity that comes out of AI and giving people the tools they need. We debate the efficacy of that. But inevitably, it’s making us all better and having us do things a bit faster. How are you seeing individual productivity change? And what are examples of how the processes inside your organization are changing as a result of AI?

Andrew Schlossberg: It’s an amazing catalyst to sometimes go from nothing to great, and a lot of times to go from something average to a better outcome. Thinking about an end-to-end process and how to simplify it is how we approach all of this.

We put the tools in the hands of every employee, and we’ve given top-down use cases—we’re certainly working on those. But some of the better ones are coming bottom up, from people reevaluating how they work.

For instance, onboarding a big institutional client can have 25 steps between when they’ve agreed to do business with you and when you’re actually taking their money and investing it. That’s a process we’ve been trying to reengineer for a long time—there’s a lot of hand-holding involved. How do you take it from 25 steps to five? Some of it is AI, and some of it is just good old-fashioned process engineering.

On the growth and revenue side, one of the hardest things for a fund manager to do is decide when to sell. Through advanced technology and generative AI, some of that emotion can get taken out of the decision, and another set of eyes can challenge you.

## Leading with balance

Eric Kutcher: I’ll turn to you as a CEO. You’ve spent the majority of your career at Invesco, is that right?

Andrew Schlossberg: Yes, that’s right. I’ve been in the industry for 30 years and have been here for 25.

Eric Kutcher: As you’ve grown into this role, which you’ve now held for a few years, how has your leadership style had to evolve?

> I’d also come to see over time that I needed to adjust my style—from being collaborative and building consensus to being equally decisive.

Andrew Schlossberg: I’ve had the benefit of 25 years at one company, which, especially in my generation, is unusual. One of the things that stuck out to me about Invesco—and I think this is true of the asset management industry, and frankly any professional services industry—is that it’s all about the people in the end.

Culture really matters, as does getting a real handle on it. Collaboration was at the core, along with team orientation. So when I stepped into the CEO role, I wanted to m
```

</details>

---

## 판정 코드

| 코드 | 의미 |
|---|---|
| O | 정확 - claim이 원문 근거와 의미 일치 |
| X-hallucination | 날조 - 원문에 없는 내용을 생성 |
| X-distortion | 왜곡 - 원문 의미를 변형/과장 |
| X-metric | 수치 오류 - 숫자/단위/맥락 불일치 |
| X-missing | 누락 - 원문에 중요 주장이 있으나 추출 안 됨 (별도 행 추가) |
| ? | 판단 보류 - 원문만으로 확인 불가 |

## 합산표

| 항목 | 건수 |
|---|---|
| 총 claim | 55 |
| O (정확) | 52 |
| X-hallucination | 0 |
| X-distortion | 3 |
| X-metric | 0 |
| X-missing (추가 발견) | 0 |
| ? (보류) | 0 |
| **정확도** (O / 판정 가능 건수) | **94.5%** (52/55) |