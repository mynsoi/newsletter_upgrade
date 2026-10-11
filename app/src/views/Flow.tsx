import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { IconArrowRight, IconCheck, IconFileText, IconPhoto, IconSparkles, IconTrash } from "@tabler/icons-react";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import ParticleButton from "@/components/kokonutui/particle-button";
import { PillTabs } from "@/components/ui/tabs";
import { ByChip, Chip, ClaudeMark, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { Director, Prose } from "@/views/Article";
import { StageChip } from "@/views/Articles";
import { PicksCard, useAttach } from "@/views/MineChat";
import { act, articleTitle, img, openLog, type Article as A, type Job, type MinePick, type MineRun, type State, type Step } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * 글 화면 = 대화 (멘토 2026-10-11: "그 글에 있는 채팅이 계속해서 글 작성까지 흐름을 끌고 간다 … 실제로 그렇게 되어야 한다")
 * 왼쪽: 요청 → 고른 원문 → 제목 후보 → 쓰기 → 과정 1·2·3 → 피드백 → 과정 4… → 그림 → 확정이 한 줄로 쌓인다.
 * 오른쪽: 지금 글(고른 원문 → 정한 제목 → 최신 과정 본문).
 * 입력창 하나 — 단계에 따라 보낸 말이 가는 곳이 정해진다(원문: 대화 전체로 다시 고르기 · 제목: astra 제목 회차 · 과정 3 뒤: 피드백).
 * 다음 단계는 카드의 버튼으로만 넘어간다(이 원문으로 · 제목 누르기 · 쓰기 · 그림 · 확정).
 */

const KINDS = ["mine", "titles", "write", "revise", "shorten", "images", "inline", "wiki-pick"];
const jobOf = (jobs: Job[], id: string) => jobs.find((j) => j.status === "running" && j.target === id && KINDS.includes(j.kind));
const MINE_TEXT: Record<string, string> = { 문서: "문서 읽는 중", 후보: "원문 카드 보는 중", 고르기: "원문 읽고 고르는 중", 제목: "제목 후보 짓는 중" };

function jobText(j: Job, a?: A, run?: MineRun): string[] {
  if (j.kind === "mine") return [MINE_TEXT[run?.stage ?? ""] ?? "원문 고르는 중"];
  if (j.kind === "titles") return ["astra", "제목 짓는 중"];
  if (j.kind === "write") {
    const i = j.stage?.index ?? 0;
    if (i >= 3) return [j.stage?.fit ? "1,500자로 줄이는 중" : "절반으로 줄이는 중"];
    return [["과정 1 · Claude 초안", "과정 2 · astra 재작성", "과정 3 · 기준 반영"][i]];
  }
  if (j.kind === "revise") return [`과정 ${(a?.steps.length ?? 0) + 1} · 피드백 반영`];
  if (j.kind === "shorten") return ["절반으로 줄이는 중"];
  if (j.kind === "images") return ["머리 그림 그리는 중"];
  if (j.kind === "inline") return ["본문 그림 그리는 중"];
  return ["…"];
}

type Route = { mode: "pick" | "titles" | "feedback" | null; label: string };
function route(a: A | undefined, run: MineRun | undefined, job: Job | undefined): Route {
  if (job) return { mode: null, label: jobText(job, a, run)[0] };
  if (!a || a.kind === "process") return { mode: null, label: "" };
  if (a.fromMine && run && !a.sourcesOk && !a.title && !a.steps.length) return { mode: "pick", label: "원문" };
  if (!a.steps.length) return { mode: "titles", label: "제목" };
  if (a.steps.length >= 3) return { mode: "feedback", label: "피드백" };
  return { mode: null, label: "" };
}

export default function Flow({ state, id, refresh, go }: { state: State; id: string; refresh: () => void; go: (h: string) => void }) {
  const a = state.articles.find((x) => x.id === id);
  const run = state.mine?.find((r) => r.id === id);
  const job = jobOf(state.jobs, id);
  const [sel, setSel] = useState<number | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [director, setDirector] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const sig = [run?.turns.length, run?.status, a?.titles.length, a?.title, a?.steps.length, a?.images.length, a?.inline.length, !!a?.confirmed, job?.id, a?.sourcesOk].join();
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" });
  }, [sig]);
  if (!a && !run) return null;
  const title = a ? articleTitle(a) : run!.message;

  return (
    <div className="grid h-screen grid-cols-[minmax(0,1fr)_460px]">
      <section className="relative flex h-screen min-w-0 flex-col border-r border-line">
        <header className="flex items-center gap-4 border-b border-line bg-page/80 px-10 py-4 backdrop-blur-xl">
          {a ? <StageChip a={a} /> : <Chip className="text-ink">원문</Chip>}
          <h1 className="line-clamp-1 min-w-0 flex-1 text-lg font-semibold text-ink">{title}</h1>
          {a && (
            <span className="flex shrink-0 items-center gap-1">
              {[
                ["title", "제목"],
                ["process", "과정"],
                ["image", "그림"],
                ["confirm", "확정"],
              ].map(([v, t]) => (
                <button key={v} onClick={() => go(`#/a/${a.id}/${v}`)} className="rounded-full px-3 py-1.5 text-sm text-ink-3 transition hover:bg-soft hover:text-ink">
                  {t}
                </button>
              ))}
            </span>
          )}
          {a && a.kind === "brief" && <Delete a={a} go={go} refresh={refresh} />}
        </header>

        <div ref={box} className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[820px] space-y-7 px-10 pt-10 pb-56">
            <Timeline a={a} run={run} job={job} state={state} refresh={refresh} sel={sel} setSel={setSel} onSource={setSrc} />
          </div>
        </div>

        <ChatInput a={a} run={run} job={job} refresh={refresh} onDirector={() => setDirector(true)} />
      </section>

      <aside className="h-screen overflow-y-auto bg-soft/30">
        <Now a={a} run={run} sel={sel} onSource={setSrc} />
      </aside>

      {a && <Director a={a} state={state} open={director} onClose={() => setDirector(false)} refresh={refresh} />}
      <SourceDrawer path={src} onClose={() => setSrc(null)} />
    </div>
  );
}

/* ---------- 대화 ---------- */

function Me({ children, docs }: { children: React.ReactNode; docs?: string[] }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl bg-violet-500/20 px-4 py-3 text-[15px] leading-relaxed whitespace-pre-line text-violet-950 dark:text-violet-50">
        {children}
        {docs && docs.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {docs.map((d) => (
              <Chip key={d} className="border-violet-400/40 bg-page/50 text-ink">
                <IconFileText className="size-3.5" />
                {d}
              </Chip>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function Ai({ children, label }: { children: React.ReactNode; label?: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
      {label && <div className="flex items-center gap-2 pl-1 text-xs text-ink-3">{label}</div>}
      {children}
    </motion.div>
  );
}

function Timeline({
  a,
  run,
  job,
  state,
  refresh,
  sel,
  setSel,
  onSource,
}: {
  a?: A;
  run?: MineRun;
  job?: Job;
  state: State;
  refresh: () => void;
  sel: number | null;
  setSel: (n: number) => void;
  onSource: (p: string) => void;
}) {
  const out: React.ReactNode[] = [];
  const started = !!a && a.steps.length > 0;

  // 1. 시작 — 내 주제로 쓰기(대화 차례) 또는 주제 지도·설정에서 온 글
  if (run) {
    const lastAi = run.turns.map((t) => t.role).lastIndexOf("ai");
    run.turns.forEach((t, i) => {
      if (t.role === "mentor") out.push(<Me key={`m${i}`} docs={t.docs}>{t.text}</Me>);
      else if (i === lastAi && run.status !== "running" && run.picked.length)
        out.push(
          <Ai key={`a${i}`} label={<>고른 원문 · 후보 {t.n_candidates}편 중</>}>
            <PicksCard
              run={run}
              canSwap={!started}
              onSource={onSource}
              refresh={refresh}
              footer={
                a && !a.sourcesOk && !a.title && !started ? (
                  <button
                    onClick={() => act("mine-ok", { article: a.id }).then(refresh)}
                    className="flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-page transition hover:bg-violet-500 hover:text-white"
                  >
                    이 원문으로
                    <IconArrowRight className="size-4" />
                  </button>
                ) : undefined
              }
            />
          </Ai>
        );
      else out.push(<Ai key={`a${i}`} label="그때 고른 원문"><PastPicks center={t.center} support={t.support} onSource={onSource} /></Ai>);
    });
    if ((run.status === "failed" || run.status === "lost") && !job)
      out.push(
        <button key="stop" onClick={() => openLog(run.job)} className="pl-1 text-left text-sm text-rose-600 hover:underline dark:text-rose-300">
          멈춤 · 로그
        </button>
      );
  } else if (a) {
    out.push(
      <Ai key="origin" label={a.fromWiki ? "주제 지도에서 고른 주제" : "글 설정"}>
        <div className="rounded-2xl border border-line bg-panel-solid px-5 py-4">
          <p className="text-[15px] leading-relaxed text-ink">{a.thesis}</p>
          {a.why && <p className="mt-2 text-[13.5px] leading-relaxed text-ink-3">{a.why}</p>}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {a.sources.map(([p, d]) => (
              <button key={p} onClick={() => onSource(p)}>
                <Chip className="text-ink-2 hover:text-ink">
                  <SiteIcon site={p.split("/")[1] ?? ""} className="size-3.5" />
                  <span className="max-w-60 truncate">{d}</span>
                </Chip>
              </button>
            ))}
          </div>
        </div>
      </Ai>
    );
  }

  // 2. 제목 — 내 주제로 쓰기는 '이 원문으로'를 누른 뒤부터
  const sourcesDone = !a?.fromMine || !run || a.sourcesOk || !!a.title || started;
  if (a && a.kind === "brief" && sourcesDone) {
    a.titles.forEach((r, ri) => {
      if (r.message) out.push(<Me key={`tm${ri}`}>{r.message}</Me>);
      out.push(
        <Ai key={`t${ri}`} label={<>제목 후보 · astra{a.titles.length > 1 && ` · ${ri + 1}회차`}</>}>
          <TitlesCard a={a} items={r.items} live={!started} refresh={refresh} />
        </Ai>
      );
    });
    if (a.title)
      out.push(
        <Me key="title">
          <span className="flex items-center gap-2 font-semibold">
            <IconCheck className="size-4 shrink-0" />
            {a.title}
          </span>
        </Me>
      );
    if (a.title && !started && job?.kind !== "write") out.push(<Ai key="write"><WriteCard a={a} refresh={refresh} /></Ai>);
  }
  if (a && a.kind === "process" && a.title) out.push(<Me key="title">{a.title}</Me>);

  // 3. 과정 — 과정 4부터 앞에 멘토 피드백(받은 그대로)
  a?.steps.forEach((s, i) => {
    if (s.n >= 4 && s.feedback && !s.mode && s.by !== "멘토") out.push(<Me key={`f${s.n}`}>{s.feedback}</Me>);
    out.push(
      <Ai key={`s${s.n}`} label={<><span className="tabular-nums">과정 {s.n}</span><ByChip by={s.by} />{s.mode && <Chip>{s.mode}</Chip>}</>}>
        <StepCard s={s} active={(sel ?? a.steps.length) === s.n} onOpen={() => setSel(s.n)} last={i === a.steps.length - 1} />
      </Ai>
    );
  });

  // 4. 그림 · 확정 — 과정 3 뒤
  if (a && a.kind === "brief" && a.steps.length >= 3) {
    out.push(<Ai key="img" label="그림"><ImagesCard a={a} state={state} refresh={refresh} /></Ai>);
    out.push(<Ai key="confirm" label="확정"><ConfirmCard a={a} refresh={refresh} /></Ai>);
  }

  // 돌고 있는 작업 — 보낸 말이 있으면 먼저(제목·피드백)
  if (job) {
    if (job.message && job.kind !== "mine") out.push(<Me key="jm">{job.message}</Me>);
    const steps = job.kind === "write" ? 3 : job.kind === "mine" ? 3 : 0;
    const at = job.kind === "write" ? job.stage?.index ?? 0 : ["후보", "고르기", "제목"].indexOf(run?.stage ?? "");
    out.push(
      <div key="job" className="flex items-center gap-4 pl-1">
        {steps > 0 && (
          <div className="flex items-center gap-1.5">
            {Array.from({ length: steps }).map((_, i) => (
              <span key={i} className={cn("h-1.5 w-8 rounded-full", i < at ? "bg-violet-400" : i === at ? "animate-pulse bg-violet-400/70" : "bg-ink/10")} />
            ))}
          </div>
        )}
        <AITextLoading texts={jobText(job, a, run)} className="text-sm font-medium" wrapperClassName="p-0 justify-start" />
        <button onClick={() => openLog(job.id)} className="text-xs text-ink-3 hover:text-ink">
          로그
        </button>
      </div>
    );
  }
  return <>{out}</>;
}

function PastPicks({ center, support, onSource }: { center: MinePick; support: MinePick[]; onSource: (p: string) => void }) {
  return (
    <div className="rounded-2xl border border-line px-5 py-3 opacity-70 transition hover:opacity-100">
      {[center, ...support].map((p, i) => (
        <div key={p.source} className="flex gap-3 py-1.5 text-[14px] leading-relaxed">
          <Chip className={cn("h-fit shrink-0 self-start whitespace-nowrap", i === 0 && "border-violet-400/50 bg-violet-500/15 text-violet-800 dark:text-violet-100")}>{i === 0 ? "중심" : "받침"}</Chip>
          <span className="min-w-0 text-ink-2">
            <button onClick={() => onSource(p.path ?? "")} className="mr-2 text-xs text-ink-3 hover:text-ink">
              {p.source} · {p.who}
            </button>
            {p.role}
          </span>
        </div>
      ))}
    </div>
  );
}

function TitlesCard({ a, items, live, refresh }: { a: A; items: string[]; live: boolean; refresh: () => void }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map((x, i) => {
        const on = a.title === x;
        return (
          <button
            key={i}
            disabled={!live}
            onClick={() => act("title", { article: a.id, title: x }).then(refresh)}
            className={cn(
              "flex gap-3 rounded-2xl border px-4 py-3.5 text-left text-[15px] leading-snug transition [word-break:keep-all]",
              on ? "border-violet-400/70 bg-violet-500/15 text-ink" : "border-line bg-panel-solid text-ink hover:border-violet-400/40",
              !live && !on && "opacity-50"
            )}
          >
            <span className="w-4 shrink-0 text-right text-sm tabular-nums text-ink-3">{i + 1}</span>
            <span className="font-medium">{x}</span>
          </button>
        );
      })}
    </div>
  );
}

function WriteCard({ a, refresh }: { a: A; refresh: () => void }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-panel-solid px-5 py-4">
      <span className="flex flex-wrap items-center gap-3">
        <PillTabs
          id="flow-target"
          tabs={["전 직원", "팀장급", "사수급", "신입사원"].map((v) => ({ value: v, title: v }))}
          value={a.target}
          onChange={(v) => act("target", { article: a.id, target: v }).then(refresh)}
        />
        <PillTabs
          id="flow-length"
          tabs={[
            { value: "full", title: "기본" },
            { value: "half", title: "절반" },
          ]}
          value={a.length}
          onChange={(v) => act("length", { article: a.id, mode: v }).then(refresh)}
        />
      </span>
      <ParticleButton
        className="h-11 shrink-0 rounded-full bg-ink px-7 text-base font-semibold text-page hover:bg-violet-500 hover:text-ink"
        onClick={() => act("write", { article: a.id }).then(refresh)}
      >
        쓰기
      </ParticleButton>
    </div>
  );
}

function StepCard({ s, active, onOpen, last }: { s: Step; active: boolean; onOpen: () => void; last: boolean }) {
  return (
    <button
      onClick={onOpen}
      className={cn(
        "block w-full rounded-2xl border px-5 py-4 text-left transition",
        active ? "border-violet-400/60 bg-panel-solid" : "border-line bg-panel-solid hover:border-violet-400/30",
        !last && !active && "opacity-75"
      )}
    >
      {s.title && <div className="mb-1.5 text-[15px] font-semibold text-ink">{s.title}</div>}
      <p className="line-clamp-3 text-[14px] leading-relaxed text-ink-2">{s.text}</p>
      <div className="mt-2 text-xs tabular-nums text-ink-3">{s.chars.toLocaleString()}자</div>
    </button>
  );
}

function ImagesCard({ a, state, refresh }: { a: A; state: State; refresh: () => void }) {
  const hero = a.images[a.images.length - 1];
  const inline = a.inline[a.inline.length - 1];
  const picked = new Set(a.inlinePicked.map((x) => x.src));
  const busyHero = state.jobs.some((j) => j.status === "running" && j.target === a.id && j.kind === "images");
  const busyInline = state.jobs.some((j) => j.status === "running" && j.target === a.id && j.kind === "inline");
  return (
    <div className="space-y-4 rounded-2xl border border-line bg-panel-solid px-5 py-4">
      <div className="flex gap-2">
        <button
          disabled={busyHero}
          onClick={() => act("images", { article: a.id }).then(refresh)}
          className="flex items-center gap-2 rounded-full border border-line px-4 py-2 text-sm text-ink transition hover:bg-soft disabled:opacity-50"
        >
          <IconPhoto className="size-4" />
          머리 그림{hero && " 다시"}
        </button>
        <button
          disabled={busyInline}
          onClick={() => act("images", { article: a.id, kind: "inline" }).then(refresh)}
          className="flex items-center gap-2 rounded-full border border-line px-4 py-2 text-sm text-ink transition hover:bg-soft disabled:opacity-50"
        >
          <IconSparkles className="size-4" />
          본문 그림{inline && " 다시"}
        </button>
      </div>
      {hero && (
        <div className="grid grid-cols-4 gap-2">
          {hero.items.filter((x) => x.src).map((x) => (
            <button key={x.src} onClick={() => act("hero", { article: a.id, src: x.src }).then(refresh)} className={cn("overflow-hidden rounded-xl ring-2 transition", a.hero === x.src ? "ring-violet-400" : "ring-transparent hover:ring-line")}>
              <img src={img(x.src, 360)} className="aspect-[3/2] w-full object-cover" />
            </button>
          ))}
        </div>
      )}
      {inline && (
        <div className="grid grid-cols-4 gap-2">
          {inline.items.filter((x) => x.src).map((x) => (
            <button key={x.src} onClick={() => act("inline", { article: a.id, src: x.src, on: !picked.has(x.src) }).then(refresh)} className={cn("overflow-hidden rounded-xl ring-2 transition", picked.has(x.src) ? "ring-violet-400" : "ring-transparent hover:ring-line")}>
              <img src={img(x.src, 360)} className="aspect-video w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ConfirmCard({ a, refresh }: { a: A; refresh: () => void }) {
  const n = a.steps.length;
  if (a.confirmed)
    return (
      <div className="flex items-center gap-3 rounded-2xl border border-emerald-400/40 bg-emerald-500/10 px-5 py-4 text-[15px] text-ink">
        <IconCheck className="size-5 text-emerald-500" />
        과정 {a.confirmed.step} 확정
        <span className="text-sm text-ink-3">{a.confirmed.file}</span>
      </div>
    );
  return (
    <button
      onClick={() => act("confirm", { article: a.id, step: n }).then(refresh)}
      className="flex w-full items-center justify-between rounded-2xl border border-line bg-panel-solid px-5 py-4 text-left text-[15px] text-ink transition hover:border-emerald-400/50"
    >
      과정 {n}으로 확정
      <IconArrowRight className="size-4" />
    </button>
  );
}

function Delete({ a, go, refresh }: { a: A; go: (h: string) => void; refresh: () => void }) {
  const [arm, setArm] = useState(false);
  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => setArm(false), 3000);
    return () => clearTimeout(t);
  }, [arm]);
  return (
    <button
      onClick={async () => {
        if (!arm) return setArm(true);
        await act("delete", { article: a.id });
        go("#/articles");
        refresh();
      }}
      title="삭제"
      className={cn(
        "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition",
        arm ? "border-rose-400/60 bg-rose-500/15 text-rose-700 dark:text-rose-200" : "border-transparent text-ink-3 hover:border-line hover:text-ink"
      )}
    >
      <IconTrash className="size-4" />
      {arm && "한 번 더"}
    </button>
  );
}

/* ---------- 입력 ---------- */

function ChatInput({ a, run, job, refresh, onDirector }: { a?: A; run?: MineRun; job?: Job; refresh: () => void; onDirector: () => void }) {
  const r = route(a, run, job);
  const [mode, setMode] = useState("auto");
  const at = useAttach();
  const modes = [
    { id: "auto", label: r.label || "—", icon: <IconSparkles className="size-3.5 text-violet-300" /> },
    ...(a ? [{ id: "director", label: "진행자", icon: <ClaudeMark className="size-3.5" /> }] : []),
  ];
  const off = mode === "auto" && !r.mode;
  const send = async (v: string) => {
    if (mode === "director" && a) {
      act("chat", { article: a.id, message: v }).then(refresh);
      return onDirector();
    }
    if (r.mode === "pick") await act("mine-more", { id: run!.id, message: v, files: await at.encode() });
    else if (r.mode === "titles") await act("titles", { article: a!.id, message: v });
    else if (r.mode === "feedback") await act("revise", { article: a!.id, feedback: v });
    at.clear();
    refresh();
  };
  return (
    <div {...(r.mode === "pick" ? at.drop : {})} className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center bg-gradient-to-t from-page via-page/90 to-transparent px-10 pt-16">
      <AI_Prompt
        className={cn("pointer-events-auto w-full max-w-[780px] pb-5", at.drag && "rounded-3xl ring-2 ring-violet-400/70")}
        modes={modes}
        mode={mode}
        onModeChange={setMode}
        disabled={off}
        placeholder={off ? (job ? `${r.label} …` : "") : mode === "director" ? "" : r.mode === "feedback" ? `과정 ${(a?.steps.length ?? 0) + 1}` : ""}
        onSubmit={send}
        tools={r.mode === "pick" && mode === "auto" ? at.tool : undefined}
        top={r.mode === "pick" && mode === "auto" ? at.chips : undefined}
      />
    </div>
  );
}

/* ---------- 지금 글 ---------- */

function Now({ a, run, sel, onSource }: { a?: A; run?: MineRun; sel: number | null; onSource: (p: string) => void }) {
  const s = a?.steps.find((x) => x.n === (sel ?? a.steps.length));
  return (
    <div className="space-y-6 px-8 py-8">
      {a?.hero && <img src={img(a.hero, 900)} className="aspect-[3/2] w-full rounded-2xl object-cover" />}
      {s ? (
        <div>
          <div className="mb-4 flex items-center gap-2 text-xs text-ink-3">
            <span className="tabular-nums">과정 {s.n}</span>
            <ByChip by={s.by} />
            <span className="tabular-nums">{s.chars.toLocaleString()}자</span>
          </div>
          <h2 className="mb-6 text-2xl font-bold leading-snug text-ink [word-break:keep-all]">{a!.title || s.title}</h2>
          <div className="text-[15px]">
            <Prose text={s.text} />
          </div>
        </div>
      ) : a?.title ? (
        <h2 className="text-2xl font-bold leading-snug text-ink [word-break:keep-all]">{a.title}</h2>
      ) : null}
      {!s && (
        <div className="space-y-3">
          {(run?.picked ?? []).map((p, i) => (
            <button key={p.source} onClick={() => onSource(p.path)} className="block w-full rounded-2xl border border-line bg-page/60 px-4 py-3 text-left transition hover:border-violet-400/40">
              <div className="flex items-center gap-2 text-xs text-ink-3">
                <Chip className={cn(i === 0 && "border-violet-400/50 bg-violet-500/15 text-violet-800 dark:text-violet-100")}>{i === 0 ? "중심" : "받침"}</Chip>
                {p.source} · {p.who}
              </div>
              <p className="mt-2 text-[14px] leading-relaxed text-ink">{p.role}</p>
            </button>
          ))}
          {!run &&
            a?.sources.map(([p, d]) => (
              <button key={p} onClick={() => onSource(p)} className="block w-full rounded-2xl border border-line bg-page/60 px-4 py-3 text-left text-[14px] text-ink-2 transition hover:border-violet-400/40">
                {d}
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
