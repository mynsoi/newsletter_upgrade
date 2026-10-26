"""글 공유(2026-10-26 사용자 결정 — 여러 사용자가 쓰는 중·확정한 글을 git으로 주고받는다. 저장소가 Public이라 올린 글은 공개된다).

운영 브랜치(mentor-lab-integration)에 글이 바뀔 때마다 올리고(push), 주기적으로 받는다(pull). 나중에 Supabase로 옮길 수 있게 글마다 폴더·파일 구조는 그대로 둔다.
  공유: 글 설정 briefs/<글>.json · 원문 확인 기록 runs/mine/<글>/ 맨 위 파일(대화·옵션·고른 원문·사내 맥락 추천 internal.json)
        · 원고 과정 runs/columns/<글>/ 맨 위 파일과 inbox/(초안·재작성·기준 반영·피드백·편집·style.json) · 제목 후보 runs/titles0/<글>/ 맨 위 파일
        · 확정 원고 columns/*-<글>*.md · columns/img/*-<글>* · 고른 그림(runs/images 중 글 설정이 가리키는 것만 — git add -f)
        · 대화 runs/studio/chat/<글>.jsonl · 작업 기록 runs/studio/activity/<git 사용자>.jsonl
  안 함(.gitignore): 단계별 지시문·로그 하위 폴더(원문 전문·경영일기 전문), 제목 지시문, 그림 후보 전부, 실행 중 작업 목록·로그(PC마다 다름)
작업 중 표시: runs/columns/<글>/lock.json(누가·무엇·언제). 다른 사용자가 작업 중이면 작업실이 그 글의 작업을 막는다(LOCK_HOURS 지나면 무시).
"""
import json
import re
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_HOURS = 2
PULL_EVERY = 90       # 초 — 다른 사용자의 변경을 받아 오는 간격
DEBOUNCE = 3          # 초 — 같은 글의 잇단 변경을 한 커밋으로
GIT = threading.Lock()  # 이 서버 안의 git 작업은 한 번에 하나(pull과 커밋이 겹치지 않게)
_pending, _plock = {}, threading.Lock()
_user = None


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def user():
    """'누가' — git 사용자 이름(2026-10-26 사용자 결정)."""
    global _user
    if _user is None:
        _user = git("config", "user.name").stdout.strip() or "알 수 없음"
    return _user


def is_article(k):
    return bool(k) and re.fullmatch(r"[A-Za-z0-9가-힣._-]+", k) and (
        (ROOT / "briefs" / f"{k}.json").exists() or (ROOT / "runs" / "mine" / k).is_dir() or git("ls-files", f"briefs/{k}.json").stdout.strip())


def _images(k):
    """글 설정이 가리키는 그림(머리·본문으로 고른 것) — runs/images는 후보까지 커서 고른 것만 올린다."""
    try:
        b = json.loads((ROOT / "briefs" / f"{k}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = re.findall(r'"(runs/images/[^"]+\.(?:png|jpg|jpeg|webp))"', json.dumps(b, ensure_ascii=False))
    return [p for p in dict.fromkeys(found) if (ROOT / p).is_file()]


def _paths(k):
    if k == "_activity":  # 글이 아닌 작업(수집·묶기 등)의 기록만
        return [p for p in [f"runs/studio/activity/{user()}.jsonl"] if (ROOT / p).exists()]
    cands = [f"briefs/{k}.json", f"runs/mine/{k}", f"runs/columns/{k}", f"runs/titles0/{k}", f"runs/studio/chat/{k}.jsonl",
             f"runs/studio/activity/{user()}.jsonl"]
    cands += [p.relative_to(ROOT).as_posix() for p in (ROOT / "runs" / "columns").glob(f"{k}.try-*")]
    cands += [p.relative_to(ROOT).as_posix() for p in (ROOT / "columns").glob(f"*-{k}*") if p.is_file()]
    cands += [p.relative_to(ROOT).as_posix() for p in (ROOT / "columns" / "img").glob(f"*-{k}*")]
    # 있거나(새로·바뀜) 이미 올라가 있던(지움) 경로만 — 없는 경로를 git add에 주면 실패한다
    return [p for p in dict.fromkeys(cands) if (ROOT / p).exists() or git("ls-files", "--", p).stdout.strip()]


def sync(k, msg):
    """글 k의 공유 파일만 커밋해 올린다. 바뀐 게 없으면 아무것도 안 한다."""
    import wiki as W
    with GIT:
        paths = _paths(k)
        if paths:
            git("add", "-A", "--", *paths)
        imgs = _images(k)
        if imgs:
            git("add", "-f", "--", *imgs)
        if not git("diff", "--cached", "--name-only").stdout.strip():
            return False
        r = git("commit", "-q", "-m", f"{msg} ({user()})")
        if r.returncode:
            print(f"글 공유 커밋 실패 {k}: {(r.stderr or r.stdout).strip()[:200]}", flush=True)
            return False
        return W.push()


def schedule(k, msg):
    """글이 바뀌었다 — DEBOUNCE초 안의 잇단 변경은 한 커밋으로."""
    if k != "_activity" and not is_article(k):
        return
    with _plock:
        _pending[k] = (msg, time.time())


def _worker():
    while True:
        time.sleep(1)
        with _plock:
            due = [(k, m) for k, (m, t) in _pending.items() if time.time() - t >= DEBOUNCE]
            for k, _ in due:
                _pending.pop(k, None)
        for k, m in due:
            try:
                sync(k, m)
            except Exception as e:  # noqa: BLE001 — 공유 실패가 작업실을 멈추지 않게
                print(f"글 공유 실패 {k}: {e}", flush=True)


# ---------- 작업 중 표시 · 작업 기록 ----------
def lock_path(k):
    return ROOT / "runs" / "columns" / k / "lock.json"


def locked_by_other(k):
    """다른 사용자가 이 글에서 작업 중이면 {"user", "kind", "at"} — 아니면 None."""
    f = lock_path(k)
    try:
        x = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if x.get("user") == user() or time.time() - float(x.get("at", 0)) > LOCK_HOURS * 3600:
        return None
    return x


def lock(k, kind):
    if not is_article(k):
        return
    f = lock_path(k)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"user": user(), "kind": kind, "at": time.time()}, ensure_ascii=False), encoding="utf-8")
    schedule(k, f"글 {k}: {kind} 시작")


def unlock(k):
    f = lock_path(k)
    try:
        if json.loads(f.read_text(encoding="utf-8")).get("user") == user():
            f.unlink()
    except (OSError, ValueError):
        pass


def record(job):
    """작업 기록 한 줄 — 사용자마다 파일이 따로라 여러 PC가 동시에 써도 부딪치지 않는다."""
    f = ROOT / "runs" / "studio" / "activity" / f"{user()}.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": round(job.get("ended") or time.time()), "user": user(), "article": job.get("target"), "kind": job.get("kind"),
           "status": job.get("status"), "secs": round((job.get("ended") or time.time()) - job.get("started", time.time()))}
    with open(f, "a", encoding="utf-8") as out:
        out.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------- 받아 오기 ----------
def pull(busy=lambda: False):
    """다른 사용자의 변경을 받는다 — 이 PC에서 작업이 도는 중이면 건너뛴다(쓰는 중인 파일이 바뀌지 않게)."""
    if busy():
        return False
    with GIT:
        branch = git("branch", "--show-current").stdout.strip()
        r = git("pull", "-q", "--rebase", "--autostash", "origin", branch)
        if r.returncode:
            git("rebase", "--abort")
            print(f"받아 오기 실패: {(r.stderr or r.stdout).strip()[:200]}", flush=True)
            return False
    return True


def start(busy):
    """서버가 뜰 때 — 한 번 받고, 올리기 일꾼과 주기적 받기를 띄운다."""
    pull(busy)
    threading.Thread(target=_worker, daemon=True).start()

    def loop():
        while True:
            time.sleep(PULL_EVERY)
            try:
                pull(busy)
            except Exception as e:  # noqa: BLE001
                print(f"받아 오기 실패: {e}", flush=True)
    threading.Thread(target=loop, daemon=True).start()
