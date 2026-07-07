"use client";

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { documentApi } from "@/lib/api";
import type { DocumentDetail } from "@/lib/types";

export function DocumentPreview({
  workspaceId,
  documentId,
}: {
  workspaceId: string;
  documentId: string;
}) {
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    documentApi
      .get(workspaceId, documentId)
      .then(setDocument)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load document"))
      .finally(() => setLoading(false));
  }, [workspaceId, documentId]);

  if (loading) {
    return <Skeleton className="h-64" />;
  }

  if (error || !document) {
    return <p className="text-sm text-destructive">{error ?? "Document not found"}</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">{document.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Parsed document · {document.page_count ?? 0} pages · {document.chunks?.length ?? 0} chunks
        </p>
      </div>

      {document.structure?.headings && document.structure.headings.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-foreground">Detected headings</h3>
          <div className="flex flex-wrap gap-2">
            {document.structure.headings.slice(0, 20).map((h, i) => (
              <Badge key={i} tone="primary">
                p.{h.page} — {h.text}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Content</h3>
        <div className="space-y-3">
          {document.chunks?.map((chunk, i) => (
            <Card key={i} className="p-4">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <FileText className="size-3.5" />
                Page {chunk.page}
              </div>
              <p className="whitespace-pre-wrap text-sm text-foreground">{chunk.text}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
