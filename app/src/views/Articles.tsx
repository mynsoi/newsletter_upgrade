import { useEffect, useState } from "react";
import { IconTrash } from "@tabler/icons-react";
import { FocusCards } from "@/components/ui/focus-cards";
import { BackgroundBeams } from "@/components/ui/background-beams";
import { Chip } from "@/components/studio/bits";
import { act, articleTitle, img, stage, type Article, type State } from "@/lib/api";
import NewChat from "@/views/MineChat";
import { hue } from "@/lib/text";
import { cn } from "@/lib/utils";

export function StageChip({ a, className }: { a: Article; className?: string }) {
  const s = stage(a);
  return (
    <Chip
      className={cn(
        "backdrop-blur",
        s === "확정" ? "border-emerald-300/40 bg-emerald-500/20 text-emerald-800 dark:text-emerald-100" : "border-line bg-page/60 text-ink",
        className
      )}
    >
      {s}
    </Chip>
  );
}

export function Cover({ a, className }: { a: Article; className?: string }) {
  const h = hue(a.id);
  return (
    <div
      className={cn("absolute inset-0", className)}
      style={{
        background: `radial-gradient(90% 120% at 15% 10%, hsl(${h} 65% 45% / .55), transparent 60%), radial-gradient(80% 120% at 90% 90%, hsl(${(h + 60) % 360} 70% 45% / .4), transparent 60%), var(--page)`,
      }}
    />
  );
}

export default function Articles({ state, refresh, go }: { state: State; refresh: () => void; go: (h: string) => void }) {
  const list = [...state.articles].sort((a, b) => {
    const ca = a.confirmed ? 0 : 1,
      cb = b.confirmed ? 0 : 1;
    return ca - cb || b.at - a.at;
  });
  return (
    <div className="min-h-full">
      <div className="relative overflow-hidden border-b border-line">
        <BackgroundBeams />
        <div className="relative z-10 mx-auto max-w-4xl px-12 pt-20 pb-12">
          <NewChat state={state} refresh={refresh} go={go} />
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-12 py-12">
        <h1 className="mb-10 text-5xl font-bold tracking-tight text-ink">
          글 <span className="text-ink-3 tabular-nums">{list.length}</span>
        </h1>
        <FocusCards
          height="h-[22rem]"
          cards={list.map((a) => ({
            key: a.id,
            title: articleTitle(a),
            src: a.hero ? img(a.hero, 900) : a.confirmed?.hero ? img(a.confirmed.hero, 900) : undefined,
            fallback: <Cover a={a} />,
            badge: <StageChip a={a} />,
            action: a.kind === "brief" ? <DeleteButton a={a} refresh={refresh} /> : undefined,
            onClick: () => go(`#/a/${a.id}`),
            overlay: (
              <div>
                <div className="text-xl font-semibold leading-snug">{articleTitle(a)}</div>
                <div className="mt-2 line-clamp-2 text-sm opacity-75">{a.thesis}</div>
              </div>
            ),
          }))}
        />
      </div>
    </div>
  );
}

/** 글 삭제 — 두 번 눌러야(지우지 않고 trash/로 옮긴다). 확정 기준 글에는 없다. 카드와 글 화면이 같이 쓴다 */
export function DeleteButton({ a, refresh, onDone, className }: { a: Article; refresh: () => void; onDone?: () => void; className?: string }) {
  const [arm, setArm] = useState(false);
  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => setArm(false), 3000);
    return () => clearTimeout(t);
  }, [arm]);
  return (
    <button
      title="삭제"
      onClick={async (e) => {
        e.stopPropagation(); // 카드를 눌러 글로 들어가지 않게
        if (!arm) return setArm(true);
        await act("delete", { article: a.id });
        onDone?.();
        refresh();
      }}
      className={cn(
        "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm backdrop-blur transition",
        arm ? "border-rose-400/60 bg-rose-500/80 text-white" : "border-line bg-page/70 text-ink-2 hover:text-ink",
        className
      )}
    >
      <IconTrash className="size-4" />
      {arm ? "한 번 더" : "삭제"}
    </button>
  );
}
