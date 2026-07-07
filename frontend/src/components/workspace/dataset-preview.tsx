"use client";

import { useEffect, useState } from "react";
import { Hash, Type, Calendar, ToggleLeft, AlertTriangle, Copy } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { datasetApi } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { DatasetDetail, DatasetColumn } from "@/lib/types";

const typeIcon: Record<DatasetColumn["type"], typeof Hash> = {
  integer: Hash,
  float: Hash,
  boolean: ToggleLeft,
  datetime: Calendar,
  string: Type,
};

function KpiCard({ label, value, tone }: { label: string; value: string | number; tone?: "warning" }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={`mt-1 font-tabular text-xl font-semibold ${tone === "warning" ? "text-accent" : "text-foreground"}`}>
        {value}
      </p>
    </Card>
  );
}

function ColumnCard({ column }: { column: DatasetColumn }) {
  const Icon = typeIcon[column.type];
  const stats = column.stats;
  const summary =
    column.type === "integer" || column.type === "float"
      ? stats.mean !== undefined
        ? `avg ${formatNumber(stats.mean)}`
        : "—"
      : stats.mode
        ? `top: ${stats.mode}`
        : "—";

  return (
    <Card className="min-w-[180px] shrink-0 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5" />
        <span className="truncate text-xs font-medium uppercase tracking-wide">{column.type}</span>
      </div>
      <p className="mt-1 truncate text-sm font-semibold text-foreground" title={column.name}>
        {column.name}
      </p>
      <p className="mt-0.5 font-tabular text-xs text-muted-foreground">{summary}</p>
      {stats.null_count > 0 && (
        <div className="mt-1.5 flex items-center gap-1 text-xs text-accent">
          <AlertTriangle className="size-3" />
          {stats.null_count} null{stats.null_count === 1 ? "" : "s"}
        </div>
      )}
    </Card>
  );
}

export function DatasetPreview({ workspaceId, datasetId }: { workspaceId: string; datasetId: string }) {
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    datasetApi
      .get(workspaceId, datasetId)
      .then(setDataset)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dataset"))
      .finally(() => setLoading(false));
  }, [workspaceId, datasetId]);

  if (loading) {
    return <Skeleton className="h-64" />;
  }

  if (error || !dataset) {
    return <p className="text-sm text-destructive">{error ?? "Dataset not found"}</p>;
  }

  const columnNames = dataset.columns.map((c) => c.name);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">{dataset.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Parsed dataset · {dataset.row_count ?? 0} rows × {dataset.columns.length} columns
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Rows" value={formatNumber(dataset.profile.row_count)} />
        <KpiCard label="Columns" value={dataset.profile.column_count} />
        <KpiCard
          label="Missing values"
          value={formatNumber(dataset.profile.missing_total)}
          tone={dataset.profile.missing_total > 0 ? "warning" : undefined}
        />
        <KpiCard label="Duplicate rows" value={formatNumber(dataset.profile.duplicate_rows)} />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-foreground">Columns</h3>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {dataset.columns.map((col) => (
            <ColumnCard key={col.name} column={col} />
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Preview</h3>
          <Badge tone="neutral">
            <Copy className="size-3" />
            First {dataset.sample_rows.length} rows
          </Badge>
        </div>
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                {columnNames.map((name) => (
                  <th key={name} className="whitespace-nowrap px-3 py-2 font-medium text-muted-foreground">
                    {name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataset.sample_rows.map((row, i) => (
                <tr key={i} className="border-b border-border last:border-0 hover:bg-muted/30">
                  {columnNames.map((name) => (
                    <td key={name} className="whitespace-nowrap px-3 py-2 font-tabular text-foreground">
                      {row[name] === null || row[name] === undefined ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        String(row[name])
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
