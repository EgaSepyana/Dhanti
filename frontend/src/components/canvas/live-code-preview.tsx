"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import dynamic from "next/dynamic";
import type { OnMount } from "@monaco-editor/react";
import { Code2, Loader2, MonitorPlay } from "lucide-react";
import { buildCanvasHtml } from "@/lib/canvas/artifact-loader";
import { cn } from "@/lib/utils";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const PREVIEW_THROTTLE_MS = 300;

/** Shows an agent-authored HTML document as it streams in, token by token —
 * the Gemini-Canvas-style "watch it write code" view. The Monaco pane updates
 * on every chunk; the iframe preview is throttled (partial HTML is valid to
 * render — browsers show what's parseable so far — but re-mounting the
 * iframe on every token would thrash and flicker). Once the agent finishes,
 * the caller swaps this out for the real ArtifactViewer. */
export function LiveCodePreview({ code, done }: { code: string; done: boolean }) {
  const [tab, setTab] = useState<"code" | "preview">("code");
  const [previewHtml, setPreviewHtml] = useState("");
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  useEffect(() => {
    const id = setTimeout(() => setPreviewHtml(buildCanvasHtml(code)), PREVIEW_THROTTLE_MS);
    return () => clearTimeout(id);
  }, [code]);

  useEffect(() => {
    const editor = editorRef.current;
    const model = editor?.getModel();
    if (editor && model) editor.revealLine(model.getLineCount());
  }, [code]);

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="inline-flex w-fit items-center gap-1 rounded-lg border border-border bg-muted/40 p-1">
          <TabButton
            active={tab === "preview"}
            onClick={() => setTab("preview")}
            icon={<MonitorPlay className="size-3.5" />}
            label="Preview"
          />
          <TabButton
            active={tab === "code"}
            onClick={() => setTab("code")}
            icon={<Code2 className="size-3.5" />}
            label="Code"
          />
        </div>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {!done && <Loader2 className="size-3 animate-spin" />}
          {done ? "Code written" : "Writing code…"}
        </span>
      </div>

      {tab === "code" ? (
        <div className="flex-1 overflow-hidden rounded-xl border border-border">
          <MonacoEditor
            height="100%"
            language="html"
            value={code}
            theme="vs-dark"
            onMount={handleMount}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              wordWrap: "on",
              scrollBeyondLastLine: false,
            }}
          />
        </div>
      ) : (
        <iframe
          srcDoc={previewHtml}
          sandbox="allow-scripts"
          className="h-full w-full flex-1 rounded-xl border border-border bg-white"
          title="Live preview"
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
        active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
