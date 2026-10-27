import { ArrowUpRight, Bot, CalendarDays, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import { formatDate, initials } from "@/lib/format";
import type { AgentListItem } from "../types";

const avatarStyles = [
  "bg-indigo-50 text-indigo-600",
  "bg-emerald-50 text-emerald-700",
  "bg-amber-50 text-amber-700",
  "bg-sky-50 text-sky-700",
  "bg-violet-50 text-violet-700",
];

export function AgentCard({ agent, index }: { agent: AgentListItem; index: number }) {
  return (
    <article className="group flex min-h-[247px] flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft transition duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-card sm:p-6">
      <div className="flex items-start justify-between">
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-[14px] ${avatarStyles[index % avatarStyles.length]}`}
        >
          <Bot size={23} strokeWidth={1.8} />
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200/80 bg-indigo-50/70 px-2.5 py-1 text-[11px] font-medium text-indigo-700">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
          Configured
        </span>
      </div>
      <div className="mt-5 flex-1">
        <h3 className="truncate text-[15px] font-semibold tracking-[-0.02em] text-slate-900">
          {agent.name}
        </h3>
        <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-slate-500">
          Version {agent.latest_version.version} ·{" "}
          {agent.latest_version.classification_id ? "Classification ready" : "Needs classification"}
        </p>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
        <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
          <CalendarDays size={13} />
          Updated {formatDate(agent.updated_at)}
        </span>
        <Link
          to={`/agents/${encodeURIComponent(agent.id)}`}
          className="-mr-2 inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs text-slate-600 hover:bg-slate-100"
        >
          View agent <ArrowUpRight size={14} />
        </Link>
      </div>
    </article>
  );
}

export function AgentCardSkeleton() {
  return (
    <div
      className="min-h-[247px] rounded-2xl border border-slate-200/80 bg-white p-6 shadow-soft"
      aria-hidden="true"
    >
      <div className="h-12 w-12 animate-pulse rounded-[14px] bg-slate-100" />
      <div className="mt-5 h-4 w-2/5 animate-pulse rounded bg-slate-100" />
      <div className="mt-3 h-3 w-full animate-pulse rounded bg-slate-100" />
      <div className="mt-2 h-3 w-3/4 animate-pulse rounded bg-slate-100" />
      <div className="mt-7 border-t border-slate-100 pt-4">
        <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
      </div>
    </div>
  );
}

export function AgentMark({ name }: { name: string }) {
  return (
    <div
      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] ${avatarStyles[name.length % avatarStyles.length]} text-sm font-semibold`}
    >
      {initials(name)}
    </div>
  );
}

export function ToolCount({ count }: { count: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
      <Wrench size={13} />
      {count} {count === 1 ? "tool" : "tools"}
    </span>
  );
}
