"""'이 글만의 것' 위키 시험 (2026-10-10) — 원문 전부를 wiki-hook/에 처음부터 넣고 정리까지.

지금 위키(wiki/)는 건드리지 않는다. wiki.py의 넣기·정리를 그대로 쓰되 위키 폴더와 커밋 경로만 wiki-hook/으로 바꾼다.
astra는 wiki-hook/ 안에서만 쓰기 가능한 샌드박스(-C wiki-hook)로 돈다 — 원문 폴더는 읽기만.
사용: python3 -I wiki-eval/run_hook.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import wiki as W  # noqa: E402

W.WIKI = ROOT / "wiki-hook"


def commit(msg):
    subprocess.run(["git", "add", "-A", "wiki-hook"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "wiki-hook: " + msg, "--", "wiki-hook"], cwd=ROOT, capture_output=True)


W.commit = commit

if __name__ == "__main__":
    t0 = time.time()
    timing = {}
    W.ingest([])
    left = W.backlog()
    if left:  # 연결이 끊겨 못 넣은 것만 한 번 더
        W.ingest(left)
    timing["ingest_s"] = round(time.time() - t0)
    t1 = time.time()
    W.lint()
    timing["lint_s"] = round(time.time() - t1)
    timing["left"] = W.backlog()
    (ROOT / "wiki-eval" / "timing-hook.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print("끝", timing)
