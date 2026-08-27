사용자가 제공한 URL을 수기 등록한다: $ARGUMENTS

절차:
1. URL의 성격을 보고 티어를 판단 (학술=T1, 컨설팅=T2, 저널=T3, 기업1차자료=T4, 뉴스=T5)
2. `python3 src/collectors/ingest_url.py <URL> --tier <티어>` 실행
3. 본문 추출 실패 시(페이월 등): 우회하지 말고, 정식 구독 계정으로 열람 후
   요지를 수기 입력하는 방법을 안내
4. 등록 성공 시 문서 ID와 함께 `make enrich` 실행 여부를 확인
