"""Typed LangChain tools for the task manager."""

import json

from langchain.tools import tool

from task_manager.agent.store import TaskStore


def make_tools(store: TaskStore):
    @tool
    def add_task(title: str, due_date: str | None = None) -> str:
        """Add a task with a title and optional due date in YYYY-MM-DD format."""
        return _result(lambda: store.add(title, due_date))

    @tool
    def list_tasks(include_completed: bool = True) -> str:
        """List tasks, optionally excluding tasks that are already complete."""
        return _result(lambda: store.list(include_completed))

    @tool
    def get_task(task_id: int) -> str:
        """Get the current details and status of one task by its ID."""
        return _result(lambda: store.get(task_id))

    @tool
    def postpone_task(task_id: int, new_due_date: str) -> str:
        """Move a task with an existing due date to a later YYYY-MM-DD date."""
        return _result(lambda: store.postpone(task_id, new_due_date))

    @tool
    def complete_task(task_id: int) -> str:
        """Mark a task complete by its ID."""
        return _result(lambda: store.complete(task_id))

    return [add_task, list_tasks, get_task, postpone_task, complete_task]


def _result(operation):
    try:
        return json.dumps({"ok": True, "result": operation()})
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
