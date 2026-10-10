"""주제 위키 — 원문을 주제 지도(wiki/)로 쌓는다 (2026-10-10 시험 뒤 채택, docs/2026-10-10-주제-위키-시험.md).

사용: python3 scripts/wiki.py --ingest [원문 경로...]   — 경로가 없으면 아직 안 넣은 원문 전부(경영일기 제외)
      python3 scripts/wiki.py --lint                   — 정리: 같은 논지 합치기·점검 보고
      python3 scripts/wiki.py --claim <주제 페이지>      — 고르자마자: 페이지의 논지·원문으로 briefs/w-<시각>.json을 바로 만든다(LLM 없음)
      python3 scripts/wiki.py --brief <주제 페이지> [글]  — 고를 때 깊게 읽기: 그 주제 원문만 읽고 설정의 논지·원문 순서를 다듬는다
      python3 scripts/wiki.py --status                 — 넣은 원문 수·남은 원문
- astra는 wiki/ 안에서만 쓰기 가능한 샌드박스로 돈다(원문 폴더는 읽기만 — 실행 환경이 막는다).
- 넣은 원문은 wiki/log.md의 "- ingest <경로>" 줄로 센다. 따로 상태 파일을 두지 않는다.
- 넣기·정리가 끝날 때마다 wiki/만 git에 커밋해 위키가 어떻게 바뀌었는지 기록으로 남긴다.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
SRC = ROOT / "sources"
STYLE_ONLY = {"infuture"}
BATCH = 6
# Windows에선 npm이 깐 codex가 codex.cmd라 이름만으로는 못 찾는다 — 전체 경로로 (리눅스는 그대로)
CODEX = shutil.which("codex") or "codex"


def astra(prompt, write=True, out=None):
    cmd = [CODEX, "exec", "-m", "gpt-6-astra", "-C", str(WIKI), "--skip-git-repo-check",
           "-s", "workspace-write" if write else "read-only", "--ephemeral", "--color", "never"]
    if out:
        cmd += ["-o", str(out)]
    sys.stdout.flush()
    r = subprocess.run(cmd + ["-"], input=prompt, text=True, encoding="utf-8", cwd=WIKI)  # 출력은 작업 로그로 그대로 — 화면에서 진행이 보이게
    return r.returncode


def commit(msg):
    subprocess.run(["git", "add", "-A", "wiki"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", msg, "--", "wiki"], cwd=ROOT, capture_output=True)


def processed():
    log = (WIKI / "log.md").read_text(encoding="utf-8") if (WIKI / "log.md").exists() else ""
    return set(re.findall(r"^- ingest \.\./sources/(originals/\S+?\.md)", log, re.M))


def backlog():
    done = processed()
    rows = []
    for f in sorted((SRC / "originals").glob("*/[0-9]*.md")):
        rel = f.relative_to(SRC).as_posix()
        if f.parent.name not in STYLE_ONLY and rel not in done:
            rows.append(rel)
    return rows


def ingest(paths):
    paths = paths or backlog()
    today = date.today().isoformat()
    for k in range(0, len(paths), BATCH):
        batch = paths[k:k + BATCH]
        p = (f"AGENTS.md를 먼저 읽고 그 규칙대로, 아래 원문을 적힌 순서대로 하나씩 넣어(ingest) 주세요. 오늘 날짜는 {today}입니다.\n"
             + "\n".join(f"- ../sources/{x}" for x in batch)
             + "\n끝나면 원문마다 처리(합침/새 주제/보탬 없음)와 주제 페이지를 한 줄씩 답해 주세요.")
        t = time.time()
        astra(p)
        left = [x for x in batch if x not in processed()]
        commit(f"wiki 넣기 {len(batch) - len(left)}/{len(batch)}편 ({time.time() - t:.0f}s)")
        print(f"넣기 {len(batch) - len(left)}/{len(batch)}편 · {time.time() - t:.0f}s" + (f" · 못 넣음 {left}" if left else ""), flush=True)
    print(f"남은 원문 {len(backlog())}편")


def lint():
    t = time.time()
    astra(f"AGENTS.md를 먼저 읽고 그 규칙의 '정리(lint)'를 해 주세요. 오늘 날짜는 {date.today().isoformat()}입니다. 끝나면 합친 것과 보고할 것을 답해 주세요.")
    commit(f"wiki 정리 ({time.time() - t:.0f}s)")
    print(f"정리 {time.time() - t:.0f}s")


def front(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1), text[m.end():]) if m else ("", text)


def set_front(page, **kv):
    """주제 페이지 머리말의 status·used_in만 바꾼다(나머지는 그대로)."""
    t = page.read_text(encoding="utf-8")
    head, body = front(t)
    for k, v in kv.items():
        line = f"{k}: {v}"
        head = re.sub(rf"^{k}:.*$", line, head, flags=re.M) if re.search(rf"^{k}:", head, re.M) else head + "\n" + line
    page.write_text(f"---\n{head}\n---\n{body}", encoding="utf-8")


def used_in(page):
    m = re.search(r"^used_in:\s*\[(.*)\]", front(page.read_text(encoding="utf-8"))[0], re.M)
    return [x.strip().strip("'\"") for x in (m.group(1).split(",") if m else []) if x.strip()]


def label(rel):
    t = (SRC / rel).read_text(encoding="utf-8")
    m = dict(re.findall(r"^(\w+): (.*)$", t.split("---", 2)[1], re.M)) if t.startswith("---") else {}
    site = {"threads": "Threads", "linkedin": "LinkedIn"}.get(rel.split("/")[1], rel.split("/")[1])
    who = (m.get("headline") or m.get("author") or "").strip("'\"")
    return ", ".join(x for x in [site, who, m.get("date", "").strip("'\"")] if x)


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def page_of(page_rel):
    rel = page_rel[5:] if page_rel.startswith("wiki/") else page_rel
    page = (WIKI / rel).resolve()
    if WIKI.resolve() not in page.parents or not page.is_file():
        sys.exit("주제 페이지 없음: " + page_rel)
    return page


def claim(page_rel):
    """고르자마자 — 페이지의 이름·논지·원문 목록으로 설정을 바로 만들고 페이지에 표시한다(LLM 없이, 1초 안)."""
    page = page_of(page_rel)
    head, body = front(page.read_text(encoding="utf-8"))
    title = (re.search(r"^title:\s*(.+)$", head, re.M) or [None, page.stem])[1].strip().strip("'\"")
    sec = sections(body)
    srcs = list(dict.fromkeys(re.findall(r"\]\(\.\./\.\./sources/(originals/[^)]+?\.md)\)", sec.get("원문", ""))))
    srcs = [x for x in srcs if (SRC / x).is_file()]
    k = "w-" + time.strftime("%Y%m%d-%H%M%S")
    b = {"topic": k, "label": title, "thesis": sec.get("이 글이 말할 것", ""), "sources": [[x, label(x)] for x in srcs],
         "from_wiki": page.relative_to(ROOT).as_posix()}
    (ROOT / "briefs" / f"{k}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    ui = used_in(page) + [f"briefs/{k}.json"]
    was = re.search(r"^status:\s*(\S+)", head, re.M)
    # 이미 쓴 주제를 다시 고르면(다시 쓰기) '씀'은 그대로 둔다 — 칼럼이 이미 있으니까
    set_front(page, status="씀" if was and was.group(1) == "씀" else "진행 중", used_in="[" + ", ".join(ui) + "]")
    commit(f"wiki: '{title}' 고름 → briefs/{k}.json")
    return k


def brief(page_rel, k=None):
    page = page_of(page_rel)
    k = k or claim(page_rel)
    d = ROOT / "runs" / "wiki" / k
    d.mkdir(parents=True, exist_ok=True)
    p = (f"AGENTS.md를 먼저 읽고 그 규칙의 '고를 때 깊게 읽기'를 해 주세요. 고른 주제 페이지: {page.relative_to(WIKI).as_posix()}\n"
         "파일은 만들거나 고치지 마세요.\n"
         "출력: JSON 하나만. {\"name\": \"짧은 이름\", \"thesis\": \"이 글이 말할 것 한두 문장\", "
         "\"sources\": [\"originals/<사이트>/NN.md\", ...]} — sources는 중심 원문을 맨 앞에, 경로는 sources/ 아래 기준(originals/로 시작).")
    (d / "prompt.md").write_text(p, encoding="utf-8")
    astra(p, write=False, out=d / "astra.md")
    raw = (d / "astra.md").read_text(encoding="utf-8") if (d / "astra.md").exists() else ""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        sys.exit("깊게 읽기 결과가 비었음 — " + str(d / "astra.md"))
    it = json.loads(m.group(0))
    srcs = [s for s in it.get("sources", []) if (SRC / s).is_file() and s.split("/")[1] not in STYLE_ONLY]
    if not srcs:
        sys.exit("원문 경로가 하나도 맞지 않음")
    bp = ROOT / "briefs" / f"{k}.json"
    b = json.loads(bp.read_text(encoding="utf-8"))
    if b.get("title"):  # 그새 제목을 골랐으면 설정을 건드리지 않는다
        print(k)
        return
    b.update({"label": it["name"], "thesis": it["thesis"], "sources": [[s, label(s)] for s in srcs], "deep_read": True})
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(k)


def mark_written(page_rel, column_rel):
    """확정 — 주제 페이지에 '씀'과 칼럼 파일을 적는다."""
    page = WIKI / page_rel if not page_rel.startswith("wiki/") else ROOT / page_rel
    if page.is_file():
        ui = used_in(page) + [column_rel]
        set_front(page, status="씀", used_in="[" + ", ".join(dict.fromkeys(ui)) + "]")
        commit(f"wiki: 확정 표시 {column_rel}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--ingest"]:
        ingest(a[1:])
    elif a[:1] == ["--lint"]:
        lint()
    elif a[:1] == ["--claim"]:
        print(claim(a[1]))
    elif a[:1] == ["--brief"]:
        brief(a[1], a[2] if len(a) > 2 else None)
    elif a[:1] == ["--written"]:
        mark_written(a[1], a[2])
    else:
        print(f"넣은 원문 {len(processed())}편 · 남은 원문 {len(backlog())}편", *backlog()[:20], sep="\n")
