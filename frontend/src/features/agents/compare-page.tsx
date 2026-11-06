import { type Query, useQueries } from "@tanstack/react-query";
import { ChevronDown, Plus, X } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { testSuitesApi, versionsApi } from "./api";
import { CATEGORIES } from "./classification-categories";
import { WorkspaceLayout } from "./components/workspace-layout";
import {
  aggregateEvaluation,
  compareScores,
  type EvaluationAggregate,
  RUBRIC_DIMENSIONS,
} from "./evaluation-comparison";
import { agentKeys, useAgent, useVersions } from "./hooks/use-agents";
import type { TestSuite, TestSuiteEvaluation } from "./types";

function AddVersionMenu({
  candidates,
  onAdd,
}: {
  candidates: { id: string; version: string }[];
  onAdd: (id: string) => void;
}) {
  return (
    <details className="relative inline-block">
      <summary
        aria-label="Add a version to comparison"
        title="Add version"
        className="flex h-7 w-7 cursor-pointer list-none items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 hover:border-indigo-300 hover:text-indigo-600 [&::-webkit-details-marker]:hidden"
      >
        <Plus size={15} />
      </summary>
      <div
        role="menu"
        className="absolute right-0 top-9 z-20 min-w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-card"
      >
        {candidates.length ? (
          candidates.map((item) => (
            <button
              type="button"
              role="menuitem"
              key={item.id}
              onClick={(event) => {
                onAdd(item.id);
                const parent = event.currentTarget.closest("details");
                if (parent) parent.open = false;
              }}
              className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              Version {item.version}
            </button>
          ))
        ) : (
          <p className="px-3 py-2 text-xs text-slate-400">No other versions available</p>
        )}
      </div>
    </details>
  );
}

function formatScore(value: number) {
  return `${Number((value * 100).toFixed(1))}%`;
}

type ColumnState = {
  aggregate?: EvaluationAggregate;
  status: string;
  error?: string;
  retry?: () => void;
};

function ScoreCell({
  value,
  reference,
  referenceVersion,
  isReference,
}: {
  value?: number;
  reference?: number;
  referenceVersion?: string;
  isReference: boolean;
}) {
  if (value === undefined) return <span className="text-xs text-slate-400">—</span>;
  const direction = isReference ? undefined : compareScores(value, reference);
  return (
    <span
      role="img"
      className="inline-flex items-center gap-1.5 tabular-nums"
      aria-label={`${formatScore(value)}${direction ? `, ${direction} than reference version ${referenceVersion}` : ""}`}
    >
      {formatScore(value)}
      {direction && (
        <span
          aria-hidden="true"
          title={`${direction === "higher" ? "Higher" : "Lower"} than reference version ${referenceVersion}`}
          className={
            direction === "higher"
              ? "font-semibold text-emerald-600"
              : "font-semibold text-rose-600"
          }
        >
          {direction === "higher" ? "↑" : "↓"}
        </span>
      )}
    </span>
  );
}

export function ComparePage() {
  const { agentId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const agent = useAgent(agentId);
  const versions = useVersions(agentId);
  const raw = searchParams.get("versions");
  const selectedIds = raw
    ? [
        ...new Set(
          raw
            .split(",")
            .map((id) => id.trim())
            .filter(Boolean),
        ),
      ]
    : [];

  useEffect(() => {
    if (raw === null && agent.data?.latest_version.id)
      setSearchParams({ versions: agent.data.latest_version.id }, { replace: true });
  }, [raw, agent.data?.latest_version.id, setSearchParams]);

  const columns = useQueries({
    queries: selectedIds.map((versionId) => ({
      queryKey: agentKeys.version(versionId),
      queryFn: ({ signal }: { signal: AbortSignal }) => versionsApi.get(versionId, signal),
      enabled: Boolean(agentId && versionId),
      retry: (count: number, error: Error & { status?: number }) =>
        error.status !== 404 && count < 1,
    })),
  });
  const suites = useQueries({
    queries: selectedIds.map((versionId, index) => ({
      queryKey: agentKeys.testSuite(versionId),
      queryFn: ({ signal }: { signal: AbortSignal }) => testSuitesApi.get(versionId, signal),
      enabled: columns[index]?.data?.agent_id === agentId,
      refetchOnWindowFocus: true,
      refetchInterval: (query: Query<TestSuite | null>) =>
        query.state.data?.status === "queued" || query.state.data?.status === "running"
          ? 2_000
          : false,
    })),
  });
  const evaluations = useQueries({
    queries: selectedIds.map((versionId, index) => ({
      queryKey: agentKeys.evaluation(suites[index]?.data?.id ?? `pending:${versionId}`),
      queryFn: ({ signal }: { signal: AbortSignal }) => {
        const suiteId = suites[index]?.data?.id;
        if (!suiteId) throw new Error("Test suite is unavailable");
        return testSuitesApi.evaluation(suiteId, signal);
      },
      enabled: Boolean(suites[index]?.data?.has_completed_suite && suites[index]?.data?.id),
      refetchOnWindowFocus: true,
      retry: (count: number, error: Error & { status?: number }) =>
        error.status !== 404 && count < 1,
      refetchInterval: (query: Query<TestSuiteEvaluation>) =>
        query.state.data?.status === "queued" || query.state.data?.status === "running"
          ? 2_000
          : false,
    })),
  });

  const selectedSet = new Set(selectedIds);
  const candidates = (versions.data?.items ?? []).filter((version) => !selectedSet.has(version.id));
  const states: ColumnState[] = selectedIds.map((_, index) => {
    const version = columns[index]?.data;
    const suite = suites[index]?.data;
    const evaluation = evaluations[index]?.data;
    const suiteQuery = suites[index];
    const evaluationQuery = evaluations[index];
    const retry = () => {
      if (suiteQuery?.isError) void suiteQuery.refetch();
      else if (evaluationQuery?.isError) void evaluationQuery.refetch();
      else void columns[index]?.refetch();
    };

    if (columns[index]?.data && version?.agent_id !== agentId)
      return { status: "Unavailable version" };
    if (columns[index]?.isError)
      return { status: "Could not load version", error: columns[index].error.message, retry };
    if (!version || columns[index]?.isLoading) return { status: "Loading version…" };
    if (suiteQuery?.isError)
      return { status: "Could not load test suite", error: suiteQuery.error.message, retry };
    if (suiteQuery?.isLoading || (suiteQuery?.isFetching && !suite))
      return { status: "Loading test suite…" };
    if (!suite) return { status: "No test suite" };
    if (suite.status === "queued" || suite.status === "running")
      return { status: `Test suite ${suite.status}…` };
    if (suite.status === "failed") return { status: "Test suite generation failed" };
    if (!suite.has_completed_suite) return { status: "No completed test suite" };
    if (evaluationQuery?.isError && (evaluationQuery.error as { status?: number }).status !== 404)
      return { status: "Could not load evaluation", error: evaluationQuery.error.message, retry };
    if (evaluationQuery?.isLoading || (evaluationQuery?.isFetching && !evaluation))
      return { status: "Loading evaluation…" };
    if (!evaluation) return { status: "No evaluation" };
    if (evaluation.status === "queued" || evaluation.status === "running")
      return { status: `Evaluation ${evaluation.status}…` };
    if (evaluation.status === "failed")
      return { status: `Evaluation failed${evaluation.error ? `: ${evaluation.error}` : ""}` };
    const aggregate = aggregateEvaluation(suite.items, evaluation);
    if (!aggregate) return { status: "Evaluation results are incomplete" };
    return { aggregate, status: "" };
  });
  const referenceVersion = columns[0]?.data?.version;

  function update(ids: string[]) {
    const next = new URLSearchParams(searchParams);
    next.set("versions", ids.join(","));
    setSearchParams(next);
  }
  function addAfter(index: number, id: string) {
    const next = [...selectedIds];
    next.splice(index + 1, 0, id);
    update(next);
  }
  function remove(id: string) {
    if (selectedIds.length > 1 && id !== selectedIds[0])
      update(selectedIds.filter((item) => item !== id));
  }

  return (
    <WorkspaceLayout
      breadcrumb={[
        { label: agent.data?.name ?? "Agent", to: `/agents/${encodeURIComponent(agentId)}` },
        { label: "Compare versions" },
      ]}
    >
      <main>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <Link
              to={`/agents/${encodeURIComponent(agentId)}`}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
            >
              ← Back to agent
            </Link>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.05em] text-slate-950">
              Compare evaluations
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Compare average evaluation scores across testing categories.
            </p>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500">
            Average rubric score
          </span>
        </div>
        {agent.isError ? (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-rose-200 bg-white p-5 text-sm text-rose-700"
          >
            {agent.error.message}{" "}
            <Button variant="outline" size="sm" onClick={() => void agent.refetch()}>
              Retry
            </Button>
          </div>
        ) : null}
        <div className="mt-7 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-soft">
          <table className="w-full min-w-[660px] border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                <th
                  scope="col"
                  className="sticky left-0 z-10 min-w-52 border-r border-slate-200 bg-slate-50 px-4 py-4 text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  Testing category
                </th>
                {selectedIds.map((id, index) => {
                  const column = columns[index];
                  const value = column?.data?.agent_id === agentId ? column.data : undefined;
                  const isReference = index === 0;
                  return (
                    <th scope="col" key={id} className="min-w-56 px-4 py-4 align-top">
                      <div className="flex min-h-8 items-center justify-between gap-2">
                        <div>
                          {value ? (
                            <Link
                              className="block text-sm font-semibold text-slate-900 hover:text-indigo-700"
                              to={`/agents/${encodeURIComponent(agentId)}/versions/${encodeURIComponent(id)}/test-suite`}
                            >
                              Version {value.version}
                            </Link>
                          ) : (
                            <span className="block text-sm font-semibold text-slate-900">
                              {column?.isError || (column?.data && !value)
                                ? "Unavailable version"
                                : "Loading version…"}
                            </span>
                          )}
                          {isReference && value && (
                            <span className="mt-1 inline-block rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                              Reference
                            </span>
                          )}
                          {value && (
                            <span className="mt-1 block text-[11px] font-normal text-slate-500">
                              Created{" "}
                              {new Intl.DateTimeFormat(undefined, {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              }).format(new Date(value.created_at))}
                            </span>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <AddVersionMenu
                            candidates={candidates}
                            onAdd={(versionId) => addAfter(index, versionId)}
                          />
                          {selectedIds.length > 1 && !isReference && (
                            <button
                              type="button"
                              aria-label={`Remove version ${value?.version ?? "column"}`}
                              onClick={() => remove(id)}
                              className="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                      {states[index]?.error ? (
                        <div className="mt-2 text-xs text-rose-700">
                          <p>{states[index].error}</p>
                          <button
                            type="button"
                            className="mt-1 underline"
                            onClick={states[index].retry}
                          >
                            Retry
                          </button>
                        </div>
                      ) : states[index]?.status ? (
                        <p className="mt-2 text-xs text-slate-400" role="status">
                          {states[index]?.status}
                        </p>
                      ) : null}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {CATEGORIES.map((category) => {
                const expanded = Boolean(expandedCategories[category.key]);
                const referenceAggregate = states[0]?.aggregate?.[category.key];
                return (
                  <FragmentCategory
                    key={category.key}
                    category={category}
                    expanded={expanded}
                    onToggle={() =>
                      setExpandedCategories((current) => ({
                        ...current,
                        [category.key]: !current[category.key],
                      }))
                    }
                    states={states}
                    selectedIds={selectedIds}
                    reference={referenceAggregate}
                    referenceVersion={referenceVersion}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
        {versions.isError && (
          <p role="alert" className="mt-4 text-sm text-rose-700">
            Could not load the version picker.{" "}
            <Button variant="outline" size="sm" onClick={() => void versions.refetch()}>
              Retry
            </Button>
          </p>
        )}
        <p className="mt-4 text-xs leading-5 text-slate-400">
          Category scores average Adherence, Consistency, and Grounding equally across the evaluated
          tests in that category. Arrows compare each version with the reference.
        </p>
      </main>
    </WorkspaceLayout>
  );
}

function FragmentCategory({
  category,
  expanded,
  onToggle,
  states,
  selectedIds,
  reference,
  referenceVersion,
}: {
  category: (typeof CATEGORIES)[number];
  expanded: boolean;
  onToggle: () => void;
  states: ColumnState[];
  selectedIds: string[];
  reference?: EvaluationAggregate[string];
  referenceVersion?: string;
}) {
  return (
    <Fragment>
      <tr className="border-b border-slate-100">
        <th
          scope="row"
          className="sticky left-0 z-10 border-r border-slate-100 bg-white px-4 py-3 text-sm font-medium text-slate-700"
        >
          <button
            type="button"
            aria-expanded={expanded}
            onClick={onToggle}
            className="flex w-full items-center gap-2 text-left hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <ChevronDown
              size={14}
              aria-hidden="true"
              className={`shrink-0 transition-transform motion-reduce:transition-none ${expanded ? "rotate-180" : ""}`}
            />
            <span className={`h-2 w-2 shrink-0 rounded-full ${category.color}`} />
            {category.label}
          </button>
        </th>
        {states.map((state, index) => {
          const value = state.aggregate?.[category.key];
          const referenceScore = reference && reference.count > 0 ? reference.average : undefined;
          return (
            <td key={selectedIds[index]} className="px-4 py-3 text-sm text-slate-700">
              {value && value.count > 0 ? (
                <div>
                  <ScoreCell
                    value={value.average}
                    reference={referenceScore}
                    referenceVersion={referenceVersion}
                    isReference={index === 0}
                  />
                </div>
              ) : state.aggregate ? (
                <span className="text-xs text-slate-400">No tests</span>
              ) : (
                <span className="text-xs text-slate-400">—</span>
              )}
            </td>
          );
        })}
      </tr>
      {expanded &&
        RUBRIC_DIMENSIONS.map((dimension) => (
          <tr
            key={`${category.key}-${dimension.key}`}
            className="border-b border-slate-100 bg-slate-50/50"
          >
            <th
              scope="row"
              className="sticky left-0 z-10 border-r border-slate-100 bg-slate-50 px-4 py-2 pl-10 text-xs font-medium text-slate-500"
            >
              {dimension.label}
            </th>
            {states.map((state, index) => {
              const value = state.aggregate?.[category.key];
              return (
                <td key={selectedIds[index]} className="px-4 py-2 text-sm text-slate-600">
                  {value && value.count > 0 ? (
                    <div>
                      <ScoreCell
                        value={value[dimension.key]}
                        reference={
                          reference && reference.count > 0 ? reference[dimension.key] : undefined
                        }
                        referenceVersion={referenceVersion}
                        isReference={index === 0}
                      />
                    </div>
                  ) : state.aggregate ? (
                    <span className="text-xs text-slate-400">No tests</span>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
    </Fragment>
  );
}
