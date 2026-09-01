/**
 * extract_article.js — 브라우저 보조 수집(/browse-collect)용 기사 추출·다운로드 스크립트.
 *
 * 사용: 기사 페이지의 콘솔(또는 자동화 도구)에서 이 파일 전체를 실행한 뒤 호출.
 *   extractArticle({ sourceId: "knowledge-wharton" })
 *   extractArticle({ sourceId: "...", container: "main .post",
 *                    exclude: [".bio", ".promo"], licenseNote: "구독 계정 열람분" })
 *
 * 동작:
 *  - 컨테이너(기본 "article") 안의 p·h2·h3·h4·li·blockquote를 문서 순서대로 수집.
 *    소제목(h2~h4)은 "## ", 목록 항목(li)은 "- ", 인용 블록(blockquote)은 "> " 접두.
 *  - 비본문 블록(저자 소개·관련 기사·공유 버튼·구독 유도 등)은 exclude 선택자로 제외.
 *  - 원문 텍스트는 변형하지 않는다(공백 정규화만) — 요약·재구성 금지(절대 규칙 8).
 *  - YAML 머리말(source_id·url·title·published·fetched_at·fetched_by·license_note)을
 *    붙여 "<source_id>_<발행일>_<슬러그>.md"로 다운로드한다.
 *    (참고: 인앱 브라우저에서는 다운로드가 GUID 이름의 .tmp로 떨어질 수 있음 —
 *     반환되는 stats.filename·bytesApprox로 파일을 식별해 개명한다.)
 *  - 반환값: { filename, published, blocks: {p,h,li,blockquote}, chars, bytesApprox }
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
    const seg = (location.pathname.split("/").filter(Boolean).pop() || "")
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

  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  const chars = lines.join("\n\n").length;
  return { filename, published, blocks, chars, bytesApprox: new TextEncoder().encode(md).length };
}
