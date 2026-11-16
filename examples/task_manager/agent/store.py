"""Simple in-memory task storage used by the Task Manager tools."""

from datetime import date


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[int, dict[str, object]] = {}
        self._next_id = 1

    def add(self, title: str, due_date: str | None = None) -> dict[str, object]:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be blank")
        clean_due_date = _iso_date(due_date) if due_date else None
        task = {
            "id": self._next_id,
            "title": clean_title,
            "due_date": clean_due_date,
            "completed": False,
        }
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task.copy()

    def list(self, include_completed: bool = True) -> list[dict[str, object]]:
        return [
            task.copy()
            for task in self._tasks.values()
            if include_completed or not task["completed"]
        ]

    def get(self, task_id: int) -> dict[str, object]:
        return self._find(task_id).copy()

    def postpone(self, task_id: int, new_due_date: str) -> dict[str, object]:
        task = self._find(task_id)
        if task["due_date"] is None:
            raise ValueError("Task has no due date to postpone")
        updated_date = _iso_date(new_due_date)
        if updated_date <= str(task["due_date"]):
            raise ValueError("New due date must be later than the current due date")
        task["due_date"] = updated_date
        return task.copy()

    def complete(self, task_id: int) -> dict[str, object]:
        task = self._find(task_id)
        task["completed"] = True
        return task.copy()

    def _find(self, task_id: int) -> dict[str, object]:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise ValueError(f"Task {task_id} does not exist") from exc


def _iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Date must use ISO format YYYY-MM-DD") from exc
    return parsed.isoformat()
