"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";

export type FocusCardData = {
  key: string;
  title: string;
  src?: string;
  fallback?: React.ReactNode;
  overlay?: React.ReactNode;
  badge?: React.ReactNode;
  selected?: boolean;
  onClick?: () => void;
};

export const Card = React.memo(
  ({
    card,
    index,
    hovered,
    setHovered,
    height,
  }: {
    card: FocusCardData;
    index: number;
    hovered: number | null;
    setHovered: React.Dispatch<React.SetStateAction<number | null>>;
    height: string;
  }) => (
    <div
      onMouseEnter={() => setHovered(index)}
      onMouseLeave={() => setHovered(null)}
      onClick={card.onClick}
      className={cn(
        "rounded-2xl relative bg-gray-100 dark:bg-neutral-900 overflow-hidden w-full transition-all duration-300 ease-out cursor-pointer",
        height,
        hovered !== null && hovered !== index && "blur-sm scale-[0.98]",
        card.selected && "ring-2 ring-violet-400 ring-offset-4 ring-offset-neutral-950"
      )}
    >
      {card.src ? (
        <img
          src={card.src}
          alt={card.title}
          loading="lazy"
          className="object-cover absolute inset-0 h-full w-full"
        />
      ) : (
        card.fallback
      )}
      {card.badge && <div className="absolute top-4 left-4 z-10">{card.badge}</div>}
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent flex items-end py-6 px-5 transition-opacity duration-300",
          hovered === index || !card.src ? "opacity-100" : "opacity-80"
        )}
      >
        {card.overlay ?? (
          <div className="text-xl md:text-2xl font-medium bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-200">
            {card.title}
          </div>
        )}
      </div>
    </div>
  )
);

Card.displayName = "Card";

export function FocusCards({
  cards,
  className,
  height = "h-80",
}: {
  cards: FocusCardData[];
  className?: string;
  height?: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div className={cn("grid grid-cols-3 gap-8 w-full", className)}>
      {cards.map((card, index) => (
        <Card
          key={card.key}
          card={card}
          index={index}
          hovered={hovered}
          setHovered={setHovered}
          height={height}
        />
      ))}
    </div>
  );
}
