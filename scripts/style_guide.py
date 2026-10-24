"""경영일기 252편을 쓰기에 활용한다(2026-10-24 사용자 결정 — 고정 참고 3·2편 대신).

  A. 글마다 참고 글 고르기 — 초안: 이 글의 메시지와 가까운 경영일기 2편 / 재작성: 초안과 도입·맺음 방식이 같은 글 중 메시지가 가까운 2편
  B. 문체 안내서 — 252편의 구조(도입·전개·맺음·목소리)를 한 번 분석해 안내서 한 장으로. 초안·재작성에 고정으로 넣는다

  python3 -I scripts/style_guide.py --analyze   글마다 구조 꼬리표(Claude, 계정 로그인 — 이미 한 글은 건너뜀) → _structure.json
  python3 -I scripts/style_guide.py --guide     꼬리표 + 글자 수·문단 통계로 안내서 → _style_guide.md
  python3 -I scripts/style_guide.py --refs "<이 글이 말할 것>"   고를 참고 글 보기
결과는 sources/originals/infuture/(경영일기 본문과 같은 곳, git에): _structure.json · _style_guide.md
"""
import json
import re
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import title_style as TS  # noqa: E402
import wiki as W  # noqa: E402

INF = TS.INF
STRUCT = INF / "_structure.json"
GUIDE = INF / "_style_guide.md"
RUNS = W.ROOT / "runs" / "style-guide"
BATCH = 18
OPENS = ["장면", "질문", "통념 제시", "사례·연구 소개", "독자 상황", "필자 경험", "인용"]
CLOSES = ["권유·제안", "질문 던지기", "요약·재강조", "한 줄 결론", "경고·당부"]
LEN_RANGE = (800, 1700)  # 참고 글로 쓸 길이(공백 제외) — 우리 칼럼(1,000자 안팎)과 모양이 비슷한 글만


def nchars(t):
    return len(re.sub(r"\s", "", t))


def analyze_prompt(batch):
    arts = "\n\n".join(f"=== [{a['id']}] {a['title']} ===\n{a['body'][:3500]}" for a in batch)
    return "\n\n".join([
        "아래는 「유정식의 경영일기」(경영 컨설턴트 유정식이 직장인에게 쓰는 짧은 칼럼) 글들입니다. "
        "이 필자가 글을 어떻게 짜는지 배우려고 합니다. 내용이 아니라 짜임만 정리해 주세요.",
        "글마다:\n"
        f"- open: 도입 방식 — 이 중 하나: {', '.join(OPENS)}\n"
        "- open_how: 첫 한두 문단이 실제로 무엇을 하는지 한 줄(예: '회의 장면을 그리고 그 자리의 불편함을 짚는다')\n"
        "- flow: 전개를 화살표로 4~6단계(예: 장면 → 흔한 해석 → 연구 결과 → 필자 해석 → 제안). 내용 말고 역할로\n"
        f"- close: 맺음 방식 — 이 중 하나: {', '.join(CLOSES)}\n"
        "- close_how: 마지막 문단이 실제로 무엇을 하는지 한 줄\n"
        "- voice: 필자의 목소리 특징 한 줄(어미·문장 길이·독자와의 거리·단정의 정도 등)",
        "출력: JSON 하나만. {\"items\": [{\"id\": \"p752\", \"open\": \"...\", \"open_how\": \"...\", \"flow\": \"...\", "
        "\"close\": \"...\", \"close_how\": \"...\", \"voice\": \"...\"}]} — id는 [ ] 안 그대로.",
        W.ANSWER_ONLY, W.GUARD, arts])


def analyze():
    got = json.loads(STRUCT.read_text(encoding="utf-8")) if STRUCT.exists() else {}
    arts = [a for a in TS.articles() if a["id"] not in got]
    print(f"구조 분석할 글 {len(arts)}편 (이미 {len(got)})", flush=True)
    run = RUNS / time.strftime("%Y%m%d-%H%M%S")
    batches = [arts[i:i + BATCH] for i in range(0, len(arts), BATCH)]

    def one(ib):
        i, b = ib
        raw = W.claude_login(run / f"b{i + 1:02d}", analyze_prompt(b))
        m = re.search(r"\{.*\}", raw or "", re.S)
        try:
            return b, json.loads(m.group(0)).get("items", []) if m else []
        except ValueError:
            return b, []

    with ThreadPoolExecutor(4) as ex:
        for b, items in ex.map(one, enumerate(batches)):
            ids = {a["id"]: a for a in b}
            for x in items:
                a = ids.get(x.get("id"))
                if a and x.get("open") in OPENS and x.get("close") in CLOSES:
                    got[a["id"]] = {k: str(x.get(k, "")).strip() for k in ("open", "open_how", "flow", "close", "close_how", "voice")}
                    got[a["id"]]["chars"] = nchars(a["body"])
                    got[a["id"]]["paras"] = len([p for p in re.split(r"\n\s*\n", a["body"]) if p.strip()])
            STRUCT.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"묶음 · {len(items)}/{len(b)} · 모두 {len(got)}", flush=True)
    return got


def stats(got):
    arts = {a["id"]: a for a in TS.articles()}
    sents = [len(re.sub(r"\s", "", s)) for a in arts.values() for s in re.split(r"(?<=[.?!])\s+", a["body"]) if len(s) > 5]
    ends = {}
    for a in arts.values():
        for s in re.split(r"(?<=[.?!])\s+", a["body"]):
            m = re.search(r"([가-힣]{1,3})[.?!]$", s.strip())
            if m:
                ends[m.group(1)] = ends.get(m.group(1), 0) + 1
    count = lambda key, opts: {o: sum(1 for v in got.values() if v[key] == o) for o in opts}
    return {"n": len(got), "chars_median": st.median(v["chars"] for v in got.values()),
            "paras_median": st.median(v["paras"] for v in got.values()), "sent_median": st.median(sents),
            "open": count("open", OPENS), "close": count("close", CLOSES),
            "ends": sorted(ends.items(), key=lambda x: -x[1])[:15]}


def guide_prompt(got, s):
    rows = "\n".join(f"[{k}] 도입 {v['open']}: {v['open_how']} / 전개 {v['flow']} / 맺음 {v['close']}: {v['close_how']} / 목소리 {v['voice']}"
                     for k, v in got.items())
    return "\n\n".join([
        f"아래는 「유정식의 경영일기」 {s['n']}편의 짜임을 글마다 정리한 것과 통계입니다. "
        "이 필자처럼 칼럼을 쓰려는 사람에게 줄 '문체 안내서'를 써 주세요. 사내 뉴스레터(공백 제외 1,000자 안팎) 칼럼을 쓰는 AI가 읽습니다.",
        "안내서에 담을 것(각각 짧게, 비율은 통계 그대로):\n"
        "1. 도입 — 자주 쓰는 방식과 비율, 방식마다 첫 문단이 하는 일\n"
        "2. 전개 — 자주 보이는 흐름 2~3가지(역할로)\n"
        "3. 맺음 — 자주 쓰는 방식과 비율, 마지막 문단이 하는 일\n"
        "4. 목소리 — 어미·문장 길이·문단 길이·독자와의 거리·단정의 정도\n"
        "5. 이 필자가 하지 않는 것 — 짜임 정리에서 드러나는 것만\n"
        "6. 다양하게 쓰기 — 한 가지 도입·맺음으로 굳지 않게, 어떤 글에 어떤 방식이 맞는지\n"
        "지킬 것: 특정 글의 내용·사례·문장을 옮기지 않습니다(이 안내서는 짜임만). "
        "우리 칼럼에는 개인 필자가 없으므로 필자 경험으로 여는 방식·필자 자신의 이야기를 털어놓는 목소리는 권하지 않습니다(10/24 사용자 결정). 2,000자 안팎. 제목 '# 경영일기 문체 안내서'로 시작하는 마크다운.",
        W.ANSWER_ONLY, W.GUARD,
        "=== [통계] ===\n" + json.dumps(s, ensure_ascii=False),
        "=== [글마다 짜임] ===\n" + rows])


def guide():
    got = json.loads(STRUCT.read_text(encoding="utf-8"))
    s = stats(got)
    out = W.claude_login(RUNS / ("guide-" + time.strftime("%Y%m%d-%H%M%S")), guide_prompt(got, s)).strip()
    if not out.startswith("#"):
        out = "# 경영일기 문체 안내서\n\n" + out
    head = (f"<!-- scripts/style_guide.py --guide · {time.strftime('%Y-%m-%d')} · 경영일기 {s['n']}편 · "
            f"글자 수 중앙값 {s['chars_median']:.0f} · 문단 {s['paras_median']:.0f} · 문장 {s['sent_median']:.0f}자 -->\n")
    GUIDE.write_text(head + out + "\n", encoding="utf-8")
    return s


def guide_text():
    """초안·재작성 지시에 넣을 안내서 — 없으면 빈 문자열."""
    if not GUIDE.exists():
        return ""
    return re.sub(r"\A<!--.*?-->\n", "", GUIDE.read_text(encoding="utf-8"), flags=re.S).strip()


def _pool():
    got = json.loads(STRUCT.read_text(encoding="utf-8")) if STRUCT.exists() else {}
    # 필자 경험으로 여는 글은 참고 글로 고르지 않는다(10/24) — 우리 칼럼에는 개인 필자가 없어 없는 경험을 지어내게 할 수 있다
    return {k: v for k, v in got.items() if LEN_RANGE[0] <= v.get("chars", 0) <= LEN_RANGE[1] and v.get("open") != "필자 경험"}


def draft_refs(message, n=2, exclude=()):
    """A — 초안 참고: 이 글의 메시지와 가까운 경영일기 n편(길이가 우리 칼럼과 비슷한 글만)."""
    pool = _pool()
    return [k for k, _ in TS.ranked(message) if k in pool and k not in exclude][:n]


def rewrite_refs(message, open_, close, n=2, exclude=()):
    """A — 재작성 참고: 초안과 도입·맺음 방식이 같은 글 중 메시지가 가까운 n편. 모자라면 맺음만 같은 글 → 메시지만 가까운 글로 채운다."""
    pool = _pool()
    ranked = [k for k, _ in TS.ranked(message) if k in pool and k not in exclude]
    out = [k for k in ranked if pool[k]["open"] == open_ and pool[k]["close"] == close][:n]
    out += [k for k in ranked if k not in out and pool[k]["close"] == close][:n - len(out)]
    out += [k for k in ranked if k not in out][:n - len(out)]
    return out


def label_prompt(text):
    return "\n\n".join([
        "아래 [원고]의 짜임을 꼬리표로 붙여 주세요. 내용이 아니라 짜임만 봅니다.",
        f"- open: 도입 방식 — 이 중 하나: {', '.join(OPENS)}\n- close: 맺음 방식 — 이 중 하나: {', '.join(CLOSES)}",
        "출력: JSON 하나만. {\"open\": \"...\", \"close\": \"...\"}", W.ANSWER_ONLY, W.GUARD, "=== [원고] ===\n" + text])


def label(run_dir, text):
    """초안의 도입·맺음 꼬리표(Claude, 짧은 호출) — 재작성 참고 글을 고를 때."""
    raw = W.claude_login(Path(run_dir), label_prompt(text))
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        x = json.loads(m.group(0)) if m else {}
    except ValueError:
        x = {}
    return (x.get("open") if x.get("open") in OPENS else ""), (x.get("close") if x.get("close") in CLOSES else "")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--analyze"]:
        analyze()
    elif a[:1] == ["--guide"]:
        print(json.dumps(guide(), ensure_ascii=False, indent=1))
    elif a[:1] == ["--refs"]:
        q = " ".join(a[1:])
        pairs = TS.pairs()
        for k in draft_refs(q, 4):
            print(f"[{k}] {pairs.get(k, {}).get('title', '')} — {_pool()[k]['open']} / {_pool()[k]['close']}")
    else:
        print(__doc__)
