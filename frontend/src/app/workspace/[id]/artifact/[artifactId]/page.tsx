"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, GitBranch } from "lucide-react";
import { ArtifactViewer } from "@/components/artifacts/artifact-viewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { artifactApi } from "@/lib/api";
import type { Artifact, ArtifactVersionSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ArtifactPage({
  params,
}: {
  params: Promise<{ id: string; artifactId: string }>;
}) {
  const { id: workspaceId, artifactId } = use(params);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [versions, setVersions] = useState<ArtifactVersionSummary[]>([]);
  const [lineage, setLineage] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([artifactApi.get(artifactId), artifactApi.versions(artifactId), artifactApi.lineage(artifactId)])
      .then(([a, v, l]) => {
        setArtifact(a);
        setVersions(v);
        setLineage(l);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load artifact"))
      .finally(() => setLoading(false));
  }, [artifactId]);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3">
        <Link
          href={`/workspace/${workspaceId}`}
          className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Back to workspace"
        >
          <ArrowLeft className="size-4" />
        </Link>
        <h1 className="flex-1 truncate text-sm font-semibold text-foreground">
          {artifact?.title ?? "Artifact"}
        </h1>
        {artifact && <Badge tone="primary">{artifact.type} · v{artifact.version}</Badge>}
      </header>

      <main className="mx-auto min-h-0 w-full max-w-5xl flex-1 overflow-y-auto p-6">
        {loading && (
          <div className="space-y-4">
            <Skeleton className="h-9 w-64" />
            <Skeleton className="h-[600px] w-full" />
          </div>
        )}

        {!loading && (error || !artifact) && (
          <div className="flex flex-col items-center gap-3 pt-12 text-center">
            <AlertCircle className="size-8 text-destructive" />
            <p className="text-sm text-muted-foreground">{error ?? "Artifact not found"}</p>
            <Link href={`/workspace/${workspaceId}`}>
              <Button variant="secondary">Back to workspace</Button>
            </Link>
          </div>
        )}

        {!loading && artifact && (
          <div className="space-y-4">
            {(versions.length > 1 || lineage.length > 0) && (
              <VersionAndLineageBar
                workspaceId={workspaceId}
                currentId={artifactId}
                versions={versions}
                lineage={lineage}
              />
            )}
            <ArtifactViewer artifact={artifact} workspaceId={workspaceId} canvasHeight={800} />
          </div>
        )}
      </main>
    </div>
  );
}

function VersionAndLineageBar({
  workspaceId,
  currentId,
  versions,
  lineage,
}: {
  workspaceId: string;
  currentId: string;
  versions: ArtifactVersionSummary[];
  lineage: Artifact[];
}) {
  return (
    <Card className="flex flex-wrap items-center gap-4 p-3">
      {versions.length > 1 && (
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Version:</span>
          {versions.map((v) => (
            <Link key={v.id} href={`/workspace/${workspaceId}/artifact/${v.id}`}>
              <span
                className={cn(
                  "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
                  v.id === currentId
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/70",
                )}
              >
                v{v.version}
              </span>
            </Link>
          ))}
        </div>
      )}

      {lineage.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <GitBranch className="size-3.5 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">Derived from:</span>
          {lineage.map((ancestor) => (
            <Link key={ancestor.id} href={`/workspace/${workspaceId}/artifact/${ancestor.id}`}>
              <Badge tone="neutral" className="cursor-pointer hover:bg-muted/70">
                {ancestor.type}: {ancestor.title}
              </Badge>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}
