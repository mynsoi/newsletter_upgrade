"""카드 단계 경보(src/enrich/card_health.py, 2026-11-12)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enrich.card_health import check, main  # noqa: E402

OK = "[카드] 대상 100건 (model=m, limit=100)\n  카드 [x] 제목 → 사례형\n[카드] 98건 생성, 건너뜀 2건\n"


def test_normal_day_has_no_alert():
    assert check(OK) == []
    assert check("[카드] 대상 0건 (model=m, limit=100)\n") == []
    assert check("[카드] card_enabled: false — 건너뜀. 정상 종료.") == []


def test_all_failed_alerts_with_reason():
    log = ("[카드] 대상 5건 (model=m, limit=100)\n"
           "  카드 건너뜀 [hrdive] 제목 — NotFoundError: model (다음 실행에서 재시도)\n"
           "[카드] 0건 생성, 건너뜀 5건\n")
    [a] = check(log)
    assert "전부 실패" in a and "NotFoundError" in a


def test_half_failed_alerts_only_with_enough_targets():
    assert check("[카드] 대상 10건 (m)\n[카드] 4건 생성, 건너뜀 6건\n")
    assert check("[카드] 대상 3건 (m)\n[카드] 1건 생성, 건너뜀 2건\n") == []


def test_stage_error_and_missing_stage_alert():
    assert "단계 오류" in check("[카드] 대상 3건\n[카드] 단계 오류 — 건너뜀: KeyError: x\n")[0]
    assert "기록이 없다" in check("판별 통과 3건\n")[0]
    assert "결과 줄이 없다" in check("[카드] 대상 7건 (m)\n  카드 [x] a\n")[0]


def test_main_prints_alert_lines_and_always_exits_zero(tmp_path, capsys):
    p = tmp_path / "enrich.log"
    p.write_text("[카드] 대상 5건\n[카드] 0건 생성, 건너뜀 5건\n", encoding="utf-8")
    assert main([str(p)]) == 0
    assert capsys.readouterr().out.startswith("카드 경보:")
    assert main([str(tmp_path / "none.log")]) == 0
