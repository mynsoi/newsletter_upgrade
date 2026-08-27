이론 카드를 새로 작성한다: $ARGUMENTS

절차 (기획서 3.5 반자동 구축):
1. knowledge/theories/이론_구축목록.md에서 해당 이론 확인 (없으면 적절한 영역에 추가)
2. knowledge/theories/_TEMPLATE.md 형식으로 카드 초안 작성 → status: draft
   - 핵심 명제: 참/거짓을 따질 수 있는 명제만, 자체 문장으로, 3~6개
   - 경계 조건: 이론이 성립하지 않는 상황 1~3개 (재현 실패·방법론 비판 논쟁이 있으면 반드시 포함)
   - AI 시대 연결점: 이 이론으로 최신 현상을 읽는 각도 1~3개
   - 원전 서지정보 정확히 기재
3. 사용자에게 검수를 요청한다: "원전이나 교과서와 대조해 확인 후,
   frontmatter의 status를 reviewed로, reviewed_by에 이름을 기재해 주세요."
   ※ 절대 Claude가 스스로 reviewed로 바꾸지 않는다 — 사람 검수가 색인의 전제 조건이다.
4. 사용자가 검수 완료를 알리면 `make theories` 실행 → 색인 결과 보고
