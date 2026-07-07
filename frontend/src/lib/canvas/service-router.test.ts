import { beforeEach, describe, expect, it, vi } from "vitest";

const { widgetApiMock, datasetApiMock, artifactApiMock } = vi.hoisted(() => ({
  widgetApiMock: { get: vi.fn(), execute: vi.fn() },
  datasetApiMock: { get: vi.fn() },
  artifactApiMock: { update: vi.fn() },
}));

vi.mock("@/lib/api", () => ({
  widgetApi: widgetApiMock,
  datasetApi: datasetApiMock,
  artifactApi: artifactApiMock,
}));

vi.mock("@/lib/canvas/workspace-event-bus", () => ({
  workspaceEventBus: { emit: vi.fn() },
}));

import { createServiceRouter } from "./service-router";

describe("createServiceRouter widget.execute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("executes a widget that belongs to the current workspace", async () => {
    widgetApiMock.get.mockResolvedValue({ id: "w1", workspace_id: "ws1" });
    widgetApiMock.execute.mockResolvedValue({ columns: ["a"], rows: [], row_count: 0 });

    const router = createServiceRouter("ws1", "art1");
    const result = await router("widget", "execute", { widget_id: "w1" });

    expect(widgetApiMock.execute).toHaveBeenCalledWith("w1");
    expect(result).toEqual({ columns: ["a"], rows: [], row_count: 0 });
  });

  it("rejects executing a widget that belongs to a different workspace", async () => {
    // /api/widgets/{id}/handler isn't nested under a workspace path, so this
    // ownership check has to happen client-side in the trusted router — a
    // malicious/buggy artifact must not be able to read another workspace's
    // widget just by guessing/sending its id.
    widgetApiMock.get.mockResolvedValue({ id: "w1", workspace_id: "some-other-workspace" });

    const router = createServiceRouter("ws1", "art1");

    await expect(router("widget", "execute", { widget_id: "w1" })).rejects.toThrow(
      "does not belong to this workspace",
    );
    expect(widgetApiMock.execute).not.toHaveBeenCalled();
  });
});
