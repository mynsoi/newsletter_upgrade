"""수집 대상 선정 — status가 active인 소스만 (2026-10-01 회귀 테스트).

월간 소스 리뷰(9/30)에서 excluded로 바꾼 mk-economy·chosun-economy·arxiv-cs-si가 다음 날
Actions 수집에서 그대로 수집됐다(87건). rss·api·html_list가 type만 보고 대상을 골랐기 때문이다.
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

SOURCES = [
    {"id": "rss-on", "type": "rss", "status": "active", "tier": "T5", "name": "a", "feed_url": "x"},
    {"id": "rss-off", "type": "rss", "status": "excluded", "tier": "T5", "name": "b", "feed_url": "x"},
    {"id": "api-on", "type": "api", "status": "active", "tier": "T1", "name": "c"},
    {"id": "api-off", "type": "api", "status": "excluded", "tier": "T1", "name": "d"},
    {"id": "html-on", "type": "html", "status": "active", "tier": "T1", "name": "e", "list_url": "x"},
    {"id": "html-off", "type": "html", "status": "excluded", "tier": "T2", "name": "f", "list_url": "x"},
    {"id": "nl-off", "type": "newsletter", "status": "excluded", "tier": "T1", "name": "g"},
]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith("collectors"):
            del sys.modules[mod]
    import db
    import handoff
    monkeypatch.setattr(handoff, "ensure_active", lambda *a, **k: None)
    conn = db.connect()
    db.migrate(conn)
    conn.close()
    path = tmp_path / "sources.yaml"
    path.write_text(yaml.safe_dump({"sources": SOURCES}, allow_unicode=True), encoding="utf-8")
    return path


def test_select_targets_keeps_only_active(env, capsys):
    from collectors.rss import select_targets
    assert [s["id"] for s in select_targets(SOURCES, "rss")] == ["rss-on"]
    assert [s["id"] for s in select_targets(SOURCES, "api")] == ["api-on"]
    assert [s["id"] for s in select_targets(SOURCES, "html")] == ["html-on"]
    assert "rss-off" in capsys.readouterr().out       # 건너뛴 사실을 알린다


def test_explicit_source_id_does_not_revive_excluded(env):
    from collectors.rss import select_targets
    assert select_targets(SOURCES, "rss", ["rss-off"]) == []
    assert [s["id"] for s in select_targets(SOURCES, "rss", ["rss-off", "rss-on"])] == ["rss-on"]


@pytest.mark.parametrize("module,on_id", [
    ("collectors.rss", "rss-on"),
    ("collectors.api", "api-on"),
    ("collectors.html_list", "html-on"),
])
def test_each_collector_run_skips_excluded(env, monkeypatch, module, on_id):
    """세 수집기의 run()이 실제로 이 조건을 거친다 — 퇴출 소스의 collect_source가 불리지 않는다."""
    import importlib
    mod = importlib.import_module(module)
    monkeypatch.setattr(mod, "SOURCES_PATH", env)
    called = []

    def fake_collect(s, conn, client, *a, **k):
        called.append(s["id"])
        return {"seen": 0, "new": 0, "dup": 0, "failed": 0, "up": 0, "robots": 0}
    monkeypatch.setattr(mod, "collect_source", fake_collect)
    mod.run(force=True)
    assert called == [on_id]
