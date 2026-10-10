import { useMemo, useState } from "react";
import { IconArrowRight, IconChevronDown, IconRefresh, IconStack2, IconWand } from "@tabler/icons-react";
import ExpandableCards from "@/components/expandable-cards";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { PillTabs } from "@/components/ui/tabs";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { Working } from "@/components/studio/working";
import { act, runningJob, type State, type WikiTopic } from "@/lib/api";
import { hue, roundWhen } from "@/lib/text";
import { cn } from "@/lib/utils";

/** 아직 주제 지도에 넣지 않은 원문 수 — 메뉴의 점과 '넣기' 버튼에 쓴다 */
export function newSources(state: State) {
  return state.wiki?.backlog.length ?? 0;
}

const site = (p: string) => p.split("/")[1] ?? "";
const VERDICTS = ["쓸 만함", "보통", "뺌"] as const;
type Tab = (typeof VERDICTS)[number] | "쓴 글";

/** 주제 페이지의 used_in(briefs/<id>.json · columns/<id>.md)에서 작업실 글 id를 찾는다 */
function articleOf(t: WikiTopic, state: State) {
  for (const u of [...t.usedIn].reverse()) {
    const m = u.match(/^(?:briefs|columns)\/(.+?)\.(?:json|md)$/);
    if (m && state.articles.some((a) => a.id === m[1])) return m[1];
  }
  return "";
}

const tabOf = (t: WikiTopic): Tab => (t.status !== "쓸 수 있음" ? "쓴 글" : ((t.verdict as Tab) || "보통"));

export default function Topics({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [pending, setPending] = useState("");
  const [tab, setTab] = useState<Tab>("쓸 만함");
  const [showOld, setShowOld] = useState(false);
  const wiki = state.wiki;
  const ingesting = runningJob(state.jobs, "wiki", "넣기");
  const filtering = runningJob(state.jobs, "wiki-lint", "다시 거르기");
  const judging = state.jobs.filter((j) => j.kind === "wiki-verdict" && j.status === "running");
  const backlog = newSources(state);

  const byTab = useMemo(() => {
    const m: Record<Tab, WikiTopic[]> = { "쓸 만함": [], 보통: [], 뺌: [], "쓴 글": [] };
    for (const t of wiki?.topics ?? []) m[tabOf(t)].push(t);
    for (const k of Object.keys(m) as Tab[]) m[k].sort((a, b) => b.sources.length - a.sources.length);
    return m;
  }, [wiki]);

  // 누르면 서버가 그 자리에서 글 설정을 만들고 id를 돌려준다 → 바로 그 글의 제목 화면으로(제목 후보가 이미 떠 있다)
  const pick = async (t: WikiTopic, again = false) => {
    const id = articleOf(t, state);
    if (id && !again) return go(`#/a/${id}`);
    setPending(t.page);
    try {
      const r = await act<{ article: string }>("wiki-pick", { page: t.page });
      go(`#/a/${r.article}/title`);
    } finally {
      setPending("");
    }
  };

  const judge = (t: WikiTopic, v: string) => v !== t.verdict && act("wiki-verdict", { page: t.page, verdict: v }).then(refresh);

  const items = byTab[tab].map((t) => {
    const id = articleOf(t, state);
    const picking = pending === t.page;
    const fresh = t.sources.filter((s) => s.new).length;
    const busy = judging.some((j) => j.target === t.page);
    return {
      key: t.page,
      title: t.title,
      dim: tab === "뺌",
      head: (
        <div
          className="relative flex h-24 items-end justify-between overflow-hidden px-6 pb-4"
          style={{
            background: `radial-gradient(120% 140% at 0% 0%, hsl(${hue(t.title)} 70% 45% / .45), transparent 60%), radial-gradient(120% 140% at 100% 100%, hsl(${(hue(t.title) + 70) % 360} 70% 45% / .3), transparent 55%)`,
          }}
        >
          <span className="flex flex-wrap items-center gap-1.5">
            {(t.audience || "").split("·").filter(Boolean).map((a) => (
              <Chip key={a} className="bg-page/70 px-2.5 text-ink backdrop-blur">{a}</Chip>
            ))}
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
      summary: <p className="line-clamp-2">{t.why}</p>,
      action: (
        <span className="flex shrink-0 items-center gap-2">
          {id && !picking && (
            <button
              onClick={() => pick(t, true)}
              className="flex items-center gap-1.5 rounded-full border border-line px-4 py-2.5 text-sm text-ink transition hover:bg-soft"
            >
              <IconRefresh className="size-4" /> 다시
            </button>
          )}
          <button
            onClick={() => !picking && pick(t)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition",
              picking ? "bg-soft text-ink" : "bg-ink text-page hover:bg-violet-500 hover:text-white"
            )}
          >
            {picking ? (
              <AITextLoading texts={["글 만드는 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
            ) : (
              <>
                {id ? "글" : "이 주제로"}
                <IconArrowRight className="size-4" />
              </>
            )}
          </button>
        </span>
      ),
      body: (
        <div className="space-y-7">
          {(t.titles?.length ?? 0) > 0 && (
            <ol className="grid grid-flow-col grid-cols-2 grid-rows-4 gap-x-8 gap-y-2.5">
              {t.titles!.map((x, i) => (
                <li key={i} className="flex gap-3 text-[15px] leading-snug text-ink">
                  <span className="w-4 shrink-0 text-right text-sm tabular-nums text-ink-3">{i + 1}</span>
                  <span>{x}</span>
                </li>
              ))}
            </ol>
          )}
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
          <div className="flex items-center gap-3">
            {busy ? (
              <AITextLoading texts={["판정 반영 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
            ) : (
              <PillTabs
                id={`verdict-${t.page}`}
                tabs={VERDICTS.map((v) => ({ value: v, title: v }))}
                value={t.verdict || ""}
                onChange={(v) => judge(t, v)}
              />
            )}
          </div>
        </div>
      ),
    };
  });

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
              onClick={() => !filtering && act("wiki-lint").then(refresh)}
              className="flex items-center gap-2 rounded-full border border-line bg-page/70 px-5 py-3 text-sm text-ink backdrop-blur transition hover:bg-soft"
            >
              {filtering ? (
                <AITextLoading texts={["다시 거르는 중"]} className="text-sm font-medium" wrapperClassName="p-0" />
              ) : (
                <>
                  <IconWand className="size-4" /> 다시 거르기
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
                  <AITextLoading texts={["넣는 중", `남은 ${backlog}편`]} className="text-sm font-medium" wrapperClassName="p-0" />
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

      <div className="sticky top-0 z-30 border-b border-line bg-page/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center px-12 py-3">
          <PillTabs
            id="verdicttab"
            tabs={(["쓸 만함", "보통", "뺌", "쓴 글"] as Tab[]).map((v) => ({
              value: v,
              title: (
                <span className="flex items-center gap-2">
                  {v}
                  <span className="tabular-nums text-ink-3">{byTab[v].length}</span>
                </span>
              ),
            }))}
            value={tab}
            onChange={(v) => setTab(v as Tab)}
          />
        </div>
      </div>

      <div className="mx-auto max-w-6xl space-y-16 px-12 py-12">
        {(ingesting || filtering) && (
          <Working
            job={(ingesting || filtering)!}
            title={ingesting ? "주제 넣기" : "다시 거르기"}
            status={ingesting ? `카드 → 묶기 → 거르기 → 제목 후보 · 남은 ${backlog}편` : "Claude가 판정 예시를 보고 다시 거르는 중"}
          />
        )}
        <ExpandableCards items={items} />

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
                      {r.items.map((x) => (
                        <div key={x.n} className="rounded-2xl border border-line bg-panel p-4">
                          <div className="font-medium text-ink">{x.name}</div>
                          <div className="mt-1 line-clamp-2 text-sm text-ink-2">{x.thesis}</div>
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
