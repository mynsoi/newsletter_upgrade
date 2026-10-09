// 원고 문단·문장 나누기와 앞 과정 대비 새로 들어온 문장 찾기 (build_view.py의 문장 LCS를 옮김)

export const sentences = (t: string) =>
  t
    .replace(/\s+/g, " ")
    .split(/(?<=[.?!])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

const norm = (s: string) => s.replace(/\s/g, "");

export function paragraphs(t: string) {
  return t
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

export function keptSentences(prev: string, cur: string): Set<number> {
  const a = sentences(prev).map(norm);
  const b = sentences(cur).map(norm);
  const n = a.length,
    m = b.length;
  const d = Array.from({ length: n + 1 }, () => new Int16Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--) d[i][j] = a[i] === b[j] ? d[i + 1][j + 1] + 1 : Math.max(d[i + 1][j], d[i][j + 1]);
  const kb = new Set<number>();
  let i = 0,
    j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      kb.add(j);
      i++;
      j++;
    } else if (d[i + 1][j] >= d[i][j + 1]) i++;
    else j++;
  }
  return kb;
}

export function when(ts: number) {
  const d = new Date(ts * 1000);
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function roundWhen(id: string) {
  const m = id.match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/);
  return m ? `${+m[2]}월 ${+m[3]}일 ${m[4]}:${m[5]}` : id;
}

export function hue(s: string) {
  let h = 0;
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}
