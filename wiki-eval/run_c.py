"""C(위키) 시험 실행기 — astra가 wiki/ 안에서만 쓰기 가능한 샌드박스로 넣기·정리·후보 내기를 한다.

사용: python3 wiki-eval/run_c.py ingest A|B   — phases.json의 원문을 6편씩 차례로 넣고 묶음마다 커밋
      python3 wiki-eval/run_c.py lint
      python3 wiki-eval/run_c.py query        — wiki-eval/C.json (주제 후보, 파일 쓰지 않음)
기록: wiki-eval/timing.json (단계별 걸린 시간)
"""
import json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
EVAL = ROOT / "wiki-eval"
TODAY = "2026-10-10"


def astra(prompt, write=True, out=None):
    cmd = ["codex", "exec", "-m", "gpt-6-astra", "-C", str(WIKI), "--skip-git-repo-check",
           "-s", "workspace-write" if write else "read-only", "--ephemeral", "--color", "never"]
    if out:
        cmd += ["-o", str(out)]
    t = time.time()
    r = subprocess.run(cmd + ["-"], input=prompt, text=True, capture_output=True, cwd=WIKI)
    return round(time.time() - t), r.stdout[-3000:] + r.stderr[-2000:]


def record(step, sec, note=""):
    f = EVAL / "timing.json"
    rows = json.loads(f.read_text()) if f.exists() else []
    rows.append({"step": step, "sec": sec, "note": note})
    f.write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def commit(msg):
    subprocess.run(["git", "add", "-A", "wiki", "wiki-eval"], cwd=ROOT)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT)


def ingest(phase):
    paths = json.loads((EVAL / "phases.json").read_text())[phase]
    for k in range(0, len(paths), 6):
        batch = paths[k:k + 6]
        p = (f"AGENTS.md를 먼저 읽고 그 규칙대로, 아래 원문을 적힌 순서대로 하나씩 넣어(ingest) 주세요. 오늘 날짜는 {TODAY}입니다.\n"
             + "\n".join(f"- ../sources/{x}" for x in batch)
             + "\n끝나면 원문마다 처리(합침/새 주제/보탬 없음)와 주제 페이지를 한 줄씩 답해 주세요.")
        sec, log = astra(p)
        (EVAL / f"log-ingest-{phase}-{k // 6 + 1}.txt").write_text(log)
        record(f"ingest {phase}-{k // 6 + 1}", sec, f"{len(batch)}편")
        commit(f"wiki ingest {phase}-{k // 6 + 1} ({len(batch)}편, {sec}s)")
        print(f"ingest {phase}-{k // 6 + 1}: {len(batch)}편 {sec}s", flush=True)


def lint():
    p = f"AGENTS.md를 먼저 읽고 그 규칙의 '정리(lint)'를 해 주세요. 오늘 날짜는 {TODAY}입니다. 끝나면 합친 것과 보고할 것을 답해 주세요."
    sec, log = astra(p)
    (EVAL / "log-lint.txt").write_text(log)
    record("lint", sec)
    commit(f"wiki lint ({sec}s)")
    print(f"lint {sec}s", flush=True)


def query():
    out = EVAL / "C-raw.md"
    p = ("AGENTS.md를 먼저 읽고 그 규칙의 '주제 후보 내기(query)'를 해 주세요. 파일은 만들거나 고치지 마세요.\n"
         "출력: JSON 배열만. [{\"name\": \"주제 이름\", \"thesis\": \"이 글이 말할 것 한두 문장\", "
         "\"sources\": [\"originals/<사이트>/NN.md\", ...]}] — sources는 중심 원문을 맨 앞에, 경로는 sources/ 아래 기준(originals/로 시작).")
    sec, log = astra(p, write=False, out=out)
    raw = out.read_text() if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0)) if m else []
    (EVAL / "C.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    record("query", sec, f"{len(items)}개")
    commit(f"wiki query ({len(items)}개, {sec}s)")
    print(f"query {len(items)}개 {sec}s", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"ingest": lambda: ingest(a[1]), "lint": lint, "query": query}[a[0]]()
