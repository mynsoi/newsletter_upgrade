"""주제를 경영일기 필자의 목소리로 — 작은 시험 (2026-10-10, 멘토: "말을 한국말인데 한국인이 못알아듣게 적기위해서 노력한 느낌")

금지 목록을 쌓는 대신 R4 방식(멘토가 만족한 방식)을 주제에 쓴다: astra에게 경영일기 글을 문체 참고로 주고
"이 필자가 이 원문을 읽고 '이번엔 이 얘기를 써 보자'고 한다면" 주제 이름·논지·이 글만의 것을 말하게 한다.
원문마다 서로 독립이라 동시에 돌린다(위키에 넣지 않음 — 결과만 runs/topic-voice/<시각>/).
사용: python3 -I wiki-eval/run_voice.py originals/threads/05.md originals/linkedin/02.md ...
"""
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import column_pipeline as C  # noqa: E402  body()·ref()·READER를 같이 쓴다

CODEX = shutil.which("codex") or "codex"
REFS = ["p724", "p669"]  # 재작성(R4) 기본 참고 글과 같은 것


def prompt(src):
    return "\n\n".join([
        "아래 [참고] 두 편은 경영 컨설턴트 유정식이 자기 뉴스레터 「유정식의 경영일기」에 쓴 칼럼입니다. "
        "이 필자가 아래 [원문]을 읽고, 사내 뉴스레터 편집 회의에서 \"이번엔 이 얘기를 써 보자\"고 제안한다고 상상해 주세요.",
        f"사내 뉴스레터 독자: {C.READER}",
        "필자라면 이 원문에서 무엇을 우리 직원들에게 할 이야기로 골라낼지, 필자의 말투 그대로 답해 주세요. 원문이 가장 하고 싶은 말을 붙잡고, 사소한 세부에 매달리지 않습니다. "
        "원문 속 사람이 프리랜서·개인이어도, 이야기는 회사에서 팀으로 일하는 독자의 것으로 옮겨 말합니다.",
        "지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다. [참고] 글의 내용이나 사례는 가져오지 않습니다.",
        "출력 형식(이 세 줄 머리만 쓰고 다른 설명은 붙이지 마세요):\n"
        "주제: <필자가 붙일 법한 칼럼 제목>\n"
        "이 글이 말할 것: <필자가 편집 회의에서 동료에게 말하듯 두세 문장>\n"
        "이 글만의 것: <원문이 가장 하고 싶은 말, 그리고 그것을 받치는 원문의 장면이나 사실 한두 개>",
        "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.",
        *["[참고] " + C.ref(k) for k in REFS],
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
    out = ROOT / "runs" / "topic-voice" / time.strftime("%Y%m%d-%H%M%S")
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda s: run(s, out), sys.argv[1:]))
    (out / "all.md").write_text("\n\n".join(f"## {s}\n\n{o}" for s, o in res), encoding="utf-8")
    print(out)
