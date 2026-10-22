"""경영일기 제목 짝 — 「유정식의 경영일기」 글마다 '핵심 메시지 → 실제 제목 → 쓴 장치'를 정리해 제목 짓기의 예시로 쓴다(2026-10-23).

제목 목록만으로는 필자가 글의 메시지를 어떻게 제목으로 바꾸는지 알 수 없어서, 본문을 읽고 짝을 만든다.
  python3 -I scripts/title_style.py --build      본문(sources/originals/infuture/p*.md)마다 짝을 만든다(Claude, 계정 로그인). 이미 만든 글은 건너뜀
  python3 -I scripts/title_style.py --stats      장치별 개수
  python3 -I scripts/title_style.py --similar "<이 글이 말할 것>"   메시지가 가까운 짝(임베딩)
결과: sources/originals/infuture/_title_pairs.json(짝, git에 — 경영일기 본문도 git에 있다) · _title_pairs_emb.json(메시지 임베딩, 다시 만들 수 있어 git 밖)
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki as W  # noqa: E402

INF = W.ROOT / "sources" / "originals" / "infuture"
PAIRS = INF / "_title_pairs.json"
EMB = INF / "_title_pairs_emb.json"
RUNS = W.ROOT / "runs" / "title-style"
BATCH = 20
# 경영일기 제목이 쓰는 장치 — 252개 제목을 보고 정한 이름(한 제목에 여럿 가능)
DEVICES = ["질문", "통념 뒤집기", "금지·권유", "이유", "따옴표 핵심어", "조건·전제", "역설·대비", "숫자", "독자 호명", "감탄"]
DEVICE_NOTE = {
    "질문": "독자에게 묻는다 — '~할까요?', '~나요?', '~은?'",
    "통념 뒤집기": "흔한 믿음과 반대되는 말을 단언한다 — 'AI가 혁신을 망친다'",
    "금지·권유": "하지 말라거나 하라고 말한다 — '~하지 마세요', '~하라'",
    "이유": "'~하는 이유'로 궁금하게 만든다",
    "따옴표 핵심어": "핵심 단어 하나를 따옴표로 세운다 — \"'합의'하지 마세요\"",
    "조건·전제": "'~하기 전에', '~라면', '~할 때'로 장면을 연다",
    "역설·대비": "두 가지를 맞세운다 — '~보다 ~', '~인데 ~'",
    "숫자": "숫자로 구체성을 준다",
    "독자 호명": "'여러분', '당신'을 부른다",
    "감탄": "'!'로 끝낸다",
}


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    meta = dict(re.findall(r"^(\w+):[ \t]*'?(.*?)'?[ \t]*$", m.group(1), re.M)) if m else {}
    return meta, (t[m.end():] if m else t).strip()


def articles():
    out = []
    for f in sorted(INF.glob("p*.md"), key=lambda p: int(p.stem[1:]) if p.stem[1:].isdigit() else 0):
        meta, body = front(f.read_text(encoding="utf-8"))
        title = meta.get("title", "").strip().strip("'\"")
        if title and len(body) >= 300:
            out.append({"id": f.stem, "title": title, "date": meta.get("date", ""), "body": body})
    return out


def pairs():
    return json.loads(PAIRS.read_text(encoding="utf-8")) if PAIRS.exists() else {}


def build_prompt(batch):
    arts = "\n\n".join(f"=== [{a['id']}] 제목: {a['title']} ===\n{a['body'][:3000]}" for a in batch)
    return "\n\n".join([
        "아래는 「유정식의 경영일기」(경영 컨설턴트 유정식이 직장인에게 쓰는 짧은 칼럼) 글들입니다. "
        "필자가 글의 핵심 메시지를 어떻게 제목으로 바꾸는지 배우려고 합니다. 글마다 정리해 주세요.",
        "글마다:\n"
        "- message: 이 글이 독자에게 하는 핵심 메시지 한 문장(제목을 보지 않은 사람이 본문만 읽고 정리하듯, 쉬운 말로)\n"
        f"- devices: 제목이 쓴 장치 — 이 목록에서만 골라 하나 이상: {', '.join(DEVICES)}\n"
        "- how: 제목이 메시지를 어떻게 줄이거나 비틀었는지 한 줄(무엇을 남기고 무엇을 감췄는지, 어디서 궁금증이 생기는지)",
        "출력: JSON 하나만. {\"items\": [{\"id\": \"p752\", \"message\": \"...\", \"devices\": [\"질문\"], \"how\": \"...\"}]} — id는 [ ] 안 그대로.",
        W.ANSWER_ONLY, W.GUARD,
        arts,
    ])


def build():
    got = pairs()
    todo = [a for a in articles() if a["id"] not in got]
    print(f"짝 만들 글 {len(todo)}편 (이미 {len(got)})", flush=True)
    run = RUNS / time.strftime("%Y%m%d-%H%M%S")
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        t0 = time.time()
        raw = W.claude_login(run / f"b{i // BATCH + 1:02d}", build_prompt(batch))
        m = re.search(r"\{.*\}", raw or "", re.S)
        items = json.loads(m.group(0)).get("items", []) if m else []
        by = {a["id"]: a for a in batch}
        for x in items:
            a = by.get(x.get("id"))
            if not a or not x.get("message"):
                continue
            got[a["id"]] = {"title": a["title"], "date": a["date"], "message": x["message"].strip(),
                            "devices": [d for d in x.get("devices", []) if d in DEVICES], "how": x.get("how", "").strip()}
        PAIRS.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"묶음 {i // BATCH + 1} · {len(items)}/{len(batch)} · 모두 {len(got)} · {time.time() - t0:.0f}s", flush=True)
    embed_all(got)


def embed_all(got):
    import card_search as CS
    have = json.loads(EMB.read_text(encoding="utf-8")) if EMB.exists() else {}
    todo = [k for k in got if k not in have]
    for i in range(0, len(todo), 100):
        ks = todo[i:i + 100]
        for k, v in zip(ks, CS.embed_many([got[k]["message"] for k in ks])):
            have[k] = [round(x, 5) for x in v]
    EMB.write_text(json.dumps(have), encoding="utf-8")
    print(f"메시지 임베딩 {len(have)}", flush=True)


def similar(text, n=8):
    """메시지가 가까운 경영일기 짝 n개 — [(id, 짝)]. 임베딩이 없으면 최근 글 n개."""
    got = pairs()
    if not got:
        return []
    try:
        import card_search as CS
        emb = json.loads(EMB.read_text(encoding="utf-8"))
        q = CS.embed(text)
        score = {k: sum(a * b for a, b in zip(q, v)) for k, v in emb.items() if k in got}
        keys = sorted(score, key=score.get, reverse=True)[:n]
    except Exception as e:
        print(f"짝 검색 건너뜀(최근 글로): {e}", flush=True)
        keys = sorted(got, key=lambda k: got[k].get("date", ""), reverse=True)[:n]
    return [(k, got[k]) for k in keys]


def stats():
    got = pairs()
    c = {d: 0 for d in DEVICES}
    for v in got.values():
        for d in v["devices"]:
            c[d] += 1
    return len(got), c


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--build"]:
        build()
    elif a[:1] == ["--stats"]:
        n, c = stats()
        print(f"짝 {n}개")
        for d, k in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {d:8} {k:4} ({k / max(n, 1):.0%})")
    elif a[:1] == ["--similar"]:
        for k, v in similar(" ".join(a[1:])):
            print(f"[{k}] {v['message']}\n    → {v['title']}  ({', '.join(v['devices'])})")
    else:
        print(__doc__)
