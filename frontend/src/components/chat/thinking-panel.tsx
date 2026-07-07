"use client";

import { useState } from "react";
import { AlertTriangle, Check, ChevronDown, ChevronRight, Loader2, X } from "lucide-react";
import type { AgentStepEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface AgentLog {
  statusLog: string[];
  steps: AgentStepEvent[];
}

export function ThinkingPanel({
  statusLog,
  steps,
  live,
}: AgentLog & { live: boolean }) {
  const [expanded, setExpanded] = useState(live);

  if (statusLog.length === 0 && steps.length === 0) return null;

  const isActive = live && steps.some((s) => s.status === "running");
  const groups = groupBySpecialist(steps);

  return (
    <div className="overflow-hidden rounded-md border border-border/60 bg-muted/30 text-sm">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-muted-foreground hover:text-foreground"
      >
        {expanded ? <ChevronDown className="size-3.5 shrink-0" /> : <ChevronRight className="size-3.5 shrink-0" />}
        {isActive && <Loader2 className="size-3.5 shrink-0 animate-spin" />}
        <span className="font-medium">{isActive ? "Thinking…" : "Thinking"}</span>
        {!expanded && (
          <span className="truncate text-xs text-muted-foreground/70">{statusLog.at(-1)}</span>
        )}
      </button>
      {expanded && (
        <div className="space-y-3 border-t border-border/60 px-3 py-2">
          {statusLog.length > 0 && (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {statusLog.map((message, i) => (
                <li key={i}>{message}</li>
              ))}
            </ul>
          )}
          {Object.entries(groups).map(([specialist, specialistSteps]) => (
            <div key={specialist}>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/80">
                {specialist}
              </p>
              <ul className="mt-1 space-y-1">
                {specialistSteps.map((step) => (
                  <li key={step.step_id} className="flex items-center gap-2 text-xs">
                    <StepIcon status={step.status} />
                    <span className={cn(step.status === "error" && "text-destructive")}>{step.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function groupBySpecialist(steps: AgentStepEvent[]): Record<string, AgentStepEvent[]> {
  const groups: Record<string, AgentStepEvent[]> = {};
  for (const step of steps) {
    (groups[step.specialist] ??= []).push(step);
  }
  return groups;
}

function StepIcon({ status }: { status: AgentStepEvent["status"] }) {
  if (status === "running") return <Loader2 className="size-3 shrink-0 animate-spin text-primary" />;
  if (status === "success") return <Check className="size-3 shrink-0 text-emerald-500" />;
  if (status === "error") return <X className="size-3 shrink-0 text-destructive" />;
  return <AlertTriangle className="size-3 shrink-0 text-amber-500" />;
}
