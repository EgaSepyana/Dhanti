export interface BridgePermissions {
  read: boolean;
  write: boolean;
  execute: boolean;
}

export interface BridgeContext {
  workspaceId: string;
  artifactId: string;
  permissions: BridgePermissions;
}

export type ServiceRouter = (
  module: string,
  method: string,
  params: Record<string, unknown>,
) => Promise<unknown>;

interface BridgeRequestMessage {
  type: "bridge_request";
  id: string;
  module: string;
  method: string;
  params?: Record<string, unknown>;
}

/** Which permission each bridge method requires. Methods not listed here are rejected outright. */
const REQUIRED_PERMISSION: Record<string, keyof BridgePermissions> = {
  "dataset.get": "read",
  "widget.execute": "read",
  "artifact.save": "write",
  "workspace.emit": "write",
};

export class PermissionDeniedError extends Error {}

export class BridgeGateway {
  private readonly getIframeWindow: () => Window | null;
  private readonly context: BridgeContext;
  private readonly serviceRouter: ServiceRouter;
  private readonly onError?: (message: string, source: string) => void;
  private readonly onHeartbeat?: (domNodeCount: number) => void;
  private readonly onReady?: () => void;
  private readonly listener: (event: MessageEvent) => void;

  constructor(options: {
    iframeWindow: () => Window | null;
    context: BridgeContext;
    serviceRouter: ServiceRouter;
    onError?: (message: string, source: string) => void;
    onHeartbeat?: (domNodeCount: number) => void;
    onReady?: () => void;
  }) {
    this.getIframeWindow = options.iframeWindow;
    this.context = options.context;
    this.serviceRouter = options.serviceRouter;
    this.onError = options.onError;
    this.onHeartbeat = options.onHeartbeat;
    this.onReady = options.onReady;
    this.listener = (event: MessageEvent) => this.handleMessage(event);
  }

  /** Starts listening for messages from this gateway's iframe. Returns a cleanup function. */
  attach(): () => void {
    window.addEventListener("message", this.listener);
    return () => window.removeEventListener("message", this.listener);
  }

  private handleMessage(event: MessageEvent): void {
    // A sandboxed iframe without allow-same-origin reports event.origin as the
    // literal string "null" for every message, so origin can't distinguish
    // frames. The parent holds a direct reference to its own iframe's
    // contentWindow regardless of origin — that's what we validate instead.
    if (event.source !== this.getIframeWindow()) return;

    const msg = event.data as { type?: string } | null;
    if (!msg || typeof msg !== "object") return;

    switch (msg.type) {
      case "bridge_request":
        void this.routeRequest(msg as BridgeRequestMessage);
        break;
      case "canvas_error": {
        const errMsg = msg as { message?: unknown; source?: unknown };
        this.onError?.(String(errMsg.message ?? "Unknown error"), String(errMsg.source ?? "unknown"));
        break;
      }
      case "canvas_heartbeat": {
        const hbMsg = msg as { domNodeCount?: unknown };
        this.onHeartbeat?.(Number(hbMsg.domNodeCount ?? 0));
        break;
      }
      case "canvas_ready":
        this.onReady?.();
        break;
      default:
        break;
    }
  }

  private async routeRequest(msg: BridgeRequestMessage): Promise<void> {
    try {
      this.validatePermission(msg.module, msg.method);
      const data = await this.serviceRouter(msg.module, msg.method, msg.params ?? {});
      this.respond(msg.id, "success", data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Bridge request failed";
      this.respond(msg.id, "error", undefined, message);
    }
  }

  private validatePermission(module: string, method: string): void {
    const key = `${module}.${method}`;
    const required = REQUIRED_PERMISSION[key];
    if (!required) {
      throw new PermissionDeniedError(`Unknown bridge method '${key}'`);
    }
    if (!this.context.permissions[required]) {
      throw new PermissionDeniedError(`Artifact lacks '${required}' permission for '${key}'`);
    }
  }

  private respond(id: string, status: "success" | "error", data?: unknown, errorMessage?: string): void {
    const target = this.getIframeWindow();
    if (!target) return;
    target.postMessage(
      {
        type: "bridge_response",
        id,
        status,
        data,
        error: errorMessage ? { message: errorMessage } : undefined,
      },
      "*",
    );
  }
}
