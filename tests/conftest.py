"""테스트는 운영 DB에 붙지 않는다 (2026-11-11).

개발 PC 환경에는 운영 Supabase 주소(DATABASE_URL)가 들어 있다. 그대로 pytest를 돌리면 PostgreSQL 테스트가
운영 DB에 시험 행을 쓰고 migrate()까지 돌린다 — 2026-10-28에 이 일로 마이그레이션이 계획보다 먼저 적용됐다.
그래서 테스트 세션 시작 때 DATABASE_URL을 환경에서 빼 둔다(모든 테스트는 SQLite 모드).
PostgreSQL 테스트는 시험용 DB 주소를 TEST_DATABASE_URL로 따로 줄 때만 돈다(각 테스트가 DATABASE_URL로 넣는다).
"""
import os

os.environ.pop("DATABASE_URL", None)
