export type PromptConfig = { system: string; developer?: string | null };
export type ModelConfig = { provider: string; name: string; parameters?: Record<string, unknown> };
export type ToolDefinition = {
  name: string;
  description?: string | null;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown> | null;
  metadata?: Record<string, unknown>;
};
export type AgentSchema = {
  description?: string | null;
  prompt: PromptConfig;
  model?: ModelConfig | null;
  tools?: ToolDefinition[];
  metadata?: Record<string, unknown>;
};
export type ClassificationScores = Record<
  | "happy_path"
  | "boundary_probe"
  | "missing_information"
  | "ambiguous_input"
  | "prompt_injection"
  | "policy_bypass"
  | "sensitive_data_request"
  | "hallucination_probe",
  number
>;
export type Classification = {
  id: string;
  scores: ClassificationScores;
  classifier_model: string;
  created_at: string;
  updated_at: string;
};
export type TestSuiteItem = {
  id: string;
  category: keyof ClassificationScores;
  question: string;
  expected_behavior: string;
};
export type TestSuiteStatus = "queued" | "running" | "completed" | "failed";
export type TestSuiteGeneration = {
  id: string;
  version_id: string;
  status: TestSuiteStatus;
  requested_count: number;
  allocation: Record<string, number>;
  has_completed_suite: boolean;
  error: string | null;
  created_at: string;
  updated_at: string;
};
export type TestSuite = TestSuiteGeneration & {
  items: TestSuiteItem[];
  generated_at: string | null;
};
export type EvaluationResult = {
  id: string;
  test_case_id: string;
  category: string;
  adherence_score: number;
  consistency_score: number;
  grounding_score: number;
  adherence_explanation: string;
  consistency_explanation: string;
  grounding_explanation: string;
};
export type TestSuiteEvaluation = {
  id: string;
  test_suite_id: string;
  trace_id: string;
  status: TestSuiteStatus;
  judge_model: string;
  rubric_version: string;
  classification_snapshot: Record<string, unknown>;
  error: string | null;
  created_at: string;
  updated_at: string;
  results: EvaluationResult[];
};
export type TestSuiteTrace = {
  id: string;
  test_suite_id: string;
  trace: unknown;
  created_at: string;
};
export type EvaluationSummary = {
  status: TestSuiteStatus;
  overall_score: number | null;
};
export type AgentVersionSummary = {
  id: string;
  version: string;
  created_at: string;
  classification_id: string | null;
  evaluation_summary?: EvaluationSummary | null;
};
export type AgentVersion = AgentVersionSummary & {
  agent_id: string;
  schema: AgentSchema;
  classification: Classification | null;
};
export type AgentListItem = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  latest_version: AgentVersionSummary;
};
export type AgentListResponse = { items: AgentListItem[]; total: number };
export type AgentVersionListResponse = { items: AgentVersionSummary[]; total: number };
export type Agent = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  latest_version: AgentVersion;
};
export type AgentCreateInput = {
  name: string;
  initial_version: { version?: string; schema: AgentSchema };
};
export type AgentUpdateInput = { name: string };
export type VersionCreateInput = { version: string; schema: AgentSchema };
export type ApiValidationError = { loc: (string | number)[]; msg: string; type: string };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly validationErrors: ApiValidationError[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}
