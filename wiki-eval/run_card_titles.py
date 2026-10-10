"""주제 카드마다 글 제목 후보를 붙인다 — 작업실 제목 단계(title_candidates.prompt_first)를 그대로 (2026-10-11)

멘토: "나한테 주제별로 글 제목을 준다고 하지 않았어? 그걸로 검토한다고?"
이 글이 말할 것 = 카드의 '글쓴이가 하는 말', 원문 = 그 카드의 원문. 새 규칙을 더하지 않는다. 후보는 astra만, 고르지 않고 그대로 보여 준다.
사용: python3 -I wiki-eval/run_card_titles.py runs/topic-plain/20261011-000210  → <그 폴더>/titles/<사이트>/<번호>/astra.md
"""
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import title_candidates as tc  # noqa: E402
import wiki as W  # noqa: E402  label()


def cards(run_dir):
    out = {}
    for block in re.split(r"^## ", (run_dir / "all.md").read_text(encoding="utf-8"), flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        m = re.search(r"^글쓴이가 하는 말:\s*(.+)$", body, re.M)
        if m:
            out[head.strip()] = m.group(1).strip()
    return out


def run(src, thesis, run_dir):
    d = run_dir / "titles" / Path(src).parent.name / Path(src).stem
    d.mkdir(parents=True, exist_ok=True)
    p = tc.prompt_first(thesis, [[src, W.label(src)]], ROOT / "sources")
    (d / "prompt.md").write_text(p, encoding="utf-8")
    t = time.time()
    tc.astra(d, p)
    ok = (d / "astra.md").exists()
    print(f"{src} · {time.time() - t:.0f}s · {'ok' if ok else '실패'}", flush=True)


if __name__ == "__main__":
    run_dir = ROOT / sys.argv[1]
    cs = cards(run_dir)
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda kv: run(kv[0], kv[1], run_dir), cs.items()))
