import { FocusCards } from "@/components/ui/focus-cards";
import { BackgroundBeams } from "@/components/ui/background-beams";
import { Chip } from "@/components/studio/bits";
import { articleTitle, img, stage, type Article, type State } from "@/lib/api";
import { hue } from "@/lib/text";
import { cn } from "@/lib/utils";

export function StageChip({ a, className }: { a: Article; className?: string }) {
  const s = stage(a);
  return (
    <Chip
      className={cn(
        "backdrop-blur",
        s === "확정" ? "border-emerald-300/40 bg-emerald-500/20 text-emerald-100" : "border-white/20 bg-black/40 text-white",
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
        background: `radial-gradient(90% 120% at 15% 10%, hsl(${h} 65% 45% / .55), transparent 60%), radial-gradient(80% 120% at 90% 90%, hsl(${(h + 60) % 360} 70% 45% / .4), transparent 60%), #0b0b0e`,
      }}
    />
  );
}

export default function Articles({ state, go }: { state: State; go: (h: string) => void }) {
  const list = [...state.articles].sort((a, b) => {
    const ca = a.confirmed ? 0 : 1,
      cb = b.confirmed ? 0 : 1;
    return ca - cb || b.at - a.at;
  });
  return (
    <div className="min-h-full">
      <div className="relative h-[300px] overflow-hidden border-b border-white/[0.06]">
        <BackgroundBeams />
        <div className="relative z-10 mx-auto flex h-full max-w-6xl items-end px-12 pb-12">
          <h1 className="text-6xl font-bold tracking-tight text-white">
            글 <span className="text-neutral-600 tabular-nums">{list.length}</span>
          </h1>
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-12 py-12">
        <FocusCards
          height="h-[22rem]"
          cards={list.map((a) => ({
            key: a.id,
            title: articleTitle(a),
            src: a.hero ? img(a.hero, 900) : a.confirmed?.hero ? img(a.confirmed.hero, 900) : undefined,
            fallback: <Cover a={a} />,
            badge: <StageChip a={a} />,
            onClick: () => go(`#/a/${a.id}`),
            overlay: (
              <div>
                <div className="text-xl font-semibold leading-snug text-white">{articleTitle(a)}</div>
                <div className="mt-2 line-clamp-2 text-sm text-neutral-300/80">{a.thesis}</div>
              </div>
            ),
          }))}
        />
      </div>
    </div>
  );
}
