전체 소스 수집을 PC에서 수동 실행한다 (비상용 — 평소에는 GitHub Actions daily-collect가 매일 03:17 KST에 돈다).

(2026-11-16 main에서 옮김 — 명령은 `pipeline/` 폴더에서 실행한다: `cd pipeline`)

언제 쓰나: 예약 실행이 실패했거나 늦어져 그날 수집을 PC에서 대신 돌려야 할 때.
Actions를 수동으로 돌릴 수 있으면(`gh workflow run daily-collect`) 그쪽이 먼저다.

절차:
1. `make validate` 실행 — 실패 소스가 있으면 결과를 보고하고, feed_url 수정이 필요한지 판단
   (주의: validate는 sources.yaml note에 자동검증 메모를 쓴다 — 바뀐 내용을 확인한 뒤 커밋 여부를 정한다)
2. `make collect` 실행 (빠른 동작 확인만 필요하면 `make collect-fast`)
3. `make enrich`(관련성 판별·문서 카드) → `make embed`(카드 임베딩) 실행 여부를 사용자에게 확인한다 (API 비용 발생)
4. `make stats`로 수집 결과 요약을 사용자에게 보고
5. 피드 실패가 반복되는 소스는 sources.yaml의 note에 기록하고, aside 수집 편입이 맞는지 제안한다

하루 1회 보장 잠금:
- `make collect`은 `src/collectors/collect.py` 오케스트레이터를 통해 rss+api를 실행하며,
  `collection_runs` 테이블에 오늘 날짜(KST)를 선점한다. 이미 오늘 `completed` 기록이 있으면
  `"오늘 완료됨"`을 출력하고 아무 일도 하지 않는다 (Actions·PC 중복 실행 방지).
- 수집 도중 실패하면 그날은 `failed`로 남아 다음 실행이 자동 재시도한다 (완료로 잠기지 않음).
- 하루 1회 제한을 우회해야 하면 `python src/collectors/collect.py --force`. 관련성 판별은 문서 단위로
  원자적 선점하므로 두 프로세스가 동시에 돌아도 같은 문서를 중복 처리하지 않는다.

주의: 페이월·봇 차단을 우회하지 않는다. 본문 추출 실패(요약 대체)는 정상 동작이다.
DATABASE_URL이 없으면 SQLite 로컬 모드로 돈다 — 운영 DB에 넣으려면 DATABASE_URL이 있어야 한다.
