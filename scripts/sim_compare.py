"""Claude 중앙 진행(C) vs 고정 스크립트(N) — 오케스트레이션만 비교하는 시뮬레이션.

사용: python3 sim_compare.py N   또는   python3 sim_compare.py C
결과: runs/sim/<N|C>/log.json (단계별 명령·시간·결과, C는 턴별 비용·도구 호출)

시나리오 (두 방식 같은 순서):
  1. 제목 후보 — 설정(briefs/sim-*.json)의 원문 경로 하나가 일부러 틀림(linkedin/4.md, 정답 04.md)
  2. 3번 제목으로 정하고 글 쓰기 — 10분 넘는 단계
  3. 멘토 피드백 반영 — 피드백은 파일로만 전달("출처를 문장에다가 남길 필요 없어 ...")
  4. 질문 "왜 이 원문을 썼고 피드백으로 무엇이 바뀌었나" — C만 답할 수 있음(점수 없음)
  5. aside — 경영일기에서 '팀플레이어'를 다룬 글을 찾아 원문으로 가져오기(번호를 모르는 상태)
N에서 사람이 대신 해 준 일은 개입(intervention)으로 센다.
"""
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = [sys.executable, "-I", "scripts/column_pipeline.py"]
SIM = ROOT / "runs" / "sim"


def sh(cmd, timeout=3600):
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(cmd[2:] if cmd[:2] == PIPE[:2] else cmd), "exit": r.returncode, "sec": round(time.time() - t),
            "out": (r.stdout + r.stderr)[-1500:]}


def run_n():
    log, iv = [], []
    b = "briefs/sim-N.json"
    s = sh(PIPE + ["--titles", b]); s["step"] = "1 제목 후보"; log.append(s)
    if not (ROOT / "runs/titles0/sim-N/astra.md").exists():
        d = json.loads((ROOT / b).read_text(encoding="utf-8"))
        d["sources"][0][0] = "originals/linkedin/04.md"
        (ROOT / b).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        iv.append("1단계: 원문 경로 오류를 사람이 찾아 설정 파일을 고침(4.md → 04.md)")
        s = sh(PIPE + ["--titles", b]); s["step"] = "1 제목 후보(재실행)"; log.append(s)
    s = sh(PIPE + ["--set-title", b, "3"]); s["step"] = "2a 제목 정하기"; log.append(s)
    s = sh(PIPE + [b]); s["step"] = "2b 글 쓰기"; log.append(s)
    fb = SIM / "N-feedback-1.txt"; fb.write_text((SIM / "feedback-1.txt").read_text(encoding="utf-8"), encoding="utf-8")
    s = sh(PIPE + ["--revise", b, str(fb.relative_to(ROOT))]); s["step"] = "3 피드백 반영"; log.append(s)
    log.append({"step": "4 질문", "note": "고정 화면은 답하지 못함 — 대신 설정(한 줄·원문)과 최종본↔피드백 반영본 비교를 보여 줌"})
    iv.append("5단계: '팀플레이어' 글 번호(742)를 사람이 아카이브에서 찾아 넣음")
    s = sh(PIPE + ["--fetch-infuture", "742"]); s["step"] = "5 경영일기 원문 가져오기(번호 742)"; log.append(s)
    return {"mode": "N", "steps": log, "interventions": iv}


SYSTEM = """너는 사내 뉴스레터 칼럼 제작의 진행자다. 작업 폴더는 mentor-lab(git 저장소)이다.
글·제목·그림 설명을 직접 쓰지 않는다. 아래 명령으로만 일을 진행한다.
- 제목 후보(astra): python3 -I scripts/column_pipeline.py --titles <설정 파일>
- 제목 정하기: python3 -I scripts/column_pipeline.py --set-title <설정 파일> <번호 또는 제목>
- 글 쓰기(Claude 초안 → astra 재작성 → astra 기준 반영, 보통 10분 이상 걸림): python3 -I scripts/column_pipeline.py <설정 파일>
- 피드백 반영(astra): python3 -I scripts/column_pipeline.py --revise <설정 파일> <피드백 파일>
- 경영일기 원문 가져오기: python3 -I scripts/column_pipeline.py --fetch-infuture <글 번호>
- 웹 자료 조사가 필요하면 aside-win을 쓸 수 있다(읽기 전용).
지킬 것:
- scripts/, briefs/standing-feedback.md, 지시문 파일은 고치지 않는다.
- 멘토 피드백은 파일 경로만 넘긴다. 내용을 옮겨 적거나 바꾸지 않는다.
- 설정이나 경로에 문제가 있으면 무엇이 문제인지와 고칠 방법을 멘토에게 알린다.
- 결과는 짧게 보고한다."""


def turn(sid, first, msg, log):
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "stream-json", "--verbose",
           "--tools", "Bash,Read,Write,Glob,Grep", "--permission-mode", "bypassPermissions",
           "--append-system-prompt", SYSTEM]
    cmd += ["--session-id", sid] if first else ["--resume", sid]
    cmd += [msg]
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3600)
    tools, res = [], {}
    for line in r.stdout.splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "assistant":
            for c in e["message"].get("content", []):
                if c.get("type") == "tool_use":
                    i = c.get("input", {})
                    tools.append({"tool": c["name"], "cmd": (i.get("command") or i.get("file_path") or i.get("pattern") or "")[:300],
                                  "timeout": i.get("timeout"), "background": i.get("run_in_background")})
        if e.get("type") == "result":
            res = {k: e.get(k) for k in ("result", "total_cost_usd", "num_turns", "duration_ms", "is_error", "subtype")}
    entry = {"msg": msg, "sec": round(time.time() - t), "tools": tools, **res}
    log.append(entry)
    return entry


def run_c():
    sid = str(uuid.uuid4())
    log, iv = [], []
    b = "briefs/sim-C.json"
    turn(sid, True, f"새 글을 시작합니다. 설정 파일은 {b}입니다. 먼저 제목 후보를 뽑아 주세요.", log)
    if not (ROOT / "runs/titles0/sim-C/astra.md").exists():
        iv.append("1단계: Claude가 경로 오류를 보고 → 사람이 '04.md가 맞다, 고쳐서 진행해'라고 답함")
        turn(sid, False, "원문 경로는 originals/linkedin/04.md가 맞습니다. 고쳐서 진행해 주세요.", log)
    turn(sid, False, "3번 제목으로 정하고 글을 써 주세요.", log)
    polls = 0
    while not (ROOT / "runs/columns/sim-C/final.md").exists() and polls < 6:
        polls += 1
        time.sleep(120)
        if not (ROOT / "runs/columns/sim-C/final.md").exists():
            iv.append(f"2단계: 글이 끝났는지 사람이 다시 물음({polls}회)")
            turn(sid, False, "글 쓰기가 끝났나요? 진행 상황을 확인해 주세요.", log)
    fb = SIM / "C-feedback-1.txt"; fb.write_text((SIM / "feedback-1.txt").read_text(encoding="utf-8"), encoding="utf-8")
    turn(sid, False, f"멘토 피드백을 {fb.relative_to(ROOT)}에 저장해 두었습니다. 반영해 주세요.", log)
    turn(sid, False, "이 글은 왜 이 원문들을 중심으로 썼고, 피드백을 반영하면서 무엇이 바뀌었나요?", log)
    turn(sid, False, "참고용으로 「유정식의 경영일기」에서 '팀플레이어'를 다룬 글을 찾아 원문으로 가져와 주세요.", log)
    return {"mode": "C", "session": sid, "turns": log, "interventions": iv}


if __name__ == "__main__":
    m = sys.argv[1]
    (SIM / m).mkdir(parents=True, exist_ok=True)
    t = time.time()
    out = run_n() if m == "N" else run_c()
    out["total_sec"] = round(time.time() - t)
    (SIM / m / "log.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(m, "done", out["total_sec"], "s")
