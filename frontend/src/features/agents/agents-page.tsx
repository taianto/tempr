import { useMemo, useState } from "react";
import { Activity, Bot, Plus, RefreshCw, Search } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AgentCardSkeleton } from "./components/agent-card";
import { AgentJsonDialog } from "./components/agent-json-dialog";
import { WorkspaceLayout } from "./components/workspace-layout";
import { useAgents, useCreateAgent } from "./hooks/use-agents";
import type { AgentCreateInput, AgentSchema } from "./types";

const EMPTY_SCHEMA: AgentSchema = { description: null, prompt: { system: "" }, model: null, tools: [], metadata: {} };
const CREATE_EXAMPLE = { name: "Support agent", initial_version: { version: "1.0", schema: { description: "Handles customer support requests.", prompt: { system: "You are a helpful customer support assistant." }, model: null, tools: [], metadata: {} } } };

export function AgentsPage() {
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const agents = useAgents();
  const createAgent = useCreateAgent();
  const navigate = useNavigate();
  const filtered = useMemo(() => (agents.data?.items ?? []).filter((agent) => agent.name.toLowerCase().includes(search.trim().toLowerCase())), [agents.data?.items, search]);

  async function handleCreate(value: Record<string, unknown>) {
    const created = await createAgent.mutateAsync(value as AgentCreateInput);
    navigate(`/agents/${encodeURIComponent(created.id)}`);
  }

  return <WorkspaceLayout><main id="agents">
    <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div><div className="mb-3 flex items-center gap-2 text-xs font-medium text-indigo-600"><span className="flex h-5 w-5 items-center justify-center rounded-md bg-indigo-50"><Bot size={13} /></span>Agent workspace</div><h1 className="text-[30px] font-semibold tracking-[-0.055em] text-slate-950 sm:text-[36px]">Your agents</h1><p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">Review agent versions and their testing allocations.</p></div><Button className="w-fit gap-2 shadow-sm" onClick={() => setCreateOpen(true)}><Plus size={16} />New agent</Button></div>
    <div className="mt-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="text-base font-semibold tracking-[-0.02em] text-slate-900">All agents <span className="ml-1.5 rounded-md bg-slate-100 px-1.5 py-0.5 align-middle text-[11px] font-medium text-slate-500">{agents.data?.total ?? 0}</span></h2><p className="mt-1 text-xs text-slate-400">Browse versions and classification status</p></div><div className="flex w-full items-center gap-2 sm:w-auto"><div className="relative flex-1 sm:w-[260px]"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><Input aria-label="Search agents" placeholder="Search agents..." value={search} onChange={(event) => setSearch(event.target.value)} className="h-10 border-slate-200 bg-white pl-9 text-sm shadow-sm placeholder:text-slate-400" /></div><Button variant="outline" size="icon" aria-label="Refresh agents" title="Refresh agents" className="h-10 w-10 shrink-0 bg-white" onClick={() => void agents.refetch()} disabled={agents.isFetching}><RefreshCw size={15} className={agents.isFetching ? "animate-spin" : ""} /></Button></div></div>
    <div aria-live="polite" className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">{agents.isLoading ? Array.from({ length: 6 }, (_, index) => <AgentCardSkeleton key={index} />) : agents.isError ? <div className="col-span-full flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center"><Activity size={20} className="text-rose-600" /><h3 className="mt-4 text-sm font-semibold">Unable to load agents</h3><p className="mt-1 max-w-sm text-sm text-slate-500">{agents.error.message}</p><Button variant="outline" className="mt-4" onClick={() => void agents.refetch()}>Try again</Button></div> : filtered.length ? filtered.map((agent, index) => <article key={agent.id} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-card sm:p-6"><div className="flex items-start justify-between"><div className={`flex h-12 w-12 items-center justify-center rounded-[14px] ${["bg-indigo-50 text-indigo-600", "bg-emerald-50 text-emerald-700", "bg-amber-50 text-amber-700", "bg-sky-50 text-sky-700"][index % 4]}`}><Bot size={23} /></div><span className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-600">{agent.latest_version.version}</span></div><h3 className="mt-5 truncate text-[15px] font-semibold text-slate-900">{agent.name}</h3><p className="mt-2 text-sm text-slate-500">{agent.latest_version.classification_id ? "Classification ready" : "Needs classification"}</p><div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4"><span className="text-xs text-slate-400">Updated {new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(agent.updated_at))}</span><Button asChild variant="ghost" size="sm" className="-mr-2 h-8 text-xs"><Link to={`/agents/${encodeURIComponent(agent.id)}`}>Open agent <span aria-hidden="true">↗</span></Link></Button></div></article>) : <div className="col-span-full flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center"><Bot size={20} className="text-slate-500" /><h3 className="mt-4 text-sm font-semibold">{search ? "No matching agents" : "Your workspace is ready"}</h3><p className="mt-1 max-w-sm text-sm text-slate-500">{search ? "Try a different name." : "Register an agent or create one here to get started."}</p>{!search && <Button className="mt-4" onClick={() => setCreateOpen(true)}><Plus size={15} />New agent</Button>}</div>}</div>
    <p className="mt-7 text-center text-[11px] text-slate-400">Showing {agents.isLoading ? "—" : filtered.length} {filtered.length === 1 ? "agent" : "agents"}</p>
  </main><AgentJsonDialog open={createOpen} onOpenChange={setCreateOpen} title="Create an agent" description="Create an agent and its first immutable version." submitLabel="Create agent" fieldLabel="Agent JSON" endpoint="POST /api/v1/agents" example={CREATE_EXAMPLE} initialValue={{ name: "", initial_version: { version: "1.0", schema: EMPTY_SCHEMA } }} onSubmit={handleCreate} /></WorkspaceLayout>;
}
