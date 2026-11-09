import { ChevronRight, Layers3 } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAgents } from "../hooks/use-agents";
import { ThemeSelector } from "./theme-selector";

const API_DOCS_URL = import.meta.env.VITE_API_DOCS_URL || "/docs";

export function WorkspaceLayout({
  children,
  breadcrumb = [],
}: {
  children: ReactNode;
  breadcrumb?: { label: string; to?: string }[];
}) {
  const agents = useAgents();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-10 hidden w-[248px] flex-col border-r border-slate-200/80 bg-white lg:flex">
        <Link
          to="/agents"
          className="flex h-[72px] items-center gap-3 border-b border-slate-100 px-6"
        >
          <img src="/tempr.png" alt="" className="h-8 w-8 shrink-0 object-contain" />
          <span className="text-[17px] font-semibold tracking-[-0.04em]">tempr</span>
          <span className="ml-auto rounded-md border border-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
            BETA
          </span>
        </Link>
        <div className="px-4 pt-7">
          <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            Workspace
          </p>
          <nav aria-label="Main navigation" className="mt-3 space-y-1">
            <Link
              to="/agents"
              className="flex items-center gap-3 rounded-lg bg-slate-100 px-3 py-2.5 text-sm font-medium text-slate-900"
            >
              <Layers3 size={17} className="text-slate-600" />
              Agents
              <span className="ml-auto rounded-md bg-white px-2 py-0.5 text-xs text-slate-500">
                {agents.data?.total ?? "—"}
              </span>
            </Link>
            <a
              href={API_DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
            >
              <span className="flex h-[17px] w-[17px] items-center justify-center rounded bg-slate-100 font-mono text-[9px] font-semibold">
                API
              </span>
              API Docs<span className="ml-auto text-xs text-slate-400">↗</span>
            </a>
          </nav>
        </div>
      </aside>
      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-md sm:px-8 lg:px-10">
          <nav
            aria-label="Breadcrumb"
            className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden text-sm"
          >
            <Link to="/agents" className="font-medium text-slate-500 hover:text-slate-900">
              Agents
            </Link>
            {breadcrumb.map((item) => (
              <span key={item.to ?? item.label} className="flex min-w-0 items-center gap-2">
                <ChevronRight size={14} className="shrink-0 text-slate-300" />
                {item.to ? (
                  <Link
                    to={item.to}
                    className="truncate font-medium text-slate-500 hover:text-slate-900"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="truncate font-medium text-slate-800">
                    {item.label}
                  </span>
                )}
              </span>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <ThemeSelector />
            <span className="hidden items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-500 sm:inline-flex">
              <span
                className={`h-1.5 w-1.5 rounded-full ${agents.isError ? "bg-rose-500" : agents.isSuccess ? "bg-emerald-500" : "bg-amber-400"}`}
              />
              {agents.isError
                ? "API unavailable"
                : agents.isSuccess
                  ? "API connected"
                  : "Connecting"}
            </span>
          </div>
        </header>
        <div className="mx-auto max-w-[1240px] px-5 pb-16 pt-9 sm:px-8 sm:pt-11 lg:px-10">
          {children}
        </div>
      </div>
    </div>
  );
}
