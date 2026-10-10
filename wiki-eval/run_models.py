"""같은 프롬프트로 모델만 바꿔 주제 제목을 뽑는다 — astra · sol · luna (2026-10-10, 멘토: "너무 ai 번역체임")

지금까지는 astra 프롬프트 규칙만 바꿔 왔다(권고형 → 사례 요약형 → 수수께끼형 → 경영일기 역할극). 이번엔 모델을 바꾼다.
프롬프트에서 뺀 것: 회사 장면 강제(원문에 없던 "팀"을 끼워 넣음), 편집 회의 역할극("~써보죠"·"~지 않겠습니까?").
기준은 금지 목록이 아니라 멘토 판정 파일(wiki-eval/title-verdicts.md) + 사람이 쓴 칼럼 제목(경영일기 60개).
원문·모델마다 독립이라 동시에 돌린다. 위키에는 넣지 않는다. 결과: runs/topic-models/<시각>/ (갈래 이름은 가·나·다로 가림 — mapping.json)
사용: python3 -I wiki-eval/run_models.py originals/threads/05.md ...
"""
import json
import random
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import column_pipeline as C  # noqa: E402
import title_candidates as T  # noqa: E402

CODEX = shutil.which("codex") or "codex"
MODELS = ["gpt-6-astra", "gpt-6.1-sol", "gpt-6-luna"]
VERDICTS = (ROOT / "wiki-eval" / "title-verdicts.md").read_text(encoding="utf-8")


def prompt(src):
    refs = "\n".join(f"- {t}" for t in T.ref_titles(60))
    return "\n\n".join([
        "아래 [원문]을 재료로 사내 뉴스레터(SK E&S 직원 대상, 대부분 개발자가 아닌 사무·현장 직군) 칼럼을 한 편 쓰려고 합니다. "
        "이 원문으로 쓸 칼럼의 주제를 정해 주세요.",
        "[멘토 판정]은 이 뉴스레터 멘토가 지금까지 주제 제목을 보고 내린 판정과 그때 한 말입니다. 이 판정을 보고 결을 맞춰 주세요. "
        "[사람이 쓴 칼럼 제목]은 결을 참고할 실제 칼럼 제목들입니다. 그대로 가져오지는 마세요.",
        "지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다.",
        "출력 형식(이 세 줄 머리만 쓰고 다른 설명은 붙이지 마세요):\n"
        "주제: <칼럼 제목>\n"
        "이 글이 말할 것: <한두 문장>\n"
        "이 글만의 것: <원문이 가장 하고 싶은 말, 그리고 그것을 받치는 원문의 장면이나 사실 한두 개>",
        "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.",
        "[멘토 판정]\n" + VERDICTS,
        "[사람이 쓴 칼럼 제목]\n" + refs,
        "=== [원문] ===\n" + C.body(ROOT / "sources" / src),
    ])


def run(model, src, out):
    d = out / model / Path(src).parent.name / Path(src).stem
    d.mkdir(parents=True, exist_ok=True)
    p = prompt(src)
    (d / "prompt.md").write_text(p, encoding="utf-8")
    t = time.time()
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", model, "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(d / "output.md"), "-"],
                       cwd=d, input=p, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    ok = (d / "output.md").exists()
    print(f"{model} {src} · {time.time() - t:.0f}s · {'ok' if ok else '실패'}", flush=True)
    return (d / "output.md").read_text(encoding="utf-8").strip() if ok else ""


if __name__ == "__main__":
    srcs = sys.argv[1:]
    out = ROOT / "runs" / "topic-models" / time.strftime("%Y%m%d-%H%M%S")
    jobs = [(m, s) for m in MODELS for s in srcs]
    with ThreadPoolExecutor(max_workers=9) as ex:
        res = dict(zip(jobs, ex.map(lambda j: run(j[0], j[1], out), jobs)))
    names = MODELS[:]
    random.Random(time.time()).shuffle(names)
    mapping = dict(zip("가나다", names))
    (out / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = []
    for s in srcs:
        lines.append(f"## {s}")
        for k, m in mapping.items():
            title = next((l.split(":", 1)[1].strip() for l in res[(m, s)].splitlines() if l.startswith("주제:")), "(없음)")
            lines.append(f"- {k}: {title}")
    (out / "titles-blind.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "all.md").write_text("\n\n".join(f"## {m} · {s}\n\n{res[(m, s)]}" for m in MODELS for s in srcs), encoding="utf-8")
    print(out)
