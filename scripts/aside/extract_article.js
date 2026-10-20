/**
 * extract_article.js — aside 수집(scripts/aside_collect.py)용 기사 본문 추출.
 * main 파이프라인 scripts/browse/extract_article.js를 그대로 옮기고 끝부분만 바꿨다:
 * 파일을 내려받는 대신 { md, text, title, published, mode, blocks, chars }를 돌려준다.
 * 원문 텍스트는 변형하지 않는다(공백 정규화만) — 요약·재구성 금지.
 * aside REPL에서 p.evaluate("(" + 이 함수 + ")(opts)")로 부른다.
 */
function extractArticle(opts = {}) {
  const container = opts.container || "article";
  const exclude = opts.exclude || [
    ".author", ".author-bio", ".author-info", ".bio", ".byline",
    ".related", ".related-posts", ".related-articles", ".recommended", ".read-more",
    ".share", ".sharing", ".social", ".social-share",
    ".newsletter", ".subscribe", ".signup", ".cta", ".promo",
    ".tags", ".comments", ".breadcrumb",
    "nav", "aside", "footer", "figcaption", "form",
  ];
  const sourceId = opts.sourceId || "unknown-source";
  const fetchedBy = opts.fetchedBy || "browse";
  const licenseNote = opts.licenseNote || "";

  const root = document.querySelector(container);
  if (!root) throw new Error("컨테이너를 찾지 못함: " + container);
  const exclSel = exclude.join(",");

  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const liText = (el) => {
    // 중첩 목록은 자기 줄로 따로 잡히므로 상위 li 텍스트에서는 제거
    const clone = el.cloneNode(true);
    clone.querySelectorAll("ul,ol").forEach((n) => n.remove());
    return norm(clone.textContent);
  };

  const blocks = { p: 0, h: 0, li: 0, blockquote: 0 };
  const lines = [];
  for (const el of root.querySelectorAll("p,h2,h3,h4,li,blockquote")) {
    if (exclSel && el.closest(exclSel)) continue;            // 비본문 블록 제외
    const tag = el.tagName.toLowerCase();
    const bq = el.closest("blockquote");
    if (bq && bq !== el) continue;                           // blockquote 내부는 통째로 1회만
    if (tag === "p" && el.closest("li")) continue;           // li 내부 p는 li 텍스트에 포함됨
    let text, prefix;
    if (tag === "li") { text = liText(el); prefix = "- "; blocks.li += text ? 1 : 0; }
    else if (tag === "blockquote") { text = norm(el.textContent); prefix = "> "; blocks.blockquote += text ? 1 : 0; }
    else if (tag === "p") { text = norm(el.textContent); prefix = ""; blocks.p += text ? 1 : 0; }
    else { text = norm(el.textContent); prefix = "## "; blocks.h += text ? 1 : 0; }
    if (text) lines.push(prefix + text);
  }

  // br 폴백: 제외 요소 제거 후 연속 br·블록 경계를 문단 구분으로,
  // 단일 br(문단 내 줄바꿈)은 공백으로 처리한다.
  let mode = "blocks";
  if (!lines.length) {
    mode = "br-fallback";
    const SEP = "\u0001";  // 문단 경계 마커 (본문에 나올 수 없는 제어문자)
    const clone = root.cloneNode(true);
    if (exclSel) clone.querySelectorAll(exclSel).forEach((n) => n.remove());
    clone.querySelectorAll("script,style,noscript").forEach((n) => n.remove());
    clone.querySelectorAll("br").forEach((n) => n.replaceWith(SEP));
    for (const el of clone.querySelectorAll(
      "div,section,table,tr,ul,ol,li,h1,h2,h3,h4,h5,h6,p,blockquote")) el.append(SEP + SEP);
    for (const seg of clone.textContent.split(/\u0001{2,}/)) {
      const t = norm(seg.replace(/\u0001/g, " "));
      if (t) { lines.push(t); blocks.p += 1; }
    }
  }
  if (!lines.length) throw new Error("본문 블록이 비어 있음 — container/exclude 확인 필요");

  // 발행일: meta → time → ld+json 순 (Wharton은 ld+json에만 있음)
  const published = (() => {
    const m = document.querySelector(
      'meta[property="article:published_time"], meta[name="article:published_time"], meta[itemprop="datePublished"]');
    if (m && m.content) return m.content.slice(0, 10);
    const t = document.querySelector("time[datetime]");
    if (t) return (t.getAttribute("datetime") || "").slice(0, 10);
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const j = JSON.parse(s.textContent);
        for (const o of (Array.isArray(j) ? j : (j["@graph"] || [j])))
          if (o && o.datePublished) return String(o.datePublished).slice(0, 10);
      } catch (e) { /* 형식 불량 ld+json은 무시 */ }
    }
    return "";
  })();

  const ogTitle = document.querySelector('meta[property="og:title"]');
  const title = norm((ogTitle && ogTitle.content) || document.title);
  const slug = (() => {
    // URL 끝 세그먼트가 무의미한 사이트(DBR의 /ac/m_best 등)는 opts.slug로 지정
    const seg = opts.slug || (location.pathname.split("/").filter(Boolean).pop() || "")
      .replace(/\.[a-z0-9]+$/i, "");  // .html 등 확장자 제거
    const s = (seg || title.toLowerCase()).toLowerCase()
      .replace(/[^a-z0-9가-힣-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
    return s || "article";
  })();
  const filename = sourceId + "_" + (published || "unknown") + "_" + slug + ".md";

  const yq = (s) => '"' + String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
  const md = [
    "---",
    "source_id: " + sourceId,
    "url: " + location.href,
    "title: " + yq(title),
    "published: " + (published || ""),
    "fetched_at: " + new Date().toISOString(),
    "fetched_by: " + fetchedBy,
    "license_note: " + yq(licenseNote),
    "---",
    "",
    lines.join("\n\n"),
    "",
  ].join("\n");

  const text = lines.join(String.fromCharCode(10, 10));
  return { md, text, title, published, mode, blocks, chars: text.length };
}
