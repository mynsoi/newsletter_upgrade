# AI 시대 일하는 방식 인사이트 파이프라인

AI·조직문화 콘텐츠를 수집·교차해 주 1편 인사이트 아티클을 만드는 파이프라인.
**현재 Phase 1** — 실행 계획·분업: `docs/phase1-plan.md` / 운영 규칙: `CLAUDE.md` / 전체 설계: `docs/기획서.md`(v0.15)
Phase 0 결과: 아티클 1편(content/published/), 이론 카드 5장. 데이터는 Supabase 공유 DB에 재수집으로 구축한다(git에 데이터 없음). **시작은 docs/phase1-plan.md 0단계부터.**

## 시작하기

```bash
# 의존성 (uv 권장, pip도 가능)
uv sync                # 또는: pip install feedparser trafilatura httpx pyyaml anthropic pytest

make init              # DB 초기화
make test              # 동작 확인 (네트워크 불필요)
```

## Phase 0 체크리스트 (기획서 부록 A 대응)

| # | 작업 | 방법 | 상태 |
|---|---|---|---|
| 1 | 보안 검토 요청서 제출 | `docs/보안검토요청서_초안.md`를 사내 양식에 이관 후 제출 (**첫 주 내**) | ☐ 사람 |
| 2 | 유료 구독 계약 | HBR·MIT SMR·DBR 구독 + 뉴스레터 수집용 전용 메일 계정 생성 | ☐ 사람 |
| 3 | 소스 10개 등록·검증 | `config/sources.yaml` 확인 → `make validate` → 실패 URL 수정 | ☐ |
| 4 | 최근 3개월 수집 | `make collect` (빠른 확인은 `make collect-fast`) → `make stats` | ☐ |
| 5 | claim 추출 + 스팟체크 | `export ANTHROPIC_API_KEY=...` → `make enrich` → `eval/claim_spotcheck.md` 절차 | ☐ |
| 6 | 내부 자료 등록 | A등급 3건을 `internal/*/`에 템플릿 형식으로 저장 → `make sync`. B등급 후보는 `internal/B등급_투입후보목록.md`에 목록만 | ☐ |
| 6-1 | 이론 카드 5장 (★표시) | Claude Code에서 `/add-theory <이론명>` → 초안 검수 → status: reviewed → `make theories` | ☐ |
| 7 | 아티클 1편 수동 제작 | Claude Code에서 `/draft <주제>` — 증거수집→앵글→초안→검증을 단계별 확인하며 진행 | ☐ |
| 8 | 루브릭 채점·보고 | `eval/rubric.md` 8항목 채점 → 의사결정 회의 제출 | ☐ |

## Claude Code 슬래시 커맨드

| 커맨드 | 용도 |
|---|---|
| `/collect` | 소스 검증 + 수집 + 결과 보고 |
| `/ingest-url <URL>` | 발견한 자료 수기 등록 (티어 자동 판단) |
| `/sync-internal` | 내부 자료 재색인 (C등급 자동 거부) |
| `/add-theory <이론명>` | 이론 카드 초안 생성 → 사람 검수 후 색인 (draft는 색인 거부) |
| `/draft <주제>` | Phase 0 수동 아티클 제작 절차 (단계별 확인) |
| `/publish <slug>` | 승인 체크리스트 + 승인/반려 처리 |
| `/status` | 현황 요약 (교대 인수인계용) |

## 보안 관련 동작 (기획서 4.1)

- `security: C` 파일은 색인 코드가 **본문을 읽지 않고 거부**합니다.
- `security: B` 파일은 색인되지만, `config/settings.yaml`의 `b_grade_api_approved: false`(기본값)인 동안
  **외부 API 전송 대상에서 자동 제외**됩니다. 보안 검토 승인 후에만 플래그를 변경하고,
  커밋 메시지에 승인 근거(문서번호)를 남깁니다.
- `data/`와 `internal/` 본문은 `.gitignore`로 버전관리에서 제외됩니다.

## 디렉토리

```
.claude/commands/   운영 인터페이스 (슬래시 커맨드)
config/             sources.yaml(소스 카탈로그) · settings.yaml(승인 플래그·모델)
migrations/         DB 스키마 (번호 순 SQL)
knowledge/theories/ 전통 HR·조직 이론 카드 (정전 지식베이스 — 기획서 3.5)
prompts/            claim 추출 프롬프트 · 금지 상투구 목록
src/                collectors(rss·validate·ingest) · enrich(claim 추출) · internal_sync · stats
internal/           내부 자료 (템플릿 + B등급 후보 목록)
content/            파이프라인 산출물 (topics/evidence/angles/drafts/published/rejected)
eval/               품질 루브릭 · 스팟체크 절차
docs/               보안 검토 요청서 초안 (+ 기획서 사본 배치 권장)
```
