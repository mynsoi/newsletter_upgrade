"""무유입 경보를 이슈에 어떻게 남길지 정한다 (2026-11-24).

그전에는 경보가 있는 날마다 열린 이슈에 댓글을 달았고 이슈를 닫는 길이 없었다. 매체가 몇 주 쉬면
(2026-11 charter — 피드는 멀쩡하고 매체가 글을 안 냈다) 같은 경보가 매일 쌓여, 9월에 연 이슈 하나에
댓글이 45개가 됐다. 늘 열려 있는 이슈는 새 경보가 와도 눈에 띄지 않는다.

정하는 것 (한 줄 출력, 첫 단어가 판정):
- post  — 경보가 있고 알릴 만하다: 열린 이슈가 없거나, 지난 알림에 없던 소스가 생겼거나,
          지난 알림에서 REPEAT_DAYS(7일)가 지났다.
- skip  — 경보가 있지만 같은 소스를 최근에 이미 알렸다.
- close — 경보가 없고, 수집이 끝까지 돌아 점검도 했다 → 열린 이슈를 닫는다.
- none  — 경보가 없지만 점검이 돌았는지 알 수 없다(오늘 이미 수집함·수집 실패·점검 실패) → 그대로 둔다.

python src/collectors/inflow_alert.py logs/collect.log < 이슈.json   (gh issue view N --json createdAt,body,comments)
열린 이슈가 없으면 표준입력에 {}를 준다. 항상 exit 0.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALERT_RE = re.compile(r"\[무유입 경보\] (\S+) —")
RAN_MARK = "수집 완료로 기록됨"       # collect.run()이 끝까지 돌았을 때만 찍힌다(오늘 이미 수집한 날은 없다)
CHECK_FAILED = "[경보 점검 실패]"
REPEAT_DAYS = 7


def alert_ids(text: str) -> set[str]:
    return set(ALERT_RE.findall(text or ""))


def _when(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def last_post(issue: dict) -> tuple[datetime, set[str]] | None:
    """이슈 본문·댓글 가운데 경보 줄이 있는 가장 최근 글 — (쓴 때, 그때 알린 소스들)."""
    posts = [(issue.get("createdAt"), issue.get("body"))]
    posts += [(c.get("createdAt"), c.get("body")) for c in issue.get("comments") or []]
    found = [(_when(at), alert_ids(body)) for at, body in posts]
    found = [(at, ids) for at, ids in found if at and ids]
    return max(found, key=lambda x: x[0]) if found else None


def decide(log: str, issue: dict, now: datetime | None = None) -> tuple[str, str]:
    """(판정, 이유)."""
    now = now or datetime.now(timezone.utc)
    ids = alert_ids(log)
    if not ids:
        if RAN_MARK in log and CHECK_FAILED not in log:
            return "close", "무유입 소스 없음"
        return "none", "점검이 돌았는지 알 수 없음"
    prev = last_post(issue) if issue else None
    if prev is None:
        return "post", "알린 적 없음"
    at, told = prev
    fresh = sorted(ids - told)
    if fresh:
        return "post", "새로 생긴 소스: " + ", ".join(fresh)
    days = (now - at).days
    if now - at >= timedelta(days=REPEAT_DAYS):
        return "post", f"지난 알림에서 {days}일 지남"
    return "skip", f"같은 소스를 {days}일 전에 알림(다음 알림은 {REPEAT_DAYS}일 뒤)"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0] if argv else "logs/collect.log")
    log = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    try:
        issue = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        issue = {}
    action, why = decide(log, issue if isinstance(issue, dict) else {})
    print(f"{action} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
