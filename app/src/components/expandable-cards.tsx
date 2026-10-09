"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useOutsideClick } from "@/hooks/use-outside-click";
import { cn } from "@/lib/utils";

export type ExpandableItem = {
  key: string;
  head: React.ReactNode; // 카드·펼친 화면 모두에서 같은 자리로 이어지는 머리
  title: string;
  summary: React.ReactNode;
  body: React.ReactNode;
  action?: React.ReactNode;
  dim?: boolean;
};

export default function ExpandableCards({
  items,
  className,
}: {
  items: ExpandableItem[];
  className?: string;
}) {
  const [active, setActive] = useState<ExpandableItem | null>(null);
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setActive(null);
    }
    document.body.style.overflow = active ? "hidden" : "auto";
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active]);

  useOutsideClick(ref as React.RefObject<HTMLDivElement>, () => setActive(null));

  return (
    <>
      <AnimatePresence>
        {active && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/25 dark:bg-black/60 backdrop-blur-sm h-full w-full z-40"
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {active ? (
          <div className="fixed inset-0 grid place-items-center z-[60]">
            <motion.div
              layoutId={`card-${active.key}-${id}`}
              ref={ref}
              className="w-full max-w-[760px] max-h-[88vh] flex flex-col bg-panel-solid border border-line rounded-3xl overflow-hidden shadow-2xl"
            >
              <motion.div layoutId={`head-${active.key}-${id}`}>{active.head}</motion.div>
              <div className="flex justify-between items-start gap-6 px-8 pt-6">
                <motion.h3
                  layoutId={`title-${active.key}-${id}`}
                  className="font-semibold text-ink text-2xl leading-snug"
                >
                  {active.title}
                </motion.h3>
                {active.action && (
                  <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    {active.action}
                  </motion.div>
                )}
              </div>
              <motion.div
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="px-8 pt-4 pb-8 overflow-auto [scrollbar-width:thin] text-ink-2"
              >
                {active.body}
              </motion.div>
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>
      <ul className={cn("w-full grid grid-cols-3 items-start gap-5", className)}>
        {items.map((card) => (
          <motion.div
            layoutId={`card-${card.key}-${id}`}
            key={card.key}
            onClick={() => setActive(card)}
            className={cn(
              "group flex flex-col rounded-3xl cursor-pointer overflow-hidden bg-panel border border-line hover:border-ink-3/40 hover:bg-panel-solid transition-colors",
              card.dim && "opacity-60"
            )}
          >
            <motion.div layoutId={`head-${card.key}-${id}`}>{card.head}</motion.div>
            <div className="flex flex-col gap-3 p-6">
              <motion.h3
                layoutId={`title-${card.key}-${id}`}
                className="font-semibold text-ink text-lg leading-snug"
              >
                {card.title}
              </motion.h3>
              <div className="text-ink-2 text-sm leading-relaxed">{card.summary}</div>
            </div>
          </motion.div>
        ))}
      </ul>
    </>
  );
}

export const CloseIcon = () => {
  return (
    <motion.svg
      initial={{
        opacity: 0,
      }}
      animate={{
        opacity: 1,
      }}
      exit={{
        opacity: 0,
        transition: {
          duration: 0.05,
        },
      }}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 text-black"
    >
      <path stroke="none" d="M0 0h24v24H0z" fill="none" />
      <path d="M18 6l-12 12" />
      <path d="M6 6l12 12" />
    </motion.svg>
  );
};

