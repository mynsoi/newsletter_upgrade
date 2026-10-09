import { useMemo, useRef, useState } from "react";
import { IconArrowRight, IconSparkles, IconWorldSearch } from "@tabler/icons-react";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { BentoGrid } from "@/components/ui/bento-grid";
import { GlowingEffect } from "@/components/ui/glowing-effect";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { PillTabs } from "@/components/ui/tabs";
import { Spotlight } from "@/components/ui/spotlight-new";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, Reactions, SiteIcon, SourceDrawer, sourceName } from "@/components/studio/bits";
import { act, runningJob, type Source, type State } from "@/lib/api";
import { LiveLog } from "@/components/studio/live-log";
import { roundWhen } from "@/lib/text";
import { cn } from "@/lib/utils";

const ORDER = ["threads", "linkedin", "infuture"];

export default function Library({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [site, setSite] = useState("all");
  const [open, setOpen] = useState<string | null>(null);
  const [req, setReq] = useState("");
  const collecting = state.jobs.filter((j) => j.kind === "collect" && j.status === "running");
  const box = useRef<HTMLDivElement>(null);
  const collect = () => {
    if (!req.trim()) return act("collect", { request: "" }).then(refresh); // 비우면 자동 — Threads·LinkedIn에서 알아서
    box.current?.querySelector("form")?.requestSubmit();
  };

  const sites = useMemo(() => {
    const m = new Map<string, { name: string; n: number }>();
    for (const s of state.library) m.set(s.site, { name: s.siteName, n: (m.get(s.site)?.n ?? 0) + 1 });
    return [...m.entries()].sort((a, b) => (ORDER.indexOf(a[0]) + 99) % 99 - (ORDER.indexOf(b[0]) + 99) % 99);
  }, [state.library]);

  const fresh = useMemo(() => new Set(state.collects.flatMap((c) => c.saved.map((s) => s.path).filter(Boolean))), [state.collects]);

  const rows = useMemo(() => {
    const r = state.library.filter((s) => site === "all" || s.site === site);
    return r.sort((a, b) => {
      const fa = fresh.has(a.path) ? 0 : 1,
        fb = fresh.has(b.path) ? 0 : 1;
      if (fa !== fb) return fa - fb;
      const oa = ORDER.indexOf(a.site),
        ob = ORDER.indexOf(b.site);
      if (oa !== ob) return (oa + 99) % 99 - (ob + 99) % 99;
      return b.date.localeCompare(a.date);
    });
  }, [state.library, site, fresh]);

  const wide = (s: Source) => {
    const n = parseInt(s.reactions.replace(/\D/g, "") || "0", 10);
    return n >= 200 || s.chars > 3000;
  };

  return (
    <div className="relative min-h-full">
      <div className="relative h-[380px] overflow-hidden border-b border-line">
        <Spotlight />
        <div className="relative z-10 mx-auto flex h-full max-w-6xl flex-col justify-end px-12 pb-12">
          <h1 className="text-6xl font-bold tracking-tight text-ink">서재</h1>
          <div className="mt-8 flex items-center gap-3">
          <div ref={box} className="w-full max-w-2xl [&_form]:mx-0 [&_form]:max-w-2xl">
            <PlaceholdersAndVanishInput
              placeholders={[
                "Threads에서 AI로 일하는 방식을 바꾼 실무자 글",
                "LinkedIn에서 사내 AI 도입 실패담",
                "「유정식의 경영일기」에서 팀워크를 다룬 글",
              ]}
              onChange={(e) => setReq(e.target.value)}
              onSubmit={(e) => {
                e.preventDefault();
                if (!req.trim()) return;
                act("collect", { request: req }).then(refresh);
              }}
            />
          </div>
            <HoverBorderGradient
              containerClassName="shrink-0 rounded-full"
              className="flex items-center gap-2 bg-page px-5 py-2.5 text-sm font-medium text-ink"
              onClick={collect}
            >
              <IconWorldSearch className="size-4" /> aside 수집
            </HoverBorderGradient>
            <button
              onClick={() => go("#/topics")}
              className="flex shrink-0 items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-page transition hover:bg-violet-500 hover:text-white"
            >
              <IconSparkles className="size-4" /> 주제 지도 <IconArrowRight className="size-4" />
            </button>
          </div>
          {state.collects.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {state.collects.slice(0, 6).map((c) => (
                <Chip key={c.id} className="bg-page/60 backdrop-blur">
                  <span className="tabular-nums text-ink-3">{roundWhen(c.id)}</span>
                  <span className="max-w-64 truncate">{c.request}</span>
                  <span className="tabular-nums text-violet-700 dark:text-violet-300">+{c.saved.filter((x) => x.path).length}</span>
                </Chip>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-12 py-10">
        <PillTabs
          value={site}
          onChange={setSite}
          tabs={[
            { value: "all", title: <span className="tabular-nums">전체 {state.library.length}</span> },
            ...sites.map(([k, v]) => ({
              value: k,
              title: (
                <span className="flex items-center gap-2 tabular-nums">
                  <SiteIcon site={k} className="size-3.5" />
                  {v.name} {v.n}
                </span>
              ),
            })),
          ]}
        />

        <BentoGrid className="mt-8 max-w-none md:auto-rows-[15.5rem] md:grid-cols-4 grid-flow-dense">
          {collecting.map((j) => (
            <div key={j.id} className="relative col-span-4 row-span-2 flex flex-col gap-3 rounded-2xl border border-violet-400/30 bg-violet-500/[0.06] p-4">
              <AITextLoading texts={[j.target, "aside", "UltraBrowse"]} className="text-xl" wrapperClassName="p-2" />
              <LiveLog jobId={j.id} compact />
            </div>
          ))}
          {rows.map((s) => (
            <SourceCard key={s.path} s={s} wide={wide(s)} fresh={fresh.has(s.path)} onOpen={() => setOpen(s.path)} />
          ))}
        </BentoGrid>
      </div>
      <SourceDrawer path={open} onClose={() => setOpen(null)} />
    </div>
  );
}

function SourceCard({ s, wide, fresh, onOpen }: { s: Source; wide: boolean; fresh: boolean; onOpen: () => void }) {
  return (
    <div className={cn("relative rounded-2xl", wide && "md:col-span-2")} onClick={onOpen}>
      <GlowingEffect spread={40} glow disabled={false} proximity={64} inactiveZone={0.01} borderWidth={2} />
      <div className="group/bento relative flex h-full cursor-pointer flex-col justify-between overflow-hidden rounded-2xl border border-line bg-panel p-5 transition duration-200 hover:bg-panel-solid">
        <div className="flex items-center gap-2 text-xs text-ink-2">
          <SiteIcon site={s.site} />
          <span className="truncate">{s.date}</span>
          <span className="ml-auto flex items-center gap-2">
            {fresh && <Chip className="border-violet-400/40 text-violet-700 dark:text-violet-200">new</Chip>}
            <Reactions n={s.reactions} />
          </span>
        </div>
        <div className="mt-4 flex-1 overflow-hidden transition duration-200 group-hover/bento:translate-x-1">
          <div className={cn("font-semibold text-ink leading-snug", wide ? "text-xl" : "text-base", "line-clamp-2")}>
            {sourceName(s)}
          </div>
          <p className={cn("mt-3 text-sm leading-relaxed text-ink-2", wide ? "line-clamp-4" : "line-clamp-3")}>{s.excerpt}</p>
        </div>
        <div className="mt-3 text-xs tabular-nums text-ink-3">{s.chars.toLocaleString()}자</div>
      </div>
    </div>
  );
}
