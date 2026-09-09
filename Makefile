.PHONY: init validate collect collect-fast sync enrich embed embed-backfill theories stats sources-doc test handoff receive

# .venv가 있으면 그 파이썬을 사용 (Windows: Scripts/, Linux·Actions: bin/), 없으면 python3
PYTHON := $(or $(wildcard .venv/Scripts/python.exe),$(wildcard .venv/bin/python),python3)

init:
	$(PYTHON) -c "import sys; sys.path.insert(0,'src'); import db; c=db.connect(); print('적용:', db.migrate(c) or '없음(최신)')"

validate:
	$(PYTHON) src/collectors/validate_sources.py

collect:                 # rss + api 통합 수집 (하루 1회 보장 잠금 — 우회: --force)
	$(PYTHON) src/collectors/collect.py

collect-fast:            # 본문 추출 없이 피드 요약만 (빠른 동작 확인용)
	$(PYTHON) src/collectors/collect.py --no-body

sync:
	$(PYTHON) src/internal_sync.py

enrich:
	$(PYTHON) src/enrich/extract_claims.py

enrich-dry:
	$(PYTHON) src/enrich/extract_claims.py --dry-run

embed:                   # claim 임베딩 일반 실행 (embedding IS NULL, 일일 상한까지 — A6)
	$(PYTHON) src/search/embed.py

embed-backfill:          # claim 임베딩 상한 없이 잔여 전량 변환
	$(PYTHON) src/search/embed.py --backfill

theories:
	$(PYTHON) src/load_theories.py

sources-doc:             # sources.yaml → docs/소스_카탈로그.md 재생성 (md 직접 수정 금지)
	$(PYTHON) src/sources_doc.py

stats:
	$(PYTHON) src/stats.py

handoff:
	$(PYTHON) src/handoff.py

receive:
	$(PYTHON) src/handoff.py receive $(FILE)

test:
	$(PYTHON) -m pytest tests/ -q
