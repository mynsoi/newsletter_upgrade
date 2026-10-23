"""회사 맥락 — 사내 용어집과 사내 자료(Supabase internal_docs)로 칼럼에 우리 회사 맥락을 입힌다 (2026-10-23 사용자 결정).

main 파이프라인의 원칙을 1,000자 칼럼에 맞게 가볍게 옮긴다(docs/기획서.md 7장, prompts/article_style.md):
  - 사내 자료는 인용·나열이 아니라 해석의 렌즈 — 맞을 때만 한 곳에서. 맞는 자료가 없으면 "사내 맥락 없음"이 정상
  - 용어집(main의 prompts/glossary_internal.md)은 사내 명칭을 언급할 때만 따른다
  - 사내 자료는 읽기 전용으로만 읽고, 본문·대목은 저장소에 올리지 않는다(runs/internal/, runs/mine/<글>/internal.json — git 밖)
  - 사내 자료 대목은 초안(Claude)에만 넘긴다. astra(과정 2~)에는 원고에 녹은 문장만 간다(사용자 확인 2026-10-23)
  python3 -I scripts/internal_ctx.py --search "<이 글이 말할 것>"   비슷한 대목(임베딩)
  python3 -I scripts/internal_ctx.py --glossary                      작업실이 쓰기 지시에 넣는 용어집
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "runs" / "internal"
DOCS = CACHE / "docs.json"
CHUNKS = CACHE / "chunks.json"
CHUNK = 900  # 대목 한 개 글자 수(대략) — 문단을 이어 붙여 이 정도로
TOP = 10  # Claude에게 보여 줄 대목 수(자료 하나에서 1개 — 긴 전사본이 대목을 독차지하지 않게)
REFRESH = 24 * 3600  # 사내 자료 목록을 다시 받는 간격

# ---------- 용어집 ----------
_GLOSS = None


def glossary():
    """main의 사내 용어집 — 원본은 main 브랜치 prompts/glossary_internal.md(복사본을 두지 않는다). 머리말·'이 파일을 쓰는 자리'는 뗀다."""
    global _GLOSS
    if _GLOSS is None:
        t = ""
        try:
            r = subprocess.run(["git", "show", "origin/main:prompts/glossary_internal.md"], cwd=ROOT, capture_output=True,
                               text=True, encoding="utf-8", timeout=20)
            t = r.stdout if r.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            pass
        if not t and (ROOT / "prompts" / "glossary_internal.md").is_file():
            t = (ROOT / "prompts" / "glossary_internal.md").read_text(encoding="utf-8")
        t = re.split(r"^## 이 파일을 쓰는 자리", t, flags=re.M)[0]
        t = re.sub(r"\A# .*?\n(?=## )", "", t, flags=re.S)  # 머리말(작성 절차·CLAUDE.md 안내)
        _GLOSS = t.strip()
    return _GLOSS


GLOSSARY_RULE = ("[사내 용어집] 사내 제도·조직·행사를 언급할 때만 아래 표기와 사실을 따릅니다. "
                 "이 목록 때문에 글에 없던 사내 제도를 새로 꺼내지는 않습니다.")


def glossary_block():
    g = glossary()
    return GLOSSARY_RULE + "\n" + g if g else ""


# 확정 전 점검에서 잡는 '쓰지 않는 말' — 용어집 ✗ 칸에서 다른 뜻으로 쓰일 여지가 없는 것만(1:1·포럼·평가 시스템·AI 업무 같은 말은
# 외부 사례 문장에도 흔해 뺐다). 고칠 말은 용어집 표기.
TERM_WARN = {
    "피리뷰": "P.Review", "원온원": "1 on 1", "AI 태스크": "AI Task", "AI태스크": "AI Task", "1인 1AI": "1인 1 AI Task",
    "1인1과제": "1인 1 AI Task", "셀프 리뷰": "Self-Review", "셀프리뷰": "Self-Review", "자기평가서": "본인 평가",
    "자가 평가": "본인 평가", "이천 포럼": "이천포럼", "인사이트 위클리": "Insight Weekly", "이앤에스": "E&S",
    "SKI E&S": "SK innovation E&S 또는 E&S", "기업문화팀": "기업문화AX팀",
}


def term_check(text):
    """본문에 용어집이 '쓰지 않는 말'로 정한 표기 — [{"word", "use", "sentence"}]."""
    out = []
    for sent in re.split(r"(?<=[.?!])\s+|\n+", text):
        for w, use in TERM_WARN.items():
            if w in sent:
                out.append({"word": w, "use": use, "sentence": sent.strip()[:160]})
    return out


# ---------- 사내 자료 ----------
def _connect():
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        import card_search as CS
        url = CS._key("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 없음")
    c = psycopg.connect(url, prepare_threshold=None)
    c.read_only = True
    return c


def docs(force=False):
    """지금 유효한 사내 자료(대체되지 않은 것, 외부 전송 허용) — {id: {title, type, speaker, date, hash, body}}. 하루에 한 번 다시 받는다."""
    if DOCS.exists() and not force and time.time() - DOCS.stat().st_mtime < REFRESH:
        return json.loads(DOCS.read_text(encoding="utf-8"))
    with _connect() as c:
        rows = c.execute("select id, title, type, speaker, effective_date, content_hash, body from internal_docs "
                         "where superseded_by is null and api_eligible = 1 order by id").fetchall()
    got = {r[0]: {"title": r[1] or r[0], "type": r[2] or "", "speaker": r[3] or "", "date": str(r[4] or "")[:10],
                  "hash": r[5] or "", "body": r[6] or ""} for r in rows}
    CACHE.mkdir(parents=True, exist_ok=True)
    DOCS.write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
    return got


def split(body):
    """문단을 이어 붙여 CHUNK자 안팎의 대목으로. 머리말(---)은 뗀다."""
    body = re.sub(r"\A---\n.*?\n---\n", "", body, flags=re.S)
    body = re.sub(r"\A\s*(?:>.*\n?)+", "", body.lstrip())  # 맨 앞 '> ℹ️' 등록 메모(변환 경위·출처) — 자료 내용이 아니다
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    out, cur = [], ""
    for p in paras:
        while len(p) > CHUNK * 1.6:  # 아주 긴 문단은 문장 경계에서 자른다
            cut = max(p.rfind(". ", 0, CHUNK), p.rfind("다. ", 0, CHUNK), CHUNK // 2)
            out.append((cur + "\n\n" + p[:cut + 1]).strip())
            cur, p = "", p[cut + 1:].strip()
        if len(cur) + len(p) > CHUNK and cur:
            out.append(cur.strip())
            cur = ""
        cur += "\n\n" + p
    if cur.strip():
        out.append(cur.strip())
    return out


def chunks():
    """대목과 임베딩 — 자료 내용(hash)이 바뀐 것만 다시 임베딩한다. [{"id": "자료#번호", "doc", "text", "emb"}]"""
    import card_search as CS
    ds = docs()
    have = json.loads(CHUNKS.read_text(encoding="utf-8")) if CHUNKS.exists() else {}
    changed = False
    for k, d in ds.items():
        if have.get(k, {}).get("hash") == d["hash"]:
            continue
        parts = split(d["body"])
        embs = []
        for i in range(0, len(parts), 100):
            embs += CS.embed_many([f"{d['title']}\n{t}" for t in parts[i:i + 100]])
        have[k] = {"hash": d["hash"], "parts": [{"text": t, "emb": [round(x, 5) for x in e]} for t, e in zip(parts, embs)]}
        changed = True
    for k in [k for k in have if k not in ds]:  # 대체되거나 빠진 자료
        del have[k]
        changed = True
    if changed:
        CACHE.mkdir(parents=True, exist_ok=True)
        CHUNKS.write_text(json.dumps(have, ensure_ascii=False), encoding="utf-8")
    return [{"id": f"{k}#{i}", "doc": k, "text": p["text"], "emb": p["emb"]} for k, v in have.items() for i, p in enumerate(v["parts"])]


def search(text, n=TOP, per_doc=1):
    """글의 메시지와 가까운 대목 n개 — 자료 하나에서 많아야 per_doc개. [(점수, 대목)]"""
    import card_search as CS
    q = CS.embed(text)
    scored = sorted(((sum(a * b for a, b in zip(q, c["emb"])), c) for c in chunks()), key=lambda x: -x[0])
    out, per = [], {}
    for s, c in scored:
        if per.get(c["doc"], 0) >= per_doc:
            continue
        per[c["doc"]] = per.get(c["doc"], 0) + 1
        out.append((s, c))
        if len(out) >= n:
            break
    return out


def label(d):
    """'제목 (화자, 날짜)' — 화면·지시에 보이는 사내 자료 이름."""
    extra = ", ".join(x for x in (d.get("speaker", ""), d.get("date", "")) if x)
    return f"{d['title']} ({extra})" if extra else d["title"]


def recommend_prompt(message, topic, cands, ds):
    rows = "\n\n".join(f"=== [c{i}] {label(ds[c['doc']])} ===\n{c['text']}" for i, (_, c) in enumerate(cands, 1))
    return "\n\n".join([
        "아래 [이 글이 말할 것]은 SK innovation E&S(이하 E&S) 전 직원에게 가는 사내 뉴스레터 칼럼(공백 제외 1,000자 안팎)의 메시지입니다. "
        "[사내 자료 대목]은 우리 회사의 경영층 메시지·SKMS·사내 제도 안내에서 이 메시지와 가까운 대목을 검색한 것입니다.",
        "이 글에 우리 회사 맥락을 한 곳 입힐 대목이 있는지 판단해 주세요.\n"
        "- 고를 대목: 글의 메시지를 우리 회사 상황으로 해석하게 해 주는 것 — 같은 문제를 다루거나 같은 방향을 말하는 사내 방침·경영층 메시지·제도.\n"
        "- 고르지 않을 대목: 'AI'·'변화' 같은 낱말만 겹치는 것, 글에 억지로 붙여야 하는 것, 글의 메시지와 반대로 읽히는 것.\n"
        "- 맞는 대목이 없으면 고르지 않는 것이 정상입니다(pick: null). 하나만 고릅니다.\n"
        "- 고르면 use(글에서 어떻게 이을지 한 줄 — '이 대목도 같은 말을 한다'는 나열이 아니라, 글의 주장을 우리 회사 상황으로 옮겨 읽게 하는 방식), "
        "fact(그 대목에서 글에 쓸 사실이나 취지 한두 가지 — 대목에 있는 것만), caution(시점·확정 여부·화자 등 쓸 때 조심할 점)을 적습니다. "
        "경영층 발언은 따옴표로 옮기지 않고 취지로 쓴다는 점, 안내문이 '예정'으로 쓴 것은 확정이 아니라는 점을 caution에 반영합니다.",
        "출력: JSON 하나만. {\"pick\": \"c3\" 또는 null, \"use\": \"...\", \"fact\": \"...\", \"caution\": \"...\", \"why\": \"고르거나 고르지 않은 이유 한 줄\"}",
        "[이 글이 말할 것]\n" + message, "[멘토가 처음 한 요청]\n" + (topic or message), "[사내 자료 대목]\n" + rows])


def recommend(run_dir, message, topic=""):
    """글의 메시지에 맞는 사내 자료 대목 0~1개를 Claude(계정 로그인)가 골라 run_dir/internal.json에 남긴다. 고르면 기본으로 넣는다(on)."""
    import wiki as W
    d = Path(run_dir)
    ds = docs()
    cands = search(message)
    raw = W.claude(d / "internal", recommend_prompt(message, topic, cands, ds))
    m = re.search(r"\{.*\}", raw or "", re.S)
    got = json.loads(m.group(0)) if m else {}
    pick = str(got.get("pick") or "")
    idx = int(pick[1:]) if re.fullmatch(r"c\d+", pick) and 1 <= int(pick[1:]) <= len(cands) else 0
    out = {"on": bool(idx), "why": got.get("why", ""), "candidates": [label(ds[c["doc"]]) for _, c in cands]}
    if idx:
        c = cands[idx - 1][1]
        dd = ds[c["doc"]]
        nxt = next((x["text"] for x in chunks() if x["id"] == f"{c['doc']}#{int(c['id'].split('#')[1]) + 1}"), "")
        c = {**c, "text": (c["text"] + ("\n\n" + nxt if nxt else ""))[:2200]}
        out.update({"doc": c["doc"], "chunk": c["id"], "title": dd["title"], "speaker": dd["speaker"], "date": dd["date"],
                    "type": dd["type"], "label": label(dd), "excerpt": c["text"],
                    "use": got.get("use", ""), "fact": got.get("fact", ""), "caution": got.get("caution", "")})
    (d / "internal.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


INTERNAL_RULE = ("우리 회사 자료는 글의 한 곳(한 문단 이내)에서, 글의 주장을 우리 회사 상황으로 옮겨 읽게 하는 데 씁니다. "
                 "'회사 자료는 A라고 하고 외부 연구는 B라고 한다'처럼 나란히 늘어놓지 않습니다. 자료의 연도를 밝히고(예: '2026년 이천포럼에서'), "
                 "경영층 발언은 따옴표로 옮기지 않고 취지로 씁니다. 자료가 '예정'·'방향'으로 말한 것은 확정된 것처럼 쓰지 않고, "
                 "사내 제도를 비판하는 뉘앙스로 쓰지 않으며, 자료에 없는 사내 사실은 지어내지 않습니다.")
KEEP_RULE = "원고에 우리 회사 자료를 쓴 문장이 있으면 그 사실·연도·표기를 바꾸지 마세요."


def internal_block(rec):
    """초안 지시에 넣는 사내 맥락 — 멘토가 넣기로 한 대목만."""
    if not rec or not rec.get("on") or not rec.get("excerpt"):
        return ""
    return "\n".join([f"[우리 회사 자료 — {rec['label']}] 멘토가 이 글에 넣기로 한 사내 자료의 대목입니다.",
                      f"쓸 방향: {rec.get('use', '')}", f"쓸 사실: {rec.get('fact', '')}", f"주의: {rec.get('caution', '')}",
                      INTERNAL_RULE, "--- 대목 ---", rec["excerpt"]])


def load(brief):
    """글 설정에 딸린 사내 맥락(runs/mine/<글>/internal.json) — 없거나 뺐으면 None."""
    p = ROOT / brief.get("from_mine", "") / "internal.json" if brief.get("from_mine") else None
    if not p or not p.is_file():
        return None
    rec = json.loads(p.read_text(encoding="utf-8"))
    return rec if rec.get("on") and rec.get("excerpt") else None


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    a = sys.argv[1:]
    if a[:1] == ["--search"]:
        ds = docs()
        for s, c in search(" ".join(a[1:])):
            print(f"{s:.3f} {label(ds[c['doc']])}\n      {c['text'][:120].replace(chr(10), ' ')}")
    elif a[:1] == ["--glossary"]:
        print(glossary())
    elif a[:1] == ["--refresh"]:
        print(len(docs(force=True)), "건 ·", len(chunks()), "대목")
    else:
        print(__doc__)
