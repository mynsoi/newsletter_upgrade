"""astra(codex) 사용 한도 알아보기 (2026-11-24).

한도에 걸리면 codex는 오류로 끝나지 않고 빈 답만 남긴다. 실행 로그에는
"ERROR: You've hit your usage limit. ... try again at 3:09 PM." 한 줄이 있지만 화면에는 "결과가 비었음 — 다시 실행해 주세요"만
보여, 풀릴 때까지 다시 눌러도 같은 실패가 되풀이됐다(2026-11-24 고치기 두 번).

report(로그)는 한도 줄을 찾으면 MARK로 시작하는 안내 한 줄을 출력하고 돌려준다. 작업실 서버는 실패한 작업의 로그에서
MARK 줄을 찾아 맨 끝에 다시 적는다 — 화면의 실패 알림은 로그의 마지막 줄을 보여 주기 때문이다(studio_server.limit_note).
"""
import re
from pathlib import Path

MARK = "astra 사용 한도에 걸렸습니다"
LIMIT_RE = re.compile(r"hit your usage limit", re.I)
AGAIN_RE = re.compile(r"try again (?:at|in|on|after) ([^\n]*?)\.?\s*$", re.I | re.M)
CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*([AP])M$", re.I)


def when(text):
    """codex가 알려 준 '다시 되는 때'를 그대로(시각만 있으면 '오후 3:09'로). 없으면 빈 문자열."""
    hits = [m.group(1).strip() for m in AGAIN_RE.finditer(text) if LIMIT_RE.search(text[max(0, m.start() - 400):m.start()])]
    if not hits:
        return ""
    w = hits[-1]
    m = CLOCK_RE.match(w)
    return f"{'오전' if m.group(3).upper() == 'A' else '오후'} {int(m.group(1))}:{m.group(2)}" if m else w


def reason(log):
    """실행 로그에 한도 줄이 있으면 화면에 보일 안내 한 줄, 없으면 빈 문자열."""
    try:
        text = Path(log).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not LIMIT_RE.search(text):
        return ""
    w = when(text)
    return f"{MARK} — " + (f"{w} 이후에 다시 실행해 주세요" if w else "잠시 뒤 다시 실행해 주세요") + " (그때까지 고치기·제목·그림·주제 묶기가 모두 안 됩니다)"


def report(log):
    """한도에 걸렸으면 안내를 출력하고 돌려준다 — astra를 부른 직후에 부른다."""
    r = reason(log)
    if r:
        print(r, flush=True)
    return r
