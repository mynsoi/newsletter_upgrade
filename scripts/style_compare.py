"""경영일기 참고 방식 비교 시험(2026-10-24) — 같은 글 설정으로 '지금'과 '새 방식'을 과정 1·2·3까지 나란히 쓴다.

  지금   : 초안 참고 고정 3편(p747·p724·p740) · 재작성 참고 고정 2편(p724·p669)
  새 방식: 문체 안내서(252편) + 초안 참고 = 메시지가 가까운 2편 · 재작성 참고 = 초안과 도입·맺음 방식이 같은 글 중 메시지가 가까운 2편

  python3 -I scripts/style_compare.py <글 이름> ...   → runs/style-compare/<시각>/<글>/<now|new>/{draft,r4,final}.md + meta.json
작업실 글(briefs·runs/columns)은 건드리지 않는다. 제목은 빼고(제목은 원고 뒤에 짓는다) 쓴다.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import column_pipeline as C  # noqa: E402
import style_guide as SG  # noqa: E402

OUT = C.ROOT / "runs" / "style-compare"


def one(k, variant, root):
    b = json.loads((C.ROOT / "briefs" / f"{k}.json").read_text(encoding="utf-8"))
    for x in ("title", "confirmed", "text_pick", "hero", "inline", "images_done"):
        b.pop(x, None)
    d = root / k / variant
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = {"variant": variant, "thesis": b["thesis"]}
    if variant == "new":
        guide = SG.guide_text()
        refs_d = SG.draft_refs(b["thesis"], 2)
        draft = C.run_claude(d / "_draft", C.draft_prompt(b, refs_d, guide))
        op, cl = SG.label(d / "_label", draft)
        refs_r = SG.rewrite_refs(b["thesis"], op, cl, 2, exclude=refs_d)
        meta.update({"draft_refs": refs_d, "draft_shape": [op, cl], "r4_refs": refs_r})
        r4 = C.run_astra(d / "_r4", C.r4_prompt(b, draft, refs_r, guide))
    else:
        meta.update({"draft_refs": C.DRAFT_REFS, "r4_refs": b.get("r4_refs", ["p724", "p669"])})
        draft = C.run_claude(d / "_draft", C.draft_prompt(b))
        r4 = C.run_astra(d / "_r4", C.r4_prompt(b, draft))
    final = C.run_astra(d / "_final", C.fb_prompt(r4))
    for name, t in (("draft", draft), ("r4", r4), ("final", final)):
        (d / f"{name}.md").write_text(t, encoding="utf-8")
    if C.chars(d / "final.md") > C.MAX_CHARS:
        (d / "final.md").write_text(C.run_astra(d / "_fit", C.fit_prompt(final)), encoding="utf-8")
        meta["fit"] = True
    meta.update({"chars": {n: C.chars(d / f"{n}.md") for n in ("draft", "r4", "final")}, "secs": round(time.time() - t0)})
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{k} · {variant} · {meta['secs']}s · {meta['chars']}", flush=True)
    return meta


if __name__ == "__main__":
    ks = sys.argv[1:]
    root = OUT / time.strftime("%Y%m%d-%H%M%S")
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda kv: one(kv[0], kv[1], root), [(k, v) for k in ks for v in ("now", "new")]))
    print("끝:", root)
