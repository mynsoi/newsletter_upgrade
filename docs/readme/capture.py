"""README 화면 캡처 — 작업실 대화 화면 기준 (2026-10-11 예전 탭 화면을 지우며 다시 찍음)

사용: python3 docs/readme/capture.py [작업실 주소=http://localhost:8771]
어두운 화면 1440×900, jpg. 글은 저장소에 커밋된 것만 찍는다. 그 글을 지웠으면 그 캡처는 건너뛴다.
screen-images.jpg(그림 카드)는 2026-10-11 자기평가 대화에서 찍은 것 — 그 글은 멘토가 지웠다(trash/).
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8771"
OUT = Path(__file__).resolve().parent


def open_(pg, h):
    """글이 없으면(지웠으면) False — 그 캡처는 건너뛴다"""
    pg.goto(f"{BASE}/{h}", wait_until="networkidle")
    time.sleep(2)
    if h.startswith("#/a/") and pg.locator("section").count() == 0:
        print("없는 글 — 건너뜀:", h)
        return False
    return True


def save(pg, name, clip=None):
    time.sleep(1)
    pg.screenshot(path=str(OUT / name), type="jpeg", quality=82, clip=clip)
    print(name)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")

    open_(pg, "#/articles")
    save(pg, "screen-articles.jpg")

    # 기준 글 — 대화 + 오른쪽 미리보기
    if open_(pg, "#/a/2026-10-08-ai-퇴근시간"):
        pg.get_by_role("button", name="미리보기", exact=True).click()
        save(pg, "screen-column.jpg")

    # 제목 회차
    if open_(pg, "#/a/w-20261010-043541"):
        save(pg, "screen-titles.jpg")

    # 과정과 피드백 — 오른쪽은 비교
    if open_(pg, "#/a/w-20261010-043840"):
        pg.get_by_role("button", name="비교", exact=True).click()
        save(pg, "screen-process.jpg")
    b.close()
