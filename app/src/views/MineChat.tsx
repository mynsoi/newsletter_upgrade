import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { IconArrowRight, IconChevronDown, IconCrown, IconFileText, IconMinus, IconPaperclip, IconPlus, IconUsers, IconX } from "@tabler/icons-react";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Chip, SiteIcon, SourceDrawer } from "@/components/studio/bits";
import { act, openLog, type MineRow, type MineRun, type State } from "@/lib/api";
import { cn } from "@/lib/utils";

/** 내 주제로 쓰기 — 메인 화면 채팅 (멘토 2026-10-11: "메인페이지에 채팅 ui를 띄워줘. 거기에다가 내가 요청사항 입력해서 시작하도록")
 *  요청(받은 그대로) + 문서 → scripts/my_topic.py: 카드 전부에서 후보 → 원문 통째로 중심 1 + 받침 → 글 설정 + 제목 후보(astra) */

const TARGET_MODES = [
  { id: "auto", label: "독자 자동", icon: <IconUsers className="size-3.5 text-violet-300" /> },
  ...["전 직원", "팀장급", "사수급", "신입사원"].map((t) => ({ id: t, label: t, icon: <IconUsers className="size-3.5 text-violet-300" /> })),
];
const ACCEPT = ".pdf,.docx,.doc,.hwp,.hwpx,.odt,.rtf,.txt,.md";
const STEPS = ["후보", "고르기", "제목"] as const;
const STAGE_TEXT: Record<string, string[]> = {
  문서: ["문서 읽는 중"],
  후보: ["원문 카드 보는 중", "후보 고르는 중"],
  고르기: ["원문 읽는 중", "중심 원문 고르는 중"],
  제목: ["제목 후보 짓는 중"],
};

const toB64 = (f: File) =>
  new Promise<{ name: string; data: string }>((ok, no) => {
    const r = new FileReader();
    r.onload = () => ok({ name: f.name, data: String(r.result).split(",")[1] ?? "" });
    r.onerror = () => no(r.error);
    r.readAsDataURL(f);
  });

export default function MineChat({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const runs = state.mine ?? [];
  const [files, setFiles] = useState<File[]>([]);
  const [target, setTarget] = useState("auto");
  const [drag, setDrag] = useState(false);
  const [src, setSrc] = useState<string | null>(null);
  const pick = useRef<HTMLInputElement>(null);
  const box = useRef<HTMLDivElement>(null);
  // 새 요청을 보냈을 때와 결과가 도착했을 때 맨 아래로 — 결과가 입력창 뒤에 가려지지 않게
  const last = runs[runs.length - 1];
  useEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [runs.length, last?.status, last?.stage, last?.picked.length]);

  const add = (l: FileList | null) => l && setFiles((f) => [...f, ...Array.from(l)]);
  const send = async (v: string) => {
    const enc = await Promise.all(files.map(toB64));
    await act("mine", { message: v, target: target === "auto" ? "" : target, files: enc });
    setFiles([]);
    refresh();
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        add(e.dataTransfer.files);
      }}
      className={cn("rounded-3xl transition", drag && "ring-2 ring-violet-400/70 ring-offset-8 ring-offset-transparent")}
    >
      {runs.length > 0 && (
        <div ref={box} className="max-h-[62vh] space-y-8 overflow-y-auto px-1 pb-6 pt-2">
          {runs.map((r) => (
            <Turn key={r.id} r={r} state={state} refresh={refresh} go={go} onSource={setSrc} />
          ))}
        </div>
      )}
      <AI_Prompt
        className="w-full py-2"
        modes={TARGET_MODES}
        mode={target}
        onModeChange={setTarget}
        placeholder="어떤 글을 쓸까요?"
        onSubmit={send}
        tools={
          <>
            <input ref={pick} type="file" multiple accept={ACCEPT} className="hidden" onChange={(e) => (add(e.target.files), (e.target.value = ""))} />
            <button
              type="button"
              onClick={() => pick.current?.click()}
              className="grid size-8 place-items-center rounded-md text-ink-2 transition hover:bg-black/10 dark:hover:bg-white/10"
              aria-label="문서 첨부"
            >
              <IconPaperclip className="size-4" />
            </button>
          </>
        }
        top={
          files.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {files.map((f, i) => (
                <Chip key={i} className="bg-page/70 py-1 pr-1.5 text-ink">
                  <IconFileText className="size-3.5" />
                  {f.name}
                  <button onClick={() => setFiles((x) => x.filter((_, j) => j !== i))} className="rounded-full p-0.5 hover:bg-soft" aria-label="빼기">
                    <IconX className="size-3" />
                  </button>
                </Chip>
              ))}
            </div>
          ) : undefined
        }
      />
      <SourceDrawer path={src} onClose={() => setSrc(null)} />
    </div>
  );
}

function Turn({ r, state, refresh, go, onSource }: { r: MineRun; state: State; refresh: () => void; go: (h: string) => void; onSource: (p: string) => void }) {
  const [more, setMore] = useState(false);
  const art = state.articles.find((a) => a.id === r.article);
  const canSwap = !!art && art.steps.length === 0; // 이미 쓰기 시작한 글은 원문을 바꾸지 않는다
  const now = r.picked.map((p) => p.source);
  const swap = (next: string[]) => act("mine-swap", { id: r.id, sources: next }).then(refresh);
  const running = r.status === "running";
  const stopped = r.status === "failed" || r.status === "lost";
  const step = STEPS.indexOf(r.stage as (typeof STEPS)[number]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-violet-500/20 px-4 py-3 text-[15px] leading-relaxed whitespace-pre-line text-violet-950 dark:text-violet-50">
          {r.message}
          {(r.docs.length > 0 || r.target) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {r.target && <Chip className="border-violet-400/40 bg-page/50 text-ink">{r.target}</Chip>}
              {r.docs.map((d) => (
                <Chip key={d} className="border-violet-400/40 bg-page/50 text-ink">
                  <IconFileText className="size-3.5" />
                  {d}
                </Chip>
              ))}
            </div>
          )}
        </div>
      </div>

      {running && (
        <div className="flex items-center gap-4 pl-1">
          <div className="flex items-center gap-1.5">
            {STEPS.map((s, i) => (
              <span key={s} className={cn("h-1.5 w-8 rounded-full", i < step ? "bg-violet-400" : i === step ? "animate-pulse bg-violet-400/70" : "bg-ink/10")} />
            ))}
          </div>
          <AITextLoading texts={STAGE_TEXT[r.stage] ?? ["…"]} className="text-sm font-medium" wrapperClassName="p-0 justify-start" />
        </div>
      )}

      {stopped && (
        <button onClick={() => openLog(r.job)} className="pl-1 text-left text-sm text-rose-600 hover:underline dark:text-rose-300">
          멈춤 · 로그
        </button>
      )}

      {r.picked.length > 0 && !running && (
        <div className="overflow-hidden rounded-2xl border border-line bg-panel-solid">
          {r.picked.map((p, i) => (
            <Row key={p.source} p={p} first={i === 0} onSource={onSource}>
              {canSwap && i > 0 && (
                <>
                  <IconBtn label="중심으로" onClick={() => swap([p.source, ...now.filter((x) => x !== p.source)])}>
                    <IconCrown className="size-4" />
                  </IconBtn>
                  <IconBtn label="빼기" onClick={() => swap(now.filter((x) => x !== p.source))}>
                    <IconMinus className="size-4" />
                  </IconBtn>
                </>
              )}
            </Row>
          ))}
          <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3.5">
            {r.rest.length > 0 ? (
              <button onClick={() => setMore((m) => !m)} className="flex items-center gap-1.5 text-sm text-ink-2 hover:text-ink">
                후보 {r.rest.length}
                <IconChevronDown className={cn("size-4 transition", more && "rotate-180")} />
              </button>
            ) : (
              <span />
            )}
            {r.article && (
              <button
                onClick={() => go(`#/a/${r.article}/title`)}
                className="flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-page transition hover:bg-violet-500 hover:text-white"
              >
                {art?.title || art?.steps.length ? "글" : "제목 고르기"}
                <IconArrowRight className="size-4" />
              </button>
            )}
          </div>
          {more && (
            <div className="border-t border-line bg-soft/40">
              {r.rest.map((p) => (
                <Row key={p.source} p={p} onSource={onSource}>
                  {canSwap && (
                    <>
                      <IconBtn label="중심으로" onClick={() => swap([p.source, ...now])}>
                        <IconCrown className="size-4" />
                      </IconBtn>
                      <IconBtn label="넣기" onClick={() => swap([...now, p.source])}>
                        <IconPlus className="size-4" />
                      </IconBtn>
                    </>
                  )}
                </Row>
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

function Row({ p, first, onSource, children }: { p: MineRow; first?: boolean; onSource: (p: string) => void; children?: React.ReactNode }) {
  const site = p.source.split("/")[0];
  return (
    <div className="group flex gap-4 border-t border-line px-5 py-4 first:border-t-0">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {p.kind !== "후보" && (
            <Chip className={first ? "border-violet-400/50 bg-violet-500/20 text-violet-800 dark:text-violet-100" : "text-ink"}>{p.kind}</Chip>
          )}
          {p.side === "반대편" && <Chip className="border-amber-400/40 bg-amber-500/10 text-amber-800 dark:text-amber-200">반대편</Chip>}
          <button onClick={() => onSource(p.path)} className="flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink">
            <SiteIcon site={site} className="size-3.5" />
            {p.source} · {p.who}
          </button>
        </div>
        <p className="mt-2 text-[15px] leading-relaxed text-ink">{p.role}</p>
        {p.out ? (
          <p className="mt-1 text-[13.5px] leading-relaxed text-ink-3">{p.out}</p>
        ) : (
          p.note && <p className="mt-1 line-clamp-2 text-[13.5px] leading-relaxed text-ink-3">{p.note}</p>
        )}
      </div>
      {children && <div className="flex shrink-0 items-start gap-1 opacity-0 transition group-hover:opacity-100">{children}</div>}
    </div>
  );
}

function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} className="grid size-8 place-items-center rounded-full border border-line text-ink-2 transition hover:bg-soft hover:text-ink">
      {children}
    </button>
  );
}
