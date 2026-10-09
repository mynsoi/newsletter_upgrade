"""B(지금 방식 + 기억) 시험 — topic_candidates.py와 같은 지시에 '이미 낸 주제·이미 쓴 글과 겹치지 않게'만 더한다.

사용: python3 wiki-eval/run_b.py B2   — 원문 22편 + 기억(1회차 = runs/topics/20261009-200958)
      python3 wiki-eval/run_b.py B3   — 원문 40편 + 기억(1회차 + B2)
결과: wiki-eval/B2.json, B3.json · 걸린 시간은 timing.json
"""
import json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import topic_candidates as tc

EVAL = ROOT / "wiki-eval"
WRITTEN = [("AI를 쓰는데도 퇴근 시간이 그대로인 이유", "AI로 빨라졌는데 퇴근이 그대로인 건 확인 부담·기대치·속도 차이 때문이고, 아낀 시간의 용도를 정해야 한다."),
           ("작은 반복부터 덜어내기", "AI 활용의 첫 성과는 매주 반복하는 작은 일에서 만들 수 있다.")]


def memory_block(rounds):
    seen = "\n".join(f"- {t['name']}: {t['thesis']}" for r in rounds for t in r)
    done = "\n".join(f"- 「{a}」: {b}" for a, b in WRITTEN)
    return (f"\n\n[이미 낸 주제]\n{seen}\n\n[이미 쓴 글]\n{done}\n\n"
            "위 주제·글과 같은 논지는 다시 내지 마세요. 새 원문으로 달라진 점이 분명할 때만 다른 각도로 내세요.")


def run(name):
    phases = json.loads((EVAL / "phases.json").read_text())
    pool = phases["A"] if name == "B2" else phases["A"] + phases["B"]
    files = [ROOT / "sources" / p for p in pool]
    rounds = [json.loads((ROOT / "runs/topics/20261009-200958/astra.json").read_text())]
    if name == "B3":
        rounds.append(json.loads((EVAL / "B2.json").read_text()))
    p = tc.prompt(files).replace("\n파일을 만들거나 명령을 실행하지 마세요.", memory_block(rounds) + "\n파일을 만들거나 명령을 실행하지 마세요.", 1)
    d = EVAL / f"_{name}"
    d.mkdir(exist_ok=True)
    (d / "prompt.md").write_text(p)
    t = time.time()
    subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                    "--ephemeral", "--color", "never", "-o", str(d / "astra.md"), "-"], input=p, text=True, capture_output=True, cwd=d)
    sec = round(time.time() - t)
    raw = (d / "astra.md").read_text() if (d / "astra.md").exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0)) if m else []
    known = {str(f.relative_to(ROOT / "sources")) for f in files}
    for it in items:
        it["sources"] = [s for s in it.get("sources", []) if s in known]
    (EVAL / f"{name}.json").write_text(json.dumps([i for i in items if i["sources"]], ensure_ascii=False, indent=1))
    f = EVAL / "timing-b.json"
    rows = json.loads(f.read_text()) if f.exists() else []
    rows.append({"step": name, "sec": sec, "note": f"{len(items)}개"})
    f.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"{name}: {len(items)}개 {sec}s", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
