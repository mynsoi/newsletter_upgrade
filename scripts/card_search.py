"""카드 검색 — '내 주제로 쓰기'가 원문 후보를 찾는 첫 단계(2026-10-21).

예전에는 Claude가 원문 카드 전부(59편)를 읽고 후보를 골랐다. 원문이 1,000편을 넘으면 그럴 수 없어서,
먼저 자동 카드(main document_cards, Sonnet 5.5)로 후보를 수십 편까지 좁히고, 그 카드만 Claude에게 넘긴다.

  의미 검색  — 주제 문장을 임베딩해 document_card_embeddings(핵심 주장 + 사례별)와 코사인 거리로 비교,
               문서마다 가장 가까운 부분의 점수로 순위(Supabase에서 바로, 읽기 전용).
  낱말 검색  — 주제에 나온 고유명사·영문 단어·한글 낱말로 카드 글자(받아 둔 sources/doc_cards.json)를 BM25로 순위.
               의미 검색이 회사·제품 이름(토스, Copilot 등)에 약해서.
  합치기     — 두 순위를 RRF(순위 역수 합)로 섞어 상위 TOP편(2026-10-24 사용자 결정 — 예전엔 의미 100편 뒤에 낱말 10편을 덧붙였다.
               wiki-eval/search_bench_1024.py: 주제 50개 사례 원문 153편이 넘기는 목록에 드는 비율 지금 64% → 섞기 67%, 발행처 상한은 61%라 안 씀)
  카드 임베딩이 아직 없으면(main 소급 전) 받아 둔 카드 전부를 넘긴다(상한 ALL_CAP) — 시험 카드 40장으로 개발할 때도 이 길.

  python3 -I scripts/card_search.py "<주제 문장>"   검색 결과만 보기
쿼리 임베딩은 main과 같은 모델·차원(text-embedding-3-small, 1536). 키는 환경변수 OPENAI_API_KEY.
"""
import json
import os
import re
import ssl
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki as W  # noqa: E402

# 의미 검색으로 넘길 문서 수. 2026-10-22 시험(주제 25개의 사례 원문 84편이 주제 문장 검색 몇 위에 나오나):
# 30위 안 31편(37%) · 100위 안 50편(60%) → 100으로. 주제 문장을 구체적 장면 5줄로 늘려 함께 검색하는 방식은
# 30위 23편 · 100위 45편으로 오히려 낮아 넣지 않았다(지어낸 장면이 엉뚱한 사례 쪽으로 끈다).
TOP = int(os.environ.get("CARD_SEARCH_TOP", "100"))  # LLM에 넘기는 수(두 순위를 섞은 상위)
SEM_DEPTH = 400                                        # 섞기 전에 의미 검색에서 받아 오는 깊이
K_RRF = 60                                             # RRF 상수(흔히 쓰는 값)
ALL_CAP = 200                                          # 카드 임베딩이 없을 때 넘길 카드 상한
EMBED_MODEL, EMBED_DIM = "text-embedding-3-small", 1536
SCOPE = W.ROOT / "sources" / "db_scope.json"
INDEX = W.ROOT / "sources" / "db_index.json"
# 낱말 검색에서 뺄 흔한 말(주제 문장에 늘 나오는 것)
STOP = set("AI 우리 직원 회사 일 일을 일이 것 것이 때 더 수 있다 없다 하는 하고 해야 한다 위한 위해 같은 그리고 하지만 이 그 저 글 칼럼".split())


def _key(name):
    v = os.environ.get(name) or subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"[Environment]::GetEnvironmentVariable('{name}','User')"],
        capture_output=True, text=True).stdout.strip()
    return v


def embed(text):
    """주제 문장 임베딩. 이 PC(Windows·Python 3.13)는 SDK 기본 SSL(truststore)이 재귀 오류를 내서 기본 SSL 문맥을 직접 준다."""
    import httpx
    import openai
    c = openai.OpenAI(api_key=_key("OPENAI_API_KEY"), http_client=httpx.Client(verify=ssl.create_default_context()))
    return c.embeddings.create(model=EMBED_MODEL, input=[text[:8000]], dimensions=EMBED_DIM).data[0].embedding


def embed_many(texts):
    """여러 줄을 한 번에(경영일기 제목 짝 메시지 — title_style.py)."""
    import httpx
    import openai
    c = openai.OpenAI(api_key=_key("OPENAI_API_KEY"), http_client=httpx.Client(verify=ssl.create_default_context()))
    return [d.embedding for d in c.embeddings.create(model=EMBED_MODEL, input=[t[:8000] for t in texts], dimensions=EMBED_DIM).data]


def semantic(text, keys_by_doc, depth=SEM_DEPTH):
    """Supabase 카드 임베딩으로 문서 순위. 표가 없거나 비었으면 None."""
    import psycopg
    url = os.environ.get("DATABASE_URL") or _key("DATABASE_URL")
    if not url:
        return None
    with psycopg.connect(url, prepare_threshold=None) as c:
        c.read_only = True
        if not c.execute("SELECT to_regclass('public.document_card_embeddings')").fetchone()[0]:
            return None
        if not c.execute("SELECT 1 FROM document_card_embeddings LIMIT 1").fetchone():
            return None
        vec = "[" + ",".join(f"{x:.6f}" for x in embed(text)) + "]"
        rows = c.execute("""SELECT document_id, min(embedding <=> %s::halfvec) AS dist
                            FROM document_card_embeddings WHERE document_id = ANY(%s)
                            GROUP BY document_id ORDER BY dist LIMIT %s""",
                         (vec, list(keys_by_doc), depth)).fetchall()
    return [(keys_by_doc[d], 1 - float(dist)) for d, dist in rows]


def words(text):
    """주제 문장에서 낱말 검색에 쓸 말 — 영문·숫자 단어, 두 글자 이상 한글 낱말에서 흔한 조사를 뗀 것."""
    out = set(re.findall(r"[A-Za-z][A-Za-z0-9.+-]{1,}", text))
    for w in re.findall(r"[가-힣]{2,}", text):
        w = re.sub(r"(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|까지|부터|처럼|보다)$", "", w)
        if len(w) >= 2 and w not in STOP:
            out.add(w)
    return {w for w in out if w not in STOP}


def bm25(text, cards):
    """낱말 순위 — 카드 글자(주장 + 사례)에서 BM25. [키] 점수 높은 순."""
    import math
    from collections import Counter
    qs = words(text)
    if not qs:
        return []
    docs = {k: Counter(words(" ".join([c.get("thesis", ""), *c.get("episodes", [])]))) for k, c in cards.items()}
    n, avg = len(docs), (sum(sum(c.values()) for c in docs.values()) / max(len(docs), 1)) or 1
    df = Counter(w for c in docs.values() for w in set(c) if w in qs)
    idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
    sc = {}
    for k, c in docs.items():
        ln = sum(c.values())
        s_ = sum(idf[w] * c[w] * 2.4 / (c[w] + 1.4 * (0.25 + 0.75 * ln / avg)) for w in qs if w in c and w in idf)
        if s_:
            sc[k] = s_
    return sorted(sc, key=sc.get, reverse=True)


def keyword(text, cards, skip):
    ws = words(text)
    scored = []
    for k, c in cards.items():
        if k in skip:
            continue
        blob = " ".join([c.get("thesis", ""), *c.get("episodes", [])])
        hit = sum(1 for w in ws if w in blob)
        if hit:
            scored.append((k, hit))
    scored.sort(key=lambda x: -x[1])
    return scored[:KEYWORD_TOP]


def candidates(text):
    """주제 문장 → 후보 카드 {키: 주제 지도 모양 카드}와 어떻게 찾았는지 설명 한 줄."""
    dc = W.doc_cards()
    if not dc:
        return {}, "받아 둔 자동 카드가 없음 — 서재에서 'Supabase 받기'를 먼저"
    idx = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    keys_by_doc = {doc: W.key(rel) for doc, rel in idx.items() if W.key(rel) in dc}
    sem = semantic(text, keys_by_doc) if keys_by_doc else None
    if sem is None:
        keys = sorted(dc, key=lambda k: W.date_of(W.rel(k)), reverse=True)[:ALL_CAP]
        how = f"카드 임베딩이 아직 없어 받아 둔 카드 {len(keys)}장 전부"
    else:
        usable = {k: c for k, c in dc.items() if c.get("material_type") != "재료 없음" and (W.SRC / W.rel(k)).is_file()}
        sem_keys = [k for k, _ in sem if k in usable]
        kw_keys = bm25(text, usable)[:SEM_DEPTH]
        sc = {}
        for ranked in (sem_keys, kw_keys):
            for r, k in enumerate(ranked):
                sc[k] = sc.get(k, 0) + 1 / (K_RRF + r + 1)
        keys = sorted(sc, key=sc.get, reverse=True)[:TOP]
        how = f"의미 검색 {len(sem_keys)}편 · 낱말 검색 {len(kw_keys)}편을 순위로 섞어 상위 {len(keys)}편"
    keys = [k for k in keys if dc[k].get("material_type") != "재료 없음" and (W.SRC / W.rel(k)).is_file()]
    return {k: W.as_card(dc[k]) for k in keys}, how


if __name__ == "__main__":
    q = " ".join(sys.argv[1:])
    cs, how = candidates(q)
    print(how)
    for k, c in list(cs.items())[:TOP]:
        print(f"- [{k}] {c['글쓴이가 하는 말'][:90]}")
