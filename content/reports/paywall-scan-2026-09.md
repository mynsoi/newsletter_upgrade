# 유료 소스 목록 스캔 — 연말 평가 시즌 백필 (2026-09)

<!-- 2026-09-22 · aside repl로 목록 페이지만 열람 (본문 페이지 미열람) · 조회 전용 -->

## 수집 추천 목록 (확정)

- **합계 11건** — dbr 9건 · hbr-korea 2건. 회당 상한 10건을 넘으므로 1건을 빼거나 2회로 나눈다.

| # | 소스 | 제목 | 슬롯 | 발행일 |
|---|---|---|---|---|
| 1 | dbr | [AI를 상사로 인식한 직원의 성과 동료나 부하로 여긴 직원보다 낮아](https://dbr.donga.com/article/view/1904/article_no/12277/ac/magazine) | 10/9 | 2026-09-22 |
| 2 | dbr | [재택근무자, ‘업무 중’ 입증 부담감 상사의 협업 요청에 더 신속히 응대](https://dbr.donga.com/article/view/1201/article_no/12260/ac/magazine) | 10/23 | 2026-09-08 |
| 3 | dbr | [열정적 직원에게 일 더 주는 경향 반복 땐 핵심 업무 성과 저하 위험](https://dbr.donga.com/article/view/1201/article_no/12262/ac/magazine) | 10/23 | 2026-09-08 |
| 4 | dbr | [주식 쏠림·성과급 갈등, 사회적 대가 치러 노동 계약·세대 간 부담 공정한 합의 필요](https://dbr.donga.com/article/view/1101/article_no/12242/ac/magazine) | 10/23 | 2026-08-25 |
| 5 | dbr | [조직 구성원의 ‘의도적 성과 저하’ 세 가지 동기별 다른 방식 개입 필요](https://dbr.donga.com/article/view/1201/article_no/12172/ac/magazine) | 10/16 | 2026-06-23 |
| 6 | dbr | [공정한 성과급 체계 설계하려면](https://dbr.donga.com/article/view/1101/article_no/12176/ac/magazine) | 10/23 | 2026-06-23 |
| 7 | dbr | [“공정한 보상의 조건, 재투자-협업 우선시해야 업황 변동 큰 산업, ‘보너스 뱅크’로 탄력 운영”](https://dbr.donga.com/article/view/1101/article_no/12177/ac/magazine) | 10/23 | 2026-06-23 |
| 8 | dbr | [‘깜깜이 성과급’에서 투명한 보상으로](https://dbr.donga.com/article/view/1101/article_no/12178/ac/magazine) | 10/23 | 2026-06-23 |
| 9 | dbr | [AI 시대, 고성과 배분의 새 문법](https://dbr.donga.com/article/view/1101/article_no/12179/ac/magazine) | 10/23 | 2026-06-23 |
| 10 | hbr-korea | [당신의 조언이 외국인 동료에게 안 통하는 이유](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1700/page/1) | 10/16 | 2026-09-18 |
| 11 | hbr-korea | [AI가 내린 결정을 직원이 책임질 때](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1689/page/1) | 10/9 | 2026-09-03 |

슬롯별: 10/16 2건 · 10/23 7건 · 10/9 2건. **10/16 피드백 면담이 2건뿐이다** — 아래 「범위 밖 참고」의 HBR 7월 글이 가장 정확히 맞는다.

## 스캔 범위와 원칙

- **대상**: `config/sources.yaml`의 `browse_list_urls` 전부. DBR — 매거진 랜딩(최신호 확인) → 450·449·448호 목차 (최근 30일 = 2026-08-23 이후 발행 호) + 홈. HBR Korea — `/article/latest` · 인사조직(2_1) · 리더십(8_1) · 2026.9-10월호 목차.
- **평가 시즌 특집·기획**: DBR은 10월 평가 시즌 특집이 아직 없다(최신 450호 주제 '기업교육'). 대신 성과·보상 기획인 **444호 「Redesigning Rewards」(2026-06-23)**를 기획 코너로 보고 포함했다. HBR Korea는 평가 특집 호가 없다.
- **확인 범위**: 제목·URL·발행일·코너명까지. 본문 페이지는 열지 않았다. 주제 표시·슬롯 판정은 **제목과 코너만 보고** 한 1차 선별이라, 수집 후 게이트·claim 추출 단계에서 실제 적합도가 다시 걸러진다.
- **기등재**: `documents`에서 source_id·article_no로 대조했다. 기등재 글은 추천에서 뺐다(중복 수집 방지).
- DBR 홈 노출분 중 목차 밖 4건(12194·12211·12192·12227)은 모두 30일 밖이거나 기등재라 표에 넣지 않았다.
- HBR Korea 발행일: 디지털 기사는 목록 표기일, 매거진 기사는 발행일 메타가 없어 호 첫 달 1일로 근사한다(sources.yaml note 규칙).

## 목록 표

주제 표시: 평가·피드백·성과관리·목표설정 관련만 표시. 빈칸은 이번 주제와 무관.

### DBR

| 발행일 | 위치 | 코너 | 제목 | 주제 | 슬롯 | 상태 | 판단 메모 |
|---|---|---|---|---|---|---|---|
| 2026-09-22 | 450호 | 인사/조직 | [기업교육, ‘존재의 의미’를 묻다](https://dbr.donga.com/article/view/1201/article_no/12275/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | DBR칼럼 | [AI 시대, 리더가 관리해야 할 희소 자원](https://dbr.donga.com/article/view/1801/article_no/12276/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | AI/DT | [AI를 상사로 인식한 직원의 성과 동료나 부하로 여긴 직원보다 낮아](https://dbr.donga.com/article/view/1904/article_no/12277/ac/magazine) | 성과관리 | 10/9 | **추천** | AI를 어떤 역할(상사·동료·부하)로 인식하느냐에 따라 성과가 갈린다는 연구 소개 — 자기평가 묶음 2(협업 모드)와 연결 |
| 2026-09-22 | 450호 | AI/DT | [수백 년 된 수도원도 디지털 적응 오래된 유산 ‘전용’해 혁신 자산化](https://dbr.donga.com/article/view/1904/article_no/12278/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 마케팅/세일즈 | [‘그린’보다 ‘지속가능한’ 라벨이 내구성 기대로 더 많이 선택받아](https://dbr.donga.com/article/view/1202/article_no/12279/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 스페셜리포트 | [“AI 시대 교육팀 역할과 중요성 더 커져 ‘얼마나 가르쳤나’ 아닌 성장 기회 설계해야”](https://dbr.donga.com/article/view/1101/article_no/12280/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 스페셜리포트 | [AI가 주니어 업무 대체, 시니어로 어떻게 키우나](https://dbr.donga.com/article/view/1101/article_no/12281/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 스페셜리포트 | [개인의 AI 생산성, 집단지성으로 바꾸려면](https://dbr.donga.com/article/view/1101/article_no/12282/ac/magazine) | 성과관리 |  |  | 개인 AI 생산성 → 집단 성과 전환. 10/8 창간 묶음 4와 맞닿지만 창간 슬롯은 재료 충분 |
| 2026-09-22 | 450호 | 스페셜리포트 | [AI 시대, 조직의 공동학습 설계 방안](https://dbr.donga.com/article/view/1101/article_no/12283/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 케이스스터디 | [웨이모의 ‘선택적 수직통합’과 로보택시 가치사슬 재편](https://dbr.donga.com/article/view/1901/article_no/12284/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | AI/DT | [실무자가 AI와 대화 통해 업무 세분화 외부 도움 없이 자동화 우선 과제 도출](https://dbr.donga.com/article/view/1904/article_no/12285/ac/magazine) | 목표설정 |  |  | AI 자동화 우선 과제 도출 — 10/30 목표 편과 연결 가능(재료 충분 슬롯) |
| 2026-09-22 | 450호 | 리더십 | [철학 전공한 ‘AI 국방 기업’의 지휘관 이념 리더십으로 ‘인간의 운전석’ 설계](https://dbr.donga.com/article/view/1306/article_no/12286/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 경영전략 | [어떤 재난에도 지켜야 할 핵심 기능 결정 충격 번질 길목 찾아 대체 경로 마련하라](https://dbr.donga.com/article/view/1203/article_no/12287/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 경영전략 | [위기야말로 시스템 혁신할 적기](https://dbr.donga.com/article/view/1203/article_no/12288/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 경영일반 | [정원 지키려 건물을 낮춘 미술관 ‘다시 와 걷고 싶은 하루’를 팔다](https://dbr.donga.com/article/view/1206/article_no/12289/ac/magazine) |  |  |  |  |
| 2026-09-22 | 450호 | 자기계발 | [아웃사이드인 外](https://dbr.donga.com/article/view/1303/article_no/12290/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 경영일반 | [‘순례자’들이 중국으로 가는 이유](https://dbr.donga.com/article/view/1206/article_no/12258/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | DBR칼럼 | [거인이 따라올 수 없는 자리](https://dbr.donga.com/article/view/1801/article_no/12259/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 인사/조직 | [재택근무자, ‘업무 중’ 입증 부담감 상사의 협업 요청에 더 신속히 응대](https://dbr.donga.com/article/view/1201/article_no/12260/ac/magazine) | 평가·성과관리 | 10/23 | **추천** | 원격근무자의 '보이는 성과' 부담 — 평가 가시성 편향, 공정성 묶음과 연결 |
| 2026-09-08 | 449호 | 마케팅/세일즈 | [부정 리뷰, 유용하다는 평가받지만 리뷰어에 대한 신뢰도는 떨어뜨려](https://dbr.donga.com/article/view/1202/article_no/12261/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 인사/조직 | [열정적 직원에게 일 더 주는 경향 반복 땐 핵심 업무 성과 저하 위험](https://dbr.donga.com/article/view/1201/article_no/12262/ac/magazine) | 성과관리·공정성 | 10/23 | **추천** | 열정적 직원에게 일이 몰리는 배분 편향 — 업무 배분의 공정성 |
| 2026-09-08 | 449호 | 스페셜리포트 | [베이징 WRC 2026 현장 르포 중국 로봇 산업의 진화](https://dbr.donga.com/article/view/1101/article_no/12263/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 스페셜리포트 | [중국 AI 플랫폼 ‘습관의 해자’ 전략](https://dbr.donga.com/article/view/1101/article_no/12264/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 스페셜리포트 | [기술 굴기 중국, 어떻게 ‘엔지니어의 나라’ 됐나](https://dbr.donga.com/article/view/1101/article_no/12265/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 스페셜리포트 | [中 ‘체화지능 로봇’ 혁명 이끄는 3대 지역 생태계](https://dbr.donga.com/article/view/1101/article_no/12266/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 케이스스터디 | [LG유플러스의 ‘심플리 유플러스-심플랩’ 혁신 전략](https://dbr.donga.com/article/view/1901/article_no/12267/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 리더십 | [“날 욕하는 익명 커뮤니티 글, 대응 어떻게?”](https://dbr.donga.com/article/view/1306/article_no/12268/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 경영전략 | [공급망 불안 시대엔 효율보다 회복탄력성 주주·고객 요구 반영하고 이사회가 조정을](https://dbr.donga.com/article/view/1203/article_no/12269/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 인사/조직 | [AI로 직무 급변하는 시대엔 ‘잠재력’ 본다 업무 안 정하고 새 역할 찾아갈 인재 선발](https://dbr.donga.com/article/view/1201/article_no/12270/ac/magazine) | 평가(선발) |  |  | 잠재력 기반 선발 — 채용 평가라 이번 슬롯과 거리 |
| 2026-09-08 | 449호 | 자기계발 | [Biz X 449](https://dbr.donga.com/article/view/1303/article_no/12271/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 경영전략 | [“넘버원 아닌 온리원” 40년 건재한 전략](https://dbr.donga.com/article/view/1203/article_no/12272/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 리더십 | [후계자 지정 뒤 흔들면 조직 전체 대혼란](https://dbr.donga.com/article/view/1306/article_no/12273/ac/magazine) |  |  |  |  |
| 2026-09-08 | 449호 | 자기계발 | [초풍요의 시대 外](https://dbr.donga.com/article/view/1303/article_no/12274/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 경영전략 | [경계의 재선택, ‘리바운더리’](https://dbr.donga.com/article/view/1203/article_no/12236/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | DBR칼럼 | [‘위임 설계’가 가를 AI 시대 경쟁력](https://dbr.donga.com/article/view/1801/article_no/12237/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 마케팅/세일즈 | [가격 인상보다 품질 저하가 더 위험 소비자에 ‘몰래 속였다’는 인상 줘](https://dbr.donga.com/article/view/1202/article_no/12238/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 인사/조직 | [‘님’ ‘프로’ 같은 호칭으로 직급 파괴 수직적 문화 완화에 별 효과 없어](https://dbr.donga.com/article/view/1201/article_no/12239/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | AI/DT | [진정성 더 평가받는 AI 챗봇의 사과 사람 이미지·공감 말투 쓰면 효과적](https://dbr.donga.com/article/view/1904/article_no/12240/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [2027년 경영 화두로 떠오를 12개의 키워드 DBR X1, X2팀,정리=백상경](https://dbr.donga.com/article/view/1101/article_no/12241/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [주식 쏠림·성과급 갈등, 사회적 대가 치러 노동 계약·세대 간 부담 공정한 합의 필요](https://dbr.donga.com/article/view/1101/article_no/12242/ac/magazine) | 공정성·보상 | 10/23 | **추천** | 성과급 갈등과 공정한 합의 — 공정성 묶음의 상반 관점 후보 |
| 2026-08-25 | 448호 | 스페셜리포트 | [욕망 끄거나 결합, 놀이화하는 소비자들 소비 자극 아닌 조절 돕는 브랜드 뜬다](https://dbr.donga.com/article/view/1101/article_no/12243/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [소비자·내부 직원 모두 기업 민낯 감시 결함까지 공개하는 투명성이 곧 경쟁력](https://dbr.donga.com/article/view/1101/article_no/12244/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [직무를 과업으로 나눠 사람·AI에 배분 판단 절차·결과 기록해 데이터 자산化](https://dbr.donga.com/article/view/1101/article_no/12245/ac/magazine) | 성과관리 |  | 기등재(enriched) | 과업 분해·판단 기록 — 기등재 |
| 2026-08-25 | 448호 | 스페셜리포트 | [로봇 구매 않고 고용해 필요 작업 투입 성과에 비용 지불, 中企 ‘로봇 해법’ 된다](https://dbr.donga.com/article/view/1101/article_no/12246/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [AI로 달성한 고성과를 실력으로 착각 설명·응용할 수 있는지 역량 검증해야](https://dbr.donga.com/article/view/1101/article_no/12247/ac/magazine) | 평가·역량 검증 |  | 기등재(enriched) | AI로 낸 성과와 실력의 구분 — 10/9에 정확히 맞으나 기등재 |
| 2026-08-25 | 448호 | 스페셜리포트 | [AI가 여러 앱·웹 연결해 삶의 과업 완수 성과지표, 체류시간→목표달성률 이동](https://dbr.donga.com/article/view/1101/article_no/12248/ac/magazine) | 목표설정 |  | 기등재(enriched) | 지표 이동(체류시간→목표달성률) — 소비자 맥락, 기등재 |
| 2026-08-25 | 448호 | 스페셜리포트 | [AI 발전할수록 ‘날것’의 ‘진정성’에 감동 기업과 창작자는 ‘인간의 흔적’ 설계해야](https://dbr.donga.com/article/view/1101/article_no/12249/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [전쟁·기후·AI 충격 등 위기가 경영 상수 평시 예산에도 ‘전천후 대비’ 반영 필수](https://dbr.donga.com/article/view/1101/article_no/12250/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [ESG 퇴조 속 전략적 리밸런싱 필요 관련 사업 재점검하고 비용 효율화를](https://dbr.donga.com/article/view/1101/article_no/12251/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [전쟁·AI 전력난에 자국산 에너지 중시 한국엔 원전·ESS 등 인프라 수출 기회](https://dbr.donga.com/article/view/1101/article_no/12252/ac/magazine) |  |  | 기등재(rejected) |  |
| 2026-08-25 | 448호 | 스페셜리포트 | [AI 투자로 수익 높인 기업에 기회 집중 도입 자체보다 이익 남는 사업구조 중요](https://dbr.donga.com/article/view/1101/article_no/12253/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 자기계발 | [AI의 반론, 방어만 말고 적극 활용을 문제 재정의와 사고 확장의 지름길](https://dbr.donga.com/article/view/1303/article_no/12254/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 자기계발 | [제1회 AI 대화형 비즈니스 논술대회 수상작 정리=배미정](https://dbr.donga.com/article/view/1303/article_no/12255/ac/magazine) |  |  |  |  |
| 2026-08-25 | 448호 | 인사/조직 | [근로시간 줄면 ‘고밀도 노동’ 부작용도 ‘일의 의미’ 재설계돼야 직원·조직 윈윈](https://dbr.donga.com/article/view/1201/article_no/12256/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-08-25 | 448호 | 자기계발 | [조직은 어떻게 강해지는가 外](https://dbr.donga.com/article/view/1303/article_no/12257/ac/magazine) |  |  | 기등재(enriched) |  |
| 2026-06-23 | 444호 (보상 기획) | 인사/조직 | [‘좋은 보상’의 조건](https://dbr.donga.com/article/view/1201/article_no/12170/ac/magazine) | 공정성·보상 |  |  | 444호 특집 여는 글(편집장 칼럼) — 특집 본편들로 대체 |
| 2026-06-23 | 444호 (보상 기획) | DBR칼럼 | [투표용지 사태가 기업에 주는 교훈](https://dbr.donga.com/article/view/1801/article_no/12171/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 인사/조직 | [조직 구성원의 ‘의도적 성과 저하’ 세 가지 동기별 다른 방식 개입 필요](https://dbr.donga.com/article/view/1201/article_no/12172/ac/magazine) | 성과관리·피드백 | 10/16 | **추천** | 의도적 성과 저하의 동기별 개입 — 면담에서의 개입 방식 |
| 2026-06-23 | 444호 (보상 기획) | AI/DT | [AI를 입맛대로 튜닝해 사용할 때 업무 만족하는 ‘직장 웰빙’ 높아져](https://dbr.donga.com/article/view/1904/article_no/12173/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 마케팅/세일즈 | [“패스트패션 입는 사람은 유행 추종” 자기통제력 낮다는 인상 줄 가능성](https://dbr.donga.com/article/view/1202/article_no/12174/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 인사/조직 | [위기 겪은 후 복기·학습하는 조직 다음 위기 때 회복 시간 빨라진다](https://dbr.donga.com/article/view/1201/article_no/12175/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 스페셜리포트 | [공정한 성과급 체계 설계하려면](https://dbr.donga.com/article/view/1101/article_no/12176/ac/magazine) | 공정성·보상 | 10/23 | **추천** | 공정한 성과급 체계 설계 — 444호 특집 |
| 2026-06-23 | 444호 (보상 기획) | 스페셜리포트 | [“공정한 보상의 조건, 재투자-협업 우선시해야 업황 변동 큰 산업, ‘보너스 뱅크’로 탄력 운영”](https://dbr.donga.com/article/view/1101/article_no/12177/ac/magazine) | 공정성·보상 | 10/23 | **추천** | 공정한 보상의 조건 인터뷰 — 444호 특집 |
| 2026-06-23 | 444호 (보상 기획) | 스페셜리포트 | [‘깜깜이 성과급’에서 투명한 보상으로](https://dbr.donga.com/article/view/1101/article_no/12178/ac/magazine) | 공정성·보상 | 10/23 | **추천** | 성과급 투명성 — 절차 공정성과 직결, 444호 특집 |
| 2026-06-23 | 444호 (보상 기획) | 스페셜리포트 | [AI 시대, 고성과 배분의 새 문법](https://dbr.donga.com/article/view/1101/article_no/12179/ac/magazine) | 공정성·성과 격차 | 10/23 | **추천** | AI 시대 고성과 배분 — 도구 격차 시대의 배분, 10/23 논지에 가장 근접 |
| 2026-06-23 | 444호 (보상 기획) | 스페셜리포트 | [현실 반영 못하는 근로기준법](https://dbr.donga.com/article/view/1101/article_no/12180/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 케이스스터디 | [시몬스 ‘라이프 이즈 컴포트’ 브랜드 캠페인](https://dbr.donga.com/article/view/1901/article_no/12181/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 케이스스터디 | [NH농협은행, Agentic AI Bank 전환 선언](https://dbr.donga.com/article/view/1901/article_no/12182/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 리더십 | [“성공한 AI 전환은 100% CEO가 직접 챙겨 독점 데이터를 워크플로에 내재화해야”](https://dbr.donga.com/article/view/1306/article_no/12183/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | AI/DT | [에이전틱 엔터프라이즈로의 전환 데이터 사일로 허물고 ‘파일럿 지옥’ 탈출하라](https://dbr.donga.com/article/view/1904/article_no/12184/ac/magazine) |  |  |  |  |
| 2026-06-23 | 444호 (보상 기획) | 인사/조직 | [“채용팀, AI 활용한 직무 역량 검증 필요 지원자는 ‘내 전문성에 AI 결합’ 전략을”](https://dbr.donga.com/article/view/1201/article_no/12185/ac/magazine) | 평가(선발) |  |  | 채용 역량 검증 — 이번 슬롯과 거리 |
| 2026-06-23 | 444호 (보상 기획) | 자기계발 | [생존 지능 外](https://dbr.donga.com/article/view/1303/article_no/12186/ac/magazine) |  |  |  |  |

### HBR Korea

| 발행일 | 위치 | 코너 | 제목 | 주제 | 슬롯 | 상태 | 판단 메모 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | 최신·주제별 목록 | 전략·디지털 | [에어컨 없는 지옥, 유럽을 살린 미데아의 블루오션 전략](https://www.hbrkorea.com/article/view/atype/di/category_id/1_1/article_no/1701/page/1) |  |  |  |  |
| 2026-09-18 | 최신·주제별 목록 | 리더십·디지털 | [당신의 조언이 외국인 동료에게 안 통하는 이유](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1700/page/1) | 피드백 | 10/16 | **추천** | 조언 스타일의 문화권 차이 — 피드백 전달 방식 |
| 2026-09-17 | 최신·주제별 목록 | 전략 & 위기관리·디지털 | [우리 회사의 지정학적 리스크는 얼마짜리일까](https://www.hbrkorea.com/article/view/atype/di/category_id/1_1/article_no/1699/page/1) |  |  |  |  |
| 2026-09-16 | 최신·주제별 목록 | 위기관리·디지털 | [실망스러운 실적 소식 제대로 전하는 법](https://www.hbrkorea.com/article/view/atype/di/category_id/11_1/article_no/1698/page/1) |  |  |  |  |
| 2026-09-15 | 최신·주제별 목록 | 리더십·디지털 | [AI 시대에 리더십 브랜드 지키는 법](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1697/page/1) |  |  |  |  |
| 2026-09-14 | 최신·주제별 목록 | 전략·디지털 | [AI 경쟁의 다음 단계는 마진 전쟁이다](https://www.hbrkorea.com/article/view/atype/di/category_id/1_1/article_no/1696/page/1) |  |  |  |  |
| 2026-09-11 | 최신·주제별 목록 | 운영관리·디지털 | [오프라인 매장이 살아남는 이유](https://www.hbrkorea.com/article/view/atype/di/category_id/7_1/article_no/1695/page/1) |  |  |  |  |
| 2026-09-10 | 최신·주제별 목록 | 인사조직·디지털 | [다른 지역 팀들과 효과적으로 협업하는 법](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1694/page/1) |  |  |  |  |
| 2026-09-09 | 최신·주제별 목록 | 인사조직·디지털 | [AI 에이전트는 어떻게 일의 범위를 넓히는가](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1693/page/1) | 목표설정 |  |  | AI로 넓어지는 일의 범위 — 10/30 목표 편 묶음 4와 연결(재료 충분 슬롯) |
| 2026-09-08 | 최신·주제별 목록 | 리더십 & 인사조직·디지털 | [AI시대에도 샌드위치 신세인 중간관리자](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1692/page/1) |  |  |  | 중간관리자 — 평가 주제 아님 |
| 2026-09-07 | 최신·주제별 목록 | 마케팅 & 전략·디지털 | [브랜드 인지도를 넘어 AI의 선택을 받는 법](https://www.hbrkorea.com/article/view/atype/di/category_id/3_1/article_no/1691/page/1) |  |  |  |  |
| 2026-09-04 | 최신·주제별 목록 | 혁신 & 전략·디지털 | [AI가 해결하지 못하는 혁신의 문제들](https://www.hbrkorea.com/article/view/atype/di/category_id/5_1/article_no/1690/page/1) |  |  |  |  |
| 2026-09-03 | 최신·주제별 목록 | 리더십·디지털 | [AI가 내린 결정을 직원이 책임질 때](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1689/page/1) | 성과관리·책임 | 10/9 | **추천** | AI 결정의 책임 소재 — 자기평가 묶음 3·5(검증·책임)와 연결 |
| 2026-09-02 | 최신·주제별 목록 | 인사조직·디지털 | ['재택이냐, 사무실 출근이냐'는 틀린 질문이다](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1688/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 인사조직 & 마케팅·매거진 | [편집장이 먼저 읽었습니다](https://www.hbrkorea.com/article/view/atype/ma/category_id/2_1/article_no/2466/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 전략·매거진 | [AI 시대, 전략을 수립하는 더 나은 방법](https://www.hbrkorea.com/article/view/atype/ma/category_id/1_1/article_no/2465/page/1) |  |  | 기등재(new) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 운영관리·매거진 | [AI 활용이 어려운 팀을 위한 3가지 실천 방안](https://www.hbrkorea.com/article/view/atype/ma/category_id/7_1/article_no/2471/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 운영관리·매거진 | [AI 에이전트를 위한 온보딩 계획](https://www.hbrkorea.com/article/view/atype/ma/category_id/7_1/article_no/2470/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 인사조직·매거진 | [AI 시대, 기업에는 에이전트 매니저가 필요하다](https://www.hbrkorea.com/article/view/atype/ma/category_id/2_1/article_no/2469/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 운영관리·매거진 | [AI 에이전트를 팀원으로 생각하라](https://www.hbrkorea.com/article/view/atype/ma/category_id/7_1/article_no/2468/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 운영관리 & 전략·매거진 | [‘성장’에 얼마나 투자해야 할까?](https://www.hbrkorea.com/article/view/atype/ma/category_id/7_1/article_no/2479/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 리더십·매거진 | [CEO와 이사회 관계의 4단계](https://www.hbrkorea.com/article/view/atype/ma/category_id/8_1/article_no/2478/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 마케팅·매거진 | [고객 추천의 힘을 과소평가하지 마라](https://www.hbrkorea.com/article/view/atype/ma/category_id/3_1/article_no/2477/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 데이터 사이언스 & 운영관리·매거진 | [AI 에이전트가 사일로를 넘어 오케스트레이션하는 법](https://www.hbrkorea.com/article/view/atype/ma/category_id/10_1/article_no/2476/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 전략·매거진 | [핵심 영역에서 협력하고 주변부에서 경쟁하라](https://www.hbrkorea.com/article/view/atype/ma/category_id/1_1/article_no/2475/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 혁신 & 전략·매거진 | [변화는 학습이다](https://www.hbrkorea.com/article/view/atype/ma/category_id/5_1/article_no/2474/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 전략 & 데이터 사이언스·매거진 | [AI, 전략적 의사결정을 혁신하다](https://www.hbrkorea.com/article/view/atype/ma/category_id/1_1/article_no/2473/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 리더십 & 인사조직·매거진 | [“패배는 내게 없습니다”](https://www.hbrkorea.com/article/view/atype/ma/category_id/8_1/article_no/2472/page/1) |  |  |  |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 인사조직 & 혁신·매거진 | [현금 보상이 더 나은 아이디어 창출을 반드시 보장하지 못하는 이유](https://www.hbrkorea.com/article/view/atype/ma/category_id/2_1/article_no/2467/page/1) | 보상 |  | 기등재(enriched) | 현금 보상과 아이디어 — 기등재 |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 인사조직 & 혁신·매거진 | [HCL테크 CEO, AI 시대를 위한 전환을 말하다](https://www.hbrkorea.com/article/view/atype/ma/category_id/2_1/article_no/2481/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01 | 최신·주제별 목록 | 인사조직·디지털 | [실제 조직과 보고서 속 조직의 간극 줄이기](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1687/page/1) |  |  | 기등재(enriched) |  |
| 2026-08-31 | 최신·주제별 목록 | 인사조직 & 전략·디지털 | [AI 시대, 시험대에 오른 모듈화 기업](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1686/page/1) |  |  | 기등재(enriched) |  |
| 2026-08-26 | 최신·주제별 목록 | 인사조직·디지털 | [새로운 성과 관리 지표가 필요한 AI 시대](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1683/page/1) | 성과관리 |  | 기등재(enriched) | AI 시대 성과관리 지표 — 기등재 |
| 2026-08-25 | 최신·주제별 목록 | 인사조직·디지털 | [신입 직급이 사라지면 리더십도 사라진다](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1682/page/1) |  |  | 기등재(enriched) |  |
| 2026-09-01(9-10월호) | 최신·주제별 목록 | 리더십 & 자기계발·매거진 | [권한이 없을 때 영향력을 행사하는 5가지 방법](https://www.hbrkorea.com/article/view/atype/ma/category_id/8_1/article_no/2480/page/1) |  |  | 기등재(enriched) |  |
| 2026-08-27 | 최신·주제별 목록 | 리더십·디지털 | [기업 리더에게 철학이 필요한 이유](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1684/page/1) |  |  | 기등재(enriched) |  |

## 범위 밖 참고 (30일 밖 · 특집 아님 — 추천 목록에 넣지 않음)

HBR Korea 주제별 목록에 노출된 글 중 슬롯에 정확히 맞는데 범위 밖이라 뺀 것. 넣을지는 사용자 판단.

| 발행일 | 제목 | 슬롯 | 상태 | 메모 |
|---|---|---|---|---|
| 2026-07-16 | [피드백이 감정만 상하게 할 때](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1656/page/1) | 10/16 | 미등재 | 10/16 피드백 면담에 가장 정확히 맞는 글 |
| 2026-07-20 | [직원들은 왜 AI 활용법을 숨기는가](https://www.hbrkorea.com/article/view/atype/di/category_id/2_1/article_no/1657/page/1) | 10/9 | 미등재 | 자기평가에서 AI 기여를 드러내지 않는 행동 |
| 2026-08-18 | [1000건의 회의에서 도출한 대화 관리법](https://www.hbrkorea.com/article/view/atype/di/category_id/8_1/article_no/1677/page/1) | 10/16 | 미등재 | 면담 대화 운영 |

## 다음 단계

- 사용자가 "진행"하면 추천 목록을 `/browse-collect`로 건별 수집한다 (회당 상한 10건, license_note 기존 문구 동일).
- 수집 후 게이트·추출을 이어 돌리고 슬롯별(10/9·10/16·10/23) 재료 충족을 다시 센다.
- 참고: phase2-plan(2026-09-22)에서 10/9 자기평가 요소는 10/8 창간호로 흡수됐다. 이 표의 10/9 표시는 창간호 재료로 읽는다.
