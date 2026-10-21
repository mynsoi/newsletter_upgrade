사용자가 제공한 URL을 수기 등록한다: $ARGUMENTS

절차:
1. 소스 판별 확인: `python3 src/collectors/ingest_url.py <URL> --detect`
   - URL 도메인·경로로 config/sources.yaml의 정식 소스를 자동 판별해 출력한다
     (등록·네트워크 접속 없음). 정식 소스 글을 'manual'로 넣으면 참고자료에 기관명이
     빠지고 월간 소스 리뷰 인용 수도 발행처로 잡히지 않으므로 이 단계를 건너뛰지 않는다.
2. 등록 실행 — 판별 결과에 따라:
   - **소스로 판별됨** → `python3 src/collectors/ingest_url.py <URL>` (tier는 소스 tier 자동 적용)
   - **판별 실패지만 발행처가 sources.yaml에 있음**(예: 경로가 달라 안 잡힌 글, 학술 정전 백필)
     → `--source <소스ID>` 지정. 예: `--source academic-canon`
   - **정식 소스가 아님** → 티어를 판단해 `--tier <티어>` (학술=T1, 컨설팅=T2, 저널=T3,
     기업1차자료=T4, 뉴스=T5, 기본 T5). source_id는 'manual'로 저장된다
   - 소스가 정해진 상태에서 `--tier`가 그 소스 tier와 다르면 오류로 멈춘다. 정말 수기로
     넣어야 하면 `--source manual --tier <티어>`
3. 본문 추출 실패 시(페이월 등): 우회하지 말고, 정식 구독 계정으로 열람 후
   요지를 수기 입력하는 방법을 안내
4. 등록 성공 시 문서 ID·소스와 함께 `make enrich` 실행 여부를 확인
