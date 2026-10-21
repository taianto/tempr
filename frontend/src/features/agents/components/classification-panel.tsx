import { useIsMutating } from "@tanstack/react-query";
import { LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useClassify } from "../hooks/use-agents";
import { CATEGORIES } from "../classification-categories";
import type { AgentVersion } from "../types";

export function ClassificationPanel({ agentId, version, compact = false }: { agentId: string; version: AgentVersion; compact?: boolean }) {
  const [error, setError] = useState<string | null>(null);
  const classify = useClassify(agentId, version.id);
  const regenerate = useClassify(agentId, version.id, true);
  const pending = useIsMutating({ mutationKey: ["classify", agentId, version.id] }) > 0;
  const classification = version.classification;

  async function run(refresh: boolean) {
    if (pending) return;
    if (refresh && !window.confirm(`Regenerate classification for v${version.version}? This replaces the saved weights for this version.`)) return;
    setError(null);
    try { await (refresh ? regenerate.mutateAsync() : classify.mutateAsync()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Classification failed. Try again."); }
  }

  const ranked = classification ? CATEGORIES.map((category, order) => ({ ...category, order, score: classification.scores[category.key] })).sort((a, b) => b.score - a.score || a.order - b.order) : [];
  return <section aria-labelledby={`classification-${version.id}`} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-6">
    <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Testing allocation</p><h2 id={`classification-${version.id}`} className="mt-1 text-lg font-semibold text-slate-900">Version {version.version}</h2></div>{classification && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700">Classified</span>}</div>
    {classification ? <><p className="mt-2 text-xs text-slate-500">Suggested test suite allocation by category.</p><div className={`mt-3 ${compact ? "space-y-1.5" : "space-y-1"}`}>{ranked.map((category) => <div key={category.key} data-category={category.key} className="space-y-0.5"><div className="truncate text-xs text-slate-600">{category.label}</div><div className="flex items-center gap-2"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${category.color}`} style={{ width: `${category.score * 100}%` }} /></div><span className="w-9 shrink-0 text-right text-xs font-medium tabular-nums text-slate-700">{Math.round(category.score * 100)}%</span></div></div>)}</div><Button variant="outline" size="sm" className="mt-4 gap-2" onClick={() => void run(true)} disabled={pending}><RefreshCw size={14} className={pending ? "animate-spin" : ""} />Regenerate</Button></> : <div className="mt-5 rounded-xl border border-dashed border-slate-200 bg-slate-50/70 p-5"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600"><Sparkles size={17} /></span><h3 className="mt-3 text-sm font-semibold text-slate-900">Classify your agent to plan its first test suite</h3><p className="mt-1 text-xs leading-5 text-slate-500">This analyzes the agent definition and suggests how to allocate items within a test suite.</p><Button className="mt-4 gap-2" onClick={() => void run(false)} disabled={pending}>{pending ? <LoaderCircle size={15} className="animate-spin" /> : <Sparkles size={15} />}{pending ? "Generating…" : "Generate classification"}</Button></div>}
    {error && <div role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"><p>{error}</p>{!classification && <Button variant="outline" size="sm" className="mt-2" onClick={() => void run(false)} disabled={pending}>Retry</Button>}</div>}
  </section>;
}
