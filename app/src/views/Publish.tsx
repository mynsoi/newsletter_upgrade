import { useEffect, useState } from "react";
import { IconDownload, IconExternalLink, IconEye, IconHeart, IconMail, IconSend } from "@tabler/icons-react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { PillTabs } from "@/components/ui/tabs";
import { Chip } from "@/components/studio/bits";
import { Cover } from "@/views/Articles";
import { act, articleTitle, getReaderChat, getReaderStats, img, openLog, runningJob, type Article, type ChatMode, type ReaderChat, type ReaderStats, type State } from "@/lib/api";
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
                    <span className="whitespace-nowrap tabular-nums">조회 {stats[x.id].views.toLocaleString()} · 좋아요 {stats[x.id].likes.toLocaleString()}</span>
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

const CHAT_MODES: { value: ChatMode; title: string; hint: string }[] = [
  { value: "off", title: "꺼짐", hint: "글 페이지에 질문 버튼이 보이지 않습니다." },
  { value: "test", title: "시험", hint: "글 주소 끝에 ?chat=1을 붙인 사람에게만 버튼이 보입니다." },
  { value: "on", title: "켜짐", hint: "모든 독자에게 질문 버튼이 보입니다." },
];
const CHAT_DAILY = 300; // 사이트 전체 하루 상한(migrations/017의 site_chat_begin과 같은 값)
const chatTime = (at: string) =>
  new Date(at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });

/**
 * 발행 사이트의 챗봇 — 켜기·시험·끄기(사이트 전체)와 이 글에 들어온 독자 질문·답변(scripts/reader_stats.py chat).
 * 독자는 글 페이지 오른쪽 아래 '이 글에 대해 물어보기'로 묻고, 그 글과 참고 원문을 근거로 한 답을 받는다(api/chat.py).
 * 1분마다 다시 읽는다. 누가 물었는지는 기록하지 않는다.
 */
function Chatbot({ id }: { id: string }) {
  const [data, setData] = useState<ReaderChat | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const load = () => getReaderChat(id).then(setData);
  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [id]);
  const setMode = async (mode: ChatMode) => {
    setBusy(true);
    setErr("");
    await act("chat-mode", { mode }).catch((e) => setErr(e.message));
    await load();
    setBusy(false);
  };
  if (!data) return null;
  if (!data.ready)
    return (
      <div className="rounded-2xl border border-line p-5 text-sm text-ink-3">
        <div className="font-medium text-ink">챗봇</div>
        <p className="mt-1">챗봇을 아직 쓸 수 없습니다 — DB에 챗봇 표가 적용되기 전이거나 연결이 끊겼습니다.</p>
      </div>
    );
  return (
    <div className="rounded-2xl border border-line p-5 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium text-ink">챗봇</span>
        <span className="ml-auto text-xs tabular-nums text-ink-3">오늘 질문 {data.today} / {CHAT_DAILY}</span>
      </div>
      <div className="mt-3 flex rounded-full border border-line p-0.5" role="group" aria-label="챗봇 켜기">
        {CHAT_MODES.map((m) => (
          <button
            key={m.value}
            disabled={busy}
            aria-pressed={data.mode === m.value}
            onClick={() => data.mode !== m.value && setMode(m.value)}
            className={cn("flex-1 whitespace-nowrap rounded-full px-2 py-1.5 text-xs font-medium transition", data.mode === m.value ? "bg-soft text-ink" : "text-ink-3 hover:text-ink")}
          >
            {m.title}
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-3">{CHAT_MODES.find((m) => m.value === data.mode)!.hint} 모든 글에 적용됩니다.</p>
      {!data.secret && (
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-200">
          비밀값이 아직 없어 켜도 답하지 못합니다 — python -I scripts/reader_stats.py chat-secret 으로 만들어 Vercel의 CHAT_SECRET에 넣어 주세요.
        </p>
      )}
      {!data.context && (
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-200">
          이 글은 근거 자료가 없어 질문 버튼이 보이지 않습니다 — 원고와 원문이 있는 PC에서 python -I scripts/publish.py refresh 를 돌려 주세요.
        </p>
      )}
      {err && <p className="mt-2 text-xs text-rose-600 dark:text-rose-300">{err}</p>}
      <div className="mt-3 border-t border-line pt-3">
        <div className="text-xs font-medium text-ink-2">이 글의 독자 질문 <span className="tabular-nums text-ink-3">{data.questions.length}</span></div>
        {data.questions.length > 0 ? (
          <ul className="mt-2 max-h-[28rem] space-y-2 overflow-y-auto">
            {data.questions.map((x) => (
              <li key={x.id} className="rounded-xl bg-soft p-3">
                <button onClick={() => setOpen(open === x.id ? null : x.id)} aria-expanded={open === x.id} className="block w-full text-left">
                  <span className="block break-words font-medium leading-snug text-ink">{x.question}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs tabular-nums text-ink-3">
                    <span className="whitespace-nowrap">{chatTime(x.at)}</span>
                    {x.ms != null && <span className="whitespace-nowrap">{(x.ms / 1000).toFixed(1)}초</span>}
                    {x.status === "refused" && <Chip className="py-0">모델이 거절</Chip>}
                    {x.status === "error" && <Chip className="border-rose-300/40 bg-rose-500/15 py-0 text-rose-700 dark:text-rose-200">실패</Chip>}
                    {x.status === "started" && <Chip className="py-0">끊김</Chip>}
                    {x.dropped > 0 && <Chip className="border-amber-300/40 bg-amber-500/15 py-0 text-amber-700 dark:text-amber-200">원문 겹침 {x.dropped}문장 뺌</Chip>}
                  </span>
                </button>
                {open === x.id && <p className="mt-2 whitespace-pre-wrap break-words border-t border-line pt-2 leading-relaxed text-ink-2">{x.answer || "답변 없음"}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-ink-3">아직 질문이 없습니다.</p>
        )}
      </div>
    </div>
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
                  <div className="flex items-center gap-4 tabular-nums text-ink">
                    <span className="flex items-center gap-1.5"><IconEye className="size-4 shrink-0 text-ink-3" /> 조회 {stat.views.toLocaleString()}</span>
                    <span className="flex items-center gap-1.5"><IconHeart className="size-4 shrink-0 text-ink-3" /> 좋아요 {stat.likes.toLocaleString()}</span>
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
          {a.published && <Chatbot id={a.id} />}
        </div>
      </div>
    </div>
  );
}
