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


def prompt_first(thesis, sources, src_root, message="", prev=None):
    """첫 단계 — 글을 쓰기 전에 생각 한 줄과 원문만 보고 제목 후보를 낸다 (멘토 2026-10-09: "첫 단계로 해").
    message: 멘토가 다시 뽑을 때 같이 보낸 말(원문 그대로, 2026-10-10 "제목 지을 때도 astra한테 원할 시 메시지를 같이")
    prev: 그 말이 가리킬 수 있게 직전 회차 후보 — 메시지가 있을 때만 넣는다."""
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
    return f"""아래 [원문]을 재료로 사내 뉴스레터(SK E&S 전 직원 대상) 칼럼을 쓰려고 합니다. 글을 쓰기 전에 제목부터 정하려고 합니다. 제목 후보를 8개 지어 주세요.

이 글이 말할 것: {thesis}

- [제목 참고]는 이 뉴스레터가 문체를 참고하는 「유정식의 경영일기」의 실제 제목들입니다. 이 제목들의 결을 참고하되, 그대로 가져오지는 마세요.
- [멘토가 직접 지은 제목]도 참고하세요.
- 원문이 실제로 보여 주는 것을 과장하지 않습니다.
- 후보끼리는 서로 다른 결로 지어 주세요.{ask}

출력: 번호를 붙인 제목 8줄만 주세요. 설명은 붙이지 마세요. 파일을 만들거나 명령을 실행하지 마세요.

{ask_body}[멘토가 직접 지은 제목]
- {MENTOR_TITLE}

[제목 참고]
{titles}

{srcs}"""


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
