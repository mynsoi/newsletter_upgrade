import { useEffect, useMemo, useState } from "react";
import { IconArrowRight, IconChevronDown, IconStack2, IconWand } from "@tabler/icons-react";
import ExpandableCards from "@/components/expandable-cards";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { AuroraBackground } from "@/components/ui/aurora-background";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { act, runningJob, type State, type WikiTopic } from "@/lib/api";
import { hue, roundWhen } from "@/lib/text";
import { cn } from "@/lib/utils";

/** 아직 위키에 넣지 않은 원문 수 — 메뉴의 점과 '넣기' 버튼에 쓴다 */
export function newSources(state: State) {
  return state.wiki?.backlog.length ?? 0;
}

const site = (p: string) => p.split("/")[1] ?? "";

/** 주제 페이지의 used_in(briefs/<id>.json · columns/<id>.md)에서 작업실 글 id를 찾는다 */
function articleOf(t: WikiTopic, state: State) {
  for (const u of [...t.usedIn].reverse()) {
    const m = u.match(/^(?:briefs|columns)\/(.+?)\.(?:json|md)$/);
    if (m && state.articles.some((a) => a.id === m[1])) return m[1];
  }
  return "";
}

export default function Topics({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [pending, setPending] = useState("");
  const [showOld, setShowOld] = useState(false);
  const wiki = state.wiki;
  const ingesting = runningJob(state.jobs, "wiki", "넣기");
  const linting = runningJob(state.jobs, "wiki-lint", "정리");
  const backlog = newSources(state);

  // 고른 주제의 설정이 만들어지면 그 글의 제목 화면으로 간다
  useEffect(() => {
    if (!pending || !wiki) return;
    const t = wiki.topics.find((x) => x.page === pending);
    const id = t && articleOf(t, state);
    if (id) {
      setPending("");
      go(`#/a/${id}/title`);
    }
  }, [state, pending]); // eslint-disable-line

  const fields = useMemo(() => {
    const m = new Map<string, WikiTopic[]>();
    for (const t of wiki?.topics ?? []) m.set(t.field, [...(m.get(t.field) ?? []), t]);
    const rank = (t: WikiTopic) => (t.status === "쓸 수 있음" ? 0 : 1) * 1000 - t.sources.length * 10 - (t.sources.some((s) => s.new) ? 1 : 0);
    return [...m.entries()]
      .map(([f, ts]) => [f, [...ts].sort((a, b) => rank(a) - rank(b))] as const)
      .sort((a, b) => b[1].reduce((n, t) => n + t.sources.length, 0) - a[1].reduce((n, t) => n + t.sources.length, 0));
  }, [wiki]);

  const pick = async (t: WikiTopic) => {
    const id = articleOf(t, state);
    if (id) return go(`#/a/${id}`);
    setPending(t.page);
    await act("wiki-pick", { page: t.page });
    refresh();
  };

  return (
    <div className="min-h-full">
      <AuroraBackground className="h-[340px] items-stretch justify-end bg-page dark:bg-page" showRadialGradient>
        <div className="relative z-10 mx-auto flex w-full max-w-6xl items-end justify-between px-12 pb-12">
          <div>
            <h1 className="text-6xl font-bold tracking-tight text-ink">주제</h1>
            {wiki && (
              <div className="mt-4 flex gap-2">
                <Chip className="bg-page/60 px-3 py-1 text-sm backdrop-blur">원문 {wiki.processed}</Chip>
                <Chip className="bg-page/60 px-3 py-1 text-sm backdrop-blur">주제 {wiki.topics.length}</Chip>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => !linting && act("wiki-lint").then(refresh)}
              className="flex items-center gap-2 rounded-full border border-line bg-page/70 px-5 py-3 text-sm text-ink backdrop-blur transition hover:bg-soft"
            >
              {linting ? (
                <AITextLoading texts={["정리 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
              ) : (
                <>
                  <IconWand className="size-4" /> 정리
                </>
              )}
            </button>
            {(backlog > 0 || ingesting) && (
              <HoverBorderGradient
                containerClassName="rounded-full"
                className="flex items-center gap-2 bg-page px-6 py-3 text-ink"
                onClick={() => !ingesting && act("wiki-ingest").then(refresh)}
              >
                {ingesting ? (
                  <AITextLoading texts={["astra", `넣는 중 · 남은 ${backlog}편`]} className="text-sm font-medium" wrapperClassName="p-0" />
                ) : (
                  <>
                    <IconStack2 className="size-4" /> 넣기 {backlog}
                  </>
                )}
              </HoverBorderGradient>
            )}
          </div>
        </div>
      </AuroraBackground>

      <div className="mx-auto max-w-6xl space-y-16 px-12 py-12">
        {fields.map(([field, ts]) => (
          <section key={field}>
            <div className="mb-5 flex items-center gap-3 text-sm text-ink-3">
              <span className="text-base font-semibold text-ink-2">{field}</span>
              <span className="h-px flex-1 bg-line" />
              <span className="tabular-nums">{ts.length}</span>
            </div>
            <ExpandableCards
              items={ts.map((t) => {
                const id = articleOf(t, state);
                const picking = pending === t.page || !!runningJob(state.jobs, "wiki-pick", t.page);
                const fresh = t.sources.filter((s) => s.new).length;
                return {
                  key: t.page,
                  title: t.title,
                  dim: t.status !== "쓸 수 있음",
                  head: (
                    <div
                      className="relative flex h-28 items-end justify-between overflow-hidden px-6 pb-4"
                      style={{
                        background: `radial-gradient(120% 140% at 0% 0%, hsl(${hue(t.title)} 70% 45% / .45), transparent 60%), radial-gradient(120% 140% at 100% 100%, hsl(${(hue(t.title) + 70) % 360} 70% 45% / .3), transparent 55%)`,
                      }}
                    >
                      <span className="flex items-baseline gap-1.5">
                        <span className="text-5xl font-black tabular-nums text-ink">{t.sources.length}</span>
                        <span className="text-sm text-ink-2">원문</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        {fresh > 0 && <Chip className="border-violet-400/50 bg-violet-500/20 text-violet-800 dark:text-violet-100">new {fresh}</Chip>}
                        {t.status !== "쓸 수 있음" && <Chip className="bg-page/70 text-ink">{t.status}</Chip>}
                        {[...new Set(t.sources.map((s) => site(s.path)))].map((sname) => (
                          <span key={sname} className="grid size-7 place-items-center rounded-full bg-page/60 ring-1 ring-line">
                            <SiteIcon site={sname} className="size-3.5" />
                          </span>
                        ))}
                      </span>
                    </div>
                  ),
                  summary: <p className="line-clamp-3">{t.thesis}</p>,
                  action: (
                    <button
                      onClick={() => !picking && pick(t)}
                      className={cn(
                        "flex shrink-0 items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition",
                        picking ? "bg-soft text-ink" : "bg-ink text-page hover:bg-violet-500 hover:text-white"
                      )}
                    >
                      {picking ? (
                        <AITextLoading texts={["astra", "원문 깊게 읽는 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
                      ) : (
                        <>
                          {id ? "글" : "이 주제로"}
                          <IconArrowRight className="size-4" />
                        </>
                      )}
                    </button>
                  ),
                  body: (
                    <div className="space-y-6">
                      <p className="text-[17px] leading-relaxed text-ink">{t.thesis}</p>
                      <div className="grid grid-cols-1 gap-2.5">
                        {t.sources.map((s) => (
                          <button
                            key={s.path}
                            onClick={() => setOpen(s.path)}
                            className="flex items-start gap-3 rounded-2xl border border-line bg-soft p-4 text-left transition hover:border-ink-3/40"
                          >
                            <SiteIcon site={site(s.path)} className="mt-0.5" />
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2 text-sm text-ink-2">
                                <span className="truncate">{s.who}</span>
                                {s.new && <Chip className="border-violet-400/40 text-violet-700 dark:text-violet-200">new</Chip>}
                              </span>
                              <span className="mt-1 block text-sm leading-relaxed text-ink">{s.note}</span>
                            </span>
                          </button>
                        ))}
                      </div>
                      {t.angles.length > 0 && (
                        <ul className="space-y-1.5 text-sm leading-relaxed text-ink-2">
                          {t.angles.map((x, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-ink-3">·</span>
                              <span>{x}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                      {t.related.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {t.related.map((r) => (
                            <Chip key={r.page}>{r.title}</Chip>
                          ))}
                        </div>
                      )}
                    </div>
                  ),
                };
              })}
            />
          </section>
        ))}

        {state.topics.length > 0 && (
          <section>
            <button onClick={() => setShowOld(!showOld)} className="flex items-center gap-2 text-sm text-ink-3 hover:text-ink">
              <IconChevronDown className={cn("size-4 transition", showOld && "rotate-180")} />
              이전 방식 회차 {state.topics.length}
            </button>
            {showOld && (
              <div className="mt-6 space-y-10 opacity-70">
                {state.topics.map((r) => (
                  <div key={r.id}>
                    <div className="mb-3 text-sm tabular-nums text-ink-3">{roundWhen(r.id)}</div>
                    <div className="grid grid-cols-3 gap-3">
                      {r.items.map((t) => (
                        <div key={t.n} className="rounded-2xl border border-line bg-panel p-4">
                          <div className="font-medium text-ink">{t.name}</div>
                          <div className="mt-1 line-clamp-2 text-sm text-ink-2">{t.thesis}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
      <SourceDrawer path={open} onClose={() => setOpen(null)} />
    </div>
  );
}
