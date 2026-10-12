export type AgentListItem = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentListResponse = { items: AgentListItem[]; total: number };

export type Agent = AgentListItem & {
  prompt: { system: string; developer: string | null };
  model: { provider: string; name: string; parameters: Record<string, unknown> } | null;
  tools: { name: string; description: string | null; input_schema: Record<string, unknown> }[];
  metadata: Record<string, unknown>;
};

export type AgentCreateInput = {
  name: string;
  description?: string | null;
  prompt: { system: string; developer?: string | null };
  model?: { provider: string; name: string; parameters?: Record<string, unknown> } | null;
  tools?: { name: string; description?: string | null; input_schema?: Record<string, unknown>; output_schema?: Record<string, unknown> | null; metadata?: Record<string, unknown> }[];
  metadata?: Record<string, unknown>;
};

export type AgentUpdateInput = Partial<AgentCreateInput>;

export type ApiValidationError = { loc: (string | number)[]; msg: string; type: string };

export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly validationErrors: ApiValidationError[] = []) {
    super(message);
    this.name = "ApiError";
  }
}
