"""확정본 방식 칼럼 파이프라인 — 설정 파일(briefs/*.json)대로 초안 → 재작성 → 기준 반영을 돌린다.

사용: python3 column_pipeline.py briefs/t1-A.json briefs/t1-B.json ...
단계 (확정본 「AI를 쓰는데도 퇴근 시간이 그대로인 이유」와 같은 절차):
  1. 초안   — Claude(claude -p, 빈 폴더): 원문 통째 + 경영일기 3편(p747·p724·p740) 문체 참고 + 지킬 것 2개
  2. 재작성 — astra(codex exec): "경영일기 필자가 이 원고를 직접 썼다면" (참고 2편은 설정의 r4_refs, 없으면 p724·p669 — 2026-10-09 멘토 선택)
  3. 기준   — astra: briefs/standing-feedback.md(멘토 피드백 원문)를 반영해 고침
결과: runs/columns/<topic>-<variant>/{draft,r4,final}.md (+ 각 단계 지시문·로그)
설정: thesis(이 글이 말할 것) · sources([[경로, 설명], ...] 첫째가 중심 재료) · r4_refs · draft_from(초안을 다른 갈래와 공유)
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
RUNS = ROOT / "runs" / "columns"
DRAFT_REFS = ["p747", "p724", "p740"]
READER = ("SK E&S 전 직원에게 메일로 가는 사내 뉴스레터입니다. 대부분 개발자가 아닌 사무·현장 직군이고, "
          "AI를 써 봤지만 효과가 애매하다고 느끼는 사람이 많습니다.")
OUT_RULE = "출력: 제목과 본문만 주세요. 파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요."


def body(path):
    t = Path(path).read_text(encoding="utf-8")
    if t.startswith("---"):
        t = t.split("---", 2)[2]
    return t.split("*주변 동료에게")[0].strip()


def ref(k):
    # "(끝)"은 경영일기 필자의 맺음 표시 — 우리 글에 따라 붙지 않게 참고 글에서부터 뺀다 (2026-10-09 멘토)
    t = body(SRC / "originals" / "infuture" / f"{k}.md").replace("(끝)", "").rstrip()
    return f"=== 유정식의 경영일기 {k} ===\n" + t


def draft_prompt(b):
    parts = [
        "사내 뉴스레터에 실을 칼럼 한 편을 써 주세요. 제목도 붙여 주세요.",
        f"독자: {READER}",
        f"이 글이 말할 것: {b['thesis']}",
        "아래 [원문 1]이 이 글의 중심 재료입니다. 끝까지 읽고, 그 안의 장면과 말을 재료로 삼아 깊게 풀어 주세요. "
        "[원문 2] 이후는 보조 재료입니다.",
        "쓰는 방식은 아래 [문체 참고]의 필자(경영 컨설턴트 유정식)가 쓰듯이 써 주세요. 장면이나 질문으로 열고, 재료 하나를 깊게 풀고, "
        "필자의 생각을 분명하게 말하고 맺는 흐름입니다. 분량도 그 글들 정도면 됩니다. [문체 참고] 글들의 내용이나 사례는 가져오지 마세요.",
        "지킬 것은 두 가지입니다.\n1. 원문의 문장을 그대로 옮기지 않습니다. 이야기와 사실만 가져와 내 말로 씁니다.\n"
        "2. 원문에 없는 사실·수치·경험을 지어내지 않습니다.",
        OUT_RULE,
    ]
    for i, (p, d) in enumerate(b["sources"], 1):
        parts.append(f"=== [원문 {i}] {d} ===\n" + body(SRC / p))
    for k in DRAFT_REFS:
        parts.append("[문체 참고] " + ref(k))
    return "\n\n".join(parts)


def r4_prompt(b, draft):
    parts = [
        "아래 [원고]를 [참고] 글의 필자(경영 컨설턴트 유정식)가 자기 뉴스레터에 직접 썼다면 어떻게 썼을지 상상하며 다시 써 주세요.",
        "원고의 논리 전개와 사실은 그대로 두고, 문장과 이어 가는 방식만 [참고] 필자처럼 바꿉니다. [참고] 글의 내용이나 사례는 가져오지 않습니다.",
    ]
    parts += ["[참고] " + ref(k) for k in b.get("r4_refs", ["p724", "p669"])]
    parts += [OUT_RULE + " 원고에 없는 사실·수치·경험은 더하지 마세요.", "=== 원고 ===\n" + draft]
    return "\n\n".join(parts)


def fb_prompt(text):
    fb = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8")
    return "\n\n".join([
        "아래 [원고]는 우리 사내 뉴스레터의 기준 방식으로 쓴 글입니다. 글의 흐름·문체·논리는 그대로 두고, 아래 [멘토 피드백]을 반영해 고쳐 주세요. "
        "원고에 없는 사실·수치·경험은 더하지 마세요.",
        fb, OUT_RULE, "=== [원고] ===\n" + text])


def run_claude(d, prompt):
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    r = subprocess.run(["claude", "-p", "--model", "opus", "--tools", "", "--strict-mcp-config",
                        "--no-session-persistence", prompt], cwd=d, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True)
    (d / "run.log").write_text(r.stderr, encoding="utf-8")
    return r.stdout.strip()


def run_astra(d, prompt):
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    out = d / "output.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), prompt],
                       cwd=d, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    return out.read_text(encoding="utf-8").strip() if out.exists() else ""


def stage(name, jobs):
    t = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda j: j(), jobs))
    print(f"[{name}] {len(jobs)}건 {time.time() - t:.0f}s · 빈 결과 {sum(1 for r in res if not r)}건", flush=True)
    return res


def main(paths):
    briefs = {Path(p).stem: json.loads(Path(p).read_text(encoding="utf-8")) for p in paths}
    for k, b in briefs.items():
        b["dir"] = RUNS / k
    # 1. 초안 (thesis가 있는 갈래만, 나머지는 draft_from을 공유)
    own = [k for k, b in briefs.items() if "thesis" in b]

    def mk_draft(k):
        b = briefs[k]
        f = b["dir"] / "draft.md"
        if f.exists() and f.stat().st_size > 200:
            return f.read_text(encoding="utf-8")
        t = run_claude(b["dir"] / "_draft", draft_prompt(b))
        f.write_text(t, encoding="utf-8")
        return t
    stage("초안·Claude", [lambda k=k: mk_draft(k) for k in own])

    def draft_of(k):
        b = briefs[k]
        src = briefs.get(b.get("draft_from"), b) if b.get("draft_from") else b
        return (src["dir"] / "draft.md").read_text(encoding="utf-8")

    # 2. 재작성
    def mk_r4(k):
        b = briefs[k]
        t = run_astra(b["dir"] / "_r4", r4_prompt(b, draft_of(k)))
        (b["dir"] / "r4.md").write_text(t, encoding="utf-8")
        return t
    stage("재작성·astra", [lambda k=k: mk_r4(k) for k in briefs])

    # 3. 기준 반영
    def mk_final(k):
        b = briefs[k]
        t = run_astra(b["dir"] / "_final", fb_prompt((b["dir"] / "r4.md").read_text(encoding="utf-8")))
        (b["dir"] / "final.md").write_text(t, encoding="utf-8")
        meta = {kk: vv for kk, vv in b.items() if kk != "dir"}
        if b.get("draft_from"):
            meta["thesis"] = briefs[b["draft_from"]].get("thesis")
            meta["sources"] = briefs[b["draft_from"]].get("sources")
        (b["dir"] / "brief.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        return t
    stage("기준 반영·astra", [lambda k=k: mk_final(k) for k in briefs])


if __name__ == "__main__":
    main(sys.argv[1:])
