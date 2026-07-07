"use client";

import { type ChangeEvent, type KeyboardEvent, useRef, useState } from "react";
import { ArrowUp, Loader2, Paperclip, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, fileApi } from "@/lib/api";
import { MODEL_OPTIONS } from "@/lib/models";

const ACCEPTED = ".csv,.xlsx,.xls,.pdf";

export function MessageInput({
  onSend,
  disabled,
  workspaceId,
  onFileUploaded,
}: {
  onSend: (prompt: string, model?: string) => void;
  disabled: boolean;
  workspaceId: string;
  onFileUploaded?: (fileId: string) => void;
}) {
  const [value, setValue] = useState("");
  const [model, setModel] = useState("");
  const [uploading, setUploading] = useState(false);
  const [attachedFileName, setAttachedFileName] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, model || undefined);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const res = await fileApi.upload(workspaceId, file);
      setAttachedFileName(file.name);
      onFileUploaded?.(res.file_id);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="border-t border-border bg-surface p-3">
      {(attachedFileName || uploadError) && (
        <div className="mb-2 flex items-center gap-2">
          {uploadError ? (
            <span role="alert" className="text-xs text-destructive">
              {uploadError}
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
              <Paperclip className="size-3" />
              {attachedFileName}
              <button
                type="button"
                onClick={() => setAttachedFileName(null)}
                aria-label="Dismiss attachment notice"
                className="hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            </span>
          )}
        </div>
      )}

      <div className="flex items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={handleFileChange}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || uploading}
          aria-label="Attach a file"
          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          {uploading ? <Loader2 className="size-4 animate-spin" /> : <Paperclip className="size-4" />}
        </button>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about your data..."
          rows={1}
          className="max-h-32 flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
        />
        <Button
          size="md"
          className="shrink-0 px-3"
          disabled={disabled || !value.trim()}
          onClick={submit}
          aria-label="Send message"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>

      <select
        value={model}
        onChange={(e) => setModel(e.target.value)}
        aria-label="Model for this message"
        className="mt-2 h-6 rounded-md border border-transparent bg-transparent text-xs text-muted-foreground hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {MODEL_OPTIONS.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
    </div>
  );
}
