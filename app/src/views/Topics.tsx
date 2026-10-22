import { useMemo, useState } from "react";
import { IconArrowRight, IconChevronDown, IconRefresh, IconSparkles, IconStack2, IconWand } from "@tabler/icons-react";
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
/** 다른 발행처 수 · 가장 최근 사례의 발행일 — 주제 정렬과 카드의 '사례 N · 월.일' */
const pubs = (t: WikiTopic) => new Set(t.sources.map((s) => s.site || site(s.path))).size;
const latest = (t: WikiTopic) => t.sources.reduce((x, s) => ((s.date ?? "") > x ? s.date ?? "" : x), "");
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

/** 사례의 역할 — 중심·받침·반례(반례는 메시지에 조건을 다는 사례라 색을 다르게) */
function RoleChip({ role }: { role: string }) {
  return (
    <Chip
      className={cn(
        "shrink-0 px-2 text-[11px]",
        role === "반례" && "border-amber-400/50 text-amber-700 dark:text-amber-200",
        role === "중심" && "border-violet-400/50 text-violet-700 dark:text-violet-200"
      )}
    >
      {role || "받침"}
    </Chip>
  );
}

// 판정이 비었거나 모르는 값이면 '보통' 탭 — 모르는 값이 오면 탭 묶음에 없는 칸이라 화면 전체가 멈췄다(2026-10-22)
const tabOf = (t: WikiTopic): Tab =>
  t.status !== "쓸 수 있음" ? "쓴 글" : (["쓸 만함", "보통", "뺌"] as string[]).includes(t.verdict ?? "") ? (t.verdict as Tab) : "보통";

export default function Topics({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [pending, setPending] = useState("");
  const [tab, setTab] = useState<Tab>("쓸 만함");
  const [showOld, setShowOld] = useState(false);
  const wiki = state.wiki;
  const ingesting = runningJob(state.jobs, "wiki", "넣기");
  const filtering = runningJob(state.jobs, "wiki-lint", "다시 거르기");
  // 주제 묶기(2026-10-21) — 자동 카드로 메시지 단위 주제를 만든다. 버튼에 아직 묶지 않은 카드 수
  const bundling = runningJob(state.jobs, "wiki", "주제 묶기");
  const unbundled = wiki?.unbundled ?? 0;
  const since = wiki?.bundleSince ? `발행일 ${wiki.bundleSince} 이후` : "최근 1개월";
  const judging = state.jobs.filter((j) => j.kind === "wiki-verdict" && j.status === "running");
  const backlog = newSources(state);

  const byTab = useMemo(() => {
    const m: Record<Tab, WikiTopic[]> = { "쓸 만함": [], 보통: [], 뺌: [], "쓴 글": [] };
    for (const t of wiki?.topics ?? []) m[tabOf(t)].push(t);
    // 사례 수 → 다른 발행처 수 → 가장 최근 사례의 발행일 순(2026-10-22). 예전엔 사례 수가 같으면 파일 이름(소스 알파벳)순이었다
    for (const k of Object.keys(m) as Tab[])
      m[k].sort((a, b) => b.sources.length - a.sources.length || pubs(b) - pubs(a) || latest(b).localeCompare(latest(a)));
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
    // 메시지 단위 주제(2026-10-21): 사례마다 원문 카드를 짝지어 둔다(원문 서랍·있었던 일 전문)
    const cases = (t.cases ?? []).map((c) => ({ c, s: t.sources.find((x) => x.path === `originals/${c.key}.md`) }));
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
            <Chip className="bg-page/70 px-2.5 tabular-nums text-ink-2 backdrop-blur" title="사례 수 · 가장 최근 사례 발행일">
              사례 {t.sources.length}
              {latest(t) && ` · ${latest(t).slice(5).replace("-", ".")}`}
            </Chip>
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
      summary: cases.length ? (
        <ul className="space-y-1.5">
          {cases.map(({ c }) => (
            <li key={c.key} className="flex items-baseline gap-2">
              <RoleChip role={c.role} />
              <span className="line-clamp-2 min-w-0 flex-1 text-[13px] leading-snug">{c.line}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="line-clamp-2">{t.why}</p>
      ),
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
          {cases.length ? (
            <p className="text-[15px] leading-relaxed text-ink-2">{t.why}</p>
          ) : (
            <p className="text-[17px] leading-relaxed text-ink">{t.thesis}</p>
          )}
          {cases.length > 0 && (
            <div className="grid grid-cols-1 gap-2.5">
              {cases.map(({ c, s }) => (
                <button
                  key={c.key}
                  onClick={() => s && setOpen(s.path)}
                  className="flex items-start gap-3 rounded-2xl border border-line bg-soft p-4 text-left transition hover:border-ink-3/40"
                >
                  <RoleChip role={c.role} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-medium leading-snug text-ink">{c.line}</span>
                    <span className="mt-1 flex items-center gap-2 text-sm text-ink-3">
                      <span className="truncate">{[s?.site, s?.who].filter(Boolean).join(" · ")}</span>
                      {s?.new && <Chip className="border-violet-400/40 text-violet-700 dark:text-violet-200">new</Chip>}
                    </span>
                    {s?.note && <span className="mt-2 line-clamp-3 block text-sm leading-relaxed text-ink-2">{s.note}</span>}
                  </span>
                </button>
              ))}
            </div>
          )}
          <div className={cn("grid grid-cols-1 gap-2.5", cases.length > 0 && "hidden")}>
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
            {(unbundled > 0 || bundling) && (
              <HoverBorderGradient
                containerClassName="rounded-full"
                className="flex items-center gap-2 bg-page px-6 py-3 text-ink"
                onClick={() => !bundling && act("wiki-bundle").then(refresh)}
              >
                {bundling ? (
                  <AITextLoading texts={["주제로 묶는 중", `새 카드 ${unbundled}장`]} className="text-sm font-medium" wrapperClassName="p-0" />
                ) : (
                  <>
                    <IconSparkles className="size-4" /> 주제 묶기 {unbundled}
                  </>
                )}
              </HoverBorderGradient>
            )}
            {/* 예전 '넣기'(astra로 원문마다 카드) — 자동 카드(main Sonnet)로 바뀌어 숨김(2026-10-21). 도는 중일 때만 보임, 명령 wiki.py --ingest는 그대로 */}
            {ingesting && (
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
        {bundling && (
          <Working job={bundling} title="주제 묶기" status={`${since} 새 카드 ${unbundled}장 → 메시지 단위 주제(사례 1~3개) · 판정 · 쓸 만함은 제목 후보`} />
        )}
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
