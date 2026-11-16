사내 자료(`pipeline/internal/`)를 재색인한다.

(2026-11-16 main에서 옮김 — 명령은 `pipeline/` 폴더에서 실행한다: `cd pipeline`)

사내 자료 규칙 (pipeline/CLAUDE.md 절대 규칙 4):
- `internal/`에는 공개 가능 판단이 끝난 자료만 둔다. 판단 기준: "사보에 실려도 되는가."
  이 폴더의 텍스트는 칼럼 생성 때 외부 API로 전송된다. 등급 체계는 운용하지 않는다.
- 본문 파일(*.md)은 git에 올리지 않는다(저장소 Public). git에 올라가는 것은 `_TEMPLATE.md`와
  `내부자료_등록목록.md`뿐이다.

절차:
1. 새 자료는 해당 하위 폴더(`leadership-messages/` · `policies/` · `skms/`)의 `_TEMPLATE.md` 형식으로
   파일을 만든다.
2. `make sync` 실행 — 바뀐 파일만 Supabase `internal_docs`에 반영된다(내용 해시 비교).
   형식 오류가 보고되면 해당 파일명과 수정 방법을 사용자에게 안내한다.
3. `internal/내부자료_등록목록.md`에 등록 기록(날짜·제목·출처)을 한 줄 추가한다.
4. 커밋은 등록목록만 들어가는지 `git status`로 확인한 뒤, 사용자가 요청할 때 한다.
