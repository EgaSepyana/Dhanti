import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { EChart } from "@/components/artifacts/echart";
import { CanvasWithCode } from "@/components/canvas/canvas-with-code";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { buildCanvasHtml } from "@/lib/canvas/artifact-loader";
import type { Artifact } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Renders an artifact's body by type — shared between the dedicated
 * /artifact/[artifactId] page (which adds version/lineage chrome) and the
 * inline in-body preview opened from the file/artifact lists or chat, so a
 * dashboard's live code+preview is available without leaving the workspace. */
export function ArtifactViewer({
  artifact,
  workspaceId,
  canvasHeight = 600,
}: {
  artifact: Artifact;
  workspaceId: string;
  canvasHeight?: number | "fill";
}) {
  switch (artifact.type) {
    case "text":
      return <TextArtifact content={artifact.content as unknown as { text: string }} />;
    case "dataset":
      return <DatasetArtifact content={artifact.content as unknown as DatasetArtifactContent} />;
    case "visualization":
      return (
        <VisualizationArtifact
          content={artifact.content as unknown as VisualizationArtifactContent}
        />
      );
    case "dashboard": {
      // "Dashboard" IS code generation: content.entry is a self-contained
      // HTML+CSS+JS document (see backend code_generation_agent), rendered
      // the same way any agent-authored app runs in Canvas.
      const html = String((artifact.content as { entry?: string }).entry ?? "");
      const isFill = canvasHeight === "fill";
      return (
        <div className={cn(isFill ? "flex h-full flex-col gap-3" : "space-y-3")}>
          <div className="flex shrink-0 justify-end">
            <Link href={`/workspace/${workspaceId}/dashboard/${artifact.id}`}>
              <Button variant="secondary" size="sm">
                <ExternalLink className="size-3.5" />
                Open full screen
              </Button>
            </Link>
          </div>
          <div className={cn(isFill && "min-h-0 flex-1")}>
            <CanvasWithCode
              artifact={artifact}
              workspaceId={workspaceId}
              height={canvasHeight}
              language="html"
              code={html}
              buildHtml={() => buildCanvasHtml(html)}
            />
          </div>
        </div>
      );
    }
    default:
      return (
        <Card className="p-4">
          <pre className="overflow-x-auto text-xs text-muted-foreground">
            {JSON.stringify(artifact.content, null, 2)}
          </pre>
        </Card>
      );
  }
}

function TextArtifact({ content }: { content: { text: string } }) {
  return (
    <Card className="p-6">
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{content.text}</p>
    </Card>
  );
}

interface DatasetArtifactContent {
  columns: { name: string; type: string }[];
  rows: Record<string, unknown>[];
  schema: { row_count: number; column_count: number };
}

function DatasetArtifact({ content }: { content: DatasetArtifactContent }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {content.schema.row_count} rows · {content.schema.column_count} columns
      </p>
      <Card className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              {content.columns.map((c) => (
                <th key={c.name} className="whitespace-nowrap px-3 py-2 font-medium text-muted-foreground">
                  {c.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {content.rows.slice(0, 50).map((row, i) => (
              <tr key={i} className="border-b border-border last:border-0">
                {content.columns.map((c) => (
                  <td key={c.name} className="whitespace-nowrap px-3 py-2 font-tabular text-foreground">
                    {String(row[c.name] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

interface VisualizationArtifactContent {
  config: Record<string, unknown>;
}

function VisualizationArtifact({ content }: { content: VisualizationArtifactContent }) {
  return (
    <Card className="p-4">
      <EChart option={content.config} height={420} />
    </Card>
  );
}
