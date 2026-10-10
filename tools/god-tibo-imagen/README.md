# god-tibo-imagen (그림 그리기 사본)

`scripts/image_candidates.py`가 그림을 그릴 때 부르는 gti 스크립트입니다.
원래 자리는 `~/.codex/skills/god-tibo-imagen/`이고, 그곳이 없는 PC(새 PC·Windows)에서는 이 사본을 씁니다.

- 출처: `god-tibo-imagen` 0.3.1 (npm, MIT 라이선스 — `vendor/god-tibo-imagen/package.json`)에 로컬 수정을 더한 스킬 사본.
  수정 내용: 모델을 `gpt-6-astra`로 고정(`vendor/god-tibo-imagen/src/config.js`의 `REQUIRED_CODEX_MODEL`, 멘토 2026-10-09 "gti는 무조건 gpt-6-astra").
- npm 원본 `gti`로 바꾸지 않습니다 — 원본은 기본 모델이 gpt-5.4라 400 오류가 납니다.
- ChatGPT로 로그인한 Codex 세션(`~/.codex/auth.json`, `codex login`)을 씁니다. 공개 API가 아니라 바뀔 수 있습니다(`vendor/god-tibo-imagen/NOTICE.md`).
- 필요한 것: Node.js만 (외부 패키지 없음).
