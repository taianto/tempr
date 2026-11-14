import pytest
from task_manager.agent.store import TaskStore


def test_task_store_add_get_list_and_complete():
    store = TaskStore()
    task = store.add("  Write README  ", "2026-12-01")

    assert task == {
        "id": 1,
        "title": "Write README",
        "due_date": "2026-12-01",
        "completed": False,
    }
    assert store.get(1) == task
    assert store.complete(1)["completed"] is True
    assert store.complete(1)["completed"] is True
    assert store.list(include_completed=False) == []


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda store: store.add("  "), "title cannot be blank"),
        (lambda store: store.add("Read", "tomorrow"), "ISO format"),
        (lambda store: store.get(9), "does not exist"),
        (lambda store: store.postpone(9, "2026-12-02"), "does not exist"),
        (lambda store: store.complete(9), "does not exist"),
    ],
)
def test_task_store_rejects_invalid_operations(operation, message):
    with pytest.raises(ValueError, match=message):
        operation(TaskStore())


def test_postpone_requires_a_later_date_and_existing_due_date():
    store = TaskStore()
    no_date = store.add("Read")
    with pytest.raises(ValueError, match="no due date"):
        store.postpone(no_date["id"], "2026-12-02")

    task = store.add("Plan", "2026-12-02")
    with pytest.raises(ValueError, match="must be later"):
        store.postpone(task["id"], "2026-12-02")
    with pytest.raises(ValueError, match="must be later"):
        store.postpone(task["id"], "2026-12-01")
    assert store.postpone(task["id"], "2026-12-03")["due_date"] == "2026-12-03"
