import { artifactApi, datasetApi, widgetApi } from "@/lib/api";
import { workspaceEventBus } from "@/lib/canvas/workspace-event-bus";
import type { ServiceRouter } from "@/lib/canvas/bridge-gateway";

/** Maps bridge module.method calls to real backend requests. The network
 * call happens here, in the trusted parent context — never inside the
 * CSP-restricted iframe. workspaceId/artifactId are bound from trusted React
 * props, not from anything the iframe sends, so an artifact can only ever
 * read data scoped to its own workspace and only ever save itself. */
export function createServiceRouter(workspaceId: string, artifactId: string): ServiceRouter {
  return async (module, method, params) => {
    if (module === "dataset" && method === "get") {
      const datasetId = String(params.dataset_id ?? "");
      return datasetApi.get(workspaceId, datasetId);
    }

    if (module === "widget" && method === "execute") {
      const widgetId = String(params.widget_id ?? "");
      // /api/widgets/{id}/handler isn't nested under a workspace path (unlike
      // dataset.get above), so the widget_id an artifact sends is otherwise
      // unscoped — verify ownership here, in the trusted context, before
      // executing, so an artifact can't read another workspace's widget by id.
      const widget = await widgetApi.get(widgetId);
      if (widget.workspace_id !== workspaceId) {
        throw new Error("Widget does not belong to this workspace");
      }
      return widgetApi.execute(widgetId);
    }

    if (module === "artifact" && method === "save") {
      const content = params.content as Record<string, unknown>;
      return artifactApi.update(artifactId, { content });
    }

    if (module === "workspace" && method === "emit") {
      workspaceEventBus.emit(String(params.event ?? ""), params.data);
      return { ok: true };
    }

    throw new Error(`Unsupported bridge method '${module}.${method}'`);
  };
}
