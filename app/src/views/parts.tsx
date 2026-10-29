import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { IconArrowDown, IconArrowUp } from "@tabler/icons-react";
import AI_Prompt from "@/components/kokonutui/ai-prompt";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import { ClaudeMark, MiniMd } from "@/components/studio/bits";
import { act, getChat, img, runningJob, type Article as A, type ChatMsg, type State } from "@/lib/api";
import { keptSentences, paragraphs, sentences } from "@/lib/text";
import { cn } from "@/lib/utils";

/** 글(대화) 화면이 쓰는 조각 — 예전 글 화면(Article.tsx, 2026-10-11 지움)에서 옮겨 왔다: 본문 그리기 · 진행자 창 · 본문 그림 자리 */

function Spin({ texts }: { texts: string[] }) {
  return <AITextLoading texts={texts} className="text-sm font-medium" wrapperClassName="p-0" />;
}

/** 본문 — prev를 주면 앞 과정에 없던 문장에 형광(비교) */
/** after: 문단마다 뒤에 붙일 것(본문 그림 미리보기 — 1부터 센 문단 번호와 전체 문단) */
export function Prose({ text, prev, after }: { text: string; prev?: string; after?: (n: number, all: string[]) => React.ReactNode }) {
  const kept = useMemo(() => (prev !== undefined ? keptSentences(prev, text) : null), [prev, text]);
  let idx = 0;
  return (
    <div className="prose-ko text-ink">
      {paragraphs(text).map((p, i, all) => {
        if (/^#{1,3}\s/.test(p)) return <h4 key={i} className="mt-8 mb-3 text-lg font-semibold text-ink">{p.replace(/^#+\s*/, "")}</h4>;
        return (
          <Fragment key={i}>
          <p>
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
          {after?.(i + 1, all)}
          </Fragment>
        );
      })}
    </div>
  );
}

export function Director({ a, state, open, onClose, refresh }: { a: A; state: State; open: boolean; onClose: () => void; refresh: () => void }) {
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

/** 고른 본문 그림 중 n째 문단 뒤에 들어갈 것 — 문단 첫머리(anchor)로 찾고, 못 찾으면 문단 번호로 */
export function inlineAt(a: A, paras: string[], n: number) {
  return a.inlinePicked.filter((it) => {
    const hit = it.anchor ? paras.findIndex((p) => p.startsWith(it.anchor.slice(0, 20))) + 1 : 0;
    return (hit || Math.min(it.after, paras.length)) === n;
  });
}

/** n째 문단 뒤의 본문 그림 — move가 있으면 ↑↓로 한 문단씩 옮긴다(2026-10-29 사용자: 자동으로 정한 자리를 바꿀 수 있게).
 *  옮긴 자리는 이 원고의 문단 번호와 첫머리로 저장돼 확정할 때도 그 자리에 들어간다 */
export function InlineImgs({ a, paras, n, move }: { a: A; paras: string[]; n: number; move?: () => void }) {
  return inlineAt(a, paras, n).map((it) => {
    const go = (t: number) => act("inline-move", { article: a.id, src: it.src, after: t, anchor: paras[t - 1].slice(0, 40) }).then(move);
    return (
      <div key={it.src} className="group relative my-5">
        <img src={img(it.src, 900)} className="w-full rounded-xl" />
        {move && (
          <div className="absolute top-3 right-3 flex gap-1 opacity-80 transition group-hover:opacity-100">
            {[
              { t: n - 1, label: "↑ 한 문단 위로", icon: <IconArrowUp className="size-4" /> },
              { t: n + 1, label: "↓ 한 문단 아래로", icon: <IconArrowDown className="size-4" /> },
            ].map((b) => (
              <button
                key={b.label}
                title={b.label}
                disabled={b.t < 1 || b.t > paras.length}
                onClick={() => go(b.t)}
                className="rounded-full border border-white/30 bg-black/60 p-1.5 text-white backdrop-blur transition hover:bg-black/80 disabled:opacity-30"
              >
                {b.icon}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  });
}
