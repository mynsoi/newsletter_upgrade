-- 004_fetched_by.sql — 문서 확보 수단 기록 (rss|api|html|browse 등)
-- summary_only 문서가 브라우저 전문 등으로 격상될 때 어떤 경로로 확보했는지 남긴다.
ALTER TABLE documents ADD COLUMN fetched_by TEXT;
