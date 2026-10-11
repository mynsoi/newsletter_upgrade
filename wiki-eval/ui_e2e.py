"""작업실 화면 시험 — 대화 화면(app/src/views/Flow.tsx)을 헤드리스 브라우저로 직접 눌러 본다 (2026-10-11 예전 탭 화면을 지우며 바꿈).

사용: python3 wiki-eval/ui_e2e.py <캡처 폴더> [--models] [--full "<요청>"] [--base http://localhost:8771]
  기본      모델을 부르지 않는 확인. 쓴 글 하나의 과정 1·2·3 파일을 복사한 시험 글(zz-ui-<시각>)로
            비교 · 미리보기 · 독자/분량 표시 · 여기서 이어 쓰기 · 편집 저장 · 처음부터 다시 쓰기 · 예전 주소(#/a/<글>/process) · 삭제
  --models  위 시험 글에서 제목 다시 뽑기 · 절반 줄이기도(astra, 합쳐 2분 안팎)
  --full    메인 채팅에 "<요청>"을 보내 끝까지: 원문 고르기 → 이어서 한 말 → 이 원문으로 → 제목에 바라는 말 → 제목 → 쓰기
            → 피드백 → 과정 4 → 삭제 (Claude·astra, 20분 안팎)
- 시험 글은 끝나면 화면의 삭제 버튼으로 지우고 휴지통(trash/<글>-*)까지 비운다. 멘토의 글은 복사만 하고 건드리지 않는다.
- 제목은 시험이라 astra 마지막 회차 1번을 고른다(멘토 글이 아니다).
"""
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
OUT = Path(args[0])
BASE = args[args.index("--base") + 1] if "--base" in args else "http://localhost:8771"
MODELS = "--models" in args
FULL = args[args.index("--full") + 1] if "--full" in args else ""
OUT.mkdir(parents=True, exist_ok=True)
FAILS = []


def state():
    return json.load(urllib.request.urlopen(BASE + "/api/state"))


def art(k):
    return next((a for a in state()["articles"] if a["id"] == k), None)


def run_of(k):
    return next((r for r in state().get("mine", []) if r["id"] == k), None)


def busy(k):
    return any(j["status"] == "running" and j["target"] == k for j in state()["jobs"])


def check(ok, what):
    print(("  ✓ " if ok else "  ✗ ") + what, flush=True)
    if not ok:
        FAILS.append(what)


def wait(cond, what, limit=1800):
    t0 = time.time()
    while time.time() - t0 < limit:
        try:
            if cond():
                return check(True, f"{what} ({time.time() - t0:.0f}s)")
        except Exception:
            pass
        time.sleep(5)
    check(False, f"{what} — 시간 초과")


def shot(pg, name):
    time.sleep(1)
    pg.screenshot(path=str(OUT / f"{name}.png"))


def say(pg, text):
    ta = pg.locator("textarea").last
    ta.fill(text)
    time.sleep(0.3)
    ta.press("Enter")
    time.sleep(3)


def cleanup(pg, k):
    """화면의 삭제 버튼(두 번) → 목록에서 사라졌는지 → 휴지통까지 비움"""
    pg.goto(f"{BASE}/#/a/{k}", wait_until="networkidle")
    time.sleep(1)
    d = pg.locator("button[title='삭제']")
    d.click()
    time.sleep(0.4)
    d.click()
    wait(lambda: art(k) is None and run_of(k) is None, "삭제 — 목록에서 사라짐", 30)
    gone = list((ROOT / "trash").glob(f"{k}-*"))
    check(bool(gone), "삭제 — 휴지통으로 옮겨짐")
    for x in gone:
        shutil.rmtree(x)


def test_copy(pg):
    """모델 없이: 쓴 글 하나를 복사한 시험 글로 지금 글 패널·이어 쓰기·편집·다시 쓰기·예전 주소"""
    src = next((a for a in state()["articles"] if a["kind"] == "brief" and len(a["steps"]) >= 3
                and (ROOT / "runs" / "columns" / a["id"] / "final.md").exists()), None)
    if not src:
        return check(False, "복사할 쓴 글이 없음")
    k = "zz-ui-" + time.strftime("%H%M%S")
    d = ROOT / "runs" / "columns" / k
    d.mkdir(parents=True)
    for f in ("draft.md", "r4.md", "final.md"):
        shutil.copy(ROOT / "runs" / "columns" / src["id"] / f, d / f)
    b = {"topic": k, "label": "[시험] 화면 시험", "thesis": "[시험] 화면 시험 글", "sources": src["sources"][:1], "title": "[시험] 화면 시험 글", "target": "전 직원"}
    (ROOT / "briefs" / f"{k}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"시험 글 {k} (과정 1·2·3은 {src['id']}에서 복사)", flush=True)
    try:
        pg.goto(f"{BASE}/#/a/{k}/process", wait_until="networkidle")  # 예전 주소도 대화 화면으로
        time.sleep(1.5)
        check(pg.locator("button[title='삭제']").count() == 1 and pg.get_by_role("button", name="미리보기").count() == 1, "예전 주소 → 대화 화면")
        check(pg.get_by_text("전 직원", exact=True).count() >= 1 and pg.get_by_text("절반", exact=True).count() >= 1, "오른쪽 위 독자·분량")
        pg.get_by_role("button", name="비교").click()
        time.sleep(0.8)
        check(pg.locator(".s-add").count() > 0, "비교 — 바뀐 문장 형광")
        shot(pg, "1-비교")
        pg.get_by_role("button", name="미리보기").click()
        time.sleep(0.8)
        check(pg.locator("article").count() == 1 and pg.locator("aside").get_by_role("button", name="과정 3으로 확정").count() == 1, "미리보기 — 완성본 + 확정 버튼")
        shot(pg, "2-미리보기")
        pg.get_by_role("button", name="본문", exact=True).click()
        # 과정 2를 골라 여기서 이어 쓰기
        pg.locator("div.space-y-7 > div").filter(has_text="과정 2").locator("button").first.click()
        time.sleep(0.8)
        pg.get_by_role("button", name="여기서 이어 쓰기").click()
        time.sleep(2.5)
        a = art(k)
        check(len(a["steps"]) == 4 and a["steps"][3]["text"] == a["steps"][1]["text"] and a["steps"][3]["by"] == "멘토", "여기서 이어 쓰기 → 과정 4 = 과정 2")
        # 편집 저장
        pg.get_by_role("button", name="편집", exact=True).click()
        time.sleep(1.5)
        ed = pg.locator(".ProseMirror").first
        ed.click()
        pg.keyboard.press("Control+Home")
        pg.keyboard.type("[시험 편집] ")
        shot(pg, "3-편집")
        pg.get_by_role("button", name="저장", exact=True).click()
        time.sleep(2.5)
        a = art(k)
        check(len(a["steps"]) == 5 and a["steps"][4]["text"].startswith("[시험 편집]"), "편집 저장 → 멘토 과정 5")
        if MODELS:
            pg.get_by_role("button", name="절반", exact=True).click()
            wait(lambda: not busy(k) and len(art(k)["steps"]) == 6 and art(k)["steps"][5]["mode"] == "절반", "절반 → 과정 6 (astra)", 600)
            shot(pg, "4-절반")
        # 처음부터 다시 쓰기
        r = pg.get_by_role("button", name="처음부터 다시 쓰기")
        r.click()
        time.sleep(0.4)
        pg.get_by_role("button", name="한 번 더").click()
        time.sleep(2.5)
        a = art(k)
        check(not a["steps"] and len(a["tries"]) == 1 and pg.get_by_role("button", name="쓰기", exact=True).count() == 1, "처음부터 다시 쓰기 → 앞 글 접힘 + 쓰기")
        shot(pg, "5-다시쓰기")
        if MODELS:  # 쓰기 전 단계 — 보낸 말은 제목 회차로, 그 뒤 말 없이 다시 뽑기
            n = len(a["titles"])
            say(pg, "[시험] 짧게")
            wait(lambda: not busy(k) and len(art(k)["titles"]) == n + 1, "제목에 바라는 말 → 새 회차 (astra)", 300)
            time.sleep(2)
            pg.get_by_role("button", name="다시 뽑기").click()
            wait(lambda: not busy(k) and len(art(k)["titles"]) == n + 2, "제목 다시 뽑기 (astra)", 300)
            shot(pg, "6-제목")
    finally:
        cleanup(pg, k)


def test_full(pg, request):
    """메인 채팅부터 끝까지 (모델 호출)"""
    pg.goto(f"{BASE}/#/articles", wait_until="networkidle")
    time.sleep(1)
    say(pg, request)
    t0 = time.time()
    while "#/a/" not in pg.url and time.time() - t0 < 20:
        time.sleep(0.5)
    k = pg.url.split("#/a/")[-1].split("/")[0]
    check(k.startswith("m-"), f"보내자마자 대화 화면 ({k})")
    try:
        shot(pg, "f1-고르는중")
        wait(lambda: run_of(k)["status"] != "running" and not busy(k), "원문 고르기")
        say(pg, "[시험] 다른 자리의 사례를 중심으로 다시 골라 줘")
        wait(lambda: run_of(k)["status"] != "running" and not busy(k), "이어서 한 말로 다시 고르기")
        check((ROOT / "runs" / "mine" / k / "picks-1.json").exists(), "앞 차례 picks-1.json")
        shot(pg, "f2-다시고름")
        pg.get_by_role("button", name="이 원문으로").click()
        time.sleep(3)
        n = len(art(k)["titles"])
        say(pg, "[시험] 단정하는 제목으로")
        wait(lambda: not busy(k) and len(art(k)["titles"]) > n, "제목에 바라는 말 → 새 회차")
        t = art(k)["titles"][-1]["items"][0]
        pg.get_by_text(t, exact=True).last.click()
        time.sleep(3)
        pg.get_by_role("button", name="쓰기", exact=True).click()
        wait(lambda: not busy(k) and len(art(k)["steps"]) >= 3, "쓰기 → 과정 1·2·3", 2400)
        shot(pg, "f3-씀")
        n = len(art(k)["steps"])
        say(pg, "[시험] 첫 문단을 한 문장 줄여 주세요")
        wait(lambda: not busy(k) and len(art(k)["steps"]) > n, "피드백 → 다음 과정")
        shot(pg, "f4-피드백")
    finally:
        cleanup(pg, k)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    test_copy(pg)
    if FULL:
        test_full(pg, FULL)
    b.close()
print("끝 · 실패 " + (", ".join(FAILS) if FAILS else "없음"))
sys.exit(1 if FAILS else 0)
