import { useMemo, useState } from "react";
import { BentoGrid } from "@/components/ui/bento-grid";
import { GlowingEffect } from "@/components/ui/glowing-effect";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { PillTabs } from "@/components/ui/tabs";
import { Spotlight } from "@/components/ui/spotlight-new";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, Reactions, SiteIcon, SourceDrawer, sourceName } from "@/components/studio/bits";
import { act, type Source, type State } from "@/lib/api";
import { cn } from "@/lib/utils";

const ORDER = ["threads", "linkedin", "infuture"];

export default function Library({ state, refresh }: { state: State; refresh: () => void }) {
  const [site, setSite] = useState("all");
  const [open, setOpen] = useState<string | null>(null);
  const [req, setReq] = useState("");
  const collecting = state.jobs.filter((j) => j.kind === "collect" && j.status === "running");

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
      <div className="relative h-[340px] overflow-hidden border-b border-white/[0.06]">
        <Spotlight />
        <div className="relative z-10 mx-auto flex h-full max-w-6xl flex-col justify-end px-12 pb-12">
          <h1 className="text-6xl font-bold tracking-tight text-white">서재</h1>
          <div className="mt-8 w-full max-w-2xl [&_form]:mx-0 [&_form]:max-w-2xl">
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
            <div key={j.id} className="relative col-span-2 flex items-center justify-center rounded-2xl border border-violet-400/30 bg-violet-500/[0.06]">
              <AITextLoading texts={[j.target, "aside", "UltraBrowse"]} className="text-xl" />
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
      <div className="group/bento relative flex h-full cursor-pointer flex-col justify-between overflow-hidden rounded-2xl border border-white/[0.08] bg-neutral-900/70 p-5 transition duration-200 hover:bg-neutral-900">
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <SiteIcon site={s.site} />
          <span className="truncate">{s.date}</span>
          <span className="ml-auto flex items-center gap-2">
            {fresh && <Chip className="border-violet-400/40 text-violet-200">new</Chip>}
            <Reactions n={s.reactions} />
          </span>
        </div>
        <div className="mt-4 flex-1 overflow-hidden transition duration-200 group-hover/bento:translate-x-1">
          <div className={cn("font-semibold text-neutral-100 leading-snug", wide ? "text-xl" : "text-base", "line-clamp-2")}>
            {sourceName(s)}
          </div>
          <p className={cn("mt-3 text-sm leading-relaxed text-neutral-400", wide ? "line-clamp-4" : "line-clamp-3")}>{s.excerpt}</p>
        </div>
        <div className="mt-3 text-xs tabular-nums text-neutral-600">{s.chars.toLocaleString()}자</div>
      </div>
    </div>
  );
}
