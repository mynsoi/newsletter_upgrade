"""전체 수집 오케스트레이터 — rss + api 를 하루 1회 보장 잠금 아래 실행한다.

수집은 GitHub Actions·개발 PC 어디서든 트리거될 수 있으므로, 중복 수집을
DB 레벨(collection_runs)에서 막는다. 이 스크립트가 하루치 잠금의 유일한 소유자다:
  1. begin_collection() 으로 오늘자 실행권을 원자적으로 선점
  2. rss.run(...) → api.run(...) 을 force=True 로 호출
  3. finish_collection() 으로 completed/failed 확정 (실패 시 그날은 잠기지 않음)

rss.run()/api.run() 에 넘기는 force=True 는 "상위 오케스트레이터가 이미 daily
lock 을 확인했으니 하위 워커는 collection_runs 재확인을 생략하라"는 **내부 호출
신호**다. 사용자용 --force(하루 1회 제한 우회)와는 목적이 다르다:
  - collect.py --force  → begin_collection(force=True): completed 여도 재수집
  - rss.run(force=True) → collection_done_today() 체크 생략 (오케스트레이터 전용)

사용:
  python src/collectors/collect.py [소스ID...] [--no-body] [--force] [--backfill FROM TO]
  make collect / make collect-fast
"""
from __future__ import annotations

import argparse
import socket
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import begin_collection, connect, finish_collection, migrate  # noqa: E402
import collectors.rss as rss  # noqa: E402
import collectors.api as api  # noqa: E402


def run(source_ids: list[str] | None = None, *, fetch_full: bool = True,
        force: bool = False, backfill: tuple[str, str] | None = None) -> int:
    from handoff import ensure_active
    ensure_active("수집")

    conn = connect()
    migrate(conn)
    host = socket.gethostname()
    state = begin_collection(conn, host, force=force)
    conn.close()

    today = date.today().isoformat()
    if state == "done":
        print(f"오늘({today}) 수집 완료됨 — 재수집하려면 --force")
        return 0
    if state == "running":
        print(f"오늘({today}) 다른 프로세스가 수집을 진행 중입니다 — 중복 실행 방지로 종료")
        return 0

    ok = False
    try:
        # force=True: 오케스트레이터가 이미 daily lock 을 선점 → 워커는 재확인 생략
        r = rss.run(source_ids, fetch_full=fetch_full, force=True) or {"targets": 0, "failed": 0}
        a = api.run(source_ids, backfill=backfill, force=True) or {"targets": 0, "failed": 0}
        targets = r["targets"] + a["targets"]
        failed = r["failed"] + a["failed"]
        # 전량 실패 = 인프라 문제(네트워크·DB 등) 가능성 — failed 로 남겨 자동 재시도.
        # 일부 실패는 소스 개별 문제로 보고 completed (개별 소스는 validate 로 점검).
        ok = not (targets > 0 and failed >= targets)
        if not ok:
            print(f"[수집 실패] 전 소스 실패 ({failed}/{targets}) — failed 로 기록, 다음 실행이 자동 재시도")
        elif failed:
            print(f"[주의] 일부 소스 실패 ({failed}/{targets}) — completed 로 기록, `make validate`로 점검 필요")
    except Exception as e:  # noqa: BLE001 — 실패를 failed 로 기록하고 비정상 종료 (SystemExit 는 그대로 전파)
        import traceback
        print(f"[수집 실패] {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        conn = connect()
        finish_collection(conn, ok=ok)
        conn.close()
        print(f"수집 {'완료' if ok else '실패'}로 기록됨 (collection_runs {today})")
    return 0 if ok else 1


def _parse_args(argv: list[str]):
    p = argparse.ArgumentParser(description="rss + api 통합 수집 (하루 1회 보장)")
    p.add_argument("ids", nargs="*", help="특정 소스 id만 수집 (생략 시 전체)")
    p.add_argument("--no-body", action="store_true", help="본문 추출 없이 피드 요약만")
    p.add_argument("--force", action="store_true", help="하루 1회 제한을 우회하고 재수집")
    p.add_argument("--backfill", nargs=2, metavar=("FROM", "TO"),
                   help="api 소스 과거분 소급 수집 (YYYY-MM-DD YYYY-MM-DD)")
    return p.parse_args(argv)


if __name__ == "__main__":
    a = _parse_args(sys.argv[1:])
    raise SystemExit(run(
        a.ids or None,
        fetch_full=not a.no_body,
        force=a.force,
        backfill=tuple(a.backfill) if a.backfill else None,
    ))
