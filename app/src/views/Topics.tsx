import { useMemo, useState } from "react";
import { IconArrowRight, IconFlameFilled, IconRefresh, IconSparkles, IconStack2, IconWand } from "@tabler/icons-react";
import ExpandableCards from "@/components/expandable-cards";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { PillTabs } from "@/components/ui/tabs";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { Working } from "@/components/studio/working";
import { act, runningJob, type State, type WikiTopic } from "@/lib/api";
import { hue } from "@/lib/text";
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
// 핫·지난 주제(2026-11-20) — 판정과 따로 날짜로 나눈다. 핫 = 쓸 만함 중 최근 1개월 발행처 hotMin곳 이상(쓸 만함 탭에도 함께 보임),
// 지난 주제 = 최근 1개월 사례가 없는 쓸 수 있는 주제(판정 탭에서 빠짐, 새 사례가 붙으면 돌아온다)
type Tab = "핫" | (typeof VERDICTS)[number] | "지난 주제" | "쓴 글";
const TABS: Tab[] = ["핫", "쓸 만함", "보통", "뺌", "지난 주제", "쓴 글"];
const recentOf = (t: WikiTopic) => t.heat ?? { recent: 0, pubs: 0, latest: "" };
/** 핫 탭 이름 — 불꽃 + 주황·빨강 그라데이션 HOT(2026-11-20 — 글자 '핫'만으로는 밋밋했다) */
function HotLabel({ small = false }: { small?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1">
      <IconFlameFilled className={cn("text-orange-500 drop-shadow-[0_0_6px_rgba(249,115,22,.7)]", small ? "size-3.5" : "size-4")} />
      <span className="bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500 bg-clip-text font-medium tracking-wider text-transparent">HOT</span>
    </span>
  );
}

/** '최근 한 달(10.20 이후)' — 기준일은 서버가 오늘부터 센다 */
const recentLabel = (since?: string) => (since ? `최근 한 달(${since.slice(5).replace("-", ".")} 이후)` : "최근 한 달");
/** 탭 아래에 보이는 그 탭의 기준 */
function tabNote(tab: Tab, recent: string, hotMin: number) {
  switch (tab) {
    case "핫":
      return `쓸 만함 판정 중 ${recent} 발행처 ${hotMin}곳 이상이 다룬 주제 · 발행처 많은 순`;
    case "지난 주제":
      return `${recent} 사례가 없는 주제 · 새 사례가 붙으면 판정 탭으로 돌아갑니다`;
    case "쓴 글":
      return "이 주제로 쓰는 중이거나 이미 쓴 주제";
    default:
      return `${tab} 판정 중 ${recent} 사례가 있는 주제 · 발행처 많은 순`;
  }
}

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
  t.status !== "쓸 수 있음"
    ? "쓴 글"
    : recentOf(t).recent === 0
      ? "지난 주제"
      : (["쓸 만함", "보통", "뺌"] as string[]).includes(t.verdict ?? "")
        ? (t.verdict as Tab)
        : "보통";

export default function Topics({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const [pending, setPending] = useState("");
  const [tab, setTab] = useState<Tab>("핫");
  const wiki = state.wiki;
  const ingesting = runningJob(state.jobs, "wiki", "넣기");
  const filtering = runningJob(state.jobs, "wiki-lint", "다시 거르기");
  // 주제 묶기(2026-10-21) — 자동 카드로 메시지 단위 주제를 만든다. 버튼에 아직 묶지 않은 카드 수
  const bundling = runningJob(state.jobs, "wiki", "주제 묶기");
  const unbundled = wiki?.unbundled ?? 0;
  const since = wiki?.bundleSince ? `발행일 ${wiki.bundleSince} 이후` : "최근 1개월";
  const judging = state.jobs.filter((j) => j.kind === "wiki-verdict" && j.status === "running");
  const backlog = newSources(state);

  const hotMin = wiki?.hotMin ?? 2;
  const byTab = useMemo(() => {
    const m: Record<Tab, WikiTopic[]> = { 핫: [], "쓸 만함": [], 보통: [], 뺌: [], "지난 주제": [], "쓴 글": [] };
    for (const t of wiki?.topics ?? []) {
      const k = tabOf(t);
      m[k].push(t);
      if (k === "쓸 만함" && recentOf(t).pubs >= hotMin) m.핫.push(t);
    }
    // 판정 탭·핫: 최근 1개월 발행처 수 → 최근 사례 수 → 최근 발행일(2026-11-20 — 예전엔 전체 기간 사례 수라 오래 쌓인 주제가 위에 남았다).
    // 지난 주제·쓴 글: 가장 최근 사례의 발행일 → 사례 수
    const hot = (a: WikiTopic, b: WikiTopic) => {
      const x = recentOf(a), y = recentOf(b);
      return y.pubs - x.pubs || y.recent - x.recent || y.latest.localeCompare(x.latest);
    };
    const past = (a: WikiTopic, b: WikiTopic) => latest(b).localeCompare(latest(a)) || b.sources.length - a.sources.length;
    for (const k of TABS) m[k].sort(k === "지난 주제" || k === "쓴 글" ? past : hot);
    return m;
  }, [wiki, hotMin]);
  const recentView = tab !== "지난 주제" && tab !== "쓴 글"; // 카드의 숫자를 최근 1개월 기준으로 보여 줄 탭

  // 누르면 서버가 그 자리에서 글 설정을 만들고 id를 돌려준다 → 바로 그 글의 제목 화면으로(제목 후보가 이미 떠 있다)
  const pick = async (t: WikiTopic, again = false) => {
    const id = articleOf(t, state);
    if (id && !again) return go(`#/a/${id}`);
    setPending(t.page);
    try {
      const r = await act<{ article: string }>("wiki-pick", { page: t.page });
      go(`#/a/${r.article}`); // 원문 확인부터(2026-10-22) — 확인이 끝나면 고른 원문 화면 → 제목
    } finally {
      setPending("");
    }
  };

  const judge = (t: WikiTopic, v: string) => v !== t.verdict && act("wiki-verdict", { page: t.page, verdict: v }).then(refresh);

  const items = byTab[tab].map((t) => {
    const id = articleOf(t, state);
    const picking = pending === t.page;
    const fresh = t.sources.filter((s) => s.new).length;
    // 전 직원은 모든 계층을 포함 — 들어 있으면 '전 직원'만. 특정 계층만이면 임원급·팀장급·시니어급·주니어급 순서로(2026-10-24, 예전 사수급·신입사원은 새 이름으로)
    const ALIAS: Record<string, string> = { 사수급: "시니어급", 신입사원: "주니어급" };
    const named = (t.audience || "").split("·").map((x) => ALIAS[x.trim()] ?? x.trim()).filter(Boolean);
    const levels = ["임원급", "팀장급", "시니어급", "주니어급"].filter((x) => named.includes(x));
    const audiences = named.includes("전 직원") || levels.length === 4 ? ["전 직원"] : levels; // 네 계층 모두면 전 직원
    const busy = judging.some((j) => j.target === t.page);
    // 메시지 단위 주제(2026-10-21): 사례마다 원문 카드를 짝지어 둔다(원문 서랍·있었던 일 전문)
    const cases = (t.cases ?? []).map((c) => ({ c, s: t.sources.find((x) => x.path === `originals/${c.key}.md`) }));
    return {
      key: t.page,
      title: t.title,
      dim: tab === "뺌",
      head: (
        <div
          className="relative flex min-h-[4.5rem] items-end justify-between gap-3 overflow-hidden px-6 pt-4 pb-4" // 위아래 같은 여백(고정 높이 h-24는 칩 위가 비었다)
          style={{
            background: `radial-gradient(120% 140% at 0% 0%, hsl(${hue(t.title)} 70% 45% / .45), transparent 60%), radial-gradient(120% 140% at 100% 100%, hsl(${(hue(t.title) + 70) % 360} 70% 45% / .3), transparent 55%)`,
          }}
        >
          {/* 대상 독자는 칩 각각, 여럿이면 2열 격자(2×2). 발행처는 지구본 아이콘 대신 사례 수와 다를 때만 '발행처 N곳'(올리면 이름) — 2026-10-22 */}
          <span className={cn("min-w-0 gap-1.5", audiences.length > 1 ? "grid grid-cols-2" : "flex")}>
            {audiences.map((x) => (
              <Chip key={x} className="justify-center whitespace-nowrap bg-page/70 px-2.5 text-ink backdrop-blur">{x}</Chip>
            ))}
          </span>
          <span className="flex shrink-0 items-center gap-1.5 whitespace-nowrap">
            {/* 발행처 · 사례 · 최근 발행 — 3칸, 칸마다 이름(작게) 위 값(굵게) (2026-10-22). 올리면 발행처 이름과 전체 날짜 */}
            <span
              title={`발행처: ${[...new Set(t.sources.map((s) => s.site || site(s.path)))].join(", ")}${latest(t) ? ` · 가장 최근 사례 ${latest(t)}` : ""}`}
              className="flex divide-x divide-line overflow-hidden rounded-xl border border-line bg-page/70 backdrop-blur"
            >
              {(recentView
                ? [
                    ["한 달 발행처", `${recentOf(t).pubs}곳`],
                    ["사례", recentOf(t).recent === t.sources.length ? `${t.sources.length}편` : `${recentOf(t).recent}/${t.sources.length}편`],
                    ["최근 발행", latest(t) ? latest(t).slice(5).replace("-", ".") : "—"],
                  ]
                : [
                    ["발행처", `${pubs(t)}곳`],
                    ["사례", `${t.sources.length}편`],
                    ["최근 발행", latest(t) ? latest(t).slice(5).replace("-", ".") : "—"],
                  ]
              ).map(([k, v]) => {
                // 사례 1편 — 판정은 그대로 두고 표시만(2026-11-02 사용자 결정). 글을 쓸 때 받침 원문을 넣도록
                const thin = k === "사례" && t.sources.length === 1;
                return (
                  <span
                    key={k}
                    title={thin ? "사례가 1편 — 글을 쓸 때 추천 원문에서 받침 원문을 넣으세요" : undefined}
                    className={cn("flex min-w-[3.25rem] flex-col items-center gap-0.5 px-2.5 py-1 leading-tight", thin && "bg-amber-500/20")}
                  >
                    <span className={cn("text-[10px]", thin ? "text-amber-700 dark:text-amber-200" : "text-ink-3")}>{thin ? "사례 보강" : k}</span>
                    <span className={cn("text-[13px] font-semibold tabular-nums", thin ? "text-amber-800 dark:text-amber-100" : "text-ink")}>{v}</span>
                  </span>
                );
              })}
            </span>
            {fresh > 0 && <Chip className="border-violet-400/50 bg-violet-500/20 text-violet-800 dark:text-violet-100">new {fresh}</Chip>}
            {t.status !== "쓸 수 있음" && <Chip className="bg-page/70 text-ink">{t.status}</Chip>}
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
          {/* 제목 후보는 주제 카드에 두지 않는다(2026-10-23) — 주제를 고른 뒤 글의 제목 단계에서 짓는다 */}
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
        <div className="mx-auto max-w-6xl px-12 py-3">
          <PillTabs
            id="verdicttab"
            tabs={TABS.map((v) => ({
              value: v,
              title: (
                <span className="flex items-center gap-2">
                  {v === "핫" ? <HotLabel /> : v}
                  <span className="tabular-nums text-ink-3">{byTab[v].length}</span>
                </span>
              ),
            }))}
            value={tab}
            onChange={(v) => setTab(v as Tab)}
          />
          {/* 고른 탭의 기준 — 탭 바로 아래, 탭 이름을 앞에 붙여 어느 탭 설명인지 보이게(2026-11-20 — 탭 줄 오른쪽 끝에 두니 연결이 안 보였다) */}
          <p className="mt-2 truncate px-1 text-[13px] text-ink-3">
            {tab === "핫" ? <HotLabel small /> : <span className="font-semibold text-ink-2">{tab}</span>}
            <span className="mx-2 text-ink-3/60">·</span>
            {tabNote(tab, recentLabel(wiki?.bundleSince), hotMin)}
          </p>
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
            status={ingesting ? `카드 → 묶기 → 거르기 → 제목 후보 · 남은 ${backlog}편` : "판정 기준으로 다시 판정하는 중 · 사람이 정한 판정은 그대로"}
          />
        )}
        <ExpandableCards items={items} />
      </div>
      <SourceDrawer path={open} onClose={() => setOpen(null)} />
    </div>
  );
}
