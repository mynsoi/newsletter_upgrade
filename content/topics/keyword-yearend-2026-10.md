# 키워드 탐색 — 연말 평가 시즌 (2026-10 발행 슬롯)

<!-- 조회 전용 세션 산출물 · 기준일 2026-09-18 · DB 변경 없음 -->

## 이 문서의 성격

`/topics`의 주간 후보 보고서가 **아니다**. /topics는 최근 14일 창에서 신호가 오른 묶음을 위에서부터 훑지만, 여기서는 연말 평가 시즌이라는 편성 의도에서 키워드 5개를 먼저 정하고 그 키워드로 창 전체를 훑었다. 그래서 급증도·점수 칸이 없고, 대신 **자격 기준 충족 여부**와 **무엇이 모자라는가**가 본문이다.

- **검색**: `src/search/semantic.py`의 `hybrid_search()` — 키워드(트라이그램) + 의미(pgvector) 결합. 키워드마다 질의 변형 6개를 각각 60건까지 받아 합집합으로 풀을 만들었다.
- **시간 창**: 전체 (published_at 제한 없음). `from_summary=1` claim은 제외 — 증거로 쓸 수 없다(migrations/008).
- **묶음 나누기**: `src/topics/discover.py`의 군집 로직을 그대로 재사용 (256차원 축약 · 코사인 0.62 이상 k-NN · 리더 군집 · 최소 5건).
- **자격 기준**: 독립 출처 4곳 이상 · 상반 stance(optimistic·cautious) 실존 · T1·T2 claim 2건 이상 · 연결 이론 카드 2장 이상. `qualify()`를 그대로 썼다.
- **미개척 판정**: 이론 카드 field 축 10개에 대한 발행 이력 기준. 현재 발행 2편 중 축이 잡힌 것은 「아낀 시간에는 다음 자리가 필요합니다」(일의 미래·AX) 1편뿐이므로 그 축 외에는 모두 0편이다.
- **최근 2주 신호**: 묶음 중심 벡터 반경(0.62) 안에서 2026-09-04 이후 발행분 claim 수. 묶음 자체의 크기가 아니라 '지금도 새 재료가 들어오는가'를 본다.

> 읽는 법: 자격 통과가 곧 초안 착수 승인은 아니다. 여기 재료 수는 창 전체 기준이고 `/draft` ② 증거 수집은 더 좁은 조건으로 다시 센다. 특히 증거 claim이 10건 미만인 묶음은 증거 수집에서 3건 미만으로 떨어질 수 있다.

---

## AI 업무 성과 평가

*10/2 창간호 후보 — AI Task를 연말에 어떻게 셀 것인가*

- 질의 변형: AI 업무 성과 평가 / AI 활용 성과를 평가에 반영 / 생산성 측정 지표 / AI 도입 효과 측정 / 성과 관리 제도 변화 / AI 사용량과 성과의 관계
- 군집에 들어간 claim 189건 → 묶음 8개 → **자격 통과 6개**

### 후보

| # | 주제 | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 | 최근 2주 신호 |
|---|---|---|---|---|---|---|
| 1 | AI를 쓴 일의 성과를 무엇으로 셀지 조직마다 지표를 새로 짜고 있고, 사용 여부를 평가에 반영하겠다는 결정이 지표 설계보다 먼저 와 있다 | claim 69건 · 출처 21곳 · stance cautious 18 / conditional 15 / neutral 22 / optimistic 14 · T1·T2 48건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.63) · 컴퓨터화 취약성 추정(0.59) · 적기 인재 조달(0.58) | 세는 단위를 바꾸지 않으면 'AI를 썼다'는 사실만 남는다 — 탤런트십의 질문(이 지표가 어떤 의사결정을 바꾸는가)을 연말 평가 항목에 그대로 대 본다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 526건·문서 280건) |
| 2 | AI의 생산성 효과가 나타나는 시점과 층위가 어긋난다 — 도입 초기에는 되레 떨어지고, 개인 단위 개선이 조직 성과로 이어지지 않는 구간이 있다 | claim 40건 · 출처 19곳 · stance cautious 8 / conditional 13 / neutral 8 / optimistic 11 · T1·T2 23건 | 컴퓨터화 취약성 추정(0.61) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.53) · 얼라이언스와 투어 오브 듀티(0.53) | 연말에 재는 시점이 곧 결론을 만든다 — 1년 치를 한 번에 재는 방식이 첫해 AI Task를 가장 불리하게 평가한다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 128건·문서 91건) |
| 3 | 같은 AI 활용을 놓고 자기 보고로 잰 효과와 통제된 조건에서 잰 효과가 크게 벌어지고, 효과의 크기는 원래 성과 수준에 따라 다르다 | claim 33건 · 출처 12곳 · stance cautious 8 / conditional 3 / neutral 8 / optimistic 14 · T1·T2 20건 | 팀 효과성 모형(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 탤런트십과 의사결정 과학(0.58) | 자기 보고를 성과의 증거로 받으면 부풀려진 숫자를 결재하는 셈이다 — 측정 방식이 먼저 정해져야 평가가 성립한다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 385건·문서 236건) |
| 4 | 개인 단위로 재면 좋아 보이는 AI 성과가 조직 단위에서는 산출물의 다양성 감소로 나타난다 | claim 16건 · 출처 6곳 · stance cautious 6 / conditional 1 / neutral 4 / optimistic 5 · T1·T2 14건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.55) · 경험학습 사이클(0.53) · 적응적 리더십(0.51) | 평가 단위를 개인에 두면 조직이 잃는 것이 장부에 남지 않는다 — 형평이론의 비교 준거를 개인에서 팀으로 옮겨 보는 각도 | 기발행 (일의 미래·AX 1편) | 있음 (claim 107건·문서 92건) |
| 5 | 같은 사용량이라도 사용 방식에 따라 역량이 늘기도 하고 깎이기도 한다 — 과도 의존형·혼합형·균형형이라는 서로 다른 행동 프로필이 관측된다 | claim 14건 · 출처 6곳 · stance cautious 5 / conditional 2 / neutral 5 / optimistic 2 · T1·T2 10건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 컴퓨터화 취약성 추정(0.58) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.58) | 연말에 셀 것은 사용량이 아니라 사용 방식이다 (재료 상당수가 학생 대상 연구라 사내 적용 시 외적 타당도 확인 필요) | **미개척** (학습·HRD 0편) | 있음 (claim 251건·문서 181건) |
| 6 | AI를 많이 쓰는 것과 성과·보상이 연결되지 않는 구간이 실제로 관측된다 — 고사용자의 인지 부담이 오히려 늘고, 뒤처질까 걱정하는 비율과 보상받는다고 느끼는 비율이 크게 벌어진다 | claim 6건 · 출처 5곳 · stance cautious 3 / neutral 2 / optimistic 1 · T1·T2 4건 | 선발 방법의 예측타당도와 유용성(0.54) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 얼라이언스와 투어 오브 듀티(0.52) | 사용량을 성과로 치환한 제도는 많이 쓴 사람을 손해 보게 만든다 — 커의 'A를 보상하면서 B를 기대하는 어리석음'이 AI Task 제도에서 재현되는 경로 | **미개척** (평가·공정성 0편) | 있음 (claim 162건·문서 109건) |

### 자격 미달 묶음과 보강안

| # | 재료 | 대표 claim 한 줄 | 미달 항목 | 백필하면 채워질 재료 |
|---|---|---|---|---|
| 7 | claim 6건 · 출처 4곳 · T1·T2 2건 | 중간 관리자 역할이 자동화에 특히 취약한 위험에 노출되어 있다… | 상반 stance 없음 (optimistic 0건) | 관리자 역할 변화의 낙관 쪽 근거가 통째로 비어 있다. josh-bersin·hrdive의 'AI 보좌 관리자' 리포트, HBR Korea의 관리 폭 확대 기사를 건별로 올리면 채워진다 |
| 8 | claim 5건 · 출처 5곳 · T1·T2 2건 | AI 자문 시점의 타이밍이 학습 성과에 상당한 영향을 미친다… | 상반 stance 없음 (cautious 0건) | AI 학습 효과에 대한 조직 맥락의 신중론이 없다. Charter·MIT Sloan Management Review의 AI 교육 투자 회수 회의 기사, ms-worklab의 역효과 지표가 후보 |

### 묶음 상세

#### 묶음 1 — 자격 통과 (claim 69건)

- 출처 21곳: academic-canon, aitimes, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, bain-insights, bcg-publications, charter, deloitte-insights, donga-economy, fastcompany-worklife, hankyung-it, hbr-korea, hrdive, hrtech-series, innofit-blog, josh-bersin, mckinsey-insights, ms-worklab, the-ai, worklytics-blog
- stance: cautious 18 / conditional 15 / neutral 22 / optimistic 14 · T1·T2 48건 · 문서 64건
- 주제 축 일의 미래·AX (유사도 0.697) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.63) · 컴퓨터화 취약성 추정(0.59) · 적기 인재 조달(0.58) · 경험학습 사이클(0.55) · 탤런트십과 의사결정 과학(0.54)

대표 claim:

- `1A06A3BB0386AAB3F7433871818` [T1·academic-canon·optimistic] AI 도입이 AI 능력 범위 내의 업무에서 지식근로자의 완료율을 12% 이상 향상시킨다
- `1A06A3BB0EC430C086E7EC75AFA` [T1·academic-canon·optimistic] AI 도입이 AI 능력 범위 내의 업무에서 응답 품질을 평균 32% 개선시킨다
- `1A09790C4593D5675148E35FC19` [T1·arxiv-cs-cy·conditional] AI 영향 평가는 자동화율 예측을 넘어 윤리, 웰빙, 전문성 관련 질문을 포함해야 한다
- `1A09285B918DA7CAAA3D8B422E6` [T1·arxiv-cs-cy·cautious] AI 능력 평가는 첫 번째 순서 효과(시스템 산출물의 정확성, 독성이나 편향 여부)는 포착할 수 있지만, AI의 두 번째 순서 효과(장기적 결과와 실제 사용으로부터의 결과)는 포착하지 못한다
- `1A0B173B78AFA6D999C26298296` [T1·arxiv-cs-hc·conditional] AI 에이전트의 신뢰도 보정 수준에 따라 휴먼-AI 결합 추론의 정확도 향상 폭이 달라진다

#### 묶음 2 — 자격 통과 (claim 40건)

- 출처 19곳: academic-canon, ai-post, aitimes, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, bcg-publications, brookings-future-of-work, carrot-global-blog, hankyung-it, hrdive, innofit-blog, josh-bersin, manual, mckinsey-insights, mk-economy, onemodel-blog, the-ai, worklytics-blog
- stance: cautious 8 / conditional 13 / neutral 8 / optimistic 11 · T1·T2 23건 · 문서 39건
- 주제 축 일의 미래·AX (유사도 0.676) · 발행 1편
- 이론 카드: 컴퓨터화 취약성 추정(0.61) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.53) · 얼라이언스와 투어 오브 듀티(0.53) · 흡수역량(0.52) · 선발 방법의 예측타당도와 유용성(0.51)

대표 claim:

- `1A06A3BABFDB1FEECE2628C2F5D` [T1·academic-canon·optimistic] AI 도구 사용 시 업무 완료율이 평균 12.2% 증가한다.
- `1A08D5E6E415F8ED91031C01783` [T1·arxiv-cs-cy·cautious] AI 도입이 효율성 증대와 품질 향상을 약속하지만, 실제 결과는 항상 명확하지 않다
- `1A0B1746688A36EDDF71009C746` [T1·arxiv-cs-hc·conditional] AI 도구의 생산성 향상 효과는 작업 복잡도, 개인의 사용 패턴, 팀 수준의 도입 정도에 따라 달라진다
- `1A0B17467DF9082EB731737BC0E` [T1·arxiv-cs-hc·cautious] AI 도구가 협업에 미치는 영향에 대한 증거는 상대적으로 제한적이다
- `1A0612DF2DFB7161EE90396C930` [T2·josh-bersin·conditional] AI 도입 시 생산성이 향상되지만 시스템 비용과 투자 회수 기간으로 인해 단순하지 않은 결과를 초래한다

#### 묶음 3 — 자격 통과 (claim 33건)

- 출처 12곳: academic-canon, ai-lab-enterprise-reports, aihr-blog, aitimes, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, charter, hr-bulletin, hrdive, hrtech-series, worklytics-blog
- stance: cautious 8 / conditional 3 / neutral 8 / optimistic 14 · T1·T2 20건 · 문서 31건
- 주제 축 일의 미래·AX (유사도 0.725) · 발행 1편
- 이론 카드: 팀 효과성 모형(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 탤런트십과 의사결정 과학(0.58) · 직무특성모형(0.57) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.57)

대표 claim:

- `1A06A3BAD66E8A5E1FCCF1363A0` [T1·academic-canon·optimistic] AI 지원 업무에서 하위 50% 성과층이 상위 50% 성과층보다 더 큰 성능 개선 효과를 얻는다.
- `1A097899A5784A11D398CCA0DCC` [T1·arxiv-cs-cy·optimistic] AI 통합으로 인해 학생 참여도와 성과 향상이 관찰된다
- `1A0927FCE01184F5161BBC38027` [T1·arxiv-cs-cy·cautious] AI는 효율성과 최적화 측면에서 우수하지만, 경험적 기반에서 비롯된 방향성과 신체화된 유연성이 부족하다
- `1A08D64459B3432E43DDF4879A0` [T1·arxiv-cs-cy·neutral] AI 인터뷰 완료율 데이터(지원자의 완료 여부)는 최종 면접 성과 예측보다 직무 탐색 동기를 더 일관되게 반영한다
- `1A0B16C0912880319686DB97430` [T1·arxiv-cs-hc·optimistic] AI의 성능 통찰력에 대한 정보를 제공하면 작업 성과가 향상된다

#### 묶음 4 — 자격 통과 (claim 16건)

- 출처 6곳: aihr-blog, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, innofit-blog, mckinsey-insights
- stance: cautious 6 / conditional 1 / neutral 4 / optimistic 5 · T1·T2 14건 · 문서 15건
- 주제 축 일의 미래·AX (유사도 0.631) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.55) · 경험학습 사이클(0.53) · 적응적 리더십(0.51) · 문화 차원 이론(0.51) · 형평이론(0.50)

대표 claim:

- `1A061493114A589D0750848E873` [T2·mckinsey-insights·conditional] 생성형 AI는 기술 도입률과 근로자 시간 재배치 정도에 따라 2040년까지 연간 0.1~0.6%의 노동 생산성 증가를 가능하게 할 수 있다
- `1A097AA509310F1A4E7BAE90624` [T1·arxiv-cs-cy·cautious] 생성형 AI의 출력 분산 감소는 사회·집단·개인 수준과 물질적·비물질적 차원에서 부정적 영향을 미칠 수 있다
- `1A08D68A49264D0EB8CE28CD993` [T1·arxiv-cs-cy·neutral] 생성형 AI 학생 성공 인식 측정에서 역분산 가중치 구조는 시뮬레이션 결과에 실질적인 영향을 미친다
- `1A08845BE651077F5EED9E17900` [T1·arxiv-cs-cy·cautious] 생성형 AI 도구가 프로젝트 기반 평가에서 최종 산출물의 진정성과 학습 검증을 위협한다
- `1A06B16A567E208AC0C3BEADA37` [T1·arxiv-cs-cy·optimistic] 생성형 AI 사용으로 인한 평균 인지된 품질 개선도는 7점 만점에 6.27점이다

#### 묶음 5 — 자격 통과 (claim 14건)

- 출처 6곳: arxiv-cs-cy, arxiv-cs-hc, charter, hankyung-it, mk-economy, ms-worklab
- stance: cautious 5 / conditional 2 / neutral 5 / optimistic 2 · T1·T2 10건 · 문서 13건
- 주제 축 학습·HRD (유사도 0.717) · 발행 0편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 컴퓨터화 취약성 추정(0.58) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.58) · 데니슨 조직문화 모델(0.56) · 팀 효과성 모형(0.56)

대표 claim:

- `1A08839FC6BB262F3AB611CC71A` [T1·arxiv-cs-cy·neutral] AI 사용 여부와 위험 인식 사이에는 통계적으로 유의미한 관련성이 있다
- `1A082F4FDC2562D08166CDB1E0C` [T1·arxiv-cs-cy·cautious] AI 사용은 비판적 사고력 약화, 기술 능력 저하, 불안감 증가라는 위험을 초래한다
- `1A0A2DACE3E387129C5561C7BB3` [T1·arxiv-cs-hc·optimistic] AI 사용 시 비판적 사고 성향이 높을수록 사실 판단 정확도가 더 높다
- `1A06B272BAA36DA9E7F103C6DCE` [T1·arxiv-cs-cy·cautious] AI 사용자 중 상당수가 지속적 노력에 대한 인내심 감소를 보고했다
- `1A06B272CB8A8A4C12D454CADC9` [T1·arxiv-cs-cy·neutral] AI 사용자는 과도 의존형, 혼합전략형, 균형잡힌 지원추구형 등 서로 다른 행동 프로필을 나타낸다

#### 묶음 6 — 자격 통과 (claim 6건)

- 출처 5곳: arxiv-cs-cy, arxiv-cs-hc, mckinsey-insights, ms-worklab, zdnet-korea
- stance: cautious 3 / neutral 2 / optimistic 1 · T1·T2 4건 · 문서 6건
- 주제 축 평가·공정성 (유사도 0.633) · 발행 0편
- 이론 카드: 선발 방법의 예측타당도와 유용성(0.54) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 얼라이언스와 투어 오브 듀티(0.52) · 컴퓨터화 취약성 추정(0.52) · 형평이론(0.52)

대표 claim:

- `1A08D5245FB22192CB864355CEA` [T1·arxiv-cs-cy·neutral] AI의 의인화 정도가 사용자의 AI에 대한 신뢰도와 기대치에 영향을 미친다
- `1A0A2E2B877A137D8A90648806A` [T1·arxiv-cs-hc·neutral] AI 사용을 명시적으로 공개하면 커뮤니티의 질문과 댓글이 증가하지만, 이러한 효과는 도구 선택에 비해 훨씬 작다
- `1A06B774F00C9C201DE9F384C0C` [T1·arxiv-cs-hc·cautious] AI를 많이 사용하는 사용자는 비슷한 수준의 동료 중 AI를 사용하지 않는 사용자보다 성과가 낮다
- `1A061210902EC955B670CEEE43E` [T2·mckinsey-insights·cautious] AI를 집중적으로 사용하는 고용량 사용자 집단의 인지적 부담이 감소하지 않고 오히려 증가하는 경향을 보인다
- `1A09783ED66AD6D197BAAFED53D` [T5·zdnet-korea·optimistic] AI 실행 역량이 우수한 기업은 그렇지 않은 기업보다 AI 도입으로부터 얻는 재무 성과가 훨씬 크다

#### 묶음 7 — 자격 미달 (claim 6건)

- 출처 4곳: arxiv-cs-cy, fastcompany-worklife, hr-bulletin, worklytics-blog
- stance: cautious 2 / conditional 1 / neutral 3 · T1·T2 2건 · 문서 6건
- 주제 축 인재·리텐션 (유사도 0.695) · 발행 0편
- 이론 카드: 적기 인재 조달(0.64) · 관리와 리더십의 구분(0.63) · 공유 리더십(0.59) · 심리적 계약(0.59) · 얼라이언스와 투어 오브 듀티(0.59)
- 미달 사유: 상반 stance 없음 (optimistic 0건)

대표 claim:

- `1A0694360158877E82FD76832DF` [T1·arxiv-cs-cy·cautious] 중간 관리자 역할이 자동화에 특히 취약한 위험에 노출되어 있다
- `1A06944B862DF4A66FAA4E54E9C` [T1·arxiv-cs-cy·neutral] 2022년 이후 소프트웨어 및 검증 역할은 증가했으나 개념 및 관리 역할은 감소했다
- `1A0640C69265D0B10F98AD830FD` [T3·hr-bulletin·neutral] 2020년 이후 관리자의 업무 몰입도가 지속적으로 하락했다
- `1A0614B6E3933A3F10AC5BB7C4A` [T4·worklytics-blog·conditional] 관리자 행동(일관되지 않은 체크인, 경계 위반 등)이 팀 성과와 이직률에 영향을 미친다
- `1A06137CF48CF2B105EADD78117` [T3·fastcompany-worklife·cautious] 개인 기여자로서 탁월한 성과를 이유로 관리직에 승진한 직원이 관리자 역할에 부적합하면 조직 문화와 성과에 부정적 영향을 미친다

#### 묶음 8 — 자격 미달 (claim 5건)

- 출처 5곳: arxiv-cs-cy, arxiv-cs-hc, charter, donga-economy, hbr
- stance: conditional 1 / neutral 1 / optimistic 3 · T1·T2 2건 · 문서 5건
- 주제 축 학습·HRD (유사도 0.708) · 발행 0편
- 이론 카드: 학습전이 이론(0.58) · 데니슨 조직문화 모델(0.57) · 70:20:10 프레임워크(0.57) · 탤런트십과 의사결정 과학(0.56) · 경험을 통한 리더 성장(0.54)
- 미달 사유: 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A073811BE76F31029273D4ED0F` [T1·arxiv-cs-cy·neutral] AI 자문 시점의 타이밍이 학습 성과에 상당한 영향을 미친다
- `1A06B53F2EDCAC7FB5477EF9785` [T1·arxiv-cs-hc·optimistic] AI 활용 학생이 학습에 대한 즐거움을 더 크게 보고했다
- `1A0611AE0ADBA2FD573D86040A4` [T3·hbr·optimistic] AI 역량을 이해하고 활용하는 방법을 익힌 직원이 업무와 생활에서 더 뛰어난 성과를 낼 것이다.
- `1A083E15ED5C2D416CCA421AD3C` [T5·donga-economy·optimistic] AI 활용 교육과 현장 적용 과제를 통해 품질 관리와 업무 효율성을 동시에 향상시킬 수 있다
- `1A0B15C3AA60A80EC81A1F33D7D` [T3·charter·conditional] AI 도입 시 효율성 향상을 인간의 주체성, 통제력, 잠재력 발현과 결합할 수 있다

---

## 자기 평가·성과 서술

*10/9 후보 — AI가 섞인 일의 성과를 본인 평가에 쓰는 법*

- 질의 변형: 자기 평가 성과 서술 / AI가 한 일과 내가 한 일의 구분 / 기여도 귀속 / AI 도움을 받은 결과물의 저자 / 업무 산출물의 책임 소재 / 성과 기록과 증빙
- 군집에 들어간 claim 104건 → 묶음 7개 → **자격 통과 4개**

### 후보

| # | 주제 | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 | 최근 2주 신호 |
|---|---|---|---|---|---|---|
| 1 | AI가 섞인 산출물에서 '누가 무엇을 했는가'를 구분하기 어려워지고, 원저작성 검증 자체가 과제가 됐다 | claim 40건 · 출처 14곳 · stance cautious 16 / conditional 2 / neutral 8 / optimistic 14 · T1·T2 28건 | 컴퓨터화 취약성 추정(0.56) · 선발 방법의 예측타당도와 유용성(0.55) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) | 본인 평가에 적을 것은 결과물이 아니라 판단이 개입한 지점이다 — 직무특성모형의 과업 정체성(내 일의 처음과 끝을 알아보는가)이 흔들리는 자리 | 기발행 (일의 미래·AX 1편) | 있음 (claim 207건·문서 149건) |
| 2 | 사람과 AI의 역할 분담이 업무 종류마다 다르게 정착하고 있다 — 직접 실행·반복 정제·인간 주도라는 서로 다른 모드가 구분되고, 단순 업무에서는 격차가 줄지만 복잡한 판단에서는 벌어진다 | claim 23건 · 출처 9곳 · stance cautious 3 / conditional 4 / neutral 9 / optimistic 7 · T1·T2 17건 | RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.63) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.58) · 팀 효과성 모형(0.58) | 성과 서술의 단위는 '도구를 썼다'가 아니라 '어느 모드로 일했다'여야 한다 — 같은 도구라도 모드가 다르면 기여가 다르다 | **미개척** (조직설계·변화 0편) | 있음 (claim 279건·문서 193건) |
| 3 | AI 산출물의 검증 비용이 기대 효용을 넘어서면 사람은 검증을 건너뛰고, 그 순간 결과에 대한 책임이 사라진다 | claim 10건 · 출처 6곳 · stance cautious 6 / conditional 1 / neutral 1 / optimistic 2 · T1·T2 7건 | 자동화의 대체·보완 이중효과와 폴라니의 역설(0.57) · 보상에 관한 여섯 가지 위험한 통념(0.56) · 조직문화 3수준 모형(0.56) | 자기 평가에 쓸 수 있는 근거는 산출물이 아니라 검증한 흔적이다 — 검증을 남기지 않은 성과는 본인 것이라고 말하기 어렵다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 103건·문서 84건) |
| 4 | AI가 직무의 구성과 암묵지 관행을 재편하면서 '내 일'의 경계가 다시 그려지고 있다 | claim 12건 · 출처 8곳 · stance cautious 1 / conditional 2 / neutral 7 / optimistic 2 · T1·T2 6건 | RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.60) · 직무특성모형(0.58) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.57) | 경계가 바뀐 해에 작년 양식으로 성과를 적으면 바뀐 부분이 통째로 빠진다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 199건·문서 149건) |

### 자격 미달 묶음과 보강안

| # | 재료 | 대표 claim 한 줄 | 미달 항목 | 백필하면 채워질 재료 |
|---|---|---|---|---|
| 5 | claim 9건 · 출처 3곳 · T1·T2 8건 | 생성형 AI 지침이 개별 연구자에게 준수 책임을 지우면서 결과적으로 연구자의 책임이… | 독립 출처 3곳 (기준 4곳) | 책임성 논의가 arxiv 두 곳에 몰려 있다. deloitte-insights·pwc-global-insights의 AI 거버넌스 리포트, HBR Korea의 AI 책임 소재 기사 건별 수집으로 출처를 넓힐 수 있다 |
| 6 | claim 5건 · 출처 2곳 · T1·T2 5건 | 동료 평가(peer assessment) 결과가 교수자 평가와 중간 정도의 정확성으… | 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건) | 자기평가의 정확도를 다룬 재료가 교육 맥락 arxiv 2곳뿐. **이론 카드 추가가 가장 빠르다** — 자기평가 타당도(Mabe & West 메타분석), 성과평가 100년(DeNisi & Murphy 2017). 여기에 HBR Korea 자기평가 기사 1~2건 |
| 7 | claim 5건 · 출처 3곳 · T1·T2 4건 | 주관적 평가 방식은 응답 데이터의 노이즈와 세분화되지 않은 평가 결과로 인해 효과성… | 독립 출처 3곳 (기준 4곳) | 10/9에 가장 정확히 맞는 묶음인데 출처가 3곳이라 한 칸 모자란다(이론 카드 연결은 이 키워드에서 가장 강하다 — HRM-성과 블랙박스 0.64·조직공정성 0.62). DBR·HBR Korea 평가 시즌 특집을 /browse-collect로 2~3건만 올리면 자격을 채운다 |

### 묶음 상세

#### 묶음 1 — 자격 통과 (claim 40건)

- 출처 14곳: academic-canon, ai-post, arxiv-cs-cy, arxiv-cs-hc, bain-insights, charter, fastcompany-worklife, flex-blog, hrdive, innofit-blog, knowledge-wharton, mckinsey-insights, the-ai, worklytics-blog
- stance: cautious 16 / conditional 2 / neutral 8 / optimistic 14 · T1·T2 28건 · 문서 36건
- 주제 축 일의 미래·AX (유사도 0.667) · 발행 1편
- 이론 카드: 컴퓨터화 취약성 추정(0.56) · 선발 방법의 예측타당도와 유용성(0.55) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 팀 효과성 모형(0.52) · 직무특성모형(0.52)

대표 claim:

- `1A06A3BABFDB1FEECE2628C2F5D` [T1·academic-canon·optimistic] AI 도구 사용 시 업무 완료율이 평균 12.2% 증가한다.
- `1A06A3BB0EC430C086E7EC75AFA` [T1·academic-canon·optimistic] AI 도입이 AI 능력 범위 내의 업무에서 응답 품질을 평균 32% 개선시킨다
- `1A08D665270785FD0928C6B1669` [T1·arxiv-cs-cy·cautious] AI 도구의 과도한 의존, 학술 무결성 문제, 학생 작업물 원저작성 검증의 어려움이 컴퓨터과학 교육에서의 도전 과제다
- `1A08D5E6CDA2E59816467DC7037` [T1·arxiv-cs-cy·neutral] AI 도구가 설문 구성, 데이터 종합, 분석 수행, 결과 요약 작성 등 연구 업무에 활용되고 있다
- `1A0B1746688A36EDDF71009C746` [T1·arxiv-cs-hc·conditional] AI 도구의 생산성 향상 효과는 작업 복잡도, 개인의 사용 패턴, 팀 수준의 도입 정도에 따라 달라진다

#### 묶음 2 — 자격 통과 (claim 23건)

- 출처 9곳: aitimes, arxiv-cs-cy, arxiv-cs-hc, bain-insights, dbr, hr-bulletin, hrtech-series, ms-worklab, the-ai
- stance: cautious 3 / conditional 4 / neutral 9 / optimistic 7 · T1·T2 17건 · 문서 22건
- 주제 축 조직설계·변화 (유사도 0.696) · 발행 0편
- 이론 카드: RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.63) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.58) · 팀 효과성 모형(0.58) · 직무특성모형(0.58) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.57)

대표 claim:

- `1A0979C53F7BE11F35F7CADC678` [T1·arxiv-cs-cy·neutral] AI와 협업할 때 참여자들이 인간 파트너와 협업할 때보다 더 많은 업무를 위임했다
- `1A08D5E6FAA37CE7AA9F83E7727` [T1·arxiv-cs-cy·conditional] AI가 분석가의 업무를 보조할 수 있지만, 버튼 하나로 자동화하는 방식에 대해서는 주의가 필요하다
- `1A0B16C0912880319686DB97430` [T1·arxiv-cs-hc·optimistic] AI의 성능 통찰력에 대한 정보를 제공하면 작업 성과가 향상된다
- `1A0AC5178A5416A4A866C15567C` [T1·arxiv-cs-hc·neutral] AI 지원 면접에서 면접관과 AI 간의 역할, 관계, 협업 행동, 책임이 동적으로 변화한다
- `1A0A71F94412287A1C43E27272C` [T1·arxiv-cs-hc·conditional] AI는 구조화된 일상적 업무에서는 성과 격차를 균등화하지만, 깊이 있는 판단이 필요한 복잡한 업무에서는 기존의 격차를 증폭시킨다

#### 묶음 3 — 자격 통과 (claim 10건)

- 출처 6곳: arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, deloitte-insights, fastcompany-worklife, hrtech-series
- stance: cautious 6 / conditional 1 / neutral 1 / optimistic 2 · T1·T2 7건 · 문서 10건
- 주제 축 일의 미래·AX (유사도 0.694) · 발행 1편
- 이론 카드: 자동화의 대체·보완 이중효과와 폴라니의 역설(0.57) · 보상에 관한 여섯 가지 위험한 통념(0.56) · 조직문화 3수준 모형(0.56) · 컴퓨터화 취약성 추정(0.55) · 산업 노사관계 시스템 이론(0.54)

대표 claim:

- `1A0883BCDC12521F79EFBE3EC73` [T1·arxiv-cs-cy·optimistic] AI의 추론 과정을 시각화한 자료는 의사결정의 해석 가능성과 품질을 향상시킬 수 있다
- `1A06B7BB6B7119A4A294DC9DAAA` [T1·arxiv-cs-hc·cautious] AI 시스템이 검증 불가능하지만 그럴듯한 산출물을 생성할 때 결과 기반의 행위성은 환상일 수 있다
- `1A06AE3F6F74F8187825E02F968` [T1·arxiv-cs-cy·cautious] AI 생성 산출물의 검증 비용이 그에 따른 기대 효용을 초과하면, 합리적 행위자들은 불작위를 선택하게 되며 이는 안정적이지만 파국적인 내시 균형 상태를 초래한다
- `1A06ACA748E45D47FAADFA16812` [T1·arxiv-cs-cy·conditional] AI 투명성은 최종 산출물 탐지를 넘어 상호작용 기록을 문서화하는 방향으로 나아가야 한다
- `1A061410B73C0097A2017D587E2` [T2·deloitte-insights·cautious] 의사결정 시 AI 산출물의 품질을 정기적으로 검증하는 경영진은 절반에 불과하다

#### 묶음 4 — 자격 통과 (claim 12건)

- 출처 8곳: arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, carrot-global-blog, hbr, mk-economy, ms-worklab, onemodel-blog
- stance: cautious 1 / conditional 2 / neutral 7 / optimistic 2 · T1·T2 6건 · 문서 12건
- 주제 축 일의 미래·AX (유사도 0.688) · 발행 1편
- 이론 카드: RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.60) · 직무특성모형(0.58) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.57) · 총보상 모델(0.56) · 적응적 리더십(0.55)

대표 claim:

- `1A09790C50D29DC48F2531B11D4` [T1·arxiv-cs-cy·neutral] AI는 인간-기술 관계, 전문직 역할, 암묵적 지식 관행을 재편성한다
- `1A0B17469387A9ADDBAEDFB205A` [T1·arxiv-cs-hc·optimistic] AI는 개발자를 대체하기보다는 증강하는 역할을 한다
- `1A06E56A0A1356095783785FB84` [T1·arxiv-cs-cy·neutral] AI가 인지 능력을 생물학적 제약에서 분리함에 따라 측정 가능한 업무 실행의 한계 비용이 0에 수렴한다
- `1A06BAE19D509B01782ABD06D6B` [T1·arxiv-cs-hc·conditional] AI는 과학자의 신체적 작업을 완전히 대체하기보다는 배경 인프라로 지원하는 역할이 적절하다
- `1A06BE0A2F5CA7270DFC3A14A12` [T1·arxiv-econ-gn·neutral] 자동화는 일상적 업무에 집중되어 있고, AI는 인지 업무에 집중되어 있다

#### 묶음 5 — 자격 미달 (claim 9건)

- 출처 3곳: arxiv-cs-cy, arxiv-cs-hc, zdnet-korea
- stance: cautious 2 / conditional 3 / neutral 3 / optimistic 1 · T1·T2 8건 · 문서 9건
- 주제 축 인재·리텐션 (유사도 0.661) · 발행 0편
- 이론 카드: 적기 인재 조달(0.59) · 컴퓨터화 취약성 추정(0.53) · 사회기술시스템 이론(0.52) · 산업 노사관계 시스템 이론(0.51) · 갤럽 Q12와 위대한 관리자의 네 열쇠(0.51)
- 미달 사유: 독립 출처 3곳 (기준 4곳)

대표 claim:

- `1A097AAA023597F5274BD0AB3BE` [T1·arxiv-cs-cy·cautious] 생성형 AI 지침이 개별 연구자에게 준수 책임을 지우면서 결과적으로 연구자의 책임이 증가한다
- `1A0928FB1FCC5DB3FA553B7DBE2` [T1·arxiv-cs-cy·neutral] AI 실패 사건 이후 식별 가능한 책임자의 존재 여부가 반드시 책임 추적성 증가로 이어지지는 않는다
- `1A08D5DFA87F1E5BAC5E21200BE` [T1·arxiv-cs-cy·conditional] AI의 발전이 환경 책임성과 윤리적 책임성에 부합해야 더욱 포용적이고 지속 가능한 기술 미래를 보장할 수 있다
- `1A088474DD3230BA9E923A18D5E` [T1·arxiv-cs-cy·optimistic] 사회적 책임 요구사항을 통합하는 고급 AI 시스템도 기술적 성능을 훼손하지 않으면서 개발할 수 있다
- `1A0A71FB4FA3B27F4888AE7B3A8` [T1·arxiv-cs-hc·conditional] AI가 소비자, 유권자, 의사결정자의 필요에 부응하려면 AI의 책임성이 필수적이다

#### 묶음 6 — 자격 미달 (claim 5건)

- 출처 2곳: arxiv-cs-cy, arxiv-cs-hc
- stance: conditional 1 / neutral 2 / optimistic 2 · T1·T2 5건 · 문서 5건
- 주제 축 학습·HRD (유사도 0.676) · 발행 0편
- 이론 카드: 선발 방법의 예측타당도와 유용성(0.59) · 기대이론(0.58) · 70:20:10 프레임워크(0.55) · 문화 차원 이론(0.55) · 경험학습 사이클(0.55)
- 미달 사유: 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A092809E5142DA5007FDAA04EC` [T1·arxiv-cs-cy·conditional] 동료 평가(peer assessment) 결과가 교수자 평가와 중간 정도의 정확성으로 일치한다
- `1A08D54595444222C58C49792AD` [T1·arxiv-cs-cy·neutral] 학생의 자기평가와 최종 강사 평가 사이에 일치도가 있었다
- `1A09CC85FF9A7777E829B4319C9` [T1·arxiv-cs-hc·neutral] 학습자가 인간 강사 피드백에 부여하는 평가는 인지된 진정성으로 예측된다
- `1A06B24B48D11129B9D836A30CB` [T1·arxiv-cs-cy·optimistic] 피어 리뷰와 멀티미디어 문서화를 포함한 평가 방식이 학생의 의사소통 능력을 유의미하게 향상시킨다
- `1A0A6FFB9EC3930FB51F7F7605F` [T1·arxiv-cs-hc·optimistic] 창의성 역량 평가에서 자동 평가기의 실효성이 실제 학생 과제 수행 평가에서 입증되었다

#### 묶음 7 — 자격 미달 (claim 5건)

- 출처 3곳: arxiv-cs-cy, arxiv-cs-hc, manual
- stance: cautious 3 / conditional 1 / optimistic 1 · T1·T2 4건 · 문서 5건
- 주제 축 평가·공정성 (유사도 0.761) · 발행 0편
- 이론 카드: HRM-성과 연계와 블랙박스(0.64) · 조직공정성 이론(0.62) · 목표관리(0.59) · 사회기술시스템 이론(0.58) · 기대이론(0.58)
- 미달 사유: 독립 출처 3곳 (기준 4곳)

대표 claim:

- `1A0927B2978F5AAFEA55E349D2E` [T1·arxiv-cs-cy·cautious] 주관적 평가 방식은 응답 데이터의 노이즈와 세분화되지 않은 평가 결과로 인해 효과성이 제한된다
- `1A06B2139FE1534B00485BEF2BD` [T1·arxiv-cs-cy·optimistic] 경로별 효과 기반 평가는 결과 수준의 측도로 가려진 공정성 문제를 드러낼 수 있다
- `1A06B9CCAF2846EC1FD79509DDD` [T1·arxiv-cs-hc·conditional] 신뢰 성향 평가의 해석은 상호작용의 맥락을 고려하여 반성적으로 이루어져야 한다
- `1A0A6FFF1B5F31CC26A3AEFB4EE` [T1·arxiv-cs-hc·cautious] 자기 보고식 평가와 객관적 성과 측정 사이의 직접 상관관계는 매우 낮다
- `1A06A1F03A07A0D006776A867C7` [T3·manual·cautious] 성과 평가에서 개별 평가자의 평가 편향이 분산의 62%를 설명하는 반면 실제 성과는 21%만 설명한다

---

## 피드백 면담

*10/16 후보 — 평가 코멘트·면담을 행동의 언어로*

- 질의 변형: 피드백 면담 / 관리자의 성과 피드백 대화 / 코칭 대화 / AI가 작성한 피드백 코멘트 / 1 on 1 면담 / 평가 코멘트의 구체성
- 군집에 들어간 claim 67건 → 묶음 8개 → **자격 통과 2개**

### 후보

| # | 주제 | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 | 최근 2주 신호 |
|---|---|---|---|---|---|---|
| 1 | AI가 좋은 질문을 던지는 것과 그 질문이 상대의 사고를 실제로 바꾸는 것은 서로 다른 일이다 | claim 5건 · 출처 4곳 · stance cautious 2 / conditional 1 / optimistic 2 · T1·T2 4건 | 직무요구-자원 모형(0.54) · 컴퓨터화 취약성 추정(0.52) · 선발 방법의 예측타당도와 유용성(0.51) | 면담에서 AI가 대신하지 못하는 것은 질문이 아니라 반응이다 (재료 5건·출처 4곳으로 자격선에 겨우 걸쳐 있음) | **미개척** (평가·공정성 0편) | 있음 (claim 66건·문서 58건) |
| 2 | AI가 피드백 초안을 써 주는 만큼, 관리자가 무엇을 책임지는지가 그 면담의 신뢰를 가른다 | claim 9건 · 출처 5곳 · stance cautious 1 / conditional 3 / neutral 2 / optimistic 3 · T1·T2 2건 | 갤럽 Q12와 위대한 관리자의 네 열쇠(0.62) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.61) · 관리와 리더십의 구분(0.61) | 초안은 도구가 쓰고 판단과 책임은 사람이 진다 — 이 선이 그어져야 피드백이 대화로 남는다 (T5 claim 3건이 한 문서에서 나왔고 T1·T2는 기준선인 2건뿐 — 증거 수집에서 되튕길 위험 큼) | **미개척** (팀·리더십 0편) | 있음 (claim 45건·문서 36건) |

### 자격 미달 묶음과 보강안

| # | 재료 | 대표 claim 한 줄 | 미달 항목 | 백필하면 채워질 재료 |
|---|---|---|---|---|
| 3 | claim 14건 · 출처 2곳 · T1·T2 14건 | 교육자 개입 인터페이스를 포함한 맞춤형 피드백 시스템은 교사와 학생 모두에게 권한을… | 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건) | 교육 맥락 arxiv 2곳에 낙관 일색(optimistic 10/14). 직장 성과면담 맥락과 신중론이 함께 필요 — hrdive·charter·josh-bersin의 AI 성과관리 도구 기사 |
| 4 | claim 10건 · 출처 3곳 · T1·T2 9건 | L2 작가들의 생성형 AI 활용 방식은 규범적 사용에서 대화형 사용에 이르는 스펙트… | 독립 출처 3곳 (기준 4곳) | 대화형 AI 일반론이라 면담 주제와 거리가 있다. 이 묶음을 살리기보다 아래 보강안으로 새 재료를 넣는 편이 낫다 |
| 5 | claim 6건 · 출처 2곳 · T1·T2 6건 | 피드백 장벽 해결을 위한 설계 원칙에 부합하는 스캐폴드를 적용한 시스템에서 사용자가… | 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건) | 피드백 설계 원칙이 HCI 실험실 맥락뿐. **이론 카드 추가가 결정적** — 피드백 개입 이론(Kluger & DeNisi 1996: 피드백 개입의 약 3분의 1이 성과를 되레 낮춘다)이 현재 카드 72장에 없다 |
| 6 | claim 9건 · 출처 6곳 · T1·T2 5건 | AI가 생성한 코드의 정확성과 신뢰성을 평가할 필요성이 증가하고 있다… | 상반 stance 없음 (optimistic 0건) | AI 산출물 검토·코드 리뷰 병목 쪽으로 쏠려 낙관 근거가 0건. AI 피드백 도구의 성공 사례(hrtech-series·google-rework)로 상반 stance를 채울 수 있다 |
| 7 | claim 5건 · 출처 1곳 · T1·T2 5건 | 학생들은 AI 피드백을 루브릭 정렬과 표면적 편집에 활용하는 반면, 동료 피드백은 … | 독립 출처 1곳 (기준 4곳) / 상반 stance 없음 (optimistic·cautious 0건) | 교사의 AI 피드백 수용 행태 — 단일 출처(arxiv-cs-cy). 관리자의 AI 코멘트 수용을 다룬 실무 자료가 필요하다(hrtech-series·hrdive) |
| 8 | claim 9건 · 출처 4곳 · T1·T2 0건 | 관리자는 주간 피드백 제공, 성과 칭찬, 협력적 팀 구축을 자신 있게 수행한다고 평… | T1·T2 claim 0건 (기준 2건) — T5 단독 근거 금지(기획서 4.1) | 관리자 효과성 재료는 실무 출처 4곳으로 넓은데 T1·T2가 0건이다. academic-canon에 피드백·관리자 효과 메타분석을 등재하거나 위 Kluger & DeNisi 카드를 만들면 곧바로 자격선을 넘는다 |

### 묶음 상세

#### 묶음 1 — 자격 통과 (claim 5건)

- 출처 4곳: arxiv-cs-cy, arxiv-econ-gn, dbr, mckinsey-insights
- stance: cautious 2 / conditional 1 / optimistic 2 · T1·T2 4건 · 문서 5건
- 주제 축 평가·공정성 (유사도 0.621) · 발행 0편
- 이론 카드: 직무요구-자원 모형(0.54) · 컴퓨터화 취약성 추정(0.52) · 선발 방법의 예측타당도와 유용성(0.51) · 직무특성모형(0.51) · 조직 네트워크 분석(0.50)

대표 claim:

- `1A08D5E6FAA37CE7AA9F83E7727` [T1·arxiv-cs-cy·conditional] AI가 분석가의 업무를 보조할 수 있지만, 버튼 하나로 자동화하는 방식에 대해서는 주의가 필요하다
- `1A07DDD22BA745BC1F94E771478` [T1·arxiv-cs-cy·optimistic] AI가 생성한 반성 질문은 정답 풀이에 대해서는 더 깊은 개념 이해를, 부분 정답이나 오답에 대해서는 체계적 디버깅을 유도한다
- `1A06BEE0A3D96A4F0D86EF64F04` [T1·arxiv-econ-gn·cautious] AI가 기여자의 대안적 선택지를 증가시킴으로써 게시된 질문이 해결될 확률이 낮아진다
- `1A0611B63577F068A985377A9BE` [T2·mckinsey-insights·optimistic] AI가 개별 직원의 생산성을 향상시켰다고 보고하는 응답자가 다수이다
- `1A06A33447F0D790E7B5EC2587A` [T3·dbr·cautious] AI가 좋은 질문을 던진다고 해서 참가자의 논증이 자동으로 개선되지는 않으며, AI의 질문에 답하는 것과 그 답을 실제로 자신의 사고와 글에 반영하는 것은 서로 다른 과업이다

#### 묶음 2 — 자격 통과 (claim 9건)

- 출처 5곳: arxiv-cs-hc, hbr, hr-bulletin, hrtech-series, worklytics-blog
- stance: cautious 1 / conditional 3 / neutral 2 / optimistic 3 · T1·T2 2건 · 문서 6건
- 주제 축 팀·리더십 (유사도 0.709) · 발행 0편
- 이론 카드: 갤럽 Q12와 위대한 관리자의 네 열쇠(0.62) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.61) · 관리와 리더십의 구분(0.61) · 직무특성모형(0.60) · 70:20:10 프레임워크(0.60)

대표 claim:

- `1A0A2C964B18603E2EE133DB2D9` [T1·arxiv-cs-hc·optimistic] AI 피드백 중재자를 갖춘 회의 시스템에서 발화 시간이 더 균형 잡히게 분배되었다
- `1A06B373CC0462A54D2F529528D` [T1·arxiv-cs-hc·neutral] 안전-중요 미션의 드론 운영자들은 불확실성, 시간 압박, 책임 상황에서 자동화를 이해하고 신뢰하며 통제해야 한다
- `1A06140230F54A1F419BC13ACA6` [T3·hr-bulletin·neutral] 관리자와 직원 모두 빠른 응답과 피드백의 유용성을 높게 평가하지만, 이 두 항목에서 인식 차이가 존재한다
- `1A0614366916AAB5406F971734E` [T4·worklytics-blog·cautious] 원격 근무 환경에서 관리자의 가시성 감소는 직원 정렬 부족, 피드백 부재, 팀 생산성 저하로 이어진다
- `1A092670FE46FA424A3D0E70F1E` [T5·hrtech-series·conditional] AI 피드백 도구는 일관성을 개선하고 준비를 지원할 수 있지만, 강한 거버넌스, 공정한 테스트, 관리자 책임이 직원의 프로세스 신뢰도를 결정한다

#### 묶음 3 — 자격 미달 (claim 14건)

- 출처 2곳: arxiv-cs-cy, arxiv-cs-hc
- stance: conditional 2 / neutral 2 / optimistic 10 · T1·T2 14건 · 문서 8건
- 주제 축 학습·HRD (유사도 0.678) · 발행 0편
- 이론 카드: 인지평가이론(0.57) · 70:20:10 프레임워크(0.54) · 컴퓨터화 취약성 추정(0.53) · 목표설정이론(0.53) · 경험을 통한 리더 성장(0.53)
- 미달 사유: 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A08D629C0301A5BA763FD85FFA` [T1·arxiv-cs-cy·optimistic] 교육자 개입 인터페이스를 포함한 맞춤형 피드백 시스템은 교사와 학생 모두에게 권한을 부여하는 확장 가능하고 고품질의 피드백을 제공할 수 있다
- `1A0AC4D16A433272573463418B7` [T1·arxiv-cs-hc·optimistic] AI가 생성한 메타피드백은 학생들의 피드백 리터러시를 지원하고 동료평가에 대한 학습자 참여를 강화할 잠재력이 있다
- `1A0A2C64661E3F73E68480B70A8` [T1·arxiv-cs-hc·optimistic] AI 기반 멀티모달 피드백 시스템은 교육자 피드백과 동등한 학습 효과를 달성했다
- `1A0A2C647B7D101D3422D68ECC8` [T1·arxiv-cs-hc·optimistic] AI 멀티모달 피드백이 교육자 피드백보다 명확성, 구체성, 간결성, 동기부여, 만족도에서 유의미하게 우수했다
- `1A0A2C649BAA3413255EFAEBFCF` [T1·arxiv-cs-hc·neutral] AI 멀티모달 피드백 시스템은 구조화된 텍스트 설명, 동적 멀티미디어 자료, 스트리밍 음성 해설을 통합하여 실시간 피드백을 제공한다

#### 묶음 4 — 자격 미달 (claim 10건)

- 출처 3곳: aitimes, arxiv-cs-cy, arxiv-cs-hc
- stance: cautious 2 / conditional 2 / neutral 3 / optimistic 3 · T1·T2 9건 · 문서 10건
- 주제 축 학습·HRD (유사도 0.586) · 발행 0편
- 이론 카드: 인지평가이론(0.54) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 직무요구-자원 모형(0.51) · 흡수역량(0.49) · 경험학습 사이클(0.49)
- 미달 사유: 독립 출처 3곳 (기준 4곳)

대표 claim:

- `1A092890DF2DCDF2D79566D9FEB` [T1·arxiv-cs-cy·neutral] L2 작가들의 생성형 AI 활용 방식은 규범적 사용에서 대화형 사용에 이르는 스펙트럼을 보인다
- `1A0B1638331A41BC0E950406C4D` [T1·arxiv-cs-hc·optimistic] 대규모 언어모델을 개입의 유형(예: 사실 정정, 개념 정의)으로 분류된 다중 턴 대화 데이터셋으로 학습하면, 모델이 도움이 되는 시점에만 발언하고 필요 없을 때는 침묵하는 능력을 습득할 수 있다
- `1A0AC47330620A2C74E87884FE3` [T1·arxiv-cs-hc·cautious] 대규모 언어 모델과 대화형 AI 시스템은 사용자의 주장을 과도하게 또는 무비판적으로 검증·증폭·동조하는 경향이 있다
- `1A0AC3C2BC3A54F9D816B5CBF73` [T1·arxiv-cs-hc·conditional] 고령자를 지원하는 대화형 AI 시스템의 설계에는 사용성과 신뢰성뿐만 아니라 대화 중단 처리의 견고성이 필수적이다
- `1A07DD72BCBA0828ED89ACE99B8` [T1·arxiv-cs-cy·cautious] 대규모 언어모델과의 공존에서는 문의의 변환, 대화적 검증의 필요성 증가, 행위성의 재분배라는 세 가지 도전이 발생한다

#### 묶음 5 — 자격 미달 (claim 6건)

- 출처 2곳: arxiv-cs-cy, arxiv-cs-hc
- stance: conditional 2 / neutral 2 / optimistic 2 · T1·T2 6건 · 문서 6건
- 주제 축 평가·공정성 (유사도 0.649) · 발행 0편
- 이론 카드: 인지평가이론(0.59) · 자기결정이론(0.54) · 목표설정이론(0.53) · 적응적 리더십(0.53) · 동기-위생 이론(0.53)
- 미달 사유: 독립 출처 2곳 (기준 4곳) / 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A09CD41B36C4F73D9FFA960595` [T1·arxiv-cs-hc·optimistic] 피드백 장벽 해결을 위한 설계 원칙에 부합하는 스캐폴드를 적용한 시스템에서 사용자가 더 높은 품질의 피드백을 제공할 수 있다
- `1A09CC3D737E0172B8681C8E135` [T1·arxiv-cs-hc·neutral] 사용자는 시스템이 신뢰할 수 있음을 입증한 이후에는 피드백의 상세함을 점진적으로 줄이는 적응형 접근을 선호한다
- `1A06B1A6E43DF3DE0D59A623284` [T1·arxiv-cs-cy·neutral] 수정된 피드백은 수정되지 않은 피드백보다 유의미하게 길이가 길다
- `1A06B834EA2F40758CACC24AADC` [T1·arxiv-cs-hc·conditional] 인지 부하 기반 피드백이 스트레스 기반 피드백보다 더 큰 성능 향상을 가져왔다
- `1A06AE82FD25FA16DA4A5C8CF2E` [T1·arxiv-cs-cy·optimistic] 피드백 기능이 있는 자세 교정 장치를 사용한 사용자는 피드백 없이 사용한 사용자에 비해 자세 각도가 유의미하게 개선되었다

#### 묶음 6 — 자격 미달 (claim 9건)

- 출처 6곳: ai-post, arxiv-cs-cy, arxiv-cs-hc, donga-economy, innofit-blog, worklytics-blog
- stance: cautious 6 / neutral 3 · T1·T2 5건 · 문서 9건
- 주제 축 팀·리더십 (유사도 0.598) · 발행 0편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.55) · 선발 방법의 예측타당도와 유용성(0.52) · 경험학습 사이클(0.51) · 공유 리더십(0.50) · 컴퓨터화 취약성 추정(0.49)
- 미달 사유: 상반 stance 없음 (optimistic 0건)

대표 claim:

- `1A097A0E7B0BBD39622C187F6D0` [T1·arxiv-cs-cy·neutral] AI가 생성한 코드의 정확성과 신뢰성을 평가할 필요성이 증가하고 있다
- `1A088495407D1CAE606F7B2B0F4` [T1·arxiv-cs-cy·neutral] AI가 생성한 설득력은 주제에 따라 변동한다
- `1A07DDD2436D0A630BD2BE9E7A5` [T1·arxiv-cs-cy·cautious] AI 생성 피드백의 정확성과 교실 실용성에 대한 우려가 제기되었다
- `1A06BAEF6D36D62C457A9B740A8` [T1·arxiv-cs-hc·cautious] AI가 중재하는 비디오 커뮤니케이션에서 지각된 신뢰도와 판단에 대한 확신이 감소한다
- `1A06B470DA2A9AE3B77CA3F9240` [T1·arxiv-cs-hc·cautious] AI가 생성한 코드의 편집 궤적 중 31%에서 AI 완성도가 제거된다

#### 묶음 7 — 자격 미달 (claim 5건)

- 출처 1곳: arxiv-cs-cy
- stance: conditional 2 / neutral 3 · T1·T2 5건 · 문서 4건
- 주제 축 학습·HRD (유사도 0.629) · 발행 0편
- 이론 카드: 인지평가이론(0.52) · 조직학습 — 단일고리/이중고리 학습(0.51) · 경쟁가치모형(0.51) · 학습하는 조직과 다섯 가지 규율(0.50) · 목표설정이론(0.50)
- 미달 사유: 독립 출처 1곳 (기준 4곳) / 상반 stance 없음 (optimistic·cautious 0건)

대표 claim:

- `1A07DD641267D4AFD5917A37EFC` [T1·arxiv-cs-cy·neutral] 학생들은 AI 피드백을 루브릭 정렬과 표면적 편집에 활용하는 반면, 동료 피드백은 개념 발전과 학문 분야 관련성을 위해 활용했다
- `1A06B1A6D37751090FA7B987AD7` [T1·arxiv-cs-cy·neutral] 교사들은 AI가 생성한 피드백의 약 80%를 수정 없이 그대로 수용한다
- `1A06B1A705CC1B7B8DBC562CCA6` [T1·arxiv-cs-cy·neutral] 교사가 AI 피드백을 수정할 때는 주로 정보 밀도가 높은 설명에서 더 간결하고 교정 중심의 형태로 단순화한다
- `1A06AF4F9063C4C3F4C0A767869` [T1·arxiv-cs-cy·conditional] 교사와 학생은 AI가 생성한 서술형 피드백을 강하게 수용하지만 수치 점수에는 회의적이다
- `1A0694688982C2CBE1157E17038` [T1·arxiv-cs-cy·conditional] AI 피드백은 빠르고 확장 가능한 즉각적 글쓰기 조언 제공 방식이지만, 그 자체만으로는 학생의 반성적 사고 심화로 이어지지 않는다

#### 묶음 8 — 자격 미달 (claim 9건)

- 출처 4곳: fastcompany-worklife, google-rework, hr-bulletin, worklytics-blog
- stance: cautious 2 / conditional 2 / neutral 1 / optimistic 4 · T1·T2 0건 · 문서 8건
- 주제 축 팀·리더십 (유사도 0.74) · 발행 0편
- 이론 카드: 관리와 리더십의 구분(0.68) · 공유 리더십(0.65) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.63) · 직무특성모형(0.63) · 적기 인재 조달(0.62)
- 미달 사유: T1·T2 claim 0건 (기준 2건) — T5 단독 근거 금지(기획서 4.1)

대표 claim:

- `1A06140251660A5C30DE79BA330` [T3·hr-bulletin·cautious] 관리자는 주간 피드백 제공, 성과 칭찬, 협력적 팀 구축을 자신 있게 수행한다고 평가하지만, 실제로 이에 동의하는 직원은 많지 않다
- `1A06140271D45855C28A28F80CD` [T3·hr-bulletin·optimistic] 관리자가 직원에게 자신의 행동과 영향력에 대해 직접 피드백을 요청할 때, 이를 바탕으로 변화를 실행하면 보다 빠르고 효과적으로 리더십 목표를 달성할 수 있다
- `1A0640C69265D0B10F98AD830FD` [T3·hr-bulletin·neutral] 2020년 이후 관리자의 업무 몰입도가 지속적으로 하락했다
- `1A0614B6E3933A3F10AC5BB7C4A` [T4·worklytics-blog·conditional] 관리자 행동(일관되지 않은 체크인, 경계 위반 등)이 팀 성과와 이직률에 영향을 미친다
- `1A06A26D391ABC3765C17B2ED82` [T4·google-rework·optimistic] 효과적인 관리자를 둔 팀이 그렇지 않은 팀보다 더 나은 성과를 거두고, 구성원 만족도가 높으며, 이직률이 낮다

---

## 평가 공정성·성과 격차

*10/23 후보 — 도구 격차 시대의 공정한 평가*

- 질의 변형: 평가 공정성 / 성과 격차 확대 / AI 활용 능력 차이 / 조직 내 도구 접근 불평등 / 숙련도에 따른 AI 효과 차이 / 공정한 보상 배분
- 군집에 들어간 claim 113건 → 묶음 7개 → **자격 통과 5개**

### 후보

| # | 주제 | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 | 최근 2주 신호 |
|---|---|---|---|---|---|---|
| 1 | AI의 효과가 사람마다 다르게 나타나면서 기존 성과 분포 자체가 흔들린다 — 숙련도가 낮은 쪽의 개선 폭이 크다는 결과와, 경험 많은 쪽에는 효과가 미미했다는 결과가 같은 창에 있다 | claim 62건 · 출처 14곳 · stance cautious 19 / conditional 9 / neutral 24 / optimistic 10 · T1·T2 53건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.67) · 컴퓨터화 취약성 추정(0.56) · 경험학습 사이클(0.55) | 격차의 방향이 한쪽이 아니다 — 하위가 따라붙는 업무와 상위가 더 벌리는 업무가 갈리므로, 평가 대상이 '사람'이 아니라 '업무 종류'부터 나뉘어야 한다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 557건·문서 306건) |
| 2 | AI에 접근하고 활용하는 조건이 사람마다 달라서, 능력 차이 위에 도구 차이가 덧씌워진다 | claim 13건 · 출처 5곳 · stance cautious 6 / conditional 4 / neutral 2 / optimistic 1 · T1·T2 11건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.62) · 팀 효과성 모형(0.60) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.60) | 같은 잣대를 대기 전에 같은 조건이었는지를 먼저 확인해야 한다 — 조직공정성의 절차 공정성이 걸리는 지점 | **미개척** (조직설계·변화 0편) | 있음 (claim 331건·문서 218건) |
| 3 | 생성형 AI의 성능이 업무 종류에 따라 크게 출렁이고, 그 편차를 모른 채 위임하면 인지적 오프로딩이 자율성 포기로 굳는다 | claim 11건 · 출처 4곳 · stance cautious 4 / neutral 5 / optimistic 2 · T1·T2 10건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.63) · 컴퓨터화 취약성 추정(0.53) · 공유 리더십(0.50) | 성능이 고르지 않은 도구를 고르게 평가하면 운이 성과로 기록된다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 185건·문서 144건) |
| 4 | AI 도구를 평가에 끌어들이는 순간 개인 맞춤과 동일 잣대가 정면으로 부딪친다 — 같은 사람도 직장에서는 개인 용도보다 훨씬 엄격한 정확도를 요구한다 | claim 9건 · 출처 4곳 · stance cautious 3 / conditional 1 / neutral 3 / optimistic 2 · T1·T2 7건 | 선발 방법의 예측타당도와 유용성(0.60) · HRM-성과 연계와 블랙박스(0.59) · 갤럽 Q12와 위대한 관리자의 네 열쇠(0.55) | 공정성은 같은 잣대가 아니라 같은 검증 절차에서 나온다 — 선발 타당도 연구가 쌓아 온 '무엇을 재는지 먼저 정한다'는 원칙을 평가 코멘트에 옮기는 각도 | **미개척** (평가·공정성 0편) | 있음 (claim 88건·문서 71건) |
| 5 | 도구를 깔아 놓는 것만으로는 격차가 줄지 않고, 역할 재설계를 함께한 조직에서만 앞서 나가는 결과가 나온다 | claim 5건 · 출처 5곳 · stance cautious 1 / neutral 2 / optimistic 2 · T1·T2 4건 | 컴퓨터화 취약성 추정(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 적기 인재 조달(0.53) | 격차는 도구 배포 속도가 아니라 역할을 다시 짠 범위에서 갈린다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 112건·문서 82건) |

### 자격 미달 묶음과 보강안

| # | 재료 | 대표 claim 한 줄 | 미달 항목 | 백필하면 채워질 재료 |
|---|---|---|---|---|
| 6 | claim 6건 · 출처 4곳 · T1·T2 5건 | 자원이 부족하거나 소진 상태인 구성원은 크래프팅을 시도할 여력이 없어 격차가 확대된… | 상반 stance 없음 (optimistic 0건) | 잡 크래프팅 연결이 이번 탐색 전체에서 가장 강한데(0.73) 낙관 근거가 0건이다. 자원이 적은 쪽에도 AI가 크래프팅 여지를 넓혔다는 사례 — mckinsey-insights·bcg-publications의 접근 확대 성과 리포트 |
| 7 | claim 7건 · 출처 6곳 · T1·T2 1건 | AI 기반 프로그래밍 방식 도입 시 생산성 향상 효과가 보고되었다… | T1·T2 claim 1건 (기준 2건) — T5 단독 근거 금지(기획서 4.1) | 10/23에 가장 정확히 맞는 묶음(같은 직무 두 사람의 생산성 격차, 불균등 확산이 만드는 조직 내 마찰)인데 T1·T2가 1건뿐이다. NBER·arxiv-econ-gn의 AI 확산 불평등 논문을 수집 창에 넣거나, BCG·McKinsey 격차 리포트를 건별로 올리면 채워진다 |

### 묶음 상세

#### 묶음 1 — 자격 통과 (claim 62건)

- 출처 14곳: academic-canon, ai-lab-enterprise-reports, aihr-blog, aitimes, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, fastcompany-worklife, hankyung-it, mckinsey-insights, nber-working-papers, psyarxiv, the-ai, worklytics-blog
- stance: cautious 19 / conditional 9 / neutral 24 / optimistic 10 · T1·T2 53건 · 문서 55건
- 주제 축 일의 미래·AX (유사도 0.704) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.67) · 컴퓨터화 취약성 추정(0.56) · 경험학습 사이클(0.55) · 탤런트십과 의사결정 과학(0.54) · 감성지능과 리더십 — EI 역량(0.54)

대표 claim:

- `1A06A393AE46F12BF426AC0352E` [T1·nber-working-papers·cautious] 경험이 많거나 기술 수준이 높은 근로자에게는 AI 지원의 생산성 향상 효과가 미미했다
- `1A06A3BB0386AAB3F7433871818` [T1·academic-canon·optimistic] AI 도입이 AI 능력 범위 내의 업무에서 지식근로자의 완료율을 12% 이상 향상시킨다
- `1A0978BFC7861B509743AE4EA3E` [T1·arxiv-cs-cy·optimistic] 평가자 사전 선별, 피드백 일관성의 체계적 감시, 신뢰성 가중 강화 집계를 시행하면 AI 정렬 파이프라인의 공정성, 투명성, 견고성이 향상된다
- `1A0928F48A7FD3B519E1052E1BF` [T1·arxiv-cs-cy·neutral] 기업 규모가 클수록 CSRD(기업 지속가능성 보고 지침)가 그린 AI 관행에 더 큰 영향을 미친다
- `1A09285B918DA7CAAA3D8B422E6` [T1·arxiv-cs-cy·cautious] AI 능력 평가는 첫 번째 순서 효과(시스템 산출물의 정확성, 독성이나 편향 여부)는 포착할 수 있지만, AI의 두 번째 순서 효과(장기적 결과와 실제 사용으로부터의 결과)는 포착하지 못한다

#### 묶음 2 — 자격 통과 (claim 13건)

- 출처 5곳: aihr-blog, arxiv-cs-cy, arxiv-cs-hc, flex-blog, josh-bersin
- stance: cautious 6 / conditional 4 / neutral 2 / optimistic 1 · T1·T2 11건 · 문서 13건
- 주제 축 조직설계·변화 (유사도 0.72) · 발행 0편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.62) · 팀 효과성 모형(0.60) · RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.60) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.59) · 컴퓨터화 취약성 추정(0.58)

대표 claim:

- `1A08D5DCC3EDCD6D2CFC34C12DA` [T1·arxiv-cs-cy·cautious] AI는 인지 능력이 낮은 사람들을 참여도 최적화된 인터페이스를 통해 수동적으로 만든다
- `1A08845F6DA8472BB7DD7234F88` [T1·arxiv-cs-cy·cautious] AI는 인지 편향 악용, 자동화된 허위정보 등의 알고리즘 조작 메커니즘을 통해 영향력을 행사한다
- `1A0882EDDE6AE90C005188A034B` [T1·arxiv-cs-cy·cautious] AI 기술 혁신에 대한 공평한 접근성을 보장하기 어렵다
- `1A0612C1E8AD7C12823CDAEF90D` [T2·josh-bersin·conditional] AI를 효과적으로 활용하기 위한 핵심 역량은 복잡한 문제 해결 능력과 호기심이다
- `1A082FB4D1F001FE6DB9FC97012` [T1·arxiv-cs-cy·conditional] AI의 긍정적 결과는 자동으로 나타나지 않으며, 혁신 촉진 전략과 안전 거버넌스를 결합해야 한다

#### 묶음 3 — 자격 통과 (claim 11건)

- 출처 4곳: arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, the-ai
- stance: cautious 4 / neutral 5 / optimistic 2 · T1·T2 10건 · 문서 11건
- 주제 축 일의 미래·AX (유사도 0.649) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.63) · 컴퓨터화 취약성 추정(0.53) · 공유 리더십(0.50) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.50) · 제도이론(0.48)

대표 claim:

- `1A09798456FC56E39AEC128A45B` [T1·arxiv-cs-cy·cautious] 생성형 AI 거버넌스는 프로세스 위험보다 결과 위험을 우선시해야 한다
- `1A078AD2AC1A174073AE1445146` [T1·arxiv-cs-cy·neutral] 생성형 AI의 확산이 고용과 작업 구성에 변화를 가져오고 있다
- `1A0A2DA0B6BC291CAA06988A6CE` [T1·arxiv-cs-hc·cautious] 대조적 AI는 심리적 안전감 감소 없이 창의적 성과 향상을 가져오지 못했다
- `1A073835A201CD8C1E617D72346` [T1·arxiv-econ-gn·neutral] 생성형 AI의 성능은 작업 유형에 따라 편차가 크다
- `1A06E59FD418A810A1AA9E55413` [T1·arxiv-cs-cy·neutral] 구조화된 AI 지원(설명 게이트 포함)과 제약 없는 AI 지원은 즉시적 기능적 효율성에서 차이가 없다

#### 묶음 4 — 자격 통과 (claim 9건)

- 출처 4곳: arxiv-cs-cy, arxiv-cs-hc, carrot-global-blog, ms-worklab
- stance: cautious 3 / conditional 1 / neutral 3 / optimistic 2 · T1·T2 7건 · 문서 8건
- 주제 축 평가·공정성 (유사도 0.672) · 발행 0편
- 이론 카드: 선발 방법의 예측타당도와 유용성(0.60) · HRM-성과 연계와 블랙박스(0.59) · 갤럽 Q12와 위대한 관리자의 네 열쇠(0.55) · 목표관리(0.55) · 컴퓨터화 취약성 추정(0.53)

대표 claim:

- `1A097A7E68C33BD2349EFC2CFA0` [T1·arxiv-cs-cy·optimistic] AI 도구에 대한 숙련도와 피드백 기반 개선에 대한 개방성 사이에 중간 정도의 긍정적 상관관계가 있다
- `1A08D5DCCF21B01F3AB9F76EEB7` [T1·arxiv-cs-cy·cautious] AI 도입으로 인해 정보 접근성이 커먼즈에서 동의 제조와 자율성 억압의 도구로 변환된다
- `1A0B17467DF9082EB731737BC0E` [T1·arxiv-cs-hc·cautious] AI 도구가 협업에 미치는 영향에 대한 증거는 상대적으로 제한적이다
- `1A06E64B9EFBB41640384272883` [T1·arxiv-cs-cy·neutral] AI 도구 사용량이 많고 경험이 풍부한 사용자일수록 직장 환경에서 더 엄격한 정확도 기준을 적용한다
- `1A06E64B941BE6E89F86D02C324` [T1·arxiv-cs-cy·neutral] AI 도구의 정확도 요구도 차이(직장 vs. 개인)는 상위 2개 선택지 기준으로 측정해도 유지된다

#### 묶음 5 — 자격 통과 (claim 5건)

- 출처 5곳: arxiv-cs-cy, bain-insights, hbr, mckinsey-insights, nber-working-papers
- stance: cautious 1 / neutral 2 / optimistic 2 · T1·T2 4건 · 문서 5건
- 주제 축 일의 미래·AX (유사도 0.661) · 발행 1편
- 이론 카드: 컴퓨터화 취약성 추정(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.53) · 적기 인재 조달(0.53) · 변혁적·거래적 리더십(0.53) · 팀 효과성 모형(0.52)

대표 claim:

- `1A06A39435F0E4542059462CFA3` [T1·nber-working-papers·optimistic] 낮은 숙련도 근로자가 높은 숙련도 근로자보다 AI 도입으로 인한 생산성 향상 폭이 더 크다
- `1A0830B28F219C67F9BB9651FDA` [T1·arxiv-cs-cy·cautious] AI 기반 피드백 도구의 초기 도입률이 낮았다
- `1A059B63A99E20E1B30763B769C` [T2·bain-insights·neutral] AI 도입 선도 조직들이 중앙화된 AI 로드맵과 경영진 스폰서십 체계를 갖춘 가능성이 후발 조직보다 1.8배 높다
- `1A0640B803A3C4FB8B3DCA22AEA` [T2·mckinsey-insights·optimistic] 역할 재설계를 함께 진행한 조직이 AI 도입만 한 조직보다 상위 가속화 조직이 될 확률이 높다
- `1A083DC60D3F438B1518C871E01` [T3·hbr·neutral] 중간 관리자의 AI 도입 태도가 조직의 AI 도입 성패에 중대한 영향을 미친다

#### 묶음 6 — 자격 미달 (claim 6건)

- 출처 4곳: arxiv-cs-cy, arxiv-cs-hc, hbr, theory-canon
- stance: cautious 3 / conditional 2 / neutral 1 · T1·T2 5건 · 문서 5건
- 주제 축 동기·직무설계 (유사도 0.777) · 발행 0편
- 이론 카드: 잡 크래프팅(0.73) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.64) · 동적역량(0.63) · 직무요구-자원 모형(0.62) · 조직공정성 이론(0.61)
- 미달 사유: 상반 stance 없음 (optimistic 0건)

대표 claim:

- `1A0607DA6BBA2B8E6D04EDF39ED` [T1·theory-canon·conditional] 자원이 부족하거나 소진 상태인 구성원은 크래프팅을 시도할 여력이 없어 격차가 확대된다
- `1A09282EC0C5C1269748F098ED5` [T1·arxiv-cs-cy·cautious] 공공부문 기술 시스템은 편향되고 불균등한 결과를 초래할 위험이 있다
- `1A08301A9B7F014F93723D98178` [T1·arxiv-cs-cy·neutral] 공공 자금 지원 신청 평가 과정에서 제한된 인력이 병목 현상을 초래하고 있다
- `1A06BA1931C7FB68B54FFD54D97` [T1·arxiv-cs-hc·cautious] 공공부문에서 우선순위 배분 방식을 채택할 때, 자원이 점점 부족해질수록 교차적 정체성을 가진 집단 간에 상당한 상대적 불균형이 발생한다
- `1A06BA1942866CD7F1FFF779E36` [T1·arxiv-cs-hc·cautious] 자원 배분 우선순위화가 효율적인 배치 결과를 낳을 수 있다는 주장이 있지만, 실제로는 영향받는 개인들의 불평등 인식을 심화시킬 수 있다

#### 묶음 7 — 자격 미달 (claim 7건)

- 출처 6곳: ai-lab-enterprise-reports, aitimes, arxiv-cs-hc, donga-economy, hrtech-series, worklytics-blog
- stance: cautious 2 / neutral 1 / optimistic 4 · T1·T2 1건 · 문서 7건
- 주제 축 일의 미래·AX (유사도 0.775) · 발행 1편
- 이론 카드: 컴퓨터화 취약성 추정(0.62) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.61) · 팀 효과성 모형(0.61) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 직무특성모형(0.58)
- 미달 사유: T1·T2 claim 1건 (기준 2건) — T5 단독 근거 금지(기획서 4.1)

대표 claim:

- `1A0AC3A15A201FDEC6A7B2D25C7` [T1·arxiv-cs-hc·optimistic] AI 기반 프로그래밍 방식 도입 시 생산성 향상 효과가 보고되었다
- `1A061387B8045B8544DC45A4B94` [T4·worklytics-blog·neutral] 같은 직무를 수행하는 두 직원의 생산성 격차는 AI 활용 능력 여부에 따라 커진다
- `1A061441064D44DC4307127B532` [T4·worklytics-blog·cautious] AI 도입으로 인한 생산성 향상이 조직 내에서 불균등하게 나타나면, 단순히 이점의 편차만 생기는 것이 아니라 조직 전체에 긴장과 마찰을 초래한다
- `1A06A2EF037BCE6AF9FFB614FFD` [T4·ai-lab-enterprise-reports·optimistic] AI 모델의 성능이 향상될수록 더 긴 문맥을 유지하고 여러 단계의 추론, 도구 활용, 상황 대응 등 더욱 복잡한 업무를 수행할 수 있다
- `1A06A604A20D34966813565A864` [T5·hrtech-series·optimistic] AI 기술을 요구하는 채용공고는 같은 직종의 다른 공고보다 중위 급여가 더 높다

---

## 내년 목표·리스킬링 계획

*10/30 후보 — AI 역량을 내년 목표에 넣는 법*

- 질의 변형: 내년 목표 수립 / 리스킬링 계획 / AI 역량 개발 목표 / 직무 재설계와 역량 전환 / 교육 투자와 학습 시간 / 목표 설정과 동기
- 군집에 들어간 claim 84건 → 묶음 8개 → **자격 통과 5개**

### 후보

| # | 주제 | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 | 최근 2주 신호 |
|---|---|---|---|---|---|---|
| 1 | AI를 쓰는 역량의 내용이 도구 조작에서 검증과 판단 쪽으로 옮겨 가고 있다 — 역량이 올라갈수록 산출물 검증은 오히려 어려워진다 | claim 24건 · 출처 11곳 · stance cautious 6 / conditional 5 / neutral 8 / optimistic 5 · T1·T2 16건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.69) · 컴퓨터화 취약성 추정(0.58) · 감성지능과 리더십 — EI 역량(0.56) | 내년 목표에 적을 것은 도구 이름이 아니라 검증 능력이다 | 기발행 (일의 미래·AX 1편) | 있음 (claim 530건·문서 298건) |
| 2 | AI가 학습을 돕는지 대신하는지는 개입 시점에서 갈린다 — 너무 이르거나 잦은 개입은 학습을 방해한다 | claim 13건 · 출처 7곳 · stance cautious 5 / conditional 2 / neutral 2 / optimistic 4 · T1·T2 8건 | 학습전이 이론(0.64) · 조직학습 — 단일고리/이중고리 학습(0.60) · 흡수역량(0.58) | 리스킬링 계획에 'AI를 언제 끄는가'가 들어가야 한다 — 학습전이 이론이 말하는 전이 조건을 AI 사용 설계로 옮기는 각도 (재료 다수가 교육 맥락이라 사내 학습 적용 시 외적 타당도 확인 필요) | **미개척** (학습·HRD 0편) | 있음 (claim 141건·문서 107건) |
| 3 | AI 투자를 장비 구매로 잡느냐 역량 개발로 잡느냐에 따라 내년 계획서의 항목 자체가 달라진다 | claim 9건 · 출처 7곳 · stance cautious 3 / conditional 1 / neutral 2 / optimistic 3 · T1·T2 7건 | 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.66) · 컴퓨터화 취약성 추정(0.57) · 동적역량(0.53) | 예산 줄이 바뀌면 목표 줄도 바뀐다 — 흡수역량이 없는 조직에서 도구만 늘리면 회수가 안 되는 경로 | 기발행 (일의 미래·AX 1편) | 있음 (claim 447건·문서 253건) |
| 4 | AI 역량이 올라갈수록 한 사람이 감당할 수 있는 작업의 범위가 넓어지고, 그만큼 목표의 난이도와 범위를 다시 잡아야 한다 | claim 8건 · 출처 4곳 · stance cautious 3 / conditional 1 / neutral 2 / optimistic 2 · T1·T2 7건 | 목표설정이론(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 팀 효과성 모형(0.59) | 같은 목표를 더 빨리 끝내는 것은 성장이 아니다 — 목표설정이론의 '구체적이고 도전적인 목표' 조건을 AI 사용 전제 위에서 다시 계산하는 각도 | **미개척** (평가·공정성 0편) | 있음 (claim 181건·문서 131건) |
| 5 | AI로 결과물 수준을 쉽게 올릴 수 있게 된 만큼, 개인이 역량을 쌓아 올리던 경로가 끊길 수 있다 | claim 7건 · 출처 4곳 · stance cautious 3 / conditional 1 / neutral 1 / optimistic 2 · T1·T2 5건 | RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.62) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.57) · 고성과작업시스템(0.56) | 결과물이 좋아지는 속도와 사람이 자라는 속도가 갈라지는 해 — 내년 목표는 둘을 따로 적어야 한다 | **미개척** (조직설계·변화 0편) | 있음 (claim 263건·문서 184건) |

### 자격 미달 묶음과 보강안

| # | 재료 | 대표 claim 한 줄 | 미달 항목 | 백필하면 채워질 재료 |
|---|---|---|---|---|
| 6 | claim 9건 · 출처 4곳 · T1·T2 6건 | MBO가 효과를 내는 정도는 목표설정이론(구체적·도전적 목표), 참여적 관리, 객관… | 상반 stance 없음 (cautious 0건) | 이론 연결은 이번 탐색 전체 최고치다(목표설정이론 0.88·MBO/OKR 0.86). 다만 claim 9건 중 5건이 이론 카드 자체이고 신중론이 0건이다. 목표-보상 연동의 부작용(목표 하향 협상·지표 게이밍)을 다룬 실무 기사 — DBR·HBR Korea의 OKR 운영 실패 사례 건별 수집 |
| 7 | claim 6건 · 출처 1곳 · T1·T2 6건 | 교육 기관이 명확한 AI 사용 정책과 AI 리터러시 교육 과정을 수립할 경우, AI… | 독립 출처 1곳 (기준 4곳) / 상반 stance 없음 (cautious 0건) | AI 리터러시 교육 설계가 단일 출처(arxiv-cs-cy). josh-bersin·hrdive·deloitte-insights의 사내 AI 교육 자료로 출처를 넓힐 수 있다 |
| 8 | claim 8건 · 출처 1곳 · T1·T2 0건 | 스킬 그래프 기술은 기존 HR 시스템의 부분적 직원 이해를 넘어 역량, 경험, 프로… | 독립 출처 1곳 (기준 4곳) / T1·T2 claim 0건 (기준 2건) — T5 단독 근거 금지(기획서 4.1) | 스킬 그래프 8건이 hrtech-series 한 문서에서 나왔고 T1·T2가 0건이다. 스킬 기반 인재관리는 10/30과 맞닿지만 지금은 벤더 서술 한 겹뿐 — deloitte-insights·josh-bersin 리포트, 스킬 기반 조직을 다룬 arxiv-econ-gn 논문이 필요 |

### 묶음 상세

#### 묶음 1 — 자격 통과 (claim 24건)

- 출처 11곳: aihr-blog, aitimes, arxiv-cs-cy, arxiv-cs-hc, donga-economy, hankyung-it, hrtech-series, josh-bersin, mckinsey-insights, psyarxiv, worklytics-blog
- stance: cautious 6 / conditional 5 / neutral 8 / optimistic 5 · T1·T2 16건 · 문서 23건
- 주제 축 일의 미래·AX (유사도 0.693) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.69) · 컴퓨터화 취약성 추정(0.58) · 감성지능과 리더십 — EI 역량(0.56) · 선발 방법의 예측타당도와 유용성(0.56) · 자동화의 대체·보완 이중효과와 폴라니의 역설(0.55)

대표 claim:

- `1A0928E5A4001AFECCC4DC7B7E6` [T1·arxiv-cs-cy·optimistic] 기업 아키텍처 관리(EAM)를 동적 역량(센싱, 시징, 변환)으로 개념화할 때 생성형 AI 도입을 촉진할 수 있다
- `1A0B16C0912880319686DB97430` [T1·arxiv-cs-hc·optimistic] AI의 성능 통찰력에 대한 정보를 제공하면 작업 성과가 향상된다
- `1A08845F6DA8472BB7DD7234F88` [T1·arxiv-cs-cy·cautious] AI는 인지 편향 악용, 자동화된 허위정보 등의 알고리즘 조작 메커니즘을 통해 영향력을 행사한다
- `1A0AC42AACEEE0DD8BCACBCBB10` [T1·arxiv-cs-hc·neutral] 개발자들은 핵심 업무(코딩, 테스팅)에서 생성형 AI의 현재 사용률이 높고 개선 요구도 크다
- `1A0612C1E8AD7C12823CDAEF90D` [T2·josh-bersin·conditional] AI를 효과적으로 활용하기 위한 핵심 역량은 복잡한 문제 해결 능력과 호기심이다

#### 묶음 2 — 자격 통과 (claim 13건)

- 출처 7곳: arxiv-cs-cy, arxiv-cs-hc, hbr, hrdive, josh-bersin, ms-worklab, the-ai
- stance: cautious 5 / conditional 2 / neutral 2 / optimistic 4 · T1·T2 8건 · 문서 13건
- 주제 축 학습·HRD (유사도 0.746) · 발행 0편
- 이론 카드: 학습전이 이론(0.64) · 조직학습 — 단일고리/이중고리 학습(0.60) · 흡수역량(0.58) · 컴퓨터화 취약성 추정(0.58) · 경험학습 사이클(0.57)

대표 claim:

- `1A0830ACD2C58C711454D44B253` [T1·arxiv-cs-cy·cautious] AI 교육 역량 부족의 주요 원인으로 AI 전문성을 갖춘 교수진의 부족과 재교육을 위한 제한된 시간이 있다
- `1A0830946BA09778DFAC4033CD3` [T1·arxiv-cs-cy·neutral] AI는 교육 실무에서 교수학습에 관한 오랫동안 유지되어온 가정들에 도전하면서 교육 실행 방식을 빠르게 재편하고 있다
- `1A0AC409ACFCB27FBA2D73C9A70` [T1·arxiv-cs-hc·optimistic] AI 도구를 활용한 프로그래밍 교육에서는 향상된 프로그래밍 지원이 주요 교육 목표이다
- `1A06B901074C231777DBB85FA1D` [T1·arxiv-cs-hc·conditional] AI 지원 시기를 적절히 설계하면 학생의 생산적 인지 노력을 감소시키지 않으면서 학습 과정을 지원할 수 있다
- `1A06131C563C5088D219267D424` [T2·josh-bersin·optimistic] AI로 생성된 교육 과정은 기존 방식에 비해 개발 시간이 대폭 단축된다

#### 묶음 3 — 자격 통과 (claim 9건)

- 출처 7곳: academic-canon, arxiv-cs-cy, arxiv-cs-hc, arxiv-econ-gn, hrtech-series, pwc-global-insights, the-ai
- stance: cautious 3 / conditional 1 / neutral 2 / optimistic 3 · T1·T2 7건 · 문서 9건
- 주제 축 일의 미래·AX (유사도 0.671) · 발행 1편
- 이론 카드: 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.66) · 컴퓨터화 취약성 추정(0.57) · 동적역량(0.53) · 감성지능과 리더십 — EI 역량(0.53) · 전략적 인적자원관리의 여섯 가지 이론적 관점(0.51)

대표 claim:

- `1A06A3BB0EC430C086E7EC75AFA` [T1·academic-canon·optimistic] AI 도입이 AI 능력 범위 내의 업무에서 응답 품질을 평균 32% 개선시킨다
- `1A0882C58F5410F3450DEBEE5F4` [T1·arxiv-cs-cy·optimistic] AI는 소매 업종에서 생산성을 향상시키는 역할을 한다
- `1A06A129FDE5C08FF945135D946` [T2·pwc-global-insights·optimistic] AI를 작년에 사용한 근로자 중 약 4분의 3은 AI가 생산성을 높이고 업무 품질을 향상시킨다고 보고했다
- `1A0A2DB5A5D8713ABD746BB8D71` [T1·arxiv-cs-hc·cautious] 제품 관리자들은 AI의 역량을 과대평가하는 경향이 있다
- `1A06B2254AAF32C7C82FA29D330` [T1·arxiv-cs-cy·conditional] 조직은 AI 투자를 기술 구매가 아닌 역량 개발로 재정의해야 한다

#### 묶음 4 — 자격 통과 (claim 8건)

- 출처 4곳: arxiv-cs-cy, arxiv-econ-gn, charter, knowledge-wharton
- stance: cautious 3 / conditional 1 / neutral 2 / optimistic 2 · T1·T2 7건 · 문서 8건
- 주제 축 평가·공정성 (유사도 0.732) · 발행 0편
- 이론 카드: 목표설정이론(0.60) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.59) · 팀 효과성 모형(0.59) · 선발 방법의 예측타당도와 유용성(0.58) · 강점 기반 리더십(0.57)

대표 claim:

- `1A073835C1E99FB51ECD8E1CD3C` [T1·arxiv-econ-gn·optimistic] AI 역량이 향상될수록 근로자가 채택하는 작업 방향의 범위는 확대된다
- `1A06B25E7AD833D6BCBBA594FE3` [T1·arxiv-cs-cy·neutral] AI 역량은 빠르게 발전하고 있지만 발전의 속도와 정도가 불균등하다
- `1A06AE6961D604BDD3FC6B596CC` [T1·arxiv-cs-cy·conditional] AI 시스템은 이미 주어진 목표를 최적화하는 것보다, 선택의 환상으로부터 보호하고 메타 역량을 배양하는지 여부로 평가되어야 한다
- `1A0694B3D055F8B04A355D67714` [T1·arxiv-cs-cy·cautious] AI는 예측 역량 향상을 약속하지만 실제로는 효율성과 합리화 목표에 복무한다
- `1A069448A229BF1BC7303328B30` [T1·arxiv-cs-cy·cautious] AI의 편향은 은폐적이며 정렬 목표의 특성으로 작동한다

#### 묶음 5 — 자격 통과 (claim 7건)

- 출처 4곳: arxiv-cs-cy, arxiv-cs-hc, dbr, the-ai
- stance: cautious 3 / conditional 1 / neutral 1 / optimistic 2 · T1·T2 5건 · 문서 7건
- 주제 축 조직설계·변화 (유사도 0.704) · 발행 0편
- 이론 카드: RBV의 HR 적용과 VRIO — 전략적 파트너로서의 HR(0.62) · 자동화의 과업 기반 프레임워크 — 대체효과와 복원효과(0.57) · 고성과작업시스템(0.56) · 탤런트십과 의사결정 과학(0.55) · 총보상 모델(0.55)

대표 claim:

- `1A08D5DCC3EDCD6D2CFC34C12DA` [T1·arxiv-cs-cy·cautious] AI는 인지 능력이 낮은 사람들을 참여도 최적화된 인터페이스를 통해 수동적으로 만든다
- `1A0B17469387A9ADDBAEDFB205A` [T1·arxiv-cs-hc·optimistic] AI는 개발자를 대체하기보다는 증강하는 역할을 한다
- `1A082FC43BC49016B7FAF0ADC00` [T1·arxiv-cs-cy·cautious] 직장에서의 지속적이고 공평한 AI 활용을 지원하기 위해서는 기술 수용 모형에 정서적·조직적 요인을 통합해야 한다
- `1A06B20890528DC5FE41922D4EB` [T1·arxiv-cs-cy·optimistic] AI는 애자일 방법론에서 작업 우선순위 설정을 최적화한다
- `1A09265AB8DDA302A83DB1E49B7` [T1·arxiv-cs-hc·neutral] AI 에이전트는 누적되는 도전에 따라 작업 중심 적응에서 작업 재구성, 타인에 대한 주의, 역할 경계 조정, 광범위한 조율로 확장된다

#### 묶음 6 — 자격 미달 (claim 9건)

- 출처 4곳: arxiv-cs-cy, google-rework, hr-bulletin, theory-canon
- stance: conditional 2 / neutral 5 / optimistic 2 · T1·T2 6건 · 문서 5건
- 주제 축 동기·직무설계 (유사도 0.782) · 발행 0편
- 이론 카드: 목표설정이론(0.88) · 목표관리(0.86) · 데니슨 조직문화 모델(0.63) · 팀 효과성 모형(0.63) · 사회기술시스템 이론(0.61)
- 미달 사유: 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A0607DC73F83EA96B548353127` [T1·theory-canon·neutral] MBO가 효과를 내는 정도는 목표설정이론(구체적·도전적 목표), 참여적 관리, 객관적 피드백 등 별도로 연구된 기제가 실제로 작동하는지에 달려 있다
- `1A0607DC83C72BAC7EE54C51696` [T1·theory-canon·conditional] 목표를 보상·평가에 강하게 연동하면(전형적 MBO) 목표 하향 협상, 지표 게이밍, 리스크 회피가 유발된다
- `1A0607D87741EAE35F247EB1333` [T1·theory-canon·neutral] 목표–성과 관계는 목표몰입, 피드백, 과업복잡성, 자원 가용성, 자기효능감에 의해 조절되는 것으로 제시된다
- `1A0607D87367AD89454DD951F37` [T1·theory-canon·neutral] 목표는 주의 집중, 노력 동원, 지속성 증가, 과업 관련 전략 탐색이라는 네 기제를 통해 성과에 작용한다
- `1A0607D87A6E2A28C120C77D8A4` [T1·theory-canon·neutral] 목표몰입은 목표의 중요성 지각과 달성 가능성(자기효능감)이 높을 때 강해진다

#### 묶음 7 — 자격 미달 (claim 6건)

- 출처 1곳: arxiv-cs-cy
- stance: conditional 2 / neutral 2 / optimistic 2 · T1·T2 6건 · 문서 6건
- 주제 축 학습·HRD (유사도 0.692) · 발행 0편
- 이론 카드: 70:20:10 프레임워크(0.59) · 학습전이 이론(0.57) · 조직학습 — 단일고리/이중고리 학습(0.56) · 경험학습 사이클(0.55) · 학습하는 조직과 다섯 가지 규율(0.55)
- 미달 사유: 독립 출처 1곳 (기준 4곳) / 상반 stance 없음 (cautious 0건)

대표 claim:

- `1A09293B36A5A25F865C275CA86` [T1·arxiv-cs-cy·conditional] 교육 기관이 명확한 AI 사용 정책과 AI 리터러시 교육 과정을 수립할 경우, AI의 즉시 피드백 및 개인맞춤형 학습 지원 등의 잠재력을 활용하면서 학습 과정의 무결성을 보존할 수 있다
- `1A0928CFF0D54BC53CB20A755D6` [T1·arxiv-cs-cy·optimistic] AI는 개인화된 학습과 확장 가능한 교육을 제공할 수 있다
- `1A08842C32E1B9B3C87C5ED6186` [T1·arxiv-cs-cy·optimistic] 교육자, 가족 참여 또는 AI 에이전트 활용이 협력학습의 참여 범위를 확대할 수 있다
- `1A08842D992DC211B9A8B524CBD` [T1·arxiv-cs-cy·neutral] AI 리터러시 연구에서는 학습자가 AI와 관련된 5가지 역량(인식, 지식, 적용, 평가, 개발)을 개발해야 한다고 제안한다
- `1A0830631082D8A2AC9D27572D3` [T1·arxiv-cs-cy·conditional] AI가 교육의 보조 역할을 할 때만 기본 학습 과정을 해치지 않으면서 교육의 가치 있는 자산이 될 수 있다

#### 묶음 8 — 자격 미달 (claim 8건)

- 출처 1곳: hrtech-series
- stance: cautious 1 / optimistic 7 · T1·T2 0건 · 문서 1건
- 주제 축 학습·HRD (유사도 0.674) · 발행 0편
- 이론 카드: 탤런트십과 의사결정 과학(0.57) · HR 다중역할 모델(0.56) · 경험을 통한 리더 성장(0.56) · 흡수역량(0.54) · 동기-위생 이론(0.53)
- 미달 사유: 독립 출처 1곳 (기준 4곳) / T1·T2 claim 0건 (기준 2건) — T5 단독 근거 금지(기획서 4.1)

대표 claim:

- `1A083E2DC4D43E35D152D76C431` [T5·hrtech-series·optimistic] 스킬 그래프 기술은 기존 HR 시스템의 부분적 직원 이해를 넘어 역량, 경험, 프로젝트, 역할, 비즈니스 필요를 연결한 통합적 관점을 제공한다
- `1A083E2DBF3137D9DE989F3C7B5` [T5·hrtech-series·optimistic] 스킬 그래프는 직원이 새로운 학습을 완료하거나, 새로운 프로젝트에 참여하거나, 역량을 직무 활동을 통해 입증할 때 그 프로필을 동적으로 업데이트할 수 있다
- `1A083E2DC1CA6844C8E4DB5F230` [T5·hrtech-series·optimistic] 스킬 그래프 기술을 통해 조직은 직책 기반의 매칭에서 벗어나 실제 역량 기반의 인재 발굴로 전환할 수 있다
- `1A083E2DC2EBA33AAF970095876` [T5·hrtech-series·optimistic] 스킬 추론 시스템은 직원이 명시적으로 기록하지 않은 숨겨진 역량(예: 복잡한 프로젝트 리드를 통한 프로젝트 관리 역량)을 발견할 수 있다
- `1A083E2DC3BC9214F00150B5DF0` [T5·hrtech-series·optimistic] 스킬 그래프는 정적 역량 인벤토리와 달리 직원의 새로운 교육 이수, 프로젝트 참여, 역할 변화 등에 따라 지속적으로 업데이트될 수 있다

---

## 종합 — 슬롯별 판정

| 슬롯 | 키워드 | 판정 | 자격 통과 | 최대 출처 | 최대 T1·T2 | 미개척 축 묶음 |
|---|---|---|---|---|---|---|
| 10/2 | AI 업무 성과 평가 | **충분** | 6/8묶음 | 21곳 | 48건 | 묶음 5·6 |
| 10/9 | 자기 평가·성과 서술 | **보강 필요** | 4/7묶음 | 14곳 | 28건 | 묶음 2 |
| 10/16 | 피드백 면담 | **보강 필요 — 다섯 슬롯 중 가장 약함** | 2/8묶음 | 5곳 | 4건 | 묶음 1·2 |
| 10/23 | 평가 공정성·성과 격차 | **충분** | 5/7묶음 | 14곳 | 53건 | 묶음 2·4 |
| 10/30 | 내년 목표·리스킬링 계획 | **충분** | 5/8묶음 | 11곳 | 16건 | 묶음 2·4·5 |

### 슬롯별 한 줄

- **10/2 AI 업무 성과 평가** — 충분. 창간호는 묶음 6(사용량과 보상의 어긋남, 평가·공정성 축 미개척)을 논지로 잡고 묶음 1·3의 지표·측정 재료로 받치는 구성이 가능하다. 다만 묶음 6은 증거 claim이 6건뿐이라 /draft ② 증거 수집에서 3건 이상 살아남는지 먼저 확인할 것.
- **10/9 자기 평가·성과 서술** — 보강 필요. 통과한 4묶음이 모두 'AI가 일을 어떻게 바꾸는가' 층위이고, 정작 자기평가·성과 서술 자체를 다룬 묶음 6·7은 출처 3곳에서 걸렸다. 묶음 3(검증 흔적)으로 지금도 쓸 수는 있다. 제대로 쓰려면 DBR·HBR Korea 평가 시즌 특집 2~3건 + 자기평가 타당도 이론 카드 1장.
- **10/16 피드백 면담** — 보강 필요 — 다섯 슬롯 중 가장 약함. 통과한 2묶음이 각각 claim 5건·9건이다. 묶음 2는 T5 3건이 한 문서에서 나왔고 T1·T2가 기준선인 2건이라 증거 수집에서 되튕길 공산이 크다. 나머지는 교육 맥락 arxiv에 낙관 편중. 피드백 개입 이론 카드 1장 + 직장 성과면담 실무 기사 3건 이상이 선행돼야 한다.
- **10/23 평가 공정성·성과 격차** — 충분. NBER과 academic-canon의 숙련도별 효과 차이가 T1으로 들어와 있다. 묶음 4(평가·공정성 축 미개척)를 논지로, 묶음 1의 방향이 갈리는 증거로 받치면 된다. 가장 정확히 맞는 묶음 7은 T1·T2 1건으로 미달이니 그 재료는 보조로만.
- **10/30 내년 목표·리스킬링 계획** — 충분. 묶음 2(학습·HRD 축 미개척, 출처 7곳)를 논지로 잡고 묶음 4의 목표 난이도 재설정 재료를 붙이는 구성이 가장 튼튼하다. 목표설정이론·MBO 카드 연결도 이번 탐색 최고치다.

## 이번 탐색에서 드러난 구조적 공백

1. **평가 제도 자체를 다룬 재료가 얇다.** 다섯 키워드 모두에서 자격을 통과한 큰 묶음은 대체로 'AI가 생산성에 미치는 영향' 층위였고, 자기평가·피드백 면담·평가자 편향처럼 제도의 속을 다루는 묶음은 출처 3곳 안팎에서 걸렸다. 지금 DB는 AI 쪽으로는 두껍고 인사 제도 쪽으로는 얇다.
2. **T1 재료가 교육 맥락에 쏠려 있다.** 피드백·자기평가·학습 묶음의 T1 claim 상당수가 학생·교사 대상 연구다. 사내 맥락으로 옮길 때 외적 타당도를 검증 단계에서 반드시 확인해야 하고, 옮기기 어려운 claim은 증거로 세지 말아야 한다.
3. **이론 카드 공백 3장.** 평가·공정성 축 카드가 4장뿐이다. 이번 탐색에서 가장 아쉬웠던 것은 피드백 개입 이론(Kluger & DeNisi 1996 — 피드백 개입의 약 3분의 1이 성과를 되레 낮춘다), 성과평가 100년(DeNisi & Murphy 2017), 자기평가 타당도(Mabe & West 메타분석)다. 세 장이면 10/9·10/16 두 슬롯의 이론 연결이 동시에 풀린다. (`/add-theory`로 초안을 만들고 사람 검수 후 reviewed — 절대 규칙 7)
4. **유료 건별 수집 대상이 명확하다.** DBR·HBR Korea는 10~12월이 평가 시즌 특집 시기다. `/browse-collect`로 5~8건만 올리면 10/9·10/16·10/23의 미달 묶음 대부분이 출처 기준을 넘는다.

## 다음 동작 제안

1. 10/2·10/23·10/30은 지금 재료로 `/draft` 착수 가능 — 위 후보 표에서 묶음을 고른다.
2. 10/9·10/16은 착수 전 백필: 이론 카드 3장(`/add-theory`) + DBR·HBR Korea 평가 시즌 기사 건별 수집(`/browse-collect`).
3. 백필 후 키워드 2·3만 같은 절차로 다시 돌려 자격 충족 여부를 확인한다.
