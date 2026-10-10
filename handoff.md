# handoff — mentor-lab 칼럼 작업실 (2026-10-10 기준)

이 문서 하나로 다음 사람(또는 다음 세션)이 이어받을 수 있게 정리했다. 최신 커밋 `4aefc95` 기준.

## 1. 한눈에

- **무엇:** SK E&S 기업문화AX팀(김산결M·이소민M) 사내 뉴스레터 칼럼을, 멘토(팀스파르타) 방식으로 만드는 실험 저장소 `skens/mentor-lab/`(git, 브랜치 master). 팀 저장소 `newsletter_upgrade/`와는 따로 간다 — 팀 방식(문체 지침·루브릭·증거 게이트)은 쓰지 않는다.
- **작업실(웹앱):** http://100.73.64.64:8771 (Tailscale, Mac에서도) · 이 PC에서는 http://localhost:8771. 데스크톱 전용, 비밀번호 없음(멘토 결정).
- **흐름:** 서재(aside 수집) → 주제 지도(LLM 위키) → 제목(astra) → 과정 1·2·3(Claude 초안 → astra 재작성 → astra 기준 반영) → [절반] → 과정 4~(멘토 피드백, astra) → 그림(머리 + 본문 3개, astra 설명 + gti) → 확정.
- **최근 결정 리포트:** http://100.73.64.64:8771/docs/2026-10-10-주제-위키-시험.html — 주제를 위키로 쌓기로 한 근거(블라인드 비교).

## 2. 사용자와 일하는 방식 (꼭 지킬 것)

멘토의 관점은 "결과 → 과정 → 결과 업그레이드". 아래는 멘토가 직접 정했거나 지적한 것들.

- **원문 그대로:** 요약본·발췌로 쓰지 않는다. 글은 언제나 원문 전체로. 위키·요약은 목차일 뿐.
- **멘토 피드백은 받은 그대로** 파일로 넘긴다. 해석·재작성 금지.
- **제목은 astra만** — Claude가 지은 제목은 "AI slop". 후보를 보여 줄 때도 astra 것을 그대로.
- **"(끝)"은 뺀다**(경영일기 필자의 맺음 표시라 참고 글에서부터 제거).
- **gti(그림)는 무조건 gpt-6-astra** — 전역 npm `gti`는 기본 gpt-5.4라 400. god-tibo-imagen 스킬 스크립트로 부른다.
- **화면:** 데스크톱만, wow 디자인(참고 사이트 = 컴포넌트를 실제로 설치해 쓰는 곳), UI 사이사이 설명 문구 금지, 임의 개수 상한 금지, 판은 "과정 1·2·3", 주제도 AI가 내고 멘토는 고르기만.
- **실험판은 목록에 섞지 않는다**(briefs의 `"experiment": true`).
- **리포트는 로컬 HTML**, 디자인은 `newsletter_upgrade/.herdr-web-ui/design-20261009-192345-8f64450b.md`(Sparta) 참고. claude.ai Artifact는 절대 쓰지 않는다(전역 지시).
- **팀 저장소(`newsletter_upgrade/`)에 커밋·푸시는 먼저 묻는다.** mentor-lab은 이 작업의 저장소라 커밋해 왔다.
- 보고·커밋은 한국어.

## 3. 칼럼 만드는 기준 방식

`scripts/column_pipeline.py` (설정: `briefs/<글>.json` — thesis·sources·title·length·r4_refs)

| 과정 | 누가 | 하는 일 |
|---|---|---|
| 과정 1 초안 | Claude (`claude -p --model opus`, 빈 폴더) | 원문 전체 + 경영일기 3편(p747·p724·p740) 문체 참고, 지킬 것 2개(원문 문장 옮기지 않기 · 없는 사실 지어내지 않기), 제목 고정 |
| 과정 2 재작성 | astra (`codex exec -m gpt-6-astra`) | "경영일기 필자(유정식)가 직접 썼다면" — 참고 2편 기본 p724·p669 |
| 과정 3 기준 반영 | astra | `briefs/standing-feedback.md`(멘토 피드백 원문)를 반영 |
| (절반) | astra | 설정 `"length": "half"`면 과정 3 뒤 절반 분량으로 줄인 과정을 더함(`--shorten`) |
| 과정 4~ 피드백 | astra | 작업실 입력창의 피드백을 파일 그대로 넘겨 반영(`--revise`). 절반 모드면 분량 유지 |

- 확정 칼럼: `columns/2026-10-08-ai-퇴근시간.md`「AI를 쓰는데도 퇴근 시간이 그대로인 이유」(과정 기록 `columns/*.process.json`, 과정 5 = 절반 957자).
- 그림: `scripts/image_candidates.py` — 머리 그림 후보(1536×1024, 3:2) / `--inline` 본문 그림 3개(astra가 문단 번호로 자리 지정, 16:9). 확정 때 고른 본문 그림을 그 문단 뒤에 넣는다.

## 4. 주제 = LLM 위키 (2026-10-10 채택)

- **왜:** 예전 "주제 뽑기"(`topic_candidates.py`, 원문 전부를 한 번에)는 회차마다 같은 주제가 되풀이됐고(15개 중 10개), "기억"을 붙인 땜질은 곁가지로 얇아졌다(40편 중 15편만). 위키는 논지 하나에 카드 하나로 남고 새 원문이 기존 주제에 쌓인다. 세 방식을 같은 원문 40편으로 블라인드 비교 → 멘토 "위키 방식이 훨씬 낫네". 자세히: `docs/2026-10-10-주제-위키-시험.md`·`.html`, 시험 기록 `wiki-eval/`.
- **구조:** `wiki/`(OKF v0.1 형식) — 규칙 `wiki/AGENTS.md`(Astro-Han/karpathy-llm-wiki MIT 바탕), 목록 `index.md`, 이력 `log.md`, 주제 페이지 `<분야>/<주제>.md`(머리말 type·title·description·status·used_in, 논지·원문 표(경로·URL·작성자·날짜·보태는 것)·쓸 수 있는 각도·함께 볼 주제).
- **명령:** `python3 -I scripts/wiki.py --ingest`(남은 원문 넣기) · `--lint`(같은 논지 합치기·점검) · `--claim <페이지>`(고르자마자 글 만들기, LLM 없음) · `--brief <페이지> <글>`(그 주제 원문만 깊게 읽고 설정 다듬기) · `--status`.
- **원문 보호:** astra를 `wiki/` 안에서만 쓰기 가능한 샌드박스로 돌린다(`-s workspace-write -C wiki`) — 원문 폴더는 읽기 전용으로 막힘(시험 확인).
- **현재:** 원문 53편 넣음(경영일기 46편은 문체 참고라 제외), 주제 페이지 26개, 남은 원문 0.
- 넣기·정리·고르기마다 `wiki/`만 git에 자동 커밋된다(위키 변화가 기록으로 남음).

## 5. 작업실 웹앱

- **실행:** `cd mentor-lab/app && npm run build` → `cd .. && python3 -I scripts/studio_server.py 8771`. Windows: `setup-windows.cmd`(설치·빌드, 다시 돌려도 됨) → `start-windows.cmd`(README 'Windows에서 처음 설치'). 서버가 버튼을 기존 명령(`column_pipeline.py`·`wiki.py`·`image_candidates.py`·`collect.py`)에 잇기만 한다. 작업 기록 `runs/studio/`(jobs.json·logs·chat).
- **화면:**
  - 서재 — 원문 카드(Threads·LinkedIn·경영일기), 입력창 + "aside 수집"(비우면 Threads·LinkedIn 자동), 수집 기록 줄.
  - 주제 — 위키 주제 지도(분야별, 카드마다 원문 수·new·상태). "이 주제로" → 즉시 글 생성 후 그 글로 이동, 깊게 읽기 → 제목 후보가 이어서 돈다. 쓴 주제는 "다시". "넣기 N"·"정리". 예전 회차는 맨 아래 접힘.
  - 글 — 탭 제목/과정/그림/확정, 위쪽 줄 "다시 쓰기"(같은 설정으로 새 글 `<글>-rN`, 두 번 눌러 실행)·기본/절반. 과정 탭은 지금 과정 하나만 크게, 지난 과정은 최신순 접기. 아래 입력창 = 제목 탭에선 제목/진행자(제목: 다시 뽑을 때 astra에게 같이 보낼 말 — 원문 그대로 + 앞 회차 후보, 회차마다 `runs/titles0/<글>/message[-N].txt`), 과정 탭에선 피드백/진행자(Claude, 글마다 `--resume` 세션).
  - 진행 중 카드(Working) — 단계·경과 시간·실시간 진행(Claude 초안은 쓰이는 글, 그 밖에는 AI Loading에 실제 로그 줄), 카드 아래 "로그". 왼쪽 메뉴 터미널 아이콘 = 전체 로그 창.
  - 모든 버튼: 누르는 즉시 맨 위 진행 막대, 실패는 오른쪽 위 알림. 라이트/다크(BoardUI ThemeToggle, 메뉴 맨 아래).
- **컴포넌트 출처:** Aceternity UI(사이드바·벤토·Glowing·Vanish Input·Spotlight·Tabs·Expandable Card·Aurora·Focus Cards·Background Beams·Card Hover·Multi Step Loader·Hover Border Gradient) · Kokonut UI(AI Prompt·AI Text Loading·Particle Button·AI Loading) · BoardUI(ThemeToggle) · shadcn(Drawer·Accordion·Dropdown). 21st.dev 레지스트리는 로그인(API 키) 필요해 원저자 공개 레지스트리에서 받았다. 출처표 `README.md`.
- **보안:** localhost와 Tailscale 주소에만 붙음(LAN 차단), Host·Origin 확인, POST는 JSON만, 글 이름·경로 검사. 진행자는 Bash를 쓰는 Claude라 이 차단이 중요하다.
- 리포트·블라인드 비교도 이 서버에서: `/docs/…`, `/wiki-eval/report/…`.

## 6. 수집 (aside)

- `scripts/collect.py "<요청>"` — aside UltraBrowse(`aside-win exec --host local --effort ultrabrowse`)로 주소만 받고, 글마다 REPL 스냅샷 → 파서로 원문 그대로 저장(`sources/originals/<사이트>/NN.md`). 개수 상한 없음, 이미 있는 주소는 건너뜀. 요청이 비면 자동(Threads·LinkedIn, 이미 모은 주소 제외 목록을 함께).
- Threads는 화면 밖 글을 문서에서 내리므로 끝까지 내려가며 여러 장 찍고 "답글 보기"를 펼친다(`parse_threads.py`가 합침). 12편 재수집: 본문 동일, 작성자 답글 33 → 81.
- LinkedIn 날짜가 직함 끝에 붙어 오는 경우 떼어 냄(`parse_linkedin.py`). 경영일기는 `column_pipeline.py --fetch-infuture <번호>`.
- 수집이 끝나면 위키 넣기가 저절로 이어진다.

## 7. 운영 주의 (겪은 것)

- **작업실 서버는 돌고 있는 작업이 없을 때만 재시작한다.** 재시작하면 진행 중 작업의 추적·후처리(수집 뒤 위키 넣기, 쓰기 뒤 제목 등)가 끊긴다(2026-10-10 한 번 끊음 — 결과는 남았지만 넣기는 수동으로 불렀다). 확인: `curl -s localhost:8771/api/jobs`의 running.
- 화면 코드만 바꿨으면 `npm run build`만 하면 된다(재시작 불필요). 서버 코드(`studio_server.py`)를 바꾸면 재시작해야 적용.
- astra·Claude 호출은 **프롬프트를 표준입력으로**(인자로 넘기면 원문 40편에서 128KB 한도 초과로 즉시 실패했다). `codex exec … -o out.md -` + stdin.
- astra 터널: opencodex 프록시 127.0.0.1:10100 · 허브 터널 127.0.0.1:37369 — 끊기면 503 "link tunnel unavailable".
- 설치한 외부 컴포넌트는 데모용이라 손을 봐야 한다 — Kokonut Particle Button은 `onClick`을 부르지 않아 '쓰기'·'확정'이 화면에서 안 됐었다(고침). **버튼은 서버 직접 호출만 말고 화면에서 눌러 시험할 것**(aside로 Windows 브라우저 조작 가능).
- 그림 비율: 머리 그림 3:2(허용 0.2), 본문 그림 16:9 — astra가 설명에 비율을 쓰면 gti가 그 비율로 그린다.
- **Windows:** 파이썬은 `-X utf8`로 돌린다(기본 cp949면 한글 지시문이 깨짐 — 작업실은 하위 실행에 붙여 줌). 화면·설정에 저장하는 경로는 `/`로(`as_posix()`), npm으로 깐 `codex`는 `codex.cmd`라 `shutil.which`로 찾는다. codex 샌드박스(`-s read-only`·위키의 `workspace-write` 원문 보호)는 리눅스에서만 확인됨.
- `pgrep -f`로 기다릴 때 자기 명령줄까지 잡혀 끝나지 않는 일이 있었다 — PID로 기다릴 것.

## 8. 알려진 문제·아직 확인 못 한 것

- 확정 시 위키 주제에 "씀" 표시 — 코드만, 실제 확정으로는 아직 안 돌려 봄.
- 수집 뒤 자동 넣기 — 서버 후처리 경로로는 아직 한 번도 끝까지 안 봄(끊긴 수집 뒤 넣기는 수동 호출).
- "다시 쓰기" — 설정 만들기까지만 확인, 실제 재작성 미실행.
- Claude 생각 단계는 끝날 때 한 덩어리로 와서, 생각하는 동안에는 "Claude 생각 중"과 경과 시간만 보인다.
- 위키: 원문 1편짜리 주제가 여럿(재료 보강·정리 대상), log.md에 같은 원문이 두 번 적힌 줄이 있음. 수백 편 규모는 미시험 — 그때 검색 보조(qmd 등) 검토.
- LinkedIn 글에 작성자가 단 댓글은 아직 수집하지 않음.
- 짧은 시험 프롬프트에서 Claude 출력 맨 앞에 영어 한 줄("Simple creative task…")이 붙은 적이 있음 — 기존 초안들에는 없었지만 지켜볼 것.

## 9. 커밋 안 된 것 (멘토가 작업실에서 시험하며 만든 것 — 손대지 않음)

`briefs/w-20261010-043541.json`(AI 제안서…, 제목 후보 회차 여러 개) · `briefs/w-20261010-043840.json`(“이게 아니네, 다시!”를 반복하는 이유 — 과정 1~4 절반까지 씀) · 확정 칼럼의 절반판(`columns/2026-10-08-ai-퇴근시간-절반.md`, process.json 변경) · `runs/collect/20261010-043454/`(자동 수집 13편) · `runs/columns/w-*`·`runs/studio/` 기록. 멘토 확인 뒤 커밋.

## 10. 떠 있는 것·남은 것

- 서버: `studio_server.py 8771`(작업실), `http.server 8770`(예전 비교 화면 `view/`) — 8824·8825·8765는 다른 작업의 것.
- 워크트리: `mentor-lab-wt/{base,yoonmoon,im-not-ai,avoid-ai-writing,fluent-korean}`(스킬 시험), `mentor-lab-wt/wiki`(위키 시험 — master에 합침, 깊게 읽기 시험 커밋이 더 있음). 필요 없으면 `git worktree remove --force ../mentor-lab-wt/<이름> && git branch -D wt/<이름>`.
- 스킬: `~/.claude/skills/god-tibo-imagen` → `~/.codex/skills/god-tibo-imagen` 링크 추가, god-tibo-imagen·lesson-imagegen SKILL.md에 gpt-6-astra 고정 명시.

## 11. 다음에 할 만한 것

1. 멘토가 고른 주제로 한 편 끝까지(제목 → 과정 → 피드백 → 그림 → 확정) 돌려 "확정 → 위키 씀", 본문 그림 삽입을 실제로 확인.
2. 위키 정리(lint) 결과를 화면에서 보여 주기(지금은 log.md에만), 원문 1편짜리 주제 묶기.
3. 팀(멘티)에게 전할 것 정리 — 기준 방식·위키 방식이 팀 저장소 방식과 무엇이 다른지(팀 저장소 반영은 멘토 확인 뒤).

## 12. 기록 위치

- 결정·근거: `docs/2026-10-10-주제-위키-시험.{md,html}`, `criteria.md`(멘토 기준 1~13), `interview.md`, `README.md`(작업실·컴포넌트 출처), `runs/README.md`(초기 실험), `runs/studio/selftest-20261009/`(버튼 시험 기록), `runs/studio/llm-wiki-oss-조사-20261010.md`(오픈소스 8개 비교).
- Claude 메모리(`~/.claude/projects/-home-hwjoo-01-projects-2026-mentoring-skens-newsletter-upgrade/memory/`): user-mentor-role · mentor-lab-experiment · standard-r4-astra · feedback-titles-astra · feedback-app-design · feedback-gti-astra · project-topic-wiki · feedback-write-naturally · feedback-use-references · reference-model-runs 등.
