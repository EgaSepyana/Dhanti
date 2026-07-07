"use client";

import { useEffect, useRef, useState } from "react";
import { artifactApi, conversationApi, streamChat } from "@/lib/api";
import { takePendingMessage } from "@/lib/pending-message";
import type { ArtifactSummary, ChatMessage, Conversation } from "@/lib/types";
import { ConversationMenu } from "./conversation-menu";
import { MessageInput } from "./message-input";
import { MessageList, type StreamingTurn } from "./message-list";

export interface LiveCode {
  stepId: string;
  code: string;
  done: boolean;
}

export function ChatPanel({
  workspaceId,
  onSelectArtifact,
  onFileUploaded,
  onLiveCode,
}: {
  workspaceId: string;
  onSelectArtifact?: (artifactId: string) => void;
  onFileUploaded?: (fileId: string) => void;
  onLiveCode?: (payload: LiveCode | null) => void;
}) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState<StreamingTurn | null>(null);
  const [artifactCache, setArtifactCache] = useState<Record<string, ArtifactSummary>>({});
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const liveCodeRef = useRef<{ stepId: string; code: string } | null>(null);

  useEffect(() => {
    let cancelled = false;

    conversationApi
      .list(workspaceId)
      .then(async (list) => {
        if (cancelled) return;
        setConversations(list);
        const pending = takePendingMessage(workspaceId);

        if (list.length > 0 && !pending) {
          await openConversation(list[0].id);
          return;
        }

        const created = await conversationApi.create(workspaceId);
        if (cancelled) return;
        setConversationId(created.id);
        setConversations((prev) => [created, ...prev]);
        setMessages([]);
        if (pending) handleSend(pending.message, pending.model, created.id);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  async function openConversation(id: string) {
    const detail = await conversationApi.get(id);
    setConversationId(detail.id);
    setMessages(detail.messages);
    setStreaming(null);
    setError(null);

    const missingIds = Array.from(new Set(detail.messages.flatMap((m) => m.artifacts))).filter(
      (aid) => !artifactCache[aid],
    );
    if (missingIds.length > 0) {
      const fetched = await Promise.all(missingIds.map((aid) => artifactApi.get(aid).catch(() => null)));
      setArtifactCache((prev) => {
        const next = { ...prev };
        for (const artifact of fetched) {
          if (artifact) next[artifact.id] = artifact;
        }
        return next;
      });
    }
  }

  async function startNewConversation() {
    const created = await conversationApi.create(workspaceId);
    setConversationId(created.id);
    setConversations((prev) => [created, ...prev]);
    setMessages([]);
    setStreaming(null);
    setError(null);
  }

  async function handleSend(prompt: string, model?: string, conversationIdOverride?: string) {
    const activeConversationId = conversationIdOverride ?? conversationId;
    if (!activeConversationId) return;
    setError(null);
    liveCodeRef.current = null;
    onLiveCode?.(null);

    setMessages((prev) => [
      ...prev,
      {
        id: `local-user-${crypto.randomUUID()}`,
        conversation_id: activeConversationId,
        role: "user",
        content: prompt,
        artifacts: [],
        metadata: {},
        created_at: new Date().toISOString(),
      },
    ]);
    setStreaming({ status: "Thinking...", text: "", artifacts: [], statusLog: [], steps: [] });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const event of streamChat(activeConversationId, prompt, { model, signal: controller.signal })) {
        if (event.event === "status") {
          setStreaming((prev) =>
            prev
              ? { ...prev, status: event.data.message, statusLog: [...prev.statusLog, event.data.message] }
              : prev,
          );
        } else if (event.event === "agent_step") {
          const step = event.data;
          setStreaming((prev) => {
            if (!prev) return prev;
            const idx = prev.steps.findIndex((s) => s.step_id === step.step_id);
            const steps =
              idx >= 0
                ? prev.steps.map((s, i) => (i === idx ? step : s))
                : [...prev.steps, step];
            return { ...prev, steps };
          });
          if (
            step.status !== "running" &&
            liveCodeRef.current &&
            liveCodeRef.current.stepId === step.step_id
          ) {
            onLiveCode?.({ ...liveCodeRef.current, done: true });
          }
        } else if (event.event === "code_delta") {
          const { step_id, delta } = event.data;
          if (!liveCodeRef.current || liveCodeRef.current.stepId !== step_id) {
            liveCodeRef.current = { stepId: step_id, code: "" };
          }
          liveCodeRef.current.code += delta;
          onLiveCode?.({ ...liveCodeRef.current, done: false });
        } else if (event.event === "text") {
          const content = event.data.content;
          setStreaming((prev) =>
            prev ? { ...prev, status: null, text: prev.text + content } : prev,
          );
        } else if (event.event === "artifact") {
          const artifact = event.data;
          setArtifactCache((prev) => ({ ...prev, [artifact.id]: artifact }));
          setStreaming((prev) =>
            prev ? { ...prev, artifacts: [...prev.artifacts, artifact] } : prev,
          );
          // Cached for the card in chat to render, but Canvas stays closed
          // until the user explicitly clicks it — no auto-open on generation.
        } else if (event.event === "error") {
          setError(event.data.message);
          setStreaming(null);
        } else if (event.event === "done") {
          finalizeStreamingTurn(activeConversationId);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed. Please try again.");
      setStreaming(null);
    }
  }

  function finalizeStreamingTurn(conversationId: string) {
    setStreaming((current) => {
      if (current) {
        setMessages((prev) => [
          ...prev,
          {
            id: `local-assistant-${crypto.randomUUID()}`,
            conversation_id: conversationId,
            role: "assistant",
            content: current.text,
            artifacts: current.artifacts.map((a) => a.id),
            metadata: { agent_log: { statusLog: current.statusLog, steps: current.steps } },
            created_at: new Date().toISOString(),
          },
        ]);
      }
      return null;
    });
  }

  return (
    <div className="flex h-full flex-col">
      <ConversationMenu
        conversations={conversations}
        activeId={conversationId}
        onSelect={openConversation}
        onNew={startNewConversation}
      />
      <MessageList
        messages={messages}
        streaming={streaming}
        artifactCache={artifactCache}
        workspaceId={workspaceId}
        onSelectArtifact={onSelectArtifact}
        loading={loadingHistory}
      />
      {error && (
        <p role="alert" className="border-t border-border px-4 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
      <MessageInput
        onSend={handleSend}
        disabled={!conversationId || streaming !== null}
        workspaceId={workspaceId}
        onFileUploaded={onFileUploaded}
      />
    </div>
  );
}
