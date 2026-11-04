// 원고(문단을 빈 줄로 나눈 글) ↔ 에디터 문서. 화면의 paragraphs()와 같은 규칙으로 나눠야
// 고치지 않은 문단이 글자 하나 달라지지 않는다(비교 화면이 안 바뀐 문장을 칠하지 않게).
// 강조(굵게, 2026-11-04)는 원고에 ==…==로 남긴다 — 에디터에서는 emph 표시(mark)로 바꿔 보여 준다.

export type DocNode = {
  type: string;
  attrs?: { level?: number };
  text?: string;
  marks?: { type: string }[];
  content?: DocNode[];
};

const HEAD = /^(#{1,3})\s+(\S.*)$/;

/** 한 줄의 ==…== 를 글자 조각으로 — 짝이 안 맞는 ==는 글자 그대로 둔다 */
function lineNodes(line: string): DocNode[] {
  const out: DocNode[] = [];
  const re = /==(.+?)==/g;
  let last = 0;
  for (const m of line.matchAll(re)) {
    if (m.index! > last) out.push({ type: "text", text: line.slice(last, m.index) });
    out.push({ type: "text", text: m[1], marks: [{ type: "emph" }] });
    last = m.index! + m[0].length;
  }
  if (last < line.length) out.push({ type: "text", text: line.slice(last) });
  return out;
}

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
        if (line) content.push(...lineNodes(line));
      });
      return { type: "paragraph", content };
    }),
  };
}

const isEmph = (n: DocNode) => !!n.marks?.some((m) => m.type === "emph");

/** 이어진 강조 조각은 ==…== 하나로 묶는다(에디터가 한 강조를 여러 조각으로 나눠 줄 때가 있다) */
const inline = (n: DocNode): string => {
  let s = "";
  let open = false;
  for (const c of n.content ?? []) {
    const em = c.type === "text" && isEmph(c);
    if (em !== open) {
      s += "==";
      open = em;
    }
    s += c.type === "hardBreak" ? "\n" : c.text ?? inline(c);
  }
  return open ? s + "==" : s;
};

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

/** 원고에서 강조 표시를 뗀 글 — 비교·글자 수용 */
export const plainText = (t: string) => t.replace(/==(.+?)==/gs, "$1");

/** 고른 문장들에 강조를 씌운 원고 — 이미 강조된 곳은 그대로, 원고에 없는 문장은 건너뛴다 */
export function applyEmph(text: string, picks: string[]): string {
  let out = text;
  for (const p of picks) {
    if (!p || out.includes("==" + p + "==")) continue;
    const i = out.indexOf(p);
    if (i < 0) continue;
    if ((out.slice(0, i).match(/==/g) ?? []).length % 2) continue; // 이미 강조된 문장 안쪽이면 겹쳐 씌우지 않는다
    out = out.slice(0, i) + "==" + p + "==" + out.slice(i + p.length);
  }
  return out;
}
