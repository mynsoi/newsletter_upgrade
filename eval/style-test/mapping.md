# 🔒 밀봉 — 모델↔글 매핑

> ## 평가 종료까지 열람 금지
>
> 이 파일을 먼저 읽으면 블라인드가 깨진다. `글A.md` ~ `글E.md`를 읽고 채점을 마친 뒤,
> 채점표를 `eval/scores/`에 저장한 **다음에** 연다.
> 배정은 `random.SystemRandom()`으로 뽑았고 회차 번호와 무관하다.

## 이번 회차는 대조 조건이 맞다

5회 모두 base 커밋 `376850a`에서 딴 워크트리(`st1`~`st5`)로 실행했다. 같은 재료
(`content/evidence/ai-productivity-paradox.json`), 같은 지시문(`eval/style-test/instruction.md`),
같은 판본의 `prompts/article_style.md`(228행)를 봤다. 앞선 시도에서 회차 간 base가
어긋나 폐기했던 문제는 해소됐다.

## 블라인드의 한계

`content/drafts/style-test-1.md` ~ `-5.md`에 모델명이 그대로 남아 있다. 원본은 측정
데이터라 지우지 않았다. **채점 전에 그 파일들과 `git log`를 보지 않는 것으로만
블라인드가 유지된다.**

---
---

## 매핑

| 블라인드 | 회차 | 생성 모델 |
|---|---|---|
| 글A | 회차 1 | Claude Fable 5.1 (claude-fable-5-1) |
| 글B | 회차 2 | Claude Opus 5 (claude-opus-5) |
| 글C | 회차 4 | Claude Sonnet 5 (claude-sonnet-5) |
| 글D | 회차 3 | Claude Opus 4.6 (claude-opus-4-6) |
| 글E | 회차 5 | Claude Sonnet 4.6 (claude-sonnet-4-6) |
