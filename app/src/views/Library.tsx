import { useMemo, useRef, useState } from "react";
import { IconArrowRight, IconDatabase, IconSparkles, IconWorldSearch } from "@tabler/icons-react";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { BentoGrid } from "@/components/ui/bento-grid";
import { GlowingEffect } from "@/components/ui/glowing-effect";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { PillTabs } from "@/components/ui/tabs";
import { Spotlight } from "@/components/ui/spotlight-new";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, Reactions, SiteIcon, SourceDrawer, sourceName } from "@/components/studio/bits";
import { act, runningJob, type Source, type State } from "@/lib/api";
import { Working } from "@/components/studio/working";
import { roundWhen } from "@/lib/text";
import { cn } from "@/lib/utils";

const ORDER = ["T2", "T3", "T4", "T1", "infuture"];
// Supabase에서 받은 원문(scripts/db_sources.py)은 사이트가 서른 곳 가까이라 등급으로 묶어 탭을 만든다
const TIER: Record<string, string> = { T1: "연구기관", T2: "컨설팅", T3: "저널·매체", T4: "기업 자료" };
const group = (s: Source) => (s.tier ? s.tier : s.site);
const groupName = (s: Source) => (s.tier ? TIER[s.tier] ?? s.tier : s.siteName);

export default function Library({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [site, setSiteRaw] = useState("all");
  const [src, setSrc] = useState("all"); // 분류 안의 소스 — 분류를 바꾸면 전체로
  const setSite = (v: string) => {
    setSiteRaw(v);
    setSrc("all");
  };
  const [open, setOpen] = useState<string | null>(null);
  const [req, setReq] = useState("");
  const collecting = state.jobs.filter((j) => j.kind === "collect" && j.status === "running");
  // Supabase 받기 — 서버가 켜질 때와 6시간마다 저절로 돌고(studio_server.db_sync_loop), 버튼으로 바로 받을 수도 있다
  const syncs = state.jobs.filter((j) => j.kind === "db-sync");
  const syncing = syncs.some((j) => j.status === "running");
  const lastSync = syncs.find((j) => j.status !== "running");
  const box = useRef<HTMLDivElement>(null);
  const collect = () => {
    if (!req.trim()) return act("collect", { request: "" }).then(refresh); // 비우면 소스 aside 수집(Deloitte·BCG·DBR·HBR Korea·McKinsey·Wharton → Supabase)
    box.current?.querySelector("form")?.requestSubmit();
  };

  const sites = useMemo(() => {
    const m = new Map<string, { name: string; n: number }>();
    for (const s of state.library) m.set(group(s), { name: groupName(s), n: (m.get(group(s))?.n ?? 0) + 1 });
    return [...m.entries()].sort((a, b) => (ORDER.indexOf(a[0]) + 99) % 99 - (ORDER.indexOf(b[0]) + 99) % 99);
  }, [state.library]);

  // 고른 분류(등급) 안의 소스별 개수 — 많은 순. 소스가 하나뿐인 분류(경영일기)는 하위 탭을 안 띄운다
  const srcs = useMemo(() => {
    const m = new Map<string, { name: string; n: number }>();
    for (const s of state.library) if (group(s) === site) m.set(s.site, { name: s.siteName, n: (m.get(s.site)?.n ?? 0) + 1 });
    return [...m.entries()].sort((a, b) => b[1].n - a[1].n);
  }, [state.library, site]);

  const fresh = useMemo(() => new Set(state.collects.flatMap((c) => c.saved.map((s) => s.path).filter(Boolean))), [state.collects]);

  const rows = useMemo(() => {
    const r = state.library.filter((s) => (site === "all" || group(s) === site) && (src === "all" || s.site === src));
    return r.sort((a, b) => {
      const fa = fresh.has(a.path) ? 0 : 1,
        fb = fresh.has(b.path) ? 0 : 1;
      if (fa !== fb) return fa - fb;
      const oa = ORDER.indexOf(group(a)),
        ob = ORDER.indexOf(group(b));
      if (oa !== ob) return (oa + 99) % 99 - (ob + 99) % 99;
      return b.date.localeCompare(a.date);
    });
  }, [state.library, site, src, fresh]);

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
                "비워 두고 누르면 소스 수집 — Deloitte·BCG·DBR·HBR Korea·McKinsey·Wharton",
                "적으면 그 내용으로 aside가 글을 찾아요 — 예: 사내 AI 도입 실패담",
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
              onClick={() => !syncing && act("db-sync", {}).then(refresh)}
              disabled={syncing}
              title={lastSync ? `마지막 받기 ${new Date((lastSync.ended ?? lastSync.started) * 1000).toLocaleString("ko-KR")} · ${lastSync.status === "done" ? "완료" : "실패"}` : "아직 받은 적 없음"}
              className="flex shrink-0 items-center gap-2 rounded-full border border-line bg-page px-5 py-2.5 text-sm font-medium text-ink transition hover:border-violet-400 disabled:opacity-60"
            >
              <IconDatabase className={cn("size-4", syncing && "animate-pulse")} /> {syncing ? "받는 중" : "Supabase 받기"}
            </button>
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
                  {!k.startsWith("T") && <SiteIcon site={k} className="size-3.5" />}
                  {v.name} {v.n}
                </span>
              ),
            })),
          ]}
        />

        {site !== "all" && srcs.length > 1 && (
          <PillTabs
            id="pilltab-src"
            className="mt-3 flex-wrap"
            value={src}
            onChange={setSrc}
            tabs={[
              { value: "all", title: <span className="tabular-nums">전체 {srcs.reduce((n, [, v]) => n + v.n, 0)}</span> },
              ...srcs.map(([k, v]) => ({ value: k, title: <span className="tabular-nums">{v.name} {v.n}</span> })),
            ]}
          />
        )}

        <BentoGrid className="mt-8 max-w-none md:auto-rows-[15.5rem] md:grid-cols-4 grid-flow-dense">
          {collecting.map((j) => (
            <div key={j.id} className="col-span-4 row-span-2">
              <Working job={j} title="수집" status={`aside · ${j.target}`} />
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
          {s.tier && <span className="truncate">{s.siteName}</span>}
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
