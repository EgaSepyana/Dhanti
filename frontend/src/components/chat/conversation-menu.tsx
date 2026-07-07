"use client";

import { useState } from "react";
import { History, Plus } from "lucide-react";
import type { Conversation } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

export function ConversationMenu({
  conversations,
  activeId,
  onSelect,
  onNew,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative flex items-center justify-between border-b border-border px-2 py-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <History className="size-3.5" />
        History
      </button>
      <button
        type="button"
        onClick={() => {
          onNew();
          setOpen(false);
        }}
        aria-label="New conversation"
        className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <Plus className="size-4" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
          <div className="absolute left-2 top-full z-40 mt-1 max-h-72 w-72 overflow-y-auto rounded-lg border border-border bg-surface p-1 shadow-lg">
            {conversations.length === 0 && (
              <p className="px-2 py-3 text-center text-xs text-muted-foreground">No conversations yet</p>
            )}
            {conversations.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  onSelect(c.id);
                  setOpen(false);
                }}
                className={cn(
                  "block w-full truncate rounded-md px-2 py-2 text-left text-xs",
                  c.id === activeId ? "bg-primary/10 text-primary" : "text-foreground hover:bg-muted",
                )}
              >
                {c.title || `Chat · ${formatDate(c.created_at)}`}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
