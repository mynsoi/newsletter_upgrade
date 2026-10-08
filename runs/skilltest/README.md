# 스킬 효과 테스트 (2026-10-08)

질문: 한국어 AI 문체 교정 스킬 4개가 실제로 글을 낫게 하는가.

## 워크트리 (`skens/mentor-lab-wt/`)

| 워크트리 | 스킬 | 설치 위치 (워크트리 안에서만 보임) | 실행 방식 |
|---|---|---|---|
| base | 없음 | — | `--tools ""` |
| yoonmoon | amondnet/yoonmoon (polish-all 등 6개) | `.claude/plugins/yoonmoon` | `--plugin-dir`, 도구 Skill·Read |
| im-not-ai | epoko77-ai/im-not-ai (humanize-korean) | `.claude/plugins/im-not-ai` | `--plugin-dir`, 도구 Skill·Read·Write·Bash·Agent (파이썬 진단 스크립트 실행) |
| avoid-ai-writing | conorbronsdon/avoid-ai-writing | `.claude/skills/avoid-ai-writing` | 도구 Skill·Read — **영어 기준 스킬**(스스로 그렇게 밝힘) |
| fluent-korean | snflkd/fluent-korean (스킬이 아니라 **출력 스타일**) | `.claude/output-styles/fluent-korean-not-coding.md` | `--settings outputStyle` |

- `.claude/`는 `.git/info/exclude`로 추적 제외 → 워크트리를 지우면 스킬도 같이 사라진다.
- 전역 스킬(korean-lover 등)은 모든 워크트리에 보인다. 스킬 실행에서는 쓸 스킬 이름을 지정하고, 실제 호출은 `<단계>.tools.txt`로 확인한다.
- 모델: 전부 `claude -p --model opus`, 세션 저장 안 함.

## 단계

- **A. 처음부터 쓰기**: 같은 지시문(`prompt-A.md` — 제 방식: 생각 후보 2 + 공냥이 18편 원문 + 보조 원문 + 경영일기 3편 문체 참고, 지킬 것 2개). 스킬 워크트리는 "다 쓴 뒤 해당 스킬로 다듬기"를 덧붙임. fluent-korean은 출력 스타일이 켜진 상태로 쓰기.
- **B. 같은 초안 다듬기**: base의 A 결과를 공통 초안으로, 각 워크트리가 자기 스킬로만 다듬음. base는 스킬 없이 다듬기(대조군). → 스킬 효과만 떼어 보기.

결과: `runs/skilltest/<워크트리>/<단계>.md` (최종 답) · `.jsonl` (전체 기록) · `.tools.txt` (부른 도구·스킬).

## 지우기

```bash
cd ~/01-projects/2026/mentoring/skens/mentor-lab
for n in base yoonmoon im-not-ai avoid-ai-writing fluent-korean; do
  git worktree remove --force ../mentor-lab-wt/$n && git branch -D wt/$n
done
```

## 결과 (2026-10-08)

### B. 같은 초안(base/A) 다듬기 — 스킬 효과만 떼어 본 것

| 워크트리 | 그대로 둔 문장 | 글자 유사도 | 실제로 바꾼 것 |
|---|---|---|---|
| base (스킬 없음, "소리 내 읽고 다듬기") | 58% | 0.95 | 조사·어미, 짧은 문장 합치기 |
| fluent-korean (출력 스타일) | 37% | 0.91 | 가장 많이 바꿈. 생략된 말을 채워 문장이 길어짐("직접 글을 쓰는 데 들이던 힘이 AI가 쓴 글을…") |
| yoonmoon (polish-all) | 86% | 0.99 | 낱말 바꾸기(질문→물음, 이야기→말, 세 개의 메일함→메일함 세 개) |
| im-not-ai (humanize-korean, light 경로) | 83% | 0.99 | 쉼표 제거가 대부분(스크립트), 결과 앞뒤에 ```markdown 코드 울타리가 섞여 나옴 |
| avoid-ai-writing | 97% | 1.00 | "그래서 저는 분명히 말하고 싶습니다" 한 문장만 삭제 |

- 다섯 곳 모두 "첫째·둘째·셋째" 나열, 경구형 마무리, 대비 구문 개수가 초안 그대로였다(ai_tells.py).
- 스킬 넷은 모두 "의미 불변·구조 유지·과윤문 금지"를 원칙으로 하는 **윤문(낱말·문장 단위) 도구**다. 이 초안은 번역투 표지("~를 통해·~에 의해")가 이미 0이라 손댈 게 거의 없다고 판단했다.
- 멘토 지적의 핵심(인사이트 없음, 한국어답지 않은 논리 전개, 나열·선언·경구 같은 구조 버릇)은 설계상 스킬이 건드리지 않는 영역이다.

### A. 처음부터 쓰기

- 다섯 편 모두 앞선 초안들보다 구체적(같은 원문을 깊게 판 효과). 편차는 스킬보다 매번 달라지는 초안 차이가 더 크다.
- 출력 스타일(fluent-korean)로 쓴 편만 나열·선언이 0이었다 — 표본 1개라 판단 보류.
