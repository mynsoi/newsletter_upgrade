"""글 품질 원인 찾기 비교 (2026-10-11) — 멘토: "지금 나오는 결과가 진짜 별로고 말투도 ai 같음 … 경영일기 칼럼을 참고한게 맞는지 의심이됨"

같은 제목·같은 중심 원문(threads/20)으로, 과정 1(Claude 초안) → 과정 2(astra 재작성)까지만. 운영 글(m-20261011-173414)은 건드리지 않는다.
- B   : 기준 글(퇴근 시간 칼럼) 방식 — 말할 것 = 원문 카드의 '글쓴이가 하는 말'(새로 짓지 않음), 멘토 요청은 주제 줄, 지킬 것 1·2만, 대상 독자 줄 없음
- B3  : 지금 주제 지도 길의 초안 지시문 그대로(column_pipeline.draft_prompt) — B에 지킬 것 3(회사 장면) + 대상 독자(팀장급)
과정 3(기준 반영)은 돌리지 않는다 — 지금 과정 3이 지난 글의 예문을 새 글에 넣고 "한 회사"로 바꾸는 것을 확인했다.
결과: runs/compare-1011/<B|B3>/{draft,r4}.md
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import column_pipeline as C  # noqa: E402

OUT = ROOT / "runs" / "compare-1011"
TITLE = "AI 잘 쓰는 직원만 모으면 일 잘하는 팀이 될까요?"
REQUEST = (ROOT / "runs" / "mine" / "m-20261011-173414" / "topic.txt").read_text(encoding="utf-8").strip()
CARD = json.loads((ROOT / "wiki" / "cards.json").read_text(encoding="utf-8"))["threads/20"]
SRC = [["originals/threads/20.md", "Threads, @overtime.sam, 2026-09-17"]]


def prompt_b():
    """기준 글 초안 지시문(runs/skilltest/prompt-A.md)의 짜임 그대로 + 1,500자(멘토 2026-10-11)"""
    parts = [
        "사내 뉴스레터에 실을 칼럼 한 편을 써 주세요.",
        f"제목: {TITLE}\n제목은 이대로 씁니다.",
        f"독자: {C.READER}",
        f"주제(멘토 요청): {REQUEST}",
        f"이 글이 말할 것: {CARD['글쓴이가 하는 말']}",
        "아래 [원문 1]이 이 글의 중심 재료입니다. 이 글을 끝까지 읽고, 그 안의 장면과 말을 재료로 삼아 깊게 풀어 주세요.",
        "쓰는 방식은 아래 [문체 참고]의 필자(경영 컨설턴트 유정식)가 쓰듯이 써 주세요. 장면이나 질문으로 열고, 재료 하나를 깊게 풀고, "
        "필자의 생각을 분명하게 말하고 맺는 흐름입니다. [문체 참고] 글들의 내용이나 사례는 가져오지 마세요.",
        C.LEN_RULE,
        "지킬 것은 두 가지입니다.\n1. 원문의 문장을 그대로 옮기지 않습니다. 이야기와 사실만 가져와 내 말로 씁니다.\n2. 원문에 없는 사실·수치·경험을 지어내지 않습니다.",
        C.OUT_RULE,
        "=== [원문 1] Threads, @overtime.sam, 2026-09-17 ===\n" + C.body(C.SRC / SRC[0][0]),
    ]
    parts += ["[문체 참고] " + C.ref(k) for k in C.DRAFT_REFS]
    return "\n\n".join(parts)


def prompt_b3():
    b = {"title": TITLE, "thesis": CARD["글쓴이가 하는 말"], "sources": SRC, "target": "팀장급"}
    return C.draft_prompt(b)


def run(name, p):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    draft = C.run_claude(d / "_draft", p)
    (d / "draft.md").write_text(draft, encoding="utf-8")
    r4 = C.run_astra(d / "_r4", C.r4_prompt({"title": TITLE}, draft))
    (d / "r4.md").write_text(r4, encoding="utf-8")
    print(name, "끝", len(draft), len(r4), flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda x: run(*x), [("B", prompt_b()), ("B3", prompt_b3())]))
