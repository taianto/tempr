import { useMemo, useState } from "react";
import { Activity, Bot, ChevronRight, Command, Layers3, Plus, RefreshCw, Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AgentCard, AgentCardSkeleton } from "./components/agent-card";
import { AgentDetails } from "./components/agent-details";
import { AgentJsonDialog } from "./components/agent-json-dialog";
import { useAgents, useCreateAgent, useUpdateAgent } from "./hooks/use-agents";
import type { Agent, AgentCreateInput, AgentUpdateInput } from "./types";

const EMPTY_AGENT: Record<string, unknown> = {
  name: "",
  description: null,
  prompt: { system: "" },
  model: null,
  tools: [],
  metadata: {},
};

const API_DOCS_URL = import.meta.env.VITE_API_DOCS_URL || "/docs";

function editableAgent(agent: Agent): Record<string, unknown> {
  return {
    name: agent.name,
    description: agent.description,
    prompt: agent.prompt,
    model: agent.model,
    tools: agent.tools,
    metadata: agent.metadata,
  };
}

function ApiDocsLink({ compact = false }: { compact?: boolean }) {
  return (
    <a
      href={API_DOCS_URL}
      target="_blank"
      rel="noreferrer"
      className={compact
        ? "inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 sm:hidden"
        : "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"}
    >
      <span aria-hidden="true" className="flex h-[17px] w-[17px] items-center justify-center rounded bg-slate-100 font-mono text-[9px] font-semibold text-slate-600">API</span>
      {compact ? "Docs" : "API Docs"}
      {!compact && <span aria-hidden="true" className="ml-auto text-xs text-slate-400">↗</span>}
    </a>
  );
}

export function AgentsPage() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const agents = useAgents();
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent(editingAgent?.id ?? "");
  const filtered = useMemo(
    () => (agents.data?.items ?? []).filter((agent) => `${agent.name} ${agent.description ?? ""}`.toLowerCase().includes(search.trim().toLowerCase())),
    [agents.data?.items, search],
  );

  async function handleCreate(value: Record<string, unknown>) {
    const created = await createAgent.mutateAsync(value as AgentCreateInput);
    setSelectedId(created.id);
  }

  async function handleUpdate(value: Record<string, unknown>) {
    if (!editingAgent) return;
    await updateAgent.mutateAsync(value as AgentUpdateInput);
    setEditingAgent(null);
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-[248px] flex-col border-r border-slate-200/80 bg-white lg:flex">
        <div className="flex h-[72px] items-center gap-3 border-b border-slate-100 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-slate-900 text-white"><Activity size={16} strokeWidth={2.3} /></div>
          <span className="text-[17px] font-semibold tracking-[-0.04em] text-slate-900">tempr</span>
          <span className="ml-auto rounded-md border border-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">BETA</span>
        </div>
        <div className="px-4 pt-7">
          <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">Workspace</p>
          <nav aria-label="Main navigation" className="mt-3 space-y-1">
            <a href="#agents" className="flex items-center gap-3 rounded-lg bg-slate-100 px-3 py-2.5 text-sm font-medium text-slate-900"><Layers3 size={17} className="text-slate-600" />Agents<span className="ml-auto rounded-md bg-white px-2 py-0.5 text-xs text-slate-500">{agents.data?.total ?? "—"}</span></a>
            <ApiDocsLink />
            <a href="#activity" onClick={(event) => event.preventDefault()} className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400"><Activity size={17} />Activity<span className="ml-auto text-[10px]">Soon</span></a>
          </nav>
        </div>
        <div className="mt-auto p-4">
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/80 p-4"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-indigo-600 shadow-sm"><Sparkles size={16} /></div><p className="mt-3 text-sm font-medium text-slate-800">Build with confidence</p><p className="mt-1 text-xs leading-5 text-slate-500">Test your agents against the unexpected.</p></div>
          <div className="mt-4 flex items-center gap-2 px-2"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-500"><Command size={15} /></div><div><p className="text-xs font-medium text-slate-700">Local workspace</p><p className="text-[11px] text-slate-400">Personal</p></div></div>
        </div>
      </aside>

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-5 backdrop-blur-md sm:px-8 lg:px-10">
          <div className="flex items-center gap-2 text-sm"><div className="flex items-center gap-2 font-medium text-slate-500 lg:hidden"><div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 text-white"><Activity size={14} /></div>tempr<span className="text-slate-300">/</span></div><span className="hidden text-slate-400 sm:inline">Workspace</span><ChevronRight size={14} className="hidden text-slate-300 sm:block" /><span className="font-medium text-slate-800">Agents</span></div>
          <div className="flex items-center gap-2"><ApiDocsLink compact /><span className={`hidden items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-500 sm:inline-flex`}><span className={`h-1.5 w-1.5 rounded-full ${agents.isError ? "bg-rose-500" : agents.isSuccess ? "bg-emerald-500" : "bg-amber-400"}`} />{agents.isError ? "API unavailable" : agents.isSuccess ? "API connected" : "Connecting"}</span><div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-[11px] font-semibold text-indigo-700">AT</div></div>
        </header>

        <main id="agents" className="mx-auto max-w-[1240px] px-5 pb-16 pt-9 sm:px-8 sm:pt-11 lg:px-10">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div><div className="mb-3 flex items-center gap-2 text-xs font-medium text-indigo-600"><span className="flex h-5 w-5 items-center justify-center rounded-md bg-indigo-50"><Bot size={13} /></span>Agent workspace</div><h1 className="text-[30px] font-semibold tracking-[-0.055em] text-slate-950 sm:text-[36px]">Your agents</h1><p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">A clear view of every agent in your workspace. Select one to explore its configuration.</p></div><Button className="w-fit gap-2 shadow-sm" onClick={() => setCreateOpen(true)}><Plus size={16} />New agent</Button></div>

          <div className="mt-9 grid grid-cols-1 gap-3 sm:grid-cols-3"><div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-soft"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-500">Total agents</span><Layers3 size={15} className="text-slate-400" /></div><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-900">{agents.isLoading ? "—" : agents.data?.total ?? "—"}</p></div><div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-soft"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-500">Configured</span><Bot size={15} className="text-indigo-500" /></div><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-900">{agents.isLoading ? "—" : agents.data?.total ?? "—"}</p></div><div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-soft"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-500">Workspace</span><Command size={15} className="text-slate-400" /></div><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-900">Personal</p></div></div>

          <div className="mt-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="text-base font-semibold tracking-[-0.02em] text-slate-900">All agents <span className="ml-1.5 rounded-md bg-slate-100 px-1.5 py-0.5 align-middle text-[11px] font-medium text-slate-500">{agents.data?.total ?? 0}</span></h2><p className="mt-1 text-xs text-slate-400">Browse and inspect your configured agents</p></div><div className="flex w-full items-center gap-2 sm:w-auto"><div className="relative flex-1 sm:w-[260px]"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><Input aria-label="Search agents" placeholder="Search agents..." value={search} onChange={(event) => setSearch(event.target.value)} className="h-10 border-slate-200 bg-white pl-9 text-sm shadow-sm placeholder:text-slate-400" /></div><Button variant="outline" size="icon" aria-label="Refresh agents" title="Refresh agents" className="h-10 w-10 shrink-0 bg-white" onClick={() => void agents.refetch()} disabled={agents.isFetching}><RefreshCw size={15} className={agents.isFetching ? "animate-spin" : ""} /></Button></div></div>

          <div aria-live="polite" className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">{agents.isLoading ? Array.from({ length: 6 }, (_, index) => <AgentCardSkeleton key={index} />) : agents.isError ? <div className="col-span-full flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-50 text-rose-600"><Activity size={19} /></div><h3 className="mt-4 text-sm font-semibold text-slate-900">Unable to load agents</h3><p className="mt-1 max-w-sm text-sm leading-5 text-slate-500">{agents.error.message}</p><Button variant="outline" className="mt-4" onClick={() => void agents.refetch()}>Try again</Button></div> : filtered.length ? filtered.map((agent, index) => <AgentCard key={agent.id} agent={agent} index={index} onSelect={() => setSelectedId(agent.id)} />) : <div className="col-span-full flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 text-center"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-500"><Bot size={20} /></div><h3 className="mt-4 text-sm font-semibold text-slate-900">{search ? "No matching agents" : "Your workspace is ready"}</h3><p className="mt-1 max-w-sm text-sm leading-5 text-slate-500">{search ? "Try a different name or search term." : "There are no agents here yet. Once you register an agent with the API, it will appear here."}</p></div>}</div>
          <p className="mt-7 text-center text-[11px] text-slate-400">Showing {agents.isLoading ? "—" : filtered.length} {filtered.length === 1 ? "agent" : "agents"}</p>
        </main>
      </div>
      <AgentDetails agentId={selectedId} open={Boolean(selectedId)} onOpenChange={(open) => { if (!open) setSelectedId(null); }} onEdit={setEditingAgent} />
      <AgentJsonDialog open={createOpen} onOpenChange={setCreateOpen} title="Create an agent" description="Paste an agent definition as JSON. The backend validates the fields when you save." submitLabel="Create agent" initialValue={EMPTY_AGENT} onSubmit={handleCreate} />
      <AgentJsonDialog open={Boolean(editingAgent)} onOpenChange={(open) => { if (!open) setEditingAgent(null); }} title="Edit agent JSON" description="Update this agent's configuration. Include only the fields you want to change." submitLabel="Save changes" initialValue={editingAgent ? editableAgent(editingAgent) : EMPTY_AGENT} onSubmit={handleUpdate} />
    </div>
  );
}
