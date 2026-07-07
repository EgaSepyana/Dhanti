"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CanvasErrorBoundary } from "@/components/canvas/canvas-error-boundary";
import { RuntimeManager } from "@/lib/canvas/runtime-manager";
import type { Artifact } from "@/lib/types";

function CanvasInner({
  artifact,
  workspaceId,
  buildHtml,
  height,
}: {
  artifact: Artifact;
  workspaceId: string;
  buildHtml: () => string;
  height: number | "fill";
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [crashed, setCrashed] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const permissions = {
    read: Boolean(artifact.permissions?.read),
    write: Boolean(artifact.permissions?.write),
    execute: Boolean(artifact.permissions?.execute),
  };
  const canvasHtml = permissions.execute ? buildHtml() : "";

  useEffect(() => {
    if (!permissions.execute) return;

    const manager = new RuntimeManager({
      iframeWindow: () => iframeRef.current?.contentWindow ?? null,
      workspaceId,
      artifactId: artifact.id,
      permissions,
      onCrash: setCrashed,
    });

    return () => manager.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.id, workspaceId, reloadKey, permissions.execute, permissions.read, permissions.write]);

  if (!permissions.execute) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border p-8 text-center">
        <AlertTriangle className="size-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">This artifact does not have execute permission.</p>
      </div>
    );
  }

  if (crashed) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
        <AlertTriangle className="size-6 text-destructive" />
        <p className="text-sm font-medium text-foreground">This artifact stopped working</p>
        <p className="text-xs text-muted-foreground">{crashed}</p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setCrashed(null);
            setReloadKey((k) => k + 1);
          }}
        >
          <RotateCcw className="size-3.5" />
          Reload
        </Button>
      </div>
    );
  }

  return (
    <iframe
      key={reloadKey}
      ref={iframeRef}
      srcDoc={canvasHtml}
      sandbox="allow-scripts"
      className={height === "fill" ? "h-full w-full rounded-xl border border-border bg-white" : "w-full rounded-xl border border-border bg-white"}
      style={height === "fill" ? undefined : { height }}
      title={artifact.title}
    />
  );
}

/** Renders an artifact inside a sandboxed iframe with the Bridge API wired
 * up. One artifact's crash never reaches the parent app: iframe JS errors
 * are isolated by the browser, and this component's own render errors are
 * caught by CanvasErrorBoundary. `buildHtml` decouples this from any
 * particular artifact type — every runnable artifact (dashboards included)
 * is HTML, wrapped via buildCanvasHtml. */
export function Canvas({
  artifact,
  workspaceId,
  buildHtml,
  height = 600,
}: {
  artifact: Artifact;
  workspaceId: string;
  buildHtml: () => string;
  height?: number | "fill";
}) {
  return (
    <CanvasErrorBoundary>
      <CanvasInner artifact={artifact} workspaceId={workspaceId} buildHtml={buildHtml} height={height} />
    </CanvasErrorBoundary>
  );
}
