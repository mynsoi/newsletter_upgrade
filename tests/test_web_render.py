"""web/ 렌더러 — 레이어 박스 · 발행일 머리말 · teaser 메일."""
import email
import email.header
import email.utils
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


def test_korean_sender_name_encodes_name_only(tmp_path):
    art = server.parse_article_md(LAYERED)
    eml = email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"],
                                          sender="이소민/기업문화AX팀 <noreply@example.com>",
                                          web_url="https://ex.vercel.app/t/s/")
    msg = email.message_from_bytes(eml)
    assert msg["From"].endswith("<noreply@example.com>")
    name, addr = email.utils.parseaddr(str(email.header.make_header(email.header.decode_header(msg["From"]))))
    assert name == "이소민/기업문화AX팀" and addr == "noreply@example.com"


# ── 메일 캡처 폭 (2026-10-05: 동료 원본 760으로 복귀) ──

def test_email_width_is_colleague_original_760():
    """캡처 폭은 동료 원본 메일 렌더러의 CONTENT_WIDTH와 같은 760이다.

    폰 375px에서 ×0.49로 줄어든다 — 이 비율이 리허설 체크리스트의 모바일 판정 기준이므로
    폭을 바꾸면 그 문구도 함께 고쳐야 한다.
    """
    assert email_renderer.EMAIL_WIDTH == 760
    assert email_renderer.EMAIL_WIDTH == email_renderer.CONTENT_WIDTH


def test_mail_wrapper_uses_width_constant():
    """메일 테이블 폭이 상수를 따라간다 — 하드코딩된 숫자가 남아 있지 않다."""
    w = email_renderer.EMAIL_WIDTH
    wrapped = email_renderer._wrap_mail("<tr><td>x</td></tr>")
    assert f'width="{w}"' in wrapped and f"max-width:{w}px" in wrapped


def test_email_capture_css_does_not_override_font_size():
    """캡처 CSS는 글자 크기를 키우지 않는다 — 760px에서는 웹 본문과 같은 크기로 찍는다.

    링크 밑줄·색 제거와 두 장 캡처(머리·본문) 규칙은 유지한다.
    """
    css = (Path(__file__).resolve().parent.parent / "web/static/article.css").read_text(encoding="utf-8")
    capture_rules = [ln for ln in css.splitlines() if ln.strip().startswith(".email-capture")]
    assert capture_rules, ".email-capture 규칙이 사라졌다"
    assert not [ln for ln in capture_rules if "font-size" in ln], \
        f"캡처 CSS에 font-size override가 남아 있다: {capture_rules}"
    assert any("text-decoration: none" in ln for ln in capture_rules)
    assert ".email-part-head" in css and ".email-part-body" in css


# ── 편집자 노트의 "※ …" 안내 줄 (2026-10-05: 담당자 안내) ──

NOTE_WITH_FINE = """# 제목

<!-- note -->
개편 안내 첫 줄.

문의는 담당자에게 보내주세요.

※ 담당자: 기업문화AX팀 홍길동M / 김철수M
<!-- /note -->

**세 줄 요약**

- 요약 한 줄.

도입 문단.

## 소제목

본문 문단.
"""


def test_note_fine_line_keeps_marker_and_gets_class():
    """"※ …" 줄은 작은 글자 클래스를 받고 ※ 문자가 사라지지 않는다."""
    art = server.parse_article_md(NOTE_WITH_FINE)
    html = server.render_article_html(art, {})
    assert 'class="note-fine"' in html
    assert "※ 담당자: 기업문화AX팀 홍길동M / 김철수M" in html
    assert "\x01" not in html          # 백레퍼런스 사고 재발 방지


def test_note_fine_only_applies_to_marker_paragraph():
    """※ 없는 문단에는 클래스가 붙지 않는다."""
    art = server.parse_article_md(NOTE_WITH_FINE)
    html = server.render_article_html(art, {})
    note = html[html.index('class="editor-note"'):html.index("</section>")]
    assert note.count('class="note-fine"') == 1
    assert "<p>개편 안내 첫 줄.</p>" in note


def test_teaser_note_fine_line_is_smaller(tmp_path):
    """teaser 메일에서도 ※ 줄만 작은 글자로 나간다."""
    art = server.parse_article_md(NOTE_WITH_FINE)
    eml = email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"],
                                          web_url="https://ex.vercel.app/t/s/")
    msg = email.message_from_bytes(eml)
    text = next(p for p in msg.walk() if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    fine = [ln for ln in text.split("<p ") if "※ 담당자" in ln]
    assert fine and "font-size:9.5pt" in fine[0]
    assert "font-size:11pt" in text          # 나머지 문단은 그대로


# ── 푸터 3행 (2026-10-05: 웹·메일 전문·teaser 공용) ──

def test_footer_lines_are_three_and_shared():
    """푸터는 branding.FOOTER_LINES 한 곳에서 관리한다 — 3행 구성과 문구를 고정한다."""
    import branding
    assert len(branding.FOOTER_LINES) == 3
    assert branding.FOOTER_LINES[0] == "Insight Weekly · 기업문화AX팀 발행 · 매주 금요일"
    assert "자료 수집과 정리는 AI가, 검증과 편집은 사람이 했습니다." == branding.FOOTER_LINES[1]
    assert branding.FOOTER_LINES[2].startswith("문의: 기업문화AX팀")
    # 1행에 주기가 들어갔으므로 "매주 금요일 발행합니다" 단독 줄은 없다
    assert not any(x == "매주 금요일 발행합니다." for x in branding.FOOTER_LINES)


def test_web_footer_renders_all_three_lines():
    import branding
    art = server.parse_article_md(LAYERED)
    html = server.render_article_html(art, {})
    for line in branding.FOOTER_LINES:
        assert line in html, f"웹 푸터에 빠진 줄: {line}"
    assert "{{ footer_html }}" not in html          # 자리표시자가 남지 않는다
    assert "매주 금요일 발행합니다" not in html      # 구 문구 제거


def test_full_mail_and_teaser_footers_match_web(tmp_path):
    """메일 전문·teaser 푸터가 웹과 같은 3행을 쓴다 — 세 곳이 어긋나지 않게."""
    import branding
    art = server.parse_article_md(LAYERED)
    full_html, _ = email_renderer.render_email_html(art, {}, tmp_path)
    eml = email_renderer.build_teaser_eml("제목", art, tmp_path, ["a@example.com"],
                                          web_url="https://ex.vercel.app/t/s/")
    teaser = next(p for p in email.message_from_bytes(eml).walk()
                  if p.get_content_type() == "text/html").get_payload(decode=True).decode()
    for line in branding.FOOTER_LINES:
        assert line in full_html, f"전문 메일 푸터에 빠진 줄: {line}"
        assert line in teaser, f"teaser 푸터에 빠진 줄: {line}"
    assert "매주 금요일 발행합니다" not in full_html
    assert "매주 금요일 발행합니다" not in teaser


def test_footer_text_not_duplicated_in_source():
    """푸터 문구가 소스에 하드코딩으로 남아 있지 않다 — branding.py 한 곳만."""
    web = Path(__file__).resolve().parent.parent / "web"
    needle = "기업문화AX팀 발행"
    holders = [p.name for p in (*web.glob("*.py"), *(web / "templates").glob("*.html"))
               if needle in p.read_text(encoding="utf-8")]
    assert holders == ["branding.py"], f"푸터 문구가 여러 곳에 있다: {holders}"
