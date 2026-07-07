import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BridgeGateway, type BridgePermissions } from "./bridge-gateway";

function fullPermissions(overrides: Partial<BridgePermissions> = {}): BridgePermissions {
  return { read: true, write: true, execute: true, ...overrides };
}

describe("BridgeGateway", () => {
  let iframe: HTMLIFrameElement;
  let detach: (() => void) | null;

  beforeEach(() => {
    iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    detach = null;
  });

  afterEach(() => {
    detach?.();
    iframe.remove();
  });

  function postToGateway(data: unknown, source: Window | null = iframe.contentWindow) {
    window.dispatchEvent(new MessageEvent("message", { data, source }));
  }

  it("ignores messages whose source is not this gateway's iframe", async () => {
    const serviceRouter = vi.fn();
    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions() },
      serviceRouter,
    });
    detach = gateway.attach();

    const otherIframe = document.createElement("iframe");
    document.body.appendChild(otherIframe);
    postToGateway(
      { type: "bridge_request", id: "r1", module: "dataset", method: "get", params: {} },
      otherIframe.contentWindow,
    );
    otherIframe.remove();

    await new Promise((r) => setTimeout(r, 0));
    expect(serviceRouter).not.toHaveBeenCalled();
  });

  it("rejects dataset.get when the artifact lacks read permission", async () => {
    const serviceRouter = vi.fn().mockResolvedValue({ columns: [] });
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions({ read: false }) },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({ type: "bridge_request", id: "r1", module: "dataset", method: "get", params: {} });
    await new Promise((r) => setTimeout(r, 0));

    expect(serviceRouter).not.toHaveBeenCalled();
    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "bridge_response",
        id: "r1",
        status: "error",
        error: expect.objectContaining({ message: expect.stringContaining("read") }),
      }),
      "*",
    );
  });

  it("rejects widget.execute when the artifact lacks read permission", async () => {
    const serviceRouter = vi.fn().mockResolvedValue({ columns: [], rows: [], row_count: 0 });
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions({ read: false }) },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({
      type: "bridge_request",
      id: "r1",
      module: "widget",
      method: "execute",
      params: { widget_id: "w1" },
    });
    await new Promise((r) => setTimeout(r, 0));

    expect(serviceRouter).not.toHaveBeenCalled();
    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "bridge_response",
        id: "r1",
        status: "error",
        error: expect.objectContaining({ message: expect.stringContaining("read") }),
      }),
      "*",
    );
  });

  it("rejects artifact.save when the artifact lacks write permission", async () => {
    const serviceRouter = vi.fn().mockResolvedValue({ ok: true });
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions({ write: false }) },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({
      type: "bridge_request",
      id: "r2",
      module: "artifact",
      method: "save",
      params: { content: {} },
    });
    await new Promise((r) => setTimeout(r, 0));

    expect(serviceRouter).not.toHaveBeenCalled();
    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "bridge_response", id: "r2", status: "error" }),
      "*",
    );
  });

  it("routes an authorized request through the service router and responds with success", async () => {
    const serviceRouter = vi.fn().mockResolvedValue({ columns: ["a"], rows: [] });
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions() },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({
      type: "bridge_request",
      id: "r3",
      module: "dataset",
      method: "get",
      params: { dataset_id: "ds1" },
    });
    await new Promise((r) => setTimeout(r, 0));

    expect(serviceRouter).toHaveBeenCalledWith("dataset", "get", { dataset_id: "ds1" });
    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "bridge_response",
        id: "r3",
        status: "success",
        data: { columns: ["a"], rows: [] },
      }),
      "*",
    );
  });

  it("rejects unknown bridge methods", async () => {
    const serviceRouter = vi.fn();
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions() },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({ type: "bridge_request", id: "r4", module: "totally", method: "unknown", params: {} });
    await new Promise((r) => setTimeout(r, 0));

    expect(serviceRouter).not.toHaveBeenCalled();
    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "bridge_response", id: "r4", status: "error" }),
      "*",
    );
  });

  it("propagates service router failures as error responses instead of throwing", async () => {
    const serviceRouter = vi.fn().mockRejectedValue(new Error("backend unreachable"));
    const postMessageSpy = vi.spyOn(iframe.contentWindow!, "postMessage");

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions() },
      serviceRouter,
    });
    detach = gateway.attach();

    postToGateway({ type: "bridge_request", id: "r5", module: "dataset", method: "get", params: {} });
    await new Promise((r) => setTimeout(r, 0));

    expect(postMessageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "bridge_response",
        id: "r5",
        status: "error",
        error: { message: "backend unreachable" },
      }),
      "*",
    );
  });

  it("forwards canvas_error and canvas_heartbeat messages to their callbacks", () => {
    const onError = vi.fn();
    const onHeartbeat = vi.fn();
    const onReady = vi.fn();

    const gateway = new BridgeGateway({
      iframeWindow: () => iframe.contentWindow,
      context: { workspaceId: "ws1", artifactId: "art1", permissions: fullPermissions() },
      serviceRouter: vi.fn(),
      onError,
      onHeartbeat,
      onReady,
    });
    detach = gateway.attach();

    postToGateway({ type: "canvas_error", message: "boom", source: "error" });
    postToGateway({ type: "canvas_heartbeat", domNodeCount: 42 });
    postToGateway({ type: "canvas_ready" });

    expect(onError).toHaveBeenCalledWith("boom", "error");
    expect(onHeartbeat).toHaveBeenCalledWith(42);
    expect(onReady).toHaveBeenCalledOnce();
  });
});
