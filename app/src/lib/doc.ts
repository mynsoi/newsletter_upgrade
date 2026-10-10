// 원고(문단을 빈 줄로 나눈 글) ↔ 에디터 문서. 화면의 paragraphs()와 같은 규칙으로 나눠야
// 고치지 않은 문단이 글자 하나 달라지지 않는다(비교 화면이 안 바뀐 문장을 칠하지 않게).

export type DocNode = { type: string; attrs?: { level?: number }; text?: string; content?: DocNode[] };

const HEAD = /^(#{1,3})\s+(\S.*)$/;

export function toDoc(text: string): DocNode {
  const blocks = text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
  return {
    type: "doc",
    content: blocks.map((b) => {
      const h = b.includes("\n") ? null : b.match(HEAD);
      if (h) return { type: "heading", attrs: { level: h[1].length }, content: [{ type: "text", text: h[2] }] };
      const content: DocNode[] = [];
      b.split("\n").forEach((line, i) => {
        if (i) content.push({ type: "hardBreak" });
        if (line) content.push({ type: "text", text: line });
      });
      return { type: "paragraph", content };
    }),
  };
}

const inline = (n: DocNode): string =>
  (n.content ?? []).map((c) => (c.type === "hardBreak" ? "\n" : c.text ?? inline(c))).join("");

export function fromDoc(doc: DocNode): string {
  return (doc.content ?? [])
    .map((n) => {
      const t = inline(n).trim();
      if (!t) return "";
      return n.type === "heading" ? "#".repeat(n.attrs?.level ?? 3) + " " + t : t;
    })
    .filter(Boolean)
    .join("\n\n");
}
