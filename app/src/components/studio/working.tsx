import { useEffect, useRef, useState } from "react";
import { IconCheck, IconChevronDown } from "@tabler/icons-react";
import { AILoadingLive } from "@/components/kokonutui/ai-loading";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { LiveLog } from "@/components/studio/live-log";
import { getLog, type Job, type JobLog } from "@/lib/api";
import { cn } from "@/lib/utils";

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function useJobLog(jobId: string) {
  const [log, setLog] = useState<JobLog | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    const pull = () => getLog(jobId).then((l) => alive && (setLog(l), setTick(0)));
    pull();
    const t = setInterval(pull, 1500);
    const c = setInterval(() => setTick((x) => x + 1), 1000);
    return () => {
      alive = false;
      clearInterval(t);
      clearInterval(c);
    };
  }, [jobId]);
  return { log, elapsed: (log?.elapsed ?? 0) + (log?.status === "running" ? tick : 0) };
}

const NOISE = /^(OpenAI Codex|workdir:|model:|provider:|approval:|sandbox:|reasoning|session id:|hook:|warning:|Reading prompt|user \(.*config\.toml\)|-{3,}|\d{4}-\d\d-\d\dT[\d:.]+Z\s+(ERROR|WARN|INFO))/;
const cut = (l: string) => (l.length > 140 ? l.slice(0, 140) + "…" : l);

/** 로그를 화면용 줄로 — 시동 메시지는 빼고, astra에게 보낸 요청문은 한 줄로 접는다. waiting: 요청을 보내고 답을 기다리는 중인지 */
function readLog(t: string) {
  const out: string[] = [];
  let prompt = -1;
  for (const raw of t.split("\n")) {
    const l = raw.replace(/\s+/g, " ").trim();
    if (!l || NOISE.test(l)) continue;
    if (l === "user") {
      prompt = 0;
      continue;
    }
    if (prompt >= 0) {
      if (/^(codex|thinking|exec)$/.test(l) || l.startsWith("tokens used")) {
        out.push(`astra에게 요청 전달 · ${prompt}줄`);
        prompt = -1;
        if (l === "codex") out.push("astra 답:");
        else if (l !== "thinking") out.push(l);
      } else prompt++;
      continue;
    }
    if (l === "codex") {
      out.push("astra 답:");
      continue;
    }
    out.push(cut(l));
  }
  const waiting = prompt >= 0;
  if (waiting) out.push(`astra에게 요청 전달 · ${prompt}줄`);
  return { lines: out, waiting };
}

/**
 * 진행 중 카드 — 무엇을 만드는 중인지(제목), 단계(steps), 경과 시간, 실제 진행(쓰이는 글 또는 로그 줄), 전체 로그 펼치기.
 * 쓰는 중인 글(live.md)이 있으면 그 글이 실시간으로 쌓이는 모습을, 없으면 AI Loading에 실제 로그 줄을 흘린다.
 */
export function Working({
  job,
  title,
  status,
  steps,
  stepIndex = 0,
}: {
  job: Job;
  title: React.ReactNode;
  status: string;
  steps?: { label: string; by?: string }[];
  stepIndex?: number;
}) {
  const { log, elapsed } = useJobLog(job.id);
  const [openLog, setOpenLog] = useState(false);
  const live = log?.live ?? [];
  const draft = live.find((x) => x.name.endsWith("live.md") && x.text.trim());
  const thinkingFile = live.some((x) => x.name.endsWith("live.md")) && !draft;
  const { lines, waiting } = readLog([...live.filter((x) => !x.name.endsWith("live.md") && !x.name.endsWith("thinking.md")).map((x) => x.text), log?.text ?? ""].join("\n"));
  const now = thinkingFile ? "Claude가 원문을 읽고 생각하는 중" : waiting ? "astra 생각 중" : lines[lines.length - 1] ?? "연결 중";
  const progress = steps?.length ? ((stepIndex + 0.5) / steps.length) * 100 : Math.min(95, (elapsed / 120) * 100);
  const doc = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (doc.current) doc.current.scrollTop = doc.current.scrollHeight;
  }, [draft?.text.length]);

  return (
    <div className="overflow-hidden rounded-3xl border border-violet-400/40 bg-panel shadow-[0_0_60px_-20px] shadow-violet-500/40">
      <div className="flex items-end justify-between gap-6 px-8 pt-7">
        <div className="flex items-end gap-4">
          <div className="text-4xl font-bold text-ink">{title}</div>
          <AITextLoading texts={[thinkingFile ? "Claude 생각 중" : status]} className="text-base font-semibold" wrapperClassName="p-0 pb-1 justify-start" />
        </div>
        <div className="pb-1 font-mono text-sm tabular-nums text-ink-3">{mmss(elapsed)}</div>
      </div>

      {steps && steps.length > 1 && (
        <div className="mt-5 flex flex-wrap items-center gap-2 px-8">
          {steps.map((s, i) => (
            <span key={i} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm",
                  i < stepIndex && "border-emerald-400/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-200",
                  i === stepIndex && "border-violet-400/60 bg-violet-500/15 text-violet-800 dark:text-violet-100",
                  i > stepIndex && "border-line text-ink-3"
                )}
              >
                {i < stepIndex ? <IconCheck className="size-3.5" /> : i === stepIndex ? <span className="size-2 animate-pulse rounded-full bg-violet-500" /> : <span className="size-2 rounded-full border border-ink-3" />}
                {s.label}
                {s.by && <span className="opacity-60">· {s.by}</span>}
              </span>
              {i < steps.length - 1 && <span className="text-ink-3">→</span>}
            </span>
          ))}
        </div>
      )}

      <div className="px-8 py-6">
        {draft ? (
          <div ref={doc} className="prose-ko max-h-80 overflow-y-auto rounded-2xl border border-line bg-panel-solid px-7 py-6 text-[15.5px] text-ink">
            <p className="whitespace-pre-wrap">
              {draft.text}
              <span className="ml-0.5 inline-block h-5 w-1.5 animate-pulse bg-violet-500 align-middle" />
            </p>
          </div>
        ) : (
          <AILoadingLive status={now} lines={lines.length ? lines : ["연결 중…"]} progress={progress} />
        )}
      </div>

      <button onClick={() => setOpenLog(!openLog)} className="flex w-full items-center gap-2 border-t border-line px-8 py-3 text-sm text-ink-3 transition hover:bg-soft hover:text-ink">
        <IconChevronDown className={cn("size-4 transition", openLog && "rotate-180")} />
        로그
      </button>
      {openLog && (
        <div className="px-6 pb-6">
          <LiveLog jobId={job.id} />
        </div>
      )}
    </div>
  );
}
