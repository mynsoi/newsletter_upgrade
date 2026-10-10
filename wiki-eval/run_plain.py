"""주제 카드에서 제목을 뺀다 — 원문에서 있었던 일 + 글쓴이가 하는 말 (2026-10-10)

멘토: "왜 다 물어보는 투야..? 야 너 생각안하고 행동할래 계속?"
주제 지도가 제목까지 지으려 해서 회차마다 다른 모양으로 어긋났다(권고형 → 사례 요약형 → 수수께끼형 → 번역체 → 질문형).
제목은 글을 고른 뒤 제목 단계(astra 후보 + 멘토 메시지)에서만 짓는다. 주제 카드는 무엇에 대한 이야기인지만 평서문으로.
1회차(20261010-234717)의 "할 말(우리 직원이 가져갈 것)"은 'AI를 잘 쓰려면 ~해야 한다' 일반론으로 뭉개져 "글쓴이가 하는 말"로 바꿨다.
사용: python3 -I wiki-eval/run_plain.py originals/threads/05.md ... → runs/topic-plain/<시각>/
"""
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import column_pipeline as C  # noqa: E402

CODEX = shutil.which("codex") or "codex"


def prompt(src):
    return "\n\n".join([
        "아래 [원문]을 재료로 사내 뉴스레터(SK E&S 직원 대상, 대부분 개발자가 아닌 사무·현장 직군) 칼럼을 한 편 쓰려고 합니다. "
        "제목은 나중에 따로 정합니다. 지금은 이 원문으로 무슨 이야기를 할 수 있는지만 정리해 주세요.",
        "출력 형식(이 두 줄 머리만 쓰고 다른 설명은 붙이지 마세요):\n"
        "있었던 일: <원문 속 사람이 실제로 겪거나 한 일. 사실과 숫자는 원문에 있는 그대로, 두세 문장>\n"
        "글쓴이가 하는 말: <원문 글쓴이가 가장 하고 싶은 주장을 우리말 한두 문장으로. 일반적인 교훈으로 바꾸지 않고 글쓴이의 주장 그대로>\n"
        "말끝은 모두 '~다'로 맞춥니다.",
        "지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다. "
        "원문이 가장 하고 싶은 말을 붙잡고, 사소한 세부에 매달리지 않습니다.",
        "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.",
        "=== [원문] ===\n" + C.body(ROOT / "sources" / src),
    ])


def run(src, out):
    d = out / Path(src).parent.name / Path(src).stem
    d.mkdir(parents=True, exist_ok=True)
    p = prompt(src)
    (d / "prompt.md").write_text(p, encoding="utf-8")
    t = time.time()
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(d / "output.md"), "-"],
                       cwd=d, input=p, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    ok = (d / "output.md").exists()
    print(f"{src} · {time.time() - t:.0f}s · {'ok' if ok else '실패'}", flush=True)
    return src, (d / "output.md").read_text(encoding="utf-8").strip() if ok else ""


if __name__ == "__main__":
    out = ROOT / "runs" / "topic-plain" / time.strftime("%Y%m%d-%H%M%S")
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda s: run(s, out), sys.argv[1:]))
    (out / "all.md").write_text("\n\n".join(f"## {s}\n\n{o}" for s, o in res), encoding="utf-8")
    print(out)
