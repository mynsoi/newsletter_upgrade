[Phase 0: 수동 절차] 토픽 1건으로 아티클 초안을 만든다: $ARGUMENTS

Phase 2에서 자동화 예정. 현재는 아래 수동 절차를 Claude Code가 단계별로 수행하되,
각 단계 산출물을 파일로 저장하고 다음 단계 진행 전 사용자 확인을 받는다.

② 증거 수집 → content/evidence/{slug}.json
   - claims 테이블에서 주제 관련 claim 검색 (FTS)
   - 강제 조건 확인: 독립 출처 3곳+ / 상반 stance 1건+ / T1·T2 2건+
   - 권장: 이론 claim(evidence_type='theory') 1건+ 포함 — 현상을 이론의 경계 조건과 대조하는 각도 우선 (기획서 3.5)
   - 미충족 시 중단하고 "증거 부족" 보고 (CLAUDE.md 절대 규칙 2)
③ 앵글 설계 → content/angles/{slug}.md
   - 서로 다른 논지 3개, 각각 "반증 조건" 포함 → 사용자가 1개 선택
④ 초안 작성 → content/drafts/{slug}.md
   - 기획서 6.4 템플릿 (TL;DR / 관찰된 신호 / 통념과의 충돌 / 교차 해석 /
     SK 맥락에서의 의미 / 다음 주에 시도할 것(리더·실무자 분리) / 남은 쟁점 / 참고자료)
   - 모든 문단에 근거 claim ID를 HTML 주석으로 병기
   - 내부 자료 사용 시 api_eligible=1 문서만 사용
⑤ 검증 → content/drafts/{slug}-verification.md
   - **실사용 기준(A2)**: `python src/verify_article.py content/drafts/{slug}.md` 실행.
     evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**(문단 뒤 `<!-- claims: ... -->`)
     만으로 강제 조건을 재계산한다 — 독립 출처 3곳+ / 상반 stance(optimistic·cautious 각 1건+) /
     단일 출처 40% 이하 / 수치는 사용 claim의 metric·text와 대조.
     · evidence에 없는 claim ID나 출처를 본문이 인용하면 **실패**하고 해당 문장을 지목한다.
     · 참고자료는 실사용 문서만 남긴다 — 리포트 4장의 목록을 본문에 반영.
     · 리포트 1장의 "문장 ↔ claim ID 대응"으로 사람이 근거를 따라 읽을 수 있다.
     · 액션·참고자료 섹션의 처방 값(2주·주 1회)과 달력 연도(2026년)는 수치 검사에서 면제.
   - 이어서 banned_phrases 검사, eval/rubric.md 8항목 자체 채점
   - 검증 실패(exit 1)거나 18점 미만이면 ④ 재실행 (최대 2회)
