import { useEffect, useState } from "react";
import { IconBrandLinkedin, IconBrandThreads, IconNotebook, IconWorld, IconHeart } from "@tabler/icons-react";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import Anthropic from "@/components/kokonutui/anthropic";
import AnthropicDark from "@/components/kokonutui/anthropic-dark";
import { getSource, type Source } from "@/lib/api";
import { paragraphs } from "@/lib/text";
import { cn } from "@/lib/utils";

export function SiteIcon({ site, className }: { site: string; className?: string }) {
  const c = cn("size-4", className);
  if (site === "threads") return <IconBrandThreads className={c} />;
  if (site === "linkedin") return <IconBrandLinkedin className={cn(c, "text-sky-400")} />;
  if (site === "infuture") return <IconNotebook className={cn(c, "text-amber-500 dark:text-amber-300")} />;
  return <IconWorld className={c} />;
}

export function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-line bg-soft px-2.5 py-0.5 text-xs text-ink-2",
        className
      )}
    >
      {children}
    </span>
  );
}

export function ByChip({ by }: { by: string }) {
  const tone =
    by === "Claude"
      ? "border-orange-400/30 text-orange-700 dark:text-orange-200 bg-orange-500/10"
      : by === "astra"
        ? "border-emerald-400/30 text-emerald-700 dark:text-emerald-200 bg-emerald-500/10"
        : "border-violet-400/30 text-violet-700 dark:text-violet-200 bg-violet-500/10";
  return <Chip className={tone}>{by}</Chip>;
}

export function Reactions({ n }: { n: string }) {
  if (!n) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-rose-500 dark:text-rose-300/90">
      <IconHeart className="size-3.5" />
      {n.replace(/[()]/g, "")}
    </span>
  );
}

export const sourceName = (s?: Source, fallback = "") =>
  s ? s.title || [s.author, s.headline].filter(Boolean).join(" · ") || s.path : fallback;

export function SourceDrawer({ path, onClose }: { path: string | null; onClose: () => void }) {
  const [src, setSrc] = useState<Source | null>(null);
  useEffect(() => {
    setSrc(null);
    if (path) getSource(path).then(setSrc);
  }, [path]);
  return (
    <Drawer direction="right" open={!!path} onOpenChange={(o) => !o && onClose()}>
      <DrawerContent className="z-[80] bg-page border-line data-[vaul-drawer-direction=right]:w-[720px] data-[vaul-drawer-direction=right]:sm:max-w-[720px]">
        <div className="h-full overflow-y-auto px-12 py-12">
          {src && (
            <>
              <div className="flex items-center gap-3 text-sm text-ink-2">
                <SiteIcon site={src.site} />
                <span>{src.siteName}</span>
                {src.date && <span>{src.date}</span>}
                <Reactions n={src.reactions} />
                {src.url && (
                  <a href={src.url} target="_blank" rel="noreferrer" className="ml-auto text-ink-3 hover:text-ink">
                    ↗
                  </a>
                )}
              </div>
              <DrawerTitle className="mt-4 text-2xl font-semibold leading-snug text-ink">
                {sourceName(src)}
              </DrawerTitle>
              <div className="prose-ko mt-8 text-[15.5px] text-ink-2">
                {paragraphs(src.text || "").map((p, i) =>
                  p.startsWith("## ") ? (
                    <div key={i} className="mb-3 mt-8 text-xs text-ink-3">
                      {p.slice(3)}
                    </div>
                  ) : (
                    <p key={i} className="whitespace-pre-line">
                      {p}
                    </p>
                  )
                )}
              </div>
            </>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}

export function Header({ title, right, className }: { title: React.ReactNode; right?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-end justify-between gap-6", className)}>
      <h1 className="text-5xl font-bold tracking-tight text-ink">{title}</h1>
      {right}
    </div>
  );
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

// 진행자 답에 섞여 오는 간단한 마크다운(굵게·코드·목록)만 그린다
export function MiniMd({ text }: { text: string }) {
  const html = text
    .split("\n")
    .map((l) => {
      let h = esc(l)
        .replace(/\*\*(.+?)\*\*/g, "<b class='text-ink font-semibold'>$1</b>")
        .replace(/`([^`]+)`/g, "<code class='rounded bg-soft px-1 py-0.5 text-[12.5px]'>$1</code>");
      if (/^\s*[-*] /.test(l)) h = "<span class='flex gap-2'><span class='text-ink-3'>·</span><span>" + h.replace(/^\s*[-*] /, "") + "</span></span>";
      else if (/^#{1,4} /.test(l)) h = "<b class='text-ink'>" + h.replace(/^#+ /, "") + "</b>";
      return h || "<span class='block h-2'></span>";
    })
    .join("<br/>");
  return <div className="leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
}

/** Claude 표시 — 라이트에선 검은 로고, 다크에선 흰 로고 */
export function ClaudeMark({ className }: { className?: string }) {
  return (
    <>
      <Anthropic className={cn(className, "dark:hidden")} />
      <AnthropicDark className={cn(className, "hidden dark:block")} />
    </>
  );
}
