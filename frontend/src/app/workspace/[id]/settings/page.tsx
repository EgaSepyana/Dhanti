"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { workspaceApi } from "@/lib/api";
import { MODEL_OPTIONS } from "@/lib/models";
import type { Workspace } from "@/lib/types";

const LANGUAGE_OPTIONS = [
  { value: "", label: "Default (match the user's prompt)" },
  { value: "English", label: "English" },
  { value: "Spanish", label: "Spanish" },
  { value: "French", label: "French" },
  { value: "German", label: "German" },
  { value: "Indonesian", label: "Indonesian" },
  { value: "Japanese", label: "Japanese" },
];

export default function WorkspaceSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: workspaceId } = use(params);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [language, setLanguage] = useState("");
  const [model, setModel] = useState("");

  useEffect(() => {
    workspaceApi
      .get(workspaceId)
      .then((w) => {
        setWorkspace(w);
        setName(w.name);
        setDescription(w.description ?? "");
        setLanguage(String(w.settings.language ?? ""));
        setModel(String(w.settings.model ?? ""));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load workspace"))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await workspaceApi.update(workspaceId, {
        name: name.trim(),
        description: description.trim() || undefined,
        settings: { language: language || undefined, model: model || undefined },
      });
      setWorkspace(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

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
        <h1 className="truncate text-sm font-semibold text-foreground">
          {workspace?.name ?? "Workspace"} settings
        </h1>
      </header>

      <main className="mx-auto min-h-0 w-full max-w-2xl flex-1 overflow-y-auto p-4 sm:p-6">
        {loading && (
          <div className="space-y-6">
            <Card className="space-y-4 p-5">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-20 w-full" />
            </Card>
            <Card className="space-y-4 p-5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </Card>
          </div>
        )}

        {!loading && !workspace && (
          <div className="flex flex-col items-center gap-3 pt-12 text-center">
            <AlertCircle className="size-8 text-destructive" />
            <p className="text-sm text-muted-foreground">{error ?? "Workspace not found"}</p>
          </div>
        )}

        {!loading && workspace && (
          <div className="space-y-6">
            <Card className="space-y-4 p-5">
              <h2 className="text-sm font-semibold text-foreground">General</h2>
              <div className="space-y-1.5">
                <label htmlFor="ws-name" className="text-sm font-medium text-foreground">
                  Name
                </label>
                <input
                  id="ws-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="ws-desc" className="text-sm font-medium text-foreground">
                  Description
                </label>
                <textarea
                  id="ws-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
            </Card>

            <Card className="space-y-4 p-5">
              <h2 className="text-sm font-semibold text-foreground">AI preferences</h2>
              <p className="text-xs text-muted-foreground">
                Applies to chat responses in this workspace only.
              </p>
              <div className="space-y-1.5">
                <label htmlFor="ws-language" className="text-sm font-medium text-foreground">
                  Response language
                </label>
                <select
                  id="ws-language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="ws-model" className="text-sm font-medium text-foreground">
                  Preferred model
                </label>
                <select
                  id="ws-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {MODEL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  Used for this workspace&apos;s chat replies. If the selected model&apos;s
                  provider is unavailable, DHANTI automatically falls back to Groq.
                </p>
              </div>
            </Card>

            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}

            <div className="flex items-center gap-3">
              <Button onClick={handleSave} loading={saving}>
                Save changes
              </Button>
              {saved && (
                <span className="flex items-center gap-1 text-sm text-success">
                  <Check className="size-4" />
                  Saved
                </span>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
