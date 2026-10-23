"""확정본 방식 칼럼 파이프라인 — 설정 파일(briefs/*.json)대로 초안 → 재작성 → 기준 반영을 돌린다.

사용: python3 column_pipeline.py briefs/t1-A.json briefs/t1-B.json ...
0단계 — 제목 후보 (멘토 2026-10-09: "첫 단계로 해"):
  python3 column_pipeline.py --titles briefs/t1-A.json ...  → runs/titles0/<설정>/astra.md (astra만, 쓰기 전 생각 한 줄+원문 기준)
  python3 column_pipeline.py --titles briefs/t1-A.json --message <파일>  → 멘토 메시지(파일 그대로)와 직전 회차 후보를 같이 보낸다
  2026-10-23부터 제목은 쓴 뒤에 짓는다(--titles-body). 제목 없이 1~3단계를 돌리면 본문만 쓴다(가제 없음, 10/23).
  python3 column_pipeline.py --titles-body briefs/<설정>.json <원고 파일> [--message <파일>]  → 원고 본문을 읽고 제목 후보(8개 지어 4개)
단계 (확정본 「AI를 쓰는데도 퇴근 시간이 그대로인 이유」와 같은 절차):
  1. 초안   — Claude(claude -p, 빈 폴더): 원문 통째 + 경영일기 3편(p747·p724·p740) 문체 참고 + 지킬 것 2개
  2. 재작성 — astra(codex exec): "경영일기 필자가 이 원고를 직접 썼다면" (참고 2편은 설정의 r4_refs, 없으면 p724·p669 — 2026-10-09 멘토 선택)
  3. 기준   — astra: briefs/standing-feedback.md(멘토 피드백 원문)를 반영해 고침
결과: runs/columns/<topic>-<variant>/{draft,r4,final}.md (+ 각 단계 지시문·로그)
설정: thesis(이 글이 말할 것) · sources([[경로, 설명], ...] 첫째가 중심 재료) · r4_refs · draft_from(초안을 다른 갈래와 공유)
분량 두 가지 (멘토 2026-10-10: "분량을 절반으로 … 모드를 두 가지로"): 설정 "length"가 "half"면 3단계 뒤에
  4. 절반  — astra: 지금 원고를 절반 분량으로 줄인다 → final-rN.md + mode-rN.txt("절반"). 따로: --shorten <설정>
  검증된 1~3단계는 그대로 두고 맨 끝에서만 줄인다. 절반 모드의 피드백 반영은 분량을 그대로 둔다.
"""
import re
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python3 -I 실행에서도 title_candidates를 찾게
import internal_ctx as IC  # noqa: E402 — 회사 맥락(사내 용어집·사내 자료 대목, 2026-10-23)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
RUNS = ROOT / "runs" / "columns"
# Windows에선 npm이 깐 codex가 codex.cmd라 이름만으로는 못 찾는다 — 전체 경로로 (리눅스는 그대로)
CODEX = shutil.which("codex") or "codex"
ASIDE = shutil.which("aside-win") or shutil.which("aside") or "aside-win"  # WSL은 aside-win 래퍼, Windows는 aside.exe
DRAFT_REFS = ["p747", "p724", "p740"]
READER = ("SK E&S 전 직원에게 메일로 가는 사내 뉴스레터입니다. 대부분 개발자가 아닌 사무·현장 직군이고, "
          "AI를 써 봤지만 효과가 애매하다고 느끼는 사람이 많습니다. "
          "회사 안에서 팀으로 일하고, 일은 상사·동료와의 보고·결재·회의·협업으로 이어집니다.")
# 대상 독자 (멘토 2026-10-10: "타겟층이 어떻게 될지도 골라가면서 … 팀장급이거나 신입사원이거나 사수급이거나") — 설정 "target"
TARGETS = {
    "전 직원": "",
    "팀장급": "팀을 이끄는 리더입니다. 일을 나누고, 팀원이 낸 결과를 검토하고, 위로 보고하며 결정합니다.",
    "사수급": "실무를 직접 하면서 후배에게 일을 가르치고 넘겨주는 중간 연차 구성원입니다. 위로 보고하고 아래로 일을 나눠 주는 사이에서 일이 굴러가게 합니다.",
    "신입사원": "입사한 지 얼마 되지 않아 일을 배우는 중인 구성원입니다. 사수·팀장에게 보고하고 피드백을 받으며 일합니다.",
}


def target_line(b):
    """설정의 대상 독자 한 줄 — '전 직원'(기본)이면 빈 문자열."""
    t = b.get("target", "전 직원")
    return f"{t} — {TARGETS[t]} 글의 장면과 제안을 이 사람의 자리에 맞춥니다." if TARGETS.get(t) else ""


# 분량 — 멘토 2026-10-11: "글은 가능하면 1500자 이하" → 2026-10-23 사용자: 1,000자 수준(시험 칼럼 953자가 원하는 분량). 공백 제외 — 작업실 화면의 글자 수와 같은 셈
# 절반 옵션은 같은 날 없앰(작업실에서 고를 수 없음 — 예전에 절반으로 정한 글만 아래 5단계를 탄다)
TARGET_CHARS = 1000
MAX_CHARS = 1100  # 과정 3 뒤 이보다 길면 TARGET_CHARS로 한 번 더 줄인다
LEN_RULE = "분량은 공백을 빼고 1,000자 안팎으로 합니다(1,100자를 넘지 않게). 더 길면 중심 장면과 주장 위주로 줄입니다."
# 본문에는 출처 표기를 넣지 않는다(2026-10-22 사용자 결정) — 참고자료는 발행 때 글 아래에 원문 전부를 제목과 함께 붙인다(publish.py).
# 한 원문만 '(출처: …)'로 적히면 다른 원문과 형평이 맞지 않았다. 문장 속에서 '스탠퍼드대 연구진은'처럼 누가 했는지 말하는 것은 그대로.
OUT_RULE = ("출력: 제목과 본문만 주세요. 본문에 '(출처: …)' 같은 출처 표기나 참고자료 목록은 넣지 않습니다(참고자료는 발행할 때 글 아래에 따로 붙습니다). "
            "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.")


# 기준 피드백 속 따옴표 문장은 지난 글의 문장이다 — 새 글에 그대로 들어갔다(2026-10-11 "AI를 써도 검증 부담은 사라지지 않습니다. 형태만 바뀔 뿐이죠.")
NO_COPY = ("[기준 피드백] 속 따옴표 문장과 인용된 대목은 지난 글의 문장입니다(고친 예시이거나 멘토가 걸린다고 짚은 대목). "
           "어떻게 쓰라는 뜻만 따르고, 그 문장을 이 원고에 옮겨 쓰지 마세요.")
# 사례 설명 — 멘토 2026-10-11 "누구도 본적없는 사례를 … 좀더 단순하고 명확하게 설명하고 넘어가는게 좋을거같네" · "너무 말이 뭉뚱그려서만 얘기하니까"
# (비교 C·C2에서 효과를 본 지시 그대로 — wiki-eval/run_compare_1011c.py)
CASE_RULE = ("사례는 처음 듣는 독자도 바로 알아듣게 씁니다. 원문에 나오는 회사·행사·사람의 이름과 규모·결과 숫자는 그대로 밝히고(원문에 없는 이름은 지어내지 않습니다), "
             "무슨 일이 있었고 무엇이 달라졌는지만 쉬운 말로 짧게 설명하고 넘어갑니다. 장치나 절차의 세부는 말할 것에 꼭 필요한 하나만 씁니다.")

# 인물 표기(2026-10-23 사용자: "인물이 중요하면 분명히 하는 게 좋겠다") — 「따져 보셨나요」에서 과정 1·2의 "금융업계 임원 라이언 스파크스"가
# 과정 3(기준 반영)에서 "미국 금융업계의 한 임원"으로 흐려졌다. 기준 피드백의 '원문을 쓴 강사·대표는 언급하지 말라'를 사례 속 인물에게까지 적용한 것.
PEOPLE_RULE = ("사람 이름은 두 경우를 나눕니다. 사례의 주인공(그 사람이 한 일이 곧 사례인 사람)은 원문에 나온 이름과 소속·직함을 밝힙니다 — "
               "'한 임원', '어느 회사 대표'처럼 흐리게 부르지 않습니다. 원문을 쓰거나 전한 사람(기자·강사·칼럼 필자·인터뷰어)은 글에 중요하지 않으면 "
               "언급하지 않습니다. 지난 글 피드백의 '강사·대표를 빼라'는 이 두 번째 경우입니다. 원문에 이름이 없으면 지어내지 않습니다.")


def standing_block():
    """멘토가 지난 글들에 한 말(standing-feedback) — 받은 그대로. 2026-10-11부터 초안·재작성에도 넘긴다
    (그 전엔 과정 3에만 들어가 글의 뼈대에 닿지 않았다 — 멘토가 짚은 대목이 초안에서 생겨 재작성에서 커졌다)."""
    fb = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8").strip()
    return "[멘토가 지난 글들을 읽고 한 말 — 원문 그대로] 이 글에도 지킵니다.\n" + fb.replace("[멘토 피드백 — 원문 그대로]\n", "") + "\n\n" + NO_COPY


def body(path):
    t = Path(path).read_text(encoding="utf-8")
    if t.startswith("---"):
        t = t.split("---", 2)[2]
    return t.split("*주변 동료에게")[0].strip()


def ref(k):
    # "(끝)"은 경영일기 필자의 맺음 표시 — 우리 글에 따라 붙지 않게 참고 글에서부터 뺀다 (2026-10-09 멘토)
    t = body(SRC / "originals" / "infuture" / f"{k}.md").replace("(끝)", "").rstrip()
    return f"=== 유정식의 경영일기 {k} ===\n" + t


def mine_lines(b):
    """내 주제로 쓰기(scripts/my_topic.py) — 말할 것은 멘토가 정했고 원문은 그 말을 보여 주는 사례다. 원문 글쓴이의 주장이 글을 이끌지 않게."""
    docs = [p for p, _ in b["sources"] if p.startswith("mine/")]
    return [
        f"주제(멘토 요청 — 받은 그대로): {b.get('request', b['thesis'])}",
        f"이 글이 말할 것: {b['thesis']}\n이 문장을 글 앞쪽과 맺음에서 쉬운 말로 분명히 말합니다.",
        "아래 원문들은 그 말을 보여 주는 사례이고, [원문 1]이 글을 이끄는 중심 사례입니다. "
        "원문마다 이 글에서 맡는 몫을 적어 두었습니다. 원문 글쓴이의 주장이 이 글의 주장을 대신하지 않게 하고, 중심 사례 하나를 끝까지 읽고 깊게 풀어 주세요"
        "(장면은 아래 3번처럼 회사 장면으로 옮깁니다). [원문 2] 이후는 맡은 몫만큼만 씁니다.",
        *(["[회사 자료]는 멘토가 넣은 회사 문서입니다. 적힌 사실만 쓰고, 문장을 그대로 옮기지 않고, 자료에 없는 회사 제도·일정·장면을 지어내지 않습니다."] if docs else []),
    ]


def source_blocks(b):
    roles, out, i = b.get("roles", {}), [], 0
    for p, d in b["sources"]:
        if p.startswith("mine/"):
            out.append(f"=== [회사 자료] {d} ===\n" + body(SRC / p))
            continue
        i += 1
        role = f"(이 글에서 맡는 몫: {roles[p]})\n" if roles.get(p) else ""
        out.append(f"=== [원문 {i}] {d} ===\n" + role + body(SRC / p))
    return out


def draft_prompt(b):
    mine = bool(b.get("from_mine"))
    parts = [
        "사내 뉴스레터에 실을 칼럼 한 편을 써 주세요.",
        (f"제목: {b['title']}\n제목은 이대로 씁니다." if b.get("title") else
         "제목은 본문을 다 쓴 뒤 따로 짓습니다. 제목이나 가제는 붙이지 말고 본문만 쓰세요. 말할 것을 잘 전하는 데 집중하세요."),
        f"독자: {READER}",
        *([f"이번 글의 대상 독자: {target_line(b)}"] if target_line(b) else []),
        *(mine_lines(b) if mine else [
            f"이 글이 말할 것: {b['thesis']}",
            "아래 [원문 1]이 이 글의 중심 재료입니다. 끝까지 읽고, 그 안의 이야기와 말을 재료로 삼아 깊게 풀어 주세요(장면은 아래 3번처럼 회사 장면으로 옮깁니다). "
            "[원문 2] 이후는 보조 재료입니다."]),
        "쓰는 방식은 아래 [문체 참고]의 필자(경영 컨설턴트 유정식)가 쓰듯이 써 주세요. 장면이나 질문으로 열고, 재료 하나를 깊게 풀고, "
        "필자의 생각을 분명하게 말하고 맺는 흐름입니다. [문체 참고] 글들의 내용이나 사례는 가져오지 마세요.",
        LEN_RULE,
        "지킬 것은 세 가지입니다.\n1. 원문의 문장을 그대로 옮기지 않습니다. 이야기와 사실만 가져와 내 말로 씁니다.\n"
        "2. 원문에 없는 사실·수치·경험을 지어내지 않습니다.\n"
        # 2026-10-10 멘토: 프리랜서 기준이 아니라 회사에서 일하는 기준으로 — "일반인들은 전혀 그러지않잖아. 이런걸 왜 일반화해?"
        # 원문을 회사 사람 글로만 모으자는 제안에는 "이걸 회사에서의 이야기로 바꾸면되지. 굳이 회사로 해야하나?" → 원문은 그대로, 글에서 옮겨 쓴다
        "3. 글은 회사에서 일하는 독자의 이야기로 씁니다. 원문이 프리랜서·1인 사업자·개발자 개인의 이야기라면 그 사람의 사정(자기 돈으로 내는 "
        "구독료·계정 수, 고객 영업, 혼자 하는 작업)을 독자에게 일반화하지 말고, 거기서 얻은 교훈을 독자가 회사에서 겪는 장면"
        "(팀·상사·보고·결재·회의·동료와의 협업)으로 옮겨 보여 줍니다. 글을 이끄는 장면은 이 회사 장면이고, 원문의 이야기는 그 장면을 받쳐 주는 재료입니다. "
        "옮긴 장면은 '~한 상황을 떠올려 보세요'처럼 가정으로 쓰고, 원문 속 일을 어느 회사에서 실제로 있었던 일처럼 꾸미지는 않습니다.",
        CASE_RULE,
        PEOPLE_RULE,
        *[x for x in (IC.internal_block(IC.load(b)), IC.glossary_block()) if x],  # 회사 맥락(2026-10-23) — 넣기로 한 사내 자료 대목 · 사내 용어집
        standing_block(),
        OUT_RULE,
    ]
    parts += source_blocks(b) if mine else [f"=== [원문 {i}] {d} ===\n" + body(SRC / p) for i, (p, d) in enumerate(b["sources"], 1)]
    for k in DRAFT_REFS:
        parts.append("[문체 참고] " + ref(k))
    return "\n\n".join(parts)


def r4_prompt(b, draft):
    parts = [
        "아래 [원고]를 [참고] 글의 필자(경영 컨설턴트 유정식)가 자기 뉴스레터에 직접 썼다면 어떻게 썼을지 상상하며 다시 써 주세요.",
        "원고의 논리 전개와 사실은 그대로 두고, 문장과 이어 가는 방식만 [참고] 필자처럼 바꿉니다. [참고] 글의 내용이나 사례는 가져오지 않습니다. 제목은 바꾸지 마세요.",
    ]
    parts += ["[참고] " + ref(k) for k in b.get("r4_refs", ["p724", "p669"])]
    parts += [standing_block(), PEOPLE_RULE, IC.KEEP_RULE, LEN_RULE, OUT_RULE + " 원고에 없는 사실·수치·경험은 더하지 마세요.",
              "=== 원고 ===\n" + draft]
    return "\n\n".join(parts)


def fb_prompt(text):
    fb = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8")
    return "\n\n".join([
        "아래 [원고]는 우리 사내 뉴스레터의 기준 방식으로 쓴 글입니다. 글의 흐름·문체·논리는 그대로 두고, 아래 [멘토 피드백]을 반영해 고쳐 주세요. "
        "원고에 없는 사실·수치·경험은 더하지 마세요. 제목은 바꾸지 마세요.",
        fb, NO_COPY, PEOPLE_RULE, IC.KEEP_RULE, IC.glossary_block(), LEN_RULE, OUT_RULE, "=== [원고] ===\n" + text])


def run_claude(d, prompt):
    """Claude 초안 — 쓰는 동안 글자를 live.md로 흘려 작업실 화면에서 진행이 보이게 한다(멘토 2026-10-10: "실제로 진행되는지 확인이 안 됨")."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    proc = subprocess.Popen(["claude", "-p", "--model", "opus", "--tools", "", "--strict-mcp-config", "--no-session-persistence",
                             "--output-format", "stream-json", "--verbose", "--include-partial-messages"],
                            cwd=d, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    proc.stdin.write(prompt)
    proc.stdin.close()
    parts, result = [], ""
    with open(d / "live.md", "w", encoding="utf-8") as live, open(d / "thinking.md", "w", encoding="utf-8") as think:
        for line in proc.stdout:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "stream_event":
                ev = e.get("event", {})
                delta = ev.get("delta", {}) if ev.get("type") == "content_block_delta" else {}
                if delta.get("type") == "text_delta":
                    parts.append(delta["text"])
                    live.write(delta["text"])
                    live.flush()
                elif delta.get("type") == "thinking_delta":  # 쓰기 전 생각 — 본문이 나오기 전에도 진행이 보이게
                    think.write(delta.get("thinking", ""))
                    think.flush()
            elif e.get("type") == "result":
                result = e.get("result", "")
    (d / "run.log").write_text(proc.stderr.read(), encoding="utf-8")
    proc.wait()
    return (result or "".join(parts)).strip()


def run_astra(d, prompt):
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    out = d / "output.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), "-"],
                       cwd=d, input=prompt, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    return out.read_text(encoding="utf-8").strip() if out.exists() else ""


def stage(name, jobs):
    t = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda j: j(), jobs))
    print(f"[{name}] {len(jobs)}건 {time.time() - t:.0f}s · 빈 결과 {sum(1 for r in res if not r)}건", flush=True)
    return res


def ensure_point(bp, b):
    """내 주제로 쓰기 — 말할 것 한 문장이 없거나(예전 글) 바꿔 끼우기로 중심 원문이 바뀌었으면 쓰기 직전에 다시 정한다(Claude)."""
    import my_topic as MT
    center = next((p for p, _ in b["sources"] if p.startswith("originals/")), "")
    if not center or (b.get("point") and b.get("point_for") == center):
        return
    request = b.get("request") or b["thesis"]
    point = MT.make_point(request, center, b["dir"] / "_point")
    if point:
        b.update({"request": request, "point": point, "point_for": center, "thesis": point})
        meta = {x: y for x, y in b.items() if x != "dir"}
        Path(bp).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print("말할 것:", point, flush=True)


def titles_first(args):
    """--titles <설정> ... [--message <파일>] — 메시지는 파일 내용 그대로 astra에게 (멘토 2026-10-10)."""
    import title_candidates as tc
    out = ROOT / "runs" / "titles0"
    paths, msg = list(args), ""
    if "--message" in paths:
        i = paths.index("--message")
        msg = Path(paths[i + 1]).read_text(encoding="utf-8").strip()
        del paths[i:i + 2]
    jobs = []
    for pth in paths:
        k = Path(pth).stem
        b = json.loads(Path(pth).read_text(encoding="utf-8"))
        if "thesis" not in b:
            continue
        d = out / k
        d.mkdir(parents=True, exist_ok=True)
        # 직전 회차 — 작업실은 astra.md를 astra-N.md로 밀어 두고 부른다. 바로 부르면 astra.md가 직전 회차
        olds = sorted(d.glob("astra-*.md"), key=lambda p: int(p.stem.split("-")[1]))
        last = d / "astra.md" if (d / "astra.md").exists() else (olds[-1] if olds else None)
        prev = tc.round_items(last) if msg and last else None
        (d / "message.txt").unlink(missing_ok=True)  # 덮어쓸 회차의 메시지
        pr = tc.prompt_first(b["thesis"], b["sources"], SRC, msg, prev, target=target_line(b))
        (d / "prompt.md").write_text(pr, encoding="utf-8")
        (d / "brief.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")

        def job(d=d, pr=pr, b=b):
            # 8개는 gen/에 짓고 cands.md로 — astra.md(작업실이 보는 회차)에는 고른 4개만 쓴다(2026-10-23)
            (d / "cands.md").unlink(missing_ok=True)
            (d / "devices.json").unlink(missing_ok=True)  # 본문 회차의 장치 기록이 남아 있으면 장치당 1개 규칙이 엉뚱하게 걸린다
            tc.astra(d / "gen", pr)
            if (d / "gen" / "astra.md").exists():
                (d / "cands.md").write_text((d / "gen" / "astra.md").read_text(encoding="utf-8"), encoding="utf-8")
            tc.pick(d, b["thesis"], target_line(b), msg)  # 8개 지어 4개 고름(메시지 · 후킹 · 과장 없음, 2026-10-23)
            ok = (d / "astra.md").exists()
            if ok and msg:  # 회차와 함께 남긴다 — 작업실이 후보 위에 보여 준다
                (d / "message.txt").write_text(msg, encoding="utf-8")
            return ok
        jobs.append(job)
    stage("제목 후보·astra (쓰기 전)" + (" · 멘토 메시지" if msg else ""), jobs)


def titles_body(args):
    """--titles-body <설정> <원고 파일> [--message <파일>] — 다 쓴 원고 본문을 읽고 제목 후보를 짓는다(2026-10-23 사용자 결정:
    주제 문장은 표현이 AI 같아 그걸로 지은 제목도 나아지지 않았다 — 제목은 본문을 종합해서). 8개 지어 4개 고름."""
    import title_candidates as tc
    paths, msg = list(args), ""
    if "--message" in paths:
        i = paths.index("--message")
        msg = Path(paths[i + 1]).read_text(encoding="utf-8").strip()
        del paths[i:i + 2]
    bp, text_file = Path(paths[0]), ROOT / paths[1]
    k = bp.stem
    b = json.loads(bp.read_text(encoding="utf-8"))
    d = ROOT / "runs" / "titles0" / k
    d.mkdir(parents=True, exist_ok=True)
    olds = sorted(d.glob("astra-*.md"), key=lambda p: int(p.stem.split("-")[1]))
    prev = tc.round_items(olds[-1]) if msg and olds else None
    (d / "message.txt").unlink(missing_ok=True)
    text = text_file.read_text(encoding="utf-8")
    (d / "source.txt").write_text(text_file.relative_to(ROOT).as_posix(), encoding="utf-8")
    tc.write_body(d, text, b.get("thesis", ""), target_line(b), msg, prev)  # 장치별 2개씩 8개(2026-10-23)
    tc.pick(d, b.get("thesis", ""), target_line(b), msg, text=text)
    if (d / "astra.md").exists() and msg:
        (d / "message.txt").write_text(msg, encoding="utf-8")
    print("제목 후보(본문):", " / ".join(tc.round_items(d / "astra.md")) if (d / "astra.md").exists() else "없음")


def main(paths):
    briefs = {Path(p).stem: json.loads(Path(p).read_text(encoding="utf-8")) for p in paths}
    for k, b in briefs.items():
        b["dir"] = RUNS / k
    # 제목은 쓴 뒤에 짓는다(2026-10-23) — 제목 없이도 쓴다(본문만, 가제 없음)
    # 1. 초안 (thesis가 있는 갈래만, 나머지는 draft_from을 공유)
    own = [k for k, b in briefs.items() if "thesis" in b]

    def mk_draft(k):
        b = briefs[k]
        if b.get("from_mine"):
            ensure_point(ROOT / "briefs" / f"{k}.json", b)
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

    # 4. 1,100자를 넘으면 1,000자로 줄이기 (기본 모드만 — 절반 모드는 아래에서 절반으로 줄인다)
    over = [k for k, b in briefs.items() if b.get("length") != "half" and chars(latest_final(b["dir"])[0]) > MAX_CHARS]
    if over:
        stage("1,000자·astra", [lambda k=k: fit(ROOT / "briefs" / f"{k}.json") for k in over])

    # 5. 절반 모드만
    half = [k for k, b in briefs.items() if b.get("length") == "half"]
    if half:
        stage("절반·astra", [lambda k=k: shorten(ROOT / "briefs" / f"{k}.json") for k in half])



def set_title(brief_path, pick):
    """--set-title <설정> <번호|제목> — 0단계 후보 중 번호로 고르거나 제목을 직접 넣는다."""
    import re
    bp = Path(brief_path)
    b = json.loads(bp.read_text(encoding="utf-8"))
    if pick.isdigit():
        f = ROOT / "runs" / "titles0" / bp.stem / "astra.md"
        lines = [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        title = lines[int(pick) - 1]
    else:
        title = pick
    b["title"] = title
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print("제목:", title)


def revise(brief_path, feedback_path):
    """--revise <설정> <피드백 파일> — 최신 최종본에 멘토 피드백(파일 내용 그대로)을 반영해 final-rN.md를 만든다 (astra)."""
    k = Path(brief_path).stem
    d = RUNS / k
    cur, n = latest_final(d)
    half = json.loads(Path(brief_path).read_text(encoding="utf-8")).get("length") == "half"
    fb_new = Path(feedback_path).read_text(encoding="utf-8").strip()
    standing = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8")
    prompt = "\n\n".join([
        "아래 [원고]를 [이번 멘토 피드백]대로 고쳐 주세요. 글의 흐름·문체·논리는 그대로 두고 피드백이 말하는 곳만 고칩니다. "
        "[기준 피드백]도 계속 지킵니다. 원고에 없는 사실·수치·경험은 더하지 마세요. 제목은 바꾸지 마세요."
        + (" 분량은 지금 원고 정도로 둡니다." if half else " " + LEN_RULE),
        "[이번 멘토 피드백 — 원문 그대로]\n" + fb_new, "[기준 피드백]\n" + standing, NO_COPY, PEOPLE_RULE, IC.KEEP_RULE, IC.glossary_block(), OUT_RULE,
        "=== [원고] ===\n" + cur.read_text(encoding="utf-8")])
    t0 = time.time()
    out = run_astra(d / f"_revise-r{n}", prompt)
    (d / f"final-r{n}.md").write_text(out, encoding="utf-8")
    (d / f"feedback-r{n}.txt").write_text(fb_new, encoding="utf-8")
    print(f"피드백 반영 r{n}: {cur.name} → final-r{n}.md · {time.time() - t0:.0f}s · {len(out)}자")


def latest_final(d):
    revs = sorted(d.glob("final-r*.md"), key=lambda p: int(p.stem.split("-r")[1]))
    return (revs[-1] if revs else d / "final.md"), len(revs) + 1


def shorten_prompt(text):
    title, *rest = text.strip().split("\n", 1)
    n = round(len(re.sub(r"\s", "", rest[0] if rest else text)) / 2 / 10) * 10
    standing = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8")
    return "\n\n".join([
        f"아래 [원고]를 지금의 절반 분량(공백 제외 약 {n}자)으로 줄여 주세요. 글의 흐름·문체·필자의 생각은 살리고, "
        "중심 장면과 주장 위주로 남깁니다. [기준 피드백]도 계속 지킵니다. 원고에 없는 사실·수치·경험은 더하지 마세요. 제목은 바꾸지 마세요.",
        "[기준 피드백]\n" + standing, NO_COPY, PEOPLE_RULE, IC.KEEP_RULE, OUT_RULE, "=== [원고] ===\n" + text])


def chars(f):
    """제목('# ' 줄)을 뺀 본문의 공백 제외 글자 수 — 제목 없이 쓰는 원고(10/23~)는 첫 문단부터 센다."""
    t = Path(f).read_text(encoding="utf-8").strip() if Path(f).exists() else ""
    rest = t.split("\n", 1)[1] if t.startswith("#") and "\n" in t else t
    return len(re.sub(r"\s", "", rest))


def fit_prompt(text):
    standing = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8")
    return "\n\n".join([
        f"아래 [원고]를 공백을 빼고 {TARGET_CHARS:,}자 안팎({MAX_CHARS:,}자 이하)으로 줄여 주세요. 글의 흐름·문체·필자의 생각은 살리고, 중심 장면과 주장 위주로 남깁니다. "
        "[기준 피드백]도 계속 지킵니다. 원고에 없는 사실·수치·경험은 더하지 마세요. 제목은 바꾸지 마세요.",
        "[기준 피드백]\n" + standing, NO_COPY, PEOPLE_RULE, IC.KEEP_RULE, OUT_RULE, "=== [원고] ===\n" + text])


def fit(brief_path):
    """과정 3 뒤 1,100자를 넘으면 — 최신 원고를 1,000자 안팎으로 줄여 다음 과정(final-rN.md)을 만든다 (astra)."""
    d = RUNS / Path(brief_path).stem
    cur, n = latest_final(d)
    t0 = time.time()
    out = run_astra(d / f"_fit-r{n}", fit_prompt(cur.read_text(encoding="utf-8")))
    (d / f"final-r{n}.md").write_text(out, encoding="utf-8")
    (d / f"mode-r{n}.txt").write_text("1,000자", encoding="utf-8")
    print(f"1,000자 r{n}: {cur.name} → final-r{n}.md · {time.time() - t0:.0f}s · 본문 {chars(d / f'final-r{n}.md')}자")


def shorten(brief_path):
    """--shorten <설정> — 최신 원고를 절반 분량으로 줄여 다음 과정(final-rN.md)을 만든다 (astra)."""
    d = RUNS / Path(brief_path).stem
    cur, n = latest_final(d)
    t0 = time.time()
    out = run_astra(d / f"_shorten-r{n}", shorten_prompt(cur.read_text(encoding="utf-8")))
    (d / f"final-r{n}.md").write_text(out, encoding="utf-8")
    (d / f"mode-r{n}.txt").write_text("절반", encoding="utf-8")
    print(f"절반 r{n}: {cur.name} → final-r{n}.md · {time.time() - t0:.0f}s · {len(out)}자")


def shorten_file(src, out_dir):
    """--shorten-file <원고> <폴더> — 설정 없는 확정 칼럼용. 결과는 <폴더>/output.md"""
    d = Path(out_dir)
    d = d if d.is_absolute() else (ROOT / d)  # 상대 경로를 그대로 넘기면 astra가 폴더를 못 찾아 빈 결과가 났다(2026-10-10)
    src_f = Path(src) if Path(src).is_absolute() else ROOT / src
    out = run_astra(d.resolve(), shorten_prompt(src_f.read_text(encoding="utf-8")))
    print(f"절반: {src} → {out_dir}/output.md · {len(out)}자")
    if not out.strip():
        sys.exit("절반 결과가 비었음 — 로그: " + str(d / "run.log"))


def fetch_infuture(post_id):
    """--fetch-infuture <번호> — 경영일기 글 한 편을 aside REPL 스냅샷으로 받아 원문 파일로 저장 (shadow DOM 본문)."""
    inf = SRC / "originals" / "infuture"
    snap = inf / "snap" / f"p{post_id}.txt"
    js = (f"const tF{post_id} = await openTab('https://infuture.stibee.com/p/{post_id}'); "
          f"const sF{post_id} = await snapshot(tF{post_id}); console.log(sF{post_id}.tree); await closeTab(tF{post_id});")
    r = subprocess.run([ASIDE, "repl", "--host", "local", js], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    snap.write_text(r.stdout, encoding="utf-8")
    title = ""
    import re
    m = re.search(r'- text: "(.+?) ?(\d{4})\. \d{1,2}\. \d{1,2}\."', r.stdout)  # 제목 끝 ?·! 뒤에 날짜가 붙는 경우도
    if m:
        title = m.group(1)
    out = subprocess.run([sys.executable, "-X", "utf8", "-I", str(ROOT / "scripts" / "parse_infuture.py"), str(snap), title], capture_output=True, text=True, encoding="utf-8")
    (inf / f"p{post_id}.md").write_text(out.stdout, encoding="utf-8")
    print(f"p{post_id} 저장: {title} · {len(out.stdout)}자")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--titles"]:
        titles_first(a[1:])
    elif a[:1] == ["--titles-body"]:
        titles_body(a[1:])
    elif a[:1] == ["--set-title"]:
        set_title(a[1], a[2])
    elif a[:1] == ["--revise"]:
        revise(a[1], a[2])
    elif a[:1] == ["--shorten"]:
        shorten(a[1])
    elif a[:1] == ["--shorten-file"]:
        shorten_file(a[1], a[2])
    elif a[:1] == ["--fetch-infuture"]:
        fetch_infuture(a[1])
    else:
        main(a)
