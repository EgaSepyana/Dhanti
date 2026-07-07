import Link from "next/link";
import {
  BarChart3,
  ExternalLink,
  FileText,
  LayoutDashboard,
  Table2,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import type { ArtifactSummary, ArtifactType } from "@/lib/types";

const ARTIFACT_ICON: Record<ArtifactType, LucideIcon> = {
  text: FileText,
  dataset: Table2,
  visualization: BarChart3,
  dashboard: LayoutDashboard,
  workflow: Workflow,
};

const ARTIFACT_LABEL: Record<ArtifactType, string> = {
  text: "Insight",
  dataset: "Dataset",
  visualization: "Chart",
  dashboard: "Dashboard",
  workflow: "Workflow",
};

/** When `onSelect` is given, the card opens the artifact inline (in the
 * workspace body / Canvas + code view) instead of navigating to the
 * dedicated permalink page — that page is still reachable via the small
 * external-link affordance for sharing or browsing version history. */
export function ArtifactCard({
  artifact,
  workspaceId,
  onSelect,
}: {
  artifact: ArtifactSummary;
  workspaceId: string;
  onSelect?: (artifactId: string) => void;
}) {
  const Icon = ARTIFACT_ICON[artifact.type] ?? FileText;

  const body = (
    <Card className="flex items-center gap-3 p-3 transition-shadow hover:shadow-md">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{artifact.title}</p>
        <p className="text-xs text-muted-foreground">
          {ARTIFACT_LABEL[artifact.type] ?? artifact.type} · v{artifact.version}
        </p>
      </div>
      {onSelect && (
        <Link
          href={`/workspace/${workspaceId}/artifact/${artifact.id}`}
          onClick={(e) => e.stopPropagation()}
          aria-label="Open full page"
          className="flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ExternalLink className="size-3.5" />
        </Link>
      )}
    </Card>
  );

  if (onSelect) {
    return (
      <button type="button" onClick={() => onSelect(artifact.id)} className="block w-full text-left">
        {body}
      </button>
    );
  }

  return <Link href={`/workspace/${workspaceId}/artifact/${artifact.id}`}>{body}</Link>;
}
