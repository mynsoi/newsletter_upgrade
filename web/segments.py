"""레이어 표기(segment) 공용 처리 — server.py(웹)·email_renderer.py(메일)가 함께 쓴다."""
import re

# 레이어(prompts/segment_layers.md 표기 형식). 파서가 `<!-- segment: X -->`를 아래 표지로 바꿔
# 문단 첫 줄에 남기고, 렌더러는 표지가 붙은 문단을 역할 박스로 감싼다.
SEGMENT_COMMENT_RE = re.compile(r"<!--\s*segment:\s*([\w-]+)\s*-->[ \t]*")
SEGMENT_MARK_PREFIX = "[[segment:"
SEGMENT_MARK_RE = re.compile(r"^\[\[segment:([\w-]+)\]\]\s*")
SEGMENT_LABELS = {
    "exec": "임원이라면",
    "lead": "팀장이라면",
    "leader": "리더라면",
    "member": "팀원이라면",
}


def split_segment_blocks(text: str) -> list[tuple[str, str]]:
    """본문을 (역할, 마크다운) 묶음으로 나눈다. 역할이 ""이면 코어 문단.

    레이어는 표지가 붙은 문단 하나다(표기 형식: 표지 줄 → 문단 → claims 주석).
    표지 다음에 빈 줄이 있어도 바로 뒤 문단을 레이어로 본다. 연속한 코어 문단은 한 묶음.
    """
    blocks: list[tuple[str, str]] = []
    pending_role = ""
    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        m = SEGMENT_MARK_RE.match(para)
        role = pending_role
        if m:
            role, para = m.group(1), para[m.end():].strip()
        if not para:            # 표지만 있는 줄 — 다음 문단에 붙인다
            pending_role = role
            continue
        pending_role = ""
        if not role and blocks and not blocks[-1][0]:
            blocks[-1] = ("", blocks[-1][1] + "\n\n" + para)
        else:
            blocks.append((role, para))
    return blocks


def strip_segment_marks(text: str) -> str:
    """표지를 지운 본문 (이미지 프롬프트처럼 레이어 구분이 필요 없는 곳)."""
    return re.sub(r"\[\[segment:[\w-]+\]\]\s*", "", text)
