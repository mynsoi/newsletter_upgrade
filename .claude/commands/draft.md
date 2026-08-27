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
   - 수치 대조(claims의 metric과 일치), 단독출처 40% 룰, banned_phrases 검사,
     eval/rubric.md 8항목 자체 채점
   - 18점 미만이면 ④ 재실행 (최대 2회)
