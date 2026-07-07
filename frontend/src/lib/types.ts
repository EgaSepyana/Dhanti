export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceDetail extends Workspace {
  files: FileItem[];
  datasets: Dataset[];
  documents: DocumentItem[];
  artifacts: { id: string; type: string; title: string; version: number }[];
}

export type FileStatus = "uploaded" | "parsing" | "parsed" | "error";

export interface FileItem {
  id: string;
  workspace_id: string;
  name: string;
  type: "csv" | "xlsx" | "xls" | "pdf";
  size_bytes: number | null;
  status: FileStatus;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface FileUploadResponse {
  file_id: string;
  status: string;
}

export interface ColumnStats {
  null_count: number;
  unique_count: number;
  min?: number | string;
  max?: number | string;
  mean?: number;
  median?: number;
  mode?: number | string | null;
  distribution?: { range?: string; value?: string; count: number }[];
}

export interface DatasetColumn {
  name: string;
  type: "integer" | "float" | "boolean" | "datetime" | "string";
  stats: ColumnStats;
}

export interface Dataset {
  id: string;
  workspace_id: string;
  file_id: string;
  name: string;
  columns: DatasetColumn[];
  row_count: number | null;
  profile: {
    row_count: number;
    column_count: number;
    missing_total: number;
    duplicate_rows: number;
    columns_with_nulls: string[];
  };
  created_at: string;
}

export interface DatasetDetail extends Dataset {
  sample_rows: Record<string, unknown>[];
}

export interface DocumentItem {
  id: string;
  workspace_id: string;
  file_id: string;
  name: string | null;
  page_count: number | null;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  structure: { headings: { text: string; page: number }[] } | null;
  chunks: { text: string; page: number; embedding_id: string | null }[] | null;
}

// "dashboard" IS code generation — content is a self-contained HTML+CSS+JS
// document (see backend code_generation_agent), not a JSON widget config.
// There is no separate "executable" type anymore; it was merged into this.
export type ArtifactType =
  | "text"
  | "dataset"
  | "visualization"
  | "dashboard"
  | "workflow";

export interface ArtifactSummary {
  id: string;
  type: ArtifactType;
  title: string;
  version: number;
}

export type WidgetType = "table" | "chart" | "metric";

export interface Widget {
  id: string;
  workspace_id: string;
  dataset_id: string;
  name: string;
  title: string;
  type: WidgetType;
  query: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WidgetExecutionResult {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
}

export interface ArtifactRelation {
  type: "derived" | "depends_on" | "visualizes" | "extends";
  target_id: string;
}

export interface Artifact {
  id: string;
  workspace_id: string;
  type: ArtifactType;
  title: string;
  description: string | null;
  content: Record<string, unknown>;
  version: number;
  parent_id: string | null;
  permissions: Record<string, boolean>;
  relations: ArtifactRelation[];
  created_at: string;
  updated_at: string;
}

export interface ArtifactVersionSummary {
  id: string;
  version: number;
  title: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export type MessageRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  artifacts: string[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface AgentStepEvent {
  step_id: string;
  agent: string;
  specialist: string;
  label: string;
  status: "running" | "success" | "error" | "partial";
}

export type ChatSSEEvent =
  | { event: "status"; data: { phase: string; message: string } }
  | { event: "agent_step"; data: AgentStepEvent }
  | { event: "code_delta"; data: { step_id: string; delta: string } }
  | { event: "text"; data: { content: string } }
  | { event: "artifact"; data: ArtifactSummary }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: Record<string, never> };
