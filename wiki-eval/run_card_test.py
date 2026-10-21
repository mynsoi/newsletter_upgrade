"""카드 비교 시험 (2026-10-21) — 같은 원문 40편으로 카드를 네 방식으로 만들고, 같은 묶기·거르기를 거쳐 주제를 나란히 본다.

  A0  astra · 멘토 원래 카드(있었던 일 1개 + 글쓴이가 하는 말) — wiki.py card_prompt 그대로
  A   astra · 새 카드 형식
  B   Claude Haiku 5.5 · 새 카드 형식   (main Actions에서 자동으로 돌릴 후보)
  C   Claude Sonnet 5.5 · 새 카드 형식  (〃, 더 좋은 모델)
  새 카드 형식 = 글쓴이가 하는 말 + 있었던 일 1~4개 + 재료 유형

뒷단계는 넷 다 같다: 묶기(astra, wiki.group_prompt) → 거르기(Claude Opus 5.5, wiki.filter_prompt — 멘토 판정 예시 포함).
주제 지도(wiki/)·Supabase에는 아무것도 쓰지 않는다(DB는 표본 고를 때 읽기만). 결과는 runs/card-test/<시각>/.

  python3 -I wiki-eval/run_card_test.py --run            표본 → 카드 → 묶기·거르기 → 점검 (중간 결과가 있으면 이어서)
  python3 -I wiki-eval/run_card_test.py --page <폴더>    가린 비교 페이지(docs/)만 다시 만들기
"""
import argparse
import json
import os
import random
import re
import ssl
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import wiki as W  # noqa: E402  카드·묶기·거르기 프롬프트와 astra 호출을 그대로 쓴다

RUNS = ROOT / "runs" / "card-test"
SRC = ROOT / "sources"
QUOTA = {"T2": 12, "T3": 14, "T4": 10, "T1": 4}  # 40편 — 분류별로 고르게
PER_SOURCE = 2  # 한 소스에서 최대 2편
MAX_CHARS = 60000  # 모든 방식에 같은 길이로 넣는다(초장문만 잘림)
METHODS = ["A0", "A", "B", "C"]
MODELS = {"B": "claude-haiku-5-5", "C": "claude-sonnet-5-5"}
FILTER_MODEL = "claude-opus-5-5"
GROUP_BY = os.environ.get("CARD_TEST_GROUP", "opus")  # opus | astra


# ---------- 표본 ----------

def sample(d):
    f = d / "sample.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    import psycopg
    sc = json.loads((SRC / "db_scope.json").read_text(encoding="utf-8"))
    idx = json.loads((SRC / "db_index.json").read_text(encoding="utf-8"))
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None) as c:
        c.read_only = True
        rows = c.execute("""SELECT id, source_id, tier FROM documents WHERE source_id = ANY(%s) AND status = 'enriched'
                            AND coalesce(summary_only, 0) = 0 AND length(body) >= 800 AND source_id <> 'manual'""",
                         (list(sc["sources"]),)).fetchall()
    rnd = random.Random(20261021)
    rnd.shuffle(rows)
    out, per = [], {}
    for doc_id, sid, tier in rows:
        if doc_id not in idx or QUOTA.get(tier, 0) <= sum(1 for x in out if x["tier"] == tier) or per.get(sid, 0) >= PER_SOURCE:
            continue
        per[sid] = per.get(sid, 0) + 1
        out.append({"doc_id": doc_id, "source": sid, "tier": tier, "rel": idx[doc_id]})
    f.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def key(s):
    return W.key(s["rel"])


def text_of(s):
    return W.body(s["rel"])[:MAX_CHARS]


def title_of(s):
    t = (SRC / s["rel"]).read_text(encoding="utf-8")
    m = re.search(r"^title: (.*)$", t.split("---", 2)[1], re.M)
    return m.group(1).strip() if m else ""


# ---------- 새 카드 형식 ----------

def new_card_prompt(s):
    return "\n\n".join([
        f"아래 [원문]을 재료로 {W.READER} 칼럼을 쓰려고 합니다. 제목은 나중에 따로 정합니다. 지금은 이 원문을 칼럼 재료 카드 한 장으로 정리해 주세요.",
        "출력: JSON 하나만(다른 설명 없이).\n"
        '{"글쓴이가 하는 말": "...", "있었던 일": ["...", "..."], "재료 유형": "사례형"}\n'
        "- 글쓴이가 하는 말: 원문 글쓴이가 가장 하고 싶은 주장을 우리말 한두 문장으로. 일반적인 교훈으로 바꾸지 않고 글쓴이의 주장 그대로.\n"
        "- 있었던 일: 원문 속 사람이나 조직이 실제로 겪거나 한 일 1~4개, 중요한 것부터. 하나마다 두세 문장으로 누가(회사·사람 이름) 무엇을 했고 무엇이 드러났는지. "
        "사실과 숫자는 원문에 있는 그대로. 원문에 실제로 있었던 일이 없으면 빈 배열.\n"
        "- 재료 유형: 사례형(특정 조직·사람이 한 일이 중심) · 데이터형(설문·통계 수치가 중심) · 의견형(글쓴이 견해가 중심) · 재료 없음(홍보·공지, 일하는 방식에 대한 이야기가 없음) 중 하나.\n"
        "- 말끝은 모두 '~다'로 맞춥니다.",
        "지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다. 원문이 가장 하고 싶은 말을 붙잡고, 사소한 세부에 매달리지 않습니다.",
        W.ANSWER_ONLY, W.GUARD,
        f"=== [원문] {title_of(s)} ===\n{text_of(s)}",
    ])


def parse_new(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    eps = [e for e in d.get("있었던 일", []) if isinstance(e, str) and e.strip()]
    return {"글쓴이가 하는 말": str(d.get("글쓴이가 하는 말", "")).strip(), "episodes": eps,
            "재료 유형": str(d.get("재료 유형", "")).strip(),
            # 묶기·거르기 프롬프트(wiki.py)가 읽는 모양으로
            "있었던 일": " ".join(f"({i}) {e}" for i, e in enumerate(eps, 1)) or "(원문에 있었던 일 없음)"}


def parse_mentor(text):
    sec = {}
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(있었던 일|글쓴이가 하는 말)\s*[:：]\s*(.*)$", line)
        if m:
            sec[m.group(1)] = m.group(2).strip()
    if not sec.get("있었던 일"):
        return None
    return {"있었던 일": sec["있었던 일"], "글쓴이가 하는 말": sec.get("글쓴이가 하는 말", ""), "episodes": [sec["있었던 일"]], "재료 유형": ""}


# ---------- 모델 부르기 ----------

def api():
    import anthropic
    k = os.environ.get("ANTHROPIC_API_KEY") or subprocess.run(
        ["powershell", "-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')"],
        capture_output=True, text=True).stdout.strip()
    # truststore가 Python 3.13에서 재귀 오류를 내서(2026-10-21 확인) 기본 SSL 문맥을 직접 준다. 데스크톱 앱이 넣는 ANTHROPIC_BASE_URL은 쓰지 않는다
    return anthropic.Anthropic(api_key=k, base_url="https://api.anthropic.com",
                               http_client=anthropic.DefaultHttpxClient(verify=ssl.create_default_context()))


USAGE = {}


def claude_api(client, model, prompt, d, effort="medium", max_tokens=8000):
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    for attempt in range(3):
        try:
            with client.messages.stream(model=model, max_tokens=max_tokens, output_config={"effort": effort},
                                        messages=[{"role": "user", "content": prompt}]) as st:
                msg = st.get_final_message()
            break
        except Exception as e:  # 일시 오류만 두 번 더
            (d / "run.log").write_text(repr(e), encoding="utf-8")
            if attempt == 2:
                return ""
            time.sleep(10 * (attempt + 1))
    if msg.stop_reason == "refusal":
        (d / "run.log").write_text("refusal", encoding="utf-8")
        return ""
    out = "".join(b.text for b in msg.content if b.type == "text")
    (d / "output.md").write_text(out, encoding="utf-8")
    u = USAGE.setdefault(model, {"in": 0, "out": 0, "calls": 0})
    u["in"] += msg.usage.input_tokens
    u["out"] += msg.usage.output_tokens
    u["calls"] += 1
    return W.clean(out, str(d))


# ---------- 단계 ----------

def make_cards(d, samples, m, client):
    f = d / m / "cards.json"
    cs = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    todo = [s for s in samples if key(s) not in cs]

    def one(s):
        cd = d / m / "cards" / key(s).replace("/", "-")
        if m == "A0":
            return key(s), parse_mentor(W.astra(cd, W.card_prompt(s["rel"])))
        if m == "A":
            return key(s), parse_new(W.astra(cd, new_card_prompt(s)))
        return key(s), parse_new(claude_api(client, MODELS[m], new_card_prompt(s), cd))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4 if m in ("A0", "A") else 6) as ex:
        for k, c in ex.map(one, todo):
            if c:
                cs[k] = c
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{m}] 카드 {len(cs)}/{len(samples)} · {time.time() - t0:.0f}s", flush=True)
    return cs


def group_and_filter(d, m, cs, client):
    f = d / m / "topics.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    keys = list(cs)
    # 묶기: 원래 astra(멘토 방식). 2026-10-21 첫 회차에서 카드 80장 뒤 ChatGPT 사용 한도에 걸려 네 방식 모두 Claude Opus로 같게 돌림
    prompt = W.group_prompt(keys, cs, [])
    raw = claude_api(client, FILTER_MODEL, prompt, d / m / "group", effort="high", max_tokens=16000) if GROUP_BY == "opus" else W.astra(d / m / "group", prompt)
    g = json.loads(re.search(r"\{.*\}", raw, re.S).group(0)) if re.search(r"\{.*\}", raw or "", re.S) else {"new": [{"center": k, "sources": [k]} for k in keys]}
    topics, placed = [], set()
    for nt in g.get("new", []):
        srcs = [x for x in nt.get("sources", []) if x in cs and x not in placed]
        c = nt.get("center") if nt.get("center") in srcs else (srcs[0] if srcs else None)
        if c:
            placed |= set(srcs)
            topics.append({"page": f"wiki/주제/{c.replace('/', '-')}.md", "center": c, "sources": srcs, "status": "쓸 수 있음", "title": ""})
    excluded = [{"source": x.get("source"), "reason": x.get("reason", "")} for x in g.get("excluded", []) if x.get("source") in cs]
    placed |= {x["source"] for x in excluded}
    for k in keys:  # 묶기에서 빠진 카드는 혼자 주제로
        if k not in placed:
            topics.append({"page": f"wiki/주제/{k.replace('/', '-')}.md", "center": k, "sources": [k], "status": "쓸 수 있음", "title": ""})
    out = claude_api(client, FILTER_MODEL, W.filter_prompt(topics, cs, topics), d / m / "filter", effort="high", max_tokens=32000)
    res = json.loads(re.search(r"\{.*\}", out, re.S).group(0)).get("topics", []) if re.search(r"\{.*\}", out or "", re.S) else []
    by = {Path(t["page"]).stem: t for t in topics}
    for r in res:
        t = by.get(r.get("page"))
        if t:
            t.update({k: r.get(k, "") for k in ("verdict", "line", "why", "audience")})
    data = {"topics": topics, "excluded": excluded}
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{m}] 주제 {len(topics)} · 뺌(묶기) {len(excluded)} · 거르기 {len(res)}", flush=True)
    return data


# ---------- 메시지 단위 주제 (2026-10-21 추가) ----------
# 사용자 지적: 지금 '주제'는 원문에서 있었던 일 한 줄(사례)이라, 글 주제를 고르는 사람이 무슨 글이 될지 알 수 없다.
# → 주제 = 우리 독자에게 할 핵심 메시지 한 문장, 그 아래에 받치는 사례 1~3개(가능하면 다른 발행처). 묶는 기준도 '같은 메시지를 받치는가'.

def site_name(k):
    t = (SRC / W.rel(k)).read_text(encoding="utf-8")
    m = re.search(r"^site_name: (.*)$", t.split("---", 2)[1], re.M)
    return m.group(1).strip() if m else k.split("/")[0]


def message_prompt(cs):
    cards = "\n\n".join(
        f"[{k}] 발행처: {site_name(k)}\n글쓴이가 하는 말: {c.get('글쓴이가 하는 말', '')}\n있었던 일: {c.get('있었던 일', '')}"
        for k, c in cs.items())
    ex = W.EXAMPLES.read_text(encoding="utf-8") if W.EXAMPLES.exists() else "(아직 없음)"
    return "\n\n".join([
        f"아래는 {W.READER} 칼럼 재료로 모은 원문 카드들입니다. 칼럼을 쓸 사람이 고를 '주제' 목록을 만들어 주세요.",
        "주제란: 우리 독자(개발자가 아닌 사무·현장 직원)에게 할 **핵심 메시지 한 문장**입니다. 글 한 편이 끝까지 끌고 갈 주장이어야 합니다.\n"
        "- 좋은 주제: 일반적이면서 논리가 있는 주장. 읽는 사람이 '아, 이런 글이 되겠구나'를 바로 알 수 있음. 통념을 뒤집거나 긴장이 있는 주장이면 더 좋음.\n"
        "- 나쁜 주제: ① 특정 회사·연구의 사실 한 줄(그건 사례) ② '~부터 시작하자', 'AI를 잘 쓰려면 ~해야 한다' 같은 교육 자료식 구호 ③ 여러 이야기를 뭉뚱그린 분야 이름.\n"
        "- 주제는 반드시 아래 카드의 사례가 받쳐 줘야 합니다. 사례 없이 그럴듯하기만 한 주제는 만들지 않습니다.",
        "할 일:\n"
        "1. 같은 메시지를 받쳐 주는 카드끼리 한 주제로 묶습니다. 원문 글쓴이의 주장이 똑같을 필요는 없고, 우리 독자에게 같은 메시지를 보여 주면 됩니다.\n"
        "2. 주제마다 사례 1~3개를 고릅니다. 가능하면 서로 다른 발행처에서. 첫 번째가 중심 사례입니다. 메시지에 반대되거나 조건을 다는 사례가 있으면 role을 '반례'로.\n"
        "3. 사례마다 line: 그 카드의 있었던 일 한 줄(누가 무엇을 했고 무엇이 드러났는지, 이름·숫자 그대로, 60자 안팎).\n"
        "4. 판정: [판정 예시]의 결을 따라 우리 직원에게 쓸모 있는지 쓸 만함 · 보통 · 뺌. why 한 줄, audience(팀장급·사수급·신입사원·전 직원 중 하나 이상, '·'로).\n"
        "5. 어느 주제에도 쓸 수 없는 카드(우리 독자와 무관하거나 재료가 없는 것)는 excluded에 이유와 함께. 모든 카드는 주제 하나에 들어가거나 excluded에 있어야 합니다(한 카드를 두 주제에 쓰지 않음).",
        "출력: JSON 하나만.\n"
        '{"topics": [{"주제": "...", "cases": [{"key": "hbr-korea/0001", "role": "중심", "line": "..."}], "verdict": "쓸 만함", "why": "...", "audience": "전 직원"}], '
        '"excluded": [{"key": "...", "reason": "..."}]}  — key는 카드의 [ ] 안 그대로.',
        W.ANSWER_ONLY, W.GUARD,
        "=== [판정 예시] ===\n" + ex,
        "=== [카드] ===\n" + cards,
    ])


def message_topics(d, m, cs, client):
    f = d / m / "messages.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    out = claude_api(client, FILTER_MODEL, message_prompt(cs), d / m / "message", effort="high", max_tokens=32000)
    mt = re.search(r"\{.*\}", out or "", re.S)
    data = json.loads(mt.group(0)) if mt else {"topics": [], "excluded": []}
    for tp in data.get("topics", []):
        tp["cases"] = [c for c in tp.get("cases", []) if c.get("key") in cs]
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{m}] 메시지 주제 {len(data.get('topics', []))} · 뺌 {len(data.get('excluded', []))}", flush=True)
    return data


def run_messages(dir_):
    d = (ROOT / dir_).resolve()
    client = api()
    cards = {m: json.loads((d / m / "cards.json").read_text(encoding="utf-8")) for m in METHODS}
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda m: message_topics(d, m, cards[m], client), METHODS))
    u = d / "usage-messages.json"
    u.write_text(json.dumps(USAGE, ensure_ascii=False, indent=1), encoding="utf-8")
    page(d)


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
LATIN = re.compile(r"\b[A-Z][A-Za-z0-9&.\-]{1,}(?:\s+[A-Z][A-Za-z0-9&.\-]+)*")


def check(samples, cs):
    """카드 속 숫자·영문 고유명사가 원문에 실제로 있는지 — 지어내기 점검(자동, 거친 기준)."""
    body = {key(s): text_of(s) for s in samples}
    n_ok = n_all = p_ok = p_all = 0
    for k, c in cs.items():
        t = body.get(k, "")
        flat = t.replace(",", "")
        txt = " ".join([c.get("글쓴이가 하는 말", "")] + c.get("episodes", []))
        for x in set(NUM.findall(txt)):
            x2 = x.replace(",", "")
            if len(x2) < 2 and "." not in x2:
                continue  # 한 자리 수(1~9)는 서술에 흔해 뺀다
            n_all += 1
            n_ok += x2 in flat
        for x in set(LATIN.findall(txt)):
            p_all += 1
            p_ok += x in t
    return {"num": [n_ok, n_all], "name": [p_ok, p_all]}


# ---------- 가린 비교 페이지 ----------

def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page(d):
    samples = json.loads((d / "sample.json").read_text(encoding="utf-8"))
    names = {s["rel"]: f"{s['source']} · {title_of(s)[:70]}" for s in samples}
    labels = ["가", "나", "다", "라"]
    order = METHODS[:]
    rnd = random.Random(d.name + "-blind")
    while order == METHODS:  # 라벨이 방식 순서와 같으면 가린 의미가 없다(첫 회차에서 그렇게 나옴)
        rnd.shuffle(order)
    lab = dict(zip(order, labels))  # 방식 → 라벨
    data, cards, checks = {}, {}, {}
    for m in METHODS:
        cards[m] = json.loads((d / m / "cards.json").read_text(encoding="utf-8")) if (d / m / "cards.json").exists() else {}
        data[m] = json.loads((d / m / "topics.json").read_text(encoding="utf-8")) if (d / m / "topics.json").exists() else {"topics": [], "excluded": []}
        checks[m] = check(samples, cards[m])
    cnt = lambda m, v: sum(1 for t in data[m]["topics"] if t.get("verdict") == v)
    rows = ""
    for m in sorted(METHODS, key=lambda x: lab[x]):
        ts = data[m]["topics"]
        ck = checks[m]
        pct = lambda a: f"{a[0]}/{a[1]}" + (f" ({a[0] * 100 // a[1]}%)" if a[1] else "")
        mt = {}
        for c in cards[m].values():
            mt[c.get("재료 유형") or "—"] = mt.get(c.get("재료 유형") or "—", 0) + 1
        rows += (f"<tr><th>{lab[m]}</th><td>{len(cards[m])}/40</td><td>{len(ts)}</td><td>{sum(1 for t in ts if len(t['sources']) > 1)}</td>"
                 f"<td class=g>{cnt(m, '쓸 만함')}</td><td>{cnt(m, '보통')}</td><td>{cnt(m, '뺌')}</td><td>{len(data[m]['excluded'])}</td>"
                 f"<td>{pct(ck['num'])}</td><td>{pct(ck['name'])}</td><td>{esc(' · '.join(f'{k} {v}' for k, v in mt.items()))}</td></tr>")
    cols = ""
    for m in sorted(METHODS, key=lambda x: lab[x]):
        items = ""
        for v in ("쓸 만함", "보통", "뺌", ""):
            for t in [t for t in data[m]["topics"] if (t.get("verdict") or "") == v]:
                c = cards[m].get(t["center"], {})
                srcs = "".join(f"<li>{esc(names.get(W.rel(x), x))}</li>" for x in t["sources"])
                items += (f"<details class='t v{['쓸 만함', '보통', '뺌', ''].index(v)}'><summary><b>{esc(v or '판정 없음')}</b> {esc(t.get('line') or c.get('있었던 일', '')[:80])}"
                          f"{' <span class=multi>원문 ' + str(len(t['sources'])) + '</span>' if len(t['sources']) > 1 else ''}</summary>"
                          f"<p><i>왜</i> {esc(t.get('why'))}</p><p><i>대상</i> {esc(t.get('audience'))}</p>"
                          f"<p><i>글쓴이가 하는 말</i> {esc(c.get('글쓴이가 하는 말'))}</p><ul>{srcs}</ul></details>")
        if data[m]["excluded"]:
            items += "<details class=t><summary>묶기에서 뺀 원문 " + str(len(data[m]["excluded"])) + "</summary><ul>" + "".join(
                f"<li>{esc(names.get(W.rel(x['source']), x['source']))} — {esc(x['reason'])}</li>" for x in data[m]["excluded"]) + "</ul></details>"
        cols += f"<section><h3>{lab[m]}</h3>{items}</section>"
    per = ""
    for s in samples:
        k = key(s)
        cells = ""
        for m in sorted(METHODS, key=lambda x: lab[x]):
            c = cards[m].get(k)
            if not c:
                cells += "<td class=miss>카드 없음</td>"
                continue
            eps = "".join(f"<li>{esc(e)}</li>" for e in c.get("episodes", []))
            cells += f"<td><p class=th>{esc(c.get('글쓴이가 하는 말'))}</p><ol>{eps}</ol>{'<span class=mt>' + esc(c['재료 유형']) + '</span>' if c.get('재료 유형') else ''}</td>"
        per += f"<tr><th>{esc(names[s['rel']])}<br><small>{s['tier']}</small></th>{cells}</tr>"
    msec, mrows = "", ""
    if all((d / m / "messages.json").exists() for m in METHODS):
        mcols = ""
        for m in sorted(METHODS, key=lambda x: lab[x]):
            md = json.loads((d / m / "messages.json").read_text(encoding="utf-8"))
            tps = md.get("topics", [])
            pubs = [len({c["key"].split("/")[0] for c in tp["cases"]}) for tp in tps]
            mrows += (f"<tr><th>{lab[m]}</th><td>{len(tps)}</td><td>{sum(1 for x in pubs if x > 1)}</td>"
                      f"<td>{(sum(len(tp['cases']) for tp in tps) / len(tps)) if tps else 0:.1f}</td>"
                      f"<td class=g>{sum(1 for tp in tps if tp.get('verdict') == '쓸 만함')}</td><td>{sum(1 for tp in tps if tp.get('verdict') == '보통')}</td>"
                      f"<td>{sum(1 for tp in tps if tp.get('verdict') == '뺌')}</td><td>{len(md.get('excluded', []))}</td></tr>")
            items = ""
            for v in ("쓸 만함", "보통", "뺌"):
                for tp in [x for x in tps if x.get("verdict") == v]:
                    cases = "".join(f"<li><span class=role>{esc(c.get('role'))}</span> {esc(c.get('line'))} <small>— {esc(site_name(c['key']))}</small></li>" for c in tp["cases"])
                    items += (f"<details class='t v{['쓸 만함', '보통', '뺌'].index(v)}' {'open' if v == '쓸 만함' else ''}><summary><b>{esc(v)}</b> <span class=msg>{esc(tp.get('주제'))}</span></summary>"
                              f"<ul class=cases>{cases}</ul><p><i>왜</i> {esc(tp.get('why'))}</p><p><i>대상</i> {esc(tp.get('audience'))}</p></details>")
            if md.get("excluded"):
                items += "<details class=t><summary>주제에 못 쓴 카드 " + str(len(md["excluded"])) + "</summary><ul>" + "".join(
                    f"<li>{esc(names.get(W.rel(x.get('key', '')), x.get('key')))} — {esc(x.get('reason'))}</li>" for x in md["excluded"]) + "</ul></details>"
            mcols += f"<section><h3>{lab[m]}</h3>{items}</section>"
        msec = (f"<h2>③ 메시지 단위 주제 (같은 카드, 다시 묶음)</h2><div class=note>주제 = 우리 독자에게 할 핵심 메시지 한 문장, 그 아래 받치는 사례(가능하면 다른 발행처). "
                f"②의 '주제'는 원문에서 있었던 일 한 줄(사실상 사례)이라 무슨 글이 될지 알기 어렵다는 지적(2026-10-21)으로 추가. 쓸 만함은 펼쳐 둠.</div>"
                f"<table class=sum><tr><th></th><td>주제</td><td>여러 발행처 주제</td><td>주제당 사례</td><td>쓸 만함</td><td>보통</td><td>뺌</td><td>못 쓴 카드</td></tr>{mrows}</table>"
                f"<div class=cols style='margin-top:12px'>{mcols}</div>")
    reveal = " · ".join(f"{lab[m]} = {m} ({ {'A0': 'astra · 멘토 원래 카드', 'A': 'astra · 새 카드', 'B': 'Haiku 5.5 · 새 카드', 'C': 'Sonnet 5.5 · 새 카드'}[m] })" for m in sorted(METHODS, key=lambda x: lab[x]))
    usage = json.loads((d / "usage.json").read_text(encoding="utf-8")) if (d / "usage.json").exists() else {}
    html = f"""<!doctype html><html lang=ko><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>카드 비교 시험</title><style>
:root{{--bg:#fafaf9;--ink:#1c1917;--ink2:#57534e;--line:#e7e5e4;--card:#fff;--good:#15803d;--soft:#f5f5f4}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0c0a09;--ink:#f5f5f4;--ink2:#a8a29e;--line:#292524;--card:#1c1917;--good:#4ade80;--soft:#171412}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 -apple-system,"Pretendard","Noto Sans KR",sans-serif}}
main{{max-width:1400px;margin:0 auto;padding:32px 16px 80px}} h1{{font-size:28px;margin:0 0 4px}} h2{{margin-top:44px;font-size:20px}}
.sub{{color:var(--ink2)}} table{{border-collapse:collapse;width:100%;background:var(--card)}} th,td{{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}}
.sum th{{width:40px;text-align:center;font-size:18px}} .g{{color:var(--good);font-weight:700}}
.cols{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} section{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}}
section h3{{margin:0 0 8px;font-size:20px;text-align:center}} details.t{{border-top:1px solid var(--line);padding:6px 2px}} details.t summary{{cursor:pointer}}
.v0 summary b{{color:var(--good)}} .v2{{opacity:.6}} .multi{{font-size:12px;background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:0 6px}}
details p,details ul{{margin:4px 0;font-size:14px}} i{{color:var(--ink2);font-style:normal;font-size:12px;margin-right:4px}}
.per td{{font-size:13.5px;width:22%}} .per th{{width:12%;font-size:13px}} .th{{font-weight:600;margin:0 0 4px}} ol{{margin:0;padding-left:18px}} .mt{{font-size:12px;color:var(--ink2)}} .miss{{color:#b91c1c}}
.msg{{font-weight:600}} .cases{{padding-left:16px}} .cases li{{margin:2px 0}} .role{{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--ink2)}}
.note{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 14px;color:var(--ink2);font-size:14px}}
@media (max-width:900px){{.cols{{grid-template-columns:1fr}} .per{{display:block;overflow-x:auto}}}}
</style></head><body><main>
<h1>카드 비교 시험</h1><p class=sub>{d.name} · 같은 원문 40편(게이트 통과, 분류별 고르게) · 네 방식(가·나·다·라)으로 카드를 만들고 같은 묶기·거르기(둘 다 Claude Opus 5.5, 멘토의 묶기·거르기 지시문과 판정 예시 그대로 — 묶기는 원래 astra지만 ChatGPT 사용 한도로 네 방식 모두 Opus로 맞춤)를 거침 · 방식은 맨 아래에서 공개</p>
<div class=note>보는 순서: ① 한눈에 표 → ② 지금 방식의 주제(사실상 사례 한 줄) → ③ 메시지 단위 주제('이 주제로 칼럼을 쓰고 싶은가') → ④ 원문별 카드(같은 원문을 네 방식이 어떻게 정리했나). 재료 유형이 비어 있는(—) 방식은 멘토 원래 카드 형식이라 기준선임이 드러납니다. 나머지 셋은 같은 새 카드 형식입니다. 숫자·영문 이름 점검은 카드 속 값이 원문에 그대로 있는지 본 거친 자동 점검입니다(번역·단위 표기 차이로 놓친 것도 셈).</div>
<h2>① 한눈에</h2><table class=sum><tr><th></th><td>카드</td><td>주제</td><td>여러 원문 주제</td><td>쓸 만함</td><td>보통</td><td>뺌</td><td>묶기에서 뺌</td><td>숫자 원문 확인</td><td>영문 이름 원문 확인</td><td>재료 유형</td></tr>{rows}</table>
<h2>② 방식별 주제 — 지금 방식(사례 단위)</h2><div class=cols>{cols}</div>
{msec}
<h2>④ 원문별 카드</h2><table class=per><tr><th>원문</th>{''.join(f'<td><b>{lab[m]}</b></td>' for m in sorted(METHODS, key=lambda x: lab[x]))}</tr>{per}</table>
<h2>방식 공개</h2><details><summary>평가를 마친 뒤 펼치기</summary><p>{esc(reveal)}</p><p class=sub>API 사용량: {esc(json.dumps(usage, ensure_ascii=False))}</p></details>
</main></body></html>"""
    out = ROOT / "docs" / f"{time.strftime('%Y-%m-%d')}-카드-비교-시험.html"
    out.write_text(html, encoding="utf-8")
    (d / "labels.json").write_text(json.dumps(lab, ensure_ascii=False), encoding="utf-8")
    print("페이지:", out.relative_to(ROOT).as_posix(), flush=True)


def run(dir_=None):
    ds = sorted(RUNS.glob("2*/")) if RUNS.exists() else []
    if dir_:
        d = (ROOT / dir_).resolve()  # 지정한 회차 폴더에서 이어서(만들어 둔 카드는 다시 만들지 않음)
    else:
        d = ds[-1] if ds and not (ds[-1] / "done").exists() else RUNS / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    print("폴더:", d.relative_to(ROOT).as_posix(), flush=True)
    samples = sample(d)
    print("표본:", len(samples), {t: sum(1 for s in samples if s["tier"] == t) for t in QUOTA}, flush=True)
    client = api()
    cards = {}
    with ThreadPoolExecutor(max_workers=4) as ex:  # 네 방식을 동시에(astra 둘, API 둘)
        for m, cs in zip(METHODS, ex.map(lambda m: make_cards(d, samples, m, client), METHODS)):
            cards[m] = cs
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda m: group_and_filter(d, m, cards[m], client), METHODS))
    (d / "usage.json").write_text(json.dumps(USAGE, ensure_ascii=False, indent=1), encoding="utf-8")
    page(d)
    (d / "done").write_text(time.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--page")
    ap.add_argument("--dir", help="--run을 이 회차 폴더에서 이어서")
    ap.add_argument("--messages", metavar="DIR", help="그 회차의 카드로 메시지 단위 주제를 만들어 페이지에 붙임")
    a = ap.parse_args()
    if a.messages:
        run_messages(a.messages)
    elif a.page:
        page(Path(a.page))
    elif a.run:
        run(a.dir)
    else:
        ap.print_help()
