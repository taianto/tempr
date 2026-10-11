import { ApiError, type Agent, type AgentCreateInput, type AgentListResponse, type AgentUpdateInput, type ApiValidationError } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

type RequestOptions = { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown; signal?: AbortSignal };

async function request<T>(path: string, { method = "GET", body, signal }: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
      method,
      signal,
      headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("We couldn't reach the API. Check that the backend is running, then try again.");
  }

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail = typeof payload === "object" && payload !== null && "detail" in payload ? payload.detail : undefined;
    if (Array.isArray(detail)) {
      const validationErrors = detail.filter(isValidationError);
      throw new ApiError("The API rejected this agent. Fix the fields below and try again.", response.status, validationErrors);
    }
    throw new ApiError(typeof detail === "string" ? detail : `The API returned an error (${response.status}). Please try again.`, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function isValidationError(value: unknown): value is ApiValidationError {
  if (typeof value !== "object" || value === null) return false;
  return "loc" in value && Array.isArray(value.loc) && "msg" in value && typeof value.msg === "string" && "type" in value && typeof value.type === "string";
}

export const agentsApi = {
  list: (signal?: AbortSignal) => request<AgentListResponse>("/agents", { signal }),
  get: (id: string, signal?: AbortSignal) => request<Agent>(`/agents/${encodeURIComponent(id)}`, { signal }),
  create: (agent: AgentCreateInput) => request<Agent>("/agents", { method: "POST", body: agent }),
  update: (id: string, agent: AgentUpdateInput) => request<Agent>(`/agents/${encodeURIComponent(id)}`, { method: "PATCH", body: agent }),
  delete: (id: string) => request<void>(`/agents/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
