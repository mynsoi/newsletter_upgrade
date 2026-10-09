import { useEffect, useState } from "react";
import { IconBrandLinkedin, IconBrandThreads, IconNotebook, IconWorld, IconHeart } from "@tabler/icons-react";
import { Drawer, DrawerContent, DrawerTitle } from "@/components/ui/drawer";
import { getSource, type Source } from "@/lib/api";
import { paragraphs } from "@/lib/text";
import { cn } from "@/lib/utils";

export function SiteIcon({ site, className }: { site: string; className?: string }) {
  const c = cn("size-4", className);
  if (site === "threads") return <IconBrandThreads className={c} />;
  if (site === "linkedin") return <IconBrandLinkedin className={cn(c, "text-sky-400")} />;
  if (site === "infuture") return <IconNotebook className={cn(c, "text-amber-300")} />;
  return <IconWorld className={c} />;
}

export function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-xs text-neutral-300",
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
      ? "border-orange-400/30 text-orange-200 bg-orange-500/10"
      : by === "astra"
        ? "border-emerald-400/30 text-emerald-200 bg-emerald-500/10"
        : "border-violet-400/30 text-violet-200 bg-violet-500/10";
  return <Chip className={tone}>{by}</Chip>;
}

export function Reactions({ n }: { n: string }) {
  if (!n) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-rose-300/90">
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
      <DrawerContent className="z-[80] bg-neutral-950 border-white/10 data-[vaul-drawer-direction=right]:w-[720px] data-[vaul-drawer-direction=right]:sm:max-w-[720px]">
        <div className="h-full overflow-y-auto px-12 py-12">
          {src && (
            <>
              <div className="flex items-center gap-3 text-sm text-neutral-400">
                <SiteIcon site={src.site} />
                <span>{src.siteName}</span>
                {src.date && <span>{src.date}</span>}
                <Reactions n={src.reactions} />
                {src.url && (
                  <a href={src.url} target="_blank" rel="noreferrer" className="ml-auto text-neutral-500 hover:text-white">
                    ↗
                  </a>
                )}
              </div>
              <DrawerTitle className="mt-4 text-2xl font-semibold leading-snug text-white">
                {sourceName(src)}
              </DrawerTitle>
              <div className="prose-ko mt-8 text-[15.5px] text-neutral-300">
                {paragraphs(src.text || "").map((p, i) =>
                  p.startsWith("## ") ? (
                    <div key={i} className="mb-3 mt-8 text-xs text-neutral-500">
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
      <h1 className="text-5xl font-bold tracking-tight text-white">{title}</h1>
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
        .replace(/\*\*(.+?)\*\*/g, "<b class='text-white font-semibold'>$1</b>")
        .replace(/`([^`]+)`/g, "<code class='rounded bg-white/10 px-1 py-0.5 text-[12.5px]'>$1</code>");
      if (/^\s*[-*] /.test(l)) h = "<span class='flex gap-2'><span class='text-neutral-500'>·</span><span>" + h.replace(/^\s*[-*] /, "") + "</span></span>";
      else if (/^#{1,4} /.test(l)) h = "<b class='text-white'>" + h.replace(/^#+ /, "") + "</b>";
      return h || "<span class='block h-2'></span>";
    })
    .join("<br/>");
  return <div className="leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
}
