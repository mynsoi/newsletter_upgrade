# migrations/drafts — 사람이 직접 실행하는 초안

이 폴더의 SQL은 **자동 적용되지 않는다**. `src/db.py`의 `migrate()`는 `migrations/*.sql`만 읽는다
(하위 폴더 제외). 일일 워크플로(`collect.yml`의 `make init`)가 그 목록을 매일 운영 DB에 적용하므로,
여기 있는 파일을 `migrations/` 바로 아래로 옮기면 다음 날 06:00 KST에 운영 DB에서 실행된다.
옮기지 않는다. 실행은 Supabase SQL Editor에서 사람이 단계별로 한다.

## 011_reclaim_claims_space.sql — claims 용량 회수

### 배경 (2026-11-10)

claim 추출·claim 임베딩을 없앴다. 이제 enrich 단계는 판별 → enriched/rejected → 문서 카드 →
카드 임베딩만 한다. claims를 읽던 아티클 기능(/topics·/draft 증거 검색·verify_article·
인용 원장·이론 카드 색인)도 지웠다. 칼럼 작업실은 claims를 읽지 않는다(11/10 조사).

11/10 읽기 전용 실측:

| 항목 | 크기·건수 |
|---|---|
| DB 전체 | 391MB (무료 한도 500MB) |
| claims 합계 | 174MB = 표 77MB + `idx_claims_embedding_hnsw` 72MB + `idx_claims_text_trgm` 21MB + 기타 인덱스 4MB |
| claims 행 | 53,970건 (벡터 있는 행 36,097건 · 이론 카드 claim 629건) |
| article_sources | 23행, 아티클 1편(`ai-productivity-paradox`)이 claim 18건을 가리킴 |

### 실행 전 조건

1. 이 변경(브랜치 `remove-claim-extraction`)이 `main`에 머지돼 있어야 한다.
   순서가 바뀌면 옛 `embed.py`가 `claims.embedding`에 쓰려다 일일 수집이 실패한다.
2. 머지 뒤 일일 수집이 한 번 이상 성공한 것을 확인한다(Actions `daily-collect` 초록,
   로그에 "판별 통과 …건"과 "카드 …조각"이 찍힘).

### 단계

| 단계 | 내용 | 회수 | 되돌리기 |
|---|---|---|---|
| 1 | HNSW·trgm 인덱스, `search_claims()` 함수, `claims.embedding` 열 삭제 | 인덱스 약 93MB는 즉시. 열(약 55MB)은 3단계 뒤 | 인덱스는 다시 만들 수 있다. 벡터 값은 되살릴 수 없다(다시 임베딩해야 함, 약 $0.1) |
| 2 (선택) | 원장이 가리키지 않는 claim 행 삭제 (18건만 남김) | 3단계 뒤 표 대부분 | 되돌릴 수 없다. 실행 전에 백업을 받는다(아래) |
| 3 | `VACUUM (FULL, ANALYZE) claims;` 단독 실행 | 1·2단계 삭제분이 파일에서 빠짐 | 해당 없음 |

예상 결과: 1+3단계만 하면 약 150MB, 2단계까지 하면 약 170MB를 회수한다(DB 약 220MB).
VACUUM FULL은 새 표를 다 쓴 뒤 옛 파일을 지운다. 그래서 잠깐 새 표 크기만큼 공간이 더 든다.
1단계에서 인덱스를 먼저 내리므로 순간 크기가 500MB를 넘을 일은 없다.
**3단계는 세션 풀러(포트 5432)로 접속해 실행한다.** 트랜잭션 풀러(6543)는 SET이 유지되지 않고
statement_timeout이 2분이라 VACUUM FULL이 끊긴다(2026-09-22 arXiv 벡터 정리 때 확인).
claims를 쓰는 코드가 없으므로 잠금(ACCESS EXCLUSIVE)은 문제가 되지 않는다.

확인 쿼리(각 단계 전후):

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
SELECT pg_size_pretty(pg_total_relation_size('claims'));
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
  FROM pg_stat_user_indexes WHERE relname = 'claims';
```

2단계 전 백업(선택): 로컬에서 `pg_dump --data-only --table=claims "$DATABASE_URL" > claims-backup.sql`.
원문에서 뽑은 문장이 들어 있으니 **저장소 밖**에 둔다(저장소는 Public).

### article_sources FK와 발행본 2편의 인용

- `article_sources.claim_id → claims(id)` FK 때문에, 원장이 가리키는 claim은 2단계 DELETE에서
  남는다. 남는 것은 `ai-productivity-paradox`가 가리키는 18건이다. FK는 그대로 둔다.
- 발행본 2편(`content/published/`)은 본문 문단 뒤 `<!-- claims: ID, … -->` 주석으로 claim ID를
  적어 두었다. 인용 문장의 사본은 `content/evidence/{slug}.json`의 `claims[].text`에 있다.
  - `ai-productivity-paradox`: 고유 ID 18건, 18건 모두 evidence json에 있음. 원장 23행.
  - `psych-safety-ai-experiment`: 고유 ID 14건, 13건이 evidence json에 있음. 원장에는 없음
    (기록 단계가 생기기 전 발행). 나머지 1건은 json에 없는 ID다. 2단계를 하면 DB에서 사라진다.
  - 발행된 글(웹·메일)에는 claim ID가 나오지 않는다. 발행 도구가 주석을 지운다(`web/server.py`).
    그래서 행을 지워도 발행물은 바뀌지 않는다. 잃는 것은 "이 문단의 근거 claim 원문을 DB에서
    다시 찾는 길"뿐이고, 18+13건은 json 사본으로 대신할 수 있다.
- 다른 선택지: claims와 article_sources를 통째로 지운다
  (`DROP TABLE article_sources; DROP TABLE claims;`). 다만 `001_init.sql`이 새 DB에서 두 표를
  다시 만든다. 그러면 SQLite 테스트와 운영 스키마가 어긋난다. 그래서 이번 초안에서는 표를 남기고
  비우는 쪽을 택했다. 표를 지우려면 001의 정의도 같이 정리하는 별도 마이그레이션이 필요하다.

### 실행 기록

실행하면 여기에 날짜·단계·전후 크기를 적는다.
