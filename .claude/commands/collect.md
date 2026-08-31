전체 소스 수집을 실행한다.

절차:
1. `make validate` 실행 — 실패 소스가 있으면 결과를 보고하고, feed_url 수정이 필요한지 판단
2. `make collect` 실행 (첫 실행이거나 빠른 확인이 필요하면 `make collect-fast`)
3. `make stats`로 수집 결과 요약을 사용자에게 보고
4. 피드 실패가 반복되는 소스는 sources.yaml의 note에 기록하고 뉴스레터 경로 전환을 제안

하루 1회 보장 잠금:
- `make collect`은 `src/collectors/collect.py` 오케스트레이터를 통해 rss+api를 실행하며,
  `collection_runs` 테이블에 오늘 날짜를 선점한다. 이미 오늘 `completed` 기록이 있으면
  `"오늘 완료됨"`을 출력하고 아무 일도 하지 않는다 (GitHub Actions·다른 PC 중복 실행 방지).
- 수집 도중 실패하면 그날은 `failed`로 남아 다음 실행이 자동 재시도한다 (완료로 잠기지 않음).
- 하루 1회 제한을 우회해야 하면 `python src/collectors/collect.py --force` (또는 개별
  워커에 `--force`). claim 추출(`make enrich`)은 문서 단위로 원자적 선점하므로 두 프로세스가
  동시에 돌아도 같은 문서를 중복 처리하지 않는다.

주의: 페이월 우회를 시도하지 않는다. 본문 추출 실패는 정상 동작이다.
