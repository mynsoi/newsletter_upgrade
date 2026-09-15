[테스트: 세그먼트 레이어] 기존 발행본에 레이어를 붙인다: $ARGUMENTS

이 커맨드는 draft.md ④(초안)와 ⑤(검증) 사이에 들어가는 실험 단계다. draft.md를 대체하지 않는다.

전제: prompts/article_style.md와 prompts/segment_layers.md를 먼저 읽는다.
작성 모델은 config/settings.yaml의 write_model. 실행 전 /model로 확인하고 초안 머리말에 기록.

④-L1 세그먼트 매핑 → content/angles/{slug}-layers.md
   - content/angles/{slug}.md의 앵글 3안을 읽고, 각 앵글이 임원/팀장/팀원 중 누구의 자리에서
     읽을 때 인사이트가 되는지 표로 정리한다. 근거 claim ID를 함께 적는다.
   - 선택된 앵글(발행본의 논지)은 코어의 논지로 고정한다. 나머지 앵글은 버리지 않고
     "그 세그먼트 레이어의 씨앗"으로 표시한다.
   - 어떤 세그먼트에 claim 근거가 없으면 "생략"으로 표시하고 이유를 한 줄 적는다.
   - 사용자 확인 후 진행.
④-L2 코어 재구성 → content/drafts/{slug}-v3-layers.md (1차 저장)
   - 발행본의 "## 우리 조직에 적용해본다면"에서 역할별 행동이 섞인 문단만 들어내고,
     공통 도입 문단(이론 요지·내부 자료 인용)과 마무리 문단은 코어로 남긴다.
   - 나머지 코어 본문은 논지·문단·claims 주석을 그대로 유지한다 (변수 고정). 문체 수정 금지.
④-L3 레이어 작성 → 같은 파일 (2차 저장)
   - ④-L1 표에서 "생략"이 아닌 세그먼트마다 segment_layers.md 규칙으로 300~400자 작성.
   - 레이어의 claims 주석은 evidence json에 있는 ID만. 새 출처 인용 금지.
   - 세 레이어를 쓴 뒤 스스로 대조한다: 각 레이어가 다른 레이어 없이도 완결되게 읽히는지,
     다른 역할과 이어 주려는 연결 문장("↳", "○○ 레이어", "팀장이 물을 때…" 식)이 없는지,
     주차·기간·횟수 처방이 없는지, 비유·조어로 개념을 대신한 표현이 없는지(segment_layers.md 레이어 내용 규칙).
   - 머리말에 기록: 코어 N자 / 레이어 각 N자 (공백 제외).
⑤ 검증은 draft.md ⑤를 그대로 따른다:
   python src/verify_article.py content/drafts/{slug}-v3-layers.md \
     --evidence content/evidence/{slug}.json \
     --out content/drafts/{slug}-v3-layers-verification.md
   주의: 40% 룰은 본문이 인용한 **고유 claim 수** 기준이다(verify_article.py — 문단 수가 아님).
   레이어가 새 claim을 더하면 비율이 바뀐다. 리포트의 최대 의존 출처 비율을
   발행본 리포트(mckinsey-insights 22%)와 나란히 기록한다.
