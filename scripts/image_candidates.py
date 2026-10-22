"""그림 후보 — 마지막 과정의 원고를 astra가 읽고 머리 그림 설명을 쓰면 gti가 그린다.

사용: python3 image_candidates.py <설정 이름|원고 파일>            — 머리 그림 후보
      python3 image_candidates.py [--inline] <설정 이름> --file <원고 파일>  — 원고로 정한 과정(작업실 원고 → 그림 → 확정)을 읽고 그림 폴더는 설정 이름으로
      python3 image_candidates.py --inline <설정 이름|원고 파일>   — 본문 그림 2개(멘토 2026-10-11: "본문에 설명에 도움을 줄수있는 이미지도 한 2개정도")
결과: runs/images/<이름>/<회차>/{prompt.md, astra.json, NN.png} · 본문 그림은 회차 폴더가 inline-<시각>,
      astra.json 항목마다 after(몇째 문단 뒤)·anchor(그 문단 첫머리)
- 설명은 astra만 쓴다(제목과 같은 이유 — Claude가 쓰면 AI slop). 회차를 다시 돌리면 후보가 쌓인다.
- gti는 무조건 gpt-6-astra(멘토 2026-10-09). god-tibo-imagen 스킬 스크립트로 불러 모델 고정·PNG 검증을 맡긴다.
  Codex ChatGPT 인증으로 도는 비공식 경로라 깨질 수 있다.
- 다시 그리기: python3 image_candidates.py --redraw runs/images/<이름>/<회차>  (설명은 그대로, 그림 없는 것만)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs" / "images"
# gti는 무조건 gpt-6-astra (멘토 2026-10-09). 전역 npm gti는 기본 gpt-5.4라 400이 나서,
# 모델을 강제하고 PNG를 검증하는 god-tibo-imagen 스킬 스크립트로 부른다.
# 이 PC의 스킬(모델 고정 수정본)을 먼저 쓰고, 없으면 저장소 사본(tools/god-tibo-imagen — 새 PC·Windows용)
GEN = next((str(p) for p in (Path.home() / ".codex" / "skills" / "god-tibo-imagen" / "scripts" / "generate-image.mjs",
                             ROOT / "tools" / "god-tibo-imagen" / "scripts" / "generate-image.mjs") if p.exists()), "")
# Windows에선 npm이 깐 codex가 codex.cmd라 이름만으로는 못 찾는다 — 전체 경로로 (리눅스는 그대로)
CODEX = shutil.which("codex") or "codex"
# 그림체는 고정한다(2026-10-20) — astra가 매번 그림체까지 정하니 정물화·아이소메트릭·회화로 제각각이 됐다.
# main 브랜치의 '일러스트 B'를 config/image_style.json에 두고, astra는 장면·구도만 쓴다.
# 장수 고정(2026-10-22 사용자 결정): 머리 그림 후보 4장 그려 1장 고름, 본문 그림 2장 그려 1~2장 고름(작업실 act_inline이 2장까지)
HERO_N, INLINE_N = 4, 2
STYLE = json.loads((ROOT / "config" / "image_style.json").read_text(encoding="utf-8"))
STYLE_RULE = ("- 그림체는 이미 정해져 있습니다(" + STYLE["label"] + ": " + STYLE["prefix"] + ") — 설명에는 그림체·색·화풍을 쓰지 말고"
              " 장면·인물·사물·구도만 쓰세요")


def latest(name):
    d = ROOT / "runs" / "columns" / name
    revs = sorted(d.glob("final-r*.md"), key=lambda p: int(p.stem.split("-r")[1]))
    for f in [*reversed(revs), d / "final.md", d / "r4.md", d / "draft.md"]:
        if f.exists():
            return f


def prompt(text):
    return f"""아래 칼럼은 사내 뉴스레터(SK E&S 전 직원 대상) 메일 맨 위에 그림 한 장과 함께 나갑니다.
그 머리 그림의 후보 {HERO_N}개를 그림 설명으로 써 주세요. 설명은 이미지 생성 모델에 그대로 넣습니다.

- 후보끼리 장면·구도가 서로 다르게
- 글이 실제로 말하는 장면이나 생각에서 출발
{STYLE_RULE}
- 그림 안에 글자는 넣지 않음

출력: JSON 배열만 주세요(정확히 {HERO_N}개). [{{"name": "짧은 이름", "prompt": "이미지 생성 모델에 넣을 설명(영어)"}}]
파일을 만들거나 명령을 실행하지 마세요.

=== 칼럼 ===
{text.replace("(끝)", "").strip()}"""


def paragraphs(text):
    body = text.replace("(끝)", "").strip()
    lines = body.split("\n", 1)
    if lines[0].lstrip().startswith("#") or len(lines[0]) < 60 and len(lines) > 1:  # 첫 줄 제목은 뺀다
        body = lines[1] if len(lines) > 1 else ""
    return [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]


def inline_prompt(paras):
    numbered = "\n\n".join(f"[{i}] {x}" for i, x in enumerate(paras, 1))
    return f"""아래 칼럼은 사내 뉴스레터(SK E&S 전 직원 대상)에 실립니다. 본문 사이사이에 넣어, 읽는 사람이 글의 설명을 더 쉽게 이해하도록 돕는 그림을 {INLINE_N}개 골라 그림 설명을 써 주세요. 설명은 이미지 생성 모델에 그대로 넣습니다.

- 그림마다 어느 문단 뒤에 넣을지 [문단 번호]로
- 글이 설명하는 생각·관계·흐름이 한눈에 보이게
- 장식이 아니라 설명을 돕는 그림 — 글이 말하는 장면이나 전후 차이를 보여 줌
- 16:9 한 화면에 들어가는 구도로. 칸을 나눈 띠 그림(나란히 놓인 두 장면, 화살표로 이은 3단계 연속 장면, 파노라마)은 쓰지 않음 — 그림 모델이 아주 긴 가로 그림을 그려 버린다. 전후 차이는 한 화면 안에서(예: 책상 양쪽, 앞과 뒤)
{STYLE_RULE}
- 그림 안에 글자는 넣지 않음
- 왜 그 문단인지 한 줄로(why)

출력: JSON 배열만 주세요(정확히 {INLINE_N}개). [{{"after": 문단 번호, "name": "짧은 이름", "why": "그 문단을 고른 이유(한국어 한 줄)", "prompt": "이미지 생성 모델에 넣을 설명(영어)"}}]
파일을 만들거나 명령을 실행하지 마세요.

=== 칼럼 (문단 번호 붙임) ===
{numbered}"""


def source_of(target, file=None):
    """그림이 읽을 원고 — --file(원고로 정한 과정)이 있으면 그것, 아니면 원고 파일이나 설정의 마지막 과정."""
    if file:
        return (ROOT / file).resolve()
    return (ROOT / target).resolve() if target.endswith(".md") else latest(target)


def run_inline(target, file=None):
    f = source_of(target, file)
    name = Path(target).stem if target.endswith(".md") else target
    d = OUT / name / ("inline-" + time.strftime("%Y%m%d-%H%M%S"))
    d.mkdir(parents=True, exist_ok=True)
    paras = paragraphs(f.read_text(encoding="utf-8"))
    p = inline_prompt(paras)
    (d / "prompt.md").write_text(p, encoding="utf-8")
    (d / "source.txt").write_text(f.relative_to(ROOT).as_posix(), encoding="utf-8")
    out = d / "astra.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), "-"],
                       cwd=d, input=p, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    raw = out.read_text(encoding="utf-8") if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = (json.loads(m.group(0)) if m else [])[:INLINE_N]  # 더 내도 앞의 INLINE_N장만 그린다
    for it in items:
        k = int(it.get("after", 0))
        it["after"] = k
        it["anchor"] = paras[k - 1][:40] if 1 <= k <= len(paras) else ""  # 과정이 바뀌어도 자리를 찾게 문단 첫머리를 함께 둔다
    (d / "astra.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    paint(d, items)


def draw(d, i, it):
    png = d / f"{i:02d}.png"
    if png.exists():  # 줄 서 있던 사이 다른 회차·다시 그리기로 이미 그려졌으면 덮어쓰지 않는다
        return True
    with open(d / f"{i:02d}.log", "w", encoding="utf-8") as log:
        # 본문 그림은 16:9(astra가 설명에 와이드로 쓰고 그림 서버도 그 비율로 그린다 — 3:2 검사에 걸려 전부 버려졌다, 2026-10-10)
        size, ratio, tol = ("2048x1152", "16:9", "0.05") if d.name.startswith("inline-") else ("1536x1024", "3:2", "0.2")
        frame = " Compose it as one single scene in a standard 16:9 widescreen frame, not a panoramic strip or multi-panel sequence." if d.name.startswith("inline-") else ""
        full = f'{STYLE["prefix"]} {it["prompt"]}{frame} {STYLE["suffix"]}'
        subprocess.run(["node", GEN, "--prompt", full, "--output", str(png), "--size", size, "--ratio", ratio,
                        "--tolerance", tol, "--model", "gpt-6-astra",
                        # 한 장 40초대지만 같은 계정의 요청은 서버가 차례로 처리한다 — 6장 동시면 90초(gti 기본)를 넘겨
                        # 전부 시간 초과로 버려졌다(2026-10-20 Windows 시험: 1장 43초, 3장 동시 45·67·80초). 5분 × 2회까지 기다린다
                        "--timeout-ms", "300000", "--retries", "1"],
                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=900,
                       # Node가 Windows 인증서 저장소를 믿게 한다 — 사내망은 HTTPS를 회사 인증서로 다시 서명해서, Node 기본 인증서만으로는
                       # 연결이 성립하지 않고 응답 없이 시간 초과로 끝났다(2026-10-22: 이 값이 없으면 100초 초과, 있으면 48초에 그림)
                       env={**os.environ, "NODE_USE_SYSTEM_CA": "1"})
    return png.exists()


def run(target, file=None):
    f = source_of(target, file)
    name = Path(target).stem if target.endswith(".md") else target
    d = OUT / name / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    p = prompt(f.read_text(encoding="utf-8"))
    (d / "prompt.md").write_text(p, encoding="utf-8")
    (d / "source.txt").write_text(f.relative_to(ROOT).as_posix(), encoding="utf-8")
    out = d / "astra.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), "-"],
                       cwd=d, input=p, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    raw = out.read_text(encoding="utf-8") if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = (json.loads(m.group(0)) if m else [])[:HERO_N]  # 더 내도 앞의 HERO_N장만 그린다
    (d / "astra.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    paint(d, items)


def paint(d, items):
    todo = [(i, it) for i, it in enumerate(items, 1) if not (d / f"{i:02d}.png").exists()]
    with ThreadPoolExecutor(max_workers=2) as ex:  # 머리·본문 그림 작업이 같이 돌면 4장 — 그 이상은 기다리는 줄만 길어진다
        list(ex.map(lambda a: draw(d, *a), todo))
    ok = sum(1 for i in range(1, len(items) + 1) if (d / f"{i:02d}.png").exists())
    print(f"그림 후보 {ok}/{len(items)} → {d.relative_to(ROOT)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    file = a[a.index("--file") + 1] if "--file" in a else None
    if file:
        a = a[:a.index("--file")] + a[a.index("--file") + 2:]
    if a[:1] == ["--inline"]:
        run_inline(a[1], file)
    elif a[:1] == ["--redraw"]:
        d = (ROOT / a[1]).resolve()
        paint(d, json.loads((d / "astra.json").read_text(encoding="utf-8")))
    else:
        run(a[0], file)
