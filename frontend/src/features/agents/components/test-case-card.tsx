import { ChevronDown, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { EvaluationResult, TestSuiteItem } from "../types";

const dimensions = [
  ["adherence", "Adherence"],
  ["consistency", "Consistency"],
  ["grounding", "Grounding"],
] as const;

function scoreText(score: number) {
  return `${Number((score * 100).toFixed(1))}%`;
}

export function TestCaseCard({
  item,
  categoryLabel,
  index,
  result,
  expanded,
  onToggle,
  onViewTrace,
}: {
  item: TestSuiteItem;
  categoryLabel: string;
  index: number;
  result?: EvaluationResult;
  expanded: boolean;
  onToggle: () => void;
  onViewTrace: () => void;
}) {
  const breakdownId = `evaluation-breakdown-${item.id}`;
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-sm font-semibold text-indigo-700">
            {index + 1}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
            {categoryLabel}
          </span>
        </div>
        {result && (
          <dl className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
            {dimensions.map(([key, label]) => (
              <div key={key} className="inline-flex items-center gap-1.5">
                <dt className="text-slate-400">{label}</dt>
                <dd className="font-medium tabular-nums text-slate-700">
                  {scoreText(result[`${key}_score`])}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      <div className="mt-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Question</h2>
        <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{item.question}</p>
      </div>
      <div className="mt-4 border-t border-slate-100 pt-4">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Acceptance criteria
        </h3>
        <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
          {item.expected_behavior}
        </p>
      </div>

      {result && (
        <div
          className="grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none"
          style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
        >
          <div className="min-h-0 overflow-hidden" id={breakdownId}>
            <dl className="mt-4 grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-3">
              {dimensions.map(([key, label]) => (
                <div key={key} className="rounded-xl bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <dt className="text-sm font-medium text-slate-800">{label}</dt>
                    <dd className="text-sm font-semibold tabular-nums text-indigo-700">
                      {scoreText(result[`${key}_score`])}
                    </dd>
                  </div>
                  <dd className="mt-2 text-sm leading-6 text-slate-600">
                    {result[`${key}_explanation`]}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
        {result && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-expanded={expanded}
            aria-controls={breakdownId}
            onClick={onToggle}
            className="px-2 text-slate-600"
          >
            <ChevronDown
              size={15}
              className={`transition-transform duration-200 motion-reduce:transition-none ${expanded ? "rotate-180" : ""}`}
            />
            {expanded ? "Hide breakdown" : "View breakdown"}
          </Button>
        )}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onViewTrace}
          className="px-2 text-slate-600"
        >
          <Eye size={15} />
          View trace &amp; response
        </Button>
      </div>
    </article>
  );
}
