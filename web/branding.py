"""발행물 공통 브랜드 문구 — server.py(웹)·email_renderer.py(메일 전문·teaser)가 함께 쓴다.

푸터가 세 곳에 따로 적혀 있어 문구를 고칠 때마다 한 곳이 빠졌다. 2026-10-05부터 여기 한 군데서
관리한다. 웹 템플릿은 `{{ footer_html }}` 자리에 `footer_html()`을 끼워 넣는다.
"""
import html

# 푸터 3행. 1행은 발행 주체·주기, 2행은 제작 방식 고지, 3행은 문의처다.
# 3행의 담당자는 창간호 인사말(note)의 "※ 담당자" 줄과 겹치지만 역할이 다르다 —
# 인사말은 그 호의 안내이고 푸터는 매 호 고정 문의처다. 둘 다 유지한다(2026-10-05 결정).
FOOTER_LINES = (
    "Insight Weekly · 기업문화AX팀 발행 · 매주 금요일",
    "자료 수집과 정리는 AI가, 검증과 편집은 사람이 했습니다.",
    "문의: 기업문화AX팀 김산결M / 이소민M",
)


def footer_html(indent: str = "") -> str:
    """푸터 3행을 <br>로 이은 HTML. indent를 주면 줄마다 앞에 붙인다(템플릿 들여쓰기용)."""
    lines = [html.escape(x) for x in FOOTER_LINES]
    joined = "<br>\n".join(indent + x for x in lines)
    return joined[len(indent):] if indent else joined
