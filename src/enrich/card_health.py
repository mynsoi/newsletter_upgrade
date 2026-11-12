"""카드 단계 경보 — 일일 실행 로그(logs/enrich.log)에서 카드 단계가 조용히 망가진 신호를 찾는다 (2026-11-12).

카드 실패는 판별 결과(exit code)를 바꾸지 않는다(relevance.main). 실패한 문서는 다음 실행에서 다시
대상이 되니 하루 이틀은 괜찮지만, 모델 이름 변경·크레딧 소진·응답 형식 변화처럼 매일 전량 실패하는
고장은 워크플로가 계속 "성공"으로 끝나 아무도 모른다. 작업실은 카드만 읽으므로 새 글이 서재에 안 들어온다.

경보 조건 (하나라도 맞으면 경보 줄을 출력):
- "[카드] 단계 오류" — 카드 단계 전체가 예외로 끝났다.
- 대상이 있었는데 0장 생성 — 전량 실패.
- 건너뜀이 생성 이상 — 절반 넘게 실패(대상 4건 이상일 때만, 적은 건수의 우연한 실패는 무시).
- 카드 단계 줄이 아예 없다 — 판별이 카드 단계까지 가지 못했다(판별 실패는 따로 실패 이슈로 잡힌다).
card_enabled: false로 끈 날은 경보하지 않는다.

python src/enrich/card_health.py logs/enrich.log  → 경보 줄을 출력(없으면 아무것도 안 함), 항상 exit 0
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGETS_RE = re.compile(r"\[카드\] 대상 (\d+)건")
RESULT_RE = re.compile(r"\[카드\] (\d+)건 생성, 건너뜀 (\d+)건")
MIN_TARGETS_FOR_RATIO = 4


def check(log: str) -> list[str]:
    """경보 문장 목록. 정상이면 빈 목록."""
    if "[카드] card_enabled: false" in log:
        return []
    alerts = []
    errors = [line.strip() for line in log.splitlines() if "[카드] 단계 오류" in line]
    if errors:
        alerts.append(f"카드 단계 오류로 카드를 하나도 만들지 못했다: {errors[-1]}")
        return alerts
    targets = TARGETS_RE.findall(log)
    if not targets:
        return ["카드 단계 기록이 없다 — 판별이 카드 단계까지 가지 못했다"]
    n = int(targets[-1])
    if n == 0:
        return []
    result = RESULT_RE.findall(log)
    if not result:
        return [f"카드 대상 {n}건인데 결과 줄이 없다 — 카드 단계가 중간에 멈췄다"]
    made, skipped = (int(x) for x in result[-1])
    if made == 0:
        reasons = [line.strip() for line in log.splitlines() if "카드 건너뜀 [" in line][:3]
        alerts.append(f"카드 대상 {n}건 전부 실패(0장 생성)" + ("" if not reasons else " — 예: " + " / ".join(reasons)))
    elif n >= MIN_TARGETS_FOR_RATIO and skipped >= made:
        alerts.append(f"카드 대상 {n}건 중 {skipped}건 실패(생성 {made}장) — 절반 이상 실패")
    return alerts


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0] if argv else "logs/enrich.log")
    if not path.exists():
        print(f"카드 경보: {path} 없음 — 판별 단계가 돌지 않았다")
        return 0
    for a in check(path.read_text(encoding="utf-8", errors="replace")):
        print(f"카드 경보: {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
