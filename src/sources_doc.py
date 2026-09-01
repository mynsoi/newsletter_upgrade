"""config/sources.yaml → docs/소스_카탈로그.md 생성기 (사람용 뷰).

사용: make sources-doc
확정본은 sources.yaml이며 md는 파생 문서다 — md를 직접 수정하지 않는다.
구조: 티어별(요약표 + 상세 카드), 티어 내 수집 방식(API→RSS→뉴스레터→수기)→id 순.
excluded 소스는 제외한다.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "config" / "sources.yaml"
DOC_PATH = ROOT / "docs" / "소스_카탈로그.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TYPE_ORDER = {"api": 0, "rss": 1, "newsletter": 2, "manual": 3}
TYPE_WORD = {"api": "API", "rss": "RSS", "newsletter": "뉴스레터", "manual": "수기"}
TIER_TITLES = {
    "T1": "실증 연구·데이터 — 수치 근거 (가장 믿을 만함)",
    "T2": "컨설팅·리서치·싱크탱크 — 분석 틀·프레임워크",
    "T3": "저널·전문 매체 — 관점·논쟁",
    "T4": "기업·기관 1차 자료 — 실제 사례",
    "T5": '뉴스 — "요즘 무슨 일이 있나" 신호 감지 전용 (논지 근거 단독 사용 금지)',
}
LANG = {"en": "영", "ko": "한"}


def collect_path(s: dict) -> str:
    t = s["type"]
    if t in ("api", "rss"):
        return f"{TYPE_WORD[t]} · 상시 자동 (Actions 매일 06:00)"
    if t == "newsletter":
        return f"뉴스레터 · {s.get('subscription_status', '구독 대기')} → A4 구축 후 자동"
    return "수기 · 수기 등록 (/ingest-url · /ingest-file)"


def status_label(s: dict) -> str:
    return f"시험 운영 (~{s['trial_until']})" if s.get("trial_until") else "현행"


def constraints_full(s: dict) -> str:
    c = s.get("constraints", "")
    if s.get("allow_feed_discovery") is False:
        c += " · 섹션 피드 한정 — 관례 경로 탐지 금지"
    if s.get("request_headers"):
        c += " · 브라우저형 요청 헤더 필요"
    return c


def card_url(s: dict) -> str | None:
    return s.get("feed_url") or s.get("endpoint") or s.get("homepage")


def render(sources: list[dict]) -> str:
    active = [s for s in sources if s.get("status") != "excluded"]
    excluded_n = sum(1 for s in sources if s.get("status") == "excluded")
    by_tier: dict[str, list[dict]] = {}
    for s in active:
        by_tier.setdefault(s["tier"], []).append(s)
    for tier in by_tier:
        by_tier[tier].sort(key=lambda s: (TYPE_ORDER[s["type"]], s["id"]))

    tier_counts = " · ".join(f"{t} {len(by_tier.get(t, []))}" for t in sorted(by_tier))
    type_counts = {t: sum(1 for s in active if s["type"] == t) for t in TYPE_ORDER}
    type_line = (f"API {type_counts['api']} · RSS {type_counts['rss']} · "
                 f"뉴스레터 {type_counts['newsletter']} · 수기 {type_counts['manual']}")

    L: list[str] = []
    L.append("# 소스 카탈로그 (사람용 뷰)")
    L.append("")
    L.append("> **파생 문서** — 확정본은 `config/sources.yaml`이며 이 문서는 그 요약·해설 뷰다. "
             '소스 변경 후 Claude Code에 "소스 카탈로그 md 다시 생성해줘"로 동기화한다. '
             f"확정: 2026-08-31 α4 회의 · 생성 기준: {date.today().isoformat()} · "
             f"**{len(active)}개 소스**(제외 {excluded_n}건·미등재 중앙일보 미포함)")
    L.append("")
    L.append("**주제 축 9개**: 리더십 · 조직 설계 · 인재 육성 · 평가·보상 · 일하는 방식 · "
             "AI 리터러시 · AI 거버넌스 · 채용 · 조직 문화  ")
    L.append("**수집 방식**: API(공식 창구 질의, 소급 가능) · RSS(새 글 목록→본문 추출) · "
             "뉴스레터(전용 메일함 자동 판독, A4 구축 후 가동) · 수기(사람이 발견 시 등록)  ")
    L.append("**상태**: 현행 = Phase 0부터 가동 · 시험 운영 = α5 거버넌스에 따라 1개월 관찰 후 "
             "월간 성과 리뷰에서 재판정")
    L.append("")
    L.append(f"**구성**: {tier_counts} / {type_line}")
    L.append("")
    L.append("")

    for tier in sorted(by_tier):
        rows = by_tier[tier]
        L.append("---")
        L.append("")
        L.append(f"## {tier} — {TIER_TITLES[tier]} ({len(rows)})")
        L.append("")
        L.append("### 요약표")
        L.append("")
        L.append("| 소스명 (ID) | 수집 방식 · 경로 상태 | 언어 | 갱신 | 상태 | 파이프라인 내 역할 |")
        L.append("|---|---|---|---|---|---|")
        for s in rows:
            L.append(f"| {s['name']} (`{s['id']}`) | {collect_path(s)} | {LANG[s['lang']]} "
                     f"| {s.get('frequency', '')} | {status_label(s)} | {s.get('role', '')} |")
        L.append("")
        L.append("### 상세")
        L.append("")
        for s in rows:
            L.append(f"**{s['name']}** — {TYPE_WORD[s['type']]} · {status_label(s)}  ")
            L.append(f"- 특징: {s.get('description', '')}  ")
            L.append(f"- 주요 다루는 내용: {s.get('topics', '')}  ")
            L.append(f"- 제약·비고: {constraints_full(s)}  ")
            url = card_url(s)
            if url:
                L.append(f"- 주소: {url}")
            L.append("")
        L.append("")

    # 마지막 티어 뒤의 여분 공백 줄 정리: 파일은 마지막 카드 다음 줄에서 끝난다
    while L and L[-1] == "":
        L.pop()
    return "\n".join(L) + "\n"


def main() -> int:
    data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    out = render(data.get("sources", []))
    DOC_PATH.write_text(out, encoding="utf-8", newline="\n")
    print(f"생성 완료: {DOC_PATH.relative_to(ROOT)} ({len(out.splitlines())}줄)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
