[발행 확정 플로우] 승인부터 본발송·기록까지 한 편을 발행한다: $ARGUMENTS

**발행 규칙: 매주 금요일 발행. 금요일이 휴일이면 직전 워킹데이에 발행한다**
(예: 창간호 — 2026-10-09(금) 한글날 휴일 → 10-08(목) 발행). 1단계의 `발행 승인` 날짜가 곧 발행일이다.

2026-10-05 확정(창간호 런치). 한 단계가 끝나야 다음으로 간다 — 단계를 합치거나 건너뛰지 않는다.
표기: 🤖 Claude가 실행 · 🙋 사람이 실행 · ✋ 사람 확인 후 다음 단계. 담당은 역할로 적는다
(편집 담당 = 원고·발행 책임자, 리더 = 컨펌권자).

| # | 단계 | 실행 | 담당 | 산출·확인 |
|---|---|---|---|---|
| 1 | 승인 | 🙋 ✋ | 편집 담당 + 리더 | 체크리스트 통과 · 머리말 `<!-- 발행 승인: YYYY-MM-DD -->` |
| 2 | /publish 기록 | 🤖 ✋ | Claude | content/published/ 이동 · DB approved · 인용 원장 |
| 3 | 발행 도구 | 🙋 | 편집 담당 | output/{slug}/ (웹 HTML·이미지·article.json) |
| 4 | make site | 🤖 | Claude | site/{token}/{slug}/ + 아카이브 갱신 |
| 5 | 커밋·push | 🤖 ✋ | Claude (push는 사람 승인) | origin/main → Vercel 자동 배포 |
| 6 | Vercel 확인 | 🤖 + 🙋 | Claude(헤더·응답) · 편집 담당(눈으로) | 200 · X-Robots-Tag · 링크 동작 |
| 7 | .eml 생성 | 🤖 또는 🙋 | 편집 담당 | newsletter.eml (image) / newsletter-teaser.eml |
| 8 | 리허설 | 🙋 ✋ | 편집 담당 → 리허설 3인 | content/reports/launch-rehearsal-checklist.md 판정 |
| 9 | 본발송 | 🙋 | 편집 담당 (VDI Outlook) | 전 구성원 발송 — Claude는 발송하지 않는다 |
| 10 | 기록 | 🤖 | Claude | 발행 기록 머리말 · 커밋·push |

## 1. 승인 (게이트 ⑥ — 기획서 6.2) 🙋 ✋

체크리스트를 사용자와 함께 확인한다:
□ 톤·강도·민감표현: 직군·세대·조직을 일반화하는 표현이 없는가
□ 경영층 인용: 실명·직책 정확, 발언 맥락 왜곡 없음, supersedes 체크(최신 메시지와 정합)
□ 검증 리포트의 플래그 전건 해소 · 리포트 10장(발행 전 사람 확인 항목) 처리
□ 저작권: 원문 문장 전재 없음, 출처 목록 완비
□ 편집자 노트(`<!-- note -->`)가 있으면 문안 확정 — 검증·분량 대상이 아니므로 사람이 읽는다

통과하면 원고 머리말 주석에 `<!-- 발행 승인: YYYY-MM-DD -->`(발행일)를 넣는다.
발행 도구가 이 값을 발행일로 쓴다 — 없으면 오늘 날짜가 들어가고 경고가 뜬다.
반려 시: content/rejected/로 이동, 부록 B 코드(R-01~R-08)를 파일명 뒤에 기록하고 여기서 멈춘다.

## 2. /publish 기록 🤖 ✋

- 파일을 content/published/{slug}.md로 이동, articles 테이블 status='approved' 갱신.
- **인용 원장 기록 (필수)**: `python src/article_ledger.py record {slug}`
  본문의 `<!-- claims: -->` 주석을 문단 단위로 article_sources에 쓴다(재실행 안전 — 본문을 고쳐
  재승인하면 다시 돌린다). DB에 없는 claim이 있으면 기록하지 않고 실패한다 — 검증 리포트를 다시
  확인할 것. 이 원장이 비면 "6개월 무인용 소스 퇴출"(기획서 4.2)을 셀 수 없다.

## 3. 발행 도구 🙋

- `make publish-ui` (또는 /publish-ui) → http://localhost:5001 에서 content/published/{slug}.md 업로드.
- 발행일 경고가 뜨면 1단계로 돌아가 승인 날짜를 넣는다.
- 호수 입력, 이미지 스타일 선택(히어로·소제목 — OpenAI 이미지 생성 비용 발생), 태그 확인 후 발행.
- 산출: output/{slug}/ (index.html · 이미지 · style.css · article.json). output/은 저장소에 올라가지 않는다.

## 4. make site 🤖

`make site SLUG={slug}` — output/{slug}/를 site/{web_path_token}/{slug}/로 복사하고 아카이브
목록(site/{token}/index.html)을 다시 만든다. 메일 부산물(.eml·캡처)은 복사하지 않는다.

## 5. 커밋·push 🤖 ✋

`git add site/ && git commit -m "publish: {slug}"` → push는 사람 승인 후.
site/·vercel.json이 바뀐 커밋에서만 Vercel이 빌드한다(vercel.json ignoreCommand).

## 6. Vercel 확인 🤖 + 🙋

- 🤖 `curl -sI {web_base_url}/{token}/{slug}/` → `200` · `x-robots-tag: noindex, nofollow, noarchive`.
- 🤖 아카이브 `{web_base_url}/{token}/`에 새 카드가 최상단에 있는지.
- 🙋 브라우저로 열어 이미지·레이어 박스·편집자 노트·참고자료 링크를 눈으로 확인.
- 웹 주소가 열리기 전에는 7단계로 가지 않는다 — 메일의 "웹에서 보기"가 죽은 링크가 된다.

## 7. .eml 생성 🤖 또는 🙋

- 발행 도구 하단 "메일 형식" → 전문 이미지(기본) / 요약 + 웹 링크(teaser) → .eml 다운로드, 또는
  `python web/email_renderer.py {slug} --to … [--mode teaser]`.
- 제목: `[Insight Weekly] {아티클 제목}` · 발신: 편집 담당 계정(이소민/기업문화AX팀)에서 그대로 보낸다 — 공용 메일함 불필요.
- settings.yaml `web_base_url`이 비어 있으면 링크가 빠진다(경고 출력) — teaser는 아예 만들지 않는다.

## 8. 리허설 🙋 ✋

리허설 3인(실무 2 + 팀장)에게 먼저 보낸다. content/reports/launch-rehearsal-checklist.md의
항목을 판정하고, 기준에 걸리면 teaser로 전환해 7단계부터 다시 한다. 판정 결과를 체크리스트에 적는다.

## 9. 본발송 🙋

편집 담당이 VDI Outlook에서 .eml을 열어 수신자를 전 구성원으로 바꿔 보낸다.
Claude는 메일을 보내지 않는다(발송은 사람의 일).

## 10. 기록 🤖

content/published/{slug}.md 머리말에 한 줄을 덧붙이고 커밋·push한다:
`<!-- 발송: YYYY-MM-DD HH:MM · 형식 image|teaser · 리허설 판정 요약 · 웹 {URL} -->`
