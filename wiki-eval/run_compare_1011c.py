"""글 품질 비교 C·C2 (2026-10-11) — B·B3를 읽은 멘토: "누구도 본적없는 사례를 … 좀더 단순하고 명확하게 설명하고 넘어가는게 좋을거같네.
여전히 무슨말을 하려고 하는지 너무 뜬구름 잡는 느낌이난다." · "300명이 참여한 사내 AI 경연대회 이런거는 … 그냥 직접적으로 어떤 해커톤이다 설명해도 되잖아."

바꾼 것 (B에서)
1. 쓰기 전에 '말할 것'을 Claude가 한 문장으로 정한다 — 독자가 한 번 듣고 따라 말할 수 있게, 원문 글쓴이의 주장 안에서, 멘토 요청(주제)에 답하게.
2. 초안에 멘토가 지난 판들에 한 말(standing-feedback)을 받은 그대로 넘긴다 — 지금까지는 과정 3에만 들어가 글의 뼈대에 닿지 않았다.
3. 사례: 원문에 나오는 이름·규모·결과는 그대로 밝히고(지어내지 않음), 무슨 일이 있었고 무엇이 달라졌는지만 쉬운 말로 짧게.
- C  : 같은 원문(threads/20 — 원문 자체에 회사·행사 이름이 없다)
- C2 : 토스 원문(linkedin/01 — 토스 CDAO, AI 정답률 24.7%→95%)
과정 1(Claude) → 과정 2(astra 재작성, p724·p669)까지. 결과: runs/compare-1011/<C|C2>/{thesis,draft,r4}.md
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "wiki-eval"))
import column_pipeline as C  # noqa: E402
from run_compare_1011 import CARD, OUT, REQUEST, TITLE  # noqa: E402
import json  # noqa: E402

CARDS = json.loads((ROOT / "wiki" / "cards.json").read_text(encoding="utf-8"))
STANDING = (ROOT / "briefs" / "standing-feedback.md").read_text(encoding="utf-8").strip()
SOURCES = {
    "C": ("originals/threads/20.md", "Threads, @overtime.sam, 2026-09-17", CARD),
    "C2": ("originals/linkedin/01.md", "LinkedIn, 토스(비바리퍼블리카) CDAO 김홍수, 9월 17일", CARDS["linkedin/01"]),
}
CASE_RULE = ("사례는 처음 듣는 독자도 바로 알아듣게 씁니다. 원문에 나오는 회사·행사·사람의 이름과 규모·결과 숫자는 그대로 밝히고(원문에 없는 이름은 지어내지 않습니다), "
             "무슨 일이 있었고 무엇이 달라졌는지만 쉬운 말로 짧게 설명하고 넘어갑니다. 장치나 절차의 세부는 말할 것에 꼭 필요한 하나만 씁니다.")


def thesis_prompt(src, card):
    return "\n\n".join([
        f"사내 뉴스레터 칼럼을 쓰기 전에, 이 글이 말할 것을 한 문장으로 정해 주세요. 독자: {C.READER}",
        f"주제(멘토 요청): {REQUEST}",
        f"원문 글쓴이가 하는 말: {card['글쓴이가 하는 말']}",
        "조건: 독자가 한 번 듣고 그대로 따라 말할 수 있는 쉬운 한 문장. 원문 글쓴이의 주장 안에서, 멘토 요청의 주제에 답하는 문장. "
        "'기준·체계·구조·문화·역량' 같은 뭉뚱그린 말 대신 일하는 장면의 말로. 원문에 없는 사실을 더하지 않습니다.",
        "출력: 그 한 문장만. 따옴표나 설명 없이. 파일을 만들거나 명령을 실행하지 말고 답변으로만.",
        "=== [원문] ===\n" + C.body(C.SRC / src),
    ])


def draft_prompt(src, label, thesis):
    parts = [
        "사내 뉴스레터에 실을 칼럼 한 편을 써 주세요.",
        f"제목: {TITLE}\n제목은 이대로 씁니다.",
        f"독자: {C.READER}",
        f"주제(멘토 요청): {REQUEST}",
        f"이 글이 말할 것: {thesis}\n이 문장을 글 앞쪽과 맺음에서 쉬운 말로 분명히 말합니다.",
        "아래 [원문 1]이 이 글의 중심 재료입니다. 끝까지 읽고, 말할 것을 보여 주는 데 필요한 만큼만 가져옵니다.",
        CASE_RULE,
        "쓰는 방식은 아래 [문체 참고]의 필자(경영 컨설턴트 유정식)가 쓰듯이 써 주세요. 장면이나 질문으로 열고, 재료 하나를 풀고, "
        "필자의 생각을 분명하게 말하고 맺는 흐름입니다. [문체 참고] 글들의 내용이나 사례는 가져오지 마세요.",
        C.LEN_RULE,
        "지킬 것은 두 가지입니다.\n1. 원문의 문장을 그대로 옮기지 않습니다. 이야기와 사실만 가져와 내 말로 씁니다.\n2. 원문에 없는 사실·수치·경험을 지어내지 않습니다.",
        "[멘토가 지난 글들을 읽고 한 말 — 원문 그대로] 아래 말을 이 글에도 지킵니다. 따옴표 속 문장은 지난 글의 문장이니 옮겨 쓰지 않습니다.\n" + STANDING,
        C.OUT_RULE,
        f"=== [원문 1] {label} ===\n" + C.body(C.SRC / src),
    ]
    parts += ["[문체 참고] " + C.ref(k) for k in C.DRAFT_REFS]
    return "\n\n".join(parts)


def run(name):
    src, label, card = SOURCES[name]
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    thesis = C.run_claude(d / "_thesis", thesis_prompt(src, card)).strip().strip('"“”')
    (d / "thesis.md").write_text(thesis + "\n", encoding="utf-8")
    draft = C.run_claude(d / "_draft", draft_prompt(src, label, thesis))
    (d / "draft.md").write_text(draft, encoding="utf-8")
    r4 = C.run_astra(d / "_r4", C.r4_prompt({"title": TITLE}, draft))
    (d / "r4.md").write_text(r4, encoding="utf-8")
    print(name, "끝 · 말할 것:", thesis, flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(run, ["C", "C2"]))
