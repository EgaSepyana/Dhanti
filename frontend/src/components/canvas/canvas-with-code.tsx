"use client";

import { useState, type ReactNode } from "react";
import dynamic from "next/dynamic";
import { Code2, MonitorPlay } from "lucide-react";
import { Canvas } from "@/components/canvas/canvas";
import type { Artifact } from "@/lib/types";
import { cn } from "@/lib/utils";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

/** Preview/Code toggle around the sandboxed Canvas. The code view is a
 * read-only Monaco pane showing the agent-authored source (HTML for
 * executable artifacts, the dashboard JSON spec for dashboards) — edits
 * happen by asking the agent to revise, not by typing here, so there's no
 * second write path to reconcile with artifact versioning. */
export function CanvasWithCode({
  artifact,
  workspaceId,
  buildHtml,
  height = 600,
  code,
  language = "html",
}: {
  artifact: Artifact;
  workspaceId: string;
  buildHtml: () => string;
  height?: number | "fill";
  code: string;
  language?: "html" | "json";
}) {
  const [tab, setTab] = useState<"preview" | "code">("preview");

  return (
    <div className={height === "fill" ? "flex h-full flex-col gap-2" : "space-y-2"}>
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

      {tab === "preview" ? (
        <div className={cn("overflow-hidden", height === "fill" && "min-h-0 flex-1")}>
          <Canvas artifact={artifact} workspaceId={workspaceId} buildHtml={buildHtml} height={height} />
        </div>
      ) : (
        <div
          className={cn(
            "overflow-hidden rounded-xl border border-border",
            height === "fill" && "flex-1",
          )}
          style={height === "fill" ? undefined : { height }}
        >
          <MonacoEditor
            height={height === "fill" ? "100%" : height}
            language={language}
            value={code}
            theme="vs-dark"
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              wordWrap: "on",
              scrollBeyondLastLine: false,
            }}
          />
        </div>
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
