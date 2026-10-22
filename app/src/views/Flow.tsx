import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { IconArrowBackUp, IconArrowRight, IconCheck, IconChevronDown, IconFileText, IconPencil, IconPhoto, IconRefresh, IconSparkles, IconTrash } from "@tabler/icons-react";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import ParticleButton from "@/components/kokonutui/particle-button";
import { PillTabs } from "@/components/ui/tabs";
import { ByChip, Chip, ClaudeMark, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { Director, Prose, inlineAt } from "@/views/parts";
import { DeleteButton, StageChip } from "@/views/Articles";
import { OptionsCard, PicksCard, useAttach } from "@/views/MineChat";
import { act, articleTitle, img, openLog, type Article as A, type Job, type MinePick, type MineRun, type State, type Step } from "@/lib/api";
import { paragraphs } from "@/lib/text";
import { cn } from "@/lib/utils";

// 편집기(Tiptap)는 '편집'을 누를 때만 받아 온다
const ProseEditor = lazy(() => import("@/components/studio/editor").then((m) => ({ default: m.ProseEditor })));

/**
 * 글 화면 = 대화 (멘토 2026-10-11: "그 글에 있는 채팅이 계속해서 글 작성까지 흐름을 끌고 간다 … 실제로 그렇게 되어야 한다")
 * 왼쪽: 요청 → 고른 원문 → 제목 후보 → 쓰기 → 과정 1·2·3 → 피드백 → 과정 4… → 그림 → 확정이 한 줄로 쌓인다.
 * 오른쪽: 지금 글(고른 원문 → 정한 제목 → 최신 과정 본문).
 * 입력창 하나 — 단계에 따라 보낸 말이 가는 곳이 정해진다(원문: 대화 전체로 다시 고르기 · 제목: astra 제목 회차 · 과정 3 뒤: 피드백).
 * 다음 단계는 카드의 버튼으로만 넘어간다(이 원문으로 · 제목 누르기 · 쓰기 · 그림 · 확정).
 */

/** 숫자 뒤 '로/으로' — 1·2·4·5·7·8·9는 로, 3·6·0은 으로(삼·육·영·십) */
const ro = (n: number) => ([3, 6, 0].includes(n % 10) ? "으로" : "로");

const KINDS = ["mine", "titles", "write", "revise", "shorten", "images", "inline", "wiki-pick"];
const jobOf = (jobs: Job[], id: string) => jobs.find((j) => j.status === "running" && j.target === id && KINDS.includes(j.kind));
const MINE_TEXT: Record<string, string> = { 문서: "문서 읽는 중", 후보: "원문 카드 보는 중", 고르기: "원문 읽고 고르는 중", 옵션: "카드 보고 글 옵션 짜는 중", 확인: "고른 원문 끝까지 읽는 중", 제목: "제목 후보 짓는 중" };

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
  if (j.kind === "images" || j.kind === "inline") {
    const what = j.kind === "images" ? "머리 그림" : "본문 그림";
    const s = j.istage;
    if (!s || s.phase === "설명") return [`${what} · astra가 그림 설명 쓰는 중`];
    const min = Math.floor((Date.now() / 1000 - s.since) / 60);
    const wait = min >= 1 ? ` · ${min}분째` : "";
    const fail = s.failed ? ` · 실패 ${s.failed}` : "";
    return [`${what} 그리는 중 ${s.done}/${s.total}장${fail}${wait}`];
  }
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
  const nSteps = a?.steps.length ?? 0;
  useEffect(() => setSel(null), [nSteps]); // 새 과정이 생기면 오른쪽은 최신 과정으로
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
          {a && a.kind === "brief" && <DeleteButton a={a} refresh={refresh} onDone={() => go("#/articles")} />}
        </header>

        <div ref={box} className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[820px] space-y-7 px-10 pt-10 pb-56">
            <Timeline a={a} run={run} job={job} state={state} refresh={refresh} sel={sel} setSel={setSel} onSource={setSrc} />
          </div>
        </div>

        <ChatInput a={a} run={run} job={job} refresh={refresh} onDirector={() => setDirector(true)} />
      </section>

      <aside className="h-screen overflow-y-auto bg-soft/30">
        <Now a={a} run={run} job={job} sel={sel} setSel={setSel} refresh={refresh} onSource={setSrc} />
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
  setSel: (n: number | null) => void;
  onSource: (p: string) => void;
}) {
  const out: React.ReactNode[] = [];
  const started = !!a && a.steps.length > 0;

  // 1. 시작 — 내 주제로 쓰기(대화 차례) 또는 주제 지도·설정에서 온 글
  if (run) {
    const lastAi = run.turns.map((t) => t.role).lastIndexOf("ai");
    run.turns.forEach((t, i) => {
      if (t.role === "mentor") out.push(<Me key={`m${i}`} docs={t.docs}>{t.text}</Me>);
      else if ("options" in t) {
        // 글 옵션 — 바로 뒤 차례가 고른 원문이면 그 번호를 '고름'으로
        const next = run.turns[i + 1];
        const chosen = next && next.role === "ai" && "center" in next ? next.option : undefined;
        out.push(
          <Ai key={`o${i}`} label={<>글 옵션 {t.options.length}개{chosen ? "" : " · 하나를 고르면 원문을 끝까지 읽고 확인합니다"}</>}>
            <OptionsCard run={run} options={t.options} live={i === lastAi && run.status !== "running" && !started} chosen={chosen} onSource={onSource} refresh={refresh} />
          </Ai>
        );
      } else if (i === lastAi && run.status !== "running" && run.picked.length)
        out.push(
          <Ai key={`a${i}`} label={t.option ? <>고른 원문 · 옵션 {t.option} · 원문 확인 뒤</> : <>고른 원문 · 후보 {t.n_candidates}편 중</>}>
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
    // 이 글이 말할 것 — 원문을 고를 때 같이 정한 한 문장(멘토 2026-10-11 "무슨말을 하려고 하는지 너무 뜬구름") · 쓰기 전에 보고 고칠 수 있게
    if (a?.fromMine && a.thesis && a.thesis !== run.message && run.status !== "running")
      out.push(
        <Ai key="point" label="이 글이 말할 것">
          <div className="rounded-2xl border border-violet-400/40 bg-violet-500/[0.07] px-5 py-3.5 text-[15.5px] font-medium leading-relaxed text-ink">{a.thesis}</div>
        </Ai>
      );
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
          <TitlesCard a={a} items={r.items} live={!started} last={ri === a.titles.length - 1 && !job} refresh={refresh} />
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
    a.tries?.forEach((tr) => {
      out.push(
        <Ai key={`try${tr.n}`} label={<>{tr.n}번째 글 · 과정 1–{tr.steps.length}</>}>
          <TryCard title={tr.title} steps={tr.steps} />
        </Ai>
      );
      out.push(
        <Me key={`tryr${tr.n}`}>
          <span className="flex items-center gap-2"><IconRefresh className="size-4" />처음부터 다시 쓰기</span>
        </Me>
      );
    });
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
    out.push(<Ai key="confirm" label="확정"><ConfirmCard a={a} sel={sel} setSel={setSel} refresh={refresh} /></Ai>);
  }
  if (a && a.kind === "brief" && started && !a.confirmed && !job) out.push(<Restart key="restart" a={a} refresh={refresh} />);

  // 돌고 있는 작업 — 보낸 말이 있으면 먼저(제목·피드백)
  if (job) {
    if (job.message && job.kind !== "mine") out.push(<Me key="jm">{job.message}</Me>);
    const steps = job.kind === "write" ? 3 : job.kind === "mine" ? 3 : 0;
    const at = job.kind === "write" ? job.stage?.index ?? 0 : ["옵션", "확인", "제목"].indexOf(run?.stage ?? "");
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

function TitlesCard({ a, items, live, last, refresh }: { a: A; items: string[]; live: boolean; last: boolean; refresh: () => void }) {
  return (
    <div className="space-y-2">
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
    {live && last && (
      <div className="flex justify-end">
        <SmallBtn onClick={() => act("titles", { article: a.id }).then(refresh)}>
          <IconRefresh className="size-3.5" />
          다시 뽑기
        </SmallBtn>
      </div>
    )}
    </div>
  );
}

function WriteCard({ a, refresh }: { a: A; refresh: () => void }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-panel-solid px-5 py-4">
      <span className="flex flex-wrap items-center gap-2">
        <Chip className="text-ink">{a.target}</Chip>
        <Chip className="text-ink">{a.length === "half" ? "절반" : "기본"}</Chip>
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
  const [old, setOld] = useState(false);
  const picked = new Set(a.inlinePicked.map((x) => x.src));
  const busyHero = state.jobs.some((j) => j.status === "running" && j.target === a.id && j.kind === "images");
  const busyInline = state.jobs.some((j) => j.status === "running" && j.target === a.id && j.kind === "inline");
  const pastN = Math.max(0, a.images.length - 1) + Math.max(0, a.inline.length - 1);
  const heroRound = (r: A["images"][number]) => (
    <div key={r.id} className="grid grid-cols-4 gap-2">
      {r.items.filter((x) => x.src).map((x) => (
        <Thumb key={x.src} src={x.src} on={a.hero === x.src} ratio="aspect-[3/2]" name={x.name} onClick={() => act("hero", { article: a.id, src: x.src }).then(refresh)} />
      ))}
    </div>
  );
  const inlineRound = (r: A["inline"][number]) => (
    <div key={r.id} className="grid grid-cols-4 gap-2">
      {r.items.filter((x) => x.src).map((x) => (
        <Thumb key={x.src} src={x.src} on={picked.has(x.src)} ratio="aspect-video" name={x.why ? `${x.name} — ${x.why}` : x.name} chip={x.after ? `문단 ${x.after}` : ""} onClick={() => act("inline", { article: a.id, src: x.src, on: !picked.has(x.src) }).then(refresh)} />
      ))}
    </div>
  );
  return (
    <div className="space-y-4 rounded-2xl border border-line bg-panel-solid px-5 py-4">
      <div className="flex items-center gap-2">
        <button
          disabled={busyHero}
          onClick={() => act("images", { article: a.id }).then(refresh)}
          className="flex items-center gap-2 rounded-full border border-line px-4 py-2 text-sm text-ink transition hover:bg-soft disabled:opacity-50"
        >
          <IconPhoto className="size-4" />
          머리 그림{a.images.length > 0 && " 다시"}
        </button>
        <button
          disabled={busyInline}
          onClick={() => act("images", { article: a.id, kind: "inline" }).then(refresh)}
          className="flex items-center gap-2 rounded-full border border-line px-4 py-2 text-sm text-ink transition hover:bg-soft disabled:opacity-50"
        >
          <IconSparkles className="size-4" />
          본문 그림{a.inline.length > 0 && " 다시"}
        </button>
        {pastN > 0 && (
          <button onClick={() => setOld(!old)} className="ml-auto flex items-center gap-1 text-sm text-ink-3 hover:text-ink">
            지난 회차 {pastN}
            <IconChevronDown className={cn("size-4 transition", old && "rotate-180")} />
          </button>
        )}
      </div>
      {old && (
        <div className="space-y-2 opacity-70">
          {a.images.slice(0, -1).map(heroRound)}
          {a.inline.slice(0, -1).map(inlineRound)}
        </div>
      )}
      {a.images.length > 0 && heroRound(a.images[a.images.length - 1])}
      {a.inline.length > 0 && inlineRound(a.inline[a.inline.length - 1])}
    </div>
  );
}

function Thumb({ src, on, ratio, name, chip, onClick }: { src: string; on: boolean; ratio: string; name: string; chip?: string; onClick: () => void }) {
  return (
    <button onClick={onClick} title={name} className={cn("group relative overflow-hidden rounded-xl ring-2 transition", on ? "ring-violet-400" : "ring-transparent hover:ring-line")}>
      <img src={img(src, 360)} className={cn(ratio, "w-full object-cover")} />
      {chip && <span className="absolute top-1.5 left-1.5 rounded-full bg-black/60 px-2 py-0.5 text-[11px] text-white">{chip}</span>}
      <span className="absolute inset-x-0 bottom-0 line-clamp-1 bg-gradient-to-t from-black/70 to-transparent px-2 pt-4 pb-1.5 text-left text-[11px] text-white opacity-0 transition group-hover:opacity-100">{name}</span>
    </button>
  );
}

/** 확정 — 확정할 과정을 고른다(멘토 2026-10-11: "과정은 내가 원하는 과정을 선택할수있도록도 해줘야할듯. 확정이 강요됨").
 *  과정 칩을 누르면 오른쪽 '지금 글'에 그 과정이 뜨고, 확정은 원할 때만. 확정한 뒤에도 다른 과정으로 바꿀 수 있다. */
function ConfirmCard({ a, sel, setSel, refresh }: { a: A; sel: number | null; setSel: (n: number | null) => void; refresh: () => void }) {
  const n = sel ?? a.confirmed?.step ?? a.steps.length;
  const same = a.confirmed?.step === n;
  return (
    <div className={cn("rounded-2xl border px-5 py-4", a.confirmed ? "border-emerald-400/40 bg-emerald-500/[0.06]" : "border-line bg-panel-solid")}>
      <div className="flex flex-wrap items-center gap-1.5">
        {a.steps.map((s) => (
          <button
            key={s.n}
            onClick={() => setSel(s.n)}
            className={cn(
              "flex items-center gap-1 rounded-full border px-3 py-1 text-sm tabular-nums transition",
              s.n === n ? "border-ink bg-ink text-page" : "border-line text-ink-2 hover:text-ink"
            )}
          >
            {a.confirmed?.step === s.n && <IconCheck className="size-3.5" />}
            과정 {s.n}
          </button>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="min-w-0 truncate text-sm text-ink-3">{a.confirmed ? `과정 ${a.confirmed.step} 확정 · ${a.confirmed.file}` : ""}</span>
        <button
          disabled={same}
          onClick={() => act("confirm", { article: a.id, step: n }).then(refresh)}
          className="flex shrink-0 items-center gap-2 rounded-full border border-emerald-400/50 px-4 py-2 text-sm text-ink transition hover:bg-emerald-500/10 disabled:opacity-40"
        >
          {same ? "확정됨" : a.confirmed ? `과정 ${n}${ro(n)} 바꿔 확정` : `과정 ${n}${ro(n)} 확정`}
          {!same && <IconArrowRight className="size-4" />}
        </button>
      </div>
    </div>
  );
}


/* ---------- 입력 ---------- */

function ChatInput({ a, run, job, refresh, onDirector }: { a?: A; run?: MineRun; job?: Job; refresh: () => void; onDirector: () => void }) {
  const r = route(a, run, job);
  const fixed = a?.kind === "process"; // 확정 기준 글 — 원문·제목 단계가 없어 진행자만
  const [mode, setMode] = useState(fixed ? "director" : "auto");
  const at = useAttach();
  const modes = [
    ...(fixed ? [] : [{ id: "auto", label: r.label || "—", icon: <IconSparkles className="size-3.5 text-violet-300" /> }]),
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

function Now({
  a,
  run,
  job,
  sel,
  setSel,
  refresh,
  onSource,
}: {
  a?: A;
  run?: MineRun;
  job?: Job;
  sel: number | null;
  setSel: (n: number | null) => void;
  refresh: () => void;
  onSource: (p: string) => void;
}) {
  const s = a?.steps.find((x) => x.n === (sel ?? a.steps.length));
  const prev = a && s ? a.steps.find((x) => x.n === s.n - 1) : undefined;
  const latest = a?.steps.length ?? 0;
  const [edit, setEdit] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [view, setView] = useState<"본문" | "비교" | "미리보기">("본문");
  useEffect(() => setEdit(null), [s?.n]);
  const writing = !!job && ["write", "revise", "shorten"].includes(job.kind);
  const hero = a?.hero || a?.confirmed?.hero || "";
  const v = view === "비교" && !prev ? "본문" : view;
  const save = async () => {
    if (!a || !s || edit === null || saving) return;
    setSaving(true);
    try {
      await act("edit", { article: a.id, base: s.n, text: edit }); // 덮어쓰지 않고 '멘토' 과정으로 쌓인다
      setEdit(null);
      setSel(null);
      refresh();
    } finally {
      setSaving(false);
    }
  };
  const confirm = a && s && a.kind === "brief" && !a.confirmed && !writing && (
    <SmallBtn strong={v === "미리보기"} onClick={() => act("confirm", { article: a.id, step: s.n }).then(refresh)}>
      <IconCheck className="size-3.5" />
      과정 {s.n}
      {ro(s.n)} 확정
    </SmallBtn>
  );
  return (
    <div className="space-y-6 px-8 py-6">
      {a && (
        <div className="flex flex-wrap items-center gap-2 border-b border-line pb-4">
          {a.kind === "brief" && (
            <PillTabs
              id="now-target"
              tabs={["전 직원", "팀장급", "사수급", "신입사원"].map((x) => ({ value: x, title: x }))}
              value={a.target}
              onChange={(x) => act("target", { article: a.id, target: x }).then(refresh)}
            />
          )}
          <PillTabs
            id="now-length"
            tabs={[
              { value: "full", title: "기본" },
              { value: "half", title: "절반" },
            ]}
            value={a.length}
            onChange={(x) => !writing && act("length", { article: a.id, mode: x }).then(refresh)}
          />
        </div>
      )}
      {hero && v !== "미리보기" && <img src={img(hero, 900)} className="aspect-[3/2] w-full rounded-2xl object-cover" />}
      {s ? (
        <div>
          <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-ink-3">
            <span className="tabular-nums">과정 {s.n}</span>
            <ByChip by={s.by} />
            <span className="tabular-nums">{(edit === null ? s.chars : edit.replace(/\s/g, "").length).toLocaleString()}자</span>
            {edit === null && (
              <span className="ml-auto flex rounded-full border border-line p-0.5">
                {(["본문", "비교", "미리보기"] as const).map((x) => (
                  <button
                    key={x}
                    disabled={x === "비교" && !prev}
                    onClick={() => setView(x)}
                    className={cn("rounded-full px-2.5 py-0.5 transition disabled:opacity-30", v === x ? "bg-ink text-page" : "hover:text-ink")}
                  >
                    {x}
                  </button>
                ))}
              </span>
            )}
          </div>
          <div className="mb-4 flex flex-wrap items-center gap-1.5">
            {edit !== null ? (
              <>
                <SmallBtn onClick={() => setEdit(null)}>취소</SmallBtn>
                <SmallBtn strong onClick={save}>{saving ? "…" : "저장"}</SmallBtn>
              </>
            ) : (
              a &&
              !writing && (
                <>
                  <SmallBtn onClick={() => (setView("본문"), setEdit(s.text))}>
                    <IconPencil className="size-3.5" />
                    편집
                  </SmallBtn>
                  {a.kind === "brief" && s.n < latest && (
                    <SmallBtn onClick={() => act("base", { article: a.id, step: s.n }).then(() => (setSel(null), refresh()))}>
                      <IconArrowBackUp className="size-3.5" />
                      여기서 이어 쓰기
                    </SmallBtn>
                  )}
                  {(s.n < latest || v === "미리보기") && confirm}
                </>
              )
            )}
          </div>
          {v === "미리보기" && edit === null ? (
            <article className="overflow-hidden rounded-2xl border border-line bg-[#fbfaf7] text-neutral-900 shadow-xl">
              {hero && <img src={img(hero, 900)} className="aspect-[3/2] w-full object-cover" />}
              <div className="px-7 py-7">
                <h2 className="text-[22px] font-bold leading-snug tracking-tight [word-break:keep-all]">{a!.title || s.title}</h2>
                <div className="prose-ko mt-5 text-[14.5px] text-neutral-800">
                  {paragraphs(s.text).map((p_, i, all) => (
                    <div key={i}>
                      <p>{p_}</p>
                      {inlineAt(a!, all, i + 1).map((it) => (
                        <img key={it.src} src={img(it.src, 900)} className="my-5 w-full rounded-xl" />
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </article>
          ) : (
            <>
              <h2 className="mb-6 text-2xl font-bold leading-snug text-ink [word-break:keep-all]">{a!.title || s.title}</h2>
              <div className="text-[15px]">
                {edit !== null ? (
                  <div className="rounded-2xl border border-violet-400/50 bg-panel-solid px-5 py-4">
                    <Suspense fallback={<Prose text={edit} />}>
                      <ProseEditor text={edit} onChange={setEdit} onSave={save} className="prose-ko text-ink" />
                    </Suspense>
                  </div>
                ) : (
                  <Prose text={s.text} prev={v === "비교" ? prev?.text : undefined} />
                )}
              </div>
            </>
          )}
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

function SmallBtn({ children, onClick, strong }: { children: React.ReactNode; onClick: () => void; strong?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full border px-3 py-1 text-xs transition",
        strong ? "border-violet-400/60 bg-violet-500/20 text-ink" : "border-line text-ink-2 hover:bg-soft hover:text-ink"
      )}
    >
      {children}
    </button>
  );
}

/** 처음부터 다시 쓰기로 넘긴 앞 글 — 접어 두고, 펼치면 과정마다 본문 */
function TryCard({ title, steps }: { title: string; steps: Step[] }) {
  const [open, setOpen] = useState(false);
  const last = steps[steps.length - 1];
  return (
    <div className="rounded-2xl border border-line px-5 py-4 opacity-70 transition hover:opacity-100">
      <button onClick={() => setOpen(!open)} className="flex w-full items-start justify-between gap-3 text-left">
        <span className="flex min-w-0 flex-col">
          {title && <span className="text-[15px] font-semibold text-ink">{title}</span>}
          {last && <span className="mt-1 line-clamp-2 text-[13.5px] leading-relaxed text-ink-3">{last.text}</span>}
        </span>
        <IconChevronDown className={cn("mt-1 size-4 shrink-0 text-ink-3 transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="mt-4 space-y-5 border-t border-line pt-4">
          {steps.map((s) => (
            <div key={s.n}>
              <div className="mb-2 flex items-center gap-2 text-xs text-ink-3">
                <span className="tabular-nums">과정 {s.n}</span>
                <ByChip by={s.by} />
                <span className="tabular-nums">{s.chars.toLocaleString()}자</span>
              </div>
              <div className="text-[14px]">
                <Prose text={s.text} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** 처음부터 다시 쓰기 — 같은 대화 안에서. 두 번 눌러야(10분 넘게 다시 도는 일이라) */
function Restart({ a, refresh }: { a: A; refresh: () => void }) {
  const [arm, setArm] = useState(false);
  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => setArm(false), 3000);
    return () => clearTimeout(t);
  }, [arm]);
  return (
    <div className="flex justify-end">
      <button
        onClick={() => (arm ? act("restart", { article: a.id }).then(refresh) : setArm(true))}
        className={cn(
          "flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm transition",
          arm ? "border-violet-400/60 bg-violet-500/15 text-violet-800 dark:text-violet-100" : "border-line text-ink-3 hover:bg-soft hover:text-ink"
        )}
      >
        <IconRefresh className="size-4" />
        {arm ? "한 번 더" : "처음부터 다시 쓰기"}
      </button>
    </div>
  );
}
