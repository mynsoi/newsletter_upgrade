"""칼럼 본문은 두고 제목 후보만 뽑는다 (멘토: "제목이 항상 좀 별로", 2026-10-09).

사용: python3 title_candidates.py <이름>=<본문 파일> ...
결과: runs/titles/<이름>/astra.md — 번호 붙은 제목 8줄 (astra만 — 멘토 2026-10-09: Claude가 지은 제목은 AI slop이 심하다)
쓰기 전 제목(prompt_first)은 column_pipeline.py --titles가 부른다 — 멘토 메시지(--message)를 같이 보낼 수 있다.
참고: 「유정식의 경영일기」 최근 제목 60개(공지·강좌 제외, AI 아닌 주제 포함) + 멘토가 직접 지은 제목 1개
"""
import html
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INF = ROOT / "sources" / "originals" / "infuture"
OUT = ROOT / "runs" / "titles"
# Windows에선 npm이 깐 codex가 codex.cmd라 이름만으로는 못 찾는다 — 전체 경로로 (리눅스는 그대로)
CODEX = shutil.which("codex") or "codex"
MENTOR_TITLE = "왜 AI를 쓰는데 더 퇴근 시간이 빨라지지 않을까요?"
RECENT = [  # 아카이브 첫 화면(737~756) — _titles.tsv에 없는 구간
    "연봉을 많이 줘도 직원들이 퇴사하는 이유", "경쟁시키면 성과가 올라갈까요?", "질문으로 상대방의 행동에 개입하는 법",
    "동료에게 부탁할 때 꼭 지켜야 할 룰은?", "직원들에게 AI를 적극 활용하라고 하기 전에", "일 잘하는 직원에겐 교육이 필요없을까요?",
    "'우리와 잘 맞는 사람'이라는 평가는 온당할까?", "조직의 문제는 없는 게 아니라 '리더만 모를 뿐'", "지친 직원에게 업무를 줄여주지 마세요",
    "AI 결과물은 너무 훌륭해서 문제!", "남을 웃기려면 머리를 쓰게 하지 마세요", "인앤아웃이 맥도날드보다 잘 나가는 이유는?",
    "모두를 동등하게 대하는 것은 나쁜 리더십", "지원자의 성격을 보고 채용하나요?", "여러분의 직원들은 '팀플레이어'인가요?",
    "'원료비 급등으로 가격 인상합니다'란 말은 하지 마세요", "AI가 팀워크에 기여하도록 하려면?", "AI가 만든 광고는 과연 효과적일까요?",
    "성공 스토리의 함정에 빠지지 마세요", "'관리자 하기 싫다'는 직원들을 나무라기 전에",
]


def ref_titles(n=60):
    rows = []
    for line in (INF / "_titles.tsv").read_text(encoding="utf-8").splitlines():
        k, status, t = (line.split("\t") + ["", ""])[:3]
        t = html.unescape(t).strip()
        if status == "200" and t and not re.search(r"^\[|강좌|쇼케이스|공지|시즌 \d", t):
            rows.append((int(k), t))
    rows.sort(reverse=True)
    return (RECENT + [t for _, t in rows])[:n]


def prompt(text):
    text = text.replace("(끝)", "").strip()
    titles = "\n".join(f"- {t}" for t in ref_titles())
    return f"""아래 [본문]은 사내 뉴스레터(SK E&S 전 직원 대상)에 실을 칼럼입니다. 이 글의 제목 후보를 8개 지어 주세요.

- [제목 참고]는 이 뉴스레터가 문체를 참고하는 「유정식의 경영일기」의 실제 제목들입니다. 이 제목들의 결을 참고하되, 그대로 가져오지는 마세요.
- [멘토가 직접 지은 제목]도 참고하세요.
- 본문이 실제로 말하는 것을 과장하지 않습니다.
- 후보끼리는 서로 다른 결로 지어 주세요.

출력: 번호를 붙인 제목 8줄만 주세요. 설명은 붙이지 마세요. 파일을 만들거나 명령을 실행하지 마세요.

[멘토가 직접 지은 제목]
- {MENTOR_TITLE}

[제목 참고]
{titles}

[본문]
{text}"""


def round_items(f):
    """회차 파일(astra.md·astra-N.md)에서 번호·머리표를 뗀 제목 줄만."""
    return [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]


N_WRITE, N_SHOW = 8, 4  # 2026-10-23: 8개 지어 4개 고른다(메시지 전달 · 후킹 · 과장 없음으로) — 처음부터 4개만 지으면 고를 여지가 없다


def pairs_block(thesis):
    """경영일기 짝 — 이 글이 말할 것과 메시지가 가까운 경영일기 글의 '핵심 메시지 → 실제 제목 → 장치 → 어떻게 바꿨나'(title_style.py).
    짝이 아직 없으면 빈 문자열 — 그때는 제목 목록만 참고한다."""
    try:
        import title_style as TS
        near = TS.similar(thesis, 8)
        n, c = TS.stats()
    except Exception as e:
        print(f"경영일기 짝 건너뜀: {e}", flush=True)
        return ""
    if not near:
        return ""
    kinds = "\n".join(f"- {d}: {TS.DEVICE_NOTE[d]} — 경영일기 {n}편 중 {k}편" for d, k in sorted(c.items(), key=lambda x: -x[1]) if k)
    ex = "\n".join(f"- 메시지: {v['message']}\n  → 제목: {v['title']}  [{', '.join(v['devices'])}]" for _, v in near)
    return f"[경영일기 제목 장치]\n{kinds}\n\n[경영일기: 메시지가 가까운 글의 '메시지 → 제목']\n{ex}\n\n"


def prompt_first(thesis, sources, src_root, message="", prev=None, target=""):
    """첫 단계 — 글을 쓰기 전에 생각 한 줄과 원문만 보고 제목 후보를 낸다 (멘토 2026-10-09: "첫 단계로 해").
    message: 멘토가 다시 뽑을 때 같이 보낸 말(원문 그대로, 2026-10-10 "제목 지을 때도 astra한테 원할 시 메시지를 같이")
    prev: 그 말이 가리킬 수 있게 직전 회차 후보 — 메시지가 있을 때만 넣는다.
    target: 대상 독자 한 줄(column_pipeline.target_line) — 비면 넣지 않는다."""
    def body(path):
        s = Path(path).read_text(encoding="utf-8")
        return (s.split("---", 2)[2] if s.startswith("---") else s).strip()
    titles = "\n".join(f"- {t}" for t in ref_titles())
    srcs = "\n\n".join(f"=== [원문 {i}] {d} ===\n" + body(Path(src_root) / p) for i, (p, d) in enumerate(sources, 1))
    ask = ask_body = ""
    if message:
        ask = ("\n- [이번 멘토 요청]을 따라 주세요. 위 항목과 부딪치면 요청을 따릅니다."
               + (" [앞 회차 후보]는 멘토가 이미 본 후보입니다." if prev else ""))
        ask_body = "[이번 멘토 요청 — 원문 그대로]\n" + message.strip() + "\n\n"
        if prev:
            ask_body += "[앞 회차 후보]\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(prev, 1)) + "\n\n"
    pairs = pairs_block(thesis)
    how = ("- [경영일기: 메시지 → 제목]은 이 뉴스레터가 문체를 참고하는 「유정식의 경영일기」 필자가 글의 메시지를 제목으로 옮긴 예입니다. "
           "말투와 장치(묻기·단언·금지·이유 등)를 참고하세요. 다만 경영일기 제목 중 메시지를 감춰 궁금하게만 만든 것은 따르지 말고, "
           "메시지가 제목에 드러나는 쪽을 따릅니다. 그 제목들을 그대로 가져오지는 마세요.\n"
           "- [경영일기 제목 장치]에서 후보마다 다른 장치를 쓰세요.\n" if pairs else
           "- [제목 참고]는 이 뉴스레터가 문체를 참고하는 「유정식의 경영일기」의 실제 제목들입니다. 이 제목들의 결을 참고하되, 그대로 가져오지는 마세요.\n")
    return f"""아래 [원문]을 재료로 사내 뉴스레터(SK E&S 전 직원 대상) 칼럼을 쓰려고 합니다. 글을 쓰기 전에 제목부터 정하려고 합니다. 제목 후보를 {N_WRITE}개 지어 주세요.

이 글이 말할 것: {thesis}
{f"대상 독자: {target}" + chr(10) if target else ""}
기준은 순서대로입니다(2026-10-23 사용자 기준).
1. 주제 전달(가장 중요): 본문을 모르는 사람이 제목만 읽고 이 글이 무엇을 말하는지 바로 알 수 있어야 합니다. 해석이 필요하면 안 됩니다.
2. 매력적인 표현: 1을 지킨 위에서 읽고 싶게 만드는 질문·단언·뒤집기를 씁니다. 원문이 보여 주는 것을 과장하지는 않습니다.
가장 피할 것: 함축. 글자 수를 줄이려고 말을 압축하거나 비유·은유로 돌려 말하면 메시지가 흐려지고 독자가 해석해야 합니다.
'~의 차례', '~한 기여', '숨은 비용'처럼 명사로 끊어 뜻을 감추는 말, 본문을 읽어야 알 수 있는 사례 이름·숫자만 앞세운 제목은 쓰지 않습니다.
{how}- [멘토가 직접 지은 제목]도 참고하세요.
- 한 제목에 생각 하나, 콜론·부제 없이. 길이는 뜻이 분명한 쪽을 택합니다(대략 30자 안팎까지 괜찮음).
- 후보끼리는 서로 다른 결로 지어 주세요.{ask}

출력: 번호를 붙인 제목 {N_WRITE}줄만 주세요. 설명은 붙이지 마세요. 파일을 만들거나 명령을 실행하지 마세요.

{ask_body}[멘토가 직접 지은 제목]
- {MENTOR_TITLE}

{pairs}[제목 참고]
{titles}

{srcs}"""


def prompt_body(text, thesis="", message="", prev=None, target=""):
    """다 쓴 원고 본문을 읽고 제목을 짓는다(2026-10-23) — 기준은 prompt_first와 같고, 무엇을 말하는지는 본문에서 읽는다.
    주제 문장은 참고만(표현을 따르지 않음 — 사용자: 주제 문장 표현이 AI 같아 그걸로 지은 제목도 별로였다)."""
    body = re.sub(r"^#.*\n", "", text.replace("(끝)", "").strip(), count=1).strip()
    ask = ask_body = ""
    if message:
        ask = ("\n- [이번 멘토 요청]을 따라 주세요. 위 항목과 부딪치면 요청을 따릅니다."
               + (" [앞 회차 후보]는 멘토가 이미 본 후보입니다." if prev else ""))
        ask_body = "[이번 멘토 요청 — 원문 그대로]\n" + message.strip() + "\n\n"
        if prev:
            ask_body += "[앞 회차 후보]\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(prev, 1)) + "\n\n"
    pairs = pairs_block(body[:1500])
    return f"""아래 [본문]은 사내 뉴스레터(SK E&S 전 직원 대상)에 실을 칼럼입니다. 본문을 끝까지 읽고 이 글의 제목 후보를 {N_WRITE}개 지어 주세요.
{f"대상 독자: {target}" + chr(10) if target else ""}
기준은 순서대로입니다.
1. 주제 전달(가장 중요): 본문을 읽지 않은 사람이 제목만 보고 이 글이 무엇을 말하는지 바로 알 수 있어야 합니다. 해석이 필요하면 안 됩니다.
   무엇을 말하는지는 [본문]을 종합해서 정합니다 — 본문이 결국 독자에게 하는 말, 맺음에서 남기는 말을 중심으로.
2. 매력적인 표현: 1을 지킨 위에서 읽고 싶게 만드는 질문·단언·뒤집기를 씁니다. 본문이 말하지 않는 것을 약속하거나 부풀리지 않습니다.
가장 피할 것: 함축. 글자 수를 줄이려고 말을 압축하거나 비유·은유로 돌려 말하면 메시지가 흐려지고 독자가 해석해야 합니다.
'~의 차례', '~한 기여', '숨은 비용'처럼 명사로 끊어 뜻을 감추는 말, 본문을 읽어야 알 수 있는 사례 이름·숫자만 앞세운 제목은 쓰지 않습니다.
- [기획 때 적은 말할 것]은 참고만 하세요. 그 문장의 표현을 따르지 말고 본문이 실제로 한 말로 짓습니다.
{"- [경영일기: 메시지 → 제목]은 이 뉴스레터가 문체를 참고하는 「유정식의 경영일기」 필자가 글의 메시지를 제목으로 옮긴 예입니다. 말투와 장치를 참고하되, 메시지를 감춰 궁금하게만 만든 제목은 따르지 말고, 그 제목들을 그대로 가져오지도 마세요." + chr(10) + "- [경영일기 제목 장치]에서 후보마다 다른 장치를 쓰세요." + chr(10) if pairs else ""}- 한 제목에 생각 하나, 콜론·부제 없이. 길이는 뜻이 분명한 쪽을 택합니다(대략 30자 안팎까지 괜찮음).
- 후보끼리는 서로 다른 결로 지어 주세요.{ask}

출력: 번호를 붙인 제목 {N_WRITE}줄만 주세요. 설명은 붙이지 마세요. 파일을 만들거나 명령을 실행하지 마세요.

{ask_body}{pairs}[기획 때 적은 말할 것]
{thesis or "(없음)"}

[본문]
{body}"""


def pick_prompt(thesis, cands, target="", message="", text=""):
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(cands, 1))
    return f"""사내 뉴스레터(SK E&S 전 직원 대상) 칼럼의 제목 후보 {len(cands)}개입니다. 사람에게 보여 줄 {N_SHOW}개를 골라 주세요.

{"[본문]을 읽고 이 글이 무엇을 말하는지 먼저 정리한 뒤 판정하세요(기획 때 적은 말할 것: " + thesis + ")" if text else "이 글이 말할 것: " + thesis}
{f"대상 독자: {target}" + chr(10) if target else ""}{f"멘토 요청(원문 그대로): {message}" + chr(10) if message else ""}
후보마다 세 가지를 1~5점으로 매기세요.
- message(가장 중요): 본문을 모르는 사람이 제목만 읽고 이 글이 무엇을 말하는지 한 문장으로 말할 수 있나.
  해석이 필요한 함축(압축·비유·명사로 끊어 뜻을 감춤, 본문을 알아야 아는 사례 이름·숫자)이면 2점 이하.
- hook: 읽고 싶어지나(질문·단언·뒤집기) — 뻔한 요약이면 낮게
- honest: 글이 말하지 않는 것을 약속하거나 부풀리지 않나
고르는 순서: message 4점 이상만 → 그중 hook이 높은 순 → honest 3점 이상. 결(질문·단언·금지·이유 등)이 서로 겹치지 않게 {N_SHOW}개, 가장 좋은 것부터.

출력: JSON 하나만. {{"scores": [{{"n": 1, "message": 4, "hook": 3, "honest": 5}}], "pick": [3, 1, 6, 8]}}
파일을 만들거나 명령을 실행하지 마세요. 답만 주세요.

[후보]
{numbered}
{(chr(10) + "[본문]" + chr(10) + text) if text else ""}"""


def pick(d, thesis, target="", message="", text=""):
    """astra가 지은 후보(astra.md)에서 Claude(계정 로그인)가 메시지 · 후킹 · 과장 없음으로 N_SHOW개를 골라 astra.md를 그 순서로 바꾼다.
    지은 후보 전부는 cands.md, 점수는 pick.json. 판정이 안 되면 앞의 N_SHOW개."""
    import json
    import wiki as W
    f = Path(d) / "astra.md"
    if not f.exists():
        return []
    cands = round_items(f)[:N_WRITE]
    (Path(d) / "cands.md").write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    chosen = cands[:N_SHOW]
    try:
        raw = W.claude_login(Path(d) / "pick", pick_prompt(thesis, cands, target, message, text))
        m = re.search(r"\{.*\}", raw or "", re.S)
        got = json.loads(m.group(0)) if m else {}
        idx = [int(i) for i in got.get("pick", []) if 1 <= int(i) <= len(cands)]
        if idx:
            chosen = [cands[i - 1] for i in dict.fromkeys(idx)][:N_SHOW]
        (Path(d) / "pick.json").write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
    except (Exception, SystemExit) as e:
        print(f"제목 고르기 건너뜀(앞 {N_SHOW}개): {e}", flush=True)
    f.write_text("\n".join(f"{i}. {t}" for i, t in enumerate(chosen, 1)) + "\n", encoding="utf-8")
    return chosen


def astra(d, p):
    d.mkdir(parents=True, exist_ok=True)
    out = d / "astra.md"
    with open(d / "astra.log", "w", encoding="utf-8") as log:
        subprocess.run([CODEX, "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), "-"],
                       cwd=d, input=p, text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)


def claude(d, p):
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["claude", "-p", "--model", "opus", "--tools", "", "--strict-mcp-config", "--no-session-persistence"],
                       cwd=d, input=p, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (d / "claude.md").write_text(r.stdout.strip(), encoding="utf-8")


if __name__ == "__main__":
    jobs = []
    for arg in sys.argv[1:]:
        name, path = arg.split("=", 1)
        d = OUT / name
        p = prompt(Path(path).read_text(encoding="utf-8"))
        d.mkdir(parents=True, exist_ok=True)
        (d / "prompt.md").write_text(p, encoding="utf-8")
        (d / "source.txt").write_text(path, encoding="utf-8")
        jobs += [lambda d=d, p=p: astra(d, p)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda j: j(), jobs))
    print("done", len(jobs))
