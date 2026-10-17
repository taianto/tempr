import { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeftRight, CalendarDays, Code2, Cpu, MessageSquareText, Pencil, Plus, Trash2, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { WorkspaceLayout } from "./components/workspace-layout";
import { AgentDetails } from "./components/agent-details";
import { AgentJsonDialog } from "./components/agent-json-dialog";
import { ClassificationPanel } from "./components/classification-panel";
import { formatDate } from "@/lib/format";
import { useAgent, useCreateVersion, useDeleteAgent, useUpdateAgent, useVersions } from "./hooks/use-agents";
import type { AgentSchema, VersionCreateInput } from "./types";

export function AgentPage() {
  const { agentId = "" } = useParams();
  const navigate = useNavigate();
  const agent = useAgent(agentId);
  const versions = useVersions(agentId);
  const createVersion = useCreateVersion(agentId);
  const update = useUpdateAgent(agentId);
  const remove = useDeleteAgent();
  const [newVersionOpen, setNewVersionOpen] = useState(false);
  const [detailsVersionId, setDetailsVersionId] = useState<string | null>(null);
  const [renameOpen, setRenameOpen] = useState(false);
  const [name, setName] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const latestSchema = agent.data?.latest_version.schema;
  const versionExample = { version: "", schema: latestSchema ?? { prompt: { system: "" }, model: null, tools: [], metadata: {} } };

  async function handleVersion(value: Record<string, unknown>) { await createVersion.mutateAsync(value as VersionCreateInput); }
  async function handleRename(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setRenameError(null);
    try { await update.mutateAsync({ name: name.trim() }); setRenameOpen(false); }
    catch (cause) { setRenameError(cause instanceof Error ? cause.message : "Could not rename this agent."); }
  }
  async function handleDelete() {
    if (!window.confirm(`Remove ${agent.data?.name ?? "this agent"} from your workspace? It will no longer appear in the agent list.`)) return;
    setDeleteError(null);
    try { await remove.mutateAsync(agentId); navigate("/agents"); }
    catch (cause) { setDeleteError(cause instanceof Error ? cause.message : "Could not remove this agent."); }
  }

  return <WorkspaceLayout breadcrumb={agent.data ? [{ label: agent.data.name }] : [{ label: "Agent" }]}><main>
    {agent.isLoading ? <div className="space-y-4"><div className="h-10 w-1/2 animate-pulse rounded bg-slate-200" /><div className="h-72 animate-pulse rounded-2xl bg-white" /></div> : agent.isError ? <div role="alert" className="rounded-2xl border border-rose-200 bg-white p-8"><h1 className="text-xl font-semibold">Unable to load agent</h1><p className="mt-2 text-sm text-rose-700">{agent.error.message}</p><Button variant="outline" className="mt-4" onClick={() => void agent.refetch()}>Try again</Button></div> : agent.data ? <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3"><div><p className="mb-2 text-xs font-medium text-indigo-600">Agent workspace</p><h1 className="break-words text-3xl font-semibold tracking-[-0.05em] text-slate-950 sm:text-4xl">{agent.data.name}</h1><p className="mt-2 text-sm text-slate-500">Created {formatDate(agent.data.created_at)}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={() => { setName(agent.data!.name); setRenameError(null); setRenameOpen(true); }}><Pencil size={14} />Rename</Button><Button variant="outline" size="sm" onClick={() => setNewVersionOpen(true)}><Plus size={14} />New version</Button><Button variant="ghost" size="sm" className="text-rose-600 hover:bg-rose-50" onClick={() => void handleDelete()} disabled={remove.isPending}><Trash2 size={14} />Remove</Button></div></div>
      {renameOpen && <form onSubmit={(event) => void handleRename(event)} className="mb-5 flex flex-col gap-2 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row"><label className="sr-only" htmlFor="agent-name">Agent name</label><Input id="agent-name" autoFocus maxLength={255} required value={name} onChange={(event) => setName(event.target.value)} placeholder="Agent name" /><Button type="submit" disabled={update.isPending}>{update.isPending ? "Saving…" : "Save name"}</Button><Button type="button" variant="outline" onClick={() => setRenameOpen(false)}>Cancel</Button>{renameError && <p role="alert" className="basis-full text-sm text-rose-700">{renameError}</p>}</form>}
      {deleteError && <p role="alert" className="mb-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{deleteError}</p>}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(380px,1fr)]"><section className="flex flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-6"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Current version</p><h2 className="mt-1 text-lg font-semibold">{agent.data.latest_version.version}</h2></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-600">Latest</span></div><p className="mt-3 text-sm text-slate-500">{agent.data.latest_version.schema.description || "No description provided."}</p><dl className="mt-5 space-y-4 border-t border-slate-100 pt-4 text-sm"><div className="flex items-center gap-3"><Cpu size={15} className="shrink-0 text-slate-400"/><dt className="w-20 shrink-0 text-xs text-slate-400">Model</dt><dd className="min-w-0 truncate text-slate-600">{agent.data.latest_version.schema.model ? `${agent.data.latest_version.schema.model.provider} · ${agent.data.latest_version.schema.model.name}` : "Not configured"}</dd></div><div className="flex items-center gap-3"><Wrench size={15} className="shrink-0 text-slate-400"/><dt className="w-20 shrink-0 text-xs text-slate-400">Tools</dt><dd className="text-slate-600">{agent.data.latest_version.schema.tools?.length ?? 0} {(agent.data.latest_version.schema.tools?.length ?? 0) === 1 ? "tool" : "tools"}</dd></div><div className="flex items-center gap-3"><MessageSquareText size={15} className="shrink-0 text-slate-400"/><dt className="w-20 shrink-0 text-xs text-slate-400">Prompt</dt><dd className="text-slate-600">{agent.data.latest_version.schema.prompt.developer ? "System + developer" : "System"}</dd></div></dl><Button variant="outline" size="sm" className="mt-auto self-start" onClick={() => setDetailsVersionId(agent.data!.latest_version.id)}><Code2 size={14} />View configuration</Button></section><ClassificationPanel agentId={agentId} version={agent.data.latest_version} /></div>
      <section className="mt-10"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-semibold tracking-[-0.03em]">Versions <span className="ml-1 rounded-md bg-slate-100 px-1.5 py-0.5 align-middle text-xs font-medium text-slate-500">{versions.data?.total ?? 0}</span></h2><p className="mt-1 text-sm text-slate-500">Immutable agent definitions, newest first.</p></div><Button onClick={() => setNewVersionOpen(true)}><Plus size={15} />New version</Button></div>
        {versions.isLoading ? <div className="mt-4 space-y-3">{[1, 2].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-white" />)}</div> : versions.isError ? <div role="alert" className="mt-4 rounded-xl border border-rose-200 bg-white p-5 text-sm text-rose-700">Couldn't load versions. <Button variant="outline" size="sm" className="ml-2" onClick={() => void versions.refetch()}>Retry</Button></div> : <div className="mt-4 space-y-3">{(versions.data?.items ?? []).map((version, index) => <article key={version.id} className="flex flex-col gap-4 rounded-xl border border-slate-200/80 bg-white p-4 shadow-soft sm:flex-row sm:items-center sm:justify-between sm:p-5"><div className="flex min-w-0 items-center gap-4"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-semibold ${index === 0 ? "bg-indigo-50 text-indigo-700" : "bg-slate-100 text-slate-600"}`}>v</span><div className="min-w-0"><h3 className="truncate font-semibold text-slate-900">Version {version.version}{index === 0 && <span className="ml-2 rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">Latest</span>}</h3><p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><CalendarDays size={12} />{formatDate(version.created_at)}</span><span>{version.classification_id ? "Classification ready" : "Not classified"}</span></p></div></div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" onClick={() => setDetailsVersionId(version.id)}><Code2 size={14} />View configuration</Button><Button asChild size="sm"><Link to={`/agents/${encodeURIComponent(agentId)}/compare?versions=${encodeURIComponent(version.id)}`}><ArrowLeftRight size={14} />Compare</Link></Button></div></article>)}{versions.data?.items.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">No versions found.</p>}</div>}
      </section>
      <AgentDetails agentId={agentId} versionId={detailsVersionId} open={Boolean(detailsVersionId)} onOpenChange={(open) => { if (!open) setDetailsVersionId(null); }} />
      <AgentJsonDialog open={newVersionOpen} onOpenChange={setNewVersionOpen} title="Create a version" description="Add a new immutable schema revision. Enter a unique version label." submitLabel="Create version" fieldLabel="Version JSON" endpoint={`POST /api/v1/agents/${agentId}/versions`} example={versionExample} initialValue={{ version: "", schema: latestSchema ?? ({} as AgentSchema) }} onSubmit={handleVersion} />
    </> : null}
  </main></WorkspaceLayout>;
}
