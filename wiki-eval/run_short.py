"""직원 인사이트를 한 줄로 줄인다 — 읽기 좋게 (2026-10-11, 멘토: "가독성있게좀 보여줘라 드럽게 읽기 힘드네")

새로 쓰지 않고, astra가 이미 쓴 빌려 올 점·인사이트를 짧게 줄이기만 한다. 결과: <insight 폴더>/short.json
사용: python3 -I wiki-eval/run_short.py runs/topic-full/20261011-full/insight/<시각>
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wiki-eval"))
import run_full as F  # noqa: E402


def prompt(f):
    return "\n\n".join([
        "아래 [인사이트]와 [빌려 올 점]을 짧게 줄여 주세요. 새 내용을 더하지 말고, 있는 내용만 줄입니다. 말끝은 '~다'나 명사로 끝내도 됩니다.",
        "출력 형식(이 두 줄만):\n사례 한 줄: <원문 속 사람이 한 일, 30자 안팎>\n인사이트 한 줄: <직원에게 주는 인사이트, 40자 안팎>",
        "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.",
        f"[빌려 올 점]\n{f['빌려 올 점']}\n\n[인사이트]\n{f['인사이트']}",
    ])


def one(k, f, run):
    d = run / k.replace("/", "-") / "short"
    text = ""
    for _ in range(2):
        text = F.astra(d, prompt(f))
        if text:
            break
    return k, {m.group(1): m.group(2).strip() for m in re.finditer(r"^(사례 한 줄|인사이트 한 줄):\s*(.+)$", text, re.M)}


if __name__ == "__main__":
    run = ROOT / sys.argv[1]
    ins = json.loads((run / "insight.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(ex.map(lambda kv: one(kv[0], kv[1], run), ins.items()))
    (run / "short.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, "|", v.get("사례 한 줄"), "→", v.get("인사이트 한 줄"))
