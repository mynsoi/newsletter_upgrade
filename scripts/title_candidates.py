"""칼럼 본문은 두고 제목 후보만 뽑는다 (멘토: "제목이 항상 좀 별로", 2026-10-09).

사용: python3 title_candidates.py <이름>=<본문 파일> ...
결과: runs/titles/<이름>/{astra,claude}.md — 번호 붙은 제목 8줄
참고: 「유정식의 경영일기」 최근 제목 60개(공지·강좌 제외, AI 아닌 주제 포함) + 멘토가 직접 지은 제목 1개
"""
import html
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INF = ROOT / "sources" / "originals" / "infuture"
OUT = ROOT / "runs" / "titles"
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


def astra(d, p):
    d.mkdir(parents=True, exist_ok=True)
    out = d / "astra.md"
    with open(d / "astra.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), p],
                       cwd=d, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)


def claude(d, p):
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["claude", "-p", "--model", "opus", "--tools", "", "--strict-mcp-config", "--no-session-persistence", p],
                       cwd=d, stdin=subprocess.DEVNULL, capture_output=True, text=True)
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
        jobs += [lambda d=d, p=p: astra(d, p), lambda d=d, p=p: claude(d, p)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda j: j(), jobs))
    print("done", len(jobs))
