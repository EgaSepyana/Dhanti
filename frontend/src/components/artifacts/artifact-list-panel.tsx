"use client";

import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { ArtifactCard } from "@/components/artifacts/artifact-card";
import { Skeleton } from "@/components/ui/skeleton";
import { artifactApi } from "@/lib/api";
import type { Artifact, ArtifactType } from "@/lib/types";

const TYPE_ORDER: ArtifactType[] = [
  "dashboard",
  "visualization",
  "dataset",
  "text",
  "workflow",
];

const TYPE_GROUP_LABEL: Record<ArtifactType, string> = {
  dashboard: "Dashboards",
  visualization: "Charts",
  dataset: "Datasets",
  text: "Insights",
  workflow: "Workflows",
};

export function ArtifactListPanel({
  workspaceId,
  onSelect,
}: {
  workspaceId: string;
  onSelect?: (artifactId: string) => void;
}) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    artifactApi
      .list(workspaceId)
      .then(setArtifacts)
      .finally(() => setLoading(false));
  }, [workspaceId]);

  const grouped = useMemo(() => {
    const filtered = artifacts.filter((a) =>
      a.title.toLowerCase().includes(query.trim().toLowerCase()),
    );
    const groups = new Map<ArtifactType, Artifact[]>();
    for (const type of TYPE_ORDER) groups.set(type, []);
    for (const artifact of filtered) {
      groups.get(artifact.type)?.push(artifact);
    }
    return groups;
  }, [artifacts, query]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3">
        <h2 className="mb-2 text-sm font-semibold text-foreground">Artifacts</h2>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search artifacts..."
            className="h-8 w-full rounded-md border border-border bg-background pl-8 pr-2 text-xs text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading && (
          <div className="space-y-1.5 p-1">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        )}

        {!loading && artifacts.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            No artifacts yet. Ask DHANTI to analyze your data to generate some.
          </p>
        )}

        {!loading &&
          TYPE_ORDER.map((type) => {
            const items = grouped.get(type) ?? [];
            if (items.length === 0) return null;
            return (
              <div key={type} className="mb-3">
                <p className="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {TYPE_GROUP_LABEL[type]}
                </p>
                <div className="space-y-1.5">
                  {items.map((artifact) => (
                    <ArtifactCard
                      key={artifact.id}
                      artifact={artifact}
                      workspaceId={workspaceId}
                      onSelect={onSelect}
                    />
                  ))}
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}
