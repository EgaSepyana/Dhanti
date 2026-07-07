"use client";

import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUp, Menu, Paperclip, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, fileApi, workspaceApi } from "@/lib/api";
import { MODEL_OPTIONS } from "@/lib/models";
import { setPendingMessage } from "@/lib/pending-message";
import type { Workspace } from "@/lib/types";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "Analyze this dataset and find key trends",
  "Create a dashboard from my sales data",
  "Summarize this PDF report",
];

const FILE_ACCEPT = ".csv,.xlsx,.xls,.pdf";

/** Landing page doubles as the "new chat" composer, ChatGPT/Claude-style:
 * typing a first message (or attaching a file) creates an auto-named
 * workspace behind the scenes and drops the user straight into the
 * conversation — no upfront name/description form. Past chats live in the
 * left sidebar, same as Claude/ChatGPT/Gemini. */
export default function Home() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [creating, setCreating] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [prompt]);

  useEffect(() => {
    workspaceApi
      .list()
      .then(setWorkspaces)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load workspaces"))
      .finally(() => setLoading(false));
  }, []);

  // Attaching a file here only stages it — no workspace exists yet, so
  // nothing is created or uploaded until the user actually sends (matches
  // "don't navigate me away just for picking a file").
  async function beginChat(message: string) {
    const trimmedMessage = message.trim();
    if (!trimmedMessage && !attachedFile) return;
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      const titleSource = trimmedMessage || attachedFile?.name || "New chat";
      const title = titleSource.length > 60 ? `${titleSource.slice(0, 57)}...` : titleSource;
      const workspace = await workspaceApi.create({ name: title });
      if (attachedFile) {
        await fileApi.upload(workspace.id, attachedFile);
      }
      if (trimmedMessage) {
        setPendingMessage(workspace.id, trimmedMessage, model || undefined);
      }
      router.push(`/workspace/${workspace.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start chat");
      setCreating(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    beginChat(prompt);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      beginChat(prompt);
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) setAttachedFile(file);
  }

  return (
    <div className="relative flex flex-1 overflow-hidden bg-background">
      <aside
        className={cn(
          "z-20 flex w-64 shrink-0 flex-col border-r border-border bg-surface transition-transform duration-200",
          "absolute inset-y-0 left-0 lg:static lg:translate-x-0",
          historyOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Logo />
          <span className="text-sm font-semibold tracking-tight text-foreground">DHANTI</span>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          <p className="px-2 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Recent chats
          </p>

          {loading && (
            <div className="space-y-1.5 p-1">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          )}

          {!loading && workspaces.length === 0 && (
            <p className="px-2 py-6 text-center text-sm text-muted-foreground">No chats yet</p>
          )}

          {!loading && workspaces.length > 0 && (
            <ul className="space-y-0.5">
              {workspaces.map((ws) => (
                <li key={ws.id}>
                  <Link
                    href={`/workspace/${ws.id}`}
                    title={ws.name}
                    className="block truncate rounded-md px-2 py-2 text-sm text-foreground hover:bg-muted"
                  >
                    {ws.name}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
      {historyOpen && (
        <div
          className="absolute inset-0 z-10 bg-black/30 lg:hidden"
          onClick={() => setHistoryOpen(false)}
          aria-hidden
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border bg-surface px-4 py-3 lg:hidden">
          <button
            onClick={() => setHistoryOpen((v) => !v)}
            aria-label="Show recent chats"
            className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Menu className="size-4" />
          </button>
          <Logo className="size-6" />
          <span className="text-sm font-semibold text-foreground">DHANTI</span>
        </header>

        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-12">
          <div className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
            <div>
              <h1 className="text-3xl font-semibold text-foreground">What are we analyzing today?</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Describe what you want — DHANTI creates a workspace for it automatically. You can
                upload files here or once you&apos;re in.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="w-full max-w-xl">
              <div className="rounded-2xl border border-border bg-surface p-3 shadow-sm focus-within:ring-2 focus-within:ring-ring">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={FILE_ACCEPT}
                  className="hidden"
                  onChange={handleFileChange}
                />
                {attachedFile && (
                  <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
                    <Paperclip className="size-3" />
                    <span className="max-w-40 truncate">{attachedFile.name}</span>
                    <button
                      type="button"
                      onClick={() => setAttachedFile(null)}
                      aria-label="Remove attachment"
                      className="hover:text-foreground"
                    >
                      <X className="size-3" />
                    </button>
                  </div>
                )}
                <textarea
                  ref={textareaRef}
                  autoFocus
                  rows={1}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Message DHANTI..."
                  className="block max-h-40 min-h-6 w-full resize-none overflow-y-auto bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none"
                />
                <div className="mt-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={creating}
                      aria-label="Attach a file"
                      className="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <Paperclip className="size-4" />
                    </button>
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      aria-label="Model for this chat"
                      className="h-8 rounded-lg border border-transparent bg-transparent px-1.5 text-xs text-muted-foreground hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {MODEL_OPTIONS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button
                    type="submit"
                    disabled={(!prompt.trim() && !attachedFile) || creating}
                    loading={creating}
                    aria-label="Start chat"
                    className="size-8 shrink-0 px-0"
                  >
                    <ArrowUp className="size-4" />
                  </Button>
                </div>
              </div>
            </form>

            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => beginChat(s)}
                  disabled={creating}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
