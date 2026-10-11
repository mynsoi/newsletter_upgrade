"""내 주제로 쓰기 — 멘토가 주제(하고 싶은 말)와 문서를 주면, 모아 둔 원문에서 그 주제를 보여 줄 원문을 골라 글 설정을 만든다.

멘토 2026-10-11: "내가 직접 문서랑 주제를 주고, 인사이트를 골라서 글을 생성하게도 하고싶은데"
사용: python3 -I scripts/my_topic.py --new <주제 파일> [--target 팀장급] [--doc <파일> ...] [--id m-<이름>]
        → runs/mine/<글>/ (topic.txt · candidates · pick · picks.json) + sources/mine/<글>/NN.md(문서를 글자만 그대로)
        → briefs/<글>.json + 제목 후보(astra, column_pipeline --titles). 작업실 글 목록에 뜨고, 제목을 고르면 과정 1·2·3
      python3 -I scripts/my_topic.py --more <글> <말 파일> [--doc <파일> ...]  — 같은 대화에서 이어서 한 말로 원문 다시 고르기(대화 전체를 넘김)
      python3 -I scripts/my_topic.py --brief <글> [원문 키 ...]  — 고른 원문을 바꿔 글 설정을 다시 만든다(첫째가 중심, 예: linkedin/03 threads/27)
      python3 -I scripts/my_topic.py --page <글> <이름> [점검 메모]  — 결과 페이지 docs/<오늘>-<이름>.html (작업실 /docs/)
단계
1. 후보(Claude, 원문 카드 전부 — 주제 지도의 판정과 상관없이): 원문 속 사람이 한 일이 주제가 말하는 것을 보여 주는가.
   키워드·분야가 겹치는지가 아니라. 그렇게 하지 않아 생긴 일(반대편)도 후보.
2. 고르기(Claude, 후보 원문 전체): 중심 1 + 받침 0~2, 고른 원문마다 이 글에서 맡는 몫·가져올 사실, 나머지는 왜 이번에 빼는지.
   하나로 좁히는 이유 — 사례를 여럿 끼우면 무엇을 말하는지 흐려진다(criteria 4), 창간호 반려 사유도 인용 과다였다.
- 주제 문장은 받은 그대로 thesis가 된다(다듬지 않는다). 문서는 Claude·astra로 나간다 — 보내도 되는 것만 넣는다.
- 주제 지도(wiki/)는 건드리지 않는다(주제 상태·판정 예시 그대로). 글 설정에는 from_mine이 붙고, 초안은 이 표시를 보고
  "멘토가 정한 말을 원문 사례로 보여 주는" 지시를 쓴다(column_pipeline.draft_prompt).
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki as W  # 카드·원문 읽기·모델 부르기(답만 받기)를 같이 쓴다

ROOT = W.ROOT
SRC = W.SRC
MINE_RUNS = ROOT / "runs" / "mine"
MINE_SRC = SRC / "mine"
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
PY = [sys.executable, "-X", "utf8", "-I", "-u"]


# ---------- 문서 ----------

def doc_text(p):
    """문서를 글자로 — md·txt는 그대로, pdf는 pdftotext, docx·hwp 등은 LibreOffice. 요약하지 않는다."""
    p = Path(p)
    suf = p.suffix.lower()
    if suf in (".md", ".txt"):
        return p.read_text(encoding="utf-8")
    if suf == ".pdf":
        r = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            sys.exit(f"pdf를 글자로 못 바꿈: {p.name} — {r.stderr[-300:]}")
        return r.stdout
    if not SOFFICE:
        sys.exit(f"{p.name}: LibreOffice가 없어 글자로 못 바꿈 — pdf나 txt로 주세요")
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([SOFFICE, "--headless", "--convert-to", "txt:Text (encoded):UTF8", "--outdir", td, str(p)],
                       capture_output=True, timeout=180)
        out = list(Path(td).glob("*.txt"))
        if not out:
            sys.exit(f"{p.name}: 글자로 못 바꿈 — pdf나 txt로 주세요")
        return out[0].read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")  # LibreOffice txt는 BOM을 붙인다


def save_docs(k, docs, start=1):
    """문서를 sources/mine/<글>/NN.md로 — 글 설정의 sources가 sources/ 아래만 읽는다. 이어서 말할 때 올린 문서는 번호를 이어 간다."""
    out = []
    for i, p in enumerate(docs, start):
        text = doc_text(p).strip()
        if not text:
            sys.exit(f"{Path(p).name}: 글자가 비었음(그림만 있는 pdf일 수 있음)")
        f = MINE_SRC / k / f"{i:02d}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"^\d{2}-", "", Path(p).name)  # 작업실이 올린 파일은 NN-<원래 이름>
        f.write_text(f"---\nkind: 회사 자료\nname: {name}\nadded: {date.today().isoformat()}\n---\n\n{text}\n", encoding="utf-8")
        out.append([f.relative_to(SRC).as_posix(), f"회사 자료 — {name}"])
    return out


def docs_block(docs):
    return "\n\n".join(f"=== [회사 자료] {d} ===\n" + W.body(p) for p, d in docs)


# ---------- 1. 후보 (카드 전부) ----------

FOLLOW = ("[멘토 주제]는 멘토와 주고받은 대화입니다. 처음 요청이 이 글의 주제이고, 이어서 한 말은 원문을 고르는 데 대한 요청입니다. "
          "나중에 한 말을 먼저 따르고, [그때 고른 원문]은 멘토가 이미 본 결과입니다.")


def cand_prompt(topic, docs, cs, follow=False):
    cards_txt = "\n\n".join(f"[{k}]\n있었던 일: {v['있었던 일']}\n글쓴이가 하는 말: {v['글쓴이가 하는 말']}" for k, v in cs.items())
    return "\n\n".join([
        *([FOLLOW] if follow else []),
        f"멘토가 {W.READER} 칼럼의 주제를 정했습니다. [멘토 주제]는 멘토가 한 말 그대로입니다. "
        "[원문 카드]는 모아 둔 원문마다 있었던 일과 글쓴이가 하는 말을 정리한 것입니다. 이 주제로 쓸 글에 사례로 쓸 수 있는 원문 후보를 골라 주세요.",
        "고르는 기준: 키워드나 분야가 겹치는지가 아니라, 원문 속 사람이 실제로 한 일이 [멘토 주제]가 말하는 것을 보여 주는가입니다. "
        "그렇게 하지 않아서 생긴 일을 보여 주는 원문(반대편)도 후보가 됩니다. 원문이 개인·프리랜서 이야기여도 회사 직원에게 통하면 후보입니다. "
        "쓸 만한 것만 고르고, 개수는 정하지 않습니다.",
        "출력: JSON 하나만. {\"candidates\": [{\"source\": \"linkedin/03\", \"side\": \"보여 줌\", \"why\": \"...\"}]}"
        "  — source는 카드의 [ ] 안 그대로, side는 '보여 줌' 또는 '반대편', why는 원문 속 어떤 일이 주제의 어떤 말을 보여 주는지 한 줄. 관련이 깊은 순서로.",
        W.ANSWER_ONLY, W.GUARD,
        "=== [멘토 주제] ===\n" + topic,
        *([docs_block(docs)] if docs else []),
        "=== [원문 카드] ===\n" + cards_txt,
    ])


# ---------- 2. 고르기 (후보 원문 전체) ----------

def pick_prompt(topic, docs, cands, ask_target, follow=False):
    blocks = "\n\n".join(f"=== [{c['source']}] {W.label(W.rel(c['source']))} — 1차 이유({c.get('side', '')}): {c.get('why', '')} ===\n"
                         + W.body(W.rel(c["source"])) for c in cands)
    return "\n\n".join([
        *([FOLLOW] if follow else []),
        f"멘토가 정한 [멘토 주제]로 {W.READER} 칼럼 한 편(공백 제외 1,500자 이하)을 씁니다. 아래 [후보 원문]은 1차로 고른 후보입니다. "
        "원문을 끝까지 읽고 이 글에 쓸 원문을 정해 주세요.",
        "정할 것:\n"
        "- center: 글을 이끌 중심 원문 하나 — [멘토 주제]가 말하는 것을 가장 구체적인 일로 보여 주는 원문. "
        "비슷하면 회사·사람·행사 이름과 숫자가 원문에 있어 처음 듣는 독자도 바로 알아들을 수 있는 쪽을 먼저 고릅니다(이름이 없다는 이유로 빼지는 않습니다)\n"
        "- support: 중심을 받칠 원문. 없어도 되고 많아야 둘입니다. 중심과 다른 몫(반대편, 다른 자리의 사례)을 할 때만 넣습니다. "
        "한 편에 사례를 여럿 끼우면 무엇을 말하는지 흐려집니다.\n"
        "- 고른 원문마다 role(이 글에서 맡는 몫 한 줄)과 use(원문에서 가져올 사실 한두 줄 — 원문 문장을 옮기지 않고 사실만)\n"
        "- rest: 고르지 않은 후보마다 왜 이번에 빼는지 한 줄\n"
        "- point: 이 글이 말할 것 한 문장 — 독자가 한 번 듣고 그대로 따라 말할 수 있게, 중심 원문 글쓴이의 주장 안에서, [멘토 주제]에 답하게. "
        "'기준·체계·구조·문화·역량' 같은 뭉뚱그린 말 대신 일하는 장면의 말로"
        + ("\n- audience: 이 글을 가장 먼저 읽어야 할 자리 — 팀장급·사수급·신입사원·전 직원 중 하나" if ask_target else ""),
        "판단은 원문에 실제로 있는 일로 합니다. 원문에 없는 일을 덧붙이지 않습니다. "
        "고른 이유를 'AI 시대에는 ~이 중요하다' 같은 일반론으로 쓰지 말고 원문 속 일로 씁니다.",
        "출력: JSON 하나만. {\"center\": {\"source\": \"...\", \"role\": \"...\", \"use\": \"...\"}, \"support\": [{\"source\": \"...\", \"role\": \"...\", \"use\": \"...\"}], "
        "\"rest\": [{\"source\": \"...\", \"why\": \"...\"}], \"point\": \"...\"" + (", \"audience\": \"전 직원\"" if ask_target else "") + "}"
        "  — source는 [후보 원문]의 [ ] 안 그대로.",
        W.ANSWER_ONLY, W.GUARD,
        "=== [멘토 주제] ===\n" + topic,
        *([docs_block(docs)] if docs else []),
        "=== [후보 원문] ===\n" + blocks,
    ])


def point_prompt(request, center):
    """말할 것 한 문장 — 쓰기 직전에 다시 정할 때(바꿔 끼우기로 중심이 바뀜 · 예전 글). 비교 C·C2에서 쓴 지시 그대로."""
    card = W.cards().get(W.key(center), {})
    return "\n\n".join([
        f"사내 뉴스레터 칼럼을 쓰기 전에, 이 글이 말할 것을 한 문장으로 정해 주세요. 독자: {W.READER}",
        f"주제(멘토 요청): {request}",
        *([f"원문 글쓴이가 하는 말: {card['글쓴이가 하는 말']}"] if card else []),
        "조건: 독자가 한 번 듣고 그대로 따라 말할 수 있는 쉬운 한 문장. 원문 글쓴이의 주장 안에서, 멘토 요청의 주제에 답하는 문장. "
        "'기준·체계·구조·문화·역량' 같은 뭉뚱그린 말 대신 일하는 장면의 말로. 원문에 없는 사실을 더하지 않습니다.",
        "출력: 그 한 문장만. 따옴표나 설명 없이. " + W.ANSWER_ONLY, W.GUARD,
        "=== [원문] ===\n" + W.body(center),
    ])


def make_point(request, center, run_dir):
    return W.claude(Path(run_dir), point_prompt(request, center)).strip().strip('"“”')


def json_of(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else {}


# ---------- 글 설정 ----------

def make_brief(k, chosen=None):
    """picks.json(또는 멘토가 바꾼 원문 목록)으로 briefs/<글>.json을 만든다 — 주제 문장 그대로, 중심·받침·회사 자료 순."""
    d = MINE_RUNS / k
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    picks = json.loads((d / "picks.json").read_text(encoding="utf-8"))
    topic = (d / "topic.txt").read_text(encoding="utf-8").strip()
    picked = [picks["center"]] + picks.get("support", [])
    if chosen:  # 멘토가 바꿔 끼운 원문 — 맡는 몫은 고르기에서 적은 것이 있으면 그대로, 없으면 1차 이유
        info = {p["source"]: p for p in picked}
        info.update({c["source"]: {"source": c["source"], "role": c.get("why", ""), "use": ""} for c in picks.get("_candidates", []) if c["source"] not in info})
        picked = [info.get(s, {"source": s, "role": "", "use": ""}) for s in chosen]
    cs = W.cards()
    bad = [p["source"] for p in picked if p["source"] not in cs]
    if bad:
        sys.exit(f"카드가 없는 원문: {bad}")
    sources = [[W.rel(p["source"]), W.label(W.rel(p["source"]))] for p in picked] + meta["docs"]
    roles = {W.rel(p["source"]): p.get("role", "") + (f" — 가져올 사실: {p['use']}" if p.get("use") else "") for p in picked}
    point = picks.get("point", "").strip()
    b = {"topic": k, "label": topic.splitlines()[0][:80], "thesis": point or topic, "request": topic,
         **({"point": point, "point_for": W.rel(picks["center"]["source"])} if point else {}),  # 바꿔 끼워 중심이 바뀌면 쓰기 직전에 다시 정함
         "sources": sources, "roles": roles,
         "target": W.target_of(meta.get("target") or picks.get("audience", "")),
         "from_mine": d.relative_to(ROOT).as_posix()}
    bp = ROOT / "briefs" / f"{k}.json"
    old = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    b.update({x: old[x] for x in ("title", "target", "length") if x in old})  # 바꿔 끼워도 멘토가 고른 제목·대상 독자·분량은 그대로
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print("글 설정:", bp.relative_to(ROOT).as_posix(), "· 원문", [p["source"] for p in picked], "· 대상", b["target"], flush=True)
    return bp


def stage(d, s):
    """작업실 화면의 진행 막대 — 후보 · 고르기 · 제목 · 끝"""
    (d / "stage.txt").write_text(s, encoding="utf-8")


def turns(d):
    f = d / "turns.jsonl"
    if f.exists():
        return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 대화 기록이 생기기 전의 첫 요청(2026-10-11 자기평가) — 요청과 고른 결과로 만든다
    out = [{"role": "mentor", "text": (d / "topic.txt").read_text(encoding="utf-8").strip(), "docs": [], "at": 0}]
    if (d / "picks.json").exists():
        out.append({"role": "ai", **snapshot(json.loads((d / "picks.json").read_text(encoding="utf-8"))), "at": 0})
    return out


def add_turn(d, turn):
    with open(d / "turns.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({**turn, "at": time.time()}, ensure_ascii=False) + "\n")


def snapshot(picks):
    """그 차례에 고른 원문 — 화면이 지난 차례를 굳힌 채로 보여 준다."""
    return {"center": {k: picks["center"].get(k, "") for k in ("source", "role")},
            "support": [{k: p.get(k, "") for k in ("source", "role")} for p in picks.get("support", [])],
            "n_candidates": len(picks.get("_candidates", []))}


def convo_text(ts):
    """대화 전체를 고르기에 넘기는 글 — 멘토 말은 받은 그대로, 그 사이에 그때 고른 원문."""
    out, first = [], True
    for x in ts:
        if x["role"] == "mentor":
            out.append(("[처음 요청]" if first else "[이어서 한 말]") + "\n" + x["text"])
            first = False
        else:
            s = [x["center"]] + x.get("support", [])
            out.append("[그때 고른 원문] " + " / ".join(f"{p['source']}({'중심' if i == 0 else '받침'}): {p.get('role', '')}" for i, p in enumerate(s)))
    return "\n\n".join(out)


def choose(d, topic, saved, ask_target, follow=False):
    """1. 후보(카드 전부) → 2. 고르기(후보 원문 통째) → picks.json"""
    t0 = time.time()
    cs = W.cards()
    n = len(list(d.glob("picks-*.json"))) + (2 if (d / "picks.json").exists() else 1)  # 이어서 말한 차례는 폴더를 따로
    sfx = "" if n == 1 else f"-{n}"
    stage(d, "후보")
    cands = json_of(W.claude(d / f"candidates{sfx}", cand_prompt(topic, saved, cs, follow))).get("candidates", [])
    cands = [c for c in cands if c.get("source") in cs]
    print(f"후보 {len(cands)}편 · {time.time() - t0:.0f}s", flush=True)
    if not cands:
        sys.exit("후보가 없음 — 로그: " + str(d / f"candidates{sfx}"))
    stage(d, "고르기")
    picks = json_of(W.claude(d / f"pick{sfx}", pick_prompt(topic, saved, cands, ask_target, follow)))
    if not picks.get("center", {}).get("source") in cs:
        sys.exit("고르기 결과가 비었음 — 로그: " + str(d / f"pick{sfx}"))
    picks["support"] = [p for p in picks.get("support", []) if p.get("source") in cs]
    picks["_candidates"] = cands
    if (d / "picks.json").exists():  # 앞 차례는 picks-N.json으로 남긴다
        (d / "picks.json").rename(d / f"picks-{n - 1}.json")
    (d / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"고르기 · 중심 {picks['center']['source']} · 받침 {[p['source'] for p in picks['support']]} · {time.time() - t0:.0f}s", flush=True)
    return picks


def titles(bp, k):
    """제목 후보(astra) — 다시 뽑으면 앞 회차는 astra-N.md로 남긴다(작업실 제목 탭과 같은 방식)."""
    d = ROOT / "runs" / "titles0" / k
    if (d / "astra.md").exists():
        n = len(list(d.glob("astra-*.md"))) + 1
        (d / "astra.md").rename(d / f"astra-{n}.md")
        if (d / "message.txt").exists():
            (d / "message.txt").rename(d / f"message-{n}.txt")
    subprocess.run(PY + ["scripts/column_pipeline.py", "--titles", bp.relative_to(ROOT).as_posix()], cwd=ROOT)


def new(topic_file, target="", docs=(), k=""):
    topic = Path(topic_file).read_text(encoding="utf-8").strip()
    if not topic:
        sys.exit("주제가 비었음")
    if target and target not in W.TARGETS:
        sys.exit(f"대상 독자는 {W.TARGETS} 중 하나")
    k = k or "m-" + time.strftime("%Y%m%d-%H%M%S")  # 작업실은 요청을 받을 때 이름을 정해 넘긴다(--id)
    if not re.match(r"^m-[\w-]+$", k):
        sys.exit("잘못된 이름: " + k)
    d = MINE_RUNS / k
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stage(d, "문서")
    (d / "topic.txt").write_text(topic + "\n", encoding="utf-8")
    saved = save_docs(k, docs)
    (d / "meta.json").write_text(json.dumps({"target": target, "docs": saved}, ensure_ascii=False, indent=1), encoding="utf-8")
    add_turn(d, {"role": "mentor", "text": topic, "docs": [x[1].removeprefix("회사 자료 — ") for x in saved]})
    picks = choose(d, topic, saved, not target)
    add_turn(d, {"role": "ai", **snapshot(picks)})
    bp = make_brief(k)
    stage(d, "제목")
    titles(bp, k)
    stage(d, "끝")
    print(f"끝 · {k} · {time.time() - t0:.0f}s")
    return k


def more(k, msg_file, docs=()):
    """--more <글> <말 파일> [--doc …] — 같은 대화에서 이어서 한 말로 원문을 다시 고른다(대화 전체를 넘김).
    주제(thesis)는 처음 요청 그대로. 쓰기를 시작한 글은 다시 고르지 않는다. 제목을 아직 안 골랐으면 제목 후보도 다시."""
    d = MINE_RUNS / k
    msg = Path(msg_file).read_text(encoding="utf-8").strip()
    if not msg or not (d / "meta.json").exists():
        sys.exit("이어서 할 말이 비었거나 없는 대화: " + k)
    if (ROOT / "runs" / "columns" / k / "draft.md").exists():
        sys.exit("쓰기를 시작한 글은 원문을 다시 고르지 않습니다 — 새 대화로 시작하세요")
    t0 = time.time()
    stage(d, "문서")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    saved = save_docs(k, docs, start=len(meta["docs"]) + 1)
    meta["docs"] += saved
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if not (d / "turns.jsonl").exists():  # 대화 기록 전의 첫 차례를 먼저 적어 둔다
        for x in turns(d):
            add_turn(d, {k_: v for k_, v in x.items() if k_ != "at"})
    add_turn(d, {"role": "mentor", "text": msg, "docs": [x[1].removeprefix("회사 자료 — ") for x in saved]})
    picks = choose(d, convo_text(turns(d)), meta["docs"], not meta.get("target"), follow=True)
    add_turn(d, {"role": "ai", **snapshot(picks)})
    bp = make_brief(k)
    b = json.loads(bp.read_text(encoding="utf-8"))
    b.pop("sources_ok", None)  # 새로 고른 원문은 다시 확인받는다
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    if not b.get("title"):
        stage(d, "제목")
        titles(bp, k)
    stage(d, "끝")
    print(f"이어서 고르기 끝 · {k} · {time.time() - t0:.0f}s")


# ---------- 결과 페이지 (작업실 /docs/) ----------

def src_link(k):
    a, _, u = W.src_meta(k)
    return f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(k)} · {esc(a)}</a>'


def esc(s):
    import html
    return html.escape(str(s or ""))


def page(k, name, note=""):
    """--page <글> <이름> [점검 메모 파일] → docs/<오늘>-<이름>.html (같은 주소는 Mac 브라우저가 예전 판을 보여 줘서 바꿀 때마다 새 이름으로).
    점검 메모: 보여 주기 전에 원문과 대조한 것 — 한 줄에 하나, 맨 위 요약표 아래에 붙는다."""
    d = MINE_RUNS / k
    topic = (d / "topic.txt").read_text(encoding="utf-8").strip()
    picks = json.loads((d / "picks.json").read_text(encoding="utf-8"))
    b = json.loads((ROOT / "briefs" / f"{k}.json").read_text(encoding="utf-8"))
    cs = W.cards()
    tf = ROOT / "runs" / "titles0" / k / "astra.md"
    titles = [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()] if tf.exists() else []
    first = {c["source"]: c for c in picks.get("_candidates", [])}
    chosen = [("중심", picks["center"])] + [("받침", p) for p in picks.get("support", [])]
    cards_html = "".join(f"""<article class="g">
  <div class="top"><span class="tag{' hi' if r == '중심' else ''}">{r}</span><span class="src">{src_link(p['source'])}</span><span class="side">{esc(first.get(p['source'], {}).get('side', ''))}</span></div>
  <p class="role">{esc(p.get('role', ''))}</p>
  <dl>
    <dt>있었던 일</dt><dd>{esc(cs.get(p['source'], {}).get('있었던 일', ''))}</dd>
    <dt>가져올 사실</dt><dd>{esc(p.get('use', ''))}</dd>
  </dl>
</article>""" for r, p in chosen)
    rest = "".join(f'<tr><td class="src">{src_link(x["source"])}</td><td><span class="side">{esc(first.get(x["source"], {}).get("side", ""))}</span> '
                   f'{esc(first.get(x["source"], {}).get("why", ""))}<br><span class="why">이번에 뺀 이유 — {esc(x.get("why", ""))}</span></td></tr>'
                   for x in picks.get("rest", []))
    title_html = "".join(f"<li>{esc(t)}</li>" for t in titles)
    docs = [x for x in b["sources"] if x[0].startswith("mine/")]
    notes = [l.strip().lstrip("-").strip() for l in Path(note).read_text(encoding="utf-8").splitlines() if l.strip()] if note else []
    note_html = ('<div class="check"><b>보여 드리기 전 점검</b><ul>' + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul></div>") if notes else ""
    PAGE = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>내 주제로 고르기</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root {{ --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; word-break:keep-all; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:0 32px 80px; }}
  header {{ padding:56px 0 8px; }}
  h1 {{ font-size:30px; font-weight:700; margin:0 0 18px; }}
  table.sum {{ width:100%; border-collapse:collapse; background:var(--surface-soft); border-radius:14px; overflow:hidden; }}
  table.sum th {{ text-align:left; width:130px; font-size:13px; font-weight:600; color:var(--muted); padding:12px 18px; vertical-align:top; }}
  table.sum td {{ font-size:15px; line-height:1.7; padding:12px 18px 12px 0; }}
  table.sum tr + tr th, table.sum tr + tr td {{ border-top:1px solid var(--hairline-soft); }}
  .quote {{ font-size:16px; font-weight:600; }}
  table.sum a {{ color:var(--ink); text-decoration:none; font-weight:600; }} table.sum a:hover {{ text-decoration:underline; }}
  h2 {{ font-size:22px; font-weight:700; margin:44px 0 6px; }}
  h2 small {{ font-size:14px; font-weight:500; color:var(--muted); margin-left:8px; }}
  .g {{ border-top:1px solid var(--hairline); padding:20px 0; }}
  .top {{ display:flex; gap:10px; align-items:baseline; }}
  .tag {{ font-size:12.5px; font-weight:700; color:var(--muted); background:var(--surface-soft); border-radius:6px; padding:2px 8px; }}
  .tag.hi {{ color:var(--primary); background:#fff1f3; }}
  .side {{ font-size:12.5px; color:var(--muted-soft); }}
  .src, .src a {{ font-size:12.5px; color:var(--muted-soft); text-decoration:none; }}
  .src a:hover {{ text-decoration:underline; }}
  .role {{ font-size:17.5px; font-weight:600; line-height:1.6; margin:8px 0 10px; }}
  dl {{ margin:0; display:grid; grid-template-columns:96px 1fr; gap:6px 12px; font-size:14.5px; line-height:1.7; }}
  dt {{ color:var(--muted); }} dd {{ margin:0; color:var(--body); }}
  ol.titles {{ font-size:17px; line-height:2; padding-left:24px; margin:10px 0 0; }}
  details {{ margin-top:40px; border-top:1px solid var(--hairline); padding-top:16px; }}
  summary {{ font-size:18px; font-weight:700; cursor:pointer; }}
  table.rest {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  table.rest td {{ border-top:1px solid var(--hairline-soft); padding:12px 8px; vertical-align:top; font-size:14.5px; line-height:1.65; }}
  table.rest td.src {{ width:200px; }}
  .why {{ color:var(--muted); }}
  .note {{ font-size:14.5px; line-height:1.8; color:var(--body); }}
  .check {{ border:1px solid var(--hairline); border-radius:14px; padding:14px 22px; margin:40px 0 0; font-size:14.5px; line-height:1.8; color:var(--body); }}
  .check b {{ color:var(--ink); }} .check ul {{ margin:6px 0 0; padding-left:18px; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>내 주제로 원문 고르기</h1>
  <table class="sum">
    <tr><th>멘토 주제</th><td class="quote">{esc(topic)}</td></tr>
    <tr><th>중심 원문</th><td>{src_link(picks['center']['source'])} — {esc(picks['center'].get('role', ''))}</td></tr>
    <tr><th>받침</th><td>{'<br>'.join(src_link(p['source']) + ' — ' + esc(p.get('role', '')) for p in picks.get('support', [])) or '없음'}</td></tr>
    <tr><th>회사 자료</th><td>{'<br>'.join(esc(x[1]) for x in docs) or '없음'}</td></tr>
    <tr><th>대상 독자</th><td>{esc(b.get('target', ''))}</td></tr>
    <tr><th>후보 → 고름</th><td>카드 {len(cs)}편 → 후보 {len(first)}편 → {len(chosen)}편</td></tr>
  </table>
</header>

<h2>고른 원문 <small>이 글에서 맡는 몫 · 있었던 일 · 가져올 사실</small></h2>
{cards_html}

<h2>제목 후보 <small>astra · 고르면 과정 1·2·3</small></h2>
<ol class="titles">{title_html}</ol>

{note_html}

<details>
  <summary>나머지 후보 {len(picks.get('rest', []))}편 — 1차 이유 · 이번에 뺀 이유</summary>
  <table class="rest">{rest}</table>
</details>

<details>
  <summary>이렇게 골랐습니다</summary>
  <div class="note">
    <p>1. 후보 — Claude가 원문 카드 {len(cs)}편 전부(주제 지도 판정과 상관없이)를 멘토 주제와 맞춰 봅니다. 키워드가 겹치는지가 아니라, 원문 속 사람이 한 일이 주제가 말하는 것을 보여 주는지로 고릅니다. 그렇게 하지 않아 생긴 일(반대편)도 후보에 넣습니다.</p>
    <p>2. 고르기 — 후보 원문을 통째로 읽고 중심 1편과 받침 0~2편을 정합니다. 한 편에 사례를 여럿 끼우면 무엇을 말하는지 흐려져서입니다(기준 4).</p>
    <p>3. 글 설정 — 멘토 주제를 받은 그대로 "이 글이 말할 것"에 넣고, 초안에는 "말할 것은 멘토가 정했고 원문은 그 말을 보여 주는 사례"라고 알립니다. 주제 지도의 판정·상태는 바꾸지 않습니다.</p>
  </div>
</details>
</div>
</body>
</html>
"""
    out = ROOT / "docs" / f"{date.today().isoformat()}-{name}.html"
    out.write_text(PAGE, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--new"]:
        rest, target, docs, k = a[2:], "", [], ""
        while rest:
            if rest[0] == "--id":
                k, rest = rest[1], rest[2:]
            elif rest[0] == "--target":
                target, rest = rest[1], rest[2:]
            elif rest[0] == "--doc":
                docs.append(rest[1])
                rest = rest[2:]
            else:
                sys.exit("모르는 인자: " + rest[0])
        new(a[1], target, docs, k)
    elif a[:1] == ["--more"]:
        rest, docs = a[3:], []
        while rest:
            if rest[0] != "--doc":
                sys.exit("모르는 인자: " + rest[0])
            docs.append(rest[1])
            rest = rest[2:]
        more(a[1], a[2], docs)
    elif a[:1] == ["--brief"]:
        make_brief(a[1], a[2:] or None)
    elif a[:1] == ["--page"]:
        page(a[1], a[2], a[3] if len(a) > 3 else "")
    else:
        print(__doc__)
