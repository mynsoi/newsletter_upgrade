전체 소스 수집을 실행한다.

절차:
1. `make validate` 실행 — 실패 소스가 있으면 결과를 보고하고, feed_url 수정이 필요한지 판단
2. `make collect` 실행 (첫 실행이거나 빠른 확인이 필요하면 `make collect-fast`)
3. `make stats`로 수집 결과 요약을 사용자에게 보고
4. 피드 실패가 반복되는 소스는 sources.yaml의 note에 기록하고 뉴스레터 경로 전환을 제안

주의: 페이월 우회를 시도하지 않는다. 본문 추출 실패는 정상 동작이다.
