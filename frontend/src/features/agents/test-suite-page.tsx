import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ClipboardList, LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WorkspaceLayout } from "./components/workspace-layout";
import { CATEGORIES } from "./classification-categories";
import { useAgent, useClassify, useGenerateTestSuite, useTestSuite, useVersion } from "./hooks/use-agents";

export function TestSuitePage() {
  const { agentId = "", versionId = "" } = useParams();
  const agent = useAgent(agentId);
  const version = useVersion(agentId, versionId);
  const suite = useTestSuite(agentId, versionId);
  const classify = useClassify(agentId, versionId);
  const generate = useGenerateTestSuite(agentId, versionId);
  const [totalCount, setTotalCount] = useState("20");
  const [editingCount, setEditingCount] = useState(false);
  const [phase, setPhase] = useState<"classifying" | "generating" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const validCount = /^\d+$/.test(totalCount) && Number(totalCount) >= 1 && Number(totalCount) <= 100;
  const busy = phase !== null || generate.isPending || suite.data?.status === "queued" || suite.data?.status === "running";
  const isReplacing = Boolean(suite.data?.has_completed_suite);

  useEffect(() => {
    if (suite.data?.has_completed_suite) setTotalCount(String(suite.data.requested_count));
  }, [suite.data?.has_completed_suite, suite.data?.requested_count]);
  const breadcrumb = [
    { label: agent.data?.name ?? "Agent", to: `/agents/${encodeURIComponent(agentId)}` },
    { label: `Version ${version.data?.version ?? "…"}`, to: `/agents/${encodeURIComponent(agentId)}` },
    { label: "Test suite" },
  ];

  async function handleGenerate() {
    if (!validCount || busy) return;
    if (isReplacing && !window.confirm("Regenerating removes the current test suite. If generation fails, the previous suite cannot be restored. Continue?")) return;

    setActionError(null);
    try {
      if (!version.data?.classification) {
        setPhase("classifying");
        await classify.mutateAsync();
      }
      setPhase("generating");
      await generate.mutateAsync(Number(totalCount));
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Could not generate the test suite. Try again.");
    } finally {
      setPhase(null);
    }
  }

  const categoryLabel = (key: string) => CATEGORIES.find((category) => category.key === key)?.label ?? key;

  return <WorkspaceLayout breadcrumb={breadcrumb}><main>
    <Link to={`/agents/${encodeURIComponent(agentId)}`} className="text-xs font-medium text-indigo-600 hover:text-indigo-800">← Back to agent</Link>
    {version.isLoading ? <div className="mt-5 space-y-3"><div className="h-9 w-1/2 animate-pulse rounded bg-slate-200"/><div className="h-28 animate-pulse rounded-2xl bg-white"/></div> : version.isError ? <section role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-white p-8"><h1 className="text-xl font-semibold">Unable to load this version</h1><p className="mt-2 text-sm text-rose-700">{version.error.message}</p><Button variant="outline" className="mt-4" onClick={() => void version.refetch()}>Try again</Button></section> : version.data ? <>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-medium text-indigo-600">{agent.data?.name ?? "Agent"}</p><h1 className="mt-1 text-3xl font-semibold tracking-[-0.05em] text-slate-950">Test suite · v{version.data.version}</h1><p className="mt-2 text-sm text-slate-500">Review the questions and acceptance criteria used to evaluate this version.</p></div><span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500"><ClipboardList size={14}/>{suite.data?.has_completed_suite ? `${suite.data.items.length} tests` : "Version test suite"}</span></div>

      {suite.isLoading ? <div className="mt-7 space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-2xl bg-white" />)}</div> : suite.isError ? <section role="alert" className="mt-7 rounded-2xl border border-rose-200 bg-white p-6"><h2 className="font-semibold text-slate-900">Couldn't load the test suite</h2><p className="mt-1 text-sm text-rose-700">{suite.error.message}</p><Button variant="outline" className="mt-4" onClick={() => void suite.refetch()}>Retry</Button></section> : suite.data?.has_completed_suite ? <><section aria-label="Generated test suite" className="mt-7 space-y-3">{suite.data.items.map((item, index) => <article key={`${index}-${item.category}`} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-6"><div className="flex items-center gap-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-sm font-semibold text-indigo-700">{index + 1}</span><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{categoryLabel(item.category)}</span></div><div className="mt-4"><h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Question</h2><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{item.question}</p></div><div className="mt-4 border-t border-slate-100 pt-4"><h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Acceptance criteria</h3><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.expected_behavior}</p></div></article>)}</section><div className="mt-5 flex flex-wrap items-end gap-3">{editingCount ? <><div><label htmlFor="test-count" className="mb-1.5 block text-xs font-medium text-slate-600">Number of questions</label><input id="test-count" type="number" min={1} max={100} step={1} value={totalCount} onChange={(event) => setTotalCount(event.target.value)} aria-invalid={!validCount} className="h-10 w-36 rounded-lg border border-slate-200 px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"/></div><Button onClick={() => void handleGenerate()} disabled={!validCount || busy}>{busy ? <LoaderCircle size={15} className="animate-spin"/> : <RefreshCw size={15}/>} {phase === "classifying" ? "Classifying…" : phase === "generating" || generate.isPending ? "Generating…" : "Confirm regeneration"}</Button><Button variant="outline" onClick={() => setEditingCount(false)} disabled={busy}>Cancel</Button></> : <Button variant="outline" onClick={() => setEditingCount(true)}><RefreshCw size={14}/>Regenerate suite</Button>}</div></> : <section className="mt-7 rounded-2xl border border-dashed border-slate-300 bg-white p-6 sm:p-8"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><Sparkles size={18}/></span><h2 className="mt-4 text-lg font-semibold text-slate-900">{suite.data?.status === "failed" ? "Test suite generation failed" : suite.data?.status === "queued" || suite.data?.status === "running" ? "Generating your test suite" : "No test suite yet"}</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">{suite.data?.status === "failed" ? suite.data.error ?? "The generation did not complete. You can try again." : suite.data?.status === "queued" || suite.data?.status === "running" ? "Your suite is being generated. This page will update when it is ready." : "Generate a set of questions and expected behaviors from this version’s definition and testing allocation."}</p>
        {suite.data?.status !== "queued" && suite.data?.status !== "running" && <div className="mt-5 flex flex-wrap items-end gap-3"><div><label htmlFor="test-count" className="mb-1.5 block text-xs font-medium text-slate-600">Number of questions</label><input id="test-count" type="number" min={1} max={100} step={1} value={totalCount} onChange={(event) => setTotalCount(event.target.value)} aria-invalid={!validCount} className="h-10 w-36 rounded-lg border border-slate-200 px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"/></div><Button onClick={() => void handleGenerate()} disabled={!validCount || busy || suite.isError}>{busy ? <LoaderCircle size={15} className="animate-spin"/> : isReplacing ? <RefreshCw size={15}/> : <Sparkles size={15}/>} {phase === "classifying" ? "Classifying…" : phase === "generating" || generate.isPending ? "Generating…" : suite.data?.status === "failed" ? "Retry generation" : isReplacing ? "Regenerate suite" : "Generate test suite"}</Button></div>}
        {actionError && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{actionError}</p>}
      </section>}
    </> : null}
  </main></WorkspaceLayout>;
}
