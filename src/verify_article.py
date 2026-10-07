"""아티클 검증 — 실사용 기준 (A2).

evidence 파일 전체가 아니라 **본문이 실제로 인용한 claim**만으로 강제 조건을 재계산한다.
본문 각 문단 뒤의 `<!-- claims: ID, ID -->` 주석이 사용 근거의 유일한 원본이다.

검사 항목
  1. 미등록 claim/출처 — 본문이 evidence에 없는 claim ID나 출처를 인용하면 실패(문장 지목)
  2. 독립 출처 3곳 이상 (사용 claim 기준)
  3. 상반 stance — optimistic·cautious 각 1건 이상 (CLAUDE.md 절대 규칙 2)
  4. 단일 출처 40% 초과 금지 (기획서 6.3)
  5. 수치 대조 — 본문 수치가 사용 claim의 metric/text에 있는지 (절대 규칙 3)
     · 달력 연도·참고자료 섹션은 면제(서지 정보)
     · 액션 문단의 기간·횟수(N주·주 N회 등)는 "처방 값"으로 분류해 대조하지 않는다.
       액션 판정은 섹션 이름이 아니라 문단의 액션 마커("리더가 할 일" 등)로 한다 —
       소제목을 메시지 문장으로 쓰라는 문체 지침과 충돌하지 않도록.
  6. 내부 자료 인용 대조 — 본문 직접 인용을 internal_docs 원문과 문구 대조
     · 문구 일치까지만 기계 검증. 발언 맥락 왜곡 여부는 사람 확인 항목이다.
     · 내부 자료를 인용한 문단에 연도 표기가 없으면 "내부 자료 시점 미표기"로 경고한다
       (article_style 5절 — 연례 행사·정기 발행물은 어느 해 것인지가 근거의 일부다).
  7. 참고자료 — 실사용 문서만 남기고, 올바른 목록을 리포트에 생성 (CDATA 래퍼 제거)
     · 한 출처 안에서 제목만으로 구분되지 않는 문서에는 발행일을 병기한다
       (같은 제목 앞부분을 쓰는 별개 글 — 예: josh-bersin의 Supermanager 2편)
  8. 작성 모델 — 초안 머리말의 모델 표기를 읽어 리포트 머리에 남긴다 (검사가 아니라 기록.
     config/settings.yaml의 write_model과 대조할 수 있도록)

포맷 프로파일 (2026-10-07 — docs/column-format-design.md)
  초안 머리말의 `format: column`(또는 `<!-- format: column -->`)이나 --format으로 고른다.
  표기가 없으면 article — 기존 초안·발행본은 그대로 검증된다.
  · article: 위 1~8 그대로 (독립 출처 3곳+ · 상반 stance · 단일 출처 40% 이하)
  · column : 독립 출처 2곳+ · 통념→반전 구조 또는 상반 stance · 단일 출처 50% 이하 ·
             분량 상한 · 명시 인용 상한 · 수치 상한. 문단 수·문단 길이·소제목·세 줄 요약·
             레이어·어미는 경고로만 알린다. 1·5~7(미등록·수치 대조·내부 인용·참고자료)은 공통.

사용:
  python src/verify_article.py content/drafts/{slug}.md [--evidence ...] [--out ...] [--stdout]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"

CLAIM_COMMENT_RE = re.compile(r"<!--\s*claims?:\s*([^>]+?)\s*-->", re.I)
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
# 정량 주장 후보 — 단위가 붙거나 범위로 쓰인 수치만 본다(목록 번호·연도 단독은 제외)
NUMBER_RE = re.compile(r"\d[\d,.]*\s*(?:~\s*\d[\d,.]*\s*)?(?:%|퍼센트|배|년|개월|주|일|명|건|점|만|억|조|배로)")
# 달력 연도(2026년·1999년)는 서지·시점 표기지 근거 수치가 아니다 — 기간("20~30년")과 구분한다
CALENDAR_YEAR_RE = re.compile(r"^(?:19|20)\d{2}\s*년$")
# 내부 자료(SKMS·경영층 메시지)는 claims 테이블을 거치지 않으므로 claim 대조 대상이 아니다
INTERNAL_REF_HINTS = ("내부:", "skms", "신년사", "internal/")
# 근거를 끌어다 쓰는 전형적 표현 — 주석 없는 문단에 있으면 claim 주석 누락을 의심한다
EVIDENTIAL_RE = re.compile(
    r"에\s*따르면|(?:연구|조사|설문|실험|보고서|분석|통계)\s*(?:결과|에서)|메타\s*분석"
    r"|보고(?:됐|된|되었)|관측(?:됐|된|되었)|실측(?:됐|된|되었)"
    r"|according to|study (?:finds|shows)|research shows", re.I)

MIN_INDEPENDENT_SOURCES = 3
MAX_SINGLE_SOURCE_RATIO = 0.40

# 칼럼 프로파일 (docs/column-format-design.md — 레퍼런스 20편 실측 eval/column-reference-analysis.md)
COLUMN_MIN_SOURCES = 2
COLUMN_MAX_SINGLE_SOURCE_RATIO = 0.50
COLUMN_LENGTH = (1000, 1400)          # 공백 제외 — 20편 중앙값 1,185자 기준 (2026-10-07 확정)
COLUMN_MAX_NAMED_CITATIONS = 2        # 연구자·기관 이름을 밝힌 출처
COLUMN_MAX_NUMBERS = 2                # 근거 수치 (연도·처방 값 제외)
COLUMN_PARAGRAPHS = (12, 16)
COLUMN_PARAGRAPH_LEN = (80, 150)
FORMATS = ("article", "column")
FORMAT_RE = re.compile(r"^\s*(?:-\s*)?(?:format|포맷)\s*[:：]\s*([A-Za-z]+)\s*$", re.M | re.I)
# 칼럼의 조언 어미("~해 보세요")도 처방 문단으로 본다. article 판정에는 쓰지 않는다(불변).
COLUMN_ACTION_RE = re.compile(r"(?:해|어|아|여)\s*보세요|보면\s*어떨까요")
# 통념→반전 구조 — 통념을 세우는 말과 그것을 꺾는 말. 같은 문단이나 바로 다음 문단에 있으면
# 구조가 있다고 본다(글 앞 절반 안에서만). 결정적 휴리스틱이라 미검출은 사람이 다시 본다.
CONVENTION_RE = re.compile(
    r"흔히|대개|대부분|으레|당연히|통념|많은\s*(?:사람|리더|팀장|기업|조직|분)"
    r"|믿(?:습니다|는|고|어|죠)|여깁니다|여기(?:는|죠|고)|생각합니다|기대합니다|알려져")
TURN_RE = re.compile(r"(?:^|[\s.?!])(?:하지만|그러나|그런데|오히려|반대로|정작|사실은|실제로는)"
                     r"|(?:이|가)\s*아니라")
# 명시 인용 판정 — 고유명사는 원어로 쓴다(article_style 2절). 괄호 밖 로마자 고유명사가
# 있는 근거 문단을 "이름을 밝힌 인용"으로 본다. 괄호 안은 개념 영문 병기라 제외한다.
LATIN_NAME_RE = re.compile(r"\b[A-Z][A-Za-z&.\-]+")
LATIN_NAME_STOP = {"AI", "HR", "IT", "CEO", "KPI", "LLM", "GPT", "ChatGPT", "OKR", "SK", "SKMS",
                   "AX", "DX", "PM", "ERP", "Q", "B", "A", "C"}
# 칼럼 톤 — 지시·당위 어미 금지("~해 보세요"류 조언형만), 구어체 종결 혼용
COLUMN_BANNED_ENDING_RE = re.compile(
    r"(?:해야|어야|아야|여야)\s*합니다|명심|바랍니다|하십시오|하시기\s*바랍니다")
COLUMN_COLLOQUIAL_RE = re.compile(r"죠[.?!]|[는은인]데요|거든요|네요[.?!]")
# 수치 대조·출처 검사를 면제하는 섹션 (처방 값·서지 정보)
EXEMPT_HEADING_HINTS = ("시도할 것", "참고자료", "액션", "리더용", "실무자용",
                        "적용해본다면", "적용한다면", "제언")
# 액션·제언 문단 — 소제목을 메시지 문장으로 쓰라는 문체 지침(article_style 4절) 때문에
# 섹션 이름만으로는 못 찾는다. 문단 자체의 마커로도 인식한다.
# 박스 구조("리더가 할 일")뿐 아니라 제언형 산문("~해볼 수 있습니다")도 잡는다.
ACTION_MARKER_RE = re.compile(
    r"(?:리더|실무자|팀장|구성원|매니저|담당자)\s*(?:가|는|들이|들은)?\s*할\s*일"
    r"|리더용|실무자용|시도할\s*것|확인\s*지표|점검\s*지표"
    r"|적용해\s*본다면|적용한다면"
    r"|해\s*볼\s*수\s*있습니다|해\s*보는\s*것|시작해\s*볼|정해\s*둡?니다|적어\s*둡?니다"
    r"|권합니다|제안합니다|충분합니다")
# 처방 값 — 액션에서 "언제까지·몇 번"을 정하는 기간·횟수 단위. 근거 수치가 아니므로
# 우연히 claim 숫자에 매칭돼 "근거 있음"으로 잘못 통과하는 일이 없도록 따로 분류한다.
PRESCRIPTIVE_UNIT_RE = re.compile(r"^\d[\d,.]*\s*(?:주|개월|일|년|회|건|개|차례|분|시간)$")
# 본문의 직접 인용 — 내부 자료(경영층 발언 등) 원문 대조 대상
QUOTE_RE = re.compile(r"[\"“]([^\"“”]{10,200})[\"”]")
# 초안 머리말의 작성 모델 표기 — YAML(`model: x`)과 HTML 주석(`<!-- 모델: x -->`) 둘 다 받는다.
# 회차마다 머리말 형식이 갈려서 한쪽만 보면 놓친다.
WRITE_MODEL_RE = re.compile(
    r"^\s*(?:-\s*)?(?:write_?model|model|모델|작성\s*모델)\s*[:：]\s*(.+?)\s*$", re.M | re.I)
# 시점 표기 — 내부 자료를 인용한 문단에 연도가 있는지 본다 (2026년 / 2026 / '26년 아님)
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
# 내부 문서 제목에서 이 문서를 특정하는 낱말만 골라낸다. 짧거나 흔한 말은 오탐이 된다
# ("CEO", "메시지"가 걸리면 무관한 문단까지 내부 인용으로 잡힌다).
TITLE_TOKEN_STOP = {"ceo", "패널토의", "메시지", "발표", "자료", "보고", "회의", "말씀",
                    "토의", "간담회", "워크숍", "워크샵", "세미나", "가이드", "지침", "문서",
                    "타운홀미팅", "상반기", "하반기", "wrap", "script", "vision", "system",
                    "management", "why", "next", "free", "human", "resource", "session"}
# 조사·어미가 붙은 어절은 고유명사가 아니라 서술형 제목의 조각이다("사례를", "중심으로").
# 이런 말로 문단을 찾으면 무관한 본문이 걸린다.
PARTICLE_TAIL_RE = re.compile(r"(?:의|를|을|와|과|로|으로|에|에서|는|은|이|가|도|만|과의|와의)$")
# 이론 카드가 들어오는 출처 id. 참고자료에서 이론 카드 형식으로 낸다.
THEORY_SOURCE = "theory-canon"
# sources.yaml의 name이 매체명이 아니라 파이프라인 분류 라벨인 출처
# (academic-canon="학술 정전(수기 백필)", manual=수동 등록). 여러 발행처의 글이 섞여
# 들어오므로 출처 단위 기관명을 붙이면 틀린 표기가 된다 — 기관명 없이 제목·링크만 낸다.
REF_NAME_SKIP = {"academic-canon", "manual"}

# 참고자료에서 문서를 특정하는 제목 앞부분의 길이. 검사 7의 문서명 매칭과 같은 값을 쓴다 —
# 이 범위가 겹치는 두 문서는 목록에서 구분되지 않으므로 발행일을 병기한다.
REF_TITLE_KEY_LEN = 14
# RSS CDATA 래퍼가 제목에 섞여 들어온 경우 (bain-insights 등) 리포트에서는 벗겨 쓴다
CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def clean_title(title: str) -> str:
    """CDATA 래퍼·잉여 공백을 벗긴 문서 제목."""
    if not title:
        return title
    return CDATA_RE.sub(r"\1", title).strip()


@dataclass
class Segment:
    """문단 하나와 그 문단이 인용한 claim ID."""
    heading: str
    text: str
    claim_ids: list[str] = field(default_factory=list)
    line: int = 0

    @property
    def exempt(self) -> bool:
        """섹션 이름 기반 면제 (참고자료·액션 섹션)."""
        return any(h in self.heading for h in EXEMPT_HEADING_HINTS)

    @property
    def is_action(self) -> bool:
        """액션 문단인가 — 섹션 이름 또는 문단 안의 액션 마커로 판정."""
        return self.exempt or bool(ACTION_MARKER_RE.search(self.text))


@dataclass
class Issue:
    level: str      # "fail" | "warn"
    kind: str
    message: str
    where: str = ""


def load_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data.get("claims", [])}


def load_internal_docs() -> list[dict]:
    """internal_docs에서 api_eligible=1 문서를 읽어온다 (인용 원문 대조용).

    DB에 붙지 못하면 빈 목록을 반환한다 — 검증 자체는 DB 없이도 돌아야 하므로
    내부 인용 대조만 "확인 불가"로 남기고 나머지 검사는 그대로 진행한다.
    """
    try:
        from db import connect
        conn = connect()
        rows = conn.execute(
            "SELECT id, title, speaker, body, effective_date "
            "FROM internal_docs WHERE api_eligible = 1"
        ).fetchall()
        conn.close()
        return [{"id": r["id"], "title": r["title"], "speaker": r["speaker"],
                 "body": r["body"] or "", "effective_date": r["effective_date"]}
                for r in rows]
    except Exception:  # noqa: BLE001 — DB 없음·스키마 미적용 등은 치명적이지 않다
        return []


def load_document_dates() -> dict[tuple[str, str], str]:
    """(source_id, 제목) → 발행일(YYYY-MM-DD). DB를 못 읽으면 빈 dict.

    참고자료에서 제목만으로 구분되지 않는 문서를 발행일로 갈라 놓기 위한 것이다
    (예: josh-bersin의 "The Rise Of The Supermanager"와 "…: A New Role In The World of AI"는
    URL·발행일·본문이 다른 별개 글인데 제목 앞부분이 같다).
    """
    try:
        from db import connect
        conn = connect()
        rows = conn.execute(
            "SELECT source_id, title, published_at FROM documents "
            "WHERE title IS NOT NULL AND published_at IS NOT NULL"
        ).fetchall()
        conn.close()
        return {(r["source_id"], clean_title(r["title"])): str(r["published_at"])[:10]
                for r in rows}
    except Exception:  # noqa: BLE001 — DB 없이도 검증은 돌아야 한다
        return {}


def load_document_meta() -> dict[tuple[str, str], dict]:
    """(source_id, 제목) → {"url", "author", "year"}. DB를 못 읽으면 빈 dict.

    참고자료 목록 생성(검사 7·리포트 6장)이 쓴다. 하이퍼링크는 documents.url만 쓰고,
    url이 없으면 링크 없이 제목만 낸다 — 없는 주소를 만들지 않는다.
    """
    try:
        from db import connect
        conn = connect()
        rows = conn.execute(
            "SELECT source_id, title, url, author, published_at FROM documents "
            "WHERE title IS NOT NULL"
        ).fetchall()
        conn.close()
        return {(r["source_id"], clean_title(r["title"])): {
            "url": (r["url"] or "").strip(),
            "author": (r["author"] or "").strip(),
            "year": str(r["published_at"])[:4] if r["published_at"] else "",
        } for r in rows}
    except Exception:  # noqa: BLE001 — DB 없이도 검증은 돌아야 한다
        return {}


def reader_name(name: str) -> str:
    """sources.yaml의 운영용 이름 → 독자용 매체명 (2026-10-05).

    운영용 이름에 붙은 구분 꼬리를 뗀다: " - 분야"(arXiv - Human-Computer Interaction → arXiv),
    띄어 쓴 괄호 한정어(Brookings (Future of Work) → Brookings, OECD (고용·AI) → OECD).
    붙여 쓴 괄호는 이름의 일부라 남긴다(DBR(동아비즈니스리뷰)). 꼬리를 떼면 빈 이름이 되면 원래 이름.
    """
    short = re.split(r"\s+-\s+", name, maxsplit=1)[0]
    short = re.sub(r"\s+[(（][^()（）]*[)）]\s*$", "", short).strip()
    return short or name


def source_ref_names() -> dict[str, str]:
    """source_id → 참고자료에 적을 독자용 매체·기관명.

    sources.yaml에 `ref_name`이 있으면 그것을, 없으면 `name`을 reader_name()으로 줄여 쓴다.
    """
    out: dict[str, str] = {}
    try:
        data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}
    except OSError:
        return out
    for s in data.get("sources", []):
        sid = s.get("id")
        ref = (s.get("ref_name") or "").strip()
        name = ref or reader_name((s.get("name") or "").strip())
        if sid and name:
            out[sid] = name
    return out


def format_reference(source: str, title: str, meta: dict | None,
                     names: dict[str, str] | None = None,
                     date_override: str = "") -> str:
    """참고자료 한 줄. 2026-10-05 형식 확정 — draft.md ⑤·article_style 5절과 같은 규칙.

    · 외부 문서: `매체·기관명, [제목](url) (연도)` — url이 없으면 링크 없이 제목만.
      (2026-10-05 다듬기: 연도 앞 쉼표·끝 마침표 제거, 매체명은 독자용 축약 — reader_name)
      매체·기관명을 모르거나 REF_NAME_SKIP 출처면 기관명을 붙이지 않는다(지어내지 않는다).
    · 이론 카드(theory-canon): 접두어 없이 `이론명(영문명, 저자 연도)` 평문, 링크 없음.
    · 내부 자료는 이 함수를 쓰지 않는다 — 제목 평문으로 따로 싣는다.
    """
    meta = meta or {}
    # 블로그·매체 제목에 붙어 오는 사이트명 꼬리("… | Worklytics", "… | DBR")를 벗긴다 —
    # 매체명을 앞에 따로 적으므로 그대로 두면 같은 이름이 두 번 나온다.
    title = re.sub(r"\s*\|\s*[^|]{1,30}$", "", clean_title(title) or "").strip() or "(문서명 없음)"

    if source == THEORY_SOURCE:
        # DB 제목 "직무특성모형 (Job Characteristics Model)" → 한글명 + 영문명으로 가른다
        m = re.match(r"^(.*?)\s*[(（]\s*(.+?)\s*[)）]\s*$", title)
        ko, en = (m.group(1).strip(), m.group(2).strip()) if m else (title, "")
        inner = ", ".join(x for x in (en, " ".join(
            x for x in (meta.get("author", ""), meta.get("year", "")) if x)) if x)
        return f"{ko}({inner})" if inner else ko

    linked = f"[{title}]({meta['url']})" if meta.get("url") else title
    name = "" if source in REF_NAME_SKIP else (names or {}).get(source, "")
    # 같은 출처에 제목이 구분되지 않는 문서가 둘 이상이면 연도 대신 발행일 전체를 적는다
    # (josh-bersin의 "The Rise Of The Supermanager" 두 편처럼 제목 앞부분이 같은 별개 글).
    year = date_override or meta.get("year", "")
    parts = [p for p in (name, linked) if p]
    line = ", ".join(parts)
    return f"{line} ({year})" if year else line


def reference_lines(used_docs: dict[str, set[str]], meta: dict[tuple[str, str], dict],
                    names: dict[str, str] | None = None,
                    internal_titles: list[str] | None = None,
                    dates: dict[tuple[str, str], str] | None = None) -> list[str]:
    """실사용 문서의 참고자료 목록. 배열 순서: 외부 → 이론 → 내부.

    외부·이론은 구분이 링크 유무로 드러난다(외부만 하이퍼링크). 내부 자료는 제목 평문.
    """
    names, dates = names or {}, dates or {}
    external, theory = [], []
    for src in sorted(used_docs):
        titles = sorted(clean_title(t) for t in used_docs[src])
        collided = {k for k in (_ref_key(t) for t in titles)
                    if sum(1 for t in titles if _ref_key(t) == k) > 1}
        for title in titles:
            day = dates.get((src, title), "") if _ref_key(title) in collided else ""
            line = format_reference(src, title, meta.get((src, title)), names, day)
            (theory if src == THEORY_SOURCE else external).append(line)
    return external + theory + list(internal_titles or [])


def _ref_key(title: str) -> str:
    """참고자료 대조가 쓰는 제목 식별 범위 — 이 범위가 같으면 목록에서 구분되지 않는다."""
    return re.split(r"[(（]", clean_title(title))[0].strip().lower()[:REF_TITLE_KEY_LEN]


def reference_titles(source: str, docs, dates: dict[tuple[str, str], str] | None = None) -> list[str]:
    """한 출처의 참고자료 표기 목록.

    같은 출처 안에서 제목이 서로 구분되지 않는 문서(앞부분이 같아 `_ref_key`가 겹치는 경우)
    에만 발행일을 병기한다. 발행일을 모르면 제목 그대로 둔다 — DB 없이 돌 때도 깨지지 않게.
    """
    dates = dates or {}
    titles = sorted(clean_title(d) or "(문서명 없음)" for d in docs)
    collided = {k for k in (_ref_key(t) for t in titles)
                if sum(1 for t in titles if _ref_key(t) == k) > 1}
    out = []
    for t in titles:
        day = dates.get((source, t))
        out.append(f"{t} ({day})" if day and _ref_key(t) in collided else t)
    return out


def _squash(s: str) -> str:
    """공백·문장부호 차이를 무시한 대조용 정규화."""
    return re.sub(r"[\s·,.\"'“”‘’]+", "", s or "")


def parse_write_model(md: str, head_lines: int = 15) -> str:
    """초안 머리말에서 작성 모델 표기를 읽는다. 없으면 빈 문자열.

    머리말 형식이 회차마다 달라(YAML 블록 / HTML 주석 / 한 줄에 여러 필드) 앞부분만
    훑고 첫 매칭을 쓴다. 본문에 모델 이름이 나와도 집지 않도록 범위를 머리말로 제한한다.
    검사가 아니라 기록이므로, 없으면 실패시키지 않고 빈 값을 돌려준다.
    """
    head = "\n".join(md.splitlines()[:head_lines])
    # "<!-- 모델: x · 생성일: y -->"처럼 한 줄에 여러 필드가 오는 형태를 풀어 준다
    flat = re.sub(r"<!--|-->", "\n", head)
    flat = re.sub(r"\s+·\s+", "\n", flat)
    m = WRITE_MODEL_RE.search(flat)
    if not m:
        return ""
    return m.group(1).strip().strip("\"'")


def parse_format(md: str, head_lines: int = 15) -> str:
    """초안 머리말의 포맷 표기(`format: column`). 없거나 모르는 값이면 article.

    기본값을 article로 두는 것은 머리말에 포맷이 없는 기존 초안·발행본이 예전 기준 그대로
    검증되게 하려는 것이다. 새 초안의 기본 포맷(column)은 draft.md가 머리말에 적는다.
    """
    head = "\n".join(md.splitlines()[:head_lines])
    flat = re.sub(r"\s+·\s+", "\n", re.sub(r"<!--|-->", "\n", head))
    m = FORMAT_RE.search(flat)
    fmt = m.group(1).lower() if m else "article"
    return fmt if fmt in FORMATS else "article"


def _body_paragraphs(segments: list["Segment"]) -> list["Segment"]:
    """칼럼 형식 검사 대상 문단 — 참고자료·제목 줄을 뺀 본문 문단."""
    return [s for s in segments
            if "참고자료" not in s.heading and not s.text.lstrip().startswith("# ")]


def find_reversal(paras: list["Segment"]) -> "Segment | None":
    """통념→반전 구조가 시작되는 문단. 글 앞 절반에서 통념 표지 뒤(같은·다음 문단)에
    반전 표지가 오면 그 통념 문단을 돌려준다. 없으면 None."""
    half = paras[:max(2, (len(paras) + 1) // 2)]
    for i, seg in enumerate(half):
        if not CONVENTION_RE.search(seg.text):
            continue
        nxt = paras[i + 1].text if i + 1 < len(paras) else ""
        if TURN_RE.search(seg.text) or TURN_RE.search(nxt):
            return seg
    return None


def named_entities(text: str) -> list[str]:
    """괄호 밖 로마자 고유명사(기관·인물·매체). 개념 영문 병기(괄호 안)와 흔한 약어는 뺀다."""
    outside = re.sub(r"[(（][^)）]*[)）]", " ", text)
    return [w for w in LATIN_NAME_RE.findall(outside) if w.rstrip(".-") not in LATIN_NAME_STOP]


def _title_tokens(title: str) -> list[str]:
    """내부 문서를 특정하는 제목 낱말 — 간접 서술(인용부호 없는 언급)을 잡기 위한 것.

    "2026 이천포럼 CEO 패널토의" → ["이천포럼"]. 연도가 섞인 어절("2026년"),
    조사가 붙은 어절("사례를", "회장의"), 흔한 낱말은 버린다. 남는 게 없으면 빈
    목록이고, 그 문서는 간접 서술로 찾지 않는다.
    """
    toks = re.split(r"[\s·,()\[\]—–\-/_:]+", clean_title(title) or "")
    return [t for t in toks
            if len(t) >= 3
            and not YEAR_RE.search(t)                 # "2026년"은 아무 문단에나 걸린다
            and not PARTICLE_TAIL_RE.search(t)
            and t.lower() not in TITLE_TOKEN_STOP]


def _is_internal_ref(ref: str, docs: list[dict] | None) -> bool:
    """참고자료 한 줄이 내부 자료인지. 접두어와 제목 둘 다로 판별한다.

    2026-10-05 형식 개정으로 내부 자료에서 "내부:" 접두어가 사라졌다. 접두어만 보면
    내부 자료가 외부 문서로 잡혀 "참고자료 실사용 없음" 경고가 뜨므로, internal_docs의
    제목과도 대조한다. 예전 판본(접두어 있음)도 그대로 통과하도록 둘 다 본다.
    """
    low = ref.lower()
    if any(h in low for h in INTERNAL_REF_HINTS):
        return True
    squashed_ref = _squash(ref)
    for d in (docs or []):
        t = _squash(clean_title(d.get("title") or ""))
        if t and t in squashed_ref:
            return True
    return False


def _declared_internal_docs(references: list[str], docs: list[dict]) -> list[dict]:
    """참고자료가 가리키는 내부 문서만 골라낸다 (접두어 없이 제목으로도 알아본다).

    간접 서술을 제목 낱말로 찾을 때, 내부 문서 전체(수십 건)를 대상으로 하면 "에이전트",
    "인프라" 같은 제목 낱말이 무관한 문단에 걸린다. 아티클이 참고자료에 스스로 밝힌
    문서로 후보를 좁히면 그 오탐이 사라진다. 직접 인용 대조(9)는 이 제한을 받지 않는다.
    """
    internal_refs = [r for r in references if _is_internal_ref(r, docs)]
    out = []
    for d in docs:
        title = clean_title(d.get("title") or "")
        squashed = _squash(title)
        toks = _title_tokens(title)
        for ref in internal_refs:
            if (squashed and squashed in _squash(ref)) or                sum(1 for t in toks if t in ref) >= 2:
                out.append(d)
                break
    return out


def _doc_year(doc: dict) -> str:
    """내부 자료의 시점 — 머리말 date(effective_date)의 연도. 없으면 제목에서 찾는다."""
    m = YEAR_RE.search(str(doc.get("effective_date") or ""))
    if not m:
        m = YEAR_RE.search(clean_title(doc.get("title") or ""))
    return m.group(0) if m else ""


def source_aliases() -> dict[str, str]:
    """sources.yaml의 name·id → source_id 별칭표 (본문 출처 표기 탐지용)."""
    out: dict[str, str] = {}
    try:
        data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}
    except OSError:
        return out
    for s in data.get("sources", []):
        sid = s.get("id")
        if not sid:
            continue
        out[sid.lower()] = sid
        name = (s.get("name") or "").strip()
        if name:
            out[name.lower()] = sid
            # "DBR(동아비즈니스리뷰)" → "DBR"
            short = re.split(r"[(（]", name)[0].strip()
            if len(short) >= 3:
                out[short.lower()] = sid
    return out


# 편집자 노트(<!-- note --> … <!-- /note -->, 제목과 세 줄 요약 사이) — 개편 인사말 같은 편집 공지.
# 근거 영역도 분량도 아니므로 검증·분량 계산에서 통째로 뺀다(줄 번호는 유지). 2026-10-05 도입.
NOTE_RE = re.compile(r"<!--\s*note\s*-->.*?<!--\s*/note\s*-->", re.DOTALL)
SEGMENT_RE = re.compile(r"<!--\s*segment:\s*([\w-]+)\s*-->")


def strip_note(md: str) -> str:
    """note 구간을 같은 줄 수의 빈 줄로 바꾼다 — 리포트의 행 번호가 원고와 어긋나지 않게."""
    return NOTE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), md)


def measure_length(md: str) -> dict[str, int]:
    """분량(공백 제외 글자 수). {"core": N, "<역할>": N, ...}

    세는 범위: 제목(# 줄)·주석·참고자료 절·note 구간을 뺀 본문. 마크다운 기호(**, ##, -)는
    그대로 센다 — 그동안 머리말에 적어 온 분량과 같은 기준이다(final5 코어 1800·리더 311·팀원 324).
    레이어는 segment 표지부터 그 뒤 첫 claims 주석까지다.
    """
    text = strip_note(md).split("\n## 참고자료")[0]
    out: dict[str, int] = {"core": 0}
    role = ""
    for line in text.splitlines():
        m = SEGMENT_RE.search(line)
        if m:
            role = m.group(1)
            out.setdefault(role, 0)
            continue
        if role and CLAIM_COMMENT_RE.search(line):
            role = ""
            continue
        if line.startswith("# "):
            continue
        n = len(re.sub(r"\s", "", re.sub(r"<!--.*?-->", "", line)))
        out[role or "core"] += n
    return out


def parse_article(md: str) -> tuple[list[Segment], list[str]]:
    """문단과 뒤따르는 claims 주석을 짝짓는다. 반환: (문단 목록, 참고자료 항목)."""
    segments: list[Segment] = []
    references: list[str] = []
    heading = ""
    buf: list[str] = []
    buf_line = 0

    def flush(claim_ids: list[str] | None = None) -> None:
        text = "\n".join(buf).strip()
        if text:
            segments.append(Segment(heading, text, claim_ids or [], buf_line))
        buf.clear()

    for i, raw in enumerate(md.splitlines(), 1):
        line = raw.rstrip()
        m_head = HEADING_RE.match(line)
        if m_head:
            flush()
            heading = m_head.group(1).strip()
            continue
        m_claim = CLAIM_COMMENT_RE.search(line)
        if m_claim:
            ids = [c.strip() for c in re.split(r"[,\s]+", m_claim.group(1)) if c.strip()]
            flush(ids)
            continue
        if line.startswith("<!--"):        # slug·유산 표기 등 다른 주석은 본문이 아님
            continue
        if not line.strip():
            flush()
            continue
        if "참고자료" in heading and line.strip().startswith("-"):
            references.append(line.strip().lstrip("- ").strip())
        if not buf:
            buf_line = i
        buf.append(line)
    flush()
    return segments, references


def _first_sentence(text: str, limit: int = 70) -> str:
    """표·목록에 넣어도 깨지지 않도록 한 줄로 접은 첫 문장."""
    flat = re.sub(r"\s+", " ", text.strip()).replace("|", "\\|")
    s = re.split(r"(?<=[.!?。])\s|(?<=다)\s", flat)[0]
    return (s[:limit] + "…") if len(s) > limit else s


def _column_checks(md: str, segments: list[Segment], body: list[Segment],
                   used_segments: list[Segment], evidence: dict, numbers: list,
                   length: dict[str, int], aliases: dict[str, str],
                   reversal: Segment | None, issues: list[Issue]) -> dict:
    """칼럼 프로파일 형식 검사. 상한(분량·명시 인용·수치)은 실패, 형태·어미는 경고.

    명시 인용은 출처 단위로 센다 — 근거 문단에 괄호 밖 로마자 고유명사나 sources.yaml의
    출처 이름이 있으면 그 문단이 인용한 출처를 "이름을 밝힌 인용"으로 본다. 이름 없이
    근거를 쓴 문단의 출처는 익명 요약으로 센다(claims 주석은 둘 다 똑같이 단다).
    """
    def where(seg: Segment) -> str:
        return f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"

    # 분량 — 코어(레이어 없음) 기준
    core = length.get("core", 0)
    lo, hi = COLUMN_LENGTH
    if core > hi:
        issues.append(Issue("fail", "분량 초과", f"공백 제외 {core}자 — 칼럼 상한 {hi}자"))
    elif core < lo:
        issues.append(Issue("warn", "분량 미달", f"공백 제외 {core}자 — 칼럼 하한 {lo}자"))

    # 명시 인용
    named: dict[str, list[str]] = {}          # source_id → 문단에서 찾은 이름
    anonymous: set[str] = set()
    for seg in used_segments:
        srcs = {evidence[c].get("source") for c in seg.claim_ids if c in evidence}
        low = seg.text.lower()
        names = named_entities(seg.text) + [a for a in aliases if len(a) >= 3 and a in low]
        for sid in srcs:
            if names:
                named.setdefault(sid, [])
                named[sid] += [n for n in names if n not in named[sid]]
            else:
                anonymous.add(sid)
    anonymous -= set(named)
    if len(named) > COLUMN_MAX_NAMED_CITATIONS:
        issues.append(Issue("fail", "명시 인용 초과",
                            f"이름을 밝힌 출처 {len(named)}곳({', '.join(sorted(named))}) — "
                            f"칼럼은 {COLUMN_MAX_NAMED_CITATIONS}곳까지. 나머지는 익명 요약으로 푼다"))
    elif not named:
        issues.append(Issue("warn", "명시 인용 없음",
                            "연구자·기관 이름을 밝힌 인용이 없다 — 칼럼은 1~2곳을 이름으로 밝힌다"))

    # 수치 — 근거 수치만 센다(연도·처방 값은 numbers에 없거나 prescriptive)
    evid_numbers = list(dict.fromkeys(tok for _, tok, st in numbers if st != "prescriptive"))
    if len(evid_numbers) > COLUMN_MAX_NUMBERS:
        issues.append(Issue("fail", "수치 초과",
                            f"근거 수치 {len(evid_numbers)}개({', '.join(evid_numbers)}) — "
                            f"칼럼은 {COLUMN_MAX_NUMBERS}개까지"))

    # 형태 — 경고
    # 제목(# 한 줄)은 소제목이 아니다 — ## 이하만 센다
    headings = [m.group(1).strip() for m in re.finditer(r"^#{2,6}\s+(.*)$", md, re.M)
                if "참고자료" not in m.group(1)]
    summary = any("세 줄 요약" in h for h in headings) or any(
        s.text.lstrip("*# ").startswith("세 줄 요약") for s in body)
    layered = bool(SEGMENT_RE.search(md))
    if summary:
        issues.append(Issue("warn", "세 줄 요약 있음", "칼럼은 세 줄 요약을 두지 않는다"))
    if headings:
        issues.append(Issue("warn", "소제목 있음",
                            f"칼럼은 소제목 0개 — {', '.join(h[:20] for h in headings)}"))
    if layered:
        issues.append(Issue("warn", "레이어 있음", "칼럼은 세그먼트 레이어를 쓰지 않는다"))
    p_lo, p_hi = COLUMN_PARAGRAPHS
    if not p_lo <= len(body) <= p_hi:
        issues.append(Issue("warn", "문단 수", f"본문 {len(body)}문단 — 칼럼 기준 {p_lo}~{p_hi}"))
    l_lo, l_hi = COLUMN_PARAGRAPH_LEN
    off = [(s, len(re.sub(r"\s", "", s.text))) for s in body]
    off = [(s, n) for s, n in off if not l_lo <= n <= l_hi]
    for seg, n in off:
        issues.append(Issue("warn", "문단 길이", f"{n}자 — 칼럼 기준 {l_lo}~{l_hi}자", where(seg)))

    # 톤 — 지시·당위 어미 금지, 구어체 종결 혼용
    text = "\n".join(s.text for s in body)
    banned = COLUMN_BANNED_ENDING_RE.findall(text)
    for seg in body:
        m = COLUMN_BANNED_ENDING_RE.search(seg.text)
        if m:
            issues.append(Issue("warn", "지시·당위 어미",
                                f"“{m.group(0)}” — 칼럼 조언은 “~해 보세요”류로 쓴다", where(seg)))
    colloquial = len(COLUMN_COLLOQUIAL_RE.findall(text))
    if not colloquial:
        issues.append(Issue("warn", "구어체 종결 없음",
                            "~죠·~인데요·~거든요가 한 번도 없다 — 칼럼 톤은 혼용이다"))

    return {
        "core": core, "named": named, "anonymous": sorted(anonymous),
        "numbers": evid_numbers, "paragraphs": len(body), "paragraph_off": len(off),
        "headings": headings, "summary": summary, "layered": layered,
        "banned": len(banned), "colloquial": colloquial,
        "reversal_line": reversal.line if reversal else None,
    }


def verify(md: str, evidence: dict, internal_docs: list[dict] | None = None,
           doc_dates: dict[tuple[str, str], str] | None = None,
           doc_meta: dict[tuple[str, str], dict] | None = None,
           fmt: str | None = None) -> dict:
    """실사용 기준 검증 결과를 dict로 반환.

    internal_docs를 주면 본문의 직접 인용을 내부 자료 원문과 대조한다(문구 일치까지만 —
    발언 맥락 왜곡 여부는 사람 확인 항목이다, CLAUDE.md 문체 규칙).
    fmt는 포맷 프로파일(article|column). None이면 초안 머리말에서 읽는다(parse_format).
    """
    fmt = fmt if fmt in FORMATS else parse_format(md)
    column = fmt == "column"
    md = strip_note(md)          # 편집자 노트는 근거 영역이 아니다
    segments, references = parse_article(md)
    used_segments = [s for s in segments if s.claim_ids]
    issues: list[Issue] = []

    def is_action(seg: Segment) -> bool:
        # 칼럼은 조언 어미("~해 보세요")도 처방 문단으로 본다. article 판정은 그대로다.
        return seg.is_action or (column and bool(COLUMN_ACTION_RE.search(seg.text)))

    # 1) 미등록 claim ID — 본문이 evidence에 없는 근거를 인용한 경우
    used_ids: list[str] = []
    for seg in used_segments:
        for cid in seg.claim_ids:
            if cid not in evidence:
                issues.append(Issue(
                    "fail", "미등록 claim",
                    f"evidence에 없는 claim ID `{cid}`를 인용",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))
            else:
                used_ids.append(cid)

    used = [evidence[c] for c in dict.fromkeys(used_ids)]     # 순서 유지 중복 제거
    unused = [c for cid, c in evidence.items() if cid not in set(used_ids)]

    # 2) 본문이 인용한 출처 표기 검사
    aliases = source_aliases()
    evidence_sources = {c.get("source") for c in evidence.values()}
    for seg in segments:
        if seg.exempt:
            continue
        seg_sources = {evidence[c].get("source") for c in seg.claim_ids if c in evidence}
        low = seg.text.lower()
        for alias, sid in aliases.items():
            if len(alias) < 3 or alias not in low:
                continue
            if sid not in evidence_sources:
                issues.append(Issue(
                    "fail", "미등록 출처",
                    f"evidence에 없는 출처 `{sid}`를 본문에서 인용",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))
            elif seg_sources and sid not in seg_sources:
                issues.append(Issue(
                    "warn", "출처-근거 불일치",
                    f"문단이 `{sid}`를 언급하지만 이 문단의 claim 출처는 {sorted(seg_sources)}",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행"))

    # 3~5) 사용 claim 기준 강제 조건
    sources = [c.get("source", "?") for c in used]
    counts: dict[str, int] = {}
    for s in sources:
        counts[s] = counts.get(s, 0) + 1
    stances = {c.get("stance") for c in used}
    top_source, top_n = (max(counts.items(), key=lambda kv: kv[1]) if counts else ("-", 0))
    ratio = (top_n / len(used)) if used else 0.0

    min_sources = COLUMN_MIN_SOURCES if column else MIN_INDEPENDENT_SOURCES
    max_ratio = COLUMN_MAX_SINGLE_SOURCE_RATIO if column else MAX_SINGLE_SOURCE_RATIO
    opposed = {"optimistic", "cautious"} <= stances
    body = _body_paragraphs(segments)
    reversal = find_reversal(body) if column else None

    if len(counts) < min_sources:
        issues.append(Issue("fail", "독립 출처 부족",
                            f"사용 claim의 독립 출처 {len(counts)}곳 — {min_sources}곳 이상 필요"))
    if column:
        # 칼럼은 통념→반전 구조가 상반 관점의 역할을 한다. 둘 중 하나면 통과.
        if not (opposed or reversal):
            issues.append(Issue("fail", "통념→반전 구조 없음",
                                "글 앞 절반에서 통념→반전 구조를 찾지 못했고 사용 claim에 상반 "
                                f"stance도 없음 ({sorted(s for s in stances if s)}) — 둘 중 하나 필요"))
        elif not reversal:
            issues.append(Issue("warn", "통념→반전 구조 미검출",
                                "상반 stance로 대체 통과 — 칼럼 골격(통념→반전)이 본문에 있는지 사람 확인"))
    elif not opposed:
        issues.append(Issue("fail", "상반 stance 없음",
                            f"사용 claim의 stance {sorted(s for s in stances if s)} — "
                            "optimistic·cautious 각 1건 이상 필요"))
    if ratio > max_ratio:
        issues.append(Issue("fail", "단일 출처 편중",
                            f"`{top_source}` {top_n}/{len(used)}건 = {ratio:.0%} "
                            f"— {max_ratio:.0%} 초과"))

    # 6) 수치 대조 — 사용 claim의 metric/text에 근거가 있는지
    haystack = " ".join((c.get("metric") or "") + " " + (c.get("text") or "") for c in used)
    hay_digits = set(re.findall(r"\d[\d,.]*", haystack))
    # status: "ok"(근거 있음) | "fail"(근거 없음) | "prescriptive"(처방 값 — 대조 대상 아님)
    numbers: list[tuple[Segment, str, str]] = []
    for seg in segments:
        if "참고자료" in seg.heading:      # 서지 정보 — 통째 면제
            continue
        for token in NUMBER_RE.findall(seg.text):
            tok = token.strip()
            if CALENDAR_YEAR_RE.match(tok):             # 연도 표기는 서지 정보 — 근거 수치 아님
                continue
            # 액션 문단의 기간·횟수는 실행 처방으로 제안한 값이다. 근거 대조를 하면
            # 한 자리 숫자가 claim의 큰 수에 부분 일치해 "근거 있음"으로 잘못 통과한다.
            if is_action(seg) and PRESCRIPTIVE_UNIT_RE.match(tok):
                numbers.append((seg, tok, "prescriptive"))
                continue
            digits = re.findall(r"\d[\d,.]*", tok)
            ok = all(any(d.rstrip(".,") in h or h in d.rstrip(".,") for h in hay_digits)
                     for d in digits) if digits else True
            numbers.append((seg, tok, "ok" if ok else "fail"))
            if not ok:
                issues.append(Issue(
                    "fail", "수치 근거 없음",
                    f"본문 수치 “{tok}”가 사용 claim의 metric·text에 없음",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    # 7) 참고자료 — 실사용 문서만
    used_docs: dict[str, set[str]] = {}
    for c in used:
        # 수집 단계에서 섞여 들어온 CDATA 래퍼는 벗겨서 싣는다 (참고자료에 그대로 나가지 않도록)
        used_docs.setdefault(c.get("source", "?"), set()).add(
            clean_title(c.get("doc") or "") or "(문서명 없음)")
    for ref in references:
        low = ref.lower()
        if _is_internal_ref(ref, internal_docs or []):  # 내부 자료는 claim 대조 대상이 아님
            continue
        by_source = any(sid in low or alias in low
                        for alias, sid in aliases.items() if sid in used_docs)
        # 문서명 매칭은 괄호 앞 제목만 본다("심리적 안전감 (Psychological Safety)" → "심리적 안전감")
        by_doc = any(_ref_key(doc) in low
                     for docs in used_docs.values() for doc in docs
                     if len(re.split(r"[(（]", doc)[0].strip()) >= 4)
        if not (by_source or by_doc):
            issues.append(Issue("warn", "참고자료 실사용 없음",
                                f"사용 claim과 연결되지 않는 참고자료 항목 — 실사용만 남긴다: “{ref[:60]}”"))

    # 8) 근거 주석 누락 의심 — 주석 없는 문단인데 정량·인용 표현이 있으면 사람 검토로 넘긴다
    missing_marks: list[tuple[Segment, str]] = []
    for seg in segments:
        if seg.claim_ids or "참고자료" in seg.heading:
            continue
        reasons = []
        if EVIDENTIAL_RE.search(seg.text):
            reasons.append("인용 표현")
        # 액션 문단의 처방 값은 근거 주석 대상이 아니다 (인용 표현만 본다).
        # 섹션 이름이 아니라 문단의 액션 마커로 판정하므로 소제목이 메시지 문장이어도 걸린다.
        nums = [t.strip() for t in NUMBER_RE.findall(seg.text)
                if not CALENDAR_YEAR_RE.match(t.strip())
                and not (is_action(seg) and PRESCRIPTIVE_UNIT_RE.match(t.strip()))]
        if nums:
            reasons.append(f"수치({', '.join(nums[:3])})")
        if reasons:
            missing_marks.append((seg, " · ".join(reasons)))
            issues.append(Issue(
                "warn", "근거 주석 누락 의심",
                f"{' · '.join(reasons)}이 있는데 `<!-- claims: ... -->` 주석이 없음",
                f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    # 9) 내부 자료 인용 대조 — 본문의 직접 인용이 내부 문서 원문과 문구까지 일치하는지
    quotes: list[dict] = []
    docs = internal_docs or []
    for seg in segments:
        # 액션 문단의 따옴표는 인용이 아니라 확인지표에 이름을 붙인 표현이다
        # ("재배치한 시간으로 새로 시작한 일"). 대조 대상으로 잡으면 오탐만 쌓인다.
        if "참고자료" in seg.heading or is_action(seg):
            continue
        for q in QUOTE_RE.findall(seg.text):
            hit = next((d for d in docs if _squash(q) in _squash(d["body"])), None)
            if hit:
                quotes.append({"quote": q, "seg": seg, "status": "match",
                               "doc": clean_title(hit["title"]), "speaker": hit.get("speaker")})
                continue
            # 내부 자료에 없으면 외부 claim 본문에서 온 인용인지 확인한다
            if any(_squash(q) in _squash((c.get("text") or "") + (c.get("metric") or ""))
                   for c in used):
                quotes.append({"quote": q, "seg": seg, "status": "external",
                               "doc": "(사용 claim 본문)", "speaker": None})
                continue
            quotes.append({"quote": q, "seg": seg, "status": "unmatched",
                           "doc": None, "speaker": None})
            if docs:   # DB를 못 읽었으면 단정하지 않는다
                issues.append(Issue(
                    "warn", "인용 원문 미확인",
                    f"직접 인용 “{q[:40]}…”의 원문을 내부 자료·사용 claim에서 찾지 못함",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행"))

    # 10) 내부 자료 인용의 시점 표기 — 연례 행사·정기 발행물은 어느 해 것인지가 근거의
    #     일부다(article_style 5절). 직접 인용뿐 아니라 인용부호 없는 간접 서술도 본다:
    #     "이천포럼 패널토의에서 …" 처럼 쓰면 인용부호가 없어 9)에서는 잡히지 않는다.
    #     액션 문단도 대상이다 — 수치 면제와 달리 시점 표기는 면제 사유가 없다.
    internal_refs: list[dict] = []
    quoted_doc = {id(q["seg"]): q["doc"] for q in quotes if q["status"] == "match"}
    declared = _declared_internal_docs(references, docs)
    for seg in segments:
        if "참고자료" in seg.heading:
            continue
        doc = next((d for d in docs if clean_title(d["title"]) == quoted_doc.get(id(seg))), None)
        if doc is None:
            doc = next((d for d in declared
                        if any(t in seg.text for t in _title_tokens(d["title"]))), None)
        if doc is None:
            continue
        title, year = clean_title(doc["title"]), _doc_year(doc)
        dated = bool(YEAR_RE.search(seg.text))
        internal_refs.append({"seg": seg, "doc": title, "year": year, "dated": dated})
        if not dated:
            issues.append(Issue(
                "warn", "내부 자료 시점 미표기",
                f"내부 자료 「{title}」를 인용했는데 문단에 연도 표기가 없음"
                + (f" — 자료 시점은 {year}년이다" if year else ""),
                f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    length = measure_length(md)
    column_checks = (_column_checks(md, segments, body, used_segments, evidence, numbers,
                                    length, aliases, reversal, issues) if column else None)

    return {
        "format": fmt, "column": column_checks,
        "min_sources": min_sources, "max_ratio": max_ratio, "reversal": reversal,
        "segments": segments, "used_segments": used_segments, "used": used, "unused": unused,
        "missing_marks": missing_marks,
        "counts": counts, "ratio": ratio, "top_source": top_source, "stances": stances,
        "numbers": numbers, "references": references, "used_docs": used_docs,
        "quotes": quotes, "internal_refs": internal_refs, "internal_available": bool(docs),
        "doc_dates": doc_dates or {},
        "doc_meta": doc_meta or {},
        "write_model": parse_write_model(md),
        "length": length,
        "issues": issues,
        "passed": not any(i.level == "fail" for i in issues),
    }


def _rel(p: Path) -> str:
    """리포트에는 저장소 상대경로로 적는다 (실행 위치에 따라 달라지지 않도록)."""
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def _length_line(length: dict[str, int]) -> str:
    """분량 한 줄 — 레이어가 있으면 독자 열람 최대(코어 + 가장 긴 레이어 1개)도 적는다."""
    core = length.get("core", 0)
    layers = {k: v for k, v in length.items() if k != "core"}
    line = f"분량(공백 제외 · 제목·참고자료·편집자 노트 제외): 코어 {core}자"
    if layers:
        line += (" / 레이어 " + " · ".join(f"{k} {v}자" for k, v in layers.items())
                 + f" / 독자 열람 최대 {core + max(layers.values())}자")
    return line


def _column_rows(r: dict) -> list[str]:
    """리포트 2장 아래 칼럼 형식 표. article이면 빈 목록(기존 리포트 불변)."""
    c = r.get("column")
    if not c:
        return []
    lo, hi = COLUMN_LENGTH
    named = "; ".join(f"{sid}({', '.join(n[:3])})" for sid, n in sorted(c["named"].items())) or "없음"
    ok = lambda b: "✅" if b else "❌"          # noqa: E731
    warn = lambda b: "✅" if b else "⚠️"        # noqa: E731
    return [
        "**칼럼 형식** (format: column — `docs/column-format-design.md`)", "",
        "| 항목 | 기준 | 실측 | 판정 |", "|---|---|---|---|",
        f"| 분량(공백 제외) | {lo:,}~{hi:,}자 | {c['core']:,}자 | "
        f"{ok(c['core'] <= hi) if c['core'] > hi else warn(c['core'] >= lo)} |",
        f"| 명시 인용 | 1~{COLUMN_MAX_NAMED_CITATIONS}곳 | {len(c['named'])}곳 — {named} · "
        f"익명 요약 {len(c['anonymous'])}곳 | "
        f"{ok(len(c['named']) <= COLUMN_MAX_NAMED_CITATIONS) if c['named'] else '⚠️'} |",
        f"| 근거 수치 | 0~{COLUMN_MAX_NUMBERS}개 | {len(c['numbers'])}개"
        f"{' (' + ', '.join(c['numbers']) + ')' if c['numbers'] else ''} | "
        f"{ok(len(c['numbers']) <= COLUMN_MAX_NUMBERS)} |",
        f"| 문단 | {COLUMN_PARAGRAPHS[0]}~{COLUMN_PARAGRAPHS[1]}개 · 문단당 "
        f"{COLUMN_PARAGRAPH_LEN[0]}~{COLUMN_PARAGRAPH_LEN[1]}자 | {c['paragraphs']}개 · 범위 밖 "
        f"{c['paragraph_off']}개 | {warn(COLUMN_PARAGRAPHS[0] <= c['paragraphs'] <= COLUMN_PARAGRAPHS[1] and not c['paragraph_off'])} |",
        f"| 소제목·세 줄 요약·레이어 | 모두 없음 | 소제목 {len(c['headings'])} · 요약 "
        f"{'있음' if c['summary'] else '없음'} · 레이어 {'있음' if c['layered'] else '없음'} | "
        f"{warn(not (c['headings'] or c['summary'] or c['layered']))} |",
        f"| 어미 | 지시·당위 0 · 구어체 1+ | 지시·당위 {c['banned']} · 구어체 {c['colloquial']} | "
        f"{warn(not c['banned'] and c['colloquial'])} |",
        "",
        "명시 인용은 근거 문단의 괄호 밖 로마자 고유명사·출처 이름으로 판정한다 — 국문 고유명사는 "
        "못 잡으니 사람이 한 번 더 본다.", "",
    ]


def render_report(slug: str, article_path: Path, evidence_path: Path, r: dict) -> str:
    used, counts = r["used"], r["counts"]
    min_src = r.get("min_sources", MIN_INDEPENDENT_SOURCES)
    max_ratio = r.get("max_ratio", MAX_SINGLE_SOURCE_RATIO)
    stances_txt = ", ".join(sorted(s for s in r["stances"] if s)) or "없음"
    opposed = {"optimistic", "cautious"} <= r["stances"]
    if r.get("format") == "column":
        rev = r.get("reversal")
        stance_row = (f"| 통념→반전 또는 상반 stance | 둘 중 하나 | "
                      f"반전 {f'{rev.line}행' if rev else '미검출'} · stance {stances_txt} | "
                      f"{'✅' if (rev or opposed) else '❌'} |")
    else:
        stance_row = (f"| 상반 stance | optimistic·cautious 각 1건+ | {stances_txt} | "
                      f"{'✅' if opposed else '❌'} |")
    lines = [
        f"# 검증 리포트 (실사용 기준) — {slug}", "",
        f"대상: `{_rel(article_path)}` · 증거: `{_rel(evidence_path)}`",
        f"작성 모델: {r.get('write_model') or '**머리말 미기재**'} "
        f"(정본은 `config/settings.yaml`의 `write_model`)",
    ] + ([f"포맷: **column** (칼럼 프로파일)"] if r.get("format") == "column" else []) + [
        f"판정: **{'통과' if r['passed'] else '실패'}** "
        f"(실패 {sum(1 for i in r['issues'] if i.level == 'fail')}건 · "
        f"경고 {sum(1 for i in r['issues'] if i.level == 'warn')}건)",
        _length_line(r.get("length") or {}),
        "",
        "> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.",
        "",
        "## 1. 본문 사용 claim (문장 ↔ claim ID)", "",
    ]
    if not r["used_segments"]:
        lines.append("사용 claim 없음 — 본문에 `<!-- claims: ... -->` 주석이 없다.")
    for seg in r["used_segments"]:
        lines.append(f"**[{seg.heading or '(제목 없음)'}] {seg.line}행** — “{_first_sentence(seg.text, 90)}”")
        for cid in seg.claim_ids:
            c = next((x for x in used if x["id"] == cid), None)
            if c:
                lines.append(f"- `{cid}` · {c.get('source')} · {c.get('tier')} · "
                             f"{c.get('stance')}/{c.get('evidence_type')} — {c.get('text', '')[:70]}")
            else:
                lines.append(f"- `{cid}` · **evidence에 없음(실패)**")
        lines.append("")

    lines += [
        f"사용 claim {len(used)}건 / evidence 전체 {len(used) + len(r['unused'])}건 "
        f"(미사용 {len(r['unused'])}건)", "",
        "## 2. 강제 조건 재계산 (사용 claim 기준)", "",
        "| 조건 | 기준 | 실측 | 판정 |", "|---|---|---|---|",
        f"| 독립 출처 | {min_src}곳 이상 | {len(counts)}곳 "
        f"({', '.join(f'{k} {v}' for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))}) | "
        f"{'✅' if len(counts) >= min_src else '❌'} |",
        stance_row,
        f"| 단일 출처 비중 | {max_ratio:.0%} 이하 | "
        f"{r['top_source']} {r['ratio']:.0%} | "
        f"{'✅' if r['ratio'] <= max_ratio else '❌'} |",
        "",
    ] + _column_rows(r) + [
        "## 3. 수치 대조 (절대 규칙 3)", "",
    ]
    if r["numbers"]:
        verdict = {"ok": "✅ 사용 claim에 있음", "fail": "❌ 근거 없음",
                   "prescriptive": "— 해당 없음 · 처방 값(실행 제안)"}
        lines += ["| 본문 수치 | 위치 | 근거 |", "|---|---|---|"]
        for seg, token, status in r["numbers"]:
            lines.append(f"| {token} | {seg.heading or '-'} {seg.line}행 | "
                         f"{verdict.get(status, status)} |")
        n_pres = sum(1 for _, _, s in r["numbers"] if s == "prescriptive")
        if n_pres:
            lines += ["", f"처방 값 {n_pres}건은 근거 대조 대상이 아니다 — 액션에서 제안한 "
                          "기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다."]
    else:
        lines.append("검사 대상 수치 없음 (참고자료 섹션은 면제).")

    lines += ["", "## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)", ""]
    if not r.get("internal_available"):
        lines.append("내부 자료를 읽지 못해 대조하지 못했다 (DB 미연결) — 사람 확인 필요.")
    elif not r.get("quotes"):
        lines.append("본문에 직접 인용 없음.")
    else:
        mark = {"match": "✅ 원문 문구 일치", "external": "· 외부 claim 본문에서 인용",
                "unmatched": "⚠️ 원문 미확인"}
        lines += ["| 본문 인용 | 위치 | 대조 대상 | 결과 |", "|---|---|---|---|"]
        for q in r["quotes"]:
            src = q["doc"] or "찾지 못함"
            if q.get("speaker"):
                src += f" ({q['speaker']})"
            lines.append(f"| “{q['quote'][:50]}{'…' if len(q['quote']) > 50 else ''}” | "
                         f"{q['seg'].heading or '-'} {q['seg'].line}행 | {src} | "
                         f"{mark.get(q['status'], q['status'])} |")
        if any(q["status"] == "match" for q in r["quotes"]):
            lines += ["", "> 문구 일치까지만 기계 검증했다. **발언 맥락 왜곡 여부는 사람 확인 항목**"
                          "이다 (CLAUDE.md 문체 규칙 — 경영층 인용은 발언 맥락 확인 후 발행)."]

    if r.get("internal_available"):
        lines += ["", "**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)", ""]
        if not r.get("internal_refs"):
            lines.append("본문에 내부 자료 인용 없음.")
        else:
            lines += ["| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |", "|---|---|---|---|"]
            for ref in r["internal_refs"]:
                lines.append(f"| {ref['doc']} | {ref['seg'].heading or '-'} {ref['seg'].line}행 | "
                             f"{ref['year'] + '년' if ref['year'] else '(미상)'} | "
                             f"{'✅ 있음' if ref['dated'] else '⚠️ 없음'} |")

    lines += ["", "## 5. 근거 주석 누락 의심 (사람 검토)", ""]
    if r["missing_marks"]:
        lines += ["주석 없는 문단 중 정량·인용 표현이 있는 것 — 근거를 달았는지 확인한다.", "",
                  "| 위치 | 사유 | 문장 |", "|---|---|---|"]
        for seg, reason in r["missing_marks"]:
            lines.append(f"| {seg.heading or '-'} {seg.line}행 | {reason} | "
                         f"{_first_sentence(seg.text, 60)} |")
    else:
        lines.append("없음.")

    lines += ["", "## 6. 참고자료 (실사용 문서만 — 본문에 그대로 붙여 넣는 목록)", ""]
    if r["used_docs"]:
        # internal_refs는 {seg, doc, year, dated} 목록이므로 문서명만 중복 없이 뽑는다
        seen, internal = set(), []
        for x in (r.get("internal_refs") or []):
            t = clean_title(x.get("doc") or "")
            if t and t not in seen:
                seen.add(t); internal.append(t)
        refs = reference_lines(r["used_docs"], r.get("doc_meta") or {},
                               source_ref_names(), internal, r.get("doc_dates") or {})
        lines += [f"- {x}" for x in refs]
        lines += ["", "형식: 외부 문서는 `매체·기관명, [제목](url) (연도)` · 이론 카드는 "
                  "`이론명(영문명, 저자 연도)` · 내부 자료는 제목 평문. 배열은 외부 → 이론 → 내부."]
    else:
        lines.append("(사용 claim 없음)")

    lines += ["", "## 7. 지적 사항", ""]
    if not r["issues"]:
        lines.append("없음.")
    for i in r["issues"]:
        mark = "❌ 실패" if i.level == "fail" else "⚠️ 경고"
        lines.append(f"- {mark} · **{i.kind}** — {i.message}")
        if i.where:
            lines.append(f"  - 위치: {i.where}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="아티클 실사용 기준 검증 (A2)")
    p.add_argument("article", help="검증할 아티클 md 경로")
    p.add_argument("--evidence", help="evidence json 경로 (기본: content/evidence/{slug}.json)")
    p.add_argument("--out", help="리포트 저장 경로 (기본: content/drafts/{slug}-verification.md)")
    p.add_argument("--stdout", action="store_true", help="파일로 쓰지 않고 리포트를 출력만 한다")
    p.add_argument("--format", choices=FORMATS,
                   help="포맷 프로파일 (기본: 초안 머리말의 format 표기, 없으면 article)")
    args = p.parse_args(argv)

    article_path = Path(args.article)
    md = article_path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*slug:\s*([\w-]+)", md)
    slug = m.group(1) if m else article_path.stem.replace("-verification", "")

    evidence_path = Path(args.evidence) if args.evidence else ROOT / "content" / "evidence" / f"{slug}.json"
    if not evidence_path.exists():
        print(f"evidence 파일 없음: {evidence_path}")
        return 2

    result = verify(md, load_evidence(evidence_path), load_internal_docs(),
                    load_document_dates(), load_document_meta(), fmt=args.format)
    report = render_report(slug, article_path, evidence_path, result)

    if args.stdout:
        print(report)
    else:
        out = Path(args.out) if args.out else ROOT / "content" / "drafts" / f"{slug}-verification.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"검증 리포트 저장: {out}")

    fails = sum(1 for i in result["issues"] if i.level == "fail")
    print(f"판정: {'통과' if result['passed'] else '실패'} — 사용 claim {len(result['used'])}건, "
          f"실패 {fails}건, 경고 {sum(1 for i in result['issues'] if i.level == 'warn')}건")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
