"""Run a LangChain agent and package its messages as a Tempr execution trace."""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import BaseMessage


def _message_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, BaseMessage):
        return message.model_dump()
    if isinstance(message, dict):
        return message
    return {}


def _content(message: dict[str, Any]) -> Any:
    return message.get("content", "")


def _capture(messages: list[Any]) -> tuple[list[dict[str, Any]], Any]:
    steps: list[dict[str, Any]] = []
    final_response = None
    for raw in messages:
        message = _message_dict(raw)
        role = message.get("type") or message.get("role")
        content = _content(message)
        if role in ("human", "user"):
            steps.append({"type": "user", "content": content})
        elif role in ("ai", "assistant"):
            if content:
                steps.append({"type": "assistant", "content": content})
                final_response = content
            for call in message.get("tool_calls", []) or []:
                steps.append(
                    {
                        "type": "tool_call",
                        "id": call.get("id"),
                        "name": call.get("name"),
                        "args": call.get("args", {}),
                    }
                )
        elif role in ("tool", "tool_result"):
            steps.append(
                {
                    "type": "tool_result",
                    "tool_call_id": message.get("tool_call_id"),
                    "name": message.get("name"),
                    "content": content,
                }
            )
    return steps, final_response


@dataclass(frozen=True)
class TracedRun:
    """The original LangChain output and its Tempr execution trace."""

    output: Any
    execution: dict[str, Any]

    def for_case(self, test_case_id: str) -> dict[str, Any]:
        return {"test_case_id": test_case_id, "execution": self.execution}


class TracedAgent:
    """Wrap a LangChain runnable and capture returned messages in order."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def run(self, inputs: Any, config: Any = None, **kwargs: Any) -> TracedRun:
        output = self.agent.invoke(inputs, config=config, **kwargs)
        messages = output.get("messages", []) if isinstance(output, dict) else []
        steps, final_response = _capture(messages)
        execution: dict[str, Any] = {"steps": steps}
        if final_response is not None:
            execution["final_response"] = final_response
        return TracedRun(output=output, execution=execution)

    async def arun(self, inputs: Any, config: Any = None, **kwargs: Any) -> TracedRun:
        output = await self.agent.ainvoke(inputs, config=config, **kwargs)
        messages = output.get("messages", []) if isinstance(output, dict) else []
        steps, final_response = _capture(messages)
        execution: dict[str, Any] = {"steps": steps}
        if final_response is not None:
            execution["final_response"] = final_response
        return TracedRun(output=output, execution=execution)
