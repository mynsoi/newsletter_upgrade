수집 파이프라인 현황을 보고한다.

(2026-11-16 main에서 옮김 — 명령은 `pipeline/` 폴더에서 실행한다: `cd pipeline`)

절차:
1. `make stats` 실행 결과를 요약한다 (소스별 문서 수·판별 대기·카드·DB 용량).
2. 최근 일일 수집(GitHub Actions daily-collect) 결과와 열린 경보 이슈를 확인한다
   (`daily-collect-failure` · `inflow-alert` · `card-alert` 라벨).
3. 작업실 aside 수집의 최근 회차(`runs/aside/` 최신 report.json)에서 신규·격상·실패를 확인한다.
4. 이상이 있으면 원인 후보와 다음 조치를 3줄 이내로 정리해 보고한다.
