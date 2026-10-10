"""원문 카드 → 직원 인사이트 (빌려 오기) → 제목 후보 (2026-10-11)

멘토: "나는 여기서 ai관련 회사 직원들이 업무에 도움될만한 인사이트를 뽑아내야해."
      "완전히 직원의 사례에 일치하지 않고 개개인의 사례더라도 직원에게 인사이트를 줄수있는 사례라면 잘 차용해서 넣을수가 있어야지."
쓸모는 "회사 사례인가"가 아니라 "빌려 와서 직원에게 인사이트를 줄 수 있는가"로 본다. 개인 사례는 그 사람의 일로 사실대로 두고,
그 안의 통하는 원리를 직원 업무 장면(가정)으로 옮긴다. 일반론을 막는 건 금지 목록이 아니라 시험 하나 — "다른 카드에 붙여도 말이 되면 일반론".
사용: python3 -I wiki-eval/run_insight.py runs/topic-full/20261011-full linkedin/02 threads/21 ...
결과: <run>/insight/<시각>/<사이트>-<번호>/ (output.md · titles/astra.md) + insight.json
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "wiki-eval"))
import column_pipeline as C  # noqa: E402
import run_full as F  # noqa: E402  astra()
import title_candidates as tc  # noqa: E402
import wiki as W  # noqa: E402

FIELDS = ("빌려 올 점", "직원 장면", "인사이트", "쓸모")


def prompt(k, card):
    return "\n\n".join([
        "아래는 사내 뉴스레터(SK E&S 직원 대상, 대부분 개발자가 아닌 사무·현장 직군) 칼럼 재료로 모은 원문 하나와, 그 원문을 정리한 카드입니다.",
        "할 일: 이 원문에서 우리 직원이 AI와 일하는 데 도움이 될 인사이트를 빌려 와 주세요.\n"
        "- 원문이 회사 직원의 사례가 아니어도 됩니다(프리랜서·크리에이터·개발자·1인 사업자의 사례도). 그 사례에서 직원의 일에도 통하는 원리를 찾아 빌려 옵니다.\n"
        "- 원문 속 사례는 그 사람의 일로 사실대로 둡니다. 직원의 업무 장면은 \"~할 때\"처럼 가정으로 씁니다. 어느 회사에서 실제로 있었던 일처럼 꾸미지 않습니다.\n"
        "- 인사이트에는 원문 사례의 구체적인 사실(장면·숫자·말)을 담습니다. 쓰고 나서 확인합니다: 이 문장을 다른 원문의 카드에 붙여도 말이 되면 일반론입니다 — 원문의 구체적인 사실이 빠진 것이니 다시 씁니다.\n"
        "- 쓸모는 '빌려 와서 직원에게 인사이트를 줄 수 있는가'로 판단합니다. 원문이 회사 사례인지 개인 사례인지는 따지지 않습니다.",
        "지킬 것: 원문의 문장을 그대로 옮기지 않습니다. 원문에 없는 사실·수치·경험을 지어내지 않습니다. 말끝은 '~다'로 맞춥니다.",
        "출력 형식(이 네 줄 머리만 쓰고 다른 설명은 붙이지 마세요):\n"
        "빌려 올 점: <이 사례에서 직원의 일에도 통하는 원리, 원문 사례의 구체적인 점과 함께 한두 문장>\n"
        "직원 장면: <SK E&S 직원이 이 점을 쓸 수 있는 업무 장면 한두 개, 가정으로>\n"
        "인사이트: <직원이 이 글을 읽고 업무에서 다르게 보거나 해 볼 것, 원문 사례의 구체적인 사실을 담아 한두 문장>\n"
        "쓸모: <높음|보통|낮음> — <이유 한 줄>",
        "파일을 만들거나 명령을 실행하지 말고 답변으로만 주세요.",
        f"=== [카드] ===\n있었던 일: {card['있었던 일']}\n글쓴이가 하는 말: {card['글쓴이가 하는 말']}",
        "=== [원문] ===\n" + C.body(ROOT / "sources" / "originals" / f"{k}.md"),
    ])


def one(k, card, out):
    d = out / k.replace("/", "-")
    text = ""
    for _ in range(2):
        text = F.astra(d, prompt(k, card))
        if text:
            break
    f = {m.group(1): m.group(2).strip() for m in re.finditer(r"^(빌려 올 점|직원 장면|인사이트|쓸모):\s*(.+)$", text, re.M)}
    if f.get("인사이트"):
        td = d / "titles"
        p = tc.prompt_first(f["인사이트"], [[f"originals/{k}.md", W.label(f"originals/{k}.md")]], ROOT / "sources")
        td.mkdir(parents=True, exist_ok=True)
        (td / "prompt.md").write_text(p, encoding="utf-8")
        for _ in range(2):
            tc.astra(td, p)
            if (td / "astra.md").exists():
                break
    print(f"{k} · {'ok' if len(f) == 4 else '실패'}", flush=True)
    return k, f


if __name__ == "__main__":
    run = ROOT / sys.argv[1]
    cards = json.loads((run / "cards.json").read_text(encoding="utf-8"))
    keys = sys.argv[2:]
    out = run / "insight" / time.strftime("%Y%m%d-%H%M%S")
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(ex.map(lambda k: one(k, cards[k], out), keys))
    (out / "insight.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)
