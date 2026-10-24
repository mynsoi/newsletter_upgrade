"""카드 검색 비교(2026-10-24) — 지금 · A(점수 섞기: 의미 순위 + BM25 낱말 순위, RRF) · B(발행처 상한)를 같은 조건으로.

측정: 주제 탭에서 사례가 2편 이상인 주제마다 주제 문장으로 검색해, 그 주제의 사례 원문이 넘기는 110편(지금과 같은 수) 안에 몇 편 드는지.
10/22 측정(주제 25개·원문 84편, 100위 안 60%)과 같은 방식을 지금 주제 110개로 다시 만든 것. 원문 다양성으로 넘기는 110편의 발행처 수·최다 발행처 비율도 본다.
  python3 -I wiki-eval/search_bench_1024.py
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import card_search as CS  # noqa: E402
import wiki as W  # noqa: E402

N = 110          # LLM에 넘기는 수 — 지금(의미 100 + 낱말 10)과 같게
SEM_DEPTH = 400  # A·B가 의미 검색에서 받아 오는 깊이
CAP = 15         # B: 발행처 하나당 상한
K_RRF = 60


def sem_ranked(text, keys_by_doc, depth):
    import psycopg
    with psycopg.connect(CS._key("DATABASE_URL"), prepare_threshold=None) as c:
        c.read_only = True
        vec = "[" + ",".join(f"{x:.6f}" for x in CS.embed(text)) + "]"
        rows = c.execute("""SELECT document_id, min(embedding <=> %s::halfvec) AS dist FROM document_card_embeddings
                            WHERE document_id = ANY(%s) GROUP BY document_id ORDER BY dist LIMIT %s""",
                         (vec, list(keys_by_doc), depth)).fetchall()
    return [keys_by_doc[d] for d, _ in rows]


def toks(t):
    return [w for w in CS.words(t)]


class BM25:
    def __init__(self, docs):
        self.docs = {k: Counter(toks(v)) for k, v in docs.items()}
        self.len = {k: sum(c.values()) for k, c in self.docs.items()}
        self.avg = sum(self.len.values()) / max(len(self.len), 1)
        df = Counter(w for c in self.docs.values() for w in c)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def rank(self, q, k1=1.4, b=0.75):
        qs = set(toks(q))
        sc = {}
        for k, c in self.docs.items():
            s = sum(self.idf.get(w, 0) * c[w] * (k1 + 1) / (c[w] + k1 * (1 - b + b * self.len[k] / self.avg)) for w in qs if w in c)
            if s:
                sc[k] = s
        return sorted(sc, key=sc.get, reverse=True)


def site(k):
    return k.split("/")[0]


def main():
    dc = W.doc_cards()
    idx = json.loads(CS.INDEX.read_text(encoding="utf-8"))
    keys_by_doc = {doc: W.key(rel) for doc, rel in idx.items() if W.key(rel) in dc}
    ok = {k for k in keys_by_doc.values() if dc[k].get("material_type") != "재료 없음" and (W.SRC / W.rel(k)).is_file()}
    bm = BM25({k: " ".join([dc[k].get("thesis", ""), *dc[k].get("episodes", [])]) for k in ok})
    ts = [t for t in W.topics() if len(t["sources"]) >= 2]
    res = {"지금": [0, [], []], "A 점수 섞기": [0, [], []], "B 발행처 상한": [0, [], []]}
    total = 0
    for t in ts:
        q = t["thesis"] or t["title"]
        sem = [k for k in sem_ranked(q, keys_by_doc, SEM_DEPTH) if k in ok]
        # 지금: 의미 100 + 낱말(글자 포함 개수) 10 덧붙이기
        now = sem[:100]
        now += [k for k, _ in CS.keyword(q, {k: dc[k] for k in ok}, set(now))][:N - len(now)]
        # A: RRF — 의미 순위 + BM25 순위
        kw = bm.rank(q)
        sc = {}
        for r, k in enumerate(sem):
            sc[k] = sc.get(k, 0) + 1 / (K_RRF + r + 1)
        for r, k in enumerate(kw[:SEM_DEPTH]):
            sc[k] = sc.get(k, 0) + 1 / (K_RRF + r + 1)
        a = sorted(sc, key=sc.get, reverse=True)[:N]
        # B: 의미 순위에서 발행처당 CAP편까지 100편 + 낱말 10 (지금과 같은 덧붙이기)
        per, b = Counter(), []
        for k in sem:
            if per[site(k)] < CAP:
                b.append(k)
                per[site(k)] += 1
            if len(b) >= 100:
                break
        b += [k for k, _ in CS.keyword(q, {k: dc[k] for k in ok}, set(b))][:N - len(b)]
        gold = [s for s in t["sources"] if s in ok]
        total += len(gold)
        for name, lst in (("지금", now), ("A 점수 섞기", a), ("B 발행처 상한", b)):
            res[name][0] += sum(1 for s in gold if s in lst)
            sites = Counter(site(k) for k in lst)
            res[name][1].append(len(sites))
            res[name][2].append(max(sites.values()) / len(lst))
    print(f"주제 {len(ts)}개 · 사례 원문 {total}편 · 넘기는 수 {N}편")
    for name, (hit, ns, top) in res.items():
        print(f"{name:10} 사례 원문 포함 {hit}/{total} ({hit / total:.0%}) · 발행처 수 평균 {sum(ns) / len(ns):.1f} · 최다 발행처 비율 평균 {sum(top) / len(top):.0%}")


if __name__ == "__main__":
    main()
