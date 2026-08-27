# Claim 스팟체크 기록 — 2026-08-25

절차: eval/claim_spotcheck.md · 목표 정확도 90%+
판정 기준(claim당 O/X): ①원문에 실재 ②자체 문장 재작성 ③metric 일치 ④stance/evidence_type 타당

"근거 위치"는 Claude가 원문 대조로 찾은 참고 정보(원문 파일의 행 번호). 최종 판정은 검수자가 원문을 직접 확인해 기재.

## 1. [T2/mckinsey-insights] Advancing American healthcare: An interview with Seema Verma
원문: `data\raw\mckinsey-insights\1A032DFE3AA079342F95E9C6BE8.txt`

claim 0건 — 대조 대상 없음 (피드 요약 176자만 저장된 문서, 추출 결과 없음이 정상)

## 2. [T3/hbr] 3 Warning Signs Your Supplier Is in Distress
원문: `data\raw\hbr\1A032E5E85BE3B06D7C434F2E16.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | 다국적 기업의 공급업체들이 관세, 물류 차질, 규정 준수 요구, 반복적인 글로벌 충격으로 인한 증가된 압력에 직면해 있다 | neutral | opinion |  | 2~3행 (tariffs, logistics… 열거) | O |  |
| 2 | 대규모 구매자들은 자신들에게 부과된 추가 비용의 일부를 공급업체에게 전가하는 경향이 있다 | cautious | data | many large buyers pass at least part of these additional costs | 3행 ("Recent studies suggest…") ※metric란에 수치가 아닌 원문 구절이 들어감 — 기준②·③ 판정 시 참고 | X | F3 |
| 3 | 특히 소규모 기업과 개발도상국 공급업체들은 비용 증가뿐만 아니라 동시에 품질, 납기, 감시, 규정 준수 기준을 유지해야 하는 이중 부담을 겪고 있다 | cautious | opinion |  | 3행 후반 ("especially smaller firms…" 이하) | O |  |

## 3. [T2/mckinsey-insights] Brilliant Moves: Coffee with Suzano CEO Beto Abreu
원문: `data\raw\mckinsey-insights\1A032E05EEE753B935F28B20F3D.txt`

claim 0건 — 대조 대상 없음 (피드 요약 153자만 저장)

## 4. [T5/hankyung-it] 에이프릴바이오, 에보뮨과 APB-R3 물질이전계약…후속 개발 준비
원문: `data\raw\hankyung-it\1A032E951F393FB5614CBF900F0.txt`

claim 0건 — 대조 대상 없음 (제약 계약 기사 — 파이프라인 주제와 무관해 추출 0건이 정상)

## 5. [T1/arxiv-cs-cy] Understanding as an Explicit and Assessable Component of Frontier AI Safety Decisions
원문: `data\raw\arxiv-cs-cy\1A032DE568EAABF85E7E7FF672D.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | 프론티어 AI 시스템의 훈련 또는 배포 결정을 내릴 때 의사결정자는 충분한 이해를 갖추어야 한다 | neutral | theory |  | 5행 초록 첫 문장 | O |  |
| 2 | 시간 압박 상황에서 AI가 생성한 산출물을 사용하면 안전 사례(safety case)와 시스템 카드의 존재만으로는 의사결정자의 충분한 이해를 보장할 수 없다 | cautious | opinion |  | 5행 둘째 문장 ("under time-pressure…") | O |  |
| 3 | 의사결정자의 이해를 명시적으로 기술하고 평가할 수 있는 방법론을 적용하면 AI 시스템 배포의 공학적 설계를 개선하도록 유도한다 | optimistic | experiment |  | 5행 마지막 문장 ("…drives the engineering") ※시나리오 2건 시험(trial) 기반 — experiment 분류 타당성 검토 | X | F4 |
| 4 | AI 코딩 에이전트의 배포 시나리오에서 제안된 방법론은 적용 가능하며 분석 도구로서 가치가 있음이 확인되었다 | optimistic | case |  | 5행 ("One scenario…AI coding agent" + "could be applied…generative") | O |  |

## 6. [T5/mk-economy] 매일 확인했다더니 833억 털릴때까지 몰랐다…기업은행 중국법인 금융사고
원문: `data\raw\mk-economy\1A032EB42E5A87999CF407BC4B1.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | IBK기업은행 중국법인이 협력업체의 횡령을 6개월 이상 적발하지 못했다 | cautious | case | 6개월 이상 | 3행(Key Points), 14행 ("6개월 넘게") | O |  |
| 2 | 은행이 매일 원리금 상환 내역을 확인했다고 주장했으나 실제로는 차주 민원 증가 후에야 사고를 인지했다 | cautious | case |  | 5행, 14행 (6월 24일 인지 경위) | O |  |
| 3 | 다른 중국 금융기관 5곳이 이미 문제 협력업체를 거래에서 제외했으나 기업은행은 이 신호를 제때 파악하지 못했다 | cautious | case | 5곳 | 7행, 14행, 26행 ※원문 내 제외 대상 표기가 A사(7행)/B사(14·26행)로 엇갈림 — 원문 자체 불일치, 판정 시 참고 | O |  |
| 4 | 금융권 전반에서 내부통제 시스템이 부실하여 횡령·배임 사고가 반복적으로 발생하고 있다 | cautious | case |  | 20행, 37~38행 (타 은행 사례 열거) | O |  |
| 5 | 금융기관의 감사 및 준법감시인의 독립성과 권한 강화가 금융사고 예방에 필수적이다 | conditional | opinion |  | 39행 마지막 문장 | O |  |
| 6 | 내부통제 시스템 강화를 위한 투자 확대가 단기적으로는 비용 증가를 야기하지만 장기적으로는 금융 시장 건전성을 높일 수 있다 | conditional | theory |  | 43~45행 (전망 시나리오) ※기자 전망 서술 — evidence 분류(theory vs opinion) 타당성 검토 | X | F4 |

## 7. [T2/mckinsey-insights] Joseph Tsai: Putting customers at the heart of innovation
원문: `data\raw\mckinsey-insights\1A032E06B35F6071C4F5110CFA5.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | 장기적 관점에서 고객 중심의 혁신을 추구하면 조직을 성공적으로 재편할 수 있다 | optimistic | case |  | 1행 (원문 전체가 1문장 요약) ※원문은 특정 은행 1개 사례 서술인데 claim은 일반 명제로 확장 — 과잉 일반화 여부 판정 필요 | O |  |

## 8. [T5/mk-economy] 올해 서울 공시가 20% '폭등'…부산은 1.28% 상승
원문: `data\raw\mk-economy\1A032EBCDC3A39EBD7DB006D441.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | 2026년 서울 아파트 공시가격 상승률이 전국 평균 상승률의 2배 이상이다 | neutral | data | 서울 약 20% vs 전국 평균 9.13% | 3행, 12행 ("두 배 이상" 명시) | O |  |
| 2 | 공시가격 15억원 이상 고가 아파트의 대다수가 서울에 집중되어 있다 | neutral | data | 전국 고가 아파트의 90% | 5행, 12행 | O |  |
| 3 | 서울 내 자치구별 공시가격 상승률이 최대 14배까지 벌어진다 | neutral | data | 성동구 29.04% vs 도봉구 2.07% | 38행 ("최대 14배" + 두 수치 모두 명시) | O |  |
| 4 | 공시가격 급등에 따른 보유세 부담 증가가 주택 소유자들의 매도 심리를 유발한다 | cautious | opinion |  | 9행, 15행, 20행 | O |  |
| 5 | 고가 주택 소유주들의 보유세 부담이 최대 57.1%까지 급증할 것으로 예상된다 | cautious | data | 최대 57.1% 급증 예상 | 15행 (압구정 현대·반포 원베일리 사례) | O |  |
| 6 | 현재의 공시가격 결정 방식과 현실화율이 유지될 경우 서울 고가 아파트 중심의 세금 부담 증가는 불가피하다 | cautious | opinion |  | 45행 | O |  |
| 7 | 공시가격 급등으로 인한 보유세 부담 증가가 임대료 상승으로 세입자에게 전가될 가능성이 있다 | cautious | opinion |  | 51행 | O |  |

## 9. [T2/mckinsey-insights] How to maximize competitive advantage
원문: `data\raw\mckinsey-insights\1A032E1BB4B346399DDCAFFFF4A.txt`

claim 0건 — 대조 대상 없음 (피드 요약 449자만 저장)

## 10. [T1/arxiv-cs-cy] Interaction Effects Between Learner Characteristics and Dialogue Format in TTS Dialogue-Based Lessons
원문: `data\raw\arxiv-cs-cy\1A032DD5A8BEADBEF085427F901.txt`

| # | claim | stance | evidence | metric | 근거 위치 | 판정(O/X) | 실패 유형 |
|---|---|---|---|---|---|---|---|
| 1 | 학습자의 구체적 경험 성향(CE)은 교사-교사 대화 형식에서 교사-학생 형식보다 동기에 더 긍정적인 영향을 미친다 | conditional | experiment |  | 5행 초록 ("the effect of the CE factor…") | O |  |
| 2 | 학습자의 반성적 관찰 및 추상적 개념화를 통한 능동적 실험 성향(RCE)은 교사-교사 대화 형식에서 동기에 미치는 긍정 효과가 상대적으로 약하다 | conditional | experiment |  | 5행 ("the positive effect of the RCE factor was relatively weaker") | O |  |
| 3 | TTS 대화 기반 수업에서 대화 형식과 학습자의 구체적 경험 성향 간의 상호작용이 학습 성과에 통계적으로 유의미한 경향을 보인다 | neutral | experiment |  | 5행 ("trend toward significance" = 유의 '경향' — claim 표현과 일치 여부 확인) | O |  |
| 4 | 교사-교사 대화 형식은 교사-학생 형식에 비해 전체적 평가가 유의미하게 낮다 | cautious | experiment |  | 5행 ("significantly lower") | O |  |
| 5 | 대화 형식의 동기에 미치는 긍정 효과는 전체 평가 차이와 일치하지 않는 패턴을 보인다 | neutral | experiment |  | 5행 ("a pattern that diverged…") | O |  |
| 6 | TTS 대화 기반 수업의 효과적인 설계를 위해서는 학습자의 특성에 따라 대화 형식을 차별적으로 선택해야 한다 | conditional | theory |  | 5행 결론부 ("should be selected according to…") ※저자 제언 — theory 분류 타당성 검토. 원문은 효과크기 small-to-medium의 예비 증거임을 부기 | O |  |

---
총 claim 27건 / 정확도: **88.9%** (O 24건 ÷ 27) — 목표 90% 미달 → 프롬프트 v2 보강 후 동일 문서 재실행 비교 (spotcheck-2026-08-25-rerun.md)
실패 유형 코드: F1 날조 / F2 원문 복사 / F3 수치 불일치 / F4 분류 오류

### 대조 중 발견된 참고 사항 (Claude 사전 검토 — 판정은 검수자 몫)
- 수치(metric) 대조 결과: 6개월·5곳·9.13%·90%·14배·57.1% 등 시트의 모든 수치가 원문 수치와 일치함을 확인. 날조 의심 사례는 발견하지 못함.
- 주의 깊게 볼 3건: **2-2** (metric란에 수치 아닌 영어 원문 구절 — F3 또는 기준② 위반 소지), **7-1** (단일 사례의 과잉 일반화 소지), **6-3** (원문 자체의 A사/B사 표기 불일치).
- claim 0건 문서 4건 중 3건은 본문 없이 피드 요약(130~450자)만 저장된 McKinsey 문서 — 스팟체크 모수에서 제외되므로, 필요시 표본을 추가 선정해 27건 이상을 확보하는 것도 방법.

### 최종 결론 (2026-08-25, 검수: 김산결)
- v1 정확도 88.9% (24/27) 미달 → 프롬프트 v2 보강 (metric 정의 강화, experiment/theory 분류 명확화)
- 동일 문서 재실행 비교(spotcheck-2026-08-25-rerun.md) 결과 실패 3건 모두 해소 — **재판정 통과**
- **결정: A안** — DB의 기존 v1 claims 895건은 유지 (실패 유형이 날조가 아닌 분류·표기 문제).
  아티클 증거로 선정되는 claim은 검증 단계(⑧)에서 개별 재확인. 신규 추출부터 v2 적용.
