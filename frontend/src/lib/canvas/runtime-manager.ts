import { BridgeGateway, type BridgePermissions } from "@/lib/canvas/bridge-gateway";
import { createServiceRouter } from "@/lib/canvas/service-router";
import { workspaceEventBus } from "@/lib/canvas/workspace-event-bus";

const HEARTBEAT_TIMEOUT_MS = 30_000;
const DOM_NODE_LIMIT = 10_000;
const HANG_CHECK_INTERVAL_MS = 2_000;

/** Owns a single canvas instance's lifecycle: wires the Bridge Gateway to the
 * iframe, watches heartbeats for hangs/DOM-limit violations, and forwards
 * workspace-bus events into the iframe. One instance per mounted <Canvas>. */
export class RuntimeManager {
  private readonly getIframeWindow: () => Window | null;
  private lastHeartbeatAt = Date.now();
  private detachGateway: (() => void) | null = null;
  private unsubscribeBus: (() => void) | null = null;
  private hangCheckTimer: ReturnType<typeof setInterval> | null = null;

  constructor(options: {
    iframeWindow: () => Window | null;
    workspaceId: string;
    artifactId: string;
    permissions: BridgePermissions;
    onCrash: (message: string) => void;
  }) {
    this.getIframeWindow = options.iframeWindow;

    const gateway = new BridgeGateway({
      iframeWindow: this.getIframeWindow,
      context: {
        workspaceId: options.workspaceId,
        artifactId: options.artifactId,
        permissions: options.permissions,
      },
      serviceRouter: createServiceRouter(options.workspaceId, options.artifactId),
      onError: (message) => options.onCrash(message),
      onHeartbeat: (domNodeCount) => {
        this.lastHeartbeatAt = Date.now();
        if (domNodeCount > DOM_NODE_LIMIT) {
          options.onCrash(`DOM node limit exceeded (${domNodeCount} > ${DOM_NODE_LIMIT})`);
        }
      },
    });

    this.detachGateway = gateway.attach();

    this.unsubscribeBus = workspaceEventBus.subscribe((event, data) => {
      this.getIframeWindow()?.postMessage({ type: "bridge_event", event, data }, "*");
    });

    this.hangCheckTimer = setInterval(() => {
      if (Date.now() - this.lastHeartbeatAt > HEARTBEAT_TIMEOUT_MS) {
        options.onCrash("Artifact stopped responding (execution timeout)");
      }
    }, HANG_CHECK_INTERVAL_MS);
  }

  /** Tears down listeners/timers. The caller is responsible for actually
   * removing/remounting the iframe element — that's what forcibly kills a
   * hung script, since DOM removal happens on the browser's side regardless
   * of what the iframe's JS thread is doing. */
  destroy(): void {
    this.detachGateway?.();
    this.unsubscribeBus?.();
    if (this.hangCheckTimer) clearInterval(this.hangCheckTimer);
  }
}
