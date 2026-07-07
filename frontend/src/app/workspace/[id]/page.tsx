"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, AlertCircle, LayoutPanelLeft, PanelLeft, Settings, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatPanel, type LiveCode } from "@/components/chat/chat-panel";
import { ArtifactListPanel } from "@/components/artifacts/artifact-list-panel";
import { CanvasPanel } from "@/components/workspace/canvas-panel";
import { FileExplorerPanel, type Selection } from "@/components/workspace/file-explorer-panel";
import { workspaceApi } from "@/lib/api";
import type { WorkspaceDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 1500;

export default function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: workspaceId } = use(params);

  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [pendingFileId, setPendingFileId] = useState<string | null>(null);
  const [liveCode, setLiveCode] = useState<LiveCode | null>(null);
  const [filesOpen, setFilesOpen] = useState(false);
  const [canvasOpen, setCanvasOpen] = useState(false);

  const pendingFileIdRef = useRef<string | null>(null);
  useEffect(() => {
    pendingFileIdRef.current = pendingFileId;
  }, [pendingFileId]);

  const refresh = useCallback(() => {
    return workspaceApi
      .get(workspaceId)
      .then((data) => {
        setWorkspace(data);

        const currentPendingId = pendingFileIdRef.current;
        if (!currentPendingId) return;
        const file = data.files.find((f) => f.id === currentPendingId);
        if (file?.status !== "parsed") return;

        const dataset = data.datasets.find((d) => d.file_id === currentPendingId);
        const document = data.documents.find((d) => d.file_id === currentPendingId);
        if (dataset) setSelection({ type: "dataset", id: dataset.id });
        else if (document) setSelection({ type: "document", id: document.id });
        setPendingFileId(null);
        setLiveCode(null);
        setCanvasOpen(true);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load workspace"));
  }, [workspaceId]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  // Poll while any file is still being parsed.
  useEffect(() => {
    const hasInFlight = workspace?.files.some(
      (f) => f.status === "uploaded" || f.status === "parsing",
    );
    if (!hasInFlight) return;

    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [workspace, refresh]);

  const pendingFile = workspace?.files.find((f) => f.id === pendingFileId) ?? null;
  const hasCanvasContent = Boolean(liveCode || selection || pendingFile);

  function closeCanvas() {
    setSelection(null);
    setLiveCode(null);
    setPendingFileId(null);
    setCanvasOpen(false);
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col bg-background">
        <div className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3">
          <Skeleton className="size-8 rounded-md" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="flex flex-1 overflow-hidden">
          <div className="hidden w-64 shrink-0 flex-col gap-2 border-r border-border p-3 lg:flex">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8" />
            ))}
          </div>
          <div className="flex-1 border-r border-border p-4">
            <div className="mx-auto flex h-full max-w-xl flex-col justify-end gap-3">
              <Skeleton className="h-16 w-2/3 self-end" />
              <Skeleton className="h-24 w-3/4" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
          <div className="hidden flex-1 p-4 lg:block">
            <Skeleton className="h-full w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 bg-background text-center">
        <AlertCircle className="size-8 text-destructive" />
        <p className="text-sm text-muted-foreground">{error ?? "Workspace not found"}</p>
        <Link href="/">
          <Button variant="secondary">Back to workspaces</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <header className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3">
        <Link
          href="/"
          className="flex shrink-0 items-center gap-1.5 rounded-md py-1 pl-1 pr-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Back to workspaces"
        >
          <Logo className="size-6" />
          <ArrowLeft className="size-4" />
        </Link>
        <button
          onClick={() => setFilesOpen((v) => !v)}
          aria-label={filesOpen ? "Hide files" : "Show files"}
          aria-pressed={filesOpen}
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground lg:hidden",
            filesOpen && "bg-primary/10 text-primary",
          )}
        >
          <PanelLeft className="size-4" />
        </button>
        <h1 className="flex-1 truncate text-sm font-semibold text-foreground">{workspace.name}</h1>
        <Link
          href={`/workspace/${workspaceId}/settings`}
          aria-label="Workspace settings"
          className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Settings className="size-4" />
        </Link>
        {hasCanvasContent && (
          <button
            onClick={() => setCanvasOpen((v) => !v)}
            aria-label={canvasOpen ? "Hide canvas" : "Show canvas"}
            aria-pressed={canvasOpen}
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground lg:hidden",
              canvasOpen && "bg-primary/10 text-primary",
            )}
          >
            <LayoutPanelLeft className="size-4" />
          </button>
        )}
      </header>

      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {/* Below the lg breakpoint (1024px), the files and canvas panes
            become slide-over drawers with a backdrop instead of squeezing
            chat + canvas into a viewport too narrow for a 3-pane layout. */}
        <aside
          className={cn(
            "z-20 flex w-64 shrink-0 flex-col border-r border-border bg-surface transition-transform duration-200",
            "absolute inset-y-0 left-0 lg:static lg:translate-x-0",
            filesOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="h-1/2 min-h-0 border-b border-border">
            <FileExplorerPanel
              workspaceId={workspaceId}
              files={workspace.files}
              datasets={workspace.datasets}
              documents={workspace.documents}
              selection={selection}
              onSelect={(next) => {
                setSelection(next);
                setLiveCode(null);
                setFilesOpen(false);
                setCanvasOpen(true);
              }}
              onUploaded={(fileId) => {
                setSelection(null);
                setLiveCode(null);
                setPendingFileId(fileId);
                setCanvasOpen(true);
                refresh();
              }}
            />
          </div>
          <div className="h-1/2 min-h-0">
            <ArtifactListPanel
              workspaceId={workspaceId}
              onSelect={(artifactId) => {
                setSelection({ type: "artifact", id: artifactId });
                setLiveCode(null);
                setFilesOpen(false);
                setCanvasOpen(true);
              }}
            />
          </div>
        </aside>
        {filesOpen && (
          <div
            className="absolute inset-0 z-10 bg-black/30 lg:hidden"
            onClick={() => setFilesOpen(false)}
            aria-hidden
          />
        )}

        <main className={cn("min-h-0 min-w-0 flex-1", hasCanvasContent && "border-r border-border")}>
          <ChatPanel
            workspaceId={workspaceId}
            onSelectArtifact={(artifactId) => {
              setSelection({ type: "artifact", id: artifactId });
              setLiveCode(null);
              setCanvasOpen(true);
            }}
            onFileUploaded={(fileId) => {
              setSelection(null);
              setLiveCode(null);
              setPendingFileId(fileId);
              setCanvasOpen(true);
              refresh();
            }}
            onLiveCode={(payload) => {
              setLiveCode(payload);
              if (payload) setCanvasOpen(true);
            }}
          />
        </main>

        {hasCanvasContent && (
          <aside
            className={cn(
              "z-20 flex w-full flex-col bg-surface transition-transform duration-200",
              "absolute inset-y-0 right-0 lg:static lg:w-1/2 lg:translate-x-0 lg:min-w-[420px]",
              canvasOpen ? "translate-x-0" : "translate-x-full",
            )}
          >
            <div className="flex shrink-0 items-center justify-between border-b border-border px-3 py-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Canvas
              </span>
              <button
                onClick={closeCanvas}
                aria-label="Close canvas"
                className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <CanvasPanel
                workspaceId={workspaceId}
                selection={selection}
                liveCode={liveCode}
                pendingFile={pendingFile}
                onDismissPendingFile={() => setPendingFileId(null)}
              />
            </div>
          </aside>
        )}
        {hasCanvasContent && canvasOpen && (
          <div
            className="absolute inset-0 z-10 bg-black/30 lg:hidden"
            onClick={() => setCanvasOpen(false)}
            aria-hidden
          />
        )}
      </div>
    </div>
  );
}
