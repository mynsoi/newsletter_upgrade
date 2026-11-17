"""README 도식 두 장 — docs/how-it-works/{flow,architecture}.html의 그림을 PNG로 찍는다 (2026-11-17)

사용: python3 docs/readme/capture_diagrams.py
먼저 도식 원본(docs/how-it-works/*.json)을 고치고 archify로 HTML을 다시 만든다:
  node <archify>/bin/archify.mjs deliver architecture docs/how-it-works/flow.json docs/how-it-works/flow.html --quality showcase
  node <archify>/bin/archify.mjs deliver architecture docs/how-it-works/architecture.json docs/how-it-works/architecture.html --quality showcase
색과 글꼴은 docs/2026-10-10-동작-원리.html이 입히는 것(SPARTA)을 그대로 가져와 입힌다 — 그 페이지에서 보는 모양과 같다.
작업실 서버 없이 파일을 바로 연다.
"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
DOCS = OUT.parent
SPARTA = re.search(r"const SPARTA = `(.*?)`;", (DOCS / "2026-10-10-동작-원리.html").read_text(encoding="utf-8"), re.S).group(1)
FONT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap"
SHOTS = [("diagram-flow.png", "flow.html"), ("diagram-architecture.png", "architecture.html")]


def launch(p):
    """Playwright 크로미움이 없으면 설치된 Edge·Chrome을 쓴다(브라우저를 새로 받지 않게)."""
    for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return p.chromium.launch(**kw)
        except Exception:
            continue
    sys.exit("브라우저를 찾지 못함 — `playwright install chromium` 또는 Edge·Chrome 설치")


with sync_playwright() as p:
    b = launch(p)
    for name, src in SHOTS:
        pg = b.new_page(viewport={"width": 1440, "height": 1800}, device_scale_factor=2, color_scheme="light")
        pg.goto((DOCS / "how-it-works" / src).as_uri(), wait_until="networkidle")
        pg.evaluate("""([css, font]) => {
            document.documentElement.setAttribute('data-theme', 'light');
            const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = font;
            const s = document.createElement('style'); s.textContent = css;
            document.head.append(l, s);
        }""", [SPARTA, FONT])
        time.sleep(2.5)  # 글꼴이 내려올 때까지
        svgs = pg.locator("svg")
        big = max(range(svgs.count()), key=lambda i: (lambda r: (r["width"] * r["height"]) if r else 0)(svgs.nth(i).bounding_box()))
        svgs.nth(big).screenshot(path=str(OUT / name))
        print(name, svgs.nth(big).bounding_box())
        pg.close()
    b.close()
