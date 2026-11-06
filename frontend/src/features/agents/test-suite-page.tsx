import { useQueryClient } from "@tanstack/react-query";
import { ClipboardList, LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CATEGORIES } from "./classification-categories";
import { TestCaseCard } from "./components/test-case-card";
import { TraceDialog } from "./components/trace-dialog";
import { WorkspaceLayout } from "./components/workspace-layout";
import {
  agentKeys,
  useAgent,
  useClassify,
  useEvaluation,
  useGenerateTestSuite,
  useTestSuite,
  useVersion,
} from "./hooks/use-agents";

export function TestSuitePage() {
  const { agentId = "", versionId = "" } = useParams();
  const agent = useAgent(agentId);
  const version = useVersion(versionId);
  const suite = useTestSuite(versionId);
  const evaluation = useEvaluation(suite.data?.id ?? "");
  const classify = useClassify(versionId);
  const generate = useGenerateTestSuite(versionId);
  const queryClient = useQueryClient();
  const [totalCount, setTotalCount] = useState("20");
  const [editingCount, setEditingCount] = useState(false);
  const [phase, setPhase] = useState<"classifying" | "generating" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [expandedCases, setExpandedCases] = useState<Record<string, boolean>>({});
  const [traceCaseIndex, setTraceCaseIndex] = useState<number | null>(null);
  const validCount =
    /^\d+$/.test(totalCount) && Number(totalCount) >= 1 && Number(totalCount) <= 100;
  const busy =
    phase !== null ||
    generate.isPending ||
    suite.data?.status === "queued" ||
    suite.data?.status === "running";
  const isReplacing = Boolean(suite.data?.has_completed_suite);

  useEffect(() => {
    if (suite.data?.has_completed_suite) setTotalCount(String(suite.data.requested_count));
  }, [suite.data?.has_completed_suite, suite.data?.requested_count]);

  useEffect(() => {
    if (!suite.data?.id) return;
    setExpandedCases({});
    setTraceCaseIndex(null);
  }, [suite.data?.id]);

  useEffect(() => {
    if (evaluation.data?.status === "completed") {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) }),
        queryClient.invalidateQueries({ queryKey: agentKeys.versions(agentId) }),
        queryClient.invalidateQueries({ queryKey: agentKeys.all }),
      ]);
    }
  }, [evaluation.data?.status, agentId, queryClient]);
  const breadcrumb = [
    { label: agent.data?.name ?? "Agent", to: `/agents/${encodeURIComponent(agentId)}` },
    {
      label: `Version ${version.data?.version ?? "…"}`,
      to: `/agents/${encodeURIComponent(agentId)}/compare?versions=${encodeURIComponent(versionId)}`,
    },
    { label: "Test suite" },
  ];

  async function handleGenerate() {
    if (!validCount || busy) return;
    if (
      isReplacing &&
      !window.confirm(
        "Regenerating removes the current test suite. If generation fails, the previous suite cannot be restored. Continue?",
      )
    )
      return;

    setTraceCaseIndex(null);
    setExpandedCases({});
    setActionError(null);
    try {
      if (!version.data?.classification) {
        setPhase("classifying");
        await classify.mutateAsync();
      }
      setPhase("generating");
      await generate.mutateAsync(Number(totalCount));
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : "Could not generate the test suite. Try again.",
      );
    } finally {
      setPhase(null);
    }
  }

  const categoryLabel = (key: string) =>
    CATEGORIES.find((category) => category.key === key)?.label ?? key;
  const resultsByCase = new Map(
    (evaluation.data?.results ?? []).map((result) => [result.test_case_id, result]),
  );
  const resultsComplete = Boolean(
    suite.data?.has_completed_suite &&
      evaluation.data?.status === "completed" &&
      suite.data.items.length > 0 &&
      suite.data.items.every((item) => resultsByCase.has(item.id)) &&
      evaluation.data.results.length === suite.data.items.length,
  );

  return (
    <WorkspaceLayout breadcrumb={breadcrumb}>
      <main>
        <Link
          to={`/agents/${encodeURIComponent(agentId)}`}
          className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
        >
          ← Back to agent
        </Link>
        {version.isLoading ? (
          <div className="mt-5 space-y-3">
            <div className="h-9 w-1/2 animate-pulse rounded bg-slate-200" />
            <div className="h-28 animate-pulse rounded-2xl bg-white" />
          </div>
        ) : version.isError ? (
          <section role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-white p-8">
            <h1 className="text-xl font-semibold">Unable to load this version</h1>
            <p className="mt-2 text-sm text-rose-700">{version.error.message}</p>
            <Button variant="outline" className="mt-4" onClick={() => void version.refetch()}>
              Try again
            </Button>
          </section>
        ) : version.data && version.data.agent_id !== agentId ? (
          <section role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-white p-8">
            <h1 className="text-xl font-semibold">This version does not belong to this agent</h1>
          </section>
        ) : version.data ? (
          <>
            <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-medium text-indigo-600">{agent.data?.name ?? "Agent"}</p>
                <h1 className="mt-1 text-3xl font-semibold tracking-[-0.05em] text-slate-950">
                  Test suite · v{version.data.version}
                </h1>
                <p className="mt-2 text-sm text-slate-500">
                  Review the questions and acceptance criteria used to evaluate this version.
                </p>
              </div>
              <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500">
                <ClipboardList size={14} />
                {suite.data?.has_completed_suite
                  ? `${suite.data.items.length} tests`
                  : "Version test suite"}
              </span>
            </div>

            {suite.isLoading ? (
              <div className="mt-7 space-y-3">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="h-32 animate-pulse rounded-2xl bg-white" />
                ))}
              </div>
            ) : suite.isError ? (
              <section
                role="alert"
                className="mt-7 rounded-2xl border border-rose-200 bg-white p-6"
              >
                <h2 className="font-semibold text-slate-900">Couldn't load the test suite</h2>
                <p className="mt-1 text-sm text-rose-700">{suite.error.message}</p>
                <Button variant="outline" className="mt-4" onClick={() => void suite.refetch()}>
                  Retry
                </Button>
              </section>
            ) : suite.data?.has_completed_suite ? (
              <>
                <section aria-label="Evaluation status" className="mt-7">
                  {evaluation.isLoading ? (
                    <p
                      role="status"
                      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500"
                    >
                      Loading evaluation results…
                    </p>
                  ) : evaluation.isError &&
                    (evaluation.error as { status?: number }).status !== 404 ? (
                    <div
                      role="alert"
                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-white px-4 py-3 text-sm text-rose-700"
                    >
                      <span>Couldn't load evaluation results: {evaluation.error.message}</span>
                      <Button variant="outline" size="sm" onClick={() => void evaluation.refetch()}>
                        Retry
                      </Button>
                    </div>
                  ) : evaluation.data?.status === "queued" ||
                    evaluation.data?.status === "running" ? (
                    <p
                      role="status"
                      className="rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3 text-sm text-indigo-700"
                    >
                      Evaluation {evaluation.data.status}… Results will appear here when it
                      finishes.
                    </p>
                  ) : evaluation.data?.status === "failed" ? (
                    <p
                      role="status"
                      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
                    >
                      Evaluation failed.{" "}
                      {evaluation.data.error ?? "No evaluation results are available."}
                    </p>
                  ) : evaluation.data?.status === "completed" && !resultsComplete ? (
                    <p
                      role="status"
                      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
                    >
                      Evaluation results are incomplete. Scores are hidden until every test case has
                      a result.
                    </p>
                  ) : !evaluation.data ? (
                    <p className="text-xs text-slate-400">No evaluation results yet.</p>
                  ) : null}
                </section>
                <section aria-label="Generated test suite" className="mt-7 space-y-3">
                  {suite.data.items.map((item, index) => (
                    <TestCaseCard
                      key={item.id}
                      item={item}
                      categoryLabel={categoryLabel(item.category)}
                      index={index}
                      result={resultsComplete ? resultsByCase.get(item.id) : undefined}
                      expanded={Boolean(expandedCases[item.id])}
                      onToggle={() =>
                        setExpandedCases((current) => ({
                          ...current,
                          [item.id]: !current[item.id],
                        }))
                      }
                      onViewTrace={() => setTraceCaseIndex(index)}
                    />
                  ))}
                </section>
                <TraceDialog
                  suiteId={suite.data.id}
                  items={suite.data.items}
                  result={
                    resultsComplete && traceCaseIndex !== null
                      ? resultsByCase.get(suite.data.items[traceCaseIndex]?.id)
                      : undefined
                  }
                  caseIndex={traceCaseIndex}
                  onCaseChange={setTraceCaseIndex}
                  open={traceCaseIndex !== null}
                  onOpenChange={(open) => {
                    if (!open) setTraceCaseIndex(null);
                  }}
                />
                <div className="mt-5 flex flex-wrap items-end gap-3">
                  {editingCount ? (
                    <>
                      <div>
                        <label
                          htmlFor="test-count"
                          className="mb-1.5 block text-xs font-medium text-slate-600"
                        >
                          Number of questions
                        </label>
                        <input
                          id="test-count"
                          type="number"
                          min={1}
                          max={100}
                          step={1}
                          value={totalCount}
                          onChange={(event) => setTotalCount(event.target.value)}
                          aria-invalid={!validCount}
                          className="h-10 w-36 rounded-lg border border-slate-200 px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                      </div>
                      <Button onClick={() => void handleGenerate()} disabled={!validCount || busy}>
                        {busy ? (
                          <LoaderCircle size={15} className="animate-spin" />
                        ) : (
                          <RefreshCw size={15} />
                        )}{" "}
                        {phase === "classifying"
                          ? "Classifying…"
                          : phase === "generating" || generate.isPending
                            ? "Generating…"
                            : "Confirm regeneration"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setEditingCount(false)}
                        disabled={busy}
                      >
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <Button variant="outline" onClick={() => setEditingCount(true)}>
                      <RefreshCw size={14} />
                      Regenerate suite
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <section className="mt-7 rounded-2xl border border-dashed border-slate-300 bg-white p-6 sm:p-8">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Sparkles size={18} />
                </span>
                <h2 className="mt-4 text-lg font-semibold text-slate-900">
                  {suite.data?.status === "failed"
                    ? "Test suite generation failed"
                    : suite.data?.status === "queued" || suite.data?.status === "running"
                      ? "Generating your test suite"
                      : "No test suite yet"}
                </h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
                  {suite.data?.status === "failed"
                    ? (suite.data.error ?? "The generation did not complete. You can try again.")
                    : suite.data?.status === "queued" || suite.data?.status === "running"
                      ? "Your suite is being generated. This page will update when it is ready."
                      : "Generate a set of questions and expected behaviors from this version’s definition and testing allocation."}
                </p>
                {suite.data?.status !== "queued" && suite.data?.status !== "running" && (
                  <div className="mt-5 flex flex-wrap items-end gap-3">
                    <div>
                      <label
                        htmlFor="test-count"
                        className="mb-1.5 block text-xs font-medium text-slate-600"
                      >
                        Number of questions
                      </label>
                      <input
                        id="test-count"
                        type="number"
                        min={1}
                        max={100}
                        step={1}
                        value={totalCount}
                        onChange={(event) => setTotalCount(event.target.value)}
                        aria-invalid={!validCount}
                        className="h-10 w-36 rounded-lg border border-slate-200 px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                    <Button
                      onClick={() => void handleGenerate()}
                      disabled={!validCount || busy || suite.isError}
                    >
                      {busy ? (
                        <LoaderCircle size={15} className="animate-spin" />
                      ) : isReplacing ? (
                        <RefreshCw size={15} />
                      ) : (
                        <Sparkles size={15} />
                      )}{" "}
                      {phase === "classifying"
                        ? "Classifying…"
                        : phase === "generating" || generate.isPending
                          ? "Generating…"
                          : suite.data?.status === "failed"
                            ? "Retry generation"
                            : isReplacing
                              ? "Regenerate suite"
                              : "Generate test suite"}
                    </Button>
                  </div>
                )}
                {actionError && (
                  <p
                    role="alert"
                    className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
                  >
                    {actionError}
                  </p>
                )}
              </section>
            )}
          </>
        ) : null}
      </main>
    </WorkspaceLayout>
  );
}
