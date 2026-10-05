"""web/ 렌더러 — 레이어 박스 · 발행일 머리말 · teaser 메일."""
import email
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
pytest.importorskip("flask")      # 발행 도구 의존 (pip install --group web) — CI엔 없음
pytest.importorskip("markdown")
pytest.importorskip("PIL")

import server  # noqa: E402
import email_renderer  # noqa: E402
from segments import split_segment_blocks  # noqa: E402

LAYERED = """# 제목

<!-- slug: t | 판본: x -->
<!-- 발행 승인: 2026-10-08 -->

<!-- note -->
개편 안내 첫 줄.

둘째 문단 안내.
<!-- /note -->

**세 줄 요약**

- 하나
- 둘
- 셋

도입 문단.

## 우리 조직에 적용해본다면

공통 도입. 본문에 발행 승인: 2020-01-01 이라는 말이 있어도 무시한다.
<!-- claims: A -->

<!-- segment: leader -->
**리더가 할 일.** 리더 문단.
<!-- claims: B -->

<!-- segment: member -->
**팀원에게는.** 팀원 문단.
<!-- claims: C -->

공통 마무리.
"""


def test_segment_blocks_split_core_and_layers():
    art = server.parse_article_md(LAYERED)
    blocks = split_segment_blocks(art["sections"][0]["body"])
    assert [r for r, _ in blocks] == ["", "leader", "member", ""]
    assert blocks[1][1].startswith("**리더가 할 일.**")


def test_layer_boxes_rendered_with_labels():
    art = server.parse_article_md(LAYERED)
    page = server.render_article_html(art, {})
    assert '<aside class="layer layer-leader"><div class="layer-label">리더라면</div>' in page
    assert '<aside class="layer layer-member"><div class="layer-label">팀원이라면</div>' in page
    assert "[[segment:" not in page
    # 코어 문단은 박스 밖
    assert page.index("공통 마무리") > page.rindex("</aside>")


def test_unlayered_article_has_no_boxes():
    art = server.parse_article_md(LAYERED.replace("<!-- segment: leader -->\n", "")
                                  .replace("<!-- segment: member -->\n", ""))
    page = server.render_article_html(art, {})
    assert "layer-label" not in page and 'class=""' in page


def test_pub_date_from_header_comment_only():
    art = server.parse_article_md(LAYERED)
    assert art["pub_date"] == "2026-10-08" and art["warnings"] == []


def test_pub_date_missing_falls_back_to_today_with_warning():
    art = server.parse_article_md(LAYERED.replace("<!-- 발행 승인: 2026-10-08 -->\n", ""))
    assert art["pub_date"] != "2020-01-01"      # 본문 문구는 잡지 않는다
    assert len(art["warnings"]) == 1 and "발행 승인" in art["warnings"][0]


def test_table_email_renderer_boxes_layers(tmp_path):
    art = server.parse_article_md(LAYERED)
    html, _ = email_renderer.render_email_html(art, {}, tmp_path)
    assert "리더라면" in html and "팀원이라면" in html and "[[segment:" not in html


def test_teaser_eml_has_summary_text_and_links(tmp_path):
    art = server.parse_article_md(LAYERED)
    eml = email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"],
                                          web_url="https://ex.vercel.app/t/s/")
    msg = email.message_from_bytes(eml)
    body = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    text = body.get_payload(decode=True).decode("utf-8")
    assert "하나" in text and "웹에서 전문 보기" in text
    assert 'href="https://ex.vercel.app/t/s/"' in text


def test_teaser_requires_web_url(tmp_path):
    art = server.parse_article_md(LAYERED)
    with pytest.raises(ValueError):
        email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"])


def test_note_block_rendered_as_box_and_kept_out_of_body():
    art = server.parse_article_md(LAYERED)
    assert art["note"].startswith("개편 안내 첫 줄.")
    assert "개편 안내" not in art["intro"] and art["tldr_points"] == ["하나", "둘", "셋"]
    page = server.render_article_html(art, {})
    assert '<section class="editor-note"><p>개편 안내 첫 줄.</p>' in page
    assert page.index("editor-note") < page.index('class="tldr"')


def test_no_note_no_box():
    art = server.parse_article_md(LAYERED.split("<!-- note -->")[0] + LAYERED.split("<!-- /note -->")[1])
    assert art["note"] == "" and "editor-note" not in server.render_article_html(art, {})


def test_teaser_includes_note(tmp_path):
    art = server.parse_article_md(LAYERED)
    eml = email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"],
                                          web_url="https://ex.vercel.app/t/s/")
    msg = email.message_from_bytes(eml)
    text = next(p for p in msg.walk() if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    assert "개편 안내 첫 줄." in text and "둘째 문단 안내." in text
