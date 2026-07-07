"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { CanvasWithCode } from "@/components/canvas/canvas-with-code";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { artifactApi } from "@/lib/api";
import { buildCanvasHtml } from "@/lib/canvas/artifact-loader";
import type { Artifact } from "@/lib/types";

/** Full-screen dashboard view — a dashboard is code (see backend
 * code_generation_agent): content.entry is a self-contained HTML+CSS+JS
 * document, rendered the same way as the embedded preview in the artifact
 * viewer via the Bridge API, just given the whole viewport. */
export default function DashboardViewerPage({
  params,
}: {
  params: Promise<{ id: string; dashboardId: string }>;
}) {
  const { id: workspaceId, dashboardId } = use(params);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    artifactApi
      .get(dashboardId)
      .then((a) => {
        if (a.type !== "dashboard") {
          throw new Error("This artifact is not a dashboard");
        }
        setArtifact(a);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, [dashboardId]);

  return (
    <div className="flex h-dvh flex-col bg-background">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3">
        <Link
          href={`/workspace/${workspaceId}/artifact/${dashboardId}`}
          className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Back to artifact"
        >
          <ArrowLeft className="size-4" />
        </Link>
        <h1 className="truncate text-sm font-semibold text-foreground">
          {artifact?.title ?? "Dashboard"}
        </h1>
      </header>

      <main className="flex flex-1 flex-col overflow-hidden p-4">
        {loading && <Skeleton className="h-full w-full" />}

        {!loading && (error || !artifact) && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <AlertCircle className="size-8 text-destructive" />
            <p className="text-sm text-muted-foreground">{error ?? "Dashboard not found"}</p>
            <Link href={`/workspace/${workspaceId}`}>
              <Button variant="secondary">Back to workspace</Button>
            </Link>
          </div>
        )}

        {!loading && artifact && (
          <CanvasWithCode
            artifact={artifact}
            workspaceId={workspaceId}
            height="fill"
            language="html"
            code={String((artifact.content as { entry?: string }).entry ?? "")}
            buildHtml={() =>
              buildCanvasHtml(String((artifact.content as { entry?: string }).entry ?? ""))
            }
          />
        )}
      </main>
    </div>
  );
}
