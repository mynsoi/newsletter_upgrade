import { useRef, useState } from "react";
import { IconArrowRight, IconCheck, IconChevronDown, IconCrown, IconFileText, IconMinus, IconPaperclip, IconPlus, IconRefresh, IconUsers, IconX } from "@tabler/icons-react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import { Chip, SiteIcon } from "@/components/studio/bits";
import { act, type Job, type MineOption, type MineRow, type MineRun, type State, type WikiTopic } from "@/lib/api";
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

/** 글 옵션(2026-10-22) — 옵션마다 이 글이 말할 것 한 문장과 원문 2~3편. 마지막 차례면 '이 글로'로 하나를 고른다
 *  (고르면 그 옵션의 원문을 끝까지 읽고 확인한 뒤 고른 원문 카드·제목 후보가 이어진다). 지난 차례는 고른 것만 표시한 채로 */
export function OptionsCard({
  run,
  options,
  live,
  chosen,
  onSource,
  refresh,
}: {
  run: MineRun;
  options: MineOption[];
  live: boolean;
  chosen?: number;
  onSource: (p: string) => void;
  refresh: () => void;
}) {
  const take = (n: number) => act("mine-take", { id: run.id, n }).then(refresh);
  return (
    <div className={cn("space-y-2.5", !live && "opacity-70 transition hover:opacity-100")}>
      {options.map((o, i) => {
        const on = chosen === i + 1;
        return (
          <div key={i} className={cn("rounded-2xl border bg-panel-solid px-5 py-4", on ? "border-violet-400/60" : "border-line")}>
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-soft text-xs font-semibold text-ink-2">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[15.5px] font-medium leading-relaxed text-ink">{o.message}</p>
                {o.why && <p className="mt-1 text-[13px] leading-relaxed text-ink-3">{o.why}</p>}
                <div className="mt-3 space-y-1.5">
                  {[o.center, ...o.support].map((p, j) => (
                    <div key={p.source} className="flex gap-2.5 text-[13.5px] leading-relaxed">
                      <Chip className={cn("h-fit shrink-0 whitespace-nowrap", j === 0 && "border-violet-400/50 bg-violet-500/15 text-violet-800 dark:text-violet-100")}>
                        {j === 0 ? "중심" : "받침"}
                      </Chip>
                      <span className="min-w-0 text-ink-2">
                        <button onClick={() => onSource(p.path ?? "")} className="mr-2 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink">
                          <SiteIcon site={p.source.split("/")[0]} className="size-3.5" />
                          {p.who || p.source}
                        </button>
                        {p.role}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            {(live || on || o.audience) && (
              <div className="mt-3 flex items-center justify-between gap-3 border-t border-line pt-3">
                {o.audience ? <Chip className="text-ink-2">{o.audience}</Chip> : <span />}
                {live ? (
                  <button
                    onClick={() => take(i + 1)}
                    className="flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-page transition hover:bg-violet-500 hover:text-white"
                  >
                    이 글로
                    <IconArrowRight className="size-4" />
                  </button>
                ) : (
                  on && <Chip className="border-violet-400/50 bg-violet-500/15 text-violet-800 dark:text-violet-100">고름</Chip>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** 고른 원문 카드 (2026-10-22 개편: 확인 결과를 보고 승인하는 화면)
 *  맨 위 확인 결과 한 줄(+ Claude의 주의 메모) → 원문마다 맡는 몫 · 가져올 사실 → 기준(원문 2~3편 · 다른 발행처 1편 이상)과 경고
 *  → 바꿔 넣을 원문(다른 옵션의 원문은 그 옵션 메시지별로, 확인에서 뺀 원문은 이유와 함께). 버튼은 늘 보인다.
 *  마지막 차례만 바꿔 끼우기가 되고, 지난 차례는 굳힌 채로 */
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
  const [more, setMore] = useState(true);
  const now = run.picked.map((p) => p.source);
  const swap = (next: string[]) => act("mine-swap", { id: run.id, sources: next }).then(refresh);
  const sites = new Set(run.picked.map((p) => p.site || p.source.split("/")[0]));
  const warn =
    run.picked.length < 2
      ? "원문이 1편뿐입니다 — 한 편만으로 쓰면 그 글을 말만 바꿔 옮기게 됩니다. 아래에서 받침을 하나 넣어 보세요."
      : run.picked.length > 3
        ? "원문이 3편을 넘습니다 — 사례 나열이 되기 쉽습니다. 하나를 빼 보세요."
        : sites.size < 2
          ? "원문이 모두 같은 발행처입니다 — 다른 발행처 원문을 하나 넣어 보세요."
          : "";
  const groups: Record<string, MineRow[]> = {};
  for (const p of run.rest) (groups[p.group || "후보"] ??= []).push(p);
  const rank = (g: string) => (g === "추천 원문" ? 0 : g === "확인에서 뺀 원문" ? 2 : 1);
  const order = Object.keys(groups).sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  const ck = run.check;
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-panel-solid">
      {ck && (
        <div className="space-y-1.5 border-b border-line bg-soft/40 px-5 py-3.5 text-[13.5px] leading-relaxed">
          <p className="flex items-center gap-2 text-ink">
            <IconCheck className="size-4 shrink-0 text-emerald-500" />
            옵션 {ck.option}의 원문을 끝까지 읽고 확인했습니다
            {ck.dropped > 0 ? ` · 받치지 못하는 원문 ${ck.dropped}편을 뺐습니다` : " · 뺀 원문 없음"}
          </p>
          {ck.note && <p className="pl-6 text-ink-2">주의: {ck.note}</p>}
        </div>
      )}
      {run.picked.map((p, i) => (
        <Row key={p.source} p={p} first={i === 0} onSource={onSource}>
          {canSwap && i > 0 && (
            <>
              <TextBtn onClick={() => swap([p.source, ...now.filter((x) => x !== p.source)])}>
                <IconCrown className="size-3.5" /> 중심으로
              </TextBtn>
              <TextBtn onClick={() => swap(now.filter((x) => x !== p.source))}>
                <IconMinus className="size-3.5" /> 빼기
              </TextBtn>
            </>
          )}
        </Row>
      ))}
      {run.internal && <InternalRow ic={run.internal} canSwap={canSwap} id={run.id} refresh={refresh} />}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3.5">
        <span className={cn("text-[13px]", warn ? "text-amber-700 dark:text-amber-300" : "text-ink-3")}>
          {warn || `기준: 원문 2~3편 · 다른 발행처 1편 이상 — 지금 ${run.picked.length}편 · 발행처 ${sites.size}곳`}
        </span>
        {footer}
      </div>
      {run.rest.length > 0 && (
        <div className="border-t border-line">
          <button onClick={() => setMore((m) => !m)} className="flex w-full items-center gap-1.5 px-5 py-3 text-left text-sm text-ink-2 hover:text-ink">
            추천·바꿔 넣을 수 있는 원문 {run.rest.length}
            <IconChevronDown className={cn("size-4 transition", more && "rotate-180")} />
          </button>
          {more && (
            <div className="bg-soft/40">
              {order.map((g) => (
                <div key={g}>
                  <p className="border-t border-line px-5 pt-3 pb-1 text-[12.5px] font-medium text-ink-3">
                    {g}
                    {GROUP_NOTE[g] && <span className="ml-1.5 font-normal">— {GROUP_NOTE[g]}</span>}
                  </p>
                  {groups[g].map((p) => (
                    <Row key={p.source} p={p} onSource={onSource}>
                      {canSwap && (
                        <>
                          <TextBtn onClick={() => swap([p.source, ...now])}>
                            <IconCrown className="size-3.5" /> 중심으로
                          </TextBtn>
                          <TextBtn onClick={() => swap([...now, p.source])}>
                            <IconPlus className="size-3.5" /> 넣기
                          </TextBtn>
                        </>
                      )}
                    </Row>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** 사내 맥락(2026-10-23) — 고른 메시지에 맞는 사내 자료(경영층 메시지·SKMS·사내 안내) 대목 0~1개. 넣으면 초안이 한 곳에서 우리 회사 상황으로 옮겨 읽게 쓴다. */
function InternalRow({ ic, canSwap, id, refresh }: { ic: NonNullable<MineRun["internal"]>; canSwap: boolean; id: string; refresh: () => void }) {
  const [open, setOpen] = useState(false);
  const toggle = (on: boolean) => act("mine-internal", { id, on }).then(refresh);
  if (!ic.has)
    return (
      <div className="border-t border-line px-5 py-3.5 text-[13px] text-ink-3">
        <Chip className="mr-2 text-ink-3">사내 맥락</Chip>맞는 사내 자료 없음{ic.why && ` — ${ic.why}`}
      </div>
    );
  return (
    <div className={cn("border-t border-line px-5 py-4", !ic.on && "opacity-60")}>
      <div className="flex gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className="border-emerald-400/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200">사내 맥락</Chip>
            <span className="text-xs text-ink-3">{ic.on ? "넣음" : "뺌"}</span>
          </div>
          <p className="mt-1.5 text-[15px] font-semibold text-ink">{ic.label}</p>
          {ic.use && <p className="mt-1 text-[13.5px] leading-relaxed text-ink-2">쓸 방향 · {ic.use}</p>}
          {ic.fact && <p className="mt-1 text-[13.5px] leading-relaxed text-ink-2">쓸 사실 · {ic.fact}</p>}
          {ic.caution && <p className="mt-1 text-[13px] leading-relaxed text-amber-700 dark:text-amber-300">주의 · {ic.caution}</p>}
          <button onClick={() => setOpen((o) => !o)} className="mt-1.5 flex items-center gap-1 text-xs text-ink-3 hover:text-ink">
            대목 보기 <IconChevronDown className={cn("size-3.5 transition", open && "rotate-180")} />
          </button>
          {open && <p className="mt-1.5 whitespace-pre-wrap rounded-lg bg-soft/60 px-3 py-2 text-[13px] leading-relaxed text-ink-2">{ic.excerpt}</p>}
        </div>
        {canSwap && (
          <div className="flex shrink-0 flex-col items-end gap-1.5">
            {ic.on ? (
              <TextBtn onClick={() => toggle(false)}>
                <IconMinus className="size-3.5" /> 빼기
              </TextBtn>
            ) : (
              <TextBtn onClick={() => toggle(true)}>
                <IconPlus className="size-3.5" /> 넣기
              </TextBtn>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const GROUP_NOTE: Record<string, string> = {
  "추천 원문": "고른 메시지로 다시 검색한 카드에서 Claude가 골랐습니다(카드만 보고). 넣으면 그 원문을 끝까지 읽고 확인한 뒤 들어갑니다(약 30초)",
  "확인에서 뺀 원문": "원문을 끝까지 읽어 보니 이 글을 받치지 못해 뺐습니다",
};

export function Row({ p, first, onSource, children }: { p: MineRow; first?: boolean; onSource: (p: string) => void; children?: React.ReactNode }) {
  const site = p.source.split("/")[0];
  return (
    <div className="flex gap-4 border-t border-line px-5 py-4 first:border-t-0">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {p.kind !== "후보" && (
            <Chip className={first ? "border-violet-400/50 bg-violet-500/20 text-violet-800 dark:text-violet-100" : "text-ink"}>{p.kind}</Chip>
          )}
          {p.side === "반대편" && <Chip className="border-amber-400/40 bg-amber-500/10 text-amber-800 dark:text-amber-200">반대편</Chip>}
          <button onClick={() => onSource(p.path)} className="flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink">
            <SiteIcon site={site} className="size-3.5" />
            {p.site || p.source}
            {p.who && ` · ${p.who}`}
          </button>
        </div>
        <p className="mt-2 text-[15px] leading-relaxed text-ink">{p.role}</p>
        {p.use ? (
          <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-2">
            <span className="text-ink-3">가져올 사실 · </span>
            {p.use}
          </p>
        ) : p.out ? (
          <p className="mt-1 text-[13.5px] leading-relaxed text-ink-3">{p.out}</p>
        ) : (
          p.note && <p className="mt-1 line-clamp-2 text-[13.5px] leading-relaxed text-ink-3">{p.note}</p>
        )}
      </div>
      {children && <div className="flex shrink-0 flex-col items-end gap-1.5">{children}</div>}
    </div>
  );
}

function TextBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1 whitespace-nowrap rounded-full border border-line px-3 py-1 text-[12.5px] text-ink-2 transition hover:bg-soft hover:text-ink"
    >
      {children}
    </button>
  );
}

export function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} className="grid size-8 place-items-center rounded-full border border-line text-ink-2 transition hover:bg-soft hover:text-ink">
      {children}
    </button>
  );
}
