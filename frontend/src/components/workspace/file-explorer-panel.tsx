"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { FileSpreadsheet, FileText, Loader2, AlertCircle, Upload } from "lucide-react";
import { ApiError, fileApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Dataset, DocumentItem, FileItem } from "@/lib/types";

const ACCEPTED = ".csv,.xlsx,.xls,.pdf";

export type Selection =
  | { type: "dataset"; id: string }
  | { type: "document"; id: string }
  | { type: "artifact"; id: string }
  | null;

function FileStatusIcon({ status }: { status: FileItem["status"] }) {
  if (status === "parsing" || status === "uploaded") {
    return <Loader2 className="size-3.5 shrink-0 animate-spin text-secondary" />;
  }
  if (status === "error") {
    return <AlertCircle className="size-3.5 shrink-0 text-destructive" />;
  }
  return null;
}

export function FileExplorerPanel({
  workspaceId,
  files,
  datasets,
  documents,
  selection,
  onSelect,
  onUploaded,
}: {
  workspaceId: string;
  files: FileItem[];
  datasets: Dataset[];
  documents: DocumentItem[];
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onUploaded: (fileId: string) => void;
}) {
  const datasetByFileId = new Map(datasets.map((d) => [d.file_id, d]));
  const documentByFileId = new Map(documents.map((d) => [d.file_id, d]));
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const res = await fileApi.upload(workspaceId, file);
      onUploaded(res.file_id);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Files</h2>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={handleFileChange}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          aria-label="Upload file"
          className="flex size-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        >
          {uploading ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
        </button>
      </div>

      {uploadError && (
        <p role="alert" className="border-b border-border px-4 py-2 text-xs text-destructive">
          {uploadError}
        </p>
      )}

      <div className="flex-1 overflow-y-auto p-2">
        {files.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            No files yet. Upload a CSV, XLSX, or PDF to get started.
          </p>
        )}

        <ul className="space-y-0.5">
          {files.map((file) => {
            const dataset = datasetByFileId.get(file.id);
            const document = documentByFileId.get(file.id);
            const isSelected =
              (dataset && selection?.type === "dataset" && selection.id === dataset.id) ||
              (document && selection?.type === "document" && selection.id === document.id);
            const clickable = Boolean(dataset || document);

            return (
              <li key={file.id}>
                <button
                  disabled={!clickable}
                  onClick={() => {
                    if (dataset) onSelect({ type: "dataset", id: dataset.id });
                    else if (document) onSelect({ type: "document", id: document.id });
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors",
                    clickable ? "cursor-pointer hover:bg-muted" : "cursor-default opacity-70",
                    isSelected && "bg-primary/10 text-primary",
                  )}
                >
                  {file.type === "pdf" ? (
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileSpreadsheet className="size-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1 truncate">{file.name}</span>
                  <FileStatusIcon status={file.status} />
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
