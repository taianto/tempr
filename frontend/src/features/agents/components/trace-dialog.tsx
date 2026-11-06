import { Braces, ChevronLeft, ChevronRight, Eye, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useTrace } from "../hooks/use-agents";
import type { EvaluationResult, TestSuiteItem } from "../types";

type JsonObject = Record<string, unknown>;
type TimelineStep = { label: string; value: unknown; tone: string };

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function displayValue(value: unknown) {
  return typeof value === "string" ? value : (JSON.stringify(value, null, 2) ?? String(value));
}

function labelForStep(step: unknown) {
  if (!isObject(step)) return "Step";
  const type = String(step.type ?? step.kind ?? step.event ?? step.role ?? "Step");
  return type.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function toneForStep(label: string) {
  const name = label.toLowerCase();
  if (name.includes("tool") || name.includes("action")) return "border-violet-200 bg-violet-50";
  if (name.includes("retriev") || name.includes("source")) return "border-sky-200 bg-sky-50";
  if (name.includes("assistant") || name.includes("message"))
    return "border-indigo-200 bg-indigo-50";
  return "border-slate-200 bg-slate-50";
}

function TraceStep({ step, index }: { step: TimelineStep; index: number }) {
  const value = step.value;
  const primary = isObject(value)
    ? (value.content ?? value.output ?? value.result ?? value.text)
    : value;
  const remaining = isObject(value)
    ? Object.fromEntries(
        Object.entries(value).filter(
          ([key]) => !["content", "output", "result", "text"].includes(key),
        ),
      )
    : null;
  return (
    <li className="relative pl-10">
      <span className="absolute left-0 top-1 flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-xs font-semibold tabular-nums text-slate-500">
        {index + 1}
      </span>
      <div className={`rounded-xl border p-4 ${step.tone}`}>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{step.label}</p>
        {primary !== undefined && (
          <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-800">
            {displayValue(primary)}
          </pre>
        )}
        {remaining && Object.keys(remaining).length > 0 && (
          <details className="mt-3 rounded-lg border border-white/80 bg-white/70 p-3">
            <summary className="cursor-pointer text-xs font-medium text-slate-600">
              Structured details
            </summary>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-600">
              {JSON.stringify(remaining, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </li>
  );
}

function executionFor(trace: unknown, caseId: string): JsonObject | null {
  if (!isObject(trace) || !Array.isArray(trace.executions)) return null;
  const entry = trace.executions.find(
    (candidate) => isObject(candidate) && candidate.test_case_id === caseId,
  );
  return isObject(entry) && isObject(entry.execution) ? entry.execution : null;
}

function timelineFor(execution: JsonObject): TimelineStep[] {
  const ordered = Array.isArray(execution.steps)
    ? execution.steps
    : Array.isArray(execution.messages)
      ? execution.messages
      : [];
  const timeline = ordered.map((value) => {
    const label = labelForStep(value);
    return { label, value, tone: toneForStep(label) };
  });
  if (!Array.isArray(execution.steps)) {
    for (const [key, label] of [
      ["tool_calls", "Tool call"],
      ["tool_results", "Tool result"],
      ["retrieved_information", "Retrieved information"],
    ]) {
      const values = execution[key];
      if (Array.isArray(values)) {
        timeline.push(...values.map((value) => ({ label, value, tone: toneForStep(label) })));
      }
    }
  }
  return timeline;
}

function finalResponse(execution: JsonObject): unknown {
  if (execution.final_response !== undefined) return execution.final_response;
  if (execution.output !== undefined) return execution.output;
  if (Array.isArray(execution.messages)) {
    const assistantMessages = execution.messages.filter(
      (message) =>
        isObject(message) &&
        (message.role === "assistant" || message.role === undefined) &&
        (message.content !== undefined || message.output !== undefined),
    );
    const last = assistantMessages[assistantMessages.length - 1];
    if (isObject(last)) return last.content ?? last.output;
  }
  return undefined;
}

function isNotFound(error: unknown) {
  return error instanceof Error && "status" in error && error.status === 404;
}

export function TraceDialog({
  suiteId,
  items,
  result,
  caseIndex,
  onCaseChange,
  open,
  onOpenChange,
}: {
  suiteId: string;
  items: TestSuiteItem[];
  result?: EvaluationResult;
  caseIndex: number | null;
  onCaseChange: (index: number) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const trace = useTrace(suiteId, open);
  const [showRaw, setShowRaw] = useState(false);
  const activeIndex = caseIndex ?? 0;
  const item = caseIndex === null ? undefined : items[caseIndex];
  const execution = item ? executionFor(trace.data?.trace, item.id) : null;
  const timeline = execution ? timelineFor(execution) : [];
  const response = execution ? finalResponse(execution) : undefined;
  const knownExecutionFields = new Set([
    "final_response",
    "output",
    "steps",
    "messages",
    "tool_calls",
    "tool_results",
    "retrieved_information",
  ]);
  const extraExecutionFields = execution
    ? Object.fromEntries(
        Object.entries(execution).filter(([key]) => !knownExecutionFields.has(key)),
      )
    : {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent layout="centered" aria-describedby="trace-dialog-description">
        <div className="pb-1 pr-9 pt-7 sm:pr-12 sm:pt-1">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="flex items-center gap-1.5 text-xs font-medium text-indigo-600">
                <Eye size={13} />
                Execution trace
              </p>
              <DialogTitle className="mt-1 text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
                {item
                  ? `Test ${activeIndex + 1} · ${item.category.replace(/_/g, " ")}`
                  : "Execution trace"}
              </DialogTitle>
              <DialogDescription
                id="trace-dialog-description"
                className="mt-2 max-w-3xl text-sm leading-6 text-slate-500"
              >
                {item?.question}
              </DialogDescription>
              {result && (
                <dl aria-label="Evaluation scores" className="mt-3 flex flex-wrap gap-2">
                  {[
                    ["Adherence", result.adherence_score],
                    ["Consistency", result.consistency_score],
                    ["Grounding", result.grounding_score],
                  ].map(([label, score]) => (
                    <div
                      key={label}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 text-xs"
                    >
                      <dt className="text-slate-500">{label}</dt>
                      <dd className="font-semibold tabular-nums text-slate-800">
                        {Number((Number(score) * 100).toFixed(1))}%
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
            <div className="hidden shrink-0 gap-1 sm:flex">
              <Button
                variant="outline"
                size="icon"
                aria-label="Previous test case"
                disabled={caseIndex === null || caseIndex <= 0}
                onClick={() => caseIndex !== null && onCaseChange(caseIndex - 1)}
              >
                <ChevronLeft size={16} />
              </Button>
              <Button
                variant="outline"
                size="icon"
                aria-label="Next test case"
                disabled={caseIndex === null || caseIndex >= items.length - 1}
                onClick={() => caseIndex !== null && onCaseChange(caseIndex + 1)}
              >
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-5 border-t border-slate-100 pt-5">
          {trace.isLoading ? (
            <div
              role="status"
              className="flex items-center gap-2 rounded-xl bg-slate-50 p-5 text-sm text-slate-500"
            >
              <LoaderCircle size={16} className="animate-spin" />
              Loading trace…
            </div>
          ) : trace.isError ? (
            <section className="rounded-xl border border-slate-200 bg-slate-50 p-5">
              <h3 className="font-medium text-slate-900">
                {isNotFound(trace.error)
                  ? "No trace has been uploaded"
                  : "Could not load this trace"}
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                {isNotFound(trace.error)
                  ? "Execution details will appear here after a trace is uploaded for this test suite."
                  : trace.error.message}
              </p>
              {!isNotFound(trace.error) && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => void trace.refetch()}
                >
                  Try again
                </Button>
              )}
            </section>
          ) : !execution ? (
            <section className="rounded-xl border border-dashed border-slate-200 p-5 text-sm text-slate-500">
              This test case has no execution in the uploaded trace.
            </section>
          ) : (
            <>
              <section className="overflow-hidden rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white">
                <div className="border-b border-indigo-100 px-5 py-3">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-indigo-700">
                    Final response
                  </h3>
                </div>
                <div className="p-5">
                  {response === undefined ? (
                    <p className="text-sm text-slate-500">No final response was recorded.</p>
                  ) : (
                    <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-900">
                      {displayValue(response)}
                    </pre>
                  )}
                </div>
              </section>

              <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Execution steps</h3>
                <Button variant="outline" size="sm" onClick={() => setShowRaw((value) => !value)}>
                  <Braces size={14} />
                  {showRaw ? "Hide raw JSON" : "Raw JSON"}
                </Button>
              </div>
              {!showRaw && Object.keys(extraExecutionFields).length > 0 && (
                <details className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                  <summary className="cursor-pointer text-sm font-medium text-slate-700">
                    Other execution details
                  </summary>
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-600">
                    {JSON.stringify(extraExecutionFields, null, 2)}
                  </pre>
                </details>
              )}
              {showRaw ? (
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200 bg-slate-950 p-4 text-xs leading-5 text-slate-100">
                  {JSON.stringify(execution, null, 2)}
                </pre>
              ) : timeline.length > 0 ? (
                <ol className="relative mt-4 space-y-3 before:absolute before:bottom-4 before:left-[13px] before:top-4 before:w-px before:bg-slate-200">
                  {timeline.map((step, index) => (
                    <TraceStep
                      key={
                        isObject(step.value) && typeof step.value.id === "string"
                          ? step.value.id
                          : `${step.label}-${index}`
                      }
                      step={step}
                      index={index}
                    />
                  ))}
                </ol>
              ) : (
                <p className="mt-3 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                  No steps were recorded for this execution.
                </p>
              )}
              <div className="mt-5 flex justify-between gap-2 sm:hidden">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={caseIndex === null || caseIndex <= 0}
                  onClick={() => caseIndex !== null && onCaseChange(caseIndex - 1)}
                >
                  <ChevronLeft size={15} /> Previous
                </Button>
                <span className="self-center text-xs text-slate-400">
                  {activeIndex + 1} of {items.length}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={caseIndex === null || caseIndex >= items.length - 1}
                  onClick={() => caseIndex !== null && onCaseChange(caseIndex + 1)}
                >
                  Next <ChevronRight size={15} />
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
