import { useRef, useState } from "react";
import { IconArrowRight, IconChevronDown, IconCrown, IconFileText, IconMinus, IconPaperclip, IconPlus, IconRefresh, IconUsers, IconX } from "@tabler/icons-react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import { Chip, SiteIcon } from "@/components/studio/bits";
import { act, type Job, type MineRow, type MineRun, type State, type WikiTopic } from "@/lib/api";
import { hue } from "@/lib/text";
import { cn } from "@/lib/utils";

/** 내 주제로 쓰기 — 메인 화면은 들어올 때마다 새 채팅(멘토 2026-10-11: "새 들어갈때마다 초기화", "채팅하던거는 왼쪽으로").
 *  보내면 그 대화의 글 화면(views/Flow)으로 가고, 대화는 왼쪽 목록에 쌓인다. */

export const TARGET_MODES = [
  { id: "auto", label: "독자 자동", icon: <IconUsers className="size-3.5 text-violet-300" /> },
  ...["전 직원", "팀장급", "사수급", "신입사원"].map((t) => ({ id: t, label: t, icon: <IconUsers className="size-3.5 text-violet-300" /> })),
];
export const ACCEPT = ".pdf,.docx,.doc,.hwp,.hwpx,.odt,.rtf,.txt,.md";

export const toB64 = (f: File) =>
  new Promise<{ name: string; data: string }>((ok, no) => {
    const r = new FileReader();
    r.onload = () => ok({ name: f.name, data: String(r.result).split(",")[1] ?? "" });
    r.onerror = () => no(r.error);
    r.readAsDataURL(f);
  });

/** 첨부 — 클립 버튼 + 끌어 놓기 + 파일 칩 */
export function useAttach() {
  const [files, setFiles] = useState<File[]>([]);
  const [drag, setDrag] = useState(false);
  const pick = useRef<HTMLInputElement>(null);
  const add = (l: FileList | null) => l && setFiles((f) => [...f, ...Array.from(l)]);
  const drop = {
    onDragOver: (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(true);
    },
    onDragLeave: () => setDrag(false),
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      add(e.dataTransfer.files);
    },
  };
  const tool = (
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
  );
  const chips =
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
    ) : undefined;
  return { files, clear: () => setFiles([]), drag, drop, tool, chips, encode: () => Promise.all(files.map(toB64)) };
}

export default function NewChat({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const [target, setTarget] = useState("auto");
  const at = useAttach();
  const send = async (v: string) => {
    const j = await act<Job>("mine", { message: v, target: target === "auto" ? "" : target, files: await at.encode() });
    at.clear();
    refresh();
    if (j?.target) go(`#/a/${j.target}`);
  };
  return (
    <div {...at.drop} className={cn("rounded-3xl transition", at.drag && "ring-2 ring-violet-400/70 ring-offset-8 ring-offset-transparent")}>
      <Suggest state={state} go={go} />
      <AI_Prompt
        className="w-full py-2"
        modes={TARGET_MODES}
        mode={target}
        onModeChange={setTarget}
        placeholder="어떤 글을 쓸까요?"
        onSubmit={send}
        tools={at.tool}
        top={at.chips}
      />
    </div>
  );
}

/** 추천 주제 — 채팅창 위 (멘토 2026-10-11: "글 작성할때 추천 주제를 먼저 채팅창위에 몇개 띄워주면 좋겠네").
 *  주제 지도에서 Claude가 '쓸 만함'으로 거른 주제 중 아직 안 쓴 것. 4개씩, '다른 추천'으로 다음 4개(전부 돌아가며).
 *  누르면 주제 지도의 '이 주제로'와 같다 — 글 설정을 만들고 대화 화면으로(미리 뽑아 둔 제목 후보가 바로 뜸). */
const PER = 4;
function Suggest({ state, go }: { state: State; go: (h: string) => void }) {
  const list = (state.wiki?.topics ?? [])
    .filter((x) => x.verdict === "쓸 만함" && x.status === "쓸 수 있음")
    .sort((a, b) => b.sources.length - a.sources.length);
  const [at, setAt] = useState(0);
  const [pending, setPending] = useState("");
  if (!list.length) return null;
  const start = (at * PER) % list.length;
  const shown = Array.from({ length: Math.min(PER, list.length) }, (_, i) => list[(start + i) % list.length]);
  const pick = async (x: WikiTopic) => {
    if (pending) return;
    setPending(x.page);
    try {
      const r = await act<{ article: string }>("wiki-pick", { page: x.page });
      go(`#/a/${r.article}`);
    } finally {
      setPending("");
    }
  };
  return (
    <div className="mb-3">
      <div className="grid grid-cols-2 gap-2.5">
        {shown.map((x) => (
          <button
            key={x.page}
            onClick={() => pick(x)}
            className="group relative overflow-hidden rounded-2xl border border-line bg-panel-solid/80 px-4 py-3.5 text-left backdrop-blur transition hover:-translate-y-0.5 hover:border-violet-400/50"
          >
            <span
              className="pointer-events-none absolute inset-0 opacity-40 transition group-hover:opacity-70"
              style={{ background: `radial-gradient(120% 140% at 0% 0%, hsl(${hue(x.title)} 70% 45% / .25), transparent 60%)` }}
            />
            <span className="relative flex items-center gap-1.5">
              {(x.audience || "").split("·").filter(Boolean).map((a) => (
                <Chip key={a} className="bg-page/60 px-2 py-0 text-[11px] text-ink-2">{a.trim()}</Chip>
              ))}
              {pending === x.page ? (
                <AITextLoading texts={["여는 중"]} className="ml-auto text-xs" wrapperClassName="p-0 ml-auto" />
              ) : (
                <IconArrowRight className="ml-auto size-4 text-ink-3 opacity-0 transition group-hover:opacity-100" />
              )}
            </span>
            <span className="relative mt-2 line-clamp-2 text-[14px] leading-snug text-ink [word-break:keep-all]">{x.title}</span>
          </button>
        ))}
      </div>
      {list.length > PER && (
        <div className="mt-2 flex justify-end">
          <button onClick={() => setAt((n) => n + 1)} className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs text-ink-3 transition hover:bg-soft hover:text-ink">
            <IconRefresh className="size-3.5" />
            다른 추천
          </button>
        </div>
      )}
    </div>
  );
}

/** 고른 원문 카드 — 마지막 차례는 바꿔 끼우기(중심으로·넣기·빼기)가 되고, 지난 차례는 굳힌 채로 */
export function PicksCard({
  run,
  canSwap,
  footer,
  onSource,
  refresh,
}: {
  run: MineRun;
  canSwap: boolean;
  footer?: React.ReactNode;
  onSource: (p: string) => void;
  refresh: () => void;
}) {
  const [more, setMore] = useState(false);
  const now = run.picked.map((p) => p.source);
  const swap = (next: string[]) => act("mine-swap", { id: run.id, sources: next }).then(refresh);
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-panel-solid">
      {run.picked.map((p, i) => (
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
        {run.rest.length > 0 ? (
          <button onClick={() => setMore((m) => !m)} className="flex items-center gap-1.5 text-sm text-ink-2 hover:text-ink">
            후보 {run.rest.length}
            <IconChevronDown className={cn("size-4 transition", more && "rotate-180")} />
          </button>
        ) : (
          <span />
        )}
        {footer}
      </div>
      {more && (
        <div className="border-t border-line bg-soft/40">
          {run.rest.map((p) => (
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
  );
}

export function Row({ p, first, onSource, children }: { p: MineRow; first?: boolean; onSource: (p: string) => void; children?: React.ReactNode }) {
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

export function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} className="grid size-8 place-items-center rounded-full border border-line text-ink-2 transition hover:bg-soft hover:text-ink">
      {children}
    </button>
  );
}
