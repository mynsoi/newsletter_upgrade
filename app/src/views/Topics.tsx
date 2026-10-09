import { useState } from "react";
import { IconArrowRight, IconSparkles } from "@tabler/icons-react";
import ExpandableCards from "@/components/expandable-cards";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { AuroraBackground } from "@/components/ui/aurora-background";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, Reactions, SiteIcon, SourceDrawer, sourceName } from "@/components/studio/bits";
import { act, runningJob, type State, type Topic } from "@/lib/api";
import { hue, roundWhen } from "@/lib/text";

export default function Topics({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string>("");
  const running = runningJob(state.jobs, "topics");
  const lib = Object.fromEntries(state.library.map((s) => [s.path, s]));

  const pick = async (round: string, t: Topic) => {
    if (t.brief) return go(`#/a/${t.brief}/title`);
    setBusy(`${round}-${t.n}`);
    const r = await act<{ article: string }>("pick-topic", { round, n: t.n });
    await refresh();
    go(`#/a/${r.article}/title`);
  };

  return (
    <div className="min-h-full">
      <AuroraBackground className="h-[340px] items-stretch justify-end bg-neutral-950 dark:bg-neutral-950" showRadialGradient>
        <div className="relative z-10 mx-auto flex w-full max-w-6xl items-end justify-between px-12 pb-12">
          <h1 className="text-6xl font-bold tracking-tight text-white">주제</h1>
          <HoverBorderGradient
            containerClassName="rounded-full"
            className="flex items-center gap-2 bg-neutral-950 px-6 py-3 text-white"
            onClick={() => !running && act("topics").then(refresh)}
          >
            {running ? (
              <AITextLoading texts={["astra", "원문 읽는 중", "주제 고르는 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
            ) : (
              <>
                <IconSparkles className="size-4" /> 주제 뽑기
              </>
            )}
          </HoverBorderGradient>
        </div>
      </AuroraBackground>

      <div className="mx-auto max-w-6xl space-y-16 px-12 py-12">
        {state.topics.map((r) => (
          <section key={r.id}>
            <div className="mb-5 flex items-center gap-3 text-sm text-neutral-500">
              <span className="tabular-nums">{roundWhen(r.id)}</span>
              <span className="h-px flex-1 bg-white/[0.06]" />
              <span className="tabular-nums">{r.items.length}</span>
            </div>
            <ExpandableCards
              items={r.items.map((t) => ({
                key: `${r.id}-${t.n}`,
                title: t.name,
                dim: false,
                head: (
                  <div
                    className="relative flex h-28 items-end justify-between overflow-hidden px-6 pb-4"
                    style={{
                      background: `radial-gradient(120% 140% at 0% 0%, hsl(${hue(t.name)} 70% 38% / .55), transparent 60%), radial-gradient(120% 140% at 100% 100%, hsl(${(hue(t.name) + 70) % 360} 70% 40% / .35), transparent 55%)`,
                    }}
                  >
                    <span className="text-5xl font-black tabular-nums text-white/90">{String(t.n).padStart(2, "0")}</span>
                    <span className="flex items-center gap-1.5">
                      {t.brief && <Chip className="border-violet-400/50 bg-violet-500/20 text-violet-100">글</Chip>}
                      {t.sources.map((p) => (
                        <span key={p} className="grid size-7 place-items-center rounded-full bg-black/40 ring-1 ring-white/10">
                          <SiteIcon site={lib[p]?.site ?? ""} className="size-3.5" />
                        </span>
                      ))}
                    </span>
                  </div>
                ),
                summary: <p className="line-clamp-3">{t.thesis}</p>,
                action: (
                  <button
                    onClick={() => pick(r.id, t)}
                    className="flex shrink-0 items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-violet-200"
                  >
                    {busy === `${r.id}-${t.n}` ? "…" : t.brief ? "글" : "이 주제로"}
                    <IconArrowRight className="size-4" />
                  </button>
                ),
                body: (
                  <div className="space-y-6">
                    <p className="text-[17px] leading-relaxed text-neutral-200">{t.thesis}</p>
                    <div className="grid grid-cols-1 gap-3">
                      {t.sources.map((p, i) => {
                        const s = lib[p];
                        return (
                          <button
                            key={p}
                            onClick={() => setOpen(p)}
                            className="flex items-start gap-4 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4 text-left transition hover:border-white/20 hover:bg-white/[0.06]"
                          >
                            <span className="mt-0.5 text-xs tabular-nums text-neutral-500">{i + 1}</span>
                            <SiteIcon site={s?.site ?? ""} className="mt-0.5" />
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2">
                                <span className="truncate font-medium text-neutral-100">{sourceName(s, p)}</span>
                                {s && <Reactions n={s.reactions} />}
                              </span>
                              <span className="mt-1 line-clamp-2 block text-sm text-neutral-400">{s?.excerpt}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ),
              }))}
            />
          </section>
        ))}
      </div>
      <SourceDrawer path={open} onClose={() => setOpen(null)} />
    </div>
  );
}
