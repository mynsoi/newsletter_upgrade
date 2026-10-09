import { useCallback, useEffect, useRef, useState } from "react";
import { IconBooks, IconBulb, IconFileText, IconTerminal2 } from "@tabler/icons-react";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import { LiveLog } from "@/components/studio/live-log";
import { motion } from "motion/react";
import { Sidebar, SidebarBody, SidebarLink, useSidebar } from "@/components/ui/sidebar";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import Library from "@/views/Library";
import Topics, { newSources } from "@/views/Topics";
import { ThemeToggle } from "@/components/application/theme/theme-toggle";
import Articles from "@/views/Articles";
import Article from "@/views/Article";
import { articleTitle, getJobs, getState, img, JOB_NAMES, openLog, stage, subscribeAct, type Job, type State } from "@/lib/api";
import { hue } from "@/lib/text";
import { cn } from "@/lib/utils";

function useHash() {
  const [h, setH] = useState(window.location.hash || "#/articles");
  useEffect(() => {
    const f = () => setH(window.location.hash || "#/articles");
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  const go = useCallback((to: string) => {
    window.location.hash = to;
  }, []);
  return [h, go] as const;
}

export default function App() {
  const [state, setState] = useState<State | null>(null);
  const [hash, go] = useHash();
  const sig = useRef("");
  const seen = useRef<Record<string, string>>({});
  const [toasts, setToasts] = useState<{ id: string; title: string; text: string }[]>([]);
  // 작업이 실패하면 화면에 알린다 — 조용히 실패해 "멈춘 것처럼" 보이던 문제(2026-10-10)
  const watch = useCallback(async (jobs: Job[]) => {
    const first = Object.keys(seen.current).length === 0;
    for (const j of jobs) {
      const before = seen.current[j.id];
      seen.current[j.id] = j.status;
      if (first || j.status !== "failed" || before === "failed") continue;
      const r = await fetch("/api/log?id=" + encodeURIComponent(j.id)).then((x) => x.json()).catch(() => ({ text: "" }));
      const last = (r.text as string).trim().split("\n").filter(Boolean).pop() ?? "";
      setToasts((t) => [...t, { id: j.id, title: `${JOB_NAMES[j.kind] ?? j.kind} 실패`, text: last }]);
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== j.id)), 15000);
    }
  }, []);
  const refresh = useCallback(async () => {
    const s = await getState();
    setState(s);
    watch(s.jobs);
    sig.current = s.jobs.map((j) => j.id + j.status).join();
  }, []);

  // 버튼 → 바로 진행 막대, 시작된 작업은 다음 새로고침을 기다리지 않고 화면에, 실패는 알림으로
  const [inflight, setInflight] = useState(0);
  const [logJob, setLogJob] = useState<string | null>(null);
  useEffect(() => {
    const f = (e: Event) => setLogJob((e as CustomEvent<string>).detail || "");
    window.addEventListener("studio:open-log", f);
    return () => window.removeEventListener("studio:open-log", f);
  }, []);
  useEffect(
    () =>
      subscribeAct((e) => {
        if (e.phase === "start") return setInflight((n) => n + 1);
        setInflight((n) => Math.max(0, n - 1));
        if (e.job) {
          const j = e.job;
          setState((s) => (s ? { ...s, jobs: [j, ...s.jobs.filter((x) => x.id !== j.id)] } : s));
        }
        if (e.error) {
          const id = "err-" + Date.now();
          setToasts((t) => [...t, { id, title: `${JOB_NAMES[e.name] ?? e.name} 안 됨`, text: e.error! }]);
          setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 10000);
        }
        refresh();
      }),
    [refresh]
  );

  useEffect(() => {
    refresh();
    let n = 0;
    const t = setInterval(async () => {
      n++;
      const jobs = await getJobs().catch(() => null);
      if (!jobs) return;
      watch(jobs);
      const s = jobs.map((j) => j.id + j.status).join();
      const running = jobs.some((j) => j.status === "running");
      if (s !== sig.current || (running && n % 4 === 0)) refresh();
    }, 2500);
    return () => clearInterval(t);
  }, [refresh, watch]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [hash.split("/").slice(0, 3).join("/")]);

  const parts = hash.replace(/^#\/?/, "").split("/");
  const view = parts[0] || "articles";

  return (
    <div className="min-h-screen w-full bg-page text-ink">
      {inflight > 0 && (
        <div className="fixed inset-x-0 top-0 z-[100] h-[3px] overflow-hidden">
          <motion.div
            className="h-full w-1/3 bg-gradient-to-r from-transparent via-violet-500 to-transparent"
            initial={{ x: "-100%" }}
            animate={{ x: "300%" }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      )}
      <Nav state={state} view={view} current={parts[1]} go={go} />
      <LogDrawer state={state} id={logJob} onClose={() => setLogJob(null)} onPick={setLogJob} />
      <main id="main" className="relative min-h-screen pl-[60px]">
        {state &&
          (view === "library" ? (
            <Library state={state} refresh={refresh} go={go} />
          ) : view === "topics" ? (
            <Topics state={state} refresh={refresh} go={go} />
          ) : view === "a" && parts[1] ? (
            <Article key={parts[1]} state={state} id={decodeURIComponent(parts[1])} tab={parts[2]} refresh={refresh} go={go} />
          ) : (
            <Articles state={state} go={go} />
          ))}
      </main>
      <div className="fixed top-5 right-5 z-[90] flex w-[380px] flex-col gap-2">
        {toasts.map((t) => (
          <motion.button
            key={t.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}
            className="rounded-2xl border border-rose-400/40 bg-panel-solid p-4 text-left shadow-2xl"
          >
            <div className="text-sm font-semibold text-rose-600 dark:text-rose-300">{t.title}</div>
            <div className="mt-1 line-clamp-3 break-all font-mono text-xs text-ink-2">{t.text}</div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

function Nav({ state, view, current, go }: { state: State | null; view: string; current?: string; go: (h: string) => void }) {
  const [open, setOpen] = useState(false);
  const running = state?.jobs.filter((j) => j.status === "running") ?? [];
  const links = [
    { label: "서재", href: "#/library", key: "library", icon: <IconBooks className="size-5 shrink-0 text-ink-2" /> },
    {
      label: "주제",
      href: "#/topics",
      key: "topics",
      icon: (
        <span className="relative shrink-0">
          <IconBulb className="size-5 text-ink-2" />
          {state && newSources(state) > 0 && <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-violet-500" />}
        </span>
      ),
    },
    { label: "글", href: "#/articles", key: "articles", icon: <IconFileText className="size-5 shrink-0 text-ink-2" /> },
  ];
  const arts = [...(state?.articles ?? [])].sort((a, b) => b.at - a.at);
  return (
    <div className="fixed inset-y-0 left-0 z-50 w-[60px]">
      <Sidebar open={open} setOpen={setOpen}>
        <SidebarBody className="absolute inset-y-0 left-0 justify-between gap-6 border-r border-line bg-page/95 dark:bg-page/95 px-3 backdrop-blur-xl">
          <div className="flex min-h-0 flex-1 flex-col">
            <Logo />
            <div className="mt-8 flex flex-col gap-1">
              {links.map((l) => (
                <SidebarLink
                  key={l.key}
                  link={l}
                  active={view === l.key || (l.key === "articles" && view === "a")}
                  className={cn("rounded-lg px-2", (view === l.key || (l.key === "articles" && view === "a")) && "bg-soft")}
                />
              ))}
            </div>
            <div className="mt-6 min-h-0 flex-1 space-y-0.5 overflow-y-auto overflow-x-hidden pr-1">
              {arts.map((a) => (
                <a
                  key={a.id}
                  href={`#/a/${a.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    go(`#/a/${a.id}`);
                  }}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-2 py-1.5 transition hover:bg-soft",
                    view === "a" && current === a.id && "bg-ink/[0.07]"
                  )}
                >
                  {a.hero ? (
                    <img src={img(a.hero, 120)} className="size-5 shrink-0 rounded object-cover" />
                  ) : (
                    <span
                      className="size-5 shrink-0 rounded"
                      style={{ background: `linear-gradient(135deg, hsl(${hue(a.id)} 60% 45%), hsl(${(hue(a.id) + 60) % 360} 60% 35%))` }}
                    />
                  )}
                  <motion.span animate={{ opacity: open ? 1 : 0 }} className="flex min-w-0 flex-1 items-center gap-2 whitespace-nowrap">
                    <span className="truncate text-sm text-ink-2">{articleTitle(a)}</span>
                    <span className="ml-auto shrink-0 text-[11px] tabular-nums text-ink-3">{stage(a)}</span>
                  </motion.span>
                </a>
              ))}
            </div>
          </div>
          <div>
            <Jobs jobs={running} names={Object.fromEntries((state?.articles ?? []).map((a) => [a.id, articleTitle(a)]))} />
            <button onClick={() => openLog(running[0]?.id ?? "")} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-1.5 text-ink-2 transition hover:bg-soft hover:text-ink">
              <IconTerminal2 className="size-5 shrink-0" />
            </button>
            <Theme />
          </div>
        </SidebarBody>
      </Sidebar>
    </div>
  );
}

function Logo() {
  const { open } = useSidebar();
  return (
    <div className="flex items-center gap-3 px-1.5 py-1">
      <div className="size-6 shrink-0 rounded-lg bg-gradient-to-br from-violet-400 via-fuchsia-400 to-cyan-300 shadow-lg shadow-violet-500/30" />
      <motion.span animate={{ opacity: open ? 1 : 0 }} className="whitespace-nowrap text-sm font-semibold text-ink">
        칼럼 작업실
      </motion.span>
    </div>
  );
}

function Jobs({ jobs, names }: { jobs: Job[]; names: Record<string, string> }) {
  const { open } = useSidebar();
  if (!jobs.length) return null;
  return (
    <div className="space-y-1 pb-2">
      {jobs.map((j) => (
        <button key={j.id} onClick={() => openLog(j.id)} className="flex w-full items-center gap-3 rounded-lg px-2.5 py-1.5 text-left transition hover:bg-soft">
          <span className="relative flex size-2.5 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-violet-400" />
          </span>
          {open && (
            <span className="flex min-w-0 items-center gap-2 whitespace-nowrap text-sm">
              <AITextLoading texts={[JOB_NAMES[j.kind] ?? j.kind]} className="text-sm font-medium" wrapperClassName="p-0 justify-start" />
              <span className="truncate text-ink-3">{names[j.target] ?? j.target}</span>
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function Theme() {
  const { open } = useSidebar();
  return <div className="pb-2">{open ? <ThemeToggle appearance="sidebar-segmented" /> : <ThemeToggle collapsed />}</div>;
}

/** 전체 로그 창 — 왼쪽은 최근 작업(돌고 있는 것 먼저), 오른쪽은 고른 작업의 실시간 로그 */
function LogDrawer({ state, id, onClose, onPick }: { state: State | null; id: string | null; onClose: () => void; onPick: (id: string) => void }) {
  const jobs = [...(state?.jobs ?? [])].sort((a, b) => (a.status === "running" ? 0 : 1) - (b.status === "running" ? 0 : 1) || b.started - a.started).slice(0, 20);
  const names = Object.fromEntries((state?.articles ?? []).map((a) => [a.id, articleTitle(a)]));
  const cur = id || jobs[0]?.id || "";
  return (
    <Drawer direction="right" open={id !== null} onOpenChange={(o) => !o && onClose()}>
      <DrawerContent className="z-[85] bg-page border-line data-[vaul-drawer-direction=right]:w-[960px] data-[vaul-drawer-direction=right]:sm:max-w-[960px]">
        <div className="flex h-full">
          <div className="w-72 shrink-0 overflow-y-auto border-r border-line p-3">
            <DrawerTitle className="px-2 pb-3 pt-2 text-base font-semibold text-ink">작업 로그</DrawerTitle>
            {jobs.map((j) => (
              <button
                key={j.id}
                onClick={() => onPick(j.id)}
                className={cn("mb-1 flex w-full flex-col rounded-xl px-3 py-2 text-left transition hover:bg-soft", cur === j.id && "bg-soft")}
              >
                <span className="flex items-center gap-2 text-sm text-ink">
                  <span className={cn("size-2 rounded-full", j.status === "running" ? "animate-pulse bg-emerald-500" : j.status === "failed" ? "bg-rose-500" : "bg-ink-3")} />
                  {JOB_NAMES[j.kind] ?? j.kind}
                </span>
                <span className="truncate pl-4 text-xs text-ink-3">{names[j.target] ?? j.target}</span>
              </button>
            ))}
          </div>
          <div className="min-w-0 flex-1 p-5">{cur && <LiveLog key={cur} jobId={cur} />}</div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
