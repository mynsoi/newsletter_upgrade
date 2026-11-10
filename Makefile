.PHONY: init validate collect collect-fast sync enrich embed embed-backfill cards-backfill-dry stats sources-doc test handoff receive publish-ui site

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

enrich:                  # 관련성 판별 → enriched/rejected → 문서 카드 (claim 추출은 2026-11-10 제거)
	$(PYTHON) src/enrich/relevance.py

enrich-dry:
	$(PYTHON) src/enrich/relevance.py --dry-run

cards-backfill-dry:      # 문서 카드 소급(Batch) 사전 점검 — 대상·토큰·예상 비용·DB 크기 (실행: python src/enrich/backfill_cards.py)
	$(PYTHON) src/enrich/backfill_cards.py --dry-run

embed:                   # 카드 임베딩 일반 실행 (조각이 덜 찬 카드, 일일 상한까지)
	$(PYTHON) src/search/embed.py

embed-backfill:          # 카드 임베딩 상한 없이 잔여 전량 변환
	$(PYTHON) src/search/embed.py --backfill

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

publish-ui:              # 아티클 발행 도구 로컬 서버 (http://localhost:5001)
	$(PYTHON) web/server.py

site:                    # 발행물 → site/ 내보내기 + 아카이브 갱신 (make site SLUG=..., SLUG 없으면 아카이브만)
	$(PYTHON) web/site_export.py $(or $(SLUG),--index)
