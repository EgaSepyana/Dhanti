"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/** Guards against unexpected exceptions in our own canvas-rendering code
 * (e.g. malformed artifact content). A JS error thrown inside the sandboxed
 * iframe itself never reaches this boundary — that isolation is inherent to
 * iframes and is instead reported via the Bridge's canvas_error message. */
export class CanvasErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center">
          <AlertTriangle className="size-6 text-destructive" />
          <p className="text-sm text-muted-foreground">This artifact failed to render.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
