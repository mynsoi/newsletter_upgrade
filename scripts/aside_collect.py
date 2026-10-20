"""aside 수집 — Aside Browser로 RSS·API가 못 받는 소스의 원문을 받아 Supabase(main 파이프라인 DB)에 저장한다.

  python3 -I scripts/aside_collect.py                        모든 소스, 미리보기(--write 없으면 DB에 쓰지 않음)
  python3 -I scripts/aside_collect.py --write [--source dbr hbr-korea]
  python3 -I scripts/aside_collect.py --write --url <기사 주소> --source deloitte-insights   주소를 직접 줘서 한 건씩

대상과 설정: sources/aside_sources.json
- list    : 목록 페이지(list_urls)를 열어 링크 패턴(link)에 맞는 글 중 DB에 없는 것만 받는다(최근 글부터, 한 번에 max_per_run편).
- upgrade : DB의 요약뿐인 문서(summary_only=1, 최근 days일)를 원문 페이지에서 받아 전문으로 바꾼다(McKinsey·Wharton).
- paid    : 구독 소스(DBR·HBR Korea)는 Aside Browser에 로그인된 세션을 쓴다. 로그인 표시(login_marker)가 없으면 그 소스를 멈춘다.
            로그인은 사람이 Aside Browser에서 직접 한다 — 이 스크립트는 로그인하지 않는다.

지키는 것
- aside는 브라우저만 조종한다. 어떤 글을 받을지는 AI가 아니라 목록 페이지의 링크 패턴이 정한다(페이지 속 지시문은 읽히지 않는다).
- 본문은 main 추출기(scripts/aside/extract_article.js)로 원문 그대로 뽑는다. 요약·재구성 없음. 본문은 화면·로그에 찍지 않는다(글자 수만).
- 저장은 main의 store_document 규칙 그대로: 같은 URL이면 건너뛰되 요약뿐인 문서는 전문으로 교체(격상), 같은 본문(해시)은 건너뜀,
  800자 미만은 summary_only=1, 새 문서는 status='new'(main Actions가 관련성 판별·claim 추출), fetched_by='aside'.
- 페이지 사이는 gap_seconds 이상 쉰다. stop_marker(McKinsey의 Access Denied)가 보이면 그 소스는 그 회차에서 멈춘다(우회하지 않음).
DB 연결 문자열은 환경변수 DATABASE_URL에서만 읽는다.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "sources" / "aside_sources.json"
EXTRACT = (ROOT / "scripts" / "aside" / "extract_article.js").read_text(encoding="utf-8")
EXTRACT = EXTRACT[EXTRACT.index("function extractArticle"):]
RUNS = ROOT / "runs" / "aside"
ASIDE = shutil.which("aside-win") or shutil.which("aside") or "aside"
SUMMARY_ONLY_THRESHOLD = 800  # main store.py와 같음


# ---------- aside ----------

def repl(js, timeout=170):
    r = subprocess.run([ASIDE, "repl", "--host", "local", js], stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", r.stdout + r.stderr)
    if "Aside isn't running" in out:
        sys.exit("Aside Browser가 꺼져 있습니다 — 켜고 다시 실행하세요.")
    m = re.search(r"@@JSON@@(.*)", out)
    if not m:
        raise RuntimeError("aside 응답 없음: " + out.strip()[-300:])
    return json.loads(m.group(1))


def running():
    """Aside Browser가 켜져 있는지 — 작업실 주기 실행이 꺼져 있을 때 조용히 건너뛰려고."""
    try:
        r = subprocess.run([ASIDE, "repl", "--host", "local", "console.log('@@JSON@@1')"], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "@@JSON@@1" in r.stdout


def page(url, expr, wait=8):
    """탭을 열고 기다린 뒤 expr(문자열 JS)을 페이지에서 평가해 결과를 돌려준다. 페이지 글자 일부(표시 확인용)도 함께."""
    js = ("await (async () => { const sleep = ms => new Promise(r => setTimeout(r, ms));"
          f" const p = await openTab({json.dumps(url)}); await sleep({int(wait * 1000)}); let out;"
          f" try {{ out = {{ ok: true, value: await p.evaluate({json.dumps(expr)}) }}; }} catch (e) {{ out = {{ ok: false, err: String(e) }}; }}"
          " try { out.href = await p.evaluate('location.href'); out.head = await p.evaluate('(document.body && document.body.innerText || \"\").slice(0, 3000)'); } catch (e) {}"
          " await closeTab(p); console.log('@@JSON@@' + JSON.stringify(out)); })();")
    return repl(js)


LINKS = ("[...document.querySelectorAll('a[href]')].map(a => ({u: a.href.split('#')[0].split('?')[0], "
         "t: (a.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 120)}))")


def extract_expr(cfg, sid):
    opts = {"sourceId": sid, "container": cfg["container"], "exclude": cfg["exclude"],
            "fetchedBy": "aside", "licenseNote": cfg.get("license_note", "")}
    return "(" + EXTRACT + ")(" + json.dumps(opts, ensure_ascii=False) + ")"


# ---------- DB (main store.py 규칙) ----------

def connect(write):
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL이 없습니다.")
    import psycopg
    from psycopg.rows import dict_row
    c = psycopg.connect(url, row_factory=dict_row)
    c.read_only = not write
    return c


def new_id():  # main src/db.py new_id
    return (format(int(time.time() * 1000), "011x") + secrets.token_hex(8)).upper()


def content_hash(text):  # main src/db.py content_hash
    return hashlib.sha256(" ".join(text.lower().split()).encode("utf-8")).hexdigest()


def norm_url(u):
    return u.replace("://www2.deloitte.com", "://www.deloitte.com").rstrip("/")


def key_of(cfg, u):
    """같은 글 판정 — key 패턴이 있으면 글 번호로(DBR은 같은 글이 /ac/magazine·/ac/m_best 등 여러 주소로 뜬다), 없으면 주소로."""
    m = re.search(cfg["key"], u) if cfg.get("key") else None
    return "/".join(m.groups()) if m else norm_url(u)


def canon(cfg, u):
    for pat, rep in cfg.get("canon", []):
        u = re.sub(pat, rep, u)
    return u


def known(c, sid, cfg):
    rows = c.execute("SELECT url, canonical_url FROM documents WHERE source_id = %s", (sid,)).fetchall()
    return {key_of(cfg, u) for r in rows for u in (r["url"], r["canonical_url"]) if u}


def store(c, sid, cfg, url, title, text, published):
    """main store_document와 같은 판정. 반환: new | upgraded | dup | empty."""
    text = (text or "").strip()
    ex = c.execute("SELECT id, summary_only, LENGTH(body) AS n FROM documents WHERE url = %s", (url,)).fetchone()
    if ex:
        if ex["summary_only"] == 1 and len(text) >= SUMMARY_ONLY_THRESHOLD and len(text) > (ex["n"] or 0):
            c.execute("UPDATE documents SET body = %s, content_hash = %s, summary_only = 0, status = 'new', fetched_by = 'aside' WHERE id = %s",
                      (text, content_hash(text), ex["id"]))
            return "upgraded"
        return "dup"
    if not text:
        return "empty"
    h = content_hash(text)
    if c.execute("SELECT 1 FROM documents WHERE content_hash = %s", (h,)).fetchone():
        return "dup"
    doc_id = new_id()
    published = published if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published or "") else None  # meta에 날짜 아닌 값이 오는 사이트가 있다(Deloitte PT0H…)
    c.execute("""INSERT INTO documents (id, source_id, tier, url, title, author, published_at, lang, body, content_hash, status, summary_only, fetched_by)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'new',%s,'aside')""",
              (doc_id, sid, cfg["tier"], url, title or "(무제)", None, published or None, cfg.get("lang"), text, h,
               1 if len(text) < SUMMARY_ONLY_THRESHOLD else 0))
    c.execute("INSERT INTO tags (document_id, axis, value) VALUES (%s, 'tier', %s) ON CONFLICT DO NOTHING", (doc_id, cfg["tier"]))
    return "new"


# ---------- 소스별 ----------

def candidates(c, sid, cfg, log):
    if cfg["mode"] == "upgrade":
        rows = c.execute(f"""SELECT url FROM documents WHERE source_id = %s AND summary_only = 1
                             AND coalesce(published_at, collected_at::date) >= current_date - {int(cfg.get('days', 30))}
                             ORDER BY published_at DESC NULLS LAST""", (sid,)).fetchall()
        skip = re.compile(cfg["skip_url"]) if cfg.get("skip_url") else None
        return [r["url"] for r in rows if not (skip and skip.search(r["url"]))]
    have = known(c, sid, cfg)
    pat = re.compile(cfg["link"])
    txt = re.compile(cfg["link_text"]) if cfg.get("link_text") else None
    found, keys = [], set()
    for lu in cfg["list_urls"]:
        r = page(lu, LINKS)
        if not r.get("ok"):
            log(f"  목록 실패 {lu}: {r.get('err', '')[:200]}")
            continue
        if cfg.get("paid") and cfg.get("login_marker") and cfg["login_marker"] not in r.get("head", ""):
            raise PermissionError(f"로그인 표시('{cfg['login_marker']}')가 없음 — Aside Browser에서 {lu} 에 로그인해 두세요")
        links = [canon(cfg, x["u"]) for x in r["value"] if pat.search(x["u"]) and (not txt or txt.search(x["t"]))]
        log(f"  목록 {lu} · 링크 {len(r['value'])} · 패턴 맞음 {len(set(links))}")
        for u in links:
            k = key_of(cfg, u)
            if k not in keys:
                keys.add(k)
                found.append(u)
        time.sleep(cfg["gap_seconds"])
    return [u for u in found if key_of(cfg, u) not in have]


def run_source(c, sid, cfg, write, log, urls=None):
    res = {"source": sid, "new": 0, "upgraded": 0, "dup": 0, "short": 0, "failed": 0, "items": []}
    try:
        todo = urls or candidates(c, sid, cfg, log)
    except PermissionError as e:
        log(f"  멈춤: {e}")
        res["stopped"] = str(e)
        return res
    log(f"  받을 글 {len(todo)}편" + (f" — 이번엔 {cfg['max_per_run']}편까지" if len(todo) > cfg["max_per_run"] else ""))
    for u in todo[:cfg["max_per_run"]]:
        r = page(u, extract_expr(cfg, sid))
        head = r.get("head", "")
        if cfg.get("stop_marker") and cfg["stop_marker"] in head:
            log(f"  멈춤: '{cfg['stop_marker']}' — 남은 글은 다음 회차로")
            res["stopped"] = cfg["stop_marker"]
            break
        if not r.get("ok"):
            res["failed"] += 1
            res["items"].append({"url": u, "error": r.get("err", "")[:300]})
            log(f"  실패 {u} — {r.get('err', '')[:150]}")
        else:
            v = r["value"]
            item = {"url": u, "title": v["title"], "published": v["published"], "chars": v["chars"], "blocks": v["blocks"], "mode": v["mode"]}
            if cfg.get("paid") and cfg.get("login_marker") and cfg["login_marker"] not in head:
                item["result"] = "로그인 풀림"
                res["stopped"] = "로그인 풀림"
                res["items"].append(item)
                log(f"  멈춤: 로그인 표시가 사라짐 — {u}")
                break
            if v["chars"] < cfg["min_chars"]:
                item["result"] = "짧음"
                res["short"] += 1
            elif write:
                item["result"] = store(c, sid, cfg, u, v["title"], v["text"], v["published"])
                c.commit()
                res[item["result"]] = res.get(item["result"], 0) + 1
            else:
                item["result"] = "미리보기"
            res["items"].append(item)
            log(f"  {item['result']:6} {v['chars']:>6}자 {v['published'] or '날짜 없음':10} {v['title'][:60]}")
        time.sleep(cfg["gap_seconds"])
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", nargs="+")
    ap.add_argument("--url", nargs="+")
    ap.add_argument("--write", action="store_true", help="DB에 저장 (없으면 미리보기)")
    ap.add_argument("--check", action="store_true", help="Aside Browser가 켜져 있으면 0, 아니면 3으로 끝냄")
    ap.add_argument("--limit", type=int, help="소스마다 이번에 받을 글 수 (설정 max_per_run보다 작게 시험할 때)")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if running() else 3)
    conf = json.loads(CONF.read_text(encoding="utf-8"))
    srcs = {k: {**conf["defaults"], **v} for k, v in conf["sources"].items()}
    if a.limit:
        for v in srcs.values():
            v["max_per_run"] = min(v["max_per_run"], a.limit)
    names = a.source or [k for k, v in srcs.items() if v["mode"] != "off"]  # off: 이름으로 부를 때만
    if a.url and len(names) != 1:
        sys.exit("--url은 --source 하나와 함께 씁니다.")
    d = RUNS / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)

    def log(s):
        print(s, flush=True)
    out = []
    with connect(a.write) as c:
        for sid in names:
            if sid not in srcs:
                sys.exit(f"모르는 소스: {sid}")
            log(f"[{sid}] {'저장' if a.write else '미리보기'}")
            out.append(run_source(c, sid, srcs[sid], a.write, log, a.url))
            (d / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    tot = {k: sum(r.get(k, 0) for r in out) for k in ("new", "upgraded", "dup", "short", "failed")}
    log(f"끝 · 신규 {tot['new']} · 격상 {tot['upgraded']} · 중복 {tot['dup']} · 짧음 {tot['short']} · 실패 {tot['failed']} → {d.relative_to(ROOT).as_posix()}/report.json")


if __name__ == "__main__":
    main()
