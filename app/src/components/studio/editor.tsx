import { useRef } from "react";
import { EditorContent, useEditor, useEditorState } from "@tiptap/react";
import { Mark } from "@tiptap/core";
import Document from "@tiptap/extension-document";
import Paragraph from "@tiptap/extension-paragraph";
import Text from "@tiptap/extension-text";
import Heading from "@tiptap/extension-heading";
import HardBreak from "@tiptap/extension-hard-break";
import { UndoRedo } from "@tiptap/extensions";
import { fromDoc, toDoc, type DocNode } from "@/lib/doc";
import { cn } from "@/lib/utils";

/** 강조(굵게) — 원고에는 ==…==로 남고 발행본에서 굵게 그려진다(2026-11-04 사용자: 버튼 하나로, 밑줄은 뺌) */
const Emph = Mark.create({
  name: "emph",
  parseHTML: () => [{ tag: "strong.key" }],
  renderHTML: () => ["strong", { class: "key" }, 0],
  addKeyboardShortcuts() {
    return { "Mod-b": () => this.editor.commands.toggleMark(this.name) };
  },
});

/**
 * 원고 에디터 (멘토 2026-10-10: "뷰어를 에디터로 만들어서 직접 사람이 편집할 수도 있게").
 * 서식은 강조 하나만 둔다 — 원고 파일(글자)에 ==…==로 남아 저장해도 사라지지 않는다. 굵게·목록 같은 다른 서식은 일부러 넣지 않았다.
 * 내용은 열 때 한 번만 채운다: 편집하는 동안 화면이 새로 받아 와도 쓰던 글을 덮지 않는다.
 */
export function ProseEditor({
  text,
  onChange,
  onSave,
  className,
}: {
  text: string;
  onChange: (t: string) => void;
  onSave?: () => void;
  className?: string;
}) {
  const save = useRef(onSave);
  save.current = onSave;
  const editor = useEditor({
    extensions: [Document, Paragraph, Text, Heading.configure({ levels: [1, 2, 3] }), HardBreak, UndoRedo, Emph],
    content: toDoc(text),
    autofocus: "end",
    editorProps: {
      attributes: { class: cn("ed outline-none", className) },
      handleKeyDown: (_view, e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
          e.preventDefault();
          save.current?.();
          return true;
        }
        return false;
      },
    },
    onUpdate: ({ editor }) => onChange(fromDoc(editor.getJSON() as DocNode)),
  });
  const on = useEditorState({ editor, selector: (c) => !!c.editor?.isActive("emph") });
  return (
    <>
      <div className="mb-3 flex items-center gap-2 border-b border-line pb-3">
        <button
          type="button"
          aria-pressed={on}
          title="고른 문장을 굵게 (Ctrl+B) — 다시 누르면 풀림"
          // 누르는 순간 선택이 풀리지 않게 mousedown에서 처리
          onMouseDown={(e) => {
            e.preventDefault();
            editor?.chain().focus().toggleMark("emph").run();
          }}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-semibold transition",
            on ? "border-ink bg-ink text-page" : "border-line text-ink-2 hover:border-ink-3 hover:text-ink"
          )}
        >
          <b>강조</b>
        </button>
        <span className="text-xs text-ink-3">문장을 드래그한 뒤 누르면 굵게 · Ctrl+B</span>
      </div>
      <EditorContent editor={editor} />
    </>
  );
}
