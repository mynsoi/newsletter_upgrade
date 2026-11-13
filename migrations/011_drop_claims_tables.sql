-- 011_drop_claims_tables.sql — claims·article_sources 표 삭제 (2026-11-13)
--
-- 배경: 2026-11-10 claim 추출·claim 임베딩을 없앴고(PR #19), claims를 읽던 아티클 기능
-- (/topics·/draft 증거 검색·verify_article·인용 원장·이론 카드 색인)도 함께 지웠다.
-- 칼럼 작업실(column-studio)은 claims·article_sources를 읽지 않는다(11/13 다시 확인).
-- 11/11 용량 회수(migrations/drafts/011_reclaim_claims_space.sql 1·3단계)로 벡터·인덱스는 이미 지웠고,
-- 남은 것은 행(claims 53,970건 18MB · article_sources 23건)뿐이다.
-- 운영 DB에서 두 표에 기대는 함수·뷰는 없다(11/13 확인). article_sources → claims·articles FK만 있다.
--
-- 백업: 삭제 전 claims·article_sources·articles를 CSV로 받아 git 밖에 뒀다
-- (메인 폴더 data/backups/2026-11-13-claims-drop/ — 원문에서 뽑은 문장이 들어 있어 Public 저장소에 올리지 않는다).
-- articles 표(발행 기록 1행)는 남긴다.
--
-- 순서: article_sources가 claims를 가리키므로 먼저 지운다.

DROP TABLE IF EXISTS article_sources;
DROP TABLE IF EXISTS claims;
