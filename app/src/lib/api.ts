export type Source = {
  path: string;
  site: string;
  siteName: string;
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

export type ImageItem = { name: string; prompt: string; src: string; after?: number; anchor?: string };
export type InlinePick = { src: string; after: number; anchor: string; name: string };

export type Article = {
  id: string;
  kind: "brief" | "process";
  label: string;
  thesis: string;
  sources: [string, string][];
  title: string;
  titles: { at: number; items: string[] }[];
  steps: Step[];
  images: { id: string; items: ImageItem[] }[];
  inline: { id: string; items: ImageItem[] }[];
  inlinePicked: InlinePick[];
  length: "full" | "half";
  hero: string;
  confirmed: { date: string; step?: number; file: string; hero?: string } | null;
  fromTopics?: string;
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
};

export type CollectRound = { id: string; request: string; saved: { url: string; site?: string; path?: string; error?: string }[] };

export type WikiSource = { path: string; who: string; note: string; new: boolean };
export type WikiTopic = {
  page: string;
  field: string;
  title: string;
  thesis: string;
  status: string;
  usedIn: string[];
  sources: WikiSource[];
  angles: string[];
  related: { title: string; page: string }[];
  at: string;
};
export type Wiki = { topics: WikiTopic[]; processed: number; backlog: string[]; log: string[] };

export type State = {
  wiki: Wiki | null;
  library: Source[];
  topics: TopicRound[];
  articles: Article[];
  jobs: Job[];
  collects: CollectRound[];
};

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
  chat: "진행자",
  wiki: "위키 넣기",
  "wiki-lint": "위키 정리",
  "wiki-pick": "깊게 읽기",
};

export type JobLog = { text: string; live: { name: string; text: string }[]; status?: string; elapsed?: number };
export async function getLog(id: string): Promise<JobLog> {
  const r = await fetch("/api/log?id=" + encodeURIComponent(id));
  return r.json();
}

/** 어디서든 전체 로그 창을 연다 — App이 듣는다 */
export const openLog = (id = "") => window.dispatchEvent(new CustomEvent("studio:open-log", { detail: id }));
