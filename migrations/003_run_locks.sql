-- 003_run_locks.sql — 하루 1회 수집 보장 + claim 추출 동시성 제어
-- 실행: make init (이미 적용된 마이그레이션은 건너뜀)
--
-- 배경: 수집은 GitHub Actions·개발 PC 어디서든 트리거될 수 있다. 중복 수집과
--       같은 문서에 대한 claim 추출 동시 실행을 DB 레벨 잠금으로 막는다.
-- SQLite / PostgreSQL 공통 구문 (방언 마커 불필요).

-- 하루치 수집 실행 기록 겸 잠금. run_date PK 가 "하루 1회" 를 강제한다.
--   status: running   — 선점됨, 진행 중
--           completed  — 정상 종료 (재실행 불필요)
--           failed     — 도중 실패 (다음 실행이 자동 재시도)
CREATE TABLE IF NOT EXISTS collection_runs (
  run_date    DATE PRIMARY KEY,
  host        TEXT,
  status      TEXT NOT NULL DEFAULT 'running'
              CHECK (status IN ('running', 'completed', 'failed')),
  started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP
);

-- claim 추출 문서 단위 잠금. NULL = 미선점.
-- claim_document_for_enrich() 가 원자적 UPDATE(status='new' AND 잠금 없음/만료)로 선점하고,
-- 정상 완료 시 status='enriched' 와 함께 NULL 로 정리한다. 크래시 시 reclaim_hours 후 회수.
ALTER TABLE documents ADD COLUMN enrich_locked_at TIMESTAMP;
