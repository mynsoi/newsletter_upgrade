import { useEffect, useRef, useState } from "react";
import { getLog, type JobLog } from "@/lib/api";
import { cn } from "@/lib/utils";

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** 작업 로그 꼬리 — 1.5초마다 받아 온다. 쓰는 중인 글(live.md)이 있으면 그걸 먼저, 그다음 astra·aside 출력과 작업 로그 */
export function LiveLog({ jobId, compact = false, className }: { jobId: string; compact?: boolean; className?: string }) {
  const [log, setLog] = useState<JobLog | null>(null);
  const [tick, setTick] = useState(0);
  const box = useRef<HTMLDivElement>(null);
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
  useEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [log]);
  const live = log?.live ?? [];
  const writing = live.find((x) => x.name.endsWith("live.md") && x.text.trim());
  const thinking = !writing ? live.find((x) => x.name.endsWith("thinking.md") && x.text.trim()) : undefined;
  const others = live.filter((x) => x !== writing && !x.name.endsWith("live.md") && !x.name.endsWith("thinking.md"));
  const running = log?.status === "running";
  const lines = (t: string) => t.split("\n").filter((l) => l.trim()).slice(compact ? -6 : -200).join("\n");
  return (
    <div className={cn("w-full overflow-hidden rounded-2xl border border-line bg-panel-solid/80 text-left", className)}>
      <div className="flex items-center gap-2 border-b border-line px-4 py-2 text-xs text-ink-3">
        <span className={cn("size-2 rounded-full", running ? "animate-pulse bg-emerald-500" : log?.status === "failed" ? "bg-rose-500" : "bg-ink-3")} />
        <span className="tabular-nums">{mmss((log?.elapsed ?? 0) + (running ? tick : 0))}</span>
        {(writing ?? others[0]) && <span className="truncate">{(writing ?? others[0]).name}</span>}
      </div>
      <div ref={box} className={cn("overflow-y-auto px-4 py-3", compact ? "max-h-40" : "max-h-[62vh]")}>
        {writing && writing.text.trim() && (
          <p className={cn("whitespace-pre-wrap text-ink", compact ? "line-clamp-4 text-[13px] leading-relaxed" : "mb-4 text-[15px] leading-relaxed")}>
            {compact ? writing.text.slice(-400) : writing.text}
            {running && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-violet-500 align-middle" />}
          </p>
        )}
        {running && !writing && !thinking && live.some((x) => x.name.endsWith("live.md")) && (
          <p className="mb-2 flex items-center gap-2 text-[13px] text-violet-600 dark:text-violet-300">
            <span className="size-2 animate-pulse rounded-full bg-violet-500" />
            Claude 생각 중
          </p>
        )}
        {thinking && (
          <p className={cn("whitespace-pre-wrap italic text-ink-3", compact ? "line-clamp-3 text-[12.5px]" : "mb-4 text-[13.5px]")}>
            <span className="not-italic text-violet-600 dark:text-violet-300">생각 중 · </span>
            {thinking.text.slice(compact ? -300 : -3000)}
          </p>
        )}
        {[...others.map((x) => x.text), log?.text ?? ""].filter((t) => t.trim()).map((t, i) => (
          <pre key={i} className="whitespace-pre-wrap break-all font-mono text-[11.5px] leading-relaxed text-ink-3">{lines(t)}</pre>
        ))}
        {!log && <pre className="font-mono text-[11.5px] text-ink-3">…</pre>}
      </div>
    </div>
  );
}
