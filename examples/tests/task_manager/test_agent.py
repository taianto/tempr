from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from task_manager.agent.agent import TaskManagerAgent


class ScriptedModel(BaseChatModel):
    responses: list[AIMessage]

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "scripted-test-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


def test_scripted_agent_uses_tools_and_remembers_chat_turns():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add_task",
                        "args": {
                            "title": "Prepare release notes",
                            "due_date": "2026-12-01",
                        },
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Added task 1."),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_tasks",
                        "args": {"include_completed": True},
                        "id": "call-2",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Task 1 is Prepare release notes, due 2026-12-01."),
        ]
    )
    agent = TaskManagerAgent(model_name="scripted", model=model)

    first_turn = agent.run("Add release notes due December 1, 2026")
    second_turn = agent.run("What tasks do I have?")

    assert first_turn[-1].content == "Added task 1."
    assert second_turn[-1].content.startswith("Task 1 is Prepare release notes")
    assert len(agent.messages) == 8
    assert agent.store.get(1)["title"] == "Prepare release notes"
