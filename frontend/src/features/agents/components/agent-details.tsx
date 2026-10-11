import { useState } from "react";
import { AlertTriangle, Bot, CalendarDays, Code2, Cpu, Pencil, Trash2, Wrench } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import { useAgent, useDeleteAgent } from "../hooks/use-agents";

export function AgentDetails({ agentId, open, onOpenChange, onEdit }: { agentId: string | null; open: boolean; onOpenChange: (open: boolean) => void; onEdit: (agent: import("../types").Agent) => void }) {
  const query = useAgent(agentId ?? "", open);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const deleteAgent = useDeleteAgent();

  async function handleDelete() {
    if (!agentId) return;
    setDeleteError(null);
    try {
      await deleteAgent.mutateAsync(agentId);
      setConfirmDelete(false);
      onOpenChange(false);
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Couldn't delete this agent. Please try again.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby="agent-details-description">
        {query.isLoading ? <div className="space-y-5 pt-8"><Skeleton className="h-12 w-12" /><Skeleton className="h-7 w-2/3" /><Skeleton className="h-20 w-full" /><Skeleton className="h-28 w-full" /></div> : query.isError ? (
          <div className="flex min-h-[60vh] flex-col items-center justify-center text-center"><div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-rose-50 text-rose-600"><Bot size={22} /></div><DialogTitle className="text-lg font-semibold">Couldn't load agent</DialogTitle><DialogDescription className="mt-2 max-w-xs text-sm text-slate-500">{query.error.message}</DialogDescription><Button className="mt-5" variant="outline" onClick={() => void query.refetch()}>Try again</Button></div>
        ) : query.data ? (
          <div className="pt-8">
            <div className="flex items-start gap-4"><div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] bg-indigo-50 text-indigo-600"><Bot size={24} /></div><div className="min-w-0"><div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-indigo-500" /><span className="text-xs font-medium text-indigo-700">Configured</span></div><DialogTitle className="mt-1 break-words text-2xl font-semibold tracking-[-0.04em] text-slate-900">{query.data.name}</DialogTitle></div></div>
            <DialogDescription id="agent-details-description" className="mt-5 text-sm leading-6 text-slate-500">{query.data.description || "No description provided yet."}</DialogDescription>
            <div className="mt-5 flex gap-2"><Button variant="outline" size="sm" className="h-9" onClick={() => onEdit(query.data)}><Pencil size={14} />Edit JSON</Button><Button variant="ghost" size="sm" className="h-9 text-rose-600 hover:bg-rose-50 hover:text-rose-700" onClick={() => { setDeleteError(null); setConfirmDelete(true); }}><Trash2 size={14} />Delete</Button></div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 border-y border-slate-100 py-4"><span className="inline-flex items-center gap-1.5 text-xs text-slate-500"><CalendarDays size={14} />Updated {formatDate(query.data.updated_at)}</span><span className="inline-flex items-center gap-1.5 text-xs text-slate-500"><Wrench size={14} />{query.data.tools.length} tools</span></div>
            <div className="mt-7 space-y-6">
              <section><h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400"><Cpu size={14} />Model</h3><div className="mt-3 rounded-xl border border-slate-200/80 bg-slate-50/60 p-4">{query.data.model ? <><p className="text-sm font-medium text-slate-800">{query.data.model.name}</p><p className="mt-1 text-xs capitalize text-slate-500">{query.data.model.provider}</p>{Object.keys(query.data.model.parameters).length > 0 && <pre className="mt-3 overflow-x-auto text-xs leading-5 text-slate-500">{JSON.stringify(query.data.model.parameters, null, 2)}</pre>}</> : <p className="text-sm text-slate-500">No model configuration provided.</p>}</div></section>
              <section><h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400"><Code2 size={14} />System prompt</h3><pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200/80 bg-slate-50/60 p-4 font-sans text-sm leading-6 text-slate-600">{query.data.prompt.system}</pre></section>
              {query.data.prompt.developer && <section><h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Developer prompt</h3><pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-200/80 bg-slate-50/60 p-4 font-sans text-sm leading-6 text-slate-600">{query.data.prompt.developer}</pre></section>}
              <section><h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400"><Wrench size={14} />Tools</h3>{query.data.tools.length ? <div className="mt-3 space-y-2">{query.data.tools.map((tool) => <div key={tool.name} className="rounded-xl border border-slate-200/80 p-4"><p className="text-sm font-medium text-slate-800">{tool.name}</p>{tool.description && <p className="mt-1 text-sm leading-5 text-slate-500">{tool.description}</p>}</div>)}</div> : <p className="mt-3 rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">No tools configured.</p>}</section>
            </div>
          </div>
        ) : null}
      </DialogContent>
      <Dialog open={confirmDelete} onOpenChange={(nextOpen) => { if (!deleteAgent.isPending) setConfirmDelete(nextOpen); }}>
        <DialogContent aria-describedby="delete-agent-description" className="inset-0 bottom-auto left-1/2 right-auto top-1/2 h-fit max-h-[90vh] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border p-6 sm:p-6">
          <div className="pt-5"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600"><AlertTriangle size={19} /></div><DialogTitle className="mt-4 text-lg font-semibold text-slate-900">Delete {query.data?.name ?? "this agent"}?</DialogTitle><DialogDescription id="delete-agent-description" className="mt-2 text-sm leading-5 text-slate-500">This permanently removes the agent definition from your workspace. This action cannot be undone.</DialogDescription>{deleteError && <p role="alert" className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{deleteError}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="outline" disabled={deleteAgent.isPending} onClick={() => setConfirmDelete(false)}>Cancel</Button><Button variant="default" className="bg-rose-600 text-white hover:bg-rose-700" disabled={deleteAgent.isPending} onClick={() => void handleDelete()}>{deleteAgent.isPending ? "Deleting…" : "Delete agent"}</Button></div></div>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
