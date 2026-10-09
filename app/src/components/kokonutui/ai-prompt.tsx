"use client";

/**
 * @author: @kokonutui
 * @description: AI Prompt Input
 * @version: 1.0.0
 * @date: 2025-06-26
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 */

import { ArrowRight, Check, ChevronDown } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { useAutoResizeTextarea } from "@/hooks/use-auto-resize-textarea";
import { cn } from "@/lib/utils";

export type PromptMode = { id: string; label: string; icon: React.ReactNode };

interface AIPromptProps {
  modes: PromptMode[];
  mode: string;
  onModeChange: (id: string) => void;
  placeholder?: string;
  onSubmit?: (value: string, mode: string) => void;
  busy?: React.ReactNode;
  className?: string;
}

export default function AI_Prompt({
  modes,
  mode,
  onModeChange,
  placeholder,
  onSubmit,
  busy,
  className,
}: AIPromptProps) {
  const [value, setValue] = useState("");
  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 48,
    maxHeight: 300,
  });
  const current = modes.find((m) => m.id === mode) ?? modes[0];

  const submit = () => {
    if (!value.trim()) return;
    onSubmit?.(value, current.id);
    setValue("");
    adjustHeight(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className={cn("w-4/6 py-4", className)}>
      <div className="rounded-2xl bg-black/5 p-1.5 dark:bg-white/5 backdrop-blur-xl">
        <div className="relative">
          <div className="relative flex flex-col">
            <div className="overflow-y-auto" style={{ maxHeight: "400px" }}>
              <Textarea
                className={cn(
                  "w-full resize-none rounded-xl rounded-b-none border-none bg-black/5 px-4 py-3 placeholder:text-black/70 focus-visible:ring-0 focus-visible:ring-offset-0 dark:bg-white/5 dark:text-white dark:placeholder:text-white/40 text-[15px] leading-relaxed",
                  "min-h-[48px]"
                )}
                onChange={(e) => {
                  setValue(e.target.value);
                  adjustHeight();
                }}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                ref={textareaRef}
                value={value}
              />
            </div>

            <div className="flex h-12 items-center rounded-b-xl bg-black/5 dark:bg-white/5">
              <div className="absolute right-3 bottom-2 left-3 flex w-[calc(100%-24px)] items-center justify-between">
                <div className="flex items-center gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        className="flex h-8 items-center gap-1 rounded-md pr-2 pl-1 text-xs hover:bg-black/10 focus-visible:ring-1 focus-visible:ring-blue-500 focus-visible:ring-offset-0 dark:text-white dark:hover:bg-white/10"
                        variant="ghost"
                      >
                        <AnimatePresence mode="wait">
                          <motion.div
                            animate={{ opacity: 1, y: 0 }}
                            className="flex items-center gap-1.5"
                            exit={{ opacity: 0, y: 5 }}
                            initial={{ opacity: 0, y: -5 }}
                            key={current.id}
                            transition={{ duration: 0.15 }}
                          >
                            {current.icon}
                            {current.label}
                            <ChevronDown className="h-3 w-3 opacity-50" />
                          </motion.div>
                        </AnimatePresence>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      className={cn(
                        "min-w-[10rem]",
                        "border-black/10 dark:border-white/10",
                        "bg-gradient-to-b from-white via-white to-neutral-100 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-800"
                      )}
                    >
                      {modes.map((m) => (
                        <DropdownMenuItem
                          className="flex items-center justify-between gap-2"
                          key={m.id}
                          onSelect={() => onModeChange(m.id)}
                        >
                          <div className="flex items-center gap-2">
                            {m.icon}
                            <span>{m.label}</span>
                          </div>
                          {current.id === m.id && <Check className="h-4 w-4 text-blue-500" />}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  {busy && (
                    <>
                      <div className="mx-0.5 h-4 w-px bg-black/10 dark:bg-white/10" />
                      {busy}
                    </>
                  )}
                </div>
                <button
                  aria-label="Send message"
                  className={cn(
                    "rounded-lg bg-black/5 p-2 dark:bg-white/5",
                    "hover:bg-black/10 focus-visible:ring-1 focus-visible:ring-blue-500 focus-visible:ring-offset-0 dark:hover:bg-white/10"
                  )}
                  disabled={!value.trim()}
                  onClick={submit}
                  type="button"
                >
                  <ArrowRight
                    className={cn(
                      "h-4 w-4 transition-opacity duration-200 dark:text-white",
                      value.trim() ? "opacity-100" : "opacity-30"
                    )}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
