from tempr.integrations.langchain import TracedAgent


class FakeAgent:
    def invoke(self, inputs, config=None):
        return {
            "messages": [
                {"type": "human", "content": "Add a task"},
                {
                    "type": "ai",
                    "content": "",
                    "tool_calls": [
                        {"id": "call-1", "name": "add_task", "args": {"title": "Task"}}
                    ],
                },
                {
                    "type": "tool",
                    "tool_call_id": "call-1",
                    "name": "add_task",
                    "content": '{"ok": true}',
                },
                {"type": "ai", "content": "Added the task."},
            ]
        }


def test_traced_agent_keeps_events_ordered_and_emits_case_execution():
    result = TracedAgent(FakeAgent()).run({"messages": [("user", "Add a task")]})

    assert result.execution == {
        "steps": [
            {"type": "user", "content": "Add a task"},
            {
                "type": "tool_call",
                "id": "call-1",
                "name": "add_task",
                "args": {"title": "Task"},
            },
            {
                "type": "tool_result",
                "tool_call_id": "call-1",
                "name": "add_task",
                "content": '{"ok": true}',
            },
            {"type": "assistant", "content": "Added the task."},
        ],
        "final_response": "Added the task.",
    }
    assert result.for_case("case-1") == {
        "test_case_id": "case-1",
        "execution": result.execution,
    }
