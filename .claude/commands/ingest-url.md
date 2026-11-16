사용자가 제공한 URL을 수기 등록한다: $ARGUMENTS

(2026-11-16 main에서 옮김 — 명령은 모두 `pipeline/` 폴더에서 실행한다: `cd pipeline`)

절차:
1. 소스 판별 확인: `python src/collectors/ingest_url.py <URL> --detect`
   - URL 도메인·경로로 config/sources.yaml의 정식 소스를 자동 판별해 출력한다
     (등록·네트워크 접속 없음). 정식 소스 글을 'manual'로 넣으면 서재에서 발행처가
     빠지므로 이 단계를 건너뛰지 않는다.
2. 등록 실행 — 판별 결과에 따라:
   - **소스로 판별됨** → `python src/collectors/ingest_url.py <URL>` (tier는 소스 tier 자동 적용)
   - **판별 실패지만 발행처가 sources.yaml에 있음**(예: 경로가 달라 안 잡힌 글)
     → `--source <소스ID>` 지정
   - **정식 소스가 아님** → 티어를 판단해 `--tier <티어>` (학술=T1, 컨설팅=T2, 저널=T3,
     기업1차자료=T4, 뉴스=T5, 기본 T5). source_id는 'manual'로 저장된다
   - 소스가 정해진 상태에서 `--tier`가 그 소스 tier와 다르면 오류로 멈춘다. 정말 수기로
     넣어야 하면 `--source manual --tier <티어>`
3. 본문 추출 실패 시(페이월·봇 차단 등): 우회하지 않는다. 정식 구독 계정으로 열람할 수 있는
   글이면 사용자에게 알린다. aside 격상 소스(작업실 `sources/aside_sources.json`)면 요약으로
   등록해 두면 aside가 다음 회차에 전문으로 바꾼다.
4. 등록 성공 시 문서 ID·소스를 보고한다. 판별·카드는 다음 일일 수집(03:17 KST)이 처리한다 —
   바로 필요하면 `make enrich` 실행 여부를 사용자에게 확인한다(API 비용 발생).
