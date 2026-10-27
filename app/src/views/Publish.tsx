import { useEffect, useState } from "react";
import { IconDownload, IconExternalLink, IconMail, IconSend } from "@tabler/icons-react";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { PillTabs } from "@/components/ui/tabs";
import { Chip } from "@/components/studio/bits";
import { Cover } from "@/views/Articles";
import { act, articleTitle, img, openLog, runningJob, type Article, type State } from "@/lib/api";
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
                </span>
              </span>
            </button>
          ))}
          {!list.length && <p className="px-2 text-sm text-ink-3">확정한 글 없음</p>}
        </div>
      </aside>
      {a && <Detail key={a.id} a={a} state={state} refresh={refresh} />}
    </div>
  );
}

function Detail({ a, state, refresh }: { a: Article; state: State; refresh: () => void }) {
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
        </div>
      </div>
    </div>
  );
}
