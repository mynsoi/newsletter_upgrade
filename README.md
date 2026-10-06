# AI 시대 일하는 방식 인사이트 파이프라인

외부 AI·조직문화 콘텐츠(논문·컨설팅 리포트·저널·기업 자료·뉴스)를 자동 수집해 **claim(검증 가능한 주장) 단위**로 분해하고, 확립된 조직 이론과 SK 내부 자료(공개 가능 판단이 끝난 자료)를 결합해 **다중 출처 교차 기반 인사이트 아티클을 주 1편** 만드는 반자동 파이프라인. Claude Code가 개발·실행을 담당하고, 사람은 방향 선택과 최종 승인만 맡는다.

**현재 상태 (2026-10-07)**: Phase 2(집필 자동화 + 발행 기반) — Phase 1은 2026-09-07 종료. Supabase 공유 DB + GitHub Actions 일일 수집·claim 추출·임베딩 가동 중(문서 27,000+건 · claim 27,000+건), 의미 검색(pgvector)·토픽 발굴 자동화·세그먼트 레이어 구조 확정, 로컬 발행 도구(웹 UI·이미지 메일)와 Vercel 정적 배포 구성 완료. 창간호는 2026-10-06 팀장 피드백으로 **칼럼 포맷 전환** 후 재제작 중 — 창간 목표 **10/22(목)**. 상세는 `docs/phase2-plan.md`.

## 문서는 3개가 전부다

| 문서 | 역할 | 위치 |
|---|---|---|
| **기획서** | 설계와 결정 — 무엇을·왜 | `docs/기획서.md` |
| **실행계획** | 지금 무엇을 누가 — 현황판 | `docs/phase2-plan.md` (Phase 1 기록: `docs/phase1-plan.md`) |
| **저장소** | 어떻게 — 코드·운영 규칙(`CLAUDE.md`)·지시문(`prompts/`) | 이 저장소 |

파생 뷰: `docs/소스_카탈로그.md` (확정본은 `config/sources.yaml`, `make sources-doc`로 재생성 — md 직접 수정 금지).

## 아키텍처

```
GitHub Actions (매일 06:00 KST) ──collect·enrich·embed──▶ Supabase PostgreSQL ◀── PC (Claude Code로 작업)
   rss → api → html 순 수집, 일일 잠금,                      documents · claims(halfvec 임베딩) · internal_docs
   무유입 경보(7일) → 이슈 자동 생성                           articles · article_sources(인용 원장)

아티클: /topics → /draft(-layers) → /publish → 로컬 발행 도구(web/) → .eml 이미지 메일 + Vercel 정적 사이트(site/)
```

- **수집 경로** (기획서 4.2): API(arXiv·OSF, 소급 가능) → RSS → HTML 목록 수집(A-PDF 포함) → 브라우저 보조(`/browse-round` 월간 라운드, `/browse-collect` 건별) → 유료 소스는 구독 세션에서 건별 선별 → 수기(`/ingest-url`, `/ingest-file`). 뉴스레터 인박스 경로는 폐기(2026-09-02).
- **품질 게이트**: 관련성 판별(경량 모델) → 본문 길이 임계(800자 미만 `summary_only`, API 초록형 면제) → claim 추출(지침 v2, `prompts/claim_extraction.md`) → 아티클 검증(`src/verify_article.py` — 실사용 claim 기준 출처 3곳+·상반 stance·40% 룰·수치 대조). T5 뉴스 요약분 claim은 `from_summary=1`로 토픽 신호에만 쓰고 증거에서는 제외.
- **내부 자료**: 공개 가능 판단이 끝난 자료만 등록(등급 체계는 2026-09-03 폐지). `internal/`의 텍스트는 아티클 생성 시 외부 API로 전송된다 — 전송돼도 되는 내용만("사보에 실려도 되는가").
- **비밀값**: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`(임베딩·이미지)는 각 PC 환경변수 + GitHub Secrets에만. 어떤 파일에도 쓰지 않는다.

## 시작하기 (새 팀원)

```bash
git clone <저장소>
uv sync                          # 또는 pip install -e .
export DATABASE_URL=...          # Supabase 연결 문자열 (없으면 SQLite 로컬 모드 — 테스트용)
export ANTHROPIC_API_KEY=...
make test                        # 네트워크 없이 259건 (Postgres 전용 3건은 로컬 모드에서 skip)
make init                        # 스키마 확인
claude                           # Claude Code 실행 후 /status
```

## 일상 운영 명령

| 명령 | 역할 |
|---|---|
| `make validate` | 전 소스 접속 검증 (API 질의 / RSS 4단계 / HTML 목록 링크 수) — PC·Actions 양쪽에서 |
| `make collect` | rss+api+html 통합 수집 (하루 1회 잠금, 우회 `--force`) |
| `make enrich` | 관련성 게이트 + claim 추출 (`enrich_enabled` 확인, 일일 상한 400) |
| `make embed` | claim 임베딩 증분 (arXiv는 6개월 보존 후 자동 비움) |
| `make topics` | 토픽 발굴 → `content/topics/YYYY-WW.md` |
| `make theories` / `make sync` | 이론 카드(reviewed만) / 내부 자료 색인 |
| `make citations` | 소스별 인용 횟수 (월간 소스 리뷰용) |
| `make publish-ui` | 로컬 발행 도구 (http://localhost:5001, Windows는 `발행도구.bat`) |
| `make site SLUG=...` | 발행물 → `site/` 정적 내보내기 (Vercel 배포) |
| `make sources-doc` | 소스 카탈로그 md 재생성 |
| `make stats` | 현황 집계 |

Claude Code 슬래시 커맨드: `/collect` `/status` `/topics` `/draft` `/draft-layers` `/publish` `/publish-ui` `/ingest-url` `/ingest-file` `/browse-collect` `/browse-round` `/add-theory` `/sync-internal`. 각 커맨드는 `.claude/commands/`의 한국어 절차서다. (`/handoff` `/receive`는 폐기 — 비상용으로만 남김.)

## 소스 카탈로그 (41건 active)

T1 실증 연구 · T2 컨설팅/싱크탱크 · T3 저널 · T4 기업 1차 자료 · T5 뉴스(신호 감지 전용, 단독 근거 금지) · TC 이론 카드. 2026-09 월간 리뷰로 정식 23 · 연장 7(2026-12-31 재판정) · 퇴출·휴면 7. 판정은 `make citations` 인용 원장 기준. 상세는 `docs/소스_카탈로그.md`, 리뷰 기록은 `content/reports/source-review-2026-09.md`.

## 협업 규칙 (2인)

- Phase 2는 개발 단계라 당번 미지정 — 작업자가 유동적으로 진행.
- 작업 시작 시 "최신 내용 받아줘", 끝낼 때 "커밋하고 푸시해줘" — Claude Code에 말로.
- 영역 분리: `src/` `migrations/` `.github/` `web/`는 인프라 담당, `knowledge/` `internal/` `prompts/` `docs/`는 콘텐츠 담당. 같은 파일을 동시에 만지지 않는다.
- 머지 규칙: 머지 전 상호 통지 + `make test` 통과 필수.

## 폴더

```
config/       sources.yaml(소스 확정본) · settings.yaml(모델·플래그·web_base_url)
src/          collectors/(rss·api·html_list·pubdate·store·validate) · enrich/ · search/(embed·semantic) · topics/
              db.py · verify_article.py · article_ledger.py · internal_sync.py · load_theories.py
migrations/   001~008 (pgvector halfvec · from_summary)
prompts/      article_style.md(문체 정본) · segment_layers.md · claim_extraction.md · relevance_gate.md · glossary_internal.md
knowledge/    theories/ 이론 카드 77장 (reviewed만 색인)
internal/     공개 가능 내부 자료 (git 제외, 템플릿·등록 목록만 추적)
content/      topics · evidence · angles · drafts · published · rejected(사유 README) · reports
web/          발행 도구 — server.py(웹 UI) · email_renderer.py(.eml 이미지 메일) · site_export.py · fonts/
site/         Vercel 정적 배포 산출물 (noindex)
output/       로컬 산출물 (git 제외) — launch-review/ 창간호 컨펌 패키지
docs/         기획서 · phase1-plan · phase2-plan · 소스_카탈로그(파생)
eval/         루브릭 · 채점표(scores/) · 스팟체크·레이어 테스트·문체 피드백 기록
tests/        259건
```
