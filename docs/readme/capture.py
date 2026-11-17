"""README 화면 캡처 — 작업실 화면 8장 (2026-11-17 다시 찍음)

사용: python3 docs/readme/capture.py [작업실 주소=http://localhost:8771]
어두운 화면 1440×900, jpg. 작업실 서버가 떠 있어야 한다. 글은 저장소에 커밋된 확정 칼럼(ARTICLE)을 찍는다 — 그 글을 지웠으면 ARTICLE을 바꾼다.
작업실에는 아무것도 쓰지 않는다(누르는 것은 보기 전환뿐).

제목 화면(screen-titles.jpg)만 예외: 제목 후보는 '원고를 정한 뒤 · 그림 전' 단계에서만 보이는데 ARTICLE은 이미 확정한 글이라,
화면이 받는 상태 응답(/api/state)을 브라우저 안에서만 그 단계로 바꿔 찍는다. 제목 후보는 그 글이 실제로 받은 것 그대로이고, 서버·파일은 바뀌지 않는다.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8771"
OUT = Path(__file__).resolve().parent
ARTICLE = "m-20261111-131355"  # 확정 칼럼 「AI가 요약해 줘도 판단력은 직접 길러야 합니다」 — 주제 지도에서 시작, 과정 13
A = f"#/a/{ARTICLE}"
SHOTS = [  # (파일, 주소, 대화에서 위로 올릴 표시 글자, 누를 과정 카드, 오른쪽 '지금 글'에서 누를 보기, 제목 단계로 바꿔 찍기)
    ("screen-articles.jpg", "#/articles", None, None, None, False),
    ("screen-library.jpg", "#/library", None, None, None, False),
    ("screen-topics.jpg", "#/topics", None, None, None, False),
    ("screen-column.jpg", A, None, None, "미리보기", False),
    ("screen-mine.jpg", A, "top", None, None, False),
    ("screen-process.jpg", A, "과정 3", "과정 3", "비교", False),
    ("screen-titles.jpg", A, "제목 후보", None, None, True),
    ("screen-images.jpg", A, "그림", None, None, False),
]


def launch(p):
    """Playwright 크로미움이 없으면 설치된 Edge·Chrome을 쓴다(브라우저를 새로 받지 않게)."""
    for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return p.chromium.launch(**kw)
        except Exception:
            continue
    sys.exit("브라우저를 찾지 못함 — `playwright install chromium` 또는 Edge·Chrome 설치")


def title_stage(route):
    """ARTICLE을 '원고를 정한 뒤 · 그림 전'으로 — 이 페이지가 받는 응답만 바꾼다."""
    r = route.fetch()
    s = r.json()
    for a in s.get("articles", []):
        if a.get("id") == ARTICLE:
            a.update(confirmed=None, imagesDone=False, ruleCands=None, textPick={"n": len(a["steps"]), "of": len(a["steps"])})
    route.fulfill(response=r, body=json.dumps(s, ensure_ascii=False), headers={**r.headers, "content-type": "application/json"})


def scroll_to(pg, mark):
    """대화 칸에서 그 표시 글자가 위쪽에 오게 — 대화는 열리면 맨 아래로 내려가므로 그 뒤에 올린다"""
    box = pg.locator("section div.overflow-y-auto").first
    last = -1  # 열릴 때 맨 아래로 부드럽게 내려가는 움직임이 끝날 때까지 기다린다 — 끝나기 전에 올리면 다시 끌려 내려간다
    for _ in range(40):
        time.sleep(0.4)
        cur = box.evaluate("e => e.scrollTop")
        if cur == last:
            break
        last = cur
    if mark == "top":
        box.evaluate("e => { e.style.scrollBehavior = 'auto'; e.scrollTop = 0; }")
        return
    el = box.get_by_text(mark, exact=True).first  # 대화 칸 안에서만 찾는다(왼쪽 목록에도 '과정 N' 표시가 있다). 이름표가 확정 카드의 칩보다 먼저 나온다
    if not el.count():
        el = box.get_by_text(mark).first
    if el.count():
        el.evaluate("e => { const b = e.closest('.overflow-y-auto'); b.style.scrollBehavior = 'auto'; b.scrollTop += e.getBoundingClientRect().top - 90; }")
    else:
        print("  표시 글자를 못 찾음:", mark)


with sync_playwright() as p:
    b = launch(p)
    for name, h, mark, card, view, mock in SHOTS:
        pg = b.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        if mock:
            pg.route("**/api/state*", title_stage)
        pg.goto(f"{BASE}/{h}", wait_until="networkidle")
        time.sleep(2.5)
        if h.startswith("#/a/") and pg.locator("section").count() == 0:
            print("없는 글 — 건너뜀:", h)
            pg.close()
            continue
        if mark:
            scroll_to(pg, mark)
        if card:  # 과정 카드는 이름표 바로 아래에 있다 — 이름표를 위로 올린 뒤 그 아래 카드 본문을 눌러 오른쪽 '지금 글'에 띄운다
            box = pg.locator("section div.overflow-y-auto").first.get_by_text(card, exact=True).first.bounding_box()
            pg.mouse.click(box["x"] + 300, box["y"] + 70)
            time.sleep(0.8)
        if view:
            pg.get_by_role("button", name=view, exact=True).click()
        time.sleep(1.2)
        pg.screenshot(path=str(OUT / name), type="jpeg", quality=82)
        print(name)
        pg.close()
    b.close()
