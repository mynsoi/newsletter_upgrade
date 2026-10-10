import { useRef } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import Document from "@tiptap/extension-document";
import Paragraph from "@tiptap/extension-paragraph";
import Text from "@tiptap/extension-text";
import Heading from "@tiptap/extension-heading";
import HardBreak from "@tiptap/extension-hard-break";
import { UndoRedo } from "@tiptap/extensions";
import { fromDoc, toDoc, type DocNode } from "@/lib/doc";
import { cn } from "@/lib/utils";

/**
 * 원고 에디터 (멘토 2026-10-10: "뷰어를 에디터로 만들어서 직접 사람이 편집할 수도 있게").
 * 원고는 문단만 있는 글이라 굵게·목록 같은 서식은 일부러 넣지 않았다 — 저장하면 사라질 서식을 만들지 않게.
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
    extensions: [Document, Paragraph, Text, Heading.configure({ levels: [1, 2, 3] }), HardBreak, UndoRedo],
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
  return <EditorContent editor={editor} />;
}
