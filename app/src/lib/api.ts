export type Source = {
  path: string;
  site: string;
  siteName: string;
  tier?: string;
  url: string;
  author: string;
  headline: string;
  title: string;
  date: string;
  reactions: string;
  chars: number;
  excerpt: string;
  text?: string;
};

export type Topic = { n: number; name: string; thesis: string; sources: string[]; brief: string };
export type TopicRound = { id: string; items: Topic[] };

export type Step = {
  n: number;
  file: string;
  by: string;
  title: string;
  text: string;
  chars: number;
  feedback: string;
  mode: string;
  at: number;
};

export type ImageItem = { name: string; prompt: string; src: string; after?: number; anchor?: string; why?: string };
export type InlinePick = { src: string; after: number; anchor: string; name: string };

export type Article = {
  id: string;
  kind: "brief" | "process";
  label: string;
  thesis: string;
  sources: [string, string][];
  title: string;
  titles: { at: number; items: string[]; message?: string }[];
  steps: Step[];
  images: { id: string; items: ImageItem[] }[];
  inline: { id: string; items: ImageItem[] }[];
  inlinePicked: InlinePick[];
  length: "full" | "half";
  target: string;
  hero: string;
  confirmed: { date: string; step?: number; file: string; hero?: string } | null;
  published?: { date: string; url: string; site: string; eml: string; to: string[]; cc: string[] } | null;
  fromTopics?: string;
  fromWiki?: string;
  fromMine?: boolean;
  sourcesOk?: boolean;
  tries?: { n: number; title: string; steps: Step[] }[];
  why?: string;
  at: number;
  error?: string;
};

export type Job = {
  id: string;
  kind: string;
  target: string;
  status: "running" | "done" | "failed" | "lost";
  started: number;
  ended?: number;
  log: string;
  message?: string;
  stage?: { index: number; half: boolean; fit: boolean } | null;
  /** 그림 작업(images·inline) — 설명 쓰는 중이면 phase "설명", 그리는 중이면 done/total장 */
  istage?: { phase: "설명" | "그리기"; done: number; total: number; failed: number; since: number } | null;
};

export type CollectRound = { id: string; request: string; saved: { url: string; site?: string; path?: string; error?: string }[] };

export type WikiSource = { path: string; who: string; site?: string; note: string; claim?: string; new: boolean };;
export type WikiTopic = {
  page: string;
  field: string;
  title: string;
  thesis: string;
  why?: string;
  verdict?: string;
  audience?: string;
  titles?: string[];
  status: string;
  usedIn: string[];
  sources: WikiSource[];
  angles: string[];
  related: { title: string; page: string }[];
  at: string;
  /** 메시지 단위 주제(2026-10-21)의 사례 — key 원문, role 중심·받침·반례, line 있었던 일 한 줄. 예전 사례 단위 주제는 빈 배열 */
  cases?: { key: string; role: string; line: string }[];
};
/** unbundled = 아직 주제로 묶지 않은 자동 카드 수('주제 묶기' 버튼) */
export type Wiki = { topics: WikiTopic[]; processed: number; backlog: string[]; unbundled?: number; bundleSince?: string; searchOnly?: { old: number; undated: number }; log: string[] };

/** 내 주제로 쓰기 — 메인 화면 채팅 (scripts/my_topic.py) */
export type MineRow = {
  source: string;
  path: string;
  who: string;
  url: string;
  kind: "중심" | "받침" | "후보";
  note: string;
  role: string;
  use: string;
  side: string;
  out: string;
};
export type MinePick = { source: string; role: string; who?: string; path?: string; note?: string };
/** 글 옵션(2026-10-22) — 이 글이 말할 것 한 문장 + 중심 1 + 받침 1~2. 하나를 고르면(mine-take) 원문을 확인하고 제목으로 */
export type MineOption = { message: string; center: MinePick; support: MinePick[]; why: string; audience?: string };
export type MineTurn =
  | { role: "mentor"; text: string; docs: string[]; at: number }
  | { role: "ai"; options: MineOption[]; at: number }
  | { role: "ai"; center: MinePick; support: MinePick[]; n_candidates: number; option?: number; at: number };
export type MineRun = {
  id: string;
  turns: MineTurn[];
  message: string;
  docs: string[];
  target: string;
  status: "running" | "done" | "failed" | "lost";
  stage: "문서" | "후보" | "고르기" | "옵션" | "옵션 고르기" | "확인" | "제목" | "끝";
  job: string;
  picked: MineRow[];
  rest: MineRow[];
  article: string;
  at: number;
};

export type State = {
  wiki: Wiki | null;
  library: Source[];
  topics: TopicRound[];
  articles: Article[];
  jobs: Job[];
  collects: CollectRound[];
  asideRounds?: AsideRound[];
  mine?: MineRun[];
  publish?: { to: string[]; cc: string[]; webBase: string };
};

// 소스 aside 수집 회차(scripts/aside_collect.py → Supabase) — 서재 위 칩
export type AsideRound = { id: string; new: number; upgraded: number; failed: number; stopped: string[] };

export type ChatMsg = { role: "mentor" | "claude"; text: string; at: number; cost?: number };

export async function getState(): Promise<State> {
  const r = await fetch("/api/state");
  return r.json();
}

export async function getJobs(): Promise<Job[]> {
  const r = await fetch("/api/jobs");
  return r.json();
}

export async function getSource(path: string): Promise<Source> {
  const r = await fetch("/api/source?path=" + encodeURIComponent(path));
  return r.json();
}

export async function getChat(article: string): Promise<ChatMsg[]> {
  const r = await fetch("/api/chat?article=" + encodeURIComponent(article));
  return r.json();
}

// 버튼을 누른 순간부터 끝날 때까지 화면이 알 수 있게 — 시작·끝·실패를 App이 듣는다(멘토 2026-10-10: "작업이 진행되는 동안 넘어가는 UI가 없음")
export type ActEvent = { phase: "start" | "end"; name: string; job?: Job; error?: string };
const actListeners = new Set<(e: ActEvent) => void>();
export function subscribeAct(l: (e: ActEvent) => void) {
  actListeners.add(l);
  return () => {
    actListeners.delete(l);
  };
}
const emit = (e: ActEvent) => actListeners.forEach((l) => l(e));

export async function act<T = unknown>(name: string, body: Record<string, unknown> = {}): Promise<T> {
  emit({ phase: "start", name });
  try {
    const r = await fetch("/api/" + name, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json().catch(() => ({ error: r.statusText }));
    if (!r.ok) throw new Error(j.error || r.statusText);
    emit({ phase: "end", name, job: j && j.id && j.kind && j.status ? (j as Job) : undefined });
    return j as T;
  } catch (e) {
    emit({ phase: "end", name, error: e instanceof Error ? e.message : String(e) });
    throw e;
  }
}

export const img = (src: string, w = 0) => "/img/" + src.split("/").map(encodeURIComponent).join("/") + (w ? `?w=${w}` : "");

export const articleTitle = (a: Article) => a.title || a.steps[a.steps.length - 1]?.title || a.label;

export const runningJob = (jobs: Job[], kind: string, target = "") =>
  jobs.find((j) => j.status === "running" && j.kind === kind && j.target === target);

export function stage(a: Article): string {
  if (a.confirmed) return "확정";
  if (a.steps.length) return `과정 ${a.steps.length}`;
  if (a.title) return "과정 1";
  return "제목";
}

export const JOB_NAMES: Record<string, string> = {
  topics: "주제",
  titles: "제목",
  write: "과정 1–3",
  revise: "과정 +1",
  shorten: "절반",
  inline: "본문 그림",
  images: "그림",
  collect: "수집",
  "db-sync": "Supabase 받기",
  chat: "진행자",
  wiki: "위키 넣기",
  "wiki-lint": "다시 거르기",
  "wiki-pick": "주제 고르기",
  "wiki-verdict": "판정",
  mine: "원문 고르기",
  publish: "발행",
};

export type JobLog = { text: string; live: { name: string; text: string }[]; status?: string; elapsed?: number };
export async function getLog(id: string): Promise<JobLog> {
  const r = await fetch("/api/log?id=" + encodeURIComponent(id));
  return r.json();
}

/** 어디서든 전체 로그 창을 연다 — App이 듣는다 */
export const openLog = (id = "") => window.dispatchEvent(new CustomEvent("studio:open-log", { detail: id }));
