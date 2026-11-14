import json

from task_manager.tempr._internal.trace import capture_messages, case_execution


class Message:
    def __init__(self, kind, content, **attributes):
        self.type = kind
        self.content = content
        for name, value in attributes.items():
            setattr(self, name, value)


def test_capture_messages_preserves_tool_calls_results_and_response():
    messages = [
        Message("human", "Add a task"),
        Message(
            "ai",
            "",
            tool_calls=[
                {"id": "call-1", "name": "add_task", "args": {"title": "Read"}}
            ],
        ),
        Message("tool", '{"ok":true}', tool_call_id="call-1", name="add_task"),
        Message("ai", "Added task 1."),
    ]

    captured = capture_messages(messages)
    json.dumps(captured)

    assert captured["final_response"] == "Added task 1."
    assert captured["tool_calls"][0]["name"] == "add_task"
    assert captured["tool_results"][0]["tool_call_id"] == "call-1"
    assert [item["role"] for item in captured["messages"]] == [
        "user",
        "assistant",
        "assistant",
        "tool",
        "assistant",
    ]


def test_case_execution_records_runtime_error_with_case_id():
    entry = case_execution("tc_1", "Add a task", error="RuntimeError: unavailable")

    assert entry == {
        "test_case_id": "tc_1",
        "execution": {
            "messages": [{"role": "user", "content": "Add a task"}],
            "tool_calls": [],
            "tool_results": [],
            "runtime_error": "RuntimeError: unavailable",
        },
    }
