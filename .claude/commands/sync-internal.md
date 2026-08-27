internal/ 디렉토리의 내부 자료를 재색인한다.

절차:
1. `make sync` 실행
2. security: C 거부 또는 형식 오류가 보고되면 해당 파일명과 수정 방법을 사용자에게 안내
   (C 파일은 절대 열어보지 않는다 — CLAUDE.md 절대 규칙 4)
3. B등급 문서가 "API 전송 제외(이행기)"로 표시되는 것은 정상이다.
   보안 검토 승인 전에는 settings.yaml의 b_grade_api_approved를 변경하지 않는다.
