"use client";

import { useEffect, useRef } from "react";
import { Sparkles, User } from "lucide-react";
import { ArtifactCard } from "@/components/artifacts/artifact-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Markdown } from "./markdown";
import { ThinkingPanel } from "./thinking-panel";
import type { AgentStepEvent, ArtifactSummary, ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface StreamingTurn {
  status: string | null;
  text: string;
  artifacts: ArtifactSummary[];
  statusLog: string[];
  steps: AgentStepEvent[];
}

export function MessageList({
  messages,
  streaming,
  artifactCache,
  workspaceId,
  onSelectArtifact,
  loading = false,
}: {
  messages: ChatMessage[];
  streaming: StreamingTurn | null;
  artifactCache: Record<string, ArtifactSummary>;
  workspaceId: string;
  onSelectArtifact?: (artifactId: string) => void;
  loading?: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  if (loading) {
    return (
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        <div className="flex gap-3">
          <Skeleton className="size-8 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2 pt-1">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </div>
        <div className="flex flex-row-reverse gap-3">
          <Skeleton className="size-8 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2 pt-1">
            <Skeleton className="ml-auto h-4 w-1/3" />
          </div>
        </div>
      </div>
    );
  }

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        <EmptyState
          icon={<Sparkles className="size-6" />}
          title="Ask DHANTI about your workspace"
          description="Try “Analyze this dataset” or “Create a dashboard from sales.xlsx”."
        />
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
      {messages.map((message) => (
        <MessageRow
          key={message.id}
          message={message}
          artifactCache={artifactCache}
          workspaceId={workspaceId}
          onSelectArtifact={onSelectArtifact}
        />
      ))}

      {streaming && (
        <div className="flex gap-3">
          <Avatar role="assistant" />
          <div className="min-w-0 flex-1 space-y-2">
            <ThinkingPanel statusLog={streaming.statusLog} steps={streaming.steps} live />
            {streaming.text && (
              <div className="relative">
                <Markdown content={streaming.text} />
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-primary/60 align-middle" />
              </div>
            )}
            {streaming.artifacts.length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2">
                {streaming.artifacts.map((a) => (
                  <ArtifactCard
                    key={a.id}
                    artifact={a}
                    workspaceId={workspaceId}
                    onSelect={onSelectArtifact}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

function Avatar({ role }: { role: "user" | "assistant" | "system" }) {
  return (
    <div
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full",
        role === "user" ? "bg-muted text-muted-foreground" : "bg-primary text-primary-foreground",
      )}
    >
      {role === "user" ? <User className="size-4" /> : <Sparkles className="size-4" />}
    </div>
  );
}

function MessageRow({
  message,
  artifactCache,
  workspaceId,
  onSelectArtifact,
}: {
  message: ChatMessage;
  artifactCache: Record<string, ArtifactSummary>;
  workspaceId: string;
  onSelectArtifact?: (artifactId: string) => void;
}) {
  const artifacts = message.artifacts
    .map((id) => artifactCache[id])
    .filter((a): a is ArtifactSummary => Boolean(a));
  const agentLog = message.metadata?.agent_log as
    | { statusLog: string[]; steps: AgentStepEvent[] }
    | undefined;

  return (
    <div className="flex gap-3">
      <Avatar role={message.role} />
      <div className="min-w-0 flex-1 space-y-2">
        {agentLog && (
          <ThinkingPanel statusLog={agentLog.statusLog} steps={agentLog.steps} live={false} />
        )}
        {message.role === "assistant" ? (
          <Markdown content={message.content} />
        ) : (
          <p className="whitespace-pre-wrap text-sm text-foreground">{message.content}</p>
        )}
        {artifacts.length > 0 && (
          <div className="grid gap-2 sm:grid-cols-2">
            {artifacts.map((a) => (
              <ArtifactCard
                key={a.id}
                artifact={a}
                workspaceId={workspaceId}
                onSelect={onSelectArtifact}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
