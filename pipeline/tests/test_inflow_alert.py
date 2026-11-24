"""무유입 경보를 이슈에 어떻게 남길지(src/collectors/inflow_alert.py, 2026-11-24)."""
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collectors.inflow_alert import decide, main  # noqa: E402

NOW = datetime(2026, 11, 24, 1, 0, tzinfo=timezone.utc)
DONE = "수집 완료로 기록됨 (collection_runs 2026-11-24)\n"
CHARTER = "[무유입 경보] charter — 15일째 신규 유입 없음 (기준 14일)\n"
BAIN = "[무유입 경보] bain-insights — 유입 기록 없음 (기준 7일)\n"


def issue(*comments, body="", created="2026-09-14T00:00:00Z"):
    return {"createdAt": created, "body": body,
            "comments": [{"createdAt": at, "body": text} for at, text in comments]}


def act(log, iss=None):
    return decide(log, iss or {}, NOW)[0]


def test_first_alert_posts():
    assert act(CHARTER + DONE) == "post"
    assert act(CHARTER + DONE, issue(("2026-11-23T00:00:00Z", "사람이 단 댓글"))) == "post"


def test_same_source_within_a_week_is_skipped():
    told = issue(("2026-11-22T23:40:00Z", "## 소스 무유입 경보\n```\n" + CHARTER + "```"))
    assert act(CHARTER + DONE, told) == "skip"


def test_same_source_after_a_week_posts_again():
    told = issue(("2026-11-16T23:40:00Z", CHARTER))
    assert act(CHARTER + DONE, told) == "post"


def test_new_source_posts_even_if_recent():
    told = issue(("2026-11-23T23:40:00Z", CHARTER))
    assert act(CHARTER + BAIN + DONE, told) == "post"
    assert "bain-insights" in decide(CHARTER + BAIN + DONE, told, NOW)[1]


def test_latest_post_wins_and_issue_body_counts():
    # 본문(9월)에는 다른 소스, 어제 댓글에 charter — 어제 것을 기준으로 본다
    told = issue(("2026-11-23T00:00:00Z", CHARTER), body=BAIN)
    assert act(CHARTER + DONE, told) == "skip"
    assert act(BAIN + DONE, told) == "post"
    assert act(CHARTER + DONE, issue(body=CHARTER, created="2026-11-23T00:00:00Z")) == "skip"


def test_no_alert_closes_only_when_check_ran():
    assert act(DONE) == "close"
    assert act("오늘(2026-11-24) 수집 완료됨 — 재수집하려면 --force\n") == "none"
    assert act("수집 실패로 기록됨 (collection_runs 2026-11-24)\n") == "none"
    assert act("[경보 점검 실패] OperationalError: x\n" + DONE) == "none"
    assert act("") == "none"


def test_main_reads_log_and_stdin(tmp_path, monkeypatch, capsys):
    log = tmp_path / "collect.log"
    log.write_text(CHARTER + DONE, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    assert main([str(log)]) == 0
    assert capsys.readouterr().out.startswith("post ")
    monkeypatch.setattr(sys, "stdin", io.StringIO("깨진 json"))
    assert main([str(tmp_path / "없는파일.log")]) == 0
    assert capsys.readouterr().out.startswith("none ")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(issue(("2099-01-01T00:00:00Z", CHARTER)))))
    assert main([str(log)]) == 0
    assert capsys.readouterr().out.startswith("skip ")
