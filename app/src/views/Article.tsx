import { useEffect, useMemo, useRef, useState } from "react";
import { IconPencil, IconQuote, IconRefresh, IconSparkles } from "@tabler/icons-react";
import { Timeline } from "@/components/ui/timeline";
import { HoverEffect } from "@/components/ui/card-hover-effect";
import { FocusCards } from "@/components/ui/focus-cards";
import { PillTabs } from "@/components/ui/tabs";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { MultiStepPanel } from "@/components/ui/multi-step-loader";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import ParticleButton from "@/components/kokonutui/particle-button";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import { LiveLog } from "@/components/studio/live-log";
import { Working } from "@/components/studio/working";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ByChip, Chip, ClaudeMark, MiniMd, SiteIcon, SourceDrawer, sourceName } from "@/components/studio/bits";
import { Cover, StageChip } from "@/views/Articles";
import { act, articleTitle, getChat, img, runningJob, type Article as A, type ChatMsg, type Job, type State, type Step } from "@/lib/api";
import { keptSentences, paragraphs, sentences, when } from "@/lib/text";
import { cn } from "@/lib/utils";

const TABS = [
  { value: "title", title: "제목" },
  { value: "process", title: "과정" },
  { value: "image", title: "그림" },
  { value: "confirm", title: "확정" },
];

export default function Article({
  state,
  id,
  tab,
  refresh,
  go,
}: {
  state: State;
  id: string;
  tab?: string;
  refresh: () => void;
  go: (h: string) => void;
}) {
  const a = state.articles.find((x) => x.id === id);
  const [src, setSrc] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  if (!a) return null;
  const lib = Object.fromEntries(state.library.map((s) => [s.path, s]));
  const t = tab || (a.kind === "brief" && !a.title && !a.steps.length ? "title" : "process");
  const hero = a.hero || a.confirmed?.hero || "";

  return (
    <div className="min-h-full pb-80">
      <div className="relative h-[380px] overflow-hidden">
        {hero ? (
          <img src={img(hero, 1600)} className="absolute inset-0 h-full w-full object-cover" />
        ) : (
          <Cover a={a} />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-page via-page/70 to-page/10" />
        <div className="relative z-10 mx-auto flex h-full max-w-6xl flex-col justify-end px-12 pb-10">
          <div className="flex items-center gap-2">
            <StageChip a={a} />
            {a.sources.map(([p, d]) => (
              <button key={p} onClick={() => setSrc(p)} className="transition hover:opacity-80">
                <Chip className="bg-page/60 backdrop-blur">
                  <SiteIcon site={lib[p]?.site ?? ""} className="size-3.5" />
                  <span className="max-w-56 truncate">{lib[p] ? sourceName(lib[p]) : d}</span>
                </Chip>
              </button>
            ))}
          </div>
          <h1 className="mt-5 max-w-4xl text-5xl font-bold leading-tight tracking-tight text-ink">{articleTitle(a)}</h1>
          <p className="mt-4 max-w-3xl text-[17px] leading-relaxed text-ink-2">{a.thesis}</p>
        </div>
      </div>

      <div className="sticky top-0 z-30 border-b border-line bg-page/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-12 py-3">
          <PillTabs tabs={TABS} value={t} onChange={(v) => go(`#/a/${a.id}/${v}`)} />
          <span className="flex items-center gap-3">
          <Retry a={a} go={go} refresh={refresh} />
          <PillTabs
            id="lengthtab"
            tabs={[
              { value: "full", title: "기본" },
              { value: "half", title: "절반" },
            ]}
            value={a.length}
            onChange={(v) => act("length", { article: a.id, mode: v }).then(refresh)}
          />
          </span>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-12">
        {t === "title" && <Titles a={a} state={state} refresh={refresh} go={go} />}
        {t === "process" && <Process a={a} state={state} refresh={refresh} go={go} />}
        {t === "image" && <Images a={a} state={state} refresh={refresh} />}
        {t === "confirm" && <Confirm a={a} refresh={refresh} />}
      </div>

      {(t === "process" || t === "title") && (
        <Composer key={t} a={a} tab={t} state={state} refresh={refresh} onDirector={() => setChatOpen(true)} />
      )}
      <button
        onClick={() => setChatOpen(true)}
        className="fixed right-8 bottom-8 z-40 grid size-14 place-items-center rounded-full border border-line bg-panel-solid shadow-2xl shadow-orange-500/10 transition hover:scale-105 hover:border-orange-300/40"
      >
        <ClaudeMark className="size-5" />
        {runningJob(state.jobs, "chat", a.id) && <span className="absolute top-1 right-1 size-3 animate-ping rounded-full bg-orange-400" />}
      </button>
      <Director a={a} state={state} open={chatOpen} onClose={() => setChatOpen(false)} refresh={refresh} />
      <SourceDrawer path={src} onClose={() => setSrc(null)} />
    </div>
  );
}

function Spin({ texts }: { texts: string[] }) {
  return <AITextLoading texts={texts} className="text-sm font-medium" wrapperClassName="p-0" />;
}

function RunButton({ running, onClick, icon, label, spin }: { running: boolean; onClick: () => void; icon: React.ReactNode; label: string; spin: string[] }) {
  return (
    <HoverBorderGradient
      containerClassName="rounded-full"
      className="flex items-center gap-2 bg-page px-5 py-2.5 text-sm text-ink"
      onClick={() => !running && onClick()}
    >
      {running ? (
        <Spin texts={spin} />
      ) : (
        <>
          {icon}
          {label}
        </>
      )}
    </HoverBorderGradient>
  );
}

/* ---------- 제목 ---------- */

function Titles({ a, state, refresh, go }: { a: A; state: State; refresh: () => void; go: (h: string) => void }) {
  const titleJob = runningJob(state.jobs, "titles", a.id);
  const readJob = runningJob(state.jobs, "wiki-pick", a.id);
  const running = !!titleJob;
  const reading = !!readJob;
  const writing = !!runningJob(state.jobs, "write", a.id);
  const rounds = [...a.titles].reverse();
  if (a.kind === "process")
    return <div className="py-24 text-center text-4xl font-semibold text-ink">{a.title}</div>;
  return (
    <div className="py-10">
      <div className="flex items-center justify-between">
        {a.title && !a.steps.length ? (
          <ParticleButton
            className="h-12 rounded-full bg-ink px-8 text-base font-semibold text-page hover:bg-violet-500 hover:text-ink"
            disabled={writing}
            onClick={() => act("write", { article: a.id }).then(refresh).then(() => go(`#/a/${a.id}/process`))}
          >
            {writing ? "…" : "쓰기"}
          </ParticleButton>
        ) : (
          <span />
        )}
        {!reading && <RunButton
          running={running}
          onClick={() => act("titles", { article: a.id }).then(refresh)}
          icon={<IconRefresh className="size-4" />}
          label="다시 뽑기"
          spin={["astra", "제목 짓는 중"]}
        />}
      </div>
      {(readJob || titleJob) && (
        <div className="mt-8">
          {titleJob?.message && <Feedback text={titleJob.message} />}
          <Working
            job={(readJob || titleJob)!}
            title={readJob ? "깊게 읽기" : "제목 후보"}
            status={readJob ? "astra가 이 주제 원문을 읽는 중" : "astra 제목 짓는 중"}
            steps={readJob ? [{ label: "깊게 읽기", by: "astra" }, { label: "제목 후보", by: "astra" }] : undefined}
            stepIndex={readJob ? 0 : 1}
          />
        </div>
      )}
      {rounds.map((r, ri) => (
        <section key={r.at} className={cn("mt-8", ri > 0 && "opacity-60 transition hover:opacity-100")}>
          {rounds.length > 1 && <div className="px-2 text-sm tabular-nums text-ink-3">{when(r.at)}</div>}
          {r.message && <div className="mt-3 px-2"><Feedback text={r.message} /></div>}
          <HoverEffect
            items={r.items}
            getKey={(x) => x}
            selected={a.title}
            onSelect={(x) => act("title", { article: a.id, title: x }).then(refresh)}
            render={(x, i) => (
              <div className="flex min-h-36 flex-col justify-between">
                <span className="text-sm tabular-nums text-ink-3">{String(i + 1).padStart(2, "0")}</span>
                <span className="mt-6 text-lg font-semibold leading-snug text-ink [word-break:keep-all]">{x}</span>
              </div>
            )}
          />
        </section>
      ))}
    </div>
  );
}

/* ---------- 과정 ---------- */

function Prose({ text, prev }: { text: string; prev?: string }) {
  const kept = useMemo(() => (prev !== undefined ? keptSentences(prev, text) : null), [prev, text]);
  let idx = 0;
  return (
    <div className="prose-ko text-ink">
      {paragraphs(text).map((p, i) => {
        if (/^#{1,3}\s/.test(p)) return <h4 key={i} className="mt-8 mb-3 text-lg font-semibold text-ink">{p.replace(/^#+\s*/, "")}</h4>;
        return (
          <p key={i}>
            {sentences(p.replace(/^[>*\-\s]+/, "")).map((s, j) => {
              const k = idx++;
              const fresh = kept && !kept.has(k);
              return (
                <span key={j} className={cn(fresh && "s-add text-ink")}>
                  {s}{" "}
                </span>
              );
            })}
          </p>
        );
      })}
    </div>
  );
}

function Feedback({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="mb-6 flex w-full gap-3 rounded-2xl border border-violet-400/20 bg-violet-500/[0.07] p-5 text-left"
    >
      <IconQuote className="size-5 shrink-0 text-violet-500 dark:text-violet-300" />
      <span className={cn("whitespace-pre-line text-[14.5px] leading-relaxed text-violet-900 dark:text-violet-100/90", !open && "line-clamp-3")}>{text}</span>
    </button>
  );
}

function StepCard({ s, prev, diff, articleTitle: at }: { s: Step; prev?: Step; diff: boolean; articleTitle: string }) {
  return (
    <div className="max-w-[720px]">
      {s.feedback && <Feedback text={s.feedback} />}
      <div className="rounded-3xl border border-line bg-panel px-10 py-9">
        {s.title && s.title !== at && <h3 className="mb-6 text-2xl font-semibold leading-snug text-ink">{s.title}</h3>}
        <Prose text={s.text} prev={diff && prev ? prev.text : undefined} />
      </div>
    </div>
  );
}

function StepMeta({ s }: { s: Step }) {
  return (
    <span className="flex items-center gap-2 text-sm text-ink-3">
      <ByChip by={s.by} />
      {s.mode && <Chip className="border-sky-400/40 bg-sky-500/10 text-sky-700 dark:text-sky-200">{s.mode}</Chip>}
      <span className="tabular-nums">{s.chars.toLocaleString()}자</span>
      <span className="tabular-nums">{when(s.at)}</span>
    </span>
  );
}

/**
 * 과정 — 맨 위에는 '지금 과정' 하나(진행 중이면 진행 카드, 아니면 최신 과정 본문), 그 아래 지난 과정을 최신순으로 접어 둔다
 * (멘토 2026-10-10: "역순으로, 지금 진행되는 과정만 보여 주고 과정 1·2는 접을 수 있게").
 */
function Process({ a, state, refresh, go }: { a: A; state: State; refresh: () => void; go: (h: string) => void }) {
  const [diff, setDiff] = useState(false);
  const write = runningJob(state.jobs, "write", a.id);
  const other = runningJob(state.jobs, "revise", a.id) || runningJob(state.jobs, "shorten", a.id);
  const job = write || other;
  const at = articleTitle(a);
  const past = [...a.steps].reverse();
  const current = job ? undefined : past[0];
  const rest = job ? past : past.slice(1);

  let working: React.ReactNode = null;
  if (write) {
    const st = (write as Job & { stage?: { index: number; half: boolean } }).stage;
    const steps = [
      { label: "과정 1", by: "Claude" },
      { label: "과정 2", by: "astra" },
      { label: "과정 3", by: "astra" },
      ...(st?.half || a.length === "half" ? [{ label: "과정 4 · 절반", by: "astra" }] : []),
    ];
    const i = st?.index ?? 0;
    const status = ["Claude 초안 쓰는 중", "astra 재작성 중", "astra 기준 반영 중", "astra 절반으로 줄이는 중"][i] ?? "쓰는 중";
    working = <Working job={write} title={`과정 ${i + 1}`} status={status} steps={steps} stepIndex={i} />;
  } else if (other) {
    working = (
      <Working
        job={other}
        title={`과정 ${a.steps.length + 1}`}
        status={other.kind === "shorten" ? "astra 절반으로 줄이는 중" : "astra 피드백 반영 중"}
      />
    );
  }

  if (!job && !a.steps.length)
    return (
      <div className="flex justify-center py-32">
        {a.title ? (
          <ParticleButton
            className="h-12 rounded-full bg-ink px-10 text-base font-semibold text-page hover:bg-violet-500 hover:text-ink"
            onClick={() => act("write", { article: a.id }).then(refresh)}
          >
            쓰기
          </ParticleButton>
        ) : (
          <button onClick={() => go(`#/a/${a.id}/title`)} className="rounded-full border border-line px-8 py-3 text-ink hover:bg-soft">
            제목
          </button>
        )}
      </div>
    );

  return (
    <div className="space-y-6 py-10">
      {working}

      {current && (
        <section>
          <div className="mb-5 flex items-end justify-between gap-4">
            <div className="flex items-end gap-4">
              <h2 className="text-5xl font-bold text-ink">과정 {current.n}</h2>
              <span className="pb-1.5">
                <StepMeta s={current} />
              </span>
            </div>
            {a.steps.length > 1 && (
              <button
                onClick={() => setDiff(!diff)}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm transition",
                  diff ? "border-violet-400/60 bg-violet-500/20 text-violet-800 dark:text-violet-100" : "border-line bg-panel text-ink-2 hover:text-ink"
                )}
              >
                <span className={cn("size-2 rounded-full", diff ? "bg-violet-300" : "bg-ink-3")} />
                비교
              </button>
            )}
          </div>
          <StepCard s={current} prev={a.steps[current.n - 2]} diff={diff} articleTitle={at} />
        </section>
      )}

      {rest.length > 0 && (
        <Accordion type="multiple" className="rounded-3xl border border-line bg-panel px-6">
          {rest.map((s) => (
            <AccordionItem key={s.n} value={`s${s.n}`} className="border-line">
              <AccordionTrigger className="py-4 hover:no-underline">
                <span className="flex items-center gap-4">
                  <span className="text-xl font-bold text-ink">과정 {s.n}</span>
                  <StepMeta s={s} />
                </span>
              </AccordionTrigger>
              <AccordionContent className="pb-6">
                <StepCard s={s} prev={a.steps[s.n - 2]} diff={diff} articleTitle={at} />
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}
    </div>
  );
}

/* ---------- 피드백·진행자 입력 ---------- */

function Composer({ a, tab, state, refresh, onDirector }: { a: A; tab: string; state: State; refresh: () => void; onDirector: () => void }) {
  // 제목 탭: 다시 뽑을 때 astra에게 같이 보낼 말(멘토 2026-10-10)
  const canTitle = tab === "title" && a.kind === "brief";
  const canRevise = tab === "process" && a.kind === "brief" && a.steps.length >= 3;
  const modes = [
    ...(canTitle ? [{ id: "titles", label: "제목", icon: <IconSparkles className="size-3.5 text-emerald-300" /> }] : []),
    ...(canRevise ? [{ id: "feedback", label: "피드백", icon: <IconPencil className="size-3.5 text-emerald-300" /> }] : []),
    { id: "director", label: "진행자", icon: <ClaudeMark className="size-3.5" /> },
  ];
  const [mode, setMode] = useState(modes[0].id);
  useEffect(() => {
    if (!modes.find((m) => m.id === mode)) setMode(modes[0].id);
  }, [canRevise, canTitle]); // eslint-disable-line
  const busy =
    (canTitle && (runningJob(state.jobs, "titles", a.id) || runningJob(state.jobs, "wiki-pick", a.id))) ||
    runningJob(state.jobs, "revise", a.id) ||
    runningJob(state.jobs, "chat", a.id);
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center bg-gradient-to-t from-page via-page/90 to-transparent pt-16 pl-[60px]">
      <AI_Prompt
        className="pointer-events-auto w-[680px] pb-5"
        modes={modes}
        mode={mode}
        onModeChange={setMode}
        placeholder={mode === "feedback" ? `과정 ${a.steps.length + 1}` : ""}
        busy={busy ? <Spin texts={[busy.kind === "chat" ? "진행자" : "astra", "…"]} /> : undefined}
        onSubmit={(v, m) => {
          if (m === "titles") act("titles", { article: a.id, message: v }).then(refresh);
          else if (m === "feedback") act("revise", { article: a.id, feedback: v }).then(refresh);
          else {
            act("chat", { article: a.id, message: v }).then(refresh);
            onDirector();
          }
        }}
      />
    </div>
  );
}

function Director({ a, state, open, onClose, refresh }: { a: A; state: State; open: boolean; onClose: () => void; refresh: () => void }) {
  const [log, setLog] = useState<ChatMsg[]>([]);
  const [mode, setMode] = useState("director");
  const running = runningJob(state.jobs, "chat", a.id);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    let alive = true;
    const pull = () => getChat(a.id).then((l) => alive && setLog(l));
    pull();
    const t = setInterval(pull, 2500);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [open, a.id, !!running]);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [log.length, !!running]);
  return (
    <Drawer direction="right" open={open} onOpenChange={(o) => !o && onClose()}>
      <DrawerContent className="z-[70] bg-page border-line data-[vaul-drawer-direction=right]:w-[560px] data-[vaul-drawer-direction=right]:sm:max-w-[560px]">
        <div className="flex h-full flex-col">
          <div className="flex items-center gap-3 border-b border-line px-7 py-5">
            <ClaudeMark className="size-4" />
            <DrawerTitle className="text-base font-semibold text-ink">진행자</DrawerTitle>
          </div>
          <div className="flex-1 space-y-5 overflow-y-auto px-7 py-6">
            {log.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "mentor" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "max-w-[88%] rounded-2xl px-4 py-3 text-[14.5px] leading-relaxed",
                    m.role === "mentor" && "whitespace-pre-line",
                    m.role === "mentor" ? "bg-violet-500/20 text-violet-950 dark:text-violet-50" : "border border-line bg-panel-solid text-ink"
                  )}
                >
                  {m.role === "claude" ? <MiniMd text={m.text} /> : m.text}
                </div>
              </div>
            ))}
            {running && <Spin texts={["진행자", "명령 실행 중", "결과 확인 중"]} />}
            <div ref={end} />
          </div>
          <AI_Prompt
            className="w-full px-5 pb-5"
            modes={[{ id: "director", label: "진행자", icon: <ClaudeMark className="size-3.5" /> }]}
            mode={mode}
            onModeChange={setMode}
            onSubmit={(v) => act("chat", { article: a.id, message: v }).then(refresh)}
          />
        </div>
      </DrawerContent>
    </Drawer>
  );
}

/* ---------- 그림 ---------- */

function Images({ a, state, refresh }: { a: A; state: State; refresh: () => void }) {
  const heroJob = runningJob(state.jobs, "images", a.id);
  const inlineJob = runningJob(state.jobs, "inline", a.id);
  const running = !!heroJob;
  const runningInline = !!inlineJob;
  const canDraw = a.steps.length > 0;
  const picked = new Set(a.inlinePicked.map((x) => x.src));
  return (
    <div className="space-y-20 py-10">
      <section>
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-ink">머리 그림</h2>
          {canDraw && (
            <RunButton
              running={running}
              onClick={() => act("images", { article: a.id }).then(refresh)}
              icon={<IconSparkles className="size-4" />}
              label="머리 그림 뽑기"
              spin={["astra", "gti", "그리는 중"]}
            />
          )}
        </div>
        {heroJob && (
          <div className="mt-8">
            <Working job={heroJob} title="머리 그림" status="astra 그림 설명 → gti 그리는 중" />
          </div>
        )}
        {[...a.images].reverse().map((r) => (
          <div key={r.id} className="mt-8">
            <FocusCards
              height="h-72"
              cards={r.items.map((it, i) => ({
                key: `${r.id}-${i}`,
                title: it.name,
                src: it.src ? img(it.src, 900) : undefined,
                fallback: <div className="absolute inset-0 bg-panel-solid" />,
                selected: !!it.src && a.hero === it.src,
                onClick: () => it.src && act("hero", { article: a.id, src: it.src }).then(refresh),
                overlay: <div className="text-lg font-medium">{it.name}</div>,
              }))}
            />
          </div>
        ))}
      </section>

      <section>
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-ink">
            본문 그림 {a.inlinePicked.length > 0 && <span className="tabular-nums text-violet-500">{a.inlinePicked.length}</span>}
          </h2>
          {canDraw && (
            <RunButton
              running={runningInline}
              onClick={() => act("images", { article: a.id, kind: "inline" }).then(refresh)}
              icon={<IconSparkles className="size-4" />}
              label="본문 그림 뽑기"
              spin={["astra", "gti", "그리는 중"]}
            />
          )}
        </div>
        {inlineJob && (
          <div className="mt-8">
            <Working job={inlineJob} title="본문 그림" status="astra 들어갈 자리 고르기 → gti 그리는 중" />
          </div>
        )}
        {[...a.inline].reverse().map((r) => (
          <div key={r.id} className="mt-8">
            <FocusCards
              height="h-72"
              cards={r.items.map((it, i) => ({
                key: `${r.id}-${i}`,
                title: it.name,
                src: it.src ? img(it.src, 900) : undefined,
                fallback: <div className="absolute inset-0 bg-panel-solid" />,
                selected: picked.has(it.src),
                badge: <Chip className="border-line bg-page/70 text-ink backdrop-blur">문단 {it.after}</Chip>,
                onClick: () => it.src && act("inline", { article: a.id, src: it.src, on: !picked.has(it.src) }).then(refresh),
                overlay: (
                  <div>
                    <div className="text-lg font-medium">{it.name}</div>
                    <div className="mt-1 line-clamp-1 text-sm opacity-75">{it.anchor}…</div>
                  </div>
                ),
              }))}
            />
          </div>
        ))}
      </section>
    </div>
  );
}

/* ---------- 확정 ---------- */

function Confirm({ a, refresh }: { a: A; refresh: () => void }) {
  const [n, setN] = useState(a.confirmed?.step ?? a.steps.length);
  const s = a.steps[n - 1];
  const hero = a.hero || a.confirmed?.hero || "";
  if (!s) return null;
  return (
    <div className="grid grid-cols-[1fr_260px] gap-12 py-10">
      <article className="overflow-hidden rounded-3xl border border-line bg-[#fbfaf7] text-neutral-900 shadow-2xl">
        {hero && <img src={img(hero, 1400)} className="aspect-[3/2] w-full object-cover" />}
        <div className="px-14 py-12">
          <h2 className="text-[32px] font-bold leading-snug tracking-tight">{articleTitle(a)}</h2>
          <div className="prose-ko mt-8 text-[16.5px] text-neutral-800">
            {paragraphs(s.text).map((p, i, all) => (
              <div key={i}>
                <p>{p}</p>
                {inlineAt(a, all, i + 1).map((it) => (
                  <img key={it.src} src={img(it.src, 1200)} className="my-8 w-full rounded-2xl" />
                ))}
              </div>
            ))}
          </div>
        </div>
      </article>
      <aside className="sticky top-24 h-fit space-y-6">
        <div className="flex flex-wrap gap-2">
          {a.steps.map((x) => (
            <button
              key={x.n}
              onClick={() => setN(x.n)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm transition",
                x.n === n ? "border-ink bg-ink text-page" : "border-line text-ink-2 hover:text-ink"
              )}
            >
              과정 {x.n}
            </button>
          ))}
        </div>
        <div className="text-sm tabular-nums text-ink-3">{s.chars.toLocaleString()}자</div>
        {a.confirmed ? (
          <Chip className="border-emerald-300/40 bg-emerald-500/15 px-4 py-1.5 text-sm text-emerald-800 dark:text-emerald-100">
            확정 {a.confirmed.date}
            {a.confirmed.step ? ` · 과정 ${a.confirmed.step}` : ""}
          </Chip>
        ) : null}
        {a.kind === "brief" && (
          <ParticleButton
            className="h-12 w-full rounded-full bg-ink text-base font-semibold text-page hover:bg-emerald-500 hover:text-ink"
            onClick={() => act("confirm", { article: a.id, step: n }).then(refresh)}
          >
            확정
          </ParticleButton>
        )}
      </aside>
    </div>
  );
}

/** 고른 본문 그림 중 n째 문단 뒤에 들어갈 것 — 문단 첫머리(anchor)로 찾고, 못 찾으면 문단 번호로 */
function inlineAt(a: A, paras: string[], n: number) {
  return a.inlinePicked.filter((it) => {
    const hit = it.anchor ? paras.findIndex((p) => p.startsWith(it.anchor.slice(0, 20))) + 1 : 0;
    return (hit || Math.min(it.after, paras.length)) === n;
  });
}

/** 다시 쓰기 — 같은 설정으로 새 글을 만들어 과정 1부터. 한 번 누르면 '한 번 더'로 바뀌고 두 번째에 실행(10분 넘게 도는 일이라) */
function Retry({ a, go, refresh }: { a: A; go: (h: string) => void; refresh: () => void }) {
  const [arm, setArm] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => setArm(false), 3000);
    return () => clearTimeout(t);
  }, [arm]);
  if (!a.title || !a.steps.length) return null;
  return (
    <button
      onClick={async () => {
        if (!arm) return setArm(true);
        setBusy(true);
        const r = await act<{ article: string }>("retry", { article: a.id });
        await refresh();
        go(`#/a/${r.article}/process`);
      }}
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm transition",
        arm ? "border-violet-400/60 bg-violet-500/15 text-violet-800 dark:text-violet-100" : "border-line text-ink-2 hover:bg-soft hover:text-ink"
      )}
    >
      <IconRefresh className="size-4" />
      {busy ? "…" : arm ? "한 번 더" : "다시 쓰기"}
    </button>
  );
}
