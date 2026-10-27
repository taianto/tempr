import { useIsMutating, useQueries } from "@tanstack/react-query";
import { LoaderCircle, Plus, X } from "lucide-react";
import { useEffect } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { versionsApi } from "./api";
import { CATEGORIES } from "./classification-categories";
import { WorkspaceLayout } from "./components/workspace-layout";
import { agentKeys, useAgent, useClassify, useVersions } from "./hooks/use-agents";

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

export function ComparePage() {
  const { agentId = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
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
  const selectedSet = new Set(selectedIds);
  const candidates = (versions.data?.items ?? []).filter((version) => !selectedSet.has(version.id));

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
    if (selectedIds.length > 1) update(selectedIds.filter((item) => item !== id));
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
              Compare allocations
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Compare suggested test case allocation by category.
            </p>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500">
            Testing allocation percentages
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
                  const wrongAgent = Boolean(column?.data && !value);
                  return (
                    <th scope="col" key={id} className="min-w-56 px-4 py-4 align-top">
                      <div className="flex min-h-8 items-center justify-between gap-2">
                        <div>
                          <span className="block text-sm font-semibold text-slate-900">
                            {value
                              ? `Version ${value.version}`
                              : column?.isError || wrongAgent
                                ? "Unavailable version"
                                : "Loading version…"}
                          </span>
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
                          {selectedIds.length > 1 && (
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
                      {(column?.isError || wrongAgent) && (
                        <p className="mt-2 text-xs text-rose-700">
                          This version could not be loaded.
                        </p>
                      )}
                      {column?.isLoading && (
                        <span className="mt-2 inline-flex text-xs text-slate-400">Loading…</span>
                      )}
                      {value && !value.classification && <UnclassifiedAction versionId={id} />}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {CATEGORIES.map((category) => (
                <tr key={category.key} className="border-b border-slate-100 last:border-0">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-r border-slate-100 bg-white px-4 py-4 text-sm font-medium text-slate-700"
                  >
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-2 shrink-0 rounded-full ${category.color}`} />
                      {category.label}
                    </span>
                  </th>
                  {selectedIds.map((id, index) => {
                    const column = columns[index];
                    const value = column.data;
                    const belongsToAgent = value?.agent_id === agentId;
                    const score = belongsToAgent
                      ? value.classification?.scores[category.key]
                      : undefined;
                    return (
                      <td
                        key={`${id}-${category.key}`}
                        className="px-4 py-4 text-sm tabular-nums text-slate-700"
                      >
                        {typeof score === "number" ? (
                          `${Math.round(score * 100)}%`
                        ) : column.isError || (column.data && !belongsToAgent) ? (
                          <span className="text-xs text-rose-400">Unavailable</span>
                        ) : (
                          "—"
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
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
          Each allocation is a suggested share of test cases. Generating or regenerating a
          classification analyzes the agent definition and does not run tests.
        </p>
      </main>
    </WorkspaceLayout>
  );
}

function UnclassifiedAction({ versionId }: { versionId: string }) {
  const classify = useClassify(versionId);
  const pending = useIsMutating({ mutationKey: ["classify", versionId] }) > 0;
  return (
    <div className="mt-3">
      <Button size="sm" variant="outline" onClick={() => classify.mutate()} disabled={pending}>
        <span className="sr-only">Generate classification for this version</span>
        {pending ? <LoaderCircle size={14} className="animate-spin" /> : <Plus size={14} />}{" "}
        {pending ? "Generating…" : "Generate classification"}
      </Button>
      {classify.isError && (
        <p role="alert" className="mt-2 max-w-48 text-xs text-rose-700">
          {classify.error.message}
          <button type="button" className="ml-1 underline" onClick={() => classify.mutate()}>
            Retry
          </button>
        </p>
      )}
    </div>
  );
}
