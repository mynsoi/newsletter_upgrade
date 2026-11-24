import { useEffect, useState } from "react";
import { IconDownload, IconExternalLink, IconEye, IconHeart, IconMail, IconMessage, IconSend } from "@tabler/icons-react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { PillTabs } from "@/components/ui/tabs";
import { Chip } from "@/components/studio/bits";
import { Cover } from "@/views/Articles";
import { act, articleTitle, getReaderStats, getSiteComments, img, openLog, runningJob, type Article, type CommentMode, type ReaderStats, type SiteComment, type SiteComments, type State } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * 발행 — 글 화면에서 확정한 칼럼만 모인다.
 * 고르면 publish/<글>/에 발행본을 만들어(scripts/publish.py build) 웹·메일 모양을 미리 보고,
 * 발행을 누르면 웹(site/ 커밋·푸시 → Vercel) + 이미지 메일(.eml)을 만든다(release). 메일은 .eml을 Outlook에서 열어 보낸다.
 */

const pubUrl = (k: string, f: string, v: number) => `/publish/${encodeURIComponent(k)}/${f}?v=${v}`;
const split = (s: string) => s.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
const heroOf = (a: Article) => a.confirmed?.hero || a.hero;

export default function Publish({ state, id, refresh, go }: { state: State; id?: string; refresh: () => void; go: (h: string) => void }) {
  const list = state.articles.filter((a) => a.confirmed).sort((x, y) => (y.confirmed!.date + y.at).localeCompare(x.confirmed!.date + x.at));
  const a = list.find((x) => x.id === id) ?? list[0];
  // 발행 사이트의 조회수·좋아요 — 탭을 열 때와 1분마다(서버도 1분에 한 번만 DB를 읽는다)
  const [stats, setStats] = useState<ReaderStats>({});
  useEffect(() => {
    const load = () => getReaderStats().then(setStats);
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="flex min-h-screen">
      <aside className="w-80 shrink-0 border-r border-line px-5 py-10">
        <h1 className="mb-8 px-2 text-4xl font-bold tracking-tight text-ink">
          발행 <span className="tabular-nums text-ink-3">{list.length}</span>
        </h1>
        <div className="space-y-1.5">
          {list.map((x) => (
            <button
              key={x.id}
              onClick={() => go(`#/publish/${x.id}`)}
              className={cn("flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-soft", a?.id === x.id && "bg-soft")}
            >
              <span className="relative size-14 shrink-0 overflow-hidden rounded-lg">
                {heroOf(x) ? <img src={img(heroOf(x), 160)} className="size-full object-cover" /> : <Cover a={x} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="line-clamp-2 text-sm font-medium leading-snug text-ink">{articleTitle(x)}</span>
                {/* 확정·발행 날짜는 각각 한 덩어리로 — 좁으면 덩어리째 다음 줄로(2026-10-27: '발행 2026-10-' / '26'으로 끊겼다) */}
                <span className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-ink-3">
                  <span className="whitespace-nowrap">확정 {x.confirmed!.date}</span>
                  {x.published && <Chip className="whitespace-nowrap border-emerald-300/40 bg-emerald-500/15 py-0 text-emerald-700 dark:text-emerald-200">발행 {x.published.date}</Chip>}
                  {x.published && stats[x.id] && (
                    <span className="whitespace-nowrap tabular-nums">
                      조회 {stats[x.id].views.toLocaleString()} · 좋아요 {stats[x.id].likes.toLocaleString()}
                      {stats[x.id].comments ? ` · 댓글 ${stats[x.id].comments!.toLocaleString()}` : ""}
                      {stats[x.id].pending ? <span className="text-amber-600 dark:text-amber-300"> · 승인 대기 {stats[x.id].pending}</span> : null}
                    </span>
                  )}
                </span>
              </span>
            </button>
          ))}
          {!list.length && <p className="px-2 text-sm text-ink-3">확정한 글 없음</p>}
        </div>
      </aside>
      {a && <Detail key={a.id} a={a} state={state} refresh={refresh} stat={stats[a.id]} />}
    </div>
  );
}

/** 최근 14일 날짜별 조회수 막대 — 기록이 없는 날은 0. 날짜는 한국 기준(서버가 세는 날짜와 같게) */
function ViewBars({ days }: { days: [string, number][] }) {
  const [hover, setHover] = useState<number | null>(null);
  const by = new Map(days);
  const now = Date.now() + 9 * 3600 * 1000;
  const row = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(now - (13 - i) * 86400 * 1000).toISOString().slice(0, 10);
    return [d, by.get(d) ?? 0] as const;
  });
  const max = Math.max(1, ...row.map(([, n]) => n));
  const label = (d: string) => `${+d.slice(5, 7)}월 ${+d.slice(8)}일 (${"일월화수목금토"[new Date(d + "T00:00:00Z").getUTCDay()]})`;
  return (
    <div>
      {/* 막대 위에 그날 조회수(2026-11-20 — 막대만으로는 값을 알 수 없었다). 0인 날은 숫자를 적지 않는다. 1,000부터는 '1.2천'처럼 줄여 적는다.
          마우스를 올리면 날짜·조회수 말풍선(브라우저 기본 툴팁 대신) — 양 끝 막대에서는 카드 밖으로 나가지 않게 안쪽으로 붙인다 */}
      <div className="relative" onMouseLeave={() => setHover(null)}>
        {hover !== null && (
          <div
            className="pointer-events-none absolute bottom-full z-10 mb-1.5 whitespace-nowrap rounded-lg bg-neutral-900 px-2.5 py-1.5 text-xs shadow-lg ring-1 ring-white/10 dark:bg-neutral-100 dark:ring-black/10"
            style={{ left: `${((hover + 0.5) / 14) * 100}%`, transform: `translateX(${hover < 2 ? "-20%" : hover > 11 ? "-80%" : "-50%"})` }}
          >
            <div className="text-neutral-400 dark:text-neutral-500">{label(row[hover][0])}</div>
            <div className="mt-0.5 flex items-center gap-1.5 font-semibold tabular-nums text-white dark:text-neutral-900">
              <span className="size-2 rounded-full bg-emerald-400 dark:bg-emerald-600" />
              조회 {row[hover][1].toLocaleString()}
            </div>
          </div>
        )}
        <div className="flex h-16 gap-1" role="img" aria-label="최근 14일 날짜별 조회수">
          {row.map(([d, n], i) => (
            <div key={d} onMouseEnter={() => setHover(i)} className="flex min-w-0 flex-1 cursor-default flex-col">
              <div className="flex min-h-0 flex-1 flex-col justify-end">
                {n > 0 && (
                  <span className="mb-1 self-center whitespace-nowrap text-[10px] font-medium leading-none tabular-nums text-ink-2">
                    {n < 1000 ? n : new Intl.NumberFormat("ko", { notation: "compact", maximumFractionDigits: 1 }).format(n)}
                  </span>
                )}
                <div
                  className={cn(
                    "w-full shrink-0 rounded-sm transition-colors",
                    n ? (hover === i ? "bg-emerald-500 dark:bg-emerald-300" : "bg-emerald-600/70 dark:bg-emerald-400/70") : hover === i ? "bg-ink-3" : "bg-line"
                  )}
                  style={{ height: n ? `${Math.max(4, (n / max) * 46)}px` : "2px" }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-1 flex justify-between text-xs tabular-nums text-ink-3">
        <span>{row[0][0].slice(5)}</span>
        <span>최근 14일 조회</span>
        <span>{row[13][0].slice(5)}</span>
      </div>
    </div>
  );
}

const MODES: { value: CommentMode; title: string; hint: string }[] = [
  { value: "open", title: "바로 공개", hint: "등록하면 바로 보입니다." },
  { value: "moderated", title: "승인 뒤 공개", hint: "여기서 승인한 댓글만 보입니다." },
  { value: "closed", title: "닫힘", hint: "새 댓글을 받지 않습니다. 있던 댓글은 그대로 보입니다." },
];
const commentTime = (at: string) =>
  new Date(at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });

/**
 * 발행 사이트의 댓글 — 글 하나의 댓글(숨긴 것·승인 대기 포함)을 보고 숨기기·되살리기·승인한다(scripts/reader_stats.py).
 * 받는 방식(바로 공개·승인 뒤 공개·닫힘)은 사이트 전체 설정이라 어느 글에서 바꿔도 모든 글에 적용된다.
 * 1분마다 다시 읽는다. 쓴 사람이 지운 댓글은 여기에도 나오지 않는다.
 */
function Comments({ id }: { id: string }) {
  const [data, setData] = useState<SiteComments | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => getSiteComments(id).then(setData);
  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [id]);
  const run = async (name: string, body: Record<string, unknown>) => {
    setBusy(true);
    setErr("");
    await act(name, body).catch((e) => setErr(e.message));
    await load();
    setBusy(false);
  };
  if (!data) return null;
  if (!data.ready)
    return (
      <div className="rounded-2xl border border-line p-5 text-sm text-ink-3">
        <div className="font-medium text-ink">댓글</div>
        <p className="mt-1">댓글을 아직 읽을 수 없습니다 — DB에 댓글 표가 적용되기 전이거나 연결이 끊겼습니다.</p>
      </div>
    );
  const pending = data.comments.filter((c) => c.status === "pending").length;
  const shown = data.comments.filter((c) => c.status === "visible").length;
  return (
    <div className="rounded-2xl border border-line p-5 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium text-ink">댓글 <span className="tabular-nums text-ink-3">{shown}</span></span>
        {pending > 0 && <Chip className="border-amber-300/40 bg-amber-500/15 py-0 text-amber-700 dark:text-amber-200">승인 대기 {pending}</Chip>}
      </div>
      <div className="mt-3 flex rounded-full border border-line p-0.5" role="group" aria-label="댓글 받는 방식">
        {MODES.map((m) => (
          <button
            key={m.value}
            disabled={busy}
            aria-pressed={data.mode === m.value}
            onClick={() => data.mode !== m.value && run("comment-mode", { mode: m.value })}
            className={cn("flex-1 whitespace-nowrap rounded-full px-2 py-1.5 text-xs font-medium transition", data.mode === m.value ? "bg-soft text-ink" : "text-ink-3 hover:text-ink")}
          >
            {m.title}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-3">{MODES.find((m) => m.value === data.mode)!.hint} 모든 글에 적용됩니다.</p>
      {err && <p className="mt-2 text-xs text-rose-600 dark:text-rose-300">{err}</p>}
      {data.comments.length > 0 ? (
        <ul className="mt-3 max-h-[28rem] space-y-3 overflow-y-auto border-t border-line pt-3">
          {data.comments.map((c) => (
            <CommentRow key={c.id} c={c} busy={busy} set={(status) => run("comment-set", { comment: c.id, status })} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 border-t border-line pt-3 text-ink-3">아직 댓글이 없습니다.</p>
      )}
    </div>
  );
}

function CommentRow({ c, busy, set }: { c: SiteComment; busy: boolean; set: (status: "visible" | "hidden") => void }) {
  const btn = "rounded-full border border-line px-2.5 py-1 text-xs font-medium text-ink-2 transition hover:border-ink-3 hover:text-ink disabled:opacity-40";
  return (
    <li className={cn("rounded-xl p-3", c.status === "hidden" ? "bg-soft/50" : c.status === "pending" ? "bg-amber-500/10" : "bg-soft")}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className={cn("min-w-0 break-all font-medium", c.status === "hidden" ? "text-ink-3" : "text-ink")}>{c.name}</span>
        <span className="whitespace-nowrap text-xs tabular-nums text-ink-3">{commentTime(c.at)}</span>
        {c.status === "hidden" && <Chip className="py-0 text-ink-3">숨김</Chip>}
        {c.status === "pending" && <Chip className="border-amber-300/40 bg-amber-500/15 py-0 text-amber-700 dark:text-amber-200">승인 대기</Chip>}
      </div>
      <p className={cn("mt-1 whitespace-pre-wrap break-words leading-relaxed", c.status === "hidden" ? "text-ink-3 line-through decoration-ink-3/40" : "text-ink-2")}>{c.body}</p>
      <div className="mt-2 flex gap-1.5">
        {c.status === "pending" && <button disabled={busy} onClick={() => set("visible")} className={btn}>승인</button>}
        {c.status !== "hidden" && <button disabled={busy} onClick={() => set("hidden")} className={btn}>숨기기</button>}
        {c.status === "hidden" && <button disabled={busy} onClick={() => set("visible")} className={btn}>되살리기</button>}
      </div>
    </li>
  );
}

function Detail({ a, state, refresh, stat }: { a: Article; state: State; refresh: () => void; stat?: ReaderStats[string] }) {
  const [view, setView] = useState("web");
  const [v, setV] = useState(0); // 미리보기를 다시 만들 때마다 iframe을 새로 불러온다
  const [err, setErr] = useState("");
  const [to, setTo] = useState((a.published?.to ?? state.publish?.to ?? []).join(", "));
  const [cc, setCc] = useState((a.published?.cc ?? state.publish?.cc ?? []).join(", "));
  const [arm, setArm] = useState(false);
  const job = runningJob(state.jobs, "publish", a.id);
  const last = state.jobs.find((j) => j.kind === "publish" && j.target === a.id);

  const build = () =>
    act("publish-build", { article: a.id })
      .then(() => (setErr(""), setV(Date.now())))
      .catch((e) => setErr(e.message));
  useEffect(() => {
    build();
  }, [a.id, a.confirmed?.file, a.published?.date]);
  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => setArm(false), 3000);
    return () => clearTimeout(t);
  }, [arm]);

  const publish = async () => {
    if (!arm) return setArm(true);
    setArm(false);
    await act("publish", { article: a.id, to: split(to), cc: split(cc) }).catch(() => null);
    refresh();
  };

  return (
    <div className="min-w-0 flex-1 px-10 py-10">
      <div className="mb-6 flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="text-sm text-ink-3">
            확정 {a.confirmed!.date}
            {a.confirmed!.step ? ` · 과정 ${a.confirmed!.step}` : ""}
          </div>
          <h2 className="mt-1 text-2xl font-bold leading-snug tracking-tight text-ink">{articleTitle(a)}</h2>
        </div>
        <PillTabs
          id="publish-view"
          tabs={[
            { value: "web", title: "웹" },
            { value: "mail", title: "메일" },
          ]}
          value={view}
          onChange={setView}
        />
      </div>

      <div className="flex gap-8">
        <div className="min-w-0 flex-1">
          {err ? (
            <div className="rounded-2xl border border-rose-400/40 p-6 text-sm text-rose-600 dark:text-rose-300">{err}</div>
          ) : v ? (
            <div className={cn("overflow-hidden rounded-2xl border border-line bg-white", view === "mail" && "mx-auto w-[800px] max-w-none")}>
              <iframe key={view + v} title="미리보기" src={pubUrl(a.id, view === "web" ? "index.html" : "email.html", v)} className="h-[calc(100vh-11rem)] w-full" />
            </div>
          ) : (
            <AITextLoading texts={["발행본 만드는 중"]} className="text-sm" wrapperClassName="justify-start p-0" />
          )}
        </div>

        <div className="w-80 shrink-0 space-y-5">
          <div className="rounded-2xl border border-line p-5">
            <label className="block text-sm font-medium text-ink">받는 사람</label>
            <textarea value={to} onChange={(e) => setTo(e.target.value)} rows={2} placeholder="a@sk.com, b@sk.com"
              className="mt-2 w-full resize-none rounded-xl border border-line bg-transparent px-3 py-2 text-sm text-ink outline-none focus:border-ink-3" />
            <label className="mt-3 block text-sm font-medium text-ink">참조</label>
            <textarea value={cc} onChange={(e) => setCc(e.target.value)} rows={1}
              className="mt-2 w-full resize-none rounded-xl border border-line bg-transparent px-3 py-2 text-sm text-ink outline-none focus:border-ink-3" />
            {job ? (
              <button onClick={() => openLog(job.id)} className="mt-4 flex w-full items-center justify-center rounded-full border border-line px-4 py-2.5">
                <AITextLoading texts={["캡처하는 중", "메일 만드는 중", "커밋·푸시 중"]} className="text-sm" wrapperClassName="p-0" />
              </button>
            ) : (
              <button
                onClick={publish}
                disabled={!!err || !v || !split(to).length}
                className={cn(
                  "mt-4 flex w-full items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold transition disabled:opacity-40",
                  arm ? "bg-rose-500 text-white" : "bg-[#0B6E4F] text-white hover:opacity-90"
                )}
              >
                <IconSend className="size-4" />
                {arm ? "한 번 더 누르면 발행" : a.published ? "다시 발행" : "발행"}
              </button>
            )}
            {last?.status === "failed" && (
              <button onClick={() => openLog(last.id)} className="mt-2 text-xs text-rose-600 hover:underline dark:text-rose-300">
                지난 발행이 실패했습니다 — 로그 보기
              </button>
            )}
          </div>

          {a.published && (
            <div className="space-y-2 rounded-2xl border border-emerald-400/30 bg-emerald-500/5 p-5 text-sm">
              <div className="font-medium text-ink">발행 {a.published.date}</div>
              {stat && (
                <div className="space-y-3 border-b border-emerald-400/20 pb-3">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 tabular-nums text-ink">
                    <span className="flex items-center gap-1.5"><IconEye className="size-4 shrink-0 text-ink-3" /> 조회 {stat.views.toLocaleString()}</span>
                    <span className="flex items-center gap-1.5"><IconHeart className="size-4 shrink-0 text-ink-3" /> 좋아요 {stat.likes.toLocaleString()}</span>
                    <span className="flex items-center gap-1.5"><IconMessage className="size-4 shrink-0 text-ink-3" /> 댓글 {(stat.comments ?? 0).toLocaleString()}</span>
                  </div>
                  <ViewBars days={stat.days} />
                </div>
              )}
              {a.published.url ? (
                <a href={a.published.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-ink-2 hover:text-ink">
                  <IconExternalLink className="size-4 shrink-0" /> <span className="truncate">{a.published.url}</span>
                </a>
              ) : (
                <div className="text-ink-3">웹 주소 없음 (config/publish.json web_base_url)</div>
              )}
              <a href={pubUrl(a.id, "newsletter.eml", v)} className="flex items-center gap-2 text-ink-2 hover:text-ink">
                <IconDownload className="size-4 shrink-0" /> 메일 파일(.eml)
              </a>
              <div className="flex items-start gap-2 text-ink-3">
                <IconMail className="mt-0.5 size-4 shrink-0" /> {[...a.published.to, ...a.published.cc].join(", ")}
              </div>
            </div>
          )}
          {a.published && <Comments id={a.id} />}
        </div>
      </div>
    </div>
  );
}
