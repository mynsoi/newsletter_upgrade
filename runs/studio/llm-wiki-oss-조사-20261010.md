## 결론

**자동 증분 처리까지 원하면 `llm-wiki-compiler`, 가장 가볍게 Claude Code/Codex로 시작하려면 `Astro-Han/karpathy-llm-wiki`가 맞습니다.**

8개 후보의 README·스킬/구현 소스·라이선스·기본 브랜치 커밋 기록을 직접 읽었습니다. 저장소는 수정하거나 실행하지 않았습니다.

- 확인 시점: **2026-10-10 01:36~01:55 KST**
- 별 수: GitHub 공개 API 정확값으로 보완
- 커밋 날짜: 기본 브랜치의 실제 최신 커밋을 **KST**로 표시
- **한국어 원문 90편을 실제 투입한 품질·성능 시험은 하지 않았습니다.**
- 아래의 “지원”은 **실행 코드가 있는 경우와 에이전트 지침만 있는 경우를 구분**했습니다.

Karpathy 원문도 약 100개 원문·수백 페이지에서는 index 중심 운용을 설명하고, qmd는 wiki 생성기가 아니라 선택적인 검색 도구로 소개합니다. <citation refs="JpefxSHB-eWILYIH27jN8">현재 90편은 원 패턴이 상정한 중간 규모와 가깝습니다.</citation>

---

## 1. [atomicstrata/llm-wiki-compiler](https://github.com/atomicstrata/llm-wiki-compiler)

**MIT · 별 2,173 · 최신 커밋 2026-10-09, `3df3307`**

Hermes 스킬의 옛 링크 `atomicmemory/llm-wiki-compiler`는 현재 이 저장소로 이동합니다.

- **실행·모델:** Node.js 24 이상 CLI `llmwiki`, TypeScript SDK, MCP 서버, 로컬 뷰어. <citation refs="dOddRExDu9Ja34AsNdMk-">실제 소스가 `codex exec`를 호출합니다.</citation> Codex 로컬 로그인 경로에서는 OpenAI API 키를 요구하지 않습니다. Claude Code 로그인은 **Claude Agent SDK 경로**로 지원합니다.
- **중요한 모델 의존:** <citation refs="At7ZdYQBuipI8lZZVnKS2">Codex에는 임베딩 인터페이스가 없으므로 별도 임베딩 제공자를 명시해야 합니다. Ollama를 선택하면 API 키 없는 구성이 가능합니다.</citation> “Codex 구독만 설정하면 나머지도 모두 해결”되는 구조는 아닙니다.
- **저장:** `sources/` 원문 캡처본, `wiki/` Markdown, `.llmwiki/state.json` 등 상태 파일. 임베딩은 JSON/바이너리 파일이며 **필수 DB 서버는 없습니다.**
- **ingest/query/lint:** 모두 구현. 여러 원문이 같은 concept slug를 내면 하나의 페이지로 합칩니다. query/context와 출처 검증 lint도 있습니다. 다만 <citation refs="5t7lM8eJEIfwnblKtRlM5">중복 검사는 대소문자·공백을 정규화한 동일 제목 중심이고, orphan은 주로 원문 출처를 모두 잃은 페이지를 뜻합니다.</citation> **비슷한 뜻의 서로 다른 주제 자동 병합과 입링크 0개 검사 전용 기능은 확인 못 함.**
- **증분:** <citation refs="OYFljxpn5V1n2oGB7tkRk,b_D58m6sl6YknQZrs-Tui">파일 SHA-256을 저장해 변경 없는 원문의 재추출을 건너뜁니다. 단, 기존 주제 갱신에는 이전 관련 원문 내용도 다시 합쳐 투입합니다.</citation>
- **원문·출처:** 페이지 frontmatter의 `sources[]`를 코드가 작성하고, 본문에 파일·행 범위 인용을 붙입니다. **주제에서 기여 원문 목록을 꺼낼 기반이 가장 명확합니다.** 반면 <citation refs="p4OWN-QAmvczMqMeV7xr8">같은 출처를 재ingest하면 `sources/` 캡처본을 덮어쓸 수 있으므로 엄밀한 불변 저장소는 아닙니다.</citation>
- **한국어·규모:** 출력 언어 지정 옵션은 있고 중국어·일본어 예시가 있습니다. 한국어 개별 시험은 **확인 못 함**. 병렬 컴파일, 청킹, 임베딩 배치·캐시, 프롬프트 예산이 있습니다. 원문 본문 한도는 10만 문자, concept별 기본 입력 예산은 20만 문자입니다.

**약점:** 설정과 상태 관리가 다른 스킬형보다 복잡합니다. 의미적 주제 정리에는 별도 에이전트 판단이 필요합니다. README는 네이티브 Windows 검증·CI가 미완료라고 명시합니다.

직접 확인: [README](https://github.com/atomicstrata/llm-wiki-compiler#readme) · [Codex 구현](https://github.com/atomicstrata/llm-wiki-compiler/blob/main/src/providers/codex-agent.ts) · [페이지·원문 연결](https://github.com/atomicstrata/llm-wiki-compiler/blob/main/src/compiler/page-renderer.ts) · [라이선스](https://github.com/atomicstrata/llm-wiki-compiler/blob/main/LICENSE) · [커밋 기록](https://github.com/atomicstrata/llm-wiki-compiler/commits/main/)

## 2. [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki)

**MIT · 별 2,447 · 최신 커밋 2026-07-24, `eafcc77`**

- **실행·모델:** Agent Skills 문서·템플릿과 Python 근거 검사기. Claude Code, Codex CLI, Cursor, OpenCode를 명시합니다. 특정 API 키를 스킬 자체가 요구하지는 않지만 호스트 에이전트 인증·과금은 별개입니다. **`codex exec` 전용 실행 어댑터는 확인 못 함.**
- **저장:** `raw/`, `wiki/`, `index.md`, append-only `log.md`. **DB 불필요.**
- **ingest/query/lint:** 세 작업 모두 스킬로 정의됩니다. ingest에서 “같은 핵심 논지”라면 기존 주제 문서에 합칩니다. lint는 고립 페이지·모순·누락 연결을 보고하며 사실을 자동 수정하지 않습니다. Python 검사기는 report-only입니다.
- **증분:** **해시 freshness tracking과 예약 훅을 의도적으로 제외**했습니다. 신규·수정·논쟁·변화 없음 여부를 에이전트가 판단하는 방식이지, 새 파일만 자동 처리하는 엔진은 아닙니다.
- **원문·출처:** 원문 불변은 “읽고 수정하지 않는다”는 지침입니다. 강제 쓰기 차단은 **확인 못 함**. 주제 페이지에 **`Sources`와 `Raw` 상대경로 목록을 누적**합니다.
- **한국어·규모:** 한국어 지원·시험은 **확인 못 함**. README 자기보고는 **94개 wiki 문서·99개 원문·13개 주제**로 현재 용도와 비슷합니다. 수천 편 실측은 확인 못 함.

**약점:** 무인 증분 처리에는 별도 처리 완료 목록이 필요합니다. 근거 검사기는 특정 인용·날짜·숫자 패턴을 검사할 뿐, 한국어 의미나 사실을 전면 검증하지 않습니다.

직접 확인: [README](https://github.com/Astro-Han/karpathy-llm-wiki#readme) · [SKILL](https://github.com/Astro-Han/karpathy-llm-wiki/blob/main/SKILL.md) · [검사 코드](https://github.com/Astro-Han/karpathy-llm-wiki/blob/main/scripts/check_evidence.py) · [라이선스](https://github.com/Astro-Han/karpathy-llm-wiki/blob/main/LICENSE) · [커밋 기록](https://github.com/Astro-Han/karpathy-llm-wiki/commits/main/)

## 3. [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)

**MIT · 별 3,613 · 최신 커밋 2026-10-05, `17e29b4`**

최신 커밋은 **별 이력 차트 갱신**이며 기능 개발 커밋은 아닙니다.

- **실행·모델:** Claude Code/Codex/OpenCode/Gemini용 지침과 선택적인 Python 도구. 에이전트 경로는 별도 Python·모델 API 키 없이 사용할 수 있다고 설명합니다. **Python ingest·의미 lint는 별도 LLM API 호출 경로**입니다. `codex exec` 직접 연동은 확인 못 함.
- **저장:** 로컬 Markdown과 그래프 JSON/HTML. **필수 DB 없음.**
- **ingest/query/lint:** 모두 정의·구현되어 있습니다. 원문 요약, 엔티티·concept, index/overview/log를 갱신합니다. 구조 lint에 고립 페이지 검사가 있지만, Python 의미 검사는 **첫 20페이지 표본**만 읽습니다.
- **증분:** ingest 코드가 원문 해시를 계산하지만 곧바로 LLM을 호출합니다. **동일 해시를 비교해 원문 처리를 건너뛰는 manifest는 확인 못 함.** README의 SHA-256 캐시 설명은 그래프 갱신과 구분해야 합니다.
- **원문·출처:** 불변은 지침 중심입니다. `concept.sources[] → source 요약 → source_file: raw/...` 연결이 있습니다. 읽기 좋은 주제별 원문 목록을 반드시 출력하는 규칙은 보강해야 합니다.
- **한국어·규모:** 중국어 CJK 예제가 있습니다. 한국어 개별 검증, 수백·수천 편 처리량 시험은 **확인 못 함**.

**약점:** 새 원문만 처리하는 자동화가 불명확하고, 의미 lint 표본 제한이 큽니다. Python ingest의 페이지 덮어쓰기와 에이전트의 의미적 병합 판단을 동일한 안전장치로 보면 안 됩니다.

직접 확인: [README](https://github.com/SamurAIGPT/llm-wiki-agent#readme) · [AGENTS](https://github.com/SamurAIGPT/llm-wiki-agent/blob/main/AGENTS.md) · [ingest 코드](https://github.com/SamurAIGPT/llm-wiki-agent/blob/main/tools/ingest.py#L198-L241) · [lint 코드](https://github.com/SamurAIGPT/llm-wiki-agent/blob/main/tools/lint.py#L273-L298) · [라이선스](https://github.com/SamurAIGPT/llm-wiki-agent/blob/main/LICENSE) · [커밋 기록](https://github.com/SamurAIGPT/llm-wiki-agent/commits/main/)

## 4. [nvk/llm-wiki](https://github.com/nvk/llm-wiki)

**MIT · 별 1,402 · 최신 커밋 2026-10-02, `95a042c`, 기본 브랜치 `master`**

- **실행·모델:** Claude 중심 플러그인, Codex 패키징, portable AGENTS와 Python 구조 검사 CLI. 합성·query는 LLM 에이전트가 수행합니다. 단일 모델 강제는 없으며 **`codex exec` 전용 연동과 전체 무키 구성은 확인 못 함.**
- **저장:** 주제별 Markdown/YAML, JSON·JSONL 상태 파일. **필수 DB 없음.** 외부 datasets/DB 위치를 선택적으로 연결할 수 있습니다.
- **ingest/query/lint:** 모두 지원합니다. 기존 concept 갱신, topic·reference 구성, 고립 원문·페이지 검사와 구조적 자동 수선이 있습니다. 합칠 개념과 분리할 개념은 schema로 지시합니다.
- **증분:** 일반 compile은 **원문의 `ingested` 날짜와 `Last compiled` 날짜 비교**입니다. 같은 날 추가·부분 실패를 엄밀히 처리하는 방법은 확인 못 함. 컬렉션에는 별도로 `collection + upstream_id + revision/sha`와 manifest 규약이 있습니다.
- **원문·출처:** 본문 `Sources`와 정확한 `raw/...` frontmatter 경로를 사용합니다. 그러나 불변 선언과 달리 **lint 자동 수선에 원문 이동·메타데이터 변경 경로가 있고, inbox 처리에는 삭제 가능 규칙도 있습니다.**
- **한국어·규모:** 한국어 시험은 확인 못 함. 일부 source 경로 fallback의 `slugify`가 ASCII만 남겨 한글 충돌 위험이 있습니다. subwiki, archive, bulk limit/dry-run, streaming XML, 외부 datasets로 규모를 분리합니다. 수천 한국어 문서 실측은 확인 못 함.

**약점:** 현재 용도보다 운영 체계가 크고 복잡합니다. 원문 보존이 중요하면 `lint --fix`와 inbox 처리 규칙을 그대로 채택하기 어렵습니다. 고립 원문에 backlog 링크를 만드는 것은 주제 합성 완료가 아닙니다.

직접 확인: [README](https://github.com/nvk/llm-wiki#readme) · [compile 규칙](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/references/compilation.md) · [ingest 규칙](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/references/ingestion.md) · [lint 규칙](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/references/linting.md) · [실제 CLI](https://github.com/nvk/llm-wiki/blob/master/scripts/llm-wiki) · [라이선스](https://github.com/nvk/llm-wiki/blob/master/LICENSE) · [커밋 기록](https://github.com/nvk/llm-wiki/commits/master/)

## 5. [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)

**GPLv3 · 별 20,353 · 최신 커밋 2026-09-28, `48fd970`**

- **실행·모델:** Tauri/Rust+React **데스크톱 앱**. 일반 경로는 OpenAI·Anthropic·Google·Ollama 등의 모델 설정을 사용합니다. 실제 TypeScript transport에 **`codex exec --json` 호출 경로**가 있습니다. Rust spawn 본문과 실행 성공은 확인 못 함. Claude CLI transport 파일은 있지만 본문 검증은 확인 못 함.
- **저장:** 원문·wiki Markdown과 `.llm-wiki/` JSON 상태. **LanceDB는 선택사항**, 기본 비활성입니다. git 자동 관리 기능은 확인 못 함.
- **ingest/query/lint:** 모두 있습니다. 고립·깨진 링크·outlink 없는 페이지 검사, 의미 lint, 기존 페이지 병합을 구현했습니다. 의미 lint는 페이지 preview 등을 사용하며 전체 원문 검증은 아닙니다.
- **증분:** `.llm-wiki/ingest-cache.json`의 **SHA-256 + 산출물 존재**를 확인해 재처리를 건너뜁니다. 변경된 원문이나 산출물이 사라진 항목은 재처리합니다.
- **원문·출처:** 생성 파일을 `wiki/` 안으로 제한하는 코드가 있습니다. `sources[]`와 병합 시 출처 합집합을 유지합니다. 다만 사용자의 외부 원문 편집·삭제까지 막는 불변 저장소는 아닙니다.
- **한국어·규모:** **한국어 출력 옵션과 한중일 파일명 보존 코드 확인.** 큐, 폴더 감시, 점진 렌더링, 그래프 페이지네이션 등이 있습니다. 한국어 90편 품질·수천 편 처리량은 확인 못 함.

**약점:** 원하는 “CLI 작업실”보다 앱 중심입니다. 병합 실패 시 새 본문과 출처 배열 합집합으로 fallback하며 백업도 best effort여서 기존 본문 보존을 완전히 보장하지 않습니다.

직접 확인: [README](https://github.com/nashsu/llm_wiki#readme) · [Codex transport](https://github.com/nashsu/llm_wiki/blob/main/src/lib/codex-cli-transport.ts) · [증분 캐시](https://github.com/nashsu/llm_wiki/blob/main/src/lib/ingest-cache.ts) · [병합 코드](https://github.com/nashsu/llm_wiki/blob/main/src/lib/page-merge.ts) · [한국어 옵션](https://github.com/nashsu/llm_wiki/blob/main/src/lib/output-language-options.ts#L23) · [라이선스](https://github.com/nashsu/llm_wiki/blob/main/LICENSE) · [커밋 기록](https://github.com/nashsu/llm_wiki/commits/main/)

## 6. [sdyckjq-lab/llm-wiki-skill](https://github.com/sdyckjq-lab/llm-wiki-skill)

**MIT 표방, 라이선스 원문 확인 못 함 · 별 2,529 · 최신 커밋 2026-07-27, `efa2294`**

README 배지와 SKILL에는 MIT라고 쓰지만 **연결된 LICENSE는 404이고 GitHub API의 license도 null**입니다.

- **실행·모델:** 에이전트 스킬과 Bash/Python/Node 보조 스크립트. Claude Code·Codex 설치 경로를 문서화합니다. 호스트 모델을 사용하며 별도 특정 API 키 강제는 확인 못 함. **`codex exec` 실행 어댑터는 확인 못 함.** 별도 workbench는 개발 중입니다.
- **저장:** Markdown과 `.wiki-cache.json`. **필수 DB 없음.**
- **ingest/query/lint:** 모두 정의되어 있고 기계적 lint도 있습니다. 그러나 **1,000字 이하 짧은 원문은 주제 페이지 생성·갱신을 생략**하는 간소화 경로가 있습니다. Threads·LinkedIn 짧은 글을 주제로 묶으려는 요구와 직접 충돌합니다.
- **증분:** 상대경로와 원문 bytes의 SHA-256 캐시가 실제 구현돼 있습니다. 다만 **source 요약과 캐시 저장 뒤 주제·index 갱신이 진행**되므로 캐시 HIT가 전체 ingest 완료를 뜻하지는 않습니다.
- **원문·출처:** 원문 불변은 지침이며 강제 차단은 확인 못 함. topic 템플릿의 **素材汇总**가 제목·기여·source 요약을 나열하고, source의 `source_path`가 raw를 연결합니다.
- **한국어·규모:** 언어 설정은 **zh/en**, 한국어 모드는 확인 못 함. 관련 페이지만 읽기·부분 읽기·캐시 등이 있으나 배치 **5개마다 계속할지 확인**을 요구합니다. 의미 lint는 최근 10개+랜덤 10개 표본입니다.

**약점:** 라이선스 확인, 한국어 설정, 짧은 글의 주제 갱신, 무인 배치, 전체 ingest 완료 상태를 모두 보강해야 합니다. 그대로 도입하기에는 수정 부담이 큽니다.

직접 확인: [README](https://github.com/sdyckjq-lab/llm-wiki-skill#readme) · [SKILL](https://github.com/sdyckjq-lab/llm-wiki-skill/blob/main/SKILL.md) · [캐시 코드](https://github.com/sdyckjq-lab/llm-wiki-skill/blob/main/scripts/cache.sh) · [주제 템플릿](https://github.com/sdyckjq-lab/llm-wiki-skill/blob/main/templates/topic-template.md) · [LICENSE 404](https://github.com/sdyckjq-lab/llm-wiki-skill/blob/main/LICENSE) · [커밋 기록](https://github.com/sdyckjq-lab/llm-wiki-skill/commits/main/)

## 7. [NousResearch/hermes-agent의 llm-wiki 스킬](https://github.com/NousResearch/hermes-agent/blob/main/skills/research/llm-wiki/SKILL.md)

**MIT · 저장소 전체 별 252,228 · 저장소 최신 커밋 2026-10-10, `e0550c9`**

별과 최신 커밋은 **wiki 스킬만의 수치가 아니라 Hermes 전체 값**입니다.

- **실행·모델:** Hermes Agent가 수행하는 스킬입니다. Hermes는 여러 모델 제공자를 지원하지만 **이 스킬을 Claude Code/Codex CLI에서 직접 돌리는 공식 경로는 확인 못 함.**
- **저장:** wiki 자체는 Markdown 폴더이며 **DB 불필요**라고 명시합니다. 다만 Hermes 본체의 세션·기억 시스템과는 구분해야 합니다.
- **ingest/query/lint:** 모두 상세히 정의합니다. 기존 concept 갱신, 입링크 없는 페이지, 깨진 링크, 출처·frontmatter·모순·stale 검사를 지시합니다. 비슷한 주제를 자동 합치는 별도 명령은 확인 못 함.
- **증분:** raw frontmatter에 본문 SHA-256을 기록하고 동일 URL 재ingest 시 같으면 skip하도록 지시합니다. **독립 manifest runner가 아니라 에이전트 수행 규약**입니다.
- **원문·출처:** `sources[]`와 문단별 `^[raw/...]` 출처 표시를 정의합니다. 불변 선언과 변경된 동일 URL을 update하는 규칙이 공존하며 강제 쓰기 보호는 확인 못 함.
- **한국어·규모:** 한국어 언급·시험은 확인 못 함. 100페이지 이상 검색 보강, index 200항목 이상 topic-map, 200줄 이상 페이지 분할, 500개 log 항목 회전 규칙이 있습니다.

**약점:** 이미 Hermes를 쓰는 경우에는 자연스럽지만, wiki만을 위해 새 에이전트 런타임을 도입할 이유는 약합니다. 증분·불변성도 주로 규약에 의존합니다.

직접 확인: [README](https://github.com/NousResearch/hermes-agent#readme) · [스킬 본문](https://github.com/NousResearch/hermes-agent/blob/main/skills/research/llm-wiki/SKILL.md) · [라이선스](https://github.com/NousResearch/hermes-agent/blob/main/LICENSE) · [커밋 기록](https://github.com/NousResearch/hermes-agent/commits/main/)

## 8. [tobi/qmd](https://github.com/tobi/qmd)

**MIT · 별 30,297 · 최신 커밋 2026-10-06, `93d211f`**

**wiki 생성기 대신 검색 보조 도구로 평가해야 합니다.**

- **실행·모델:** 로컬 CLI·MCP·Node/Bun SDK. Claude Code 플러그인/MCP 설정을 명시합니다. Codex가 셸로 호출하는 연결은 가능성이 있지만 **Codex 전용 설정·`codex exec` 예시는 확인 못 함**. 기본 모델 검색은 로컬 GGUF 모델을 사용하며 외부 API 키는 필요 없습니다. 도입 시 모델 파일 다운로드가 필요합니다.
- **저장:** Markdown은 원본으로 남지만 검색에 **SQLite FTS5+sqlite-vec가 필수**입니다. 기본 위치는 `~/.cache/qmd/index.sqlite`.
- **ingest/query/lint:** 파일 인덱싱과 query는 지원합니다. **주제 페이지 합성 ingest, 주제 병합, wiki lint는 확인 못 함.** index cleanup을 wiki 유지보수와 혼동하면 안 됩니다.
- **증분:** 경로·mtime·크기·hash를 저장합니다. 변동 없는 파일은 읽기를 생략하고 변경 후보는 SHA-256을 비교합니다.
- **원문·출처:** 검색 결과에 파일 경로·문서 ID·스니펫·행 번호를 반환합니다. 하지만 **주제별 영구 원문 목록을 생성·완전하게 유지하지는 않습니다.** 컬렉션 update hook에 전처리 명령을 둘 수 있어 모든 구성이 무조건 read-only인 것도 아닙니다.
- **한국어·규모:** 최신 코드에 **Hangul 포함 CJK 문자 정규화**가 있습니다. 한국어 형태소 분석기는 아닙니다. README는 기본 embeddinggemma의 CJK 한계를 설명하고 한국어 포함 다국어 Qwen3 임베딩을 권고합니다. 증분 인덱싱·청킹·배치 메모리 제한·컬렉션 필터가 있으나 한국어 검색 품질 시험은 확인 못 함. 10MB 초과 파일은 인덱싱에서 제외합니다.

**약점:** 이 도구만 붙여서는 주제 wiki가 생기지 않습니다. DB와 로컬 모델 관리 부담이 추가되므로 현재 90편 단계의 필수 구성으로 보기는 어렵습니다.

직접 확인: [README](https://github.com/tobi/qmd#readme) · [증분·CJK 코드](https://github.com/tobi/qmd/blob/main/src/store.ts) · [모델 코드](https://github.com/tobi/qmd/blob/main/src/llm.ts) · [라이선스](https://github.com/tobi/qmd/blob/main/LICENSE) · [커밋 기록](https://github.com/tobi/qmd/commits/main/)

---

## 우리 용도 기준 최종 추천

### 1순위: **llm-wiki-compiler**
**수백 편으로 늘어날 때도 반복 가능한 CLI 파이프라인이 우선이라면 선택하겠습니다.**

실제 `codex exec`, 해시 기반 증분 추출, 코드가 작성하는 주제별 `sources[]`, 인용 검사·상태 관리가 가장 잘 맞습니다. 단, **별도 임베딩 백엔드**와 **의미적 주제 병합·입링크 고립 검사**를 보완해야 합니다.

### 2순위: **Astro-Han/karpathy-llm-wiki**
**현재 90편에서 사람이 주제 선택을 함께하며 가볍게 시작하려면 선택하겠습니다.**

Markdown+git·Claude Code/Codex 스킬이라는 구성이 단순하고, 기존 주제에 원문을 누적하는 규칙과 출처 목록이 명확합니다. 대신 신규 파일 처리 완료 목록과 원문 무결성 확인은 별도로 필요합니다.

**qmd는 수백 편 이후 검색이 불편해질 때 붙일 보조 후보**입니다. 처음부터 필수로 넣지는 않겠습니다.

어느 쪽이든 뉴스레터용으로는 **주제 페이지에 원문 제목·작성자·게시일·URL·raw 경로 목록을 필수화하고, lint는 기본 보고 전용으로 두는 보강**을 권합니다. 이는 제 권장 운영 규칙이지, 모든 후보에 이미 보장된 기능은 아닙니다. 코드 라이선스와 수집한 원문·모델 서비스의 이용 권리는 별개입니다.

![직접 확인한 compiler 저장소 화면](C:/Users/c/.aside/u/0/sessions/2026-10-10_Lxc1X8a2vZcinSlR/tmp/compiler-read-proof.png)