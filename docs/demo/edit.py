"""시연 영상 편집 1차본 — record.py가 찍은 프레임·표시(marks)로 컷·빨리 감기·확대·강조·라벨·AI 배지·챕터 카드를 입혀 mp4로 (10/26)

사용: py -3 -X utf8 -I docs/demo/edit.py [--only 4,5] [--out 이름] [--audio 음성 폴더]
  --only  그 챕터만(시험용)
  --audio 타입캐스트 음성 — 챕터마다 <n>.mp3 하나(문장 사이 쉼으로 자막을 나눔) 또는 문장마다 <n>-1.mp3, <n>-2.mp3 …
          챕터 길이를 음성에 맞추고, 소리를 -16 LUFS로 맞춰 입힌다. 파일이 없는 챕터는 글자 수로 추정.
나오는 곳: _workspace/demo/edit/<이름>.mp4 · .srt(자막) · -narration.md(대본·시각·TTS 글) · -tts.txt(챕터별 TTS 입력)
- AI가 일하는 구간(marks의 'X 시작'~'X 끝')은 2.5~6초로 빨리 감고 '▶▶ ×N · 실제 M분 S초'와 일하는 AI 배지를 띄운다.
- 표시 사이가 6초 넘게 비면 가운데를 4배로(c8web 제외 — 웹 칼럼 스크롤이 볼거리).
- 클릭·마우스 올림·입력 지점을 1.2~1.6배로 당겨 보여 주고, 테두리·라벨(CALLOUT에 있는 것만)을 그린다.
- 챕터 길이는 내레이션(docs/demo/narration.json, 초당 5.5자)보다 짧으면 빨리 감기를 늦추고, 그래도 모자라면 마지막 화면을 멈춰 늘린다.
"""
import bisect
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "_workspace" / "demo"
OUTDIR = REC / "edit"
NARR = json.loads((Path(__file__).parent / "narration.json").read_text(encoding="utf-8"))
W, H, FPS = 1920, 1080, 30
CPS = 5.5  # 내레이션 빠르기 — 공백 뺀 글자/초
args = sys.argv[1:]
ONLY = {int(x) for x in args[args.index("--only") + 1].split(",")} if "--only" in args else None
NAME = args[args.index("--out") + 1] if "--out" in args else "rough-v1"
AUDIO = Path(args[args.index("--audio") + 1]) if "--audio" in args else None  # 타입캐스트 음성 폴더 — 챕터마다 <n>.mp3 또는 문장마다 <n>-<k>.mp3

PRET = ROOT / "app" / "node_modules" / "pretendard" / "dist" / "public" / "static"  # 작업실 화면과 같은 Pretendard(10/26 사용자)
FONT = str(PRET / "Pretendard-Regular.otf")
BOLD = str(PRET / "Pretendard-Bold.otf")
_fonts = {}


def font(size, bold=False):
    k = (size, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(BOLD if bold else FONT, size)
    return _fonts[k]


BG = (11, 11, 15)
INK = (240, 240, 245)
INK3 = (150, 150, 165)
VIOLET = (167, 139, 250)
ROSE = (244, 114, 140)
AI_COLOR = {"Claude": (217, 119, 87), "astra": (16, 163, 127), "gti": (139, 92, 246), "aside": (59, 130, 246)}

CHAPTERS = [
    {"n": 1, "title": "한눈에 보기", "sub": "사람은 판단만, 작업은 AI가", "parts": [("title", None), ("flow", None)]},
    {"n": 2, "title": "서재", "sub": "원문을 원문 그대로 모은다", "parts": [("clip", "c2")]},
    {"n": 3, "title": "주제 지도", "sub": "쓸 만한 주제를 거른다", "parts": [("clip", "c3")]},
    {"n": 4, "title": "요청과 글 옵션", "sub": "쓰기 전에 메시지부터 정한다", "parts": [("clip", "c4")]},
    {"n": 5, "title": "원문 확인", "sub": "요약이 아니라 원문 전체로 검증한다", "parts": [("clip", "c5"), ("clip", "c5b")]},
    {"n": 6, "title": "쓰기와 피드백", "sub": "모든 과정과 피드백이 기록으로 남는다", "parts": [("clip", "c6")]},
    {"n": 7, "title": "원고 · 제목 · 그림 · 확정", "sub": "지어낸 숫자를 막는 점검", "parts": [("clip", "c7")]},
    {"n": 8, "title": "발행", "sub": "버튼 두 번으로 웹과 메일", "parts": [("clip", "c8"), ("clip", "c8mail"), ("clip", "c8web")]},
    {"n": 9, "title": "", "sub": "", "parts": [("ending", None)]},
]
NO_SQUEEZE = {"c8web", "c8mail"}
# 말이 없어도 자르지 않는 클립(10/26 사용자: 메일·웹 결과물은 스크롤해서 길게) · 클립 끝을 앞당기는 곳(c8web 마지막 스크롤은 바닥에 닿아 흔들림)
KEEP_CLIPS = {"c8mail", "c8web"}
CLIP_END = {"c8web": 33.0}
# 일하는 AI — 기다림 표시 이름의 앞부분으로
WAIT_AI = {"글 옵션": ["astra"], "원문 끝까지": ["astra", "Claude"], "추천 원문": ["astra"], "과정 1·2·3": ["Claude", "astra"],
           "피드백": ["astra"], "제목 후보": ["astra"], "그림 그리기": ["astra", "gti"]}
# 라벨 — 표시 이름의 앞부분 → 화면에 띄울 짧은 말(없으면 테두리만)
CALLOUT = {
    "Supabase 받기 — 마지막": "6시간마다 저절로 받음", "Supabase 받기": "지금 바로 받기", "aside 수집": "RSS가 없는 사이트는 브라우저로 수집",
    "주제 카드 앞면": "말할 것 + 사례", "이 주제로": "이 주제로 바로 글 시작", "판정 칸": "판정을 바꾸면 예시로 쌓임", "다시 거르기": "쌓인 예시로 전체 다시 거르기",
    "다른 추천": "아직 안 쓴 추천 주제", "옵션 1 —": "이 글이 말할 것 + 실제 사례", "이 글로": "이 옵션으로 쓰기",
    "중심 원문": "중심 사례", "받침 원문": "받침 사례", "사내 맥락": "사내 자료 추천 (Claude)", "추천 원문": "더 넣을 만한 원문 (astra)",
    "대상 독자": "대상 독자", "바뀐 문장 형광": "앞 과정에서 바뀐 문장", "피드백 —": "적은 그대로 astra에게", "편집": "직접 고치기",
    "여기서 이어 쓰기": "앞 과정에서 이어 쓰기", "사내 맥락 넣어": "사내 맥락을 원고 한 곳에", "처음부터 다시 쓰기": "처음부터 다시 쓰기",
    "원고 정하기": "이 과정을 원고로", "제목 고르기": "제목 후보 4개 중 고르기", "본문 그림 1 —": "넣을 문단까지 정해 옴",
    "수치·용어 점검": "숫자 7개 모두 원문에 있음", "메일 —": "Outlook에서 그대로 보낼 이미지 메일", "원문 전문": "요약 없이 원문 전체를 저장", "아카이브의 발행된 칼럼": "웹 아카이브의 발행된 칼럼", "메일 미리보기": "메일 모양", "웹 미리보기": "웹 모양", "한 번 더 누르면 발행": "두 번 눌러 발행",
}
# 확대 — 챕터마다 강조할 1~2곳만(10/26 사용자: 클릭마다 당겼다 빼면 어지럽다). (클립, 첫 표시, 끝 표시, 최대 배율)
#   첫 표시 0.9초 전부터 0.8초에 걸쳐 당기고, 끝 표시가 끝날 때까지 같은 자리에서 유지, 0.8초에 걸쳐 뺀다. 자리는 구간 안 표시들을 모두 담는 상자 가운데.
ZOOMS = [
    ("c2", "Supabase 받기 — 마지막", "Supabase 받기", 1.6),
    ("c3", "판정 칸", "판정 칸", 1.5),
    ("c4", "다른 추천", "하고 싶은 말 — 입력", 1.6),
    ("c5", "사내 맥락", "사내 맥락", 1.35),
    ("c6", "지금 글 — 비교", "바뀐 문장 형광", 1.4),
    ("c6", "피드백", "피드백 — 입력", 1.5),
    ("c7", "머리 그림 고르기", "본문 그림 2 고르기", 1.4),
    ("c7", "수치·용어 점검", "확정", 1.5),
    ("c8", "받는 사람", "한 번 더 누르면 발행", 1.6),
]
# 숫자 카드 — (클립, 원본 초 시작, 끝, 글)
NUMBERS = [("c2", "탭 컨설팅", "탭 저널·매체", "원문 1,572편 · 소스 29곳 · 경영일기 252편"), ("c3", "메뉴 주제 지도", "탭 쓸 만함", "주제 126개 · 쓸 만함 69")]  # (클립, 첫 표시, 끝 표시, 글)
# 잘라 낼 구간 — 그 자리는 0.5초 교차 전환(10/26 사용자: c4 옵션이 뜬 직후 화면이 위로 확 올라가 어지럽다)
CUTS = {"c4": [("글 옵션 끝", "옵션 1 —")]}
CARD_S, TITLE_S = 1.8, 2.6
# 문장마다 기준 장면 — (클립 또는 title·flow·ending, 표시 이름 앞부분, 더할 초). 문장은 그 장면 LEAD초 전에 시작하고,
# 앞 문장이 아직 읽히는 중이면 화면이 그 장면 직전에서 멈춰 기다린다(10/26 사용자: 화면이 소리보다 너무 빠르다)
LEAD = 0.4
ANCHORS = {
    1: [("title", None, 0), ("flow", None, 0), ("flow", None, 6.4)],
    2: [("c2", "메뉴 서재", 0), ("c2", "원문 열기", 0), ("c2", "Supabase 받기 — 마지막", 0), ("c2", "aside 수집", 0)],
    3: [("c3", "메뉴 주제 지도", 0), ("c3", "카드 펼치기", 0), ("c3", "판정 칸", 0)],
    4: [("c4", "메뉴 글", 0), ("c4", "글 옵션 시작", 0), ("c4", "옵션 1", 0), ("c4", "이 글로", -1.5)],
    5: [("c5", "원문 끝까지 읽고 확인 시작", 0), ("c5", "사내 맥락", 0), ("c5b", "추천 원문", 0)],
    6: [("c6", "쓰기", 0), ("c6", "지금 글 — 비교", 0), ("c6", "피드백", 0), ("c6", "편집", 0)],
    7: [("c7", "원고로 고를 과정", 0), ("c7", "머리 그림 그리기", 0), ("c7", "수치·용어 점검", 0)],
    8: [("c8", "메뉴 발행", 0), ("c8mail", "메일 미리보기", 0), ("c8web", "아카이브의 발행된 칼럼", 0)],
    9: [("ending", None, 1.0)],
}
# 빈 구간 자르기(10/26 사용자: 5분 안팎으로, 비는 곳은 날려도 됨) — 문장이 끝나고 KEEP_AFTER초, 다음 문장 KEEP_BEFORE초 전까지 말 없이 지나가는
# 화면은 잘라 0.4초 교차 전환으로 잇고, 챕터 끝에 말 없이 남는 화면도 자른다
KEEP_AFTER, KEEP_BEFORE, XF = 2.4, 2.6, 0.4
SCHED = []  # (절대 시작, 끝, 자막, TTS 글, 챕터, 문장 wav)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------- 음성(--audio) ----------
# 챕터 n의 음성: <n>.(mp3|wav|m4a) 하나면 문장 사이 쉼(무음)을 찾아 자막을 나누고, <n>-1, <n>-2 … 문장별 파일이면 0.35초씩 띄워 잇는다.
# 챕터 길이 = 음성 길이 + 1초(앞 0.5초에서 시작). 음성이 없는 챕터는 글자 수로 추정(초당 CPS자).
SR = 48000
GAP = 0.35
_plan = {}


def ffexe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_wav(src, dst):
    subprocess.run([ffexe(), "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)], check=True)
    import wave
    with wave.open(str(dst)) as w:
        return w.getnframes() / SR


def silences(path):
    r = subprocess.run([ffexe(), "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-35dB:d=0.22", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def audio_files(n):
    if not AUDIO:
        return []
    fs = [f for f in AUDIO.iterdir() if f.suffix.lower() in (".mp3", ".wav", ".m4a") and re.fullmatch(rf"{n}([-_]\d+)?", f.stem)]
    return sorted(fs, key=lambda f: int(re.split(r"[-_]", f.stem)[1]) if re.search(r"[-_]", f.stem) else 0)


def plan(n):
    """챕터 n의 내레이션 — [(자막, TTS 글, 시작, 끝)](챕터 음성 시작 기준 초), 전체 길이, 음성 wav(없으면 None)"""
    if n in _plan:
        return _plan[n]
    L = lines(n)
    fs = audio_files(n)
    tmp = OUTDIR / "_audio"
    tmp.mkdir(parents=True, exist_ok=True)
    items, track = [], None
    if fs and len(fs) == len(L) and len(fs) > 1:  # 문장별 파일
        import wave
        t, frames = 0.0, b""
        for (text, tts), f in zip(L, fs):
            d = to_wav(f, tmp / f"{f.stem}.wav")
            with wave.open(str(tmp / f"{f.stem}.wav")) as w:
                frames += w.readframes(w.getnframes())
            items.append((text, tts, t, t + d, tmp / f"{f.stem}.wav"))
            t += d + GAP
            frames += b"\0\0" * int(GAP * SR)
        track = tmp / f"ch{n}.wav"
        with wave.open(str(track), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes(frames)
        total = t - GAP
    elif len(fs) == 1:  # 챕터 하나 — 쉼으로 문장을 나눈다
        track = tmp / f"ch{n}.wav"
        total = to_wav(fs[0], track)
        cands = [(a + b) / 2 for a, b in silences(track) if 0.4 < (a + b) / 2 < total - 0.4]
        weights = [speech(tts) for _, tts in L]
        cuts, prev, acc = [], 0.0, 0.0
        for wgt in weights[:-1]:
            acc += wgt
            want = total * acc / sum(weights)
            c = min((x for x in cands if x > prev + 0.5), key=lambda x: abs(x - want), default=want)
            cuts.append(c)
            prev = c
        bounds = [0.0] + cuts + [total]
        items = [(text, tts, bounds[i], bounds[i + 1], None) for i, (text, tts) in enumerate(L)]
    else:
        if fs:
            print(f"  음성 {n}: 파일 {len(fs)}개 · 문장 {len(L)}개가 맞지 않아 글자 수로 추정", flush=True)
        t = 0.0
        for text, tts in L:
            d = speech(tts)
            items.append((text, tts, t, t + d, None))
            t += d + GAP
        total = max(0.0, t - GAP)
    _plan[n] = (items, total, track)
    return _plan[n]


def speech(s):
    return len(re.sub(r"\s", "", s)) / CPS


def lines(n):
    return [(x[0], x[1] if len(x) > 1 else x[0]) for x in NARR.get(str(n), [])]


# ---------- 클립 ----------

class Clip:
    def __init__(self, name):
        d = REC / name
        fr = json.loads((d / "frames.json").read_text(encoding="utf-8"))
        self.name, self.dir = name, d / "frames"
        self.t0 = fr[0][1]
        self.files = [f for f, _ in fr]
        self.ts = [t - self.t0 for _, t in fr]
        self.end = self.ts[-1]
        self.marks = json.loads((d / "marks-sec.json").read_text(encoding="utf-8")) if (d / "marks-sec.json").exists() else []
        self.waits = []
        open_ = {}
        for m in self.marks:
            if m["kind"] != "wait":
                continue
            if m["label"].endswith(" 시작"):
                open_[m["label"][:-3]] = m["sec"]
            else:
                key = re.sub(r" 끝 \(\d+s\)$", "", m["label"])
                if key in open_ and m["sec"] - open_[key] > 2.5:
                    self.waits.append((open_.pop(key), m["sec"], key))
        acts = [m for m in self.marks if m["kind"] != "wait" and m.get("box")]
        self.events = []
        for i, m in enumerate(acts):
            nxt = acts[i + 1]["sec"] if i + 1 < len(acts) else m["sec"] + 6
            hold = {"click": 0.35, "hover": 1.5, "type": 4.5}[m["kind"]]  # 클릭 테두리는 누른 직후 사라진다(화면이 바뀌면 자리가 어긋남)
            x, y, w, h = m["box"]
            z = 1.0 if w > 1150 or h > 480 else max(1.2, min(1.6, W * 0.68 / max(w, h * 2.4)))  # 요소가 화면 폭의 2/3 안에 들게
            self.events.append({"t": m["sec"], "end": max(m["sec"] + 0.25, min(m["sec"] + hold, nxt - 0.25)), "box": m["box"], "z": z,
                                "label": m["label"], "kind": m["kind"], "callout": next((v for k, v in CALLOUT.items() if m["label"].startswith(k)), "")})
        self.zooms = []
        for c, first, last, zmax in ZOOMS:
            if c != name:
                continue
            a = next((e for e in self.events if e["label"].startswith(first)), None)
            b = next((e for e in reversed(self.events) if e["label"].startswith(last)), None)
            if not a or not b:
                print(f"  확대 표시 못 찾음: {c} {first} ~ {last}", flush=True)
                continue
            inside = [e for e in self.events if a["t"] <= e["t"] <= b["t"]]
            x0_ = min(e["box"][0] for e in inside)
            y0_ = min(e["box"][1] for e in inside)
            x1_ = max(e["box"][0] + e["box"][2] for e in inside)
            y1_ = max(e["box"][1] + e["box"][3] for e in inside)
            z = max(1.15, min(zmax, W * 0.82 / max(1, x1_ - x0_), H * 0.78 / max(1, y1_ - y0_)))
            self.zooms.append({"t0": a["t"] - 0.9, "t1": max(b["end"], b["t"] + 1.4) + 0.6, "cx": (x0_ + x1_) / 2, "cy": (y0_ + y1_) / 2, "z": z})
        lab = lambda pre: next((m["sec"] for m in self.marks if m["label"].startswith(pre)), None)
        self.numbers = [(lab(a), lab(b) + 1.5, text) for c, a, b, text in NUMBERS if c == name and lab(a) is not None and lab(b) is not None]
        self.cuts = [(lab(a) + 0.2, lab(b) - 0.4) for a, b in CUTS.get(name, []) if lab(a) is not None and lab(b) is not None]
        self.scrolls = [(m["sec"], m["sec"] + m.get("dur", 1.0)) for m in self.marks if m["kind"] == "scroll"]
        self._cache = (None, None)

    def frame(self, s):
        i = max(0, bisect.bisect_right(self.ts, s) - 1)
        if self._cache[0] != i:
            self._cache = (i, Image.open(self.dir / self.files[i]).convert("RGB"))
        return self._cache[1]

    def segments(self):
        """원본 시간을 (s0, s1, 빠르기, 기다림) 조각으로 — 앞뒤 군더더기를 자르고, 기다림은 빨리, 빈 곳은 4배로"""
        acts = [m["sec"] for m in self.marks if m["kind"] != "wait"]
        start = max(0.0, (min(acts + [w[0] for w in self.waits]) if acts or self.waits else 0) - 1.5)
        end = self.end if self.name in NO_SQUEEZE or not acts else min(self.end, max(acts + [w[1] for w in self.waits]) + 2.5)
        end = min(end, CLIP_END.get(self.name, end))
        cuts, t = [], start
        for a, b, key in sorted(self.waits):
            if a > t:
                cuts.append((t, a, None))
            cuts.append((a, b, key))
            t = b
        if end > t:
            cuts.append((t, end, None))
        out = []
        for a, b, key in cuts:
            if key:
                tgt = max(2.0, min(4.0, (b - a) / 14))
                out.append({"s0": a, "s1": b, "speed": (b - a) / tgt, "wait": key, "base": tgt})
                continue
            if self.name in NO_SQUEEZE:
                out.append({"s0": a, "s1": b, "speed": 1.0})
                continue
            # 빈 곳 = 앞 표시가 끝난 뒤(입력은 4.5초 동안 이어짐)부터 다음 표시까지
            busy = sorted([(e["t"], e["end"] + 0.5) for e in self.events if e["end"] > a and e["t"] < b] + [(x, y + 0.8) for x, y in self.scrolls if y > a and x < b])
            seg_start, p = a, a
            for t0_, t1_ in busy + [(b, b)]:
                if t0_ - p > 6:
                    out.append({"s0": seg_start, "s1": p + 2, "speed": 1.0})
                    out.append({"s0": p + 2, "s1": t0_ - 2, "speed": 4.0})
                    seg_start = t0_ - 2
                p = max(p, t1_)
            out.append({"s0": seg_start, "s1": b, "speed": 1.0})
        for ca, cb in self.cuts:
            cut = []
            for o in out:
                if o["s1"] <= ca or o["s0"] >= cb or o.get("wait"):
                    cut.append(o)
                    continue
                if o["s0"] < ca:
                    cut.append({**o, "s1": ca})
                cut.append({"kind": "xfade", "a": (self.name, ca), "b": (self.name, cb), "speed": 1.0, "dur": 0.5, "s0": ca, "s1": ca})
                if o["s1"] > cb:
                    cut.append({**o, "s0": cb})
            out = cut
        for o in out:
            o["clip"] = self.name
            if o.get("kind") != "xfade":
                o["dur"] = (o["s1"] - o["s0"]) / o["speed"]
        return [o for o in out if o["dur"] > 0.05]


# ---------- 그리기 ----------

def pill(d, xy, text, size=26, fg=INK, bg=(30, 27, 45), pad=(18, 10), dot=None, anchor="lt", bold=True, ff=False):
    f = font(size, bold)
    tw = d.textlength(text, font=f)
    dw = (size * 0.55 + 10) if dot else (size * 1.1 + 10) if ff else 0
    w, h = tw + pad[0] * 2 + dw, size + pad[1] * 2 + 6
    x, y = xy
    if anchor[0] == "r":
        x -= w
    if anchor[1] == "b":
        y -= h
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    if dot:
        r = size * 0.28
        cx, cy = x + pad[0] + r, y + h / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot)
    if ff:  # 빨리 감기 표시 ▶▶ — 글꼴에 없을 수 있어 직접 그린다
        a_ = size * 0.5
        x1, cy = x + pad[0], y + h / 2
        for k in (0, 1):
            bx = x1 + k * a_ * 1.05
            d.polygon([(bx, cy - a_ / 2 - 2), (bx + a_, cy), (bx, cy + a_ / 2 + 2)], fill=fg)
    d.text((x + pad[0] + dw, y + pad[1] - 1), text, font=f, fill=fg)
    return w, h


def overlay_clip(img, seg, ev, cam, s, clip):
    d = ImageDraw.Draw(img, "RGBA")
    z, x0, y0 = cam
    if ev and seg["speed"] <= 1.5:
        bx, by, bw, bh = ev["box"]
        X, Y, X2, Y2 = (bx - 6 - x0) * z, (by - 6 - y0) * z, (bx + bw + 6 - x0) * z, (by + bh + 6 - y0) * z
        if bw < 1150 and bh < 480 and (ev["kind"] != "hover" or ev["callout"]):
            d.rounded_rectangle([X, Y, X2, Y2], radius=12, outline=VIOLET + (235,), width=4)
        if ev["callout"]:
            cy = Y2 + 14 if Y2 + 80 < H else Y - 62
            cx = min(max(X, 30), W - 30 - d.textlength(ev["callout"], font=font(26, True)) - 40)
            pill(d, (cx, cy), ev["callout"], 26, fg=(255, 255, 255), bg=(91, 33, 182, 235))
    for a, b, text in clip.numbers:
        if a <= s <= b:
            pill(d, (W - 40, 40), text, 28, bg=(20, 20, 28, 230), anchor="rt", dot=VIOLET)
    if seg.get("wait"):
        real = seg["s1"] - seg["s0"]
        pill(d, (W - 40, 40), f"×{seg['speed']:.0f}  ·  실제 {int(real // 60)}분 {int(real % 60):02d}초" if real >= 60 else f"×{seg['speed']:.0f}  ·  실제 {real:.0f}초",
             28, bg=(20, 20, 28, 235), anchor="rt", ff=True)
        ais = next((v for k, v in WAIT_AI.items() if seg["wait"].startswith(k)), [])
        x = W - 40
        for name in reversed(ais):
            w, _ = pill(d, (x, H - 40), f"{name} 작업 중", 26, bg=(20, 20, 28, 235), dot=AI_COLOR[name], anchor="rb")
            x -= w + 12


def card(n, title, sub, t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((240, 400), f"{n:02d}", font=font(120, True), fill=VIOLET)
    d.text((240, 560), title, font=font(84, True), fill=INK)
    if sub:
        d.text((244, 680), sub, font=font(38), fill=INK3)
    return fade(img, t, dur)


def fade(img, t, dur, f=0.3):
    a = min(1.0, t / f, (dur - t) / f)
    return img if a >= 1 else Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, max(0.0, a))


def title_card(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f = font(110, True)
    s = "AI 뉴스레터 칼럼 제작 자동화"  # 과제 제목(10/26 사용자)
    d.text(((W - d.textlength(s, font=f)) / 2, 420), s, font=f, fill=INK)
    s2 = "원문 수집부터 발행까지, 한 화면에서"
    d.text(((W - d.textlength(s2, font=font(40))) / 2, 580), s2, font=font(40), fill=INK3)
    return fade(img, t, dur)


FLOW = [("서재", "원문 수집", "aside", False), ("주제 지도", "카드·묶기·거르기", "astra · Claude", False), ("요청", "하고 싶은 말", "", True),
        ("글 옵션", "말할 것 고르기", "astra", True), ("원문 확인", "끝까지 읽고 검증", "astra", False), ("쓰기", "과정 1·2·3", "Claude · astra", False),
        ("피드백", "적은 그대로 전달", "", True), ("원고·제목·그림", "고르기", "astra · gti", True), ("확정", "수치·용어 점검", "", False), ("발행", "웹 + 메일", "", True)]
ROLES = [("Claude", "초안 · 주제 거르기 · 사내 자료 추천"), ("astra", "원문 카드 · 글 옵션 · 확인 · 재작성 · 제목"), ("gti", "그림"), ("aside", "원문 수집")]


def flow(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((120, 90), "칼럼 한 편이 나오기까지", font=font(52, True), fill=INK)
    d.text((124, 165), "빨간 칸만 사람이 합니다", font=font(32), fill=ROSE)
    bw, bh, gap = 300, 150, 52
    for i, (name, desc, ai, human) in enumerate(FLOW):
        row, col = divmod(i, 5)
        x, y = 120 + col * (bw + gap), 270 + row * (bh + 90)
        on = ease((t - 0.4 - i * 0.55) / 0.4)
        base = (36, 34, 48)
        hi = (120, 30, 55) if human else (52, 46, 80)
        fill = tuple(int(base[k] + (hi[k] - base[k]) * on) for k in range(3))
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=22, fill=fill, outline=(ROSE if human else VIOLET) + (int(255 * on),), width=3)
        d.text((x + 24, y + 22), name, font=font(36, True), fill=INK)
        d.text((x + 24, y + 74), desc, font=font(24), fill=INK3 if not on else (215, 215, 225))
        if ai:
            d.text((x + 24, y + 108), ai, font=font(20, True), fill=(170, 170, 190))
        if col < 4:
            ax = x + bw + 8
            d.line([ax, y + bh / 2, ax + gap - 16, y + bh / 2], fill=(90, 90, 110), width=3)
    t2 = t - (0.4 + len(FLOW) * 0.55 + 0.6)
    for i, (name, role) in enumerate(ROLES):
        a = ease((t2 - i * 0.35) / 0.4)
        if a <= 0:
            continue
        x, y = 120 + (i % 2) * 860, 790 + (i // 2) * 80
        c = AI_COLOR[name]
        d.ellipse([x, y + 10, x + 28, y + 38], fill=c + (int(255 * a),))
        d.text((x + 44, y), name, font=font(34, True), fill=INK + (int(255 * a),))
        d.text((x + 44 + d.textlength(name, font=font(34, True)) + 22, y + 6), role, font=font(28), fill=INK3 + (int(255 * a),))
    return fade(img, t, dur)


def ending(t, dur):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    rows = ["사람은 판단만, 작업은 AI가", "원문에 근거한 글 — 원문 전체로 확인하고 숫자까지 점검", "버튼 몇 번으로 웹과 메일 발행"]
    for i, r in enumerate(rows):
        a = ease((t - 0.5 - i * 1.4) / 0.5)
        if a <= 0:
            continue
        col = tuple(int(BG[k] + (INK[k] - BG[k]) * a) for k in range(3))
        y = 330 + i * 110  # 체크 표시는 선으로(맑은 고딕에 ✓ 글자가 없다)
        d.line([(244, y + 40), (262, y + 58), (296, y + 20)], fill=tuple(int(BG[k] + (VIOLET[k] - BG[k]) * a) for k in range(3)), width=8, joint="curve")
        d.text((320, 330 + i * 110), r, font=font(52, True), fill=col)
    a = ease((t - 5.5) / 0.6)
    if a > 0:
        s = "AI 뉴스레터 칼럼 제작 자동화"
        d.text((240, 760), s, font=font(64, True), fill=tuple(int(BG[k] + (VIOLET[k] - BG[k]) * a) for k in range(3)))
    return fade(img, t, dur, 0.5)


# ---------- 타임라인 ----------

def build():
    clips, tl = {}, []
    for ch in CHAPTERS:
        if ONLY and ch["n"] not in ONLY:
            continue
        need = plan(ch["n"])[1] + 1.2
        if 2 <= ch["n"] <= 8:
            tl.append({"kind": "card", "ch": ch, "dur": CARD_S})
        body = []
        for kind, name in ch["parts"]:
            if kind == "clip":
                clips.setdefault(name, Clip(name))
                body += clips[name].segments()
            elif kind == "title":
                body.append({"kind": "title", "dur": TITLE_S})
            elif kind == "flow":
                body.append({"kind": "flow", "dur": 12.0})
            elif kind == "ending":
                body.append({"kind": "ending", "dur": 10.5})  # 마무리 10~12초(10/26 사용자)
        sched = fit(ch["n"], body, clips)
        for s in body:
            s.setdefault("kind", "clip")
            s["ch"] = ch
        tl += body
        ch["_sched"] = sched
    t = 0.0
    for s in tl:
        s["out0"] = t
        t += s["dur"]
    SCHED.clear()
    for ch in CHAPTERS:
        body = [s for s in tl if s["ch"] is ch and s["kind"] != "card"]
        if body:
            SCHED.extend((body[0]["out0"] + a, body[0]["out0"] + b, text, tts, ch, wav) for a, b, text, tts, wav in ch.get("_sched", []))
    return tl, clips, t


def _at(body, clips, spec):
    """기준 장면이 본문 시작에서 몇 초 뒤에 오는지"""
    what, label, off = spec
    t = 0.0
    if what in ("title", "flow", "ending"):
        for sg in body:
            if sg.get("kind") == what:
                return t + off
            t += sg["dur"]
        return None
    sec = next((m["sec"] for m in clips[what].marks if m["label"].startswith(label)), None) if what in clips else None
    if sec is None:
        return None
    for sg in body:
        if sg.get("clip") == what and sg.get("kind", "clip") == "clip" and sg["speed"] > 0 and sec <= sg["s1"]:
            return t + max(0.0, (sec - sg["s0"]) / sg["speed"]) + off
        t += sg["dur"]
    return None


def _hold(body, at, dur):
    """본문 at초 자리에서 화면을 dur초 멈춘다(그 자리 프레임 그대로)"""
    t = 0.0
    for i, sg in enumerate(body):
        if at < t + sg["dur"] or i == len(body) - 1:
            if sg.get("kind", "clip") == "clip" and sg.get("clip") and sg["speed"] > 0:
                sp = min(sg["s1"], sg["s0"] + max(0.0, at - t) * sg["speed"])
                a_, b_ = dict(sg), dict(sg)
                a_["s1"], a_["dur"] = sp, (sp - sg["s0"]) / sg["speed"]
                b_["s0"], b_["dur"] = sp, (sg["s1"] - sp) / sg["speed"]
                hold = {"kind": "clip", "clip": sg["clip"], "s0": sp, "s1": sp, "speed": 0.0, "dur": dur, "hold": True}
                body[i:i + 1] = [x for x in (a_, hold, b_) if x["dur"] > 0.001 or x is hold]
            elif sg.get("kind") == "xfade":
                body.insert(i, {"kind": "clip", "clip": sg["a"][0], "s0": sg["a"][1], "s1": sg["a"][1], "speed": 0.0, "dur": dur, "hold": True})
            elif sg.get("hold"):
                sg["dur"] += dur
            else:
                sg["dur"] += dur  # 카드·흐름도·엔딩은 그 화면을 늘린다
            return
        t += sg["dur"]


def _where(body, t):
    """본문 t초에 있는 조각 번호와 그 조각 안 초"""
    acc = 0.0
    for i, sg in enumerate(body):
        if t < acc + sg["dur"]:
            return i, t - acc
        acc += sg["dur"]
    return None, None


def _src(sg, off):
    """그 조각 off초 자리의 (클립, 원본 초) — 클립 화면이 아니면 None"""
    if sg.get("kind", "clip") != "clip" or not sg.get("clip"):
        return None
    return sg["clip"], sg["s0"] + off * sg["speed"]


def _split(body, t):
    """t초에서 조각을 둘로 — 클립·멈춤 조각만. 잘린 자리의 조각 번호를 돌려준다(못 자르면 None)"""
    i, off = _where(body, t)
    if i is None:
        return len(body)
    sg = body[i]
    if off < 1e-6:
        return i
    if sg.get("kind", "clip") != "clip" or not sg.get("clip"):
        return None
    a_, b_ = dict(sg), dict(sg)
    if sg["speed"] > 0:
        sp = sg["s0"] + off * sg["speed"]
        a_["s1"], b_["s0"] = sp, sp
    a_["dur"], b_["dur"] = off, sg["dur"] - off
    body[i:i + 1] = [a_, b_]
    return i + 1


def _cut(body, x, y):
    """본문 x~y초를 들어내고 XF초 교차 전환으로 잇는다. 줄어든 초를 돌려준다(카드·흐름도 등이 끼면 자르지 않음)"""
    i, ox = _where(body, x)
    j, oy = _where(body, y)
    if i is None or j is None:
        return 0.0
    if any(sg.get("kind", "clip") != "clip" or not sg.get("clip") or sg["clip"] in KEEP_CLIPS for sg in body[i:j + 1]):
        return 0.0
    sa, sb = _src(body[i], ox), _src(body[j], oy)
    ix = _split(body, x)  # 자르기는 시각을 바꾸지 않으므로 x, y 순서대로
    jy = _split(body, y)
    if ix is None or jy is None:
        return 0.0
    removed = sum(sg["dur"] for sg in body[ix:jy])
    body[ix:jy] = [{"kind": "xfade", "a": sa, "b": sb, "dur": XF, "clip": sa[0], "s0": sa[1], "s1": sa[1], "speed": 1.0}]
    return removed - XF


def _truncate(body, t):
    """본문을 t초까지만 — 클립 조각이 끝일 때만 자른다"""
    k = _split(body, t)
    if k is not None and k < len(body) and all(sg.get("kind", "clip") == "clip" and sg.get("clip") and sg["clip"] not in KEEP_CLIPS for sg in body[k:]):
        del body[k:]


def fit(n, body, clips):
    """문장을 기준 장면에 맞춰 놓고, 앞 문장이 길면 화면을 멈춰 기다리게 한다 → [(본문 기준 시작, 끝, 자막, TTS, wav)]"""
    items = plan(n)[0]
    specs = ANCHORS.get(n, [])
    out, cur = [], 0.5
    for k, (text, tts, a, b, wav) in enumerate(items):
        at = _at(body, clips, specs[k]) if k < len(specs) else None
        start = cur
        if at is not None:
            want = max(0.0, at - LEAD)
            if want >= cur:
                start = want
            elif want > 0.5:
                _hold(body, want, cur - want)
        out.append((start, start + (b - a), text, tts, wav))
        cur = start + (b - a) + GAP
    # 빈 구간 — 뒤에서부터 잘라야 앞 시각이 그대로다
    gaps = [(out[i][1] + KEEP_AFTER, out[i + 1][0] - KEEP_BEFORE) for i in range(len(out) - 1)]
    for x, y in reversed(gaps):
        if y - x > XF + 0.6:
            cut = _cut(body, x, y)
            if cut:
                out = [(a - cut, b - cut, *r) if a >= y else (a, b, *r) for a, b, *r in out]
    if out:  # 챕터 끝 — 마지막 문장 뒤 1.2초까지만
        _truncate(body, out[-1][1] + 1.2)
    have = sum(sg["dur"] for sg in body)
    need = (out[-1][1] + 0.8) if out else 0
    if need > have:
        last = body[-1]
        if last.get("clip"):
            body.append({"clip": last["clip"], "s0": last["s1"], "s1": last["s1"], "speed": 0.0, "dur": need - have, "hold": True})
        else:
            last["dur"] += need - have
    return out


def subtitles(tl):
    return [(a, b, text, tts, ch) for a, b, text, tts, ch, _ in SCHED]


def ts(x, sep=","):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def write_texts(subs, total):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    srt = []
    for i, (a, b, text, _, _) in enumerate(subs, 1):
        # 자막은 한 줄 40자 안팎으로 나눈다
        words, rows, cur = text.split(" "), [], ""
        for w_ in words:
            if len(cur) + len(w_) > 38 and cur:
                rows.append(cur)
                cur = w_
            else:
                cur = f"{cur} {w_}".strip()
        rows.append(cur)
        srt.append(f"{i}\n{ts(a)} --> {ts(b)}\n" + "\n".join(rows) + "\n")
    (OUTDIR / f"{NAME}.srt").write_text("\n".join(srt), encoding="utf-8")
    md = [f"# 시연 영상 내레이션 — {NAME}", "", f"전체 {int(total // 60)}분 {int(total % 60)}초 · " + (f"음성 {AUDIO.name} 길이 기준" if AUDIO else f"초당 {CPS}자 기준(TTS 음성을 받으면 실제 길이로 다시 맞춘다)"), ""]
    tts = []
    cur = None
    for a, b, text, sp, ch in subs:
        if ch is not cur:
            cur = ch
            md += ["", f"## {ch['n']}. {ch['title'] or '엔딩'}", "", "| 시각 | 자막 | TTS에 넣을 글 |", "|---|---|---|"]
            tts += ["", f"[{ch['n']}. {ch['title'] or '엔딩'}]"]
        md.append(f"| {ts(a, '.')[3:8]}–{ts(b, '.')[3:8]} | {text} | {sp if sp != text else '같음'} |")
        tts.append(sp)
    (OUTDIR / f"{NAME}-narration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUTDIR / f"{NAME}-tts.txt").write_text("\n".join(tts).strip() + "\n", encoding="utf-8")


def clip_image(clip, s, seg, quiet):
    """원본 s초 화면 — 정해 둔 확대 구간이면 당기고, 표시(테두리·라벨)와 배지를 그린다. quiet면 테두리·라벨 없이"""
    src = clip.frame(s).copy()
    best = None
    if not quiet:
        for ev in clip.events:
            # 클릭 테두리는 누르기 직전(0.12초)부터만 — 그 전에는 커서가 옮겨 가는 중이라 화면과 자리가 어긋날 수 있다(멈춘 화면에서 특히)
            lead = 0.12 if ev["kind"] == "click" else 0.3
            env = min(ease((s - (ev["t"] - lead)) / 0.12), 1 - ease((s - ev["end"]) / 0.4))
            if env > 0.01 and (best is None or env > best[1]):
                best = (ev, env)
    z, cx, cy = 1.0, W / 2, H / 2
    for zm in clip.zooms:
        env = min(ease((s - zm["t0"]) / 0.8), 1 - ease((s - zm["t1"]) / 0.8))
        if env > 0:
            z, cx, cy = 1 + (zm["z"] - 1) * env, zm["cx"], zm["cy"]
            break
    cw, chh = W / z, H / z
    x0 = min(max(cx - cw / 2, 0), W - cw)
    y0 = min(max(cy - chh / 2, 0), H - chh)
    img = src if z < 1.003 else src.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + chh))
    active = best[0] if best and best[1] > 0.6 else None
    overlay_clip(img, seg if seg.get("kind", "clip") == "clip" else {**seg, "speed": 1.0, "wait": None}, active, (z, x0, y0), s, clip)
    return img


def render(tl, clips, total):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out = OUTDIR / (f"{NAME}-video.mp4" if AUDIO else f"{NAME}.mp4")
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    z, cx, cy = 1.0, W / 2, H / 2
    n_total = int(total * FPS)
    k = 0
    for seg in tl:
        n = max(1, round(seg["dur"] * FPS))
        for f in range(n):
            t = f / FPS
            kind = seg["kind"]
            if kind == "card":
                img = card(seg["ch"]["n"], seg["ch"]["title"], seg["ch"]["sub"], t, seg["dur"])
                z, cx, cy = 1.0, W / 2, H / 2
            elif kind == "title":
                img = title_card(t, seg["dur"])
            elif kind == "flow":
                img = flow(t, seg["dur"])
            elif kind == "ending":
                img = ending(t, seg["dur"])
            elif kind == "xfade":
                (ca, sa), (cb, sb) = seg["a"], seg["b"]
                img = Image.blend(clip_image(clips[ca], sa, seg, True), clip_image(clips[cb], sb, seg, True), ease(t / seg["dur"]))
            else:
                img = clip_image(clips[seg["clip"]], seg["s0"] + t * seg["speed"], seg, seg.get("hold") or seg["speed"] > 1.5)
            p.stdin.write(img.tobytes())
            k += 1
            if k % 900 == 0:
                print(f"  {k}/{n_total} 프레임 ({k / FPS:.0f}초)", flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    tl, clips, total = build()
    subs = subtitles(tl)
    write_texts(subs, total)
    print(f"타임라인 {total:.0f}초 · 조각 {len(tl)} · 자막 {len(subs)}줄", flush=True)
    for ch in CHAPTERS:
        segs = [s for s in tl if s["ch"] is ch]
        if segs:
            print(f"  {ch['n']} {ch['title'] or '엔딩'}: {segs[0]['out0']:.0f}–{segs[-1]['out0'] + segs[-1]['dur']:.0f}초", flush=True)
    out = render(tl, clips, total)
    if AUDIO:
        out = mux(tl, total, out)
    print(f"끝 → {out}")


def mux(tl, total, video):
    """문장 음성을 자막과 같은 자리에 놓고, 소리 크기를 맞춰(-16 LUFS) 영상에 입힌다"""
    import wave
    buf = bytearray(int(total * SR) * 2 + SR * 2)
    placed = set()
    for a, b, text, tts, ch, wav in SCHED:
        src = wav
        if src is None:  # 챕터 파일 하나 — 첫 문장 자리에 통째로
            if ch["n"] in placed:
                continue
            placed.add(ch["n"])
            src = plan(ch["n"])[2]
            if not src:
                continue
        with wave.open(str(src)) as w:
            data = w.readframes(w.getnframes())
        at = int(a * SR) * 2
        buf[at:at + len(data)] = data
    wav = OUTDIR / "_audio" / f"{NAME}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(bytes(buf[: int(total * SR) * 2]))
    out = OUTDIR / f"{NAME}.mp4"
    subprocess.run([ffexe(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-movflags", "+faststart", str(out)], check=True)
    video.unlink()
    return out


if __name__ == "__main__":
    main()
