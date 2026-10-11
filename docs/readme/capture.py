"""README 화면 캡처 — 작업실 대화 화면 기준 (2026-10-11 밤 다시 찍음)

사용: python3 docs/readme/capture.py [작업실 주소=http://localhost:8771]
어두운 화면 1440×900, jpg. 글은 저장소에 커밋된 것만 찍는다. 그 글을 지웠으면 그 캡처는 건너뛴다.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8771"
OUT = Path(__file__).resolve().parent
SHOTS = [  # (파일, 주소, 대화에서 위로 올릴 표시 글자, 오른쪽 '지금 글'에서 누를 보기)
    ("screen-articles.jpg", "#/articles", None, None),
    ("screen-column.jpg", "#/a/2026-10-08-ai-퇴근시간", None, "미리보기"),
    ("screen-mine.jpg", "#/a/m-20261011-215031", "top", None),
    ("screen-titles.jpg", "#/a/w-20261010-161003", "top", None),
    ("screen-process.jpg", "#/a/m-20261011-173414", "과정 2", "비교"),
    ("screen-images.jpg", "#/a/m-20261011-173414", "그림", None),
]


def scroll_to(pg, mark):
    """대화 칸에서 그 표시 글자가 위쪽에 오게 — 대화는 열리면 맨 아래로 내려가므로 그 뒤에 올린다"""
    time.sleep(1.5)
    box = pg.locator("section div.overflow-y-auto").first
    if mark == "top":
        box.evaluate("e => { e.style.scrollBehavior = 'auto'; e.scrollTop = 0; }")
        return
    el = pg.get_by_text(mark, exact=True).first  # 대화의 이름표가 확정 카드의 칩보다 먼저 나온다
    if el.count():
        el.evaluate("e => { const b = e.closest('.overflow-y-auto'); b.style.scrollBehavior = 'auto'; b.scrollTop += e.getBoundingClientRect().top - 90; }")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")
    for name, h, mark, view in SHOTS:
        pg.goto(f"{BASE}/{h}", wait_until="networkidle")
        time.sleep(2)
        if h.startswith("#/a/") and pg.locator("section").count() == 0:
            print("없는 글 — 건너뜀:", h)
            continue
        if view:
            pg.get_by_role("button", name=view, exact=True).click()
        if mark:
            scroll_to(pg, mark)
        time.sleep(1)
        pg.screenshot(path=str(OUT / name), type="jpeg", quality=82)
        print(name)
    b.close()
