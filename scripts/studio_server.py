"""칼럼 작업실 서버 — app/dist 화면을 내주고, 화면의 버튼을 기존 명령(column_pipeline·topic_candidates·image_candidates·collect)에 잇는다.

사용: python3 scripts/studio_server.py [포트=8771]
- 비밀번호 없음(멘토 결정 2026-10-09). 파이프라인 로직은 여기서 다시 짜지 않고 명령을 백그라운드로 돌리기만 한다.
- 작업 기록: runs/studio/jobs.json · logs/<작업>.log · chat/<글>.jsonl(진행자 대화) · thumbs/(그림 축소본)
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import wiki as W  # 주제 위키(2026-10-10 채택) — 넣은 원문·남은 원문 계산을 같이 쓴다
import my_topic as MT  # 내 주제로 쓰기 — 대화 차례(turns)를 같이 읽는다
from wiki import TARGETS  # 대상 독자 이름 — 팀장급·사수급·신입사원·전 직원

DIST = ROOT / "app" / "dist"
SRC = ROOT / "sources"
STUDIO = ROOT / "runs" / "studio"
PY = [sys.executable, "-X", "utf8", "-I", "-u"]  # -u: 출력을 바로 작업 로그로(화면에서 진행이 보이게)
# -X utf8: Windows 기본 인코딩(cp949)으로는 한글 지시문·로그가 깨지거나 이모지에서 멈춘다 — 리눅스는 그대로
PIPE = PY + ["scripts/column_pipeline.py"]
for d in ("logs", "chat", "thumbs"):
    (STUDIO / d).mkdir(parents=True, exist_ok=True)

JOBS = {}
LOCK = threading.Lock()
JOBS_FILE = STUDIO / "jobs.json"
if JOBS_FILE.exists():
    for j in json.loads(JOBS_FILE.read_text(encoding="utf-8")):
        if j["status"] == "running":
            j["status"] = "lost"  # 서버가 다시 뜨기 전에 돌던 작업
        JOBS[j["id"]] = j


def save_jobs():
    with LOCK:
        rows = sorted(JOBS.values(), key=lambda j: j["started"])[-300:]
    JOBS_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def start(kind, target, cmd, after=None):
    with LOCK:
        for j in JOBS.values():
            if j["kind"] == kind and j["target"] == target and j["status"] == "running":
                return j
        jid = time.strftime("%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        log = STUDIO / "logs" / f"{jid}.log"
        j = {"id": jid, "kind": kind, "target": target, "status": "running", "started": time.time(),
             "log": log.relative_to(ROOT).as_posix()}
        JOBS[jid] = j

    def run():
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT)
        ok = r.returncode == 0
        if ok and after:
            try:
                after(j)
            except Exception as e:  # 후처리 실패도 작업 실패로 남긴다
                ok = False
                with open(log, "a", encoding="utf-8") as f:
                    f.write(f"\n[후처리 실패] {e}\n")
        j["status"] = "done" if ok else "failed"
        j["ended"] = time.time()
        save_jobs()

    threading.Thread(target=run, daemon=True).start()
    save_jobs()
    return j


# ---------- 읽기 ----------

def read(p):
    return Path(p).read_text(encoding="utf-8") if Path(p).exists() else ""


def front(t):
    m, body = {}, t
    if t.startswith("---"):
        _, head, body = t.split("---", 2)
        for line in head.splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                m[k.strip()] = v.strip().strip("'\"")
    return m, body.strip()


def clean(t):
    t = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", t.strip()).strip()
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S).strip()
    return re.sub(r"\s*\(끝\)\s*$", "", t)


def split_title(t):
    lines = t.splitlines()
    for i, l in enumerate(lines):
        if l.strip():
            if l.lstrip().startswith("#") or l.startswith("제목"):
                return re.sub(r"^[#*\s]+|[*\s]+$|^제목\s*[:：]\s*", "", l).strip(), "\n".join(lines[i + 1:]).strip()
            return "", t.strip()
    return "", t


def nospace(t):
    return len(re.sub(r"\s", "", t))


SITES = {"threads": "Threads", "linkedin": "LinkedIn", "infuture": "경영일기"}


def library(full=False):
    rows = []
    for f in sorted((SRC / "originals").glob("*/*.md")):
        if f.name.startswith("_"):
            continue
        m, body = front(read(f))
        body = body.split("*주변 동료에게")[0].strip()
        text = re.sub(r"^## \d+/\d+\s*$", "", body, flags=re.M).strip()
        rel = f.relative_to(SRC).as_posix()
        rows.append({
            "path": rel, "site": f.parent.name, "siteName": m.get("site_name") or SITES.get(f.parent.name, f.parent.name), "tier": m.get("tier", ""),
            "url": m.get("url", ""), "author": m.get("author", ""), "headline": m.get("headline", ""),
            "title": m.get("title", ""), "date": m.get("date", ""),
            "reactions": m.get("likes") or m.get("reactions") or "", "chars": nospace(text),
            "excerpt": re.sub(r"\s+", " ", re.sub(r"^## .*$", "", text, flags=re.M)).strip()[:220], **({"text": body} if full else {}),
        })
    return rows


def title_rounds(k):
    d = ROOT / "runs" / "titles0" / k
    files = sorted(d.glob("astra-*.md"), key=lambda p: int(p.stem.split("-")[1])) + [d / "astra.md"]
    out = []
    for f in files:
        if f.exists():
            lines = [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in read(f).splitlines() if l.strip()]
            if lines:  # 회차와 같은 번호의 메시지(astra-2.md ↔ message-2.txt, astra.md ↔ message.txt)
                msg = read(d / f.name.replace("astra", "message").replace(".md", ".txt")).strip()
                out.append({"at": f.stat().st_mtime, "items": lines, "message": msg})
    return out


def image_rounds(k, inline=False):
    out = []
    for d in sorted((ROOT / "runs" / "images" / k).glob("*/")):
        if d.name.startswith("inline-") != inline:
            continue
        items = json.loads(read(d / "astra.json") or "[]")
        imgs = []
        for i, it in enumerate(items, 1):
            png = d / f"{i:02d}.png"
            imgs.append({"name": it.get("name", ""), "prompt": it.get("prompt", ""),
                         "src": png.relative_to(ROOT).as_posix() if png.exists() else "",
                         "after": it.get("after", 0), "anchor": it.get("anchor", "")})
        out.append({"id": d.name, "items": imgs})
    return out


def step(n, f, by, feedback="", known="", mode=""):
    raw = clean(read(f))
    title, body = split_title(raw)
    first = body.split("\n", 1)
    if known and not title and first[0].strip().strip("*\"'「」") == known:  # 머리표 없이 제목만 첫 줄에 쓴 원고
        title, body = known, (first[1] if len(first) > 1 else "").strip()
    return {"n": n, "file": Path(f).relative_to(ROOT).as_posix(), "by": by, "title": title, "text": body, "mode": mode,
            "chars": nospace(body), "feedback": feedback.strip(), "at": Path(f).stat().st_mtime}


def steps_in(d, b):
    """한 시도의 과정 1·2·3(+ 과정 4~) — 설정 글의 runs/columns/<글>/ 또는 앞 시도 폴더."""
    standing = read(ROOT / "briefs" / "standing-feedback.md").replace("[멘토 피드백 — 원문 그대로]\n", "").strip()
    steps = []
    draft = d / "draft.md"
    if not draft.exists() and b.get("draft_from"):  # 초안을 다른 갈래와 나눠 쓴 설정
        draft = ROOT / "runs" / "columns" / b["draft_from"] / "draft.md"
    for f, by, fb in ((draft, "Claude", ""), (d / "r4.md", "astra", ""), (d / "final.md", "astra", standing)):
        if f.exists() and f.stat().st_size > 50:
            steps.append(step(len(steps) + 1, f, by, fb, b.get("title", "")))
    for f in sorted(d.glob("final-r*.md"), key=lambda p: int(p.stem.split("-r")[1])):
        n = f.stem.split("-r")[1]
        if f.stat().st_size > 50:
            steps.append(step(len(steps) + 1, f, read(d / f"by-r{n}.txt").strip() or "astra", read(d / f"feedback-r{n}.txt"),
                              b.get("title", ""), read(d / f"mode-r{n}.txt").strip()))
    return steps


def article_from_brief(bp):
    k = bp.stem
    b = json.loads(read(bp))
    d = ROOT / "runs" / "columns" / k
    steps = steps_in(d, b)
    # 처음부터 다시 쓰기로 넘긴 앞 시도들(runs/columns/<글>.try-N) — 대화에 접힌 채로 남긴다
    tries = [{"n": int(x.name.rsplit("-", 1)[1]), "title": read(x / "title.txt").strip(), "steps": steps_in(x, b)}
             for x in sorted(d.parent.glob(f"{k}.try-*"), key=lambda x: int(x.name.rsplit("-", 1)[1]))]
    return {"id": k, "kind": "brief", "label": b.get("label", k), "thesis": b.get("thesis", ""),
            "sources": b.get("sources", []), "title": b.get("title", ""), "titles": title_rounds(k),
            "steps": steps, "images": image_rounds(k), "inline": image_rounds(k, True), "inlinePicked": b.get("inline", []),
            "length": b.get("length", "full"), "target": b.get("target", "전 직원"), "hero": b.get("hero", ""), "confirmed": b.get("confirmed"),
            "fromTopics": b.get("from_topics", ""), "fromWiki": b.get("from_wiki", ""), "fromMine": bool(b.get("from_mine")),
            "sourcesOk": bool(b.get("sources_ok")), "why": b.get("why", ""), "tries": tries, "at": bp.stat().st_mtime}


def article_from_process(pp):
    k = pp.name.replace(".process.json", "")
    p = json.loads(read(pp))
    steps = [step(i, ROOT / s["file"], s["by"], s.get("feedback", ""), p["title"], s.get("mode", "")) for i, s in enumerate(p["steps"], 1)]
    return {"id": k, "kind": "process", "label": p["title"], "thesis": p.get("thesis", ""), "sources": p.get("sources", []),
            "title": p["title"], "titles": [], "steps": steps, "images": image_rounds(k), "inline": image_rounds(k, True),
            "inlinePicked": p.get("inline", []), "length": p.get("length", "full"), "target": p.get("target", "전 직원"), "hero": p.get("hero", ""),
            "confirmed": p.get("confirmed"), "fromTopics": "", "at": pp.stat().st_mtime}


def articles():
    out = [article_from_process(p) for p in sorted((ROOT / "columns").glob("*.process.json"))]
    for bp in sorted((ROOT / "briefs").glob("*.json")):
        try:
            if json.loads(read(bp)).get("experiment"):  # 실험판(t1-A…sim-C)은 글 목록에 섞지 않는다 (멘토 2026-10-09)
                continue
            out.append(article_from_brief(bp))
        except Exception as e:
            out.append({"id": bp.stem, "kind": "brief", "label": bp.stem, "error": str(e), "steps": [], "titles": [],
                        "images": [], "sources": [], "thesis": "", "title": "", "hero": "", "confirmed": None, "at": 0})
    return out


def topic_rounds():
    out = []
    picked = {}
    for bp in (ROOT / "briefs").glob("*.json"):
        b = json.loads(read(bp))
        if b.get("from_topics"):
            picked[b["topic"]] = bp.stem
    for d in sorted((ROOT / "runs" / "topics").glob("*/"), reverse=True):
        items = json.loads(read(d / "astra.json") or "[]")
        if not items:  # 실패한 회차는 보이지 않게
            continue
        for i, it in enumerate(items, 1):
            it["n"] = i
            it["brief"] = picked.get(f"{d.name}-{i}", "")
        out.append({"id": d.name, "items": items})
    return out


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def wiki_state(fresh):
    """주제 지도를 화면용으로 읽는다 (2026-10-11 개편) — 주제마다 판정·대상 독자·왜 쓸모·제목 후보·원문 카드."""
    if not W.TOPICS.exists():
        return None
    cs = W.cards()
    topics = []
    for tp in W.topics():
        srcs = [tp["center"]] + [s for s in tp["sources"] if s != tp["center"]]
        rows = []
        for s in srcs:
            a, d, _ = W.src_meta(s)
            c = cs.get(s, {})
            rows.append({"path": W.rel(s), "who": " · ".join(x for x in (a, d) if x), "note": c.get("있었던 일", ""),
                         "claim": c.get("글쓴이가 하는 말", ""), "new": W.rel(s) in fresh})
        topics.append({
            "page": tp["page"], "field": "주제", "title": tp["title"], "thesis": tp["thesis"], "why": tp["why"],
            "verdict": tp["verdict"], "audience": tp["audience"], "status": tp["status"].split("#")[0].strip(),
            "usedIn": tp["used_in"], "titles": tp["titles"], "sources": rows, "angles": [], "related": [], "at": tp["timestamp"],
        })
    log = read(W.WIKI / "log.md")
    return {"topics": topics, "processed": len(W.processed()), "backlog": W.backlog(),
            "log": [l for l in log.splitlines() if l.startswith(("## ", "- "))][:40]}


def chat_log(k):
    f = STUDIO / "chat" / f"{safe_id(k)}.jsonl"
    return [json.loads(l) for l in read(f).splitlines() if l.strip()]


def job_stage(j):
    """돌고 있는 쓰기 작업이 지금 몇 번째 과정인지 — 단계 폴더의 prompt.md가 작업 시작 뒤에 생겼는지로 본다."""
    if j["kind"] != "write" or j["status"] != "running":
        return None
    d = ROOT / "runs" / "columns" / j["target"]
    fresh = lambda pat: any(f.stat().st_mtime >= j["started"] - 2 for f in d.glob(pat))
    half = json.loads(read(ROOT / "briefs" / f"{j['target']}.json") or "{}").get("length") == "half"
    fit = fresh("_fit-r*/prompt.md")  # 과정 3 뒤 1,500자를 넘어 줄이는 중 (2026-10-11)
    i = 3 if (half and fresh("_shorten-r*/prompt.md")) or fit else 2 if fresh("_final/prompt.md") else 1 if fresh("_r4/prompt.md") else 0
    return {"index": i, "half": half, "fit": fit}


def with_stage(jobs):
    return [{**j, "stage": job_stage(j)} if j["kind"] == "write" and j["status"] == "running" else j for j in jobs]


def state():
    with LOCK:
        jobs = sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)[:60]
    jobs = with_stage(jobs)
    collects = collect_rounds()
    fresh = {x["path"] for x in collects[0]["saved"] if x.get("path")} if collects else set()
    return {"library": library(), "topics": topic_rounds(), "articles": articles(), "jobs": jobs,
            "collects": collects, "wiki": wiki_state(fresh), "mine": mine_state(jobs)}


MINE = ROOT / "runs" / "mine"
MINE_EXT = {".pdf", ".docx", ".doc", ".hwp", ".hwpx", ".odt", ".rtf", ".txt", ".md"}


def mine_state(jobs):
    """내 주제로 쓰기(scripts/my_topic.py) — 메인 화면 채팅이 읽는다. 요청 · 올린 문서 · 진행 단계 · 고른 원문 · 나머지 후보."""
    if not MINE.exists():
        return []
    cs = W.cards()
    last = {}
    for j in sorted(jobs, key=lambda j: j["started"]):
        if j["kind"] == "mine":
            last[j["target"]] = j
    out = []
    for d in sorted(MINE.glob("m-*/")):
        k = d.name
        picks = json.loads(read(d / "picks.json") or "{}")
        meta = json.loads(read(d / "meta.json") or "{}")
        j = last.get(k)
        has_brief = (ROOT / "briefs" / f"{k}.json").exists()
        st = read(d / "stage.txt").strip() or ("끝" if has_brief else "문서")
        docs = [x[1].removeprefix("회사 자료 — ") for x in meta.get("docs", [])] or \
               [re.sub(r"^\d{2}-", "", f.name) for f in sorted((d / "upload").glob("*")) if f.is_file()]
        b = json.loads(read(ROOT / "briefs" / f"{k}.json") or "{}")
        now = [W.key(s[0]) for s in b.get("sources", []) if s[0].startswith("originals/")]  # 바꿔 끼운 뒤의 지금 원문(첫째가 중심)
        info = {c["source"]: {"role": c.get("why", ""), "use": "", "side": c.get("side", "")} for c in picks.get("_candidates", [])}
        for p_ in [picks.get("center") or {}] + picks.get("support", []):
            if p_.get("source"):
                info[p_["source"]] = {**info.get(p_["source"], {}), "role": p_.get("role", ""), "use": p_.get("use", "")}
        why_out = {x["source"]: x.get("why", "") for x in picks.get("rest", [])}

        def row(s, kind):
            a_, dt, u = W.src_meta(s) if (SRC / W.rel(s)).is_file() else ("", "", "")
            return {"source": s, "path": W.rel(s), "who": a_, "url": u, "kind": kind, "note": cs.get(s, {}).get("있었던 일", ""),
                    "role": info.get(s, {}).get("role", ""), "use": info.get(s, {}).get("use", ""), "side": info.get(s, {}).get("side", ""),
                    "out": why_out.get(s, "")}
        picked = [row(s, "중심" if i == 0 else "받침") for i, s in enumerate(now)]
        rest = [row(c["source"], "후보") for c in picks.get("_candidates", []) if c["source"] not in now]
        status = j["status"] if j else ("done" if has_brief else "lost")
        try:
            ts = MT.turns(d) if (d / "topic.txt").exists() else []
        except (OSError, ValueError, KeyError):
            ts = []
        if not ts:  # 첫 요청을 받자마자(아직 topic.txt 전)
            ts = [{"role": "mentor", "text": read(d / "request.txt").strip(), "docs": docs, "at": d.stat().st_mtime}]
        for x in ts:  # 지난 차례의 원문에 누가 쓴 글인지 붙인다
            for p_ in ([x["center"]] + x.get("support", [])) if x.get("role") == "ai" else []:
                p_["who"] = W.src_meta(p_["source"])[0] if (SRC / W.rel(p_["source"])).is_file() else ""
                p_["path"] = W.rel(p_["source"])
        out.append({"id": k, "turns": ts, "message": read(d / "topic.txt").strip() or read(d / "request.txt").strip(), "docs": docs,
                    "target": meta.get("target", ""), "status": status, "stage": st, "job": j["id"] if j else "",
                    "picked": picked, "rest": rest, "article": k if has_brief else "", "at": d.stat().st_mtime})
    return out


def act_mine(a):
    """메인 화면 채팅 — 멘토가 적은 요청(받은 그대로)과 올린 문서로 my_topic.py --new를 돌린다 (멘토 2026-10-11: "메인페이지에 채팅 ui를 띄워줘")."""
    msg = str(a.get("message") or "").strip()
    if not msg:
        raise ValueError("요청이 비었음")
    target = str(a.get("target") or "")
    if target and target not in TARGETS:
        raise ValueError("잘못된 대상 독자")
    k = safe_id("m-" + time.strftime("%Y%m%d-%H%M%S"))
    d = MINE / k
    if d.exists():
        raise ValueError("방금 보낸 요청이 있음 — 잠시 뒤 다시")
    tmp = MINE / f".{k}"
    docs = save_uploads(tmp, a.get("files") or [], "")
    tmp.rename(d) if tmp.exists() else d.mkdir(parents=True)
    docs = [x.replace(f"/.{k}/", f"/{k}/") for x in docs]
    (d / "request.txt").write_text(msg + "\n", encoding="utf-8")
    cmd = PY + ["scripts/my_topic.py", "--new", (d / "request.txt").relative_to(ROOT).as_posix(), "--id", k]
    if target:
        cmd += ["--target", target]
    cmd += docs
    return start("mine", k, cmd)


def busy(k, kinds=("mine", "write", "revise", "shorten", "titles", "images", "inline", "chat")):
    with LOCK:
        return next((j for j in JOBS.values() if j["target"] == k and j["status"] == "running" and j["kind"] in kinds), None)


def save_uploads(d, files, tag):
    """올린 문서를 확인하고 runs/mine/<글>/upload/에 둔다 — 하나라도 안 되면 아무것도 쓰지 않는다."""
    got, total = [], 0
    if not isinstance(files, list):
        raise ValueError("잘못된 파일")
    for f in files:
        name = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", Path(str(f.get("name", ""))).name).strip() or "문서"
        if Path(name).suffix.lower() not in MINE_EXT:
            raise ValueError(f"{name}: pdf·docx·hwp·txt·md만 받습니다")
        try:
            data = base64.b64decode(str(f.get("data", "")), validate=True)
        except ValueError:
            raise ValueError(f"{name}: 파일을 읽지 못함")
        total += len(data)
        if total > 50 * 1024 * 1024:
            raise ValueError("파일이 너무 큼(합쳐 50MB까지)")
        got.append((name, data))
    out = []
    for i, (name, data) in enumerate(got, 1):
        f = d / "upload" / f"{tag}{i:02d}-{name}"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        out += ["--doc", f.relative_to(ROOT).as_posix()]
    return out


def act_mine_more(a):
    """같은 대화에서 이어서 한 말 — 대화 전체로 원문을 다시 고른다(받은 그대로 넘김). 쓰기를 시작한 글은 안 된다."""
    k = safe_id(a.get("id", ""))
    msg = str(a.get("message") or "").strip()
    d = MINE / k
    if not msg or not (d / "meta.json").exists():
        raise ValueError("이어서 할 말이 비었거나 없는 대화")
    if busy(k):
        raise ValueError("이 글에서 작업이 도는 중")
    if (ROOT / "runs" / "columns" / k / "draft.md").exists():
        raise ValueError("쓰기를 시작한 글은 원문을 다시 고르지 않습니다 — 새 대화로 시작하세요")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    f = d / f"more-{stamp}.txt"
    f.write_text(msg + "\n", encoding="utf-8")
    docs = save_uploads(d, a.get("files") or [], stamp + "-")
    return start("mine", k, PY + ["scripts/my_topic.py", "--more", k, f.relative_to(ROOT).as_posix(), *docs])


def act_mine_ok(a):
    """'이 원문으로' — 원문 단계를 마치고 제목 단계로. 이 뒤로 채팅에 보낸 말은 제목 회차로 간다."""
    k = safe_id(a.get("article", ""))
    if busy(k, ("mine",)):
        raise ValueError("원문을 고르는 중")
    meta_update(k, sources_ok=True)
    return {"article": k}


TRASH = ROOT / "trash"


def act_delete(a):
    """글 삭제 — 지우지 않고 trash/<글>-<시각>/으로 옮긴다(되살릴 수 있게). 확정 기준 글(과정 기록)은 안 된다.
    주제 지도에서 고른 글이면 그 주제의 used_in에서 빼고, 비면 '쓸 수 있음'으로 되돌린다."""
    k = safe_id(a.get("article", ""))
    if process_path(k):
        raise ValueError("확정 기준 글은 지우지 않습니다")
    bp = brief_path(k)
    if busy(k):
        raise ValueError("이 글에서 작업이 도는 중")
    b = json.loads(read(bp) or "{}")
    dst = TRASH / f"{k}-{time.strftime('%Y%m%d-%H%M%S')}"
    moves = [bp, ROOT / "runs" / "columns" / k, *(ROOT / "runs" / "columns").glob(f"{k}.try-*"), ROOT / "runs" / "titles0" / k, ROOT / "runs" / "images" / k,
             MINE / k, SRC / "mine" / k, STUDIO / "chat" / f"{k}.jsonl", *(ROOT / "columns").glob(f"*-{k}.md"),
             *(ROOT / "columns" / "img").glob(f"*-{k}.png"), *(ROOT / "columns" / "img").glob(f"*-{k}-*.png")]
    for src in moves:
        if src.exists():
            to = dst / src.relative_to(ROOT)
            to.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(to))
    page = b.get("from_wiki", "")
    if page and (ROOT / page).is_file():
        f = ROOT / page
        ui = [u for u in W.used_in(f) if k not in u]
        W.set_front(f, used_in="[" + ", ".join(ui) + "]", **({"status": "쓸 수 있음"} if not ui else {}))
        W.write_index(W.topics())
        W.commit(f"주제 지도: 글 삭제 {k} → used_in에서 뺌")
    return {"trash": dst.relative_to(ROOT).as_posix()}


def act_mine_swap(a):
    """고른 원문 바꿔 끼우기 — 첫째가 중심. 설정만 다시 쓴다(LLM 없음, 제목·대상 독자·분량은 그대로)."""
    k = safe_id(a.get("id", ""))
    srcs = a.get("sources") or []
    cs = W.cards()
    if not (MINE / k / "picks.json").exists() or not isinstance(srcs, list) or not srcs or any(s not in cs for s in srcs):
        raise ValueError("잘못된 원문")
    if busy(k, ("mine", "write")):
        raise ValueError("이 글에서 작업이 도는 중")
    r = subprocess.run(PY + ["scripts/my_topic.py", "--brief", k, *dict.fromkeys(srcs)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise ValueError((r.stderr or r.stdout)[-500:])
    return {"id": k}


def collect_rounds():
    out = []
    for d in sorted((ROOT / "runs" / "collect").glob("*/"), reverse=True):
        out.append({"id": d.name, "request": read(d / "request.txt"), "saved": json.loads(read(d / "saved.json") or "[]")})
    return out


# ---------- 쓰기 ----------
# 입력값은 모두 검사한다: 글 이름·회차·그림 경로가 폴더 밖을 가리키지 못하게 (2026-10-09 보안 점검)

ID = re.compile(r"^[0-9A-Za-z가-힣][0-9A-Za-z가-힣_.-]{0,80}$")


def safe_id(k):
    if not isinstance(k, str) or not ID.match(k) or ".." in k:
        raise ValueError("잘못된 글 이름")
    return k


def inside(p, base):
    p, base = Path(p).resolve(), Path(base).resolve()
    return p == base or base in p.parents


def brief_path(k):
    p = ROOT / "briefs" / f"{safe_id(k)}.json"
    if not p.exists():
        raise ValueError("설정 없음: " + k)
    return p


def process_path(k):
    p = ROOT / "columns" / f"{safe_id(k)}.process.json"
    return p if p.exists() else None


def image_src(src):
    """머리 그림은 runs/images/ 아래에서 만든 PNG만 받는다."""
    if not isinstance(src, str) or not re.match(r"^runs/images/[^/]+/(?:inline-)?\d{8}-\d{6}/\d{2}\.png$", src):
        raise ValueError("잘못된 그림 경로")
    if not inside(ROOT / src, ROOT / "runs" / "images") or not (ROOT / src).is_file():
        raise ValueError("그림 없음")
    return src


def meta_update(k, **kv):
    p = process_path(k) or brief_path(k)
    d = json.loads(read(p))
    d.update(kv)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def tail(f, n=4000):
    try:
        b = Path(f).read_bytes()[-n:]
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", b.decode("utf-8", "ignore"))
    except OSError:
        return ""


def live_of(j):
    """작업마다 지금 쓰이고 있는 파일 — 초안 글자(live.md)·astra 출력(run.log·astra.log)·그림 로그."""
    k, kind = j.get("target", ""), j["kind"]
    cands = []
    if kind in ("write", "revise", "shorten"):
        cands = [*(ROOT / "runs" / "columns" / k).glob("_*/live.md"), *(ROOT / "runs" / "columns" / k).glob("_*/thinking.md"),
                 *(ROOT / "runs" / "columns" / k).glob("_*/run.log")]
    elif kind == "titles":
        cands = [ROOT / "runs" / "titles0" / k / "astra.log"]
    elif kind in ("images", "inline"):
        rounds = sorted((ROOT / "runs" / "images" / k).glob("*/"), key=lambda d: d.stat().st_mtime)
        if rounds:
            cands = [rounds[-1] / "run.log", *rounds[-1].glob("[0-9][0-9].log")]
    cands = [c for c in cands if c.is_file() and c.stat().st_mtime >= j["started"] - 5]
    cands.sort(key=lambda c: c.stat().st_mtime, reverse=True)
    return [{"name": c.relative_to(ROOT).as_posix(), "text": tail(c)} for c in cands[:3]]


def act_topics(_):
    return start("topics", "", PY + ["scripts/topic_candidates.py"])


def act_pick_topic(a):
    rnd, n = str(a["round"]), str(int(a["n"]))
    if not re.match(r"^\d{8}-\d{6}$", rnd) or not (ROOT / "runs" / "topics" / rnd / "astra.json").exists():
        raise ValueError("잘못된 주제 회차")
    r = subprocess.run(PY + ["scripts/topic_candidates.py", "--pick", rnd, n], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise ValueError(r.stderr[-500:])
    k = f"{rnd}-{n}"
    act_titles({"article": k})
    return {"article": k}


def act_titles(a):
    """제목 후보 — 멘토가 메시지를 같이 보내면 받은 그대로 파일로 넘긴다(멘토 2026-10-10: "원할 시 메시지를 같이")."""
    k = a["article"]
    bp = brief_path(k)
    msg = str(a.get("message") or "").strip()
    with LOCK:  # 돌고 있는 회차의 파일을 밀어내지 않게
        if any(j["kind"] == "titles" and j["target"] == k and j["status"] == "running" for j in JOBS.values()):
            raise ValueError("제목 후보를 짓는 중")
    d = ROOT / "runs" / "titles0" / k
    if (d / "astra.md").exists():  # 다시 뽑으면 앞 회차를 남긴다
        n = len(list(d.glob("astra-*.md"))) + 1
        (d / "astra.md").rename(d / f"astra-{n}.md")
        if (d / "message.txt").exists():
            (d / "message.txt").rename(d / f"message-{n}.txt")
    cmd = PIPE + ["--titles", bp.relative_to(ROOT).as_posix()]
    if msg:
        inbox = d / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        f = inbox / (time.strftime("%Y%m%d-%H%M%S") + ".txt")
        f.write_text(msg, encoding="utf-8")
        cmd += ["--message", f.relative_to(ROOT).as_posix()]
    j = start("titles", k, cmd)
    if msg:
        j["message"] = msg  # 도는 동안에도 화면이 보낸 말을 보여 주게
    return j


def act_titles_ui(a):
    """화면에서 누른 제목 후보 — 깊게 읽기가 도는 동안은 거절한다. 읽기가 끝나면 제목 후보가 저절로 이어지므로,
    그 사이에 보낸 메시지 회차가 밀려나거나 이어지는 회차가 막히지 않게 (내부 호출은 act_titles를 바로 부른다)."""
    k = safe_id(a["article"])
    with LOCK:
        if any(j["kind"] == "wiki-pick" and j["target"] == k and j["status"] == "running" for j in JOBS.values()):
            raise ValueError("주제를 고르는 중 — 끝나면 제목 후보가 이어서 나옵니다")
    return act_titles(a)


def act_title(a):
    k, t = a["article"], a["title"].strip()
    b = json.loads(read(brief_path(k)))
    b["title"] = t
    brief_path(k).write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"title": t}


def act_write(a):
    k = a["article"]
    return start("write", k, PIPE + [brief_path(k).relative_to(ROOT).as_posix()])


def act_revise(a):
    k, fb = a["article"], str(a["feedback"])
    brief_path(k)
    inbox = ROOT / "runs" / "columns" / k / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    f = inbox / (time.strftime("%Y%m%d-%H%M%S") + ".txt")
    f.write_text(fb, encoding="utf-8")  # 멘토 피드백은 받은 그대로 파일로만 넘긴다
    j = start("revise", k, PIPE + ["--revise", brief_path(k).relative_to(ROOT).as_posix(), f.relative_to(ROOT).as_posix()])
    j["message"] = fb  # 도는 동안 대화에 보낸 말이 보이게
    return j


def act_images(a):
    k = safe_id(a["article"])
    pp = process_path(k)
    target = json.loads(read(pp))["steps"][-1]["file"] if pp else k
    if pp:  # 확정 칼럼은 원고 파일 이름이 그림 폴더 이름이 된다
        target = Path(target).as_posix()
    if a.get("kind") == "inline":
        return start("inline", k, PY + ["scripts/image_candidates.py", "--inline", target])
    return start("images", k, PY + ["scripts/image_candidates.py", target])


def act_inline(a):
    """본문 그림 고르기/빼기 — 고른 그림은 확정할 때 그 문단 뒤에 들어간다."""
    k, src, on = safe_id(a["article"]), image_src(a["src"]), bool(a.get("on", True))
    art = next(x for x in articles() if x["id"] == k)
    item = next((it for r in art["inline"] for it in r["items"] if it["src"] == src), None)
    if not item:
        raise ValueError("본문 그림 아님")
    picked = [x for x in art["inlinePicked"] if x["src"] != src]
    if on:
        picked.append({"src": src, "after": item["after"], "anchor": item["anchor"], "name": item["name"]})
    picked.sort(key=lambda x: x["after"])
    meta_update(k, inline=picked)
    return {"inline": picked}


def act_length(a):
    """분량 두 가지: full(기본) / half(절반). 절반으로 바꾸면 마지막 과정을 줄여 다음 과정을 만든다."""
    k, mode = safe_id(a["article"]), a.get("mode")
    if mode not in ("full", "half"):
        raise ValueError("잘못된 분량")
    meta_update(k, length=mode)
    art = next(x for x in articles() if x["id"] == k)
    if mode != "half" or not art["steps"] or art["steps"][-1].get("mode") == "절반":
        return {"length": mode}
    pp = process_path(k)
    if not pp:
        return start("shorten", k, PIPE + ["--shorten", brief_path(k).relative_to(ROOT).as_posix()])
    out_dir = ROOT / "runs" / "columns" / k / ("_shorten-" + time.strftime("%Y%m%d-%H%M%S"))

    def after(j):  # 확정 칼럼: 결과를 과정 기록에 다음 과정으로 붙인다 — 비었으면 붙이지 않고 실패로
        text = read(out_dir / "output.md").strip()
        if not text:
            raise ValueError("절반 결과가 비었음")
        f = ROOT / "columns" / f"{k}-절반.md"
        f.write_text(text + "\n", encoding="utf-8")
        d = json.loads(read(pp))
        d["steps"].append({"file": f.relative_to(ROOT).as_posix(), "by": "astra", "mode": "절반"})
        pp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return start("shorten", k, PIPE + ["--shorten-file", art["steps"][-1]["file"], out_dir.relative_to(ROOT).as_posix()], after)


def act_target(a):
    """대상 독자 고르기 (멘토 2026-10-10: "팀장급이거나 신입사원이거나 사수급이거나") — 설정만 바꾼다.
    다음 제목 후보·쓰기·다시 쓰기부터 이 독자로 쓴다(이미 쓴 과정은 그대로)."""
    k, t = safe_id(a["article"]), a.get("target")
    if t not in TARGETS:
        raise ValueError("잘못된 대상 독자")
    meta_update(k, target=t)
    return {"target": t}


EDIT_MAX = 40000  # 공백 포함 글자 — 칼럼 한 편의 열 배쯤


def blocks(t):
    return [x.strip() for x in re.split(r"\n\s*\n", t) if x.strip()]


def act_edit(a):
    """직접 편집 — 사람이 고친 원고를 덮어쓰지 않고 '멘토'가 쓴 다음 과정으로 쌓는다
    (멘토 2026-10-10: "과정, 확정에서 뷰어를 에디터로 만들어서 직접 사람이 편집할 수도 있게").
    설정 글은 final-rN.md로 남겨 다음 피드백 반영·절반 줄이기가 이 원고를 바탕으로 이어지게 한다."""
    k = safe_id(a["article"])
    text = str(a.get("text") or "").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("빈 원고")
    if len(text) > EDIT_MAX:
        raise ValueError("원고가 너무 김")
    with LOCK:  # 같은 글을 AI가 쓰는 중이면 과정 번호가 부딪친다
        if any(j["target"] == k and j["kind"] in ("write", "revise", "shorten") and j["status"] == "running" for j in JOBS.values()):
            raise ValueError("이 글을 쓰는 중 — 끝난 뒤에 고치세요")
    art = next((x for x in articles() if x["id"] == k), None)
    if not art or not art["steps"]:
        raise ValueError("고칠 과정이 없음")
    n = len(art["steps"])
    base = int(a.get("base") or n)
    if not 1 <= base <= n:
        raise ValueError("잘못된 과정 번호")
    src = art["steps"][base - 1]
    if blocks(text) == blocks(src["text"]):
        raise ValueError("바뀐 곳이 없음")
    mode = "직접 편집" if base == n else f"직접 편집 · 과정 {base}에서"
    title = art["title"] or src["title"]  # 제목은 고치는 대상이 아니다(제목 탭에서 astra 후보로)
    body = (f"# {title}\n\n" if title else "") + text + "\n"
    d = ROOT / "runs" / "columns" / k
    d.mkdir(parents=True, exist_ok=True)
    pp = process_path(k)
    if pp:  # 확정 칼럼 기록 — columns/(결과물 자리)에는 쓰지 않고 과정만 하나 늘린다
        f = d / f"edit-{time.strftime('%Y%m%d-%H%M%S')}.md"
        f.write_text(body, encoding="utf-8")
        p = json.loads(read(pp))
        p["steps"].append({"file": f.relative_to(ROOT).as_posix(), "by": "멘토", "mode": mode})
        pp.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        r = len(list(d.glob("final-r*.md"))) + 1  # column_pipeline.revise()와 같은 번호 규칙
        (d / f"final-r{r}.md").write_text(body, encoding="utf-8")
        (d / f"by-r{r}.txt").write_text("멘토", encoding="utf-8")
        (d / f"mode-r{r}.txt").write_text(mode, encoding="utf-8")
    return {"n": n + 1}


def act_base(a):
    """여기서 이어 쓰기 — 앞 과정 하나를 그대로 다음 과정으로 올린다. 이 뒤의 피드백·편집·절반은 이 원고에서 이어진다(내용은 안 바꾼다)."""
    k = safe_id(a["article"])
    if process_path(k):
        raise ValueError("확정 기준 글에서는 안 됨")
    if busy(k, ("write", "revise", "shorten")):
        raise ValueError("이 글을 쓰는 중 — 끝난 뒤에")
    art = next((x for x in articles() if x["id"] == k), None)
    n = len(art["steps"]) if art else 0
    base = int(a.get("step") or 0)
    if not 1 <= base < n:
        raise ValueError("잘못된 과정 번호")
    src = art["steps"][base - 1]
    title = art["title"] or src["title"]
    d = ROOT / "runs" / "columns" / k
    r = len(list(d.glob("final-r*.md"))) + 1
    (d / f"final-r{r}.md").write_text((f"# {title}\n\n" if title else "") + src["text"].strip() + "\n", encoding="utf-8")
    (d / f"by-r{r}.txt").write_text("멘토", encoding="utf-8")
    (d / f"mode-r{r}.txt").write_text(f"과정 {base}에서 이어 감", encoding="utf-8")
    return {"n": n + 1}


def act_restart(a):
    """처음부터 다시 쓰기 — 같은 대화 안에서. 지금까지의 과정은 runs/columns/<글>.try-N/로 옮겨 대화에 접어 두고,
    쓰기 전 단계(제목 고르기·쓰기)로 돌아간다. 제목·원문은 그대로 — 바꾸고 싶으면 그 단계에서 바꾼다."""
    k = safe_id(a["article"])
    if process_path(k):
        raise ValueError("확정 기준 글에서는 안 됨")
    b = json.loads(read(brief_path(k)) or "{}")
    if b.get("confirmed"):
        raise ValueError("확정한 글 — 다시 쓰려면 확정을 풀어야 함")
    if busy(k):
        raise ValueError("이 글에서 작업이 도는 중")
    d = ROOT / "runs" / "columns" / k
    if not d.exists():
        raise ValueError("다시 쓸 과정이 없음")
    n = len(list(d.parent.glob(f"{k}.try-*"))) + 1
    (d / "title.txt").write_text(b.get("title", ""), encoding="utf-8")
    d.rename(d.parent / f"{k}.try-{n}")
    return {"try": n}


def act_hero(a):
    src = image_src(a["src"])
    meta_update(a["article"], hero=src)
    return {"hero": src}


def act_confirm(a):
    k, n = safe_id(a["article"]), int(a["step"])
    art = next(x for x in articles() if x["id"] == k)
    if not 1 <= n <= len(art["steps"]):
        raise ValueError("잘못된 과정 번호")
    st = art["steps"][n - 1]
    out = ROOT / "columns" / f"{date.today().isoformat()}-{k}.md"
    title = art["title"] or st["title"]
    paras = [x for x in re.split(r"\n\s*\n", st["text"]) if x.strip()]
    imgs = {}
    for i, it in enumerate(art.get("inlinePicked", []), 1):
        at = next((j for j, x in enumerate(paras, 1) if it.get("anchor") and x.strip().startswith(it["anchor"][:20])), it["after"])
        dst = ROOT / "columns" / "img" / f"{out.stem}-{i}.png"
        dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / image_src(it["src"]), dst)
        imgs.setdefault(min(max(at, 1), len(paras)), []).append(f"![{it['name']}](img/{dst.name})")
    body = "\n\n".join(x + "".join("\n\n" + m for m in imgs.get(j, [])) for j, x in enumerate(paras, 1))
    out.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    conf = {"date": date.today().isoformat(), "step": n, "file": out.relative_to(ROOT).as_posix(), "inline": sum(map(len, imgs.values()))}
    if art.get("hero"):
        img = ROOT / "columns" / "img" / f"{out.stem}.png"
        img.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / image_src(art["hero"]), img)
        conf["hero"] = img.relative_to(ROOT).as_posix()
    meta_update(k, confirmed=conf)
    if not process_path(k):
        src_page = json.loads(read(brief_path(k))).get("from_wiki", "")
        if src_page:
            subprocess.run(PY + ["scripts/wiki.py", "--written", src_page, conf["file"]], cwd=ROOT, capture_output=True)
    return conf


def act_collect(a):
    req = str(a.get("request", "")).strip()

    def after(j):  # 새 원문은 바로 위키에 넣는다 (2026-10-10 위키 채택)
        if W.backlog():
            act_wiki_ingest({})
    return start("collect", req[:40] or "자동 · Threads·LinkedIn", PY + ["scripts/collect.py", req], after)


DB_EVERY = float(os.environ.get("DB_SYNC_HOURS", "6")) * 3600  # Supabase 받기 간격 — 서버가 켜질 때 한 번, 그다음 이 간격마다


def act_db_sync(_):
    """Supabase 받기 — main 파이프라인이 매일 쌓는 원문을 서재로(scripts/db_sources.py). 반려된 원문은 정리(--prune, 카드 있는 원문은 남김).
    주제 지도 넣기는 이어 붙이지 않는다 — astra를 쓰고 주제 판정은 사람이 보는 일이라 '넣기' 버튼으로."""
    return start("db-sync", "Supabase", PY + ["scripts/db_sources.py", "--sync", "--prune"])


def db_sync_loop():
    while True:
        if os.environ.get("DATABASE_URL"):
            act_db_sync({})
        time.sleep(max(DB_EVERY, 600))


def act_wiki_ingest(_):
    return start("wiki", "넣기", PY + ["scripts/wiki.py", "--ingest"])


def act_wiki_lint(_):
    """다시 거르기 — 판정 예시가 쌓였을 때 모든 주제를 다시 거른다(Claude)."""
    return start("wiki-lint", "다시 거르기", PY + ["scripts/wiki.py", "--refilter"])


def act_wiki_pick(a):
    """주제 카드를 고르면 그 자리에서 글 설정을 만든다 — 주제의 주장·원문·대상 독자, 미리 뽑아 둔 제목 후보가 제목 탭에 바로 뜬다.
    (2026-10-11 개편: 카드가 이미 원문을 읽었으므로 깊게 읽기는 없다. 제목 후보가 없는 주제만 제목 단계를 돌린다)"""
    page = str(a.get("page", ""))
    f = (ROOT / page).resolve()
    if not re.match(r"^wiki/주제/[^/]+\.md$", page) or not inside(f, W.TOPICS) or not f.is_file():
        raise ValueError("잘못된 주제 페이지")
    k = W.claim(page)
    if not (ROOT / "runs" / "titles0" / k / "astra.md").exists():
        act_titles({"article": k})
    return {"article": k}


def act_wiki_verdict(a):
    """멘토가 판정을 바꾼다 — 판정 예시에 쌓여 다음 거르기가 따른다. 쓸 만함으로 올리면 제목 후보를 뽑는다(astra)."""
    page, verdict = str(a.get("page", "")), str(a.get("verdict", ""))
    f = (ROOT / page).resolve()
    if not re.match(r"^wiki/주제/[^/]+\.md$", page) or not inside(f, W.TOPICS) or not f.is_file():
        raise ValueError("잘못된 주제 페이지")
    if verdict not in W.VERDICTS:
        raise ValueError("잘못된 판정")
    return start("wiki-verdict", page, PY + ["scripts/wiki.py", "--verdict", page, verdict])


DIRECTOR = ROOT / "scripts" / "director_system.md"


def director_prompt():
    """진행자 지시문 — Windows 셸(Git Bash)에는 python3가 없을 수 있어 작업실을 띄운 파이썬을 그대로 쓰게 한다."""
    t = read(DIRECTOR)
    if sys.platform == "win32":
        t = t.replace("python3 -I", f'"{Path(sys.executable).as_posix()}" -X utf8 -I').replace("aside-win", "aside")
    return t


def act_chat(a):
    k, msg = safe_id(a["article"]), str(a["message"]).strip()
    sess_f = STUDIO / "chat" / "sessions.json"
    sess = json.loads(read(sess_f) or "{}")
    first = k not in sess
    sid = sess.get(k) or str(uuid.uuid4())
    sess[k] = sid
    sess_f.write_text(json.dumps(sess, indent=1), encoding="utf-8")
    log = STUDIO / "chat" / f"{k}.jsonl"
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": "mentor", "text": msg, "at": time.time()}, ensure_ascii=False) + "\n")
    ctx = f"[지금 보고 있는 글: {k} — 설정 briefs/{k}.json, 결과 runs/columns/{k}/]\n" if not process_path(k) else \
        f"[지금 보고 있는 글: 확정 칼럼 columns/{k}.md — 과정 기록 columns/{k}.process.json]\n"
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--tools", "Bash,Read,Write,Glob,Grep",
           "--permission-mode", "bypassPermissions", "--append-system-prompt", director_prompt()]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    cmd += [ctx + msg]

    def after(j):
        raw = read(ROOT / j["log"])
        m = re.search(r"\{.*\}\s*$", raw, re.S)
        res = json.loads(m.group(0)) if m else {"result": raw[-2000:]}
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"role": "claude", "text": res.get("result", ""), "cost": res.get("total_cost_usd"),
                                "at": time.time()}, ensure_ascii=False) + "\n")
    return start("chat", k, cmd, after)


ACTIONS = {"topics": act_topics, "pick-topic": act_pick_topic, "titles": act_titles_ui, "title": act_title,
           "write": act_write, "revise": act_revise, "images": act_images, "hero": act_hero,
           "confirm": act_confirm, "collect": act_collect, "db-sync": act_db_sync, "chat": act_chat, "inline": act_inline, "length": act_length, "target": act_target, "edit": act_edit,
           "wiki-ingest": act_wiki_ingest, "wiki-lint": act_wiki_lint, "wiki-pick": act_wiki_pick,
           "wiki-verdict": act_wiki_verdict, "mine": act_mine, "mine-swap": act_mine_swap, "mine-more": act_mine_more,
           "mine-ok": act_mine_ok, "delete": act_delete, "base": act_base, "restart": act_restart}


# ---------- 그림 축소본 ----------

def thumb(rel, w):
    src = (ROOT / rel).resolve()
    if not any(inside(src, ROOT / d) for d in ALLOWED) or not src.is_file():
        return None
    out = STUDIO / "thumbs" / f"{re.sub(r'[^0-9A-Za-z가-힣._-]', '_', rel)}.{w}.jpg"
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((w, w * 2))
        im.save(out, "JPEG", quality=86)
    return out


ALLOWED = ("runs/images/", "columns/", "runs/studio/thumbs/")


HOSTS = set()  # 실행 때 채운다 — 이 서버가 받는 주소


def host_ok(h):
    return (h or "").rsplit(":", 1)[0].strip("[]") in HOSTS


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def guard(self):
        if not host_ok(self.headers.get("Host")):
            self.send_error(403)
            return False
        return True

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def send_file(self, p, ctype):
        b = Path(p).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self.guard():
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            return self.get(u, q)
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)

    def get(self, u, q):
        if u.path == "/api/state":
            return self.send_json(state())
        if u.path == "/api/jobs":
            with LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)[:60]
            return self.send_json(with_stage(jobs))
        if u.path == "/api/source":
            p = q.get("path", [""])[0]
            row = next((r for r in library(full=True) if r["path"] == p), None)
            if not row and p.startswith("excerpts/") and inside(SRC / p, SRC / "excerpts") and (SRC / p).is_file():
                row = {"path": p, "text": front(read(SRC / p))[1]}
            return self.send_json(row or {}, 200 if row else 404)
        if u.path == "/api/chat":
            return self.send_json(chat_log(q.get("article", [""])[0]))
        if u.path == "/api/log":
            j = JOBS.get(q.get("id", [""])[0])
            if not j:
                return self.send_json({"text": "", "live": []})
            return self.send_json({"text": tail(ROOT / j["log"], 6000), "live": live_of(j), "status": j["status"],
                                   "elapsed": round((j.get("ended") or time.time()) - j["started"])})
        if u.path.startswith(("/docs/", "/wiki-eval/report/")):
            rel = unquote(u.path.lstrip("/"))
            f = (ROOT / rel).resolve()
            if not any(inside(f, ROOT / d) for d in ("docs", "wiki-eval/report")) or not f.is_file():
                return self.send_error(404)
            ctype = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
                     ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg"}.get(f.suffix, "application/octet-stream")
            return self.send_file(f, ctype)
        if u.path.startswith("/img/"):
            rel = unquote(u.path[5:])
            if not rel.startswith(ALLOWED) or ".." in rel or not rel.lower().endswith((".png", ".jpg")):
                return self.send_error(404)
            if not any(inside(ROOT / rel, ROOT / d) for d in ALLOWED):
                return self.send_error(404)
            w = min(int(q.get("w", ["0"])[0] or 0), 2400)
            p = thumb(rel, w) if w else ROOT / rel
            if not p or not Path(p).exists():
                return self.send_error(404)
            return self.send_file(p, "image/jpeg" if w else "image/png")
        if not (DIST / u.path.lstrip("/")).exists():
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if not self.guard():
            return
        origin = self.headers.get("Origin")
        if origin and not host_ok(urlparse(origin).netloc):
            return self.send_error(403)
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.send_error(415)  # JSON만 — 다른 사이트의 form/text 요청은 브라우저가 사전 확인 없이 못 보낸다
        u = urlparse(self.path)
        name = u.path.removeprefix("/api/")
        if name not in ACTIONS:
            return self.send_error(404)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            a = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(a, dict):
                raise ValueError("잘못된 요청")
            return self.send_json(ACTIONS[name](a))
        except Exception as e:
            return self.send_json({"error": str(e)}, 400)


def tailnet_ips():
    """Tailscale 주소(100.64.0.0/10)만 찾는다 — 같은 공유기(LAN)에는 열지 않는다.
    Windows에는 ip 명령이 없어 tailscale CLI로 묻는다. 둘 다 없으면 localhost에만 붙는다."""
    cmd = ["tailscale", "ip", "-4"] if sys.platform == "win32" else ["ip", "-4", "-o", "addr"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    except OSError:
        return []
    ips = re.findall(r"(?<![\d.])(100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)(?![\d.])", out)
    return list(dict.fromkeys(ips))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8771
    binds = ["127.0.0.1"] + tailnet_ips()
    HOSTS.update(binds + ["localhost"])
    try:
        servers = [ThreadingHTTPServer((h, port), H) for h in binds]
    except OSError as e:  # 이미 작업실이 떠 있거나 다른 프로그램이 그 포트를 쓴다
        sys.exit(f"포트 {port}을 열 수 없습니다({e}). 이미 작업실이 떠 있지 않은지 확인하거나 다른 포트로 띄우세요"
                 f" (예: start-windows.cmd {port + 10} / python3 -I scripts/studio_server.py {port + 10}).")
    for srv in servers[1:]:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("칼럼 작업실 " + " · ".join(f"http://{h}:{port}" for h in binds), flush=True)
    threading.Thread(target=db_sync_loop, daemon=True).start()
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL이 없어 Supabase 자동 받기를 건너뜁니다(서재의 'Supabase 받기'도 실패합니다).", flush=True)
    servers[0].serve_forever()
