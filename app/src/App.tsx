import { useCallback, useEffect, useRef, useState } from "react";
import { IconBooks, IconBulb, IconFileText } from "@tabler/icons-react";
import { motion } from "motion/react";
import { Sidebar, SidebarBody, SidebarLink, useSidebar } from "@/components/ui/sidebar";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import Library from "@/views/Library";
import Topics, { newSources } from "@/views/Topics";
import { ThemeToggle } from "@/components/application/theme/theme-toggle";
import Articles from "@/views/Articles";
import Article from "@/views/Article";
import { articleTitle, getJobs, getState, img, JOB_NAMES, stage, type Job, type State } from "@/lib/api";
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
  const refresh = useCallback(async () => {
    const s = await getState();
    setState(s);
    sig.current = s.jobs.map((j) => j.id + j.status).join();
  }, []);

  useEffect(() => {
    refresh();
    let n = 0;
    const t = setInterval(async () => {
      n++;
      const jobs = await getJobs().catch(() => null);
      if (!jobs) return;
      const s = jobs.map((j) => j.id + j.status).join();
      const running = jobs.some((j) => j.status === "running");
      if (s !== sig.current || (running && n % 4 === 0)) refresh();
    }, 2500);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [hash.split("/").slice(0, 3).join("/")]);

  const parts = hash.replace(/^#\/?/, "").split("/");
  const view = parts[0] || "articles";

  return (
    <div className="min-h-screen w-full bg-page text-ink">
      <Nav state={state} view={view} current={parts[1]} go={go} />
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
        <div key={j.id} className="flex items-center gap-3 rounded-lg px-2.5 py-1.5">
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
        </div>
      ))}
    </div>
  );
}

function Theme() {
  const { open } = useSidebar();
  return <div className="pb-2">{open ? <ThemeToggle appearance="sidebar-segmented" /> : <ThemeToggle collapsed />}</div>;
}
