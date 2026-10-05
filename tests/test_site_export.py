"""web/site_export.py · email_renderer 웹 링크 — 정적 배포 경로와 "웹에서 보기" 링크."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
import site_export  # noqa: E402


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    settings = tmp_path / "settings.yaml"
    settings.write_text('web_base_url: "https://ex.vercel.app/"\nweb_path_token: tok123\n',
                        encoding="utf-8")
    monkeypatch.setattr(site_export, "SETTINGS_PATH", settings)
    monkeypatch.setattr(site_export, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(site_export, "SITE_DIR", tmp_path / "site")
    return tmp_path


def _publish(root: Path, slug: str, pub_date: str, title: str):
    out = root / "output" / slug
    out.mkdir(parents=True)
    (out / "index.html").write_text("<html></html>", encoding="utf-8")
    (out / "hero.png").write_bytes(b"png")
    (out / "newsletter.eml").write_bytes(b"eml")
    (out / "article.json").write_text(json.dumps({
        "title": title, "pub_date": pub_date, "tldr_points": ["<요약>"], "hero_file": "hero.png",
    }, ensure_ascii=False), encoding="utf-8")


def test_article_web_url_uses_token_and_strips_slash(sandbox):
    assert site_export.article_web_url("a-b") == "https://ex.vercel.app/tok123/a-b/"


def test_article_web_url_empty_when_base_unset(sandbox):
    (sandbox / "settings.yaml").write_text('web_base_url: ""\nweb_path_token: tok123\n',
                                           encoding="utf-8")
    assert site_export.article_web_url("a-b") == ""


def test_export_copies_under_token_and_skips_mail_files(sandbox):
    _publish(sandbox, "first", "2026-10-08", "첫 호")
    dest = site_export.export_article("first")
    assert dest == sandbox / "site" / "tok123" / "first"
    assert (dest / "index.html").exists() and (dest / "hero.png").exists()
    assert not (dest / "newsletter.eml").exists()
    root = (sandbox / "site" / "index.html").read_text(encoding="utf-8")
    assert "first" not in root and "noindex" in root  # 루트는 토큰 경로를 드러내지 않는다
    assert "Disallow: /" in (sandbox / "site" / "robots.txt").read_text(encoding="utf-8")


def test_archive_index_newest_first_and_escaped(sandbox):
    _publish(sandbox, "old", "2026-10-08", "첫 호")
    _publish(sandbox, "new", "2026-10-15", "둘째 호")
    site_export.export_article("old")
    site_export.export_article("new")
    page = (sandbox / "site" / "tok123" / "index.html").read_text(encoding="utf-8")
    assert page.index("둘째 호") < page.index("첫 호")
    assert '<meta name="robots" content="noindex, nofollow">' in page
    assert "&lt;요약&gt;" in page and "<요약>" not in page
    assert 'href="new/"' in page and 'src="new/hero.png"' in page


def test_web_link_row():
    pytest.importorskip("PIL")  # email_renderer 의존 (pip install --group web) — CI엔 없음
    import email_renderer
    assert email_renderer._web_link_row("") == ""
    row = email_renderer._web_link_row('https://ex.vercel.app/t/s/?a="b"')
    assert "웹에서 보기" in row
    assert 'href="https://ex.vercel.app/t/s/?a=&quot;b&quot;"' in row
