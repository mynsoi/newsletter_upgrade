# /ingest-file — 수집 파일 등재 (브라우저 경로 진입점)

브라우저 보조 수집(/browse-collect)이나 구독 열람으로 확보한 파일을 documents에 등재한다: $ARGUMENTS

절차:
1. 대상 파일의 frontmatter(source_id·url·title·published)와 본문이 갖춰졌는지 확인한다.
   본문은 원문 그대로여야 한다 — 요약·재구성된 텍스트는 등재하지 않는다 (절대 규칙 8).
2. `python src/collectors/ingest_file.py <파일경로>` 실행.
   - 저장은 store.py 경유: URL·내용 해시 중복 제거, summary_only 규칙 동일 적용
   - 처리된 파일은 같은 위치의 ingested/ 폴더로 이동됨
3. 결과(신규/중복/오류)를 보고하고, 신규 등재면 문서 id·본문 길이를 확인한다.
4. 유료 콘텐츠는 정식 구독 계정에서 확보한 것만 등재한다 (절대 규칙 6). 라이선스가
   불확실하면 등재 전에 담당자에게 확인한다.
