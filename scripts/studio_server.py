"""칼럼 작업실 서버 — app/dist 화면을 내주고, 화면의 버튼을 기존 명령(column_pipeline·topic_candidates·image_candidates·collect)에 잇는다.

사용: python3 scripts/studio_server.py [포트=8771]
- 비밀번호 없음(멘토 결정 2026-10-09). 파이프라인 로직은 여기서 다시 짜지 않고 명령을 백그라운드로 돌리기만 한다.
- 작업 기록: runs/studio/jobs.json · logs/<작업>.log · chat/<글>.jsonl(진행자 대화) · thumbs/(그림 축소본)
"""
import json
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
DIST = ROOT / "app" / "dist"
SRC = ROOT / "sources"
STUDIO = ROOT / "runs" / "studio"
PY = [sys.executable, "-I"]
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
             "log": str(log.relative_to(ROOT))}
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
        rel = str(f.relative_to(SRC))
        rows.append({
            "path": rel, "site": f.parent.name, "siteName": SITES.get(f.parent.name, f.parent.name),
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
            if lines:
                out.append({"at": f.stat().st_mtime, "items": lines})
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
                         "src": str(png.relative_to(ROOT)) if png.exists() else "",
                         "after": it.get("after", 0), "anchor": it.get("anchor", "")})
        out.append({"id": d.name, "items": imgs})
    return out


def step(n, f, by, feedback="", known="", mode=""):
    raw = clean(read(f))
    title, body = split_title(raw)
    first = body.split("\n", 1)
    if known and not title and first[0].strip().strip("*\"'「」") == known:  # 머리표 없이 제목만 첫 줄에 쓴 원고
        title, body = known, (first[1] if len(first) > 1 else "").strip()
    return {"n": n, "file": str(Path(f).relative_to(ROOT)), "by": by, "title": title, "text": body, "mode": mode,
            "chars": nospace(body), "feedback": feedback.strip(), "at": Path(f).stat().st_mtime}


def article_from_brief(bp):
    k = bp.stem
    b = json.loads(read(bp))
    d = ROOT / "runs" / "columns" / k
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
            steps.append(step(len(steps) + 1, f, "astra", read(d / f"feedback-r{n}.txt"), b.get("title", ""),
                              read(d / f"mode-r{n}.txt").strip()))
    return {"id": k, "kind": "brief", "label": b.get("label", k), "thesis": b.get("thesis", ""),
            "sources": b.get("sources", []), "title": b.get("title", ""), "titles": title_rounds(k),
            "steps": steps, "images": image_rounds(k), "inline": image_rounds(k, True), "inlinePicked": b.get("inline", []),
            "length": b.get("length", "full"), "hero": b.get("hero", ""), "confirmed": b.get("confirmed"),
            "fromTopics": b.get("from_topics", ""), "at": bp.stat().st_mtime}


def article_from_process(pp):
    k = pp.name.replace(".process.json", "")
    p = json.loads(read(pp))
    steps = [step(i, ROOT / s["file"], s["by"], s.get("feedback", ""), p["title"], s.get("mode", "")) for i, s in enumerate(p["steps"], 1)]
    return {"id": k, "kind": "process", "label": p["title"], "thesis": p.get("thesis", ""), "sources": p.get("sources", []),
            "title": p["title"], "titles": [], "steps": steps, "images": image_rounds(k), "inline": image_rounds(k, True),
            "inlinePicked": p.get("inline", []), "length": p.get("length", "full"), "hero": p.get("hero", ""),
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


def chat_log(k):
    f = STUDIO / "chat" / f"{safe_id(k)}.jsonl"
    return [json.loads(l) for l in read(f).splitlines() if l.strip()]


def state():
    with LOCK:
        jobs = sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)[:60]
    return {"library": library(), "topics": topic_rounds(), "articles": articles(), "jobs": jobs,
            "collects": collect_rounds()}


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


def act_topics(_):
    return start("topics", "", PY + ["scripts/topic_candidates.py"])


def act_pick_topic(a):
    rnd, n = str(a["round"]), str(int(a["n"]))
    if not re.match(r"^\d{8}-\d{6}$", rnd) or not (ROOT / "runs" / "topics" / rnd / "astra.json").exists():
        raise ValueError("잘못된 주제 회차")
    r = subprocess.run(PY + ["scripts/topic_candidates.py", "--pick", rnd, n], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise ValueError(r.stderr[-500:])
    k = f"{rnd}-{n}"
    act_titles({"article": k})
    return {"article": k}


def act_titles(a):
    k = a["article"]
    bp = brief_path(k)
    d = ROOT / "runs" / "titles0" / k
    if (d / "astra.md").exists():  # 다시 뽑으면 앞 회차를 남긴다
        n = len(list(d.glob("astra-*.md"))) + 1
        (d / "astra.md").rename(d / f"astra-{n}.md")
    return start("titles", k, PIPE + ["--titles", str(bp.relative_to(ROOT))])


def act_title(a):
    k, t = a["article"], a["title"].strip()
    b = json.loads(read(brief_path(k)))
    b["title"] = t
    brief_path(k).write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"title": t}


def act_write(a):
    k = a["article"]
    return start("write", k, PIPE + [str(brief_path(k).relative_to(ROOT))])


def act_revise(a):
    k, fb = a["article"], str(a["feedback"])
    brief_path(k)
    inbox = ROOT / "runs" / "columns" / k / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    f = inbox / (time.strftime("%Y%m%d-%H%M%S") + ".txt")
    f.write_text(fb, encoding="utf-8")  # 멘토 피드백은 받은 그대로 파일로만 넘긴다
    return start("revise", k, PIPE + ["--revise", str(brief_path(k).relative_to(ROOT)), str(f.relative_to(ROOT))])


def act_images(a):
    k = safe_id(a["article"])
    pp = process_path(k)
    target = json.loads(read(pp))["steps"][-1]["file"] if pp else k
    if pp:  # 확정 칼럼은 원고 파일 이름이 그림 폴더 이름이 된다
        target = str(Path(target))
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
        return start("shorten", k, PIPE + ["--shorten", str(brief_path(k).relative_to(ROOT))])
    out_dir = ROOT / "runs" / "columns" / k / ("_shorten-" + time.strftime("%Y%m%d-%H%M%S"))

    def after(j):  # 확정 칼럼: 결과를 과정 기록에 다음 과정으로 붙인다
        f = ROOT / "columns" / f"{k}-절반.md"
        f.write_text(read(out_dir / "output.md"), encoding="utf-8")
        d = json.loads(read(pp))
        d["steps"].append({"file": str(f.relative_to(ROOT)), "by": "astra", "mode": "절반"})
        pp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return start("shorten", k, PIPE + ["--shorten-file", art["steps"][-1]["file"], str(out_dir.relative_to(ROOT))], after)


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
    conf = {"date": date.today().isoformat(), "step": n, "file": str(out.relative_to(ROOT)), "inline": sum(map(len, imgs.values()))}
    if art.get("hero"):
        img = ROOT / "columns" / "img" / f"{out.stem}.png"
        img.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / image_src(art["hero"]), img)
        conf["hero"] = str(img.relative_to(ROOT))
    meta_update(k, confirmed=conf)
    return conf


def act_collect(a):
    req = str(a.get("request", "")).strip()
    return start("collect", req[:40] or "자동 · Threads·LinkedIn", PY + ["scripts/collect.py", req])


DIRECTOR = ROOT / "scripts" / "director_system.md"


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
           "--permission-mode", "bypassPermissions", "--append-system-prompt", read(DIRECTOR)]
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


ACTIONS = {"topics": act_topics, "pick-topic": act_pick_topic, "titles": act_titles, "title": act_title,
           "write": act_write, "revise": act_revise, "images": act_images, "hero": act_hero,
           "confirm": act_confirm, "collect": act_collect, "chat": act_chat, "inline": act_inline, "length": act_length}


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
                return self.send_json(sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)[:60])
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
            return self.send_json({"text": read(ROOT / j["log"])[-6000:] if j else ""})
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
    """Tailscale 주소(100.64.0.0/10)만 찾는다 — 같은 공유기(LAN)에는 열지 않는다."""
    out = subprocess.run(["ip", "-4", "-o", "addr"], capture_output=True, text=True).stdout
    ips = re.findall(r"inet (100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)/", out)
    return list(dict.fromkeys(ips))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8771
    binds = ["127.0.0.1"] + tailnet_ips()
    HOSTS.update(binds + ["localhost"])
    servers = [ThreadingHTTPServer((h, port), H) for h in binds]
    for srv in servers[1:]:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("칼럼 작업실 " + " · ".join(f"http://{h}:{port}" for h in binds), flush=True)
    servers[0].serve_forever()
