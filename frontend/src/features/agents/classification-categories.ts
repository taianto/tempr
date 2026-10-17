import type { ClassificationScores } from "./types";

export const CATEGORIES: { key: keyof ClassificationScores; label: string; color: string }[] = [
  { key: "happy_path", label: "Happy path", color: "bg-emerald-500" },
  { key: "boundary_probe", label: "Boundary probe", color: "bg-cyan-500" },
  { key: "missing_information", label: "Missing information", color: "bg-amber-500" },
  { key: "ambiguous_input", label: "Ambiguous input", color: "bg-orange-500" },
  { key: "prompt_injection", label: "Prompt injection", color: "bg-rose-500" },
  { key: "policy_bypass", label: "Policy bypass", color: "bg-violet-500" },
  { key: "sensitive_data_request", label: "Sensitive data request", color: "bg-pink-500" },
  { key: "hallucination_probe", label: "Hallucination probe", color: "bg-blue-500" },
];
