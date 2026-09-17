아티클 발행 도구(웹 UI)를 실행한다.

절차:
1. launch.json의 "publish-ui" 설정을 사용하여 preview_start로 서버를 실행한다.
2. Bash로 `start http://localhost:5001` 실행하여 기본 브라우저에서 페이지를 연다.
3. 사용자에게 안내: "발행 도구가 열렸습니다. .md 파일을 업로드하세요."
4. API 키가 미설정이면 상단 입력란에 OpenAI API 키를 붙여넣으라고 안내한다.
