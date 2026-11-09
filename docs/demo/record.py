"""시연 영상 녹화 — 작업실을 처음부터 발행까지 실제로 눌러 가며 챕터별로 찍는다 (계획: docs/2026-10-26-시연영상-계획.md)

사용: py -3 -X utf8 -I docs/demo/record.py [챕터 …] [--base http://localhost:8781] [--to 받는사람] [--doc 첨부파일] [--more]
      py -3 -X utf8 -I docs/demo/record.py build [챕터 …]     # 찍은 프레임 → mp4 (imageio-ffmpeg)
  챕터: c1 한눈에 · c2 서재 · c3 주제 지도 · c4 요청·글 옵션 · c5 원문 확인 · c6 쓰기·피드백 · c7 원고·제목·그림·확정 · c8 발행 · c8web 배포된 웹
  챕터를 안 적으면 c1부터 c8web까지. c4가 만든 시연 글 이름은 state.json에 남아 c5부터 이어 찍을 수 있다.
녹화 방식 — Playwright 기본 녹화는 비트레이트가 낮아 글씨가 뭉개져서, CDP 스크린캐스트로 프레임(jpg)을 받아 시각과 함께 저장하고
  build가 그 시각대로 이어 30fps mp4로 만든다. AI가 일하는 동안(wait)은 초당 2장만 남긴다(편집에서 8~16배 빨리 감기).
  가짜 커서와 클릭 물결을 페이지에 그린다(스크린캐스트는 실제 커서를 찍지 않음). 클릭·입력마다 시각·위치를 marks.json에 — 편집의 확대 지점.
나오는 곳: _workspace/demo/<챕터>/frames/*.jpg · frames.json · marks.json · <챕터>.mp4 (git 밖)
실제로 바뀌는 것: c2 Supabase 받기, c4~c7 시연 글(서버가 운영 브랜치에 자동 공유), c8 실제 발행(웹 배포 · 메일 파일). 촬영 뒤 unpublish.
주제 지도 판정은 바꾸지 않는다(판정 예시에 쌓이므로) — 판정 칸에 마우스만 올린다.

2차 심사판(11/3, 계획: docs/2026-11-03-시연영상-2차심사-계획.md) — --r2를 붙이면 _workspace/demo/r2에 따로 찍고(1차 프레임은 그대로),
  챕터를 안 적으면 s2 → s3 → c4 → c5 → s4 → s5 → c7 → s5r → s6 → c8web 순서.
  s2 메뉴·탭 둘러보기 · s3 글쓰기 A(추천 주제 → 원문 확인 → 쓰기) · s4 글쓰기 B의 쓰기(c4·c5 다음) · s5 문체 피드백 → 과정 4
  · s5r 확정 뒤 규칙 후보 → 규칙에 넣기 → 규칙 파일. 글 A는 state.json의 article_a, 글 B는 article.
  s5r은 briefs/글쓰기규칙.md에 실제로 한 줄을 넣는다(다른 PC에도 올라감) — 촬영 뒤 그 줄을 지우고 공유한다(11/3 사용자).
"""
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
R2 = "--r2" in args
OUT = ROOT / "_workspace" / "demo" / ("r2" if R2 else "")
STATE = OUT / "state.json"


def opt(name, default=""):
    return args[args.index(name) + 1] if name in args else default


BASE = opt("--base", "http://localhost:8781")
TO = opt("--to")
DOC = opt("--doc")
MORE = "--more" in args
REQUEST = "회사가 AI를 쓰라고 하는데 정작 배울 시간이나 지원은 없어서 답답하다는 이야기를 써 보고 싶어"  # 리허설 ③(10/26 확정)
FOLLOW = "다른 회사 사례로 다시 골라 줘"
OPTION_KEY = "탐색 시간"  # 리허설에서 고른 옵션의 말할 것에 든 말 — 없으면 1번
REC_KEYS = ("DBS", "아틀라시안", "Atlassian")  # 넣기로 보여 줄 추천 원문
FEEDBACK = "두 번째 문단의 사례 설명을 한 문장 줄이고, 맺음은 독자에게 묻는 문장으로 끝내 주세요."
# 2차 — 글 A의 추천 주제(11/3 리허설에서 돌린 것, 없으면 첫 카드)와 글 B의 문체 피드백(지금 규칙 11개와 겹치지 않는 것)
PICK_KEY = "자료를 많이 가진 회사라도"  # 주제 탭 첫 줄에 있고 사례가 많은 주제(11/9 재녹화, 11/3 리허설에서 돌려 봄)
STYLE_FEEDBACK = "'~할 수 있습니다', '~일지도 모릅니다' 같은 흐린 끝맺음을 줄이고 단정해서 써 주세요."
CHAPTERS = ["c1", "c2", "c3", "c4", "c5", "c5b", "c6", "c7", "c8", "c8mail", "c8web", "s2", "s3", "s4", "s5", "s5r", "s6", "c7b"]
CHAPTERS_R2 = ["s2", "s3", "c4", "c5", "s4", "s5", "c7", "s5r", "s6", "c8web"]
VIEW = {"width": 1920, "height": 1080}  # 스크린캐스트는 기기 배율을 무시하고 CSS 픽셀로 찍는다 — 1080p 원본으로(10/26 시험: dsf 1.25·2 모두 1536×864)

CURSOR_JS = """
(() => {
  if (window.__demoCursor) return; window.__demoCursor = 1;
  const add = () => {
    const c = document.createElement('div');
    c.id = '__cur';
    c.style.cssText = 'position:fixed;left:-40px;top:-40px;width:22px;height:22px;z-index:2147483647;pointer-events:none;transform:translate(-3px,-2px);transition:transform .08s';
    c.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7.5 19 2.6-7.6L21 10.8z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.display = e.target.tagName === 'IFRAME' ? 'none' : ''; c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
    // 미리보기 iframe 안으로 들어가면 바깥 커서는 숨긴다(안쪽 문서가 자기 커서를 그린다 — 10/26 커서 두 개)
    addEventListener('mouseover', e => { if (e.target.tagName === 'IFRAME') c.style.display = 'none'; }, true);
    addEventListener('mousedown', e => {
      c.style.transform = 'translate(-3px,-2px) scale(.85)';
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;left:${e.clientX - 18}px;top:${e.clientY - 18}px;width:36px;height:36px;border-radius:50%;border:3px solid rgba(167,139,250,.95);z-index:2147483646;pointer-events:none;transition:transform .5s ease-out,opacity .5s ease-out`;
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(1.8)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 600);
    }, true);
    addEventListener('mouseup', () => { c.style.transform = 'translate(-3px,-2px)'; }, true);
  };
  if (document.documentElement) add(); else addEventListener('DOMContentLoaded', add);
})();
"""


# ---------- 작업실 상태 ----------

def state():
    return json.load(urllib.request.urlopen(BASE + "/api/state"))


def art(k):
    return next((a for a in state()["articles"] if a["id"] == k), None)


def busy(k=None):
    return any(j["status"] == "running" and (k is None or j["target"] == k) for j in state()["jobs"])


def saved():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save(**kv):
    STATE.write_text(json.dumps({**saved(), **kv}, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- 녹화 ----------

class Rec:
    """챕터 하나 = 프레임 폴더 하나. wait 중에는 초당 2장만."""

    def __init__(self, pg, name):
        self.pg, self.name = pg, name
        self.dir = OUT / name
        (self.dir / "frames").mkdir(parents=True, exist_ok=True)
        for f in (self.dir / "frames").glob("*.jpg"):
            f.unlink()
        self.frames, self.marks, self.slow, self.last = [], [], False, 0.0
        self.cdp = pg.context.new_cdp_session(pg)
        self.cdp.on("Page.screencastFrame", self.frame)

    def frame(self, e):
        t = e["metadata"].get("timestamp") or time.time()
        if not self.slow or t - self.last >= 0.5:
            f = f"{len(self.frames):06d}.jpg"
            (self.dir / "frames" / f).write_bytes(base64.b64decode(e["data"]))
            self.frames.append([f, t])
            self.last = t
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": e["sessionId"]})
        except Exception:  # noqa: BLE001 — 챕터를 닫는 중이면 무시
            pass

    def __enter__(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})
        print(f"● {self.name} 녹화 시작", flush=True)
        return self

    def __exit__(self, *exc):
        time.sleep(1.2)
        self.cdp.send("Page.stopScreencast")
        time.sleep(0.5)
        (self.dir / "frames.json").write_text(json.dumps(self.frames), encoding="utf-8")
        (self.dir / "marks.json").write_text(json.dumps(self.marks, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"■ {self.name} 끝 · 프레임 {len(self.frames)} · 표시 {len(self.marks)}", flush=True)

    def mark(self, label, loc=None, kind="click"):
        box = None
        if loc is not None:
            try:
                b = loc.bounding_box()
                box = [round(b["x"]), round(b["y"]), round(b["width"]), round(b["height"])] if b else None
            except Exception:  # noqa: BLE001
                pass
        self.marks.append({"t": time.time(), "kind": kind, "label": label, "box": box})

    def wait(self, cond, label, limit=1800):
        """AI가 일하는 동안 — 프레임을 성기게, 끝나면 표시"""
        self.slow = True
        self.mark(label + " 시작", kind="wait")
        t0 = time.time()
        try:
            while time.time() - t0 < limit:
                try:
                    if cond():
                        break
                except Exception:  # noqa: BLE001
                    pass
                self.pg.wait_for_timeout(3000)
            else:
                raise TimeoutError(label)
        finally:
            self.slow = False
        self.mark(label + f" 끝 ({time.time() - t0:.0f}s)", kind="wait")
        print(f"  · {label} {time.time() - t0:.0f}s", flush=True)
        self.pg.wait_for_timeout(1200)


POS = {"x": VIEW["width"] / 2, "y": VIEW["height"] / 2}


def glide(pg, loc, pause=0.5, fx=0.5):
    loc.scroll_into_view_if_needed()
    b = loc.bounding_box()
    if b and b["y"] + b["height"] > VIEW["height"] - 200:  # 화면 맨 아래면 입력창에 가려 클릭이 빗나간다(11/3) — 가운데로
        loc.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'smooth'})")
        pg.wait_for_timeout(700)
        b = loc.bounding_box()
    x, y = b["x"] + b["width"] * fx, b["y"] + b["height"] / 2
    d = ((x - POS["x"]) ** 2 + (y - POS["y"]) ** 2) ** 0.5
    pg.mouse.move(x, y, steps=max(8, min(40, int(d / 18))))
    POS.update(x=x, y=y)
    pg.wait_for_timeout(int(pause * 1000))
    return x, y


def click(r, loc, label, pause=0.5, after=1.2, fx=0.5):
    loc = loc.first if hasattr(loc, "first") else loc
    loc.wait_for(state="visible", timeout=30000)
    glide(r.pg, loc, pause, fx)
    r.mark(label, loc)
    r.pg.mouse.down()
    r.pg.wait_for_timeout(90)
    r.pg.mouse.up()
    r.pg.wait_for_timeout(int(after * 1000))


def hover(r, loc, label, hold=1.6):
    loc = loc.first if hasattr(loc, "first") else loc
    loc.wait_for(state="visible", timeout=30000)
    glide(r.pg, loc, 0.3)
    r.mark(label, loc, "hover")
    r.pg.wait_for_timeout(int(hold * 1000))


def type_in(r, loc, text, label, send=True):
    click(r, loc, label, after=0.3)
    r.mark(label + " — 입력", loc, "type")
    r.pg.keyboard.type(text, delay=65)
    r.pg.wait_for_timeout(700)
    if send:
        r.pg.keyboard.press("Enter")
        r.pg.wait_for_timeout(1500)


def scroll(r, dy, steps=None, at=None, speed=650):
    """부드럽게 — 초당 speed px 안팎, 처음과 끝은 천천히(10/26 사용자: 휙휙 스크롤되면 어지럽다). steps는 예전 호출 호환용"""
    if at is not None:
        glide(r.pg, at, 0.2)
    dur = max(0.9, abs(dy) / speed)
    n = max(12, int(dur / 0.03))
    r.marks.append({"t": time.time(), "kind": "scroll", "label": f"스크롤 {dy:+d}", "box": None, "dur": dur})
    done = 0.0
    for i in range(1, n + 1):
        x = i / n
        target = dy * (x * x * (3 - 2 * x))
        r.pg.mouse.wheel(0, target - done)
        done = target
        r.pg.wait_for_timeout(int(dur / n * 1000))
    r.pg.wait_for_timeout(700)


def btn(pg, name, exact=False):
    return pg.get_by_role("button", name=name, exact=exact)


def chat(pg):
    return pg.locator("section div.overflow-y-auto").first  # 대화 칸(docs/readme/capture.py와 같은 기준)


def menu_link(pg, h):
    return pg.locator(f"div.mt-8 a[href='{h}']")  # 왼쪽 메뉴(아이콘만, 올리면 펼쳐짐)


def go(pg, h):
    pg.goto(BASE + "/" + h, wait_until="networkidle")
    pg.wait_for_timeout(1500)


# ---------- 챕터 ----------

def c1(pg):
    go(pg, "#/articles")
    with Rec(pg, "c1") as r:
        pg.wait_for_timeout(2500)
        for h, name in (("#/library", "서재"), ("#/topics", "주제 지도"), ("#/articles", "글"), ("#/publish", "발행")):
            hover(r, menu_link(pg, h), f"메뉴 {name}", 1.0)
        pg.wait_for_timeout(1500)


def c2(pg):
    go(pg, "#/articles")
    with Rec(pg, "c2") as r:
        click(r, menu_link(pg, "#/library"), "메뉴 서재", after=2.0)
        for name in ("컨설팅", "기업 자료", "연구기관", "경영일기", "전체", "저널·매체"):
            click(r, btn(pg, name), f"탭 {name}", after=1.4)  # 탭 이름 뒤에 편수가 붙어 있다(컨설팅 372)
        # 원문 하나를 열어 전문이 그대로 있는 것을 보인다(10/26 사용자) — 한글 제목 카드를 고른다
        scroll(r, 420)
        cards = pg.locator("div.relative.rounded-2xl").filter(has=pg.locator("div.cursor-pointer"))
        card = next((cards.nth(i) for i in range(min(cards.count(), 12)) if re.search(r"[가-힣]{6}", cards.nth(i).locator("div.font-semibold").first.inner_text())), cards.first)
        hover(r, card, "원문 카드", 1.4)
        click(r, card, "원문 열기", after=1.0)
        body = pg.locator("[data-vaul-drawer-direction=right] div.overflow-y-auto")
        body.wait_for(state="visible", timeout=15000)
        pg.wait_for_function("() => (document.querySelector('[data-vaul-drawer-direction=right] div.overflow-y-auto')?.innerText || '').length > 500", timeout=30000)
        hover(r, body.locator("h2, [id], div").first, "원문 전문 — 요약 없이 그대로", 2.0)
        scroll(r, 900, at=body)
        pg.wait_for_timeout(1200)
        scroll(r, 900)
        pg.wait_for_timeout(1500)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1200)
        scroll(r, -420)
        hover(r, btn(pg, "Supabase 받기"), "Supabase 받기 — 마지막 받은 시각", 2.5)
        click(r, btn(pg, "Supabase 받기"), "Supabase 받기")
        r.wait(lambda: not any(j["kind"] == "db-sync" and j["status"] == "running" for j in state()["jobs"]), "Supabase 받기", 900)
        hover(r, btn(pg, "aside 수집"), "aside 수집", 2.5)


def c3(pg):
    go(pg, "#/library")
    with Rec(pg, "c3") as r:
        click(r, menu_link(pg, "#/topics"), "메뉴 주제 지도", after=2.5)
        scroll(r, 420)
        for name in ("보통", "쓴 글", "쓸 만함"):
            click(r, btn(pg, name), f"탭 {name}", after=1.4)  # 탭 이름 뒤에 개수(쓸 만함 69)
        card = pg.locator("h3").first
        hover(r, card, "주제 카드 앞면 — 말할 것·사례", 2.0)
        click(r, card, "카드 펼치기", after=2.0)
        hover(r, btn(pg, "이 주제로").last, "이 주제로", 1.5)
        scroll(r, 500, 8, pg.locator("h3").last)
        scroll(r, 900, 8)
        hover(r, btn(pg, "보통", True).last, "판정 칸(쓸 만함·보통·뺌) — 바꾸면 예시로 쌓임", 2.5)  # 누르지 않는다
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1200)
        scroll(r, -1600)
        hover(r, btn(pg, "다시 거르기"), "다시 거르기", 2.0)
        if btn(pg, "주제 묶기").count():  # 새 카드가 있을 때만 보임
            hover(r, btn(pg, "주제 묶기"), "주제 묶기", 1.6)


def c4(pg):
    go(pg, "#/topics")
    with Rec(pg, "c4") as r:
        click(r, menu_link(pg, "#/articles"), "메뉴 글(메인)", after=2.5)
        if btn(pg, "다른 추천").count():
            hover(r, pg.get_by_text("다른 추천").locator("xpath=..").first, "추천 주제 넷", 1.5)
            click(r, btn(pg, "다른 추천"), "다른 추천", after=1.8)
        ta = pg.locator("textarea").last
        if DOC:
            pg.locator("input[type=file]").first.set_input_files(DOC)
            r.mark("문서 첨부", pg.locator("textarea").last, "type")
            pg.wait_for_timeout(1500)
        type_in(r, ta, REQUEST, "하고 싶은 말")
        t0 = time.time()
        while "#/a/" not in pg.url and time.time() - t0 < 30:
            pg.wait_for_timeout(500)
        k = pg.url.split("#/a/")[-1].split("/")[0]
        save(article=k)
        print(f"  · 시연 글 {k}", flush=True)
        r.wait(lambda: btn(pg, "이 글로").count() > 0 and not busy(k), "글 옵션", 900)
        if MORE:
            type_in(r, pg.locator("textarea").last, FOLLOW, "이어서 한 말")
            r.wait(lambda: btn(pg, "이 글로").count() > 0 and not busy(k) and pg.get_by_text("글 옵션").count() >= 2, "글 옵션 다시", 900)
        scroll(r, -2400, 8, chat(pg))
        live = pg.locator("div.rounded-2xl").filter(has=btn(pg, "이 글로"))
        n = live.count()
        for i in range(n):
            hover(r, live.nth(i).locator("p").first, f"옵션 {i + 1} — 이 글이 말할 것", 1.4)
        pick = next((i for i in range(n) if OPTION_KEY in live.nth(i).inner_text()), 0)
        save(option=pick + 1)
        click(r, live.nth(pick).get_by_role("button", name="이 글로"), f"이 글로 (옵션 {pick + 1})", after=1.5)


def c5(pg):
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c5") as r:
        r.wait(lambda: btn(pg, "이 원문으로 본문 쓰기").count() > 0 and not busy(k), "원문 끝까지 읽고 확인", 900)
        scroll(r, -900, 6, chat(pg))
        for name in ("중심", "받침"):
            if pg.get_by_text(name, exact=True).count():
                hover(r, pg.get_by_text(name, exact=True).last, f"{name} 원문", 1.4)
        for name in ("확인에서 뺀 원문", "추천 원문", "사내 맥락"):
            if pg.get_by_text(name, exact=True).count():
                hover(r, pg.get_by_text(name, exact=True).last, name, 1.8)
        rows = pg.locator("div.border-t").filter(has=btn(pg, "넣기"))
        rec = next((rows.nth(i) for i in range(rows.count()) if any(x in rows.nth(i).inner_text() for x in REC_KEYS) and "사내 맥락" not in rows.nth(i).inner_text()), None)
        if rec is not None:
            click(r, rec.get_by_role("button", name="넣기"), "추천 원문 넣기")
            r.wait(lambda: not busy(k), "추천 원문 끝까지 읽기", 600)
        click(r, btn(pg, "이 원문으로 본문 쓰기"), "이 원문으로 본문 쓰기", after=2.0)


def c5b(pg):
    """보충 — c5에서 추천 원문 목록이 화면 아래에 있어 못 보였다(10/26). 쓰기를 시작한 뒤라 넣기 버튼은 없고 목록만 보인다."""
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c5b") as r:
        more = pg.get_by_role("button", name="추천·바꿔 넣을 수 있는 원문")
        more.first.scroll_into_view_if_needed()
        pg.wait_for_timeout(800)
        scroll(r, 250, 5, more.first)
        for g in ("추천 원문", "확인에서 뺀 원문"):
            t = pg.locator("p", has_text=g)
            if t.count():
                hover(r, t.first, g, 2.0)
        rows = pg.locator("div.flex.gap-4.border-t")
        for i in range(rows.count()):
            if any(x in rows.nth(i).inner_text() for x in REC_KEYS):
                hover(r, rows.nth(i), "추천 원문 — " + rows.nth(i).inner_text()[:20], 2.2)
        scroll(r, 400, 6)
        pg.wait_for_timeout(1000)


def c6(pg):
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c6") as r:
        hover(r, pg.locator("div.rounded-2xl").filter(has=btn(pg, "쓰기", True)).locator("span").first, "대상 독자", 1.6)
        click(r, btn(pg, "쓰기", True), "쓰기", after=2.0)
        r.wait(lambda: len(art(k)["steps"]) >= 3 and not busy(k), "과정 1·2·3", 2400)
        click(r, pg.locator("button").filter(has_text="자").filter(has=pg.locator("p.line-clamp-3")).nth(1), "과정 2 카드", after=1.5)
        for name in ("본문", "비교", "미리보기"):
            click(r, btn(pg, name, True), f"지금 글 — {name}", after=2.2)
            if name == "비교" and pg.locator(".s-add").count():
                hover(r, pg.locator(".s-add").first, "바뀐 문장 형광", 2.0)
        n = len(art(k)["steps"])
        type_in(r, pg.locator("textarea").last, FEEDBACK, "피드백")
        r.wait(lambda: len(art(k)["steps"]) > n and not busy(k), f"피드백 → 과정 {n + 1}", 1200)
        click(r, btn(pg, "본문", True), "지금 글 — 본문", after=1.0)
        click(r, btn(pg, "편집", True), "편집", after=1.5)
        ed = pg.locator(".ProseMirror").first
        glide(pg, ed.locator("p").first, 0.3)
        r.mark("에디터에서 고치기", ed, "type")
        ed.locator("p").first.click()
        pg.keyboard.press("End")
        pg.wait_for_timeout(400)
        pg.keyboard.type(" ", delay=80)
        pg.keyboard.press("Backspace")  # 글은 그대로 두고 편집 → 저장 흐름만 보인다
        pg.wait_for_timeout(600)
        click(r, btn(pg, "저장", True), "저장 → 새 과정", after=2.5)
        click(r, pg.locator("button").filter(has=pg.locator("p.line-clamp-3")).nth(1), "앞 과정 보기", after=1.2)
        for name in ("여기서 이어 쓰기", "사내 맥락 넣어 고쳐 쓰기", "처음부터 다시 쓰기"):
            if btn(pg, name).count():
                hover(r, btn(pg, name), name, 1.6)


def c7(pg):
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c7") as r:
        a = art(k)
        n = a["steps"][-1]["n"]
        click(r, btn(pg, f"과정 {n}", True).last, f"원고로 고를 과정 {n}", after=1.0)
        click(r, pg.get_by_role("button", name="원고 정하기").last, "원고 정하기", after=2.0)
        if btn(pg, "제목 짓기").count():
            click(r, btn(pg, "제목 짓기"), "제목 짓기")
        r.wait(lambda: art(k)["titles"] and not busy(k), "제목 후보", 900)
        t = art(k)["titles"][-1]["items"][0]
        click(r, pg.get_by_role("button").filter(has_text=t).last, "제목 고르기", after=2.0)
        # 한 글에 일은 하나씩 — 머리 그림이 도는 동안 누른 본문 그림은 시작되지 않는다(11/3 녹화에서 50분 멈춤)
        click(r, btn(pg, "머리 그림"), "머리 그림 그리기", after=1.0)
        r.wait(lambda: art(k)["images"] and not busy(k), "머리 그림 그리기", 1800)
        pictures(r, pg, k)


def c7b(pg):
    """c7이 머리 그림까지 그리고 멈췄을 때 — 본문 그림부터 이어 찍는다(편집에서 c7 뒤에 붙인다)"""
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c7b") as r:
        pictures(r, pg, k)


def pictures(r, pg, k):
    """본문 그림 그리기 → 머리 그림·본문 그림 고르기 → 점검 → 확정"""
    if not art(k)["inline"]:
        click(r, btn(pg, "본문 그림"), "본문 그림 그리기", after=1.0)
        r.wait(lambda: art(k)["inline"] and not busy(k), "본문 그림 그리기", 1800)
    hero = pg.locator("div.grid-cols-4").first.locator("button")
    click(r, hero.first, "머리 그림 고르기", after=1.2)
    inline = pg.locator("div.grid-cols-4").last.locator("button")
    for i in range(min(2, inline.count())):
        hover(r, inline.nth(i), f"본문 그림 {i + 1} — 문단·고른 이유", 2.0)
        click(r, inline.nth(i), f"본문 그림 {i + 1} 고르기", after=1.0)
    click(r, btn(pg, "그림 정함 · 확정으로"), "그림 정함 · 확정으로", after=2.0)
    chk = pg.get_by_text("수치", exact=False).last
    if chk.count():
        hover(r, chk, "수치·용어 점검", 2.5)
    click(r, pg.get_by_role("button", name="확정").last, "확정", after=3.0)
    hover(r, pg.get_by_text("확정됨").last, "확정됨", 1.5)


def c8(pg):
    if not TO:
        sys.exit("c8은 --to <받는 사람>이 있어야 합니다")
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "c8") as r:
        click(r, menu_link(pg, "#/publish"), "메뉴 발행", after=2.0)
        if "#/publish" not in pg.url:  # 사이드바가 펼쳐지는 중에 누르면 안 넘어갈 때가 있다(10/26)
            click(r, menu_link(pg, "#/publish"), "메뉴 발행", after=2.0)
        # 발행 화면의 글 목록은 왼쪽 메뉴 띠(60px)와 겹친다 — 커서를 빼서 메뉴를 접고, 항목의 오른쪽을 누른다(10/26)
        glide(pg, pg.locator("main h2, main h1").last, 0.8)
        click(r, pg.locator("aside.w-80 button").filter(has_text=art(k)["title"][:10]), "확정한 글 고르기", after=1.0, fx=0.8)
        r.wait(lambda: pg.locator("iframe[title='미리보기']").count() > 0, "발행본 만들기", 600)
        pg.wait_for_timeout(2500)
        click(r, btn(pg, "메일", True), "메일 미리보기", after=3.0)
        click(r, btn(pg, "웹", True), "웹 미리보기", after=3.0)
        type_in(r, pg.locator("textarea").first, TO, "받는 사람", send=False)
        b = pg.locator("button").filter(has_text="발행").last
        click(r, b, "발행", after=1.2)
        click(r, b, "한 번 더 누르면 발행", after=2.0)
        r.wait(lambda: (art(k) or {}).get("published") and not busy(k), "캡처 · 메일 · 커밋·푸시", 1800)
        pg.wait_for_timeout(2000)
        save(published=True)


def c8mail(pg):
    """보충(10/26 사용자: 메일 모양을 더 길게) — 발행 화면에서 메일 미리보기를 끝까지 천천히 내린다. 발행 버튼은 누르지 않는다"""
    k = saved()["article"]
    go(pg, f"#/publish/{k}")
    pg.locator("iframe[title='미리보기']").wait_for(timeout=120000)
    pg.wait_for_timeout(1500)
    with Rec(pg, "c8mail") as r:
        click(r, btn(pg, "메일", True), "메일 미리보기", after=2.5)
        frame = pg.locator("iframe[title='미리보기']")
        hover(r, frame, "메일 — 그대로 보낼 이미지 메일", 1.5)
        for _ in range(5):
            scroll(r, 450, at=frame, speed=380)
            pg.wait_for_timeout(1100)
        pg.wait_for_timeout(1500)


def c8web(pg):
    """배포된 웹 칼럼 — --web-base가 있으면 그 주소(로컬 사본)로. 시연 글을 웹에서 내린 뒤라(10/26) 사이트 사본을 로컬에서 띄워 찍는다(파일은 배포본과 같음)"""
    cfg = json.loads((ROOT / "config" / "publish.json").read_text(encoding="utf-8"))
    base = (opt("--web-base") or cfg["web_base_url"]).rstrip("/") + "/" + cfg.get("web_path_token", "")
    k = saved()["article"]
    url = f"{base}/"
    print(f"  · 웹 {url}", flush=True)
    pg.goto(url, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    with Rec(pg, "c8web") as r:
        pg.wait_for_timeout(1800)
        link = pg.locator(f"a[href*='{k}']").first
        hover(r, link, "아카이브의 발행된 칼럼", 2.2)
        click(r, link, "칼럼 열기", after=2.5)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(1500)
        for _ in range(7):
            scroll(r, 520, speed=420)
            pg.wait_for_timeout(1300)
        pg.wait_for_timeout(1500)


# ---------- 2차 심사판(11/3) ----------

def s2(pg):
    """2장 둘러보기 — 메뉴 넷 → 서재 탭·원문 전문 → 주제 탭·카드 → 글·발행 목록. 아무것도 바꾸지 않는다(Supabase 받기도 마우스만)"""
    go(pg, "#/articles")
    with Rec(pg, "s2") as r:
        pg.wait_for_timeout(1500)
        for h, name in (("#/library", "서재"), ("#/topics", "주제"), ("#/articles", "글"), ("#/publish", "발행")):
            hover(r, menu_link(pg, h), f"메뉴 {name}", 0.9)
        click(r, menu_link(pg, "#/library"), "메뉴 서재", after=1.8)
        for name in ("컨설팅", "저널·매체", "기업 자료", "연구기관", "전체"):
            if btn(pg, name).count():
                click(r, btn(pg, name), f"탭 {name}", after=1.0)
        scroll(r, 420)
        cards = pg.locator("div.relative.rounded-2xl").filter(has=pg.locator("div.cursor-pointer"))
        card = next((cards.nth(i) for i in range(min(cards.count(), 12)) if re.search(r"[가-힣]{6}", cards.nth(i).locator("div.font-semibold").first.inner_text())), cards.first)
        click(r, card, "원문 열기", after=1.0)
        body = pg.locator("[data-vaul-drawer-direction=right] div.overflow-y-auto")
        body.wait_for(state="visible", timeout=15000)
        pg.wait_for_function("() => (document.querySelector('[data-vaul-drawer-direction=right] div.overflow-y-auto')?.innerText || '').length > 500", timeout=30000)
        hover(r, body.locator("h2, [id], div").first, "원문 전문", 1.5)
        scroll(r, 900, at=body)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1000)
        scroll(r, -420)
        hover(r, btn(pg, "aside 수집"), "aside 수집 — RSS 없는 사이트", 4.0)  # 11/9 사용자: 수집을 설명한다
        hover(r, btn(pg, "Supabase 받기"), "Supabase 받기 — 6시간마다 자동", 4.0)
        click(r, menu_link(pg, "#/topics"), "메뉴 주제", after=2.0)
        scroll(r, 420)
        for name in ("보통", "뺌", "쓴 글", "쓸 만함"):
            if btn(pg, name).count():
                click(r, btn(pg, name), f"탭 {name}", after=1.0)
        card = pg.locator("h3").first
        click(r, card, "주제 카드 펼치기", after=1.8)
        scroll(r, 500, at=pg.locator("h3").last)
        hover(r, btn(pg, "보통", True).last, "판정 칸 — 바꾸면 다음 거르기의 기준", 2.0)  # 누르지 않는다
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1000)
        click(r, menu_link(pg, "#/articles"), "메뉴 글", after=1.5)
        hover(r, pg.locator("textarea").last, "메인 — 어떤 글을 쓸까요?", 1.2)
        click(r, menu_link(pg, "#/publish"), "메뉴 발행", after=2.0)
        pg.wait_for_timeout(1000)


def s3(pg):
    """3장 글쓰기 A — 추천 주제 → (자동) 원문 끝까지 확인·사내 맥락 → 본문 쓰기 → 쓰기 → 과정 1·2·3 → 비교.
    11/3 리허설: 원문 확인 약 2분, 쓰기 약 2분 30초. 글 옵션 단계는 없다."""
    # 고를 주제가 추천 목록에 있는지 먼저 본다(없으면 다른 추천을 끝없이 넘김)
    tp = [x for x in state()["wiki"]["topics"] if x["verdict"] == "쓸 만함" and x["status"] == "쓸 수 있음" and PICK_KEY in x["title"]]
    if not tp:
        sys.exit(f"추천 주제에 '{PICK_KEY}'가 없습니다 — PICK_KEY를 바꿀 것")
    go(pg, "#/articles")
    with Rec(pg, "s3") as r:
        # 11/9 사용자: A안은 메인 추천 카드가 아니라 주제 탭에서 '이 주제로'를 누른다
        click(r, menu_link(pg, "#/topics"), "메뉴 주제", after=2.0)
        click(r, btn(pg, "쓸 만함"), "탭 쓸 만함", after=1.5)
        card = pg.locator("h3").filter(has_text=PICK_KEY)
        hover(r, pg.locator("h3").first, "추천 주제 카드", 1.2)
        hover(r, card, "추천 주제 카드 — 고를 주제", 1.8)
        click(r, card, "주제 펼치기", after=2.0)
        hover(r, btn(pg, "이 주제로").last, "이 주제로 — 버튼", 1.8)
        click(r, btn(pg, "이 주제로").last, "이 주제로 쓰기", after=2.0)
        t0 = time.time()
        while "#/a/" not in pg.url and time.time() - t0 < 30:
            pg.wait_for_timeout(500)
        k = pg.url.split("#/a/")[-1].split("/")[0]
        save(article_a=k)
        print(f"  · 글 A {k}", flush=True)
        hover(r, pg.get_by_text("주제 지도에서 고른 주제").first, "주제 카드 — 사람 판정·중심·받침", 2.0)
        r.wait(lambda: btn(pg, "이 원문으로 본문 쓰기").count() > 0 and not busy(k), "원문 끝까지 읽고 확인", 900)
        for name in ("중심", "받침", "사내 맥락", "추천 원문"):
            t = pg.get_by_text(name, exact=True)
            if t.count():
                hover(r, t.last, name, 1.6)
        for _ in range(3):  # 화면이 움직이는 중이면 한 번에 안 눌릴 때가 있다(11/3 재녹화)
            click(r, btn(pg, "이 원문으로 본문 쓰기"), "이 원문으로 본문 쓰기", after=1.5)
            pg.wait_for_timeout(3000)
            if btn(pg, "쓰기", True).count():
                break
        hover(r, pg.locator("div.rounded-2xl").filter(has=btn(pg, "쓰기", True)).locator("span").first, "대상 독자", 1.2)
        click(r, btn(pg, "쓰기", True), "쓰기", after=2.0)
        r.wait(lambda: len(art(k)["steps"]) >= 3 and not busy(k), "과정 1·2·3", 1800)
        click(r, pg.locator("button").filter(has_text="자").filter(has=pg.locator("p.line-clamp-3")).nth(1), "과정 2 카드", after=1.2)
        click(r, btn(pg, "비교", True), "지금 글 — 비교", after=1.5)
        if pg.locator(".s-add").count():
            hover(r, pg.locator(".s-add").first, "바뀐 문장 형광", 2.0)


def s4(pg):
    """4장 글쓰기 B의 쓰기 — c4(요청·글 옵션) · c5(원문 확인 → 이 원문으로 본문 쓰기) 다음. 편집에서 압축하므로 쓰기와 기다림만"""
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "s4") as r:
        click(r, btn(pg, "쓰기", True), "쓰기", after=2.0)
        r.wait(lambda: len(art(k)["steps"]) >= 3 and not busy(k), "과정 1·2·3", 1800)
        hover(r, pg.locator("button").filter(has=pg.locator("p.line-clamp-3")).last, "과정 3", 1.5)


def s5(pg):
    """5장 앞 — 글 B에 문체 피드백 → 과정 4 → 비교(고친 문장) · 짚지 않은 문단 표시. 원고·제목·그림·확정은 c7을 그대로"""
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "s5") as r:
        n = len(art(k)["steps"])
        type_in(r, pg.locator("textarea").last, STYLE_FEEDBACK, "문체 피드백")
        r.wait(lambda: len(art(k)["steps"]) > n and not busy(k), f"피드백 → 과정 {n + 1}", 1200)
        click(r, btn(pg, "비교", True), "지금 글 — 비교", after=1.5)
        if pg.locator(".s-add").count():
            hover(r, pg.locator(".s-add").first, "피드백으로 고친 문장", 2.2)
        stray = pg.get_by_text("짚지 않은 문단", exact=False)
        if stray.count():
            hover(r, stray.first, "짚지 않은 문단 바뀜", 1.8)


def s5r(pg):
    """5장 핵심 — c7의 확정 뒤 규칙 후보 → 근거(피드백·전→후) → 규칙에 넣기 → 규칙 파일에 더해진 한 줄.
    넣은 줄은 촬영 뒤 briefs/글쓰기규칙.md에서 지우고 공유한다."""
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "s5r") as r:
        r.wait(lambda: (art(k).get("ruleCands") or {}).get("items") and not busy(k), "규칙 후보 찾기", 900)
        pg.wait_for_timeout(1500)
        intro = pg.get_by_text("다음 글에도 지킬 만한 것을 골랐습니다", exact=False).first
        hover(r, intro, "규칙 후보 — 이 글의 피드백에서", 2.0)
        items = art(k)["ruleCands"]["items"]
        rows = pg.locator("div.rounded-xl").filter(has=btn(pg, "규칙에 넣기"))
        if not rows.count():
            print("  · 새 규칙 후보가 없음 — 피드백 문장을 바꿔 다시 찍을 것", flush=True)
            return
        row = rows.first
        hover(r, row.locator("p").first, "새 규칙 후보", 2.2)
        q = row.get_by_text("피드백 ·", exact=False)
        if q.count():
            hover(r, q.first, "받은 피드백", 2.0)
        for tag, label in (("전", "고치기 전 문장"), ("후", "고친 뒤 문장")):
            t = row.locator("span", has_text=re.compile(f"^{tag}$"))
            if t.count():
                hover(r, t.first.locator("xpath=.."), label, 1.8)
        for kind in ("이 글만", "이미 있음"):
            other = pg.locator("div.rounded-xl").filter(has=pg.get_by_text(kind, exact=True))
            if other.count():
                hover(r, other.first, f"후보 종류 — {kind}", 1.6)
        before = {i for i, it in enumerate(items) if it.get("state")}
        click(r, row.get_by_role("button", name="규칙에 넣기"), "규칙에 넣기", after=1.5)
        r.wait(lambda: any((it.get("state") or {}).get("d") == "넣기" and i not in before for i, it in enumerate(art(k)["ruleCands"]["items"])), "규칙 파일에 넣기", 300)
        hover(r, pg.get_by_text("규칙에 넣음", exact=False).first, "규칙에 넣음", 2.0)
        text = next(it["state"]["text"] for i, it in enumerate(art(k)["ruleCands"]["items"]) if (it.get("state") or {}).get("d") == "넣기" and i not in before)
        save(rule_added=text)
        page = rules_page(text)
        pg.goto(page.as_uri(), wait_until="load")
        pg.wait_for_timeout(1200)
        hit = pg.locator("li.new")
        if hit.count():
            hit.first.scroll_into_view_if_needed()
            hover(r, hit.first, "글쓰기 규칙 파일에 더해진 한 줄", 3.0)
        pg.wait_for_timeout(1500)


def s6(pg):
    """6장 발행 — 메일 발송은 찍을 수 없어(Outlook은 VDI 안) 웹·메일 미리보기를 천천히 보여 주고, 발행 뒤 메일 파일(.eml)을 받는 데까지(11/3 사용자).
    실제로 발행된다(웹 배포 · .eml) — 촬영 뒤 unpublish."""
    if not TO:
        sys.exit("s6은 --to <받는 사람>이 있어야 합니다")
    k = saved()["article"]
    go(pg, f"#/a/{k}")
    with Rec(pg, "s6") as r:
        click(r, menu_link(pg, "#/publish"), "메뉴 발행", after=2.0)
        if "#/publish" not in pg.url:
            click(r, menu_link(pg, "#/publish"), "메뉴 발행", after=2.0)
        glide(pg, pg.locator("main h2, main h1").last, 0.8)
        click(r, pg.locator("aside.w-80 button").filter(has_text=art(k)["title"][:10]), "확정한 글 고르기", after=1.0, fx=0.8)
        r.wait(lambda: pg.locator("iframe[title='미리보기']").count() > 0, "발행본 만들기", 600)
        pg.wait_for_timeout(2500)
        frame = pg.locator("iframe[title='미리보기']")
        hover(r, frame, "웹 미리보기 — 아카이브에 올라갈 칼럼", 1.5)
        for _ in range(4):
            scroll(r, 480, at=frame, speed=420)
            pg.wait_for_timeout(900)
        click(r, btn(pg, "메일", True), "메일 미리보기", after=2.5)
        frame = pg.locator("iframe[title='미리보기']")
        hover(r, frame, "메일 미리보기 — 그대로 보낼 이미지 메일", 1.5)
        for _ in range(4):
            scroll(r, 450, at=frame, speed=380)
            pg.wait_for_timeout(900)
        type_in(r, pg.locator("textarea").first, TO, "받는 사람", send=False)
        b = pg.locator("button").filter(has_text="발행").last
        click(r, b, "발행", after=1.2)
        click(r, b, "한 번 더 누르면 발행", after=2.0)
        r.wait(lambda: (art(k) or {}).get("published") and not busy(k), "캡처 · 메일 · 커밋·푸시", 1800)
        pg.wait_for_timeout(2000)
        save(published=True)
        done = pg.locator("div.border-emerald-400\\/30")
        if done.count():
            hover(r, done.first, "발행 완료 — 웹 주소", 2.0)
        eml = pg.get_by_role("link", name="메일 파일(.eml)")
        glide(pg, eml, 0.6)
        r.mark("메일 파일(.eml) 받기", eml)
        with pg.expect_download() as dl:
            pg.mouse.down()
            pg.wait_for_timeout(90)
            pg.mouse.up()
        f = OUT / dl.value.suggested_filename
        dl.value.save_as(f)
        r.mark(f"받음 · {f.name}", eml, "download")
        print(f"  · .eml {f}", flush=True)
        pg.wait_for_timeout(2500)


def rules_page(added):
    """briefs/글쓰기규칙.md를 작업실과 같은 어두운 화면으로 — 방금 넣은 줄만 형광. 파일 내용 그대로(꾸미지 않음)"""
    import html
    md = (ROOT / "briefs" / "글쓰기규칙.md").read_text(encoding="utf-8").splitlines()
    out, in_list = [], False
    for ln in md:
        if ln.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            new = added.strip()[:30] in ln
            out.append(f"<li class='{'new' if new else ''}'>{html.escape(ln[2:])}</li>")
            continue
        if in_list and not ln.startswith("  "):
            out.append("</ul>")
            in_list = False
        if ln.startswith("## "):
            out.append(f"<h2>{html.escape(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{html.escape(ln[2:])}</h1><p class='path'>briefs/글쓰기규칙.md</p>")
        elif ln.strip():
            out.append(f"<p>{html.escape(ln.strip())}</p>")
    if in_list:
        out.append("</ul>")
    css = ("body{background:#0b0b0f;color:#e7e7ea;font:18px/1.75 Pretendard,'Malgun Gothic',sans-serif;max-width:1100px;margin:60px auto;padding:0 40px}"
           "h1{font-size:34px;margin:0}h2{font-size:22px;margin:36px 0 8px;color:#c4b5fd}.path{color:#888;font-size:14px;margin:4px 0 24px}"
           "p{color:#aaa;font-size:15px}li{margin:6px 0}li.new{background:rgba(167,139,250,.22);border-radius:6px;padding:4px 8px;color:#fff}")
    f = OUT / "rules.html"
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_text(f"<!doctype html><meta charset='utf-8'><style>{css}</style>{''.join(out)}", encoding="utf-8")
    return f


# ---------- mp4 ----------

def build(names):
    import imageio_ffmpeg  # pip install imageio-ffmpeg — ffmpeg 실행 파일이 들어 있다
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    for name in names:
        d = OUT / name
        fr = json.loads((d / "frames.json").read_text(encoding="utf-8"))
        if not fr:
            print(f"{name}: 프레임 없음")
            continue
        lines = []
        for (f, t), nxt in zip(fr, fr[1:] + [[None, fr[-1][1] + 1.5]]):
            lines += [f"file 'frames/{f}'", f"duration {max(0.001, nxt[1] - t):.4f}"]
        lines.append(f"file 'frames/{fr[-1][0]}'")
        (d / "list.txt").write_text("\n".join(lines), encoding="utf-8")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-r", "30", "-vf", "format=yuv420p",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", f"{name}.mp4"], cwd=d, check=True)
        t0 = fr[0][1]
        marks = json.loads((d / "marks.json").read_text(encoding="utf-8"))
        (d / "marks-sec.json").write_text(json.dumps([{**m, "sec": round(m["t"] - t0, 2)} for m in marks], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}.mp4 · {fr[-1][1] - t0:.0f}초 · 표시 {len(marks)} → {d}")


def main():
    if "build" in args:
        return build([a for a in args if a in CHAPTERS] or [c for c in CHAPTERS if (OUT / c / "frames.json").exists()])
    names = [a for a in args if a in CHAPTERS] or (CHAPTERS_R2 if R2 else CHAPTERS[:11])
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel=opt("--channel", "msedge"))  # 설치된 Edge — playwright 브라우저를 따로 받지 않는다
        ctx = b.new_context(viewport=VIEW, color_scheme="dark", locale="ko-KR")
        ctx.add_init_script(CURSOR_JS)
        pg = ctx.new_page()
        for name in names:
            globals()[name](pg)
        b.close()


if __name__ == "__main__":
    main()
