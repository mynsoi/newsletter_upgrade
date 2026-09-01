# AI 시대 일하는 방식 인사이트 파이프라인

외부 AI·조직문화 콘텐츠(논문·컨설팅 리포트·저널·기업 자료·뉴스)를 자동 수집해 **claim(검증 가능한 주장) 단위**로 분해하고, 확립된 조직 이론과 SK 내부 자료(A등급 공개 자료)를 결합해 **다중 출처 교차 기반 인사이트 아티클을 주 1편** 만드는 반자동 파이프라인. Claude Code가 개발·실행을 담당하고, 사람은 방향 선택과 최종 승인만 맡는다.

**현재 상태 (2026-09-03)**: Phase 1(데이터 기반 완성) — 소스 카탈로그 확정(47건), Supabase 공유 DB + GitHub Actions 일일 수집 가동 중(문서 22,000+건), 이론 카드 30장, 내부 자료 등록 완료. claim 추출(enrich)은 API 크레딧 충전 대기로 일시 정지(`enrich_enabled: false`).

## 문서는 3개가 전부다

| 문서 | 역할 | 위치 |
|---|---|---|
| **기획서** | 설계와 결정 — 무엇을·왜 | `docs/기획서.md` |
| **실행계획·분업안** | 지금 무엇을 누가 — 체크박스가 현황판 | `docs/phase1-plan.md` |
| **저장소** | 어떻게 — 코드·운영 규칙(`CLAUDE.md`)·지시문(`prompts/`) | 이 저장소 |

파생 뷰: `docs/소스_카탈로그.md` (확정본은 `config/sources.yaml`, `make sources-doc`로 재생성 — md 직접 수정 금지).

## 아키텍처

```
GitHub Actions (매일 06:00 KST) ──collect──▶ Supabase PostgreSQL ◀── PC A / PC B (Claude Code로 작업)
   rss → api → html 순 수집, 일일 잠금,          documents · claims · internal_docs · articles
   무유입 경보(7일) → 이슈 자동 생성
```

- **수집 경로** (기획서 4.2): API(arXiv·OSF, 소급 가능) → RSS → HTML 목록 수집(A-PDF 포함) → 브라우저 보조(`/browse-collect`, Claude in Chrome — 사람이 실행하는 월간 라운드) → 유료 소스는 구독 세션에서 건별 선별 → 수기(`/ingest-url`, `/ingest-file`). 뉴스레터 인박스 경로는 폐기(2026-09-02).
- **품질 게이트**: 관련성 판별(경량 모델) → 본문 길이 임계(800자 미만 `summary_only`, API 초록형 면제) → claim 추출(지침 v2, `prompts/claim_extraction.md`) → 아티클 검증(실사용 claim 기준 출처 3곳+·상반 stance·40% 룰·수치 대조).
- **내부 자료**: A등급(공개 가능)만 등록. `internal/`의 텍스트는 아티클 생성 시 외부 API로 전송된다 — 전송돼도 되는 내용만. C등급은 색인 거부, B 표기는 전송 자동 제외(안전벨트).
- **비밀값**: `DATABASE_URL`, `ANTHROPIC_API_KEY`는 각 PC 환경변수 + GitHub Secrets에만. 어떤 파일에도 쓰지 않는다.

## 시작하기 (새 팀원)

```bash
git clone <저장소>
uv sync                          # 또는 pip install -r ...
export DATABASE_URL=...          # Supabase 연결 문자열 (없으면 SQLite 로컬 모드 — 테스트용)
export ANTHROPIC_API_KEY=...
make test                        # 네트워크 없이 76건
make init                        # 스키마 확인
claude                           # Claude Code 실행 후 /status
```

## 일상 운영 명령

| 명령 | 역할 |
|---|---|
| `make validate` | 전 소스 접속 검증 (API 질의 / RSS 4단계 / HTML 목록 링크 수) — PC·Actions 양쪽에서 |
| `make collect` | rss+api+html 통합 수집 (하루 1회 잠금, 우회 `--force`) |
| `make enrich` | 관련성 게이트 + claim 추출 (`enrich_enabled` 확인) |
| `make theories` / `make sync` | 이론 카드(reviewed만) / 내부 자료 색인 |
| `make sources-doc` | 소스 카탈로그 md 재생성 |
| `make stats` | 현황 집계 |

Claude Code 슬래시 커맨드: `/collect` `/ingest-url` `/add-theory` `/sync-internal` `/draft` `/publish` `/status` (+ 예정: `/ingest-file`, `/browse-collect`). 각 커맨드는 `.claude/commands/`의 한국어 절차서다.

## 소스 카탈로그 (47건 active)

T1 실증 연구 · T2 컨설팅/싱크탱크 · T3 저널 · T4 기업 1차 자료 · T5 뉴스(신호 감지 전용, 단독 근거 금지) · TC 이론 카드. 수집 유형: API 5 · RSS 27 · HTML 7 · 브라우저 8. 신규 편입 소스는 1개월 시험 운영 후 월간 성과 리뷰에서 재판정(추가=합의+검증+시험 / 제거=6개월 무인용 / 장애=수리→브라우저 전환→제외). 상세는 `docs/소스_카탈로그.md`.

## 협업 규칙 (2인)

- 주 단위 당번 교대. 당번은 운영(수집 점검·스팟체크·`/draft`·`/publish`), 비당번은 콘텐츠(이론 카드·내부 요지·문서). 어느 PC에서든 가능.
- 작업 시작 시 "최신 내용 받아줘", 끝낼 때 "커밋하고 푸시해줘" — Claude Code에 말로.
- 영역 분리: `src/` `migrations/` `.github/`는 인프라 담당, `knowledge/` `internal/` `prompts/` `docs/`는 콘텐츠 담당. 같은 파일을 동시에 만지지 않는다.

## 폴더

```
config/       sources.yaml(소스 확정본) · settings.yaml(모델·플래그)
src/          collectors/(rss·api·html_list·store·validate) · enrich/ · db.py · collect.py
prompts/      claim_extraction.md(v2) · relevance_gate.md · 작성 지침
knowledge/    theories/ 이론 카드 30장 (reviewed만 색인)
internal/     A등급 내부 자료 (git 제외, 템플릿·요지 목록만 추적)
content/      topics · evidence · angles · drafts · published · reports
docs/         기획서 · phase1-plan · 소스_카탈로그(파생)
eval/         루브릭 · 스팟체크 기록 · Phase 0 결과
tests/        76건
```
