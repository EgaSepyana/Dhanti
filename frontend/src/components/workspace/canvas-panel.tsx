"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, X } from "lucide-react";
import type { LiveCode } from "@/components/chat/chat-panel";
import { ArtifactViewer } from "@/components/artifacts/artifact-viewer";
import { LiveCodePreview } from "@/components/canvas/live-code-preview";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Selection } from "@/components/workspace/file-explorer-panel";
import { DatasetPreview } from "@/components/workspace/dataset-preview";
import { DocumentPreview } from "@/components/workspace/document-preview";
import { artifactApi } from "@/lib/api";
import type { Artifact, FileItem } from "@/lib/types";

/** The workspace's Canvas pane (Gemini-Canvas-style): whatever is active —
 * code streaming live from the agent, a file preview, or a finished artifact
 * — renders directly here. Nothing in this app opens a new tab to view an
 * artifact; this panel is the single place it's shown. */
export function CanvasPanel({
  workspaceId,
  selection,
  liveCode,
  pendingFile,
  onDismissPendingFile,
}: {
  workspaceId: string;
  selection: Selection;
  liveCode: LiveCode | null;
  pendingFile: FileItem | null;
  onDismissPendingFile: () => void;
}) {
  if (liveCode) {
    // Stays visible (frozen on its final code+preview) after the agent
    // finishes, until the user explicitly picks something else — clicking a
    // file or artifact clears it (see workspace/[id]/page.tsx).
    return (
      <div className="h-full p-3">
        <LiveCodePreview code={liveCode.code} done={liveCode.done} />
      </div>
    );
  }

  if (pendingFile) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <ParsingCard fileName={pendingFile.name} status={pendingFile.status} onDismiss={onDismissPendingFile} />
      </div>
    );
  }

  if (selection?.type === "dataset") {
    return (
      <div className="h-full overflow-y-auto p-4">
        <DatasetPreview key={selection.id} workspaceId={workspaceId} datasetId={selection.id} />
      </div>
    );
  }

  if (selection?.type === "document") {
    return (
      <div className="h-full overflow-y-auto p-4">
        <DocumentPreview key={selection.id} workspaceId={workspaceId} documentId={selection.id} />
      </div>
    );
  }

  if (selection?.type === "artifact") {
    return (
      <div className="flex h-full flex-col gap-2 p-3">
        <ArtifactSlot key={selection.id} workspaceId={workspaceId} artifactId={selection.id} />
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center p-6 text-center">
      <div className="max-w-xs space-y-2">
        <p className="text-sm font-medium text-foreground">Canvas</p>
        <p className="text-sm text-muted-foreground">
          Select a file or artifact on the left, or ask DHANTI to analyze data or build a
          dashboard — the live code and preview will open here.
        </p>
      </div>
    </div>
  );
}

function ArtifactSlot({ workspaceId, artifactId }: { workspaceId: string; artifactId: string }) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    artifactApi
      .get(artifactId)
      .then(setArtifact)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load artifact"))
      .finally(() => setLoading(false));
  }, [artifactId]);

  if (loading) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-2">
        <Skeleton className="h-4 w-40 shrink-0" />
        <Skeleton className="min-h-0 flex-1" />
      </div>
    );
  }

  if (error || !artifact) {
    return (
      <Card className="mx-auto max-w-md p-6 text-center">
        <AlertCircle className="mx-auto size-8 text-destructive" />
        <p className="mt-3 text-sm text-muted-foreground">{error ?? "Artifact not found"}</p>
      </Card>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="shrink-0">
        <h2 className="truncate text-sm font-semibold text-foreground">{artifact.title}</h2>
        <p className="text-xs text-muted-foreground">
          {artifact.type} · v{artifact.version}
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ArtifactViewer artifact={artifact} workspaceId={workspaceId} canvasHeight="fill" />
      </div>
    </div>
  );
}

function ParsingCard({
  fileName,
  status,
  onDismiss,
}: {
  fileName: string;
  status: FileItem["status"];
  onDismiss: () => void;
}) {
  if (status === "error") {
    return (
      <Card className="max-w-md p-6 text-center">
        <AlertCircle className="mx-auto size-8 text-destructive" />
        <p className="mt-3 text-sm font-medium text-foreground">Failed to parse {fileName}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          The file may be corrupted or in an unexpected format.
        </p>
        <Button variant="secondary" className="mt-4" onClick={onDismiss}>
          <X className="size-4" />
          Dismiss
        </Button>
      </Card>
    );
  }

  return (
    <Card className="max-w-md p-6 text-center">
      <Loader2 className="mx-auto size-8 animate-spin text-primary" />
      <p className="mt-3 text-sm font-medium text-foreground">Parsing {fileName}…</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Extracting schema, computing statistics, and preparing your preview.
      </p>
    </Card>
  );
}
