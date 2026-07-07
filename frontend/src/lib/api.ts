import type {
  Artifact,
  ArtifactType,
  ArtifactVersionSummary,
  ChatSSEEvent,
  Conversation,
  ConversationDetail,
  Dataset,
  DatasetDetail,
  DocumentDetail,
  DocumentItem,
  FileItem,
  FileUploadResponse,
  Widget,
  WidgetExecutionResult,
  WidgetType,
  Workspace,
  WorkspaceDetail,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export { ApiError };

export const workspaceApi = {
  list: () => request<Workspace[]>("/api/workspaces"),
  get: (id: string) => request<WorkspaceDetail>(`/api/workspaces/${id}`),
  create: (data: { name: string; description?: string }) =>
    request<Workspace>("/api/workspaces", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (
    id: string,
    data: { name?: string; description?: string; settings?: Record<string, unknown> },
  ) =>
    request<Workspace>(`/api/workspaces/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/api/workspaces/${id}`, { method: "DELETE" }),
};

export const fileApi = {
  list: (workspaceId: string) =>
    request<FileItem[]>(`/api/workspaces/${workspaceId}/files`),
  upload: (workspaceId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<FileUploadResponse>(`/api/workspaces/${workspaceId}/files`, {
      method: "POST",
      body: form,
    });
  },
};

export const datasetApi = {
  list: (workspaceId: string) =>
    request<Dataset[]>(`/api/workspaces/${workspaceId}/datasets`),
  get: (workspaceId: string, datasetId: string) =>
    request<DatasetDetail>(`/api/workspaces/${workspaceId}/datasets/${datasetId}`),
};

export const documentApi = {
  list: (workspaceId: string) =>
    request<DocumentItem[]>(`/api/workspaces/${workspaceId}/documents`),
  get: (workspaceId: string, documentId: string) =>
    request<DocumentDetail>(`/api/workspaces/${workspaceId}/documents/${documentId}`),
};

export const conversationApi = {
  list: (workspaceId: string) =>
    request<Conversation[]>(`/api/workspaces/${workspaceId}/conversations`),
  create: (workspaceId: string, title?: string) =>
    request<Conversation>(`/api/workspaces/${workspaceId}/conversations`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  get: (conversationId: string) =>
    request<ConversationDetail>(`/api/conversations/${conversationId}`),
};

export const artifactApi = {
  list: (workspaceId: string, type?: ArtifactType) =>
    request<Artifact[]>(
      `/api/workspaces/${workspaceId}/artifacts${type ? `?type=${type}` : ""}`,
    ),
  get: (artifactId: string) => request<Artifact>(`/api/artifacts/${artifactId}`),
  create: (
    workspaceId: string,
    data: { type: ArtifactType; title: string; description?: string; content: Record<string, unknown> },
  ) =>
    request<Artifact>(`/api/workspaces/${workspaceId}/artifacts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (
    artifactId: string,
    data: { title?: string; description?: string; content: Record<string, unknown> },
  ) =>
    request<Artifact>(`/api/artifacts/${artifactId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  versions: (artifactId: string) =>
    request<ArtifactVersionSummary[]>(`/api/artifacts/${artifactId}/versions`),
  lineage: (artifactId: string) => request<Artifact[]>(`/api/artifacts/${artifactId}/lineage`),
};

export const widgetApi = {
  list: (workspaceId: string, datasetId?: string) =>
    request<Widget[]>(
      `/api/workspaces/${workspaceId}/widgets${datasetId ? `?dataset_id=${datasetId}` : ""}`,
    ),
  get: (widgetId: string) => request<Widget>(`/api/widgets/${widgetId}`),
  create: (
    workspaceId: string,
    data: {
      dataset_id: string;
      name: string;
      title: string;
      type: WidgetType;
      query: string;
      config?: Record<string, unknown>;
    },
  ) =>
    request<Widget>(`/api/workspaces/${workspaceId}/widgets`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (
    widgetId: string,
    data: { title?: string; query?: string; config?: Record<string, unknown> },
  ) =>
    request<Widget>(`/api/widgets/${widgetId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (widgetId: string) => request<void>(`/api/widgets/${widgetId}`, { method: "DELETE" }),
  // The endpoint a rendered dashboard calls (via the Bridge API) to get a
  // widget's live data — runs its stored query fresh every call.
  execute: (widgetId: string) =>
    request<WidgetExecutionResult>(`/api/widgets/${widgetId}/handler`, { method: "POST" }),
};

/** Parses one SSE frame ("event: x\ndata: {...}") into a typed event. */
function parseSSEBlock(block: string): ChatSSEEvent | null {
  let event: string | null = null;
  let data: string | null = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice("event: ".length);
    else if (line.startsWith("data: ")) data = line.slice("data: ".length);
  }
  if (!event || data === null) return null;
  return { event, data: JSON.parse(data) } as ChatSSEEvent;
}

/** Streams a chat turn via SSE. POST + streaming body means EventSource can't
 * be used, so we read the fetch response body directly and split on frames. */
export async function* streamChat(
  conversationId: string,
  prompt: string,
  options?: { model?: string; signal?: AbortSignal },
): AsyncGenerator<ChatSSEEvent> {
  const res = await fetch(`${API_URL}/api/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, model: options?.model || undefined }),
    signal: options?.signal,
  });

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `Chat request failed: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const parsed = parseSSEBlock(block);
      if (parsed) yield parsed;
    }
  }

  if (buffer.trim()) {
    const parsed = parseSSEBlock(buffer);
    if (parsed) yield parsed;
  }
}
