"""그림 후보 — 마지막 과정의 원고를 astra가 읽고 머리 그림 설명을 쓰면 gti가 그린다.

사용: python3 image_candidates.py <설정 이름|원고 파일>            — 머리 그림 후보
      python3 image_candidates.py --inline <설정 이름|원고 파일>   — 본문 그림 3개(멘토 2026-10-10: "글 사이사이에 … 이해를 도울 수 있는")
결과: runs/images/<이름>/<회차>/{prompt.md, astra.json, NN.png} · 본문 그림은 회차 폴더가 inline-<시각>,
      astra.json 항목마다 after(몇째 문단 뒤)·anchor(그 문단 첫머리)
- 설명은 astra만 쓴다(제목과 같은 이유 — Claude가 쓰면 AI slop). 회차를 다시 돌리면 후보가 쌓인다.
- gti는 무조건 gpt-6-astra(멘토 2026-10-09). god-tibo-imagen 스킬 스크립트로 불러 모델 고정·PNG 검증을 맡긴다.
  Codex ChatGPT 인증으로 도는 비공식 경로라 깨질 수 있다.
- 다시 그리기: python3 image_candidates.py --redraw runs/images/<이름>/<회차>  (설명은 그대로, 그림 없는 것만)
"""
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs" / "images"
# gti는 무조건 gpt-6-astra (멘토 2026-10-09). 전역 npm gti는 기본 gpt-5.4라 400이 나서,
# 모델을 강제하고 PNG를 검증하는 god-tibo-imagen 스킬 스크립트로 부른다.
GEN = str(Path.home() / ".codex" / "skills" / "god-tibo-imagen" / "scripts" / "generate-image.mjs")


def latest(name):
    d = ROOT / "runs" / "columns" / name
    revs = sorted(d.glob("final-r*.md"), key=lambda p: int(p.stem.split("-r")[1]))
    for f in [*reversed(revs), d / "final.md", d / "r4.md", d / "draft.md"]:
        if f.exists():
            return f


def prompt(text):
    return f"""아래 칼럼은 사내 뉴스레터(SK E&S 전 직원 대상) 메일 맨 위에 그림 한 장과 함께 나갑니다.
그 머리 그림의 후보를 그림 설명으로 써 주세요. 설명은 이미지 생성 모델에 그대로 넣습니다.

- 후보끼리 서로 다른 결로
- 글이 실제로 말하는 장면이나 생각에서 출발
- 그림 안에 글자는 넣지 않음

출력: JSON 배열만 주세요. [{{"name": "짧은 이름", "prompt": "이미지 생성 모델에 넣을 설명(영어)"}}]
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
    return f"""아래 칼럼은 사내 뉴스레터(SK E&S 전 직원 대상)에 실립니다. 본문 사이사이에 넣어, 읽는 사람이 글을 더 쉽게 이해하도록 돕는 그림을 3개 골라 그림 설명을 써 주세요. 설명은 이미지 생성 모델에 그대로 넣습니다.

- 그림마다 어느 문단 뒤에 넣을지 [문단 번호]로
- 글이 설명하는 생각·관계·흐름이 한눈에 보이게
- 세 그림은 같은 그림체로
- 그림 안에 글자는 넣지 않음

출력: JSON 배열만 주세요. [{{"after": 문단 번호, "name": "짧은 이름", "prompt": "이미지 생성 모델에 넣을 설명(영어)"}}]
파일을 만들거나 명령을 실행하지 마세요.

=== 칼럼 (문단 번호 붙임) ===
{numbered}"""


def run_inline(target):
    f = (ROOT / target).resolve() if target.endswith(".md") else latest(target)
    name = Path(target).stem if target.endswith(".md") else target
    d = OUT / name / ("inline-" + time.strftime("%Y%m%d-%H%M%S"))
    d.mkdir(parents=True, exist_ok=True)
    paras = paragraphs(f.read_text(encoding="utf-8"))
    p = inline_prompt(paras)
    (d / "prompt.md").write_text(p, encoding="utf-8")
    (d / "source.txt").write_text(str(f.relative_to(ROOT)), encoding="utf-8")
    out = d / "astra.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), p],
                       cwd=d, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    raw = out.read_text(encoding="utf-8") if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0)) if m else []
    for it in items:
        k = int(it.get("after", 0))
        it["after"] = k
        it["anchor"] = paras[k - 1][:40] if 1 <= k <= len(paras) else ""  # 과정이 바뀌어도 자리를 찾게 문단 첫머리를 함께 둔다
    (d / "astra.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    paint(d, items)


def draw(d, i, it):
    png = d / f"{i:02d}.png"
    with open(d / f"{i:02d}.log", "w", encoding="utf-8") as log:
        # 본문 그림은 16:9(astra가 설명에 와이드로 쓰고 그림 서버도 그 비율로 그린다 — 3:2 검사에 걸려 전부 버려졌다, 2026-10-10)
        size, ratio, tol = ("2048x1152", "16:9", "0.05") if d.name.startswith("inline-") else ("1536x1024", "3:2", "0.2")
        subprocess.run(["node", GEN, "--prompt", it["prompt"], "--output", str(png), "--size", size, "--ratio", ratio,
                        "--tolerance", tol, "--model", "gpt-6-astra"],
                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=900)
    return png.exists()


def run(target):
    f = (ROOT / target).resolve() if target.endswith(".md") else latest(target)
    name = Path(target).stem if target.endswith(".md") else target
    d = OUT / name / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    p = prompt(f.read_text(encoding="utf-8"))
    (d / "prompt.md").write_text(p, encoding="utf-8")
    (d / "source.txt").write_text(str(f.relative_to(ROOT)), encoding="utf-8")
    out = d / "astra.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), p],
                       cwd=d, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    raw = out.read_text(encoding="utf-8") if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0)) if m else []
    (d / "astra.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    paint(d, items)


def paint(d, items):
    todo = [(i, it) for i, it in enumerate(items, 1) if not (d / f"{i:02d}.png").exists()]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda a: draw(d, *a), todo))
    ok = sum(1 for i in range(1, len(items) + 1) if (d / f"{i:02d}.png").exists())
    print(f"그림 후보 {ok}/{len(items)} → {d.relative_to(ROOT)}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--inline"]:
        run_inline(a[1])
    elif a[:1] == ["--redraw"]:
        d = (ROOT / a[1]).resolve()
        paint(d, json.loads((d / "astra.json").read_text(encoding="utf-8")))
    else:
        run(a[0])
