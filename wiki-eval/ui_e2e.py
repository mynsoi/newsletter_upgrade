"""작업실 화면에서 글 한 편을 끝까지 — 주제 고르기 → 제목(astra 후보 1번) → 쓰기(과정 1·2·3, 1,500자) → 본문 그림 2개 → 확정 (2026-10-11)

멘토: "화면에서 테스트로 결과까지 몇개 뽑아서 보여주어라" — 버튼은 화면에서 누르고(헤드리스 브라우저), 오래 걸리는 작업은 /api/jobs로 끝을 기다린다.
제목은 시험이라 astra 후보 1번을 그대로 고른다(내가 고르지 않는다 — 멘토가 바꿀 수 있다).
사용: python3 wiki-eval/ui_e2e.py "<주제 카드에 보이는 글자 일부>" <캡처 폴더> [작업실 주소]
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

NEEDLE, OUT = sys.argv[1], Path(sys.argv[2])
BASE = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8771"
OUT.mkdir(parents=True, exist_ok=True)


def api(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def article(k):
    return next((a for a in api("/api/state")["articles"] if a["id"] == k), None)


def wait_job(kind, k, limit):
    t0 = time.time()
    time.sleep(5)
    while time.time() - t0 < limit:
        js = [j for j in api("/api/jobs") if j["kind"] == kind and j["target"] == k]
        if js and js[0]["status"] != "running":
            return js[0]["status"], round(time.time() - t0)
        time.sleep(10)
    return "timeout", round(time.time() - t0)


def say(*a):
    print(f"[{time.strftime('%H:%M:%S')}] {NEEDLE[:12]}", *a, flush=True)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    # 1. 주제 고르기
    pg.goto(BASE + "/#/topics")
    pg.wait_for_timeout(2500)
    pg.get_by_text(NEEDLE, exact=False).first.click()
    pg.wait_for_timeout(1200)
    pg.get_by_role("button", name="이 주제로").first.click()
    pg.wait_for_url("**/#/a/*/title", timeout=30000)
    k = pg.url.split("#/a/")[1].split("/")[0]
    say("글", k)
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(OUT / "1-title.png"))
    # 2. 제목 — astra 후보 1번
    a = article(k)
    first = a["titles"][-1]["items"][0]
    pg.get_by_text(first, exact=True).first.click()
    for _ in range(20):
        if (article(k) or {}).get("title"):
            break
        time.sleep(0.5)
    say("제목", article(k)["title"])
    pg.wait_for_timeout(800)
    # 3. 쓰기
    pg.get_by_role("button", name="쓰기").first.click()
    st, s = wait_job("write", k, 1800)
    say("쓰기", st, f"{s}s")
    a = article(k)
    pg.goto(BASE + f"/#/a/{k}/process")
    pg.wait_for_timeout(2500)
    pg.screenshot(path=str(OUT / "2-process.png"))
    # 4. 본문 그림 2개
    pg.goto(BASE + f"/#/a/{k}/image")
    pg.wait_for_timeout(2000)
    pg.get_by_role("button", name="본문 그림 뽑기").first.click()
    st2, s2 = wait_job("inline", k, 1800)
    say("본문 그림", st2, f"{s2}s")
    pg.reload()
    pg.wait_for_timeout(3000)
    a = article(k)
    items = [it for it in (a["inline"][-1]["items"] if a["inline"] else []) if it.get("src")]
    for it in items[:2]:
        pg.get_by_text(it["name"], exact=True).first.click()
        pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "3-images.png"))
    say("고른 그림", len(article(k)["inlinePicked"]))
    # 5. 확정 — 마지막 과정으로
    pg.goto(BASE + f"/#/a/{k}/confirm")
    pg.wait_for_timeout(2500)
    pg.locator("button", has_text="확정").last.click()  # 위쪽 탭에도 "확정"이 있다 — 오른쪽 확정 버튼은 맨 뒤
    for _ in range(30):
        if (article(k) or {}).get("confirmed"):
            break
        time.sleep(1)
    a = article(k)
    pg.reload()
    pg.wait_for_timeout(3000)
    pg.screenshot(path=str(OUT / "4-confirm.png"), full_page=True)
    last = a["steps"][-1] if a["steps"] else {}
    res = {"article": k, "title": a.get("title"), "steps": [s.get("mode") or s.get("by") for s in a["steps"]],
           "chars": len("".join(last.get("text", "").split("\n", 1)[-1].split())), "confirmed": a.get("confirmed"),
           "inlinePicked": len(a.get("inlinePicked", [])), "write": [st, s], "inline": [st2, s2]}
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    say("끝", json.dumps(res, ensure_ascii=False))
    b.close()
