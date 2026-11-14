from typing import Any


def capture(messages: list[Any]) -> dict[str, Any]:
    ordered, calls, results, responses = [], [], [], []
    for message in messages:
        kind = getattr(message, "type", "")
        if kind == "human":
            ordered.append({"role": "user", "content": str(message.content)})
        elif kind == "ai":
            content = message.content
            ordered.append({"role": "assistant", "content": content})
            if content:
                responses.append(content)
            for call in getattr(message, "tool_calls", []) or []:
                row = {
                    "id": call.get("id"),
                    "name": call.get("name"),
                    "args": call.get("args", {}),
                }
                calls.append(row)
                ordered.append({"role": "assistant", "tool_call": row})
        elif kind == "tool":
            row = {
                "tool_call_id": getattr(message, "tool_call_id", None),
                "name": getattr(message, "name", None),
                "content": message.content,
            }
            results.append(row)
            ordered.append({"role": "tool", **row})
    result = {"messages": ordered, "tool_calls": calls, "tool_results": results}
    if responses:
        result["final_response"] = responses[-1]
    return result


def case_execution(
    case: dict, captured: dict | None = None, error: str | None = None
) -> dict:
    execution = captured or {
        "messages": [{"role": "user", "content": case["question"]}],
        "tool_calls": [],
        "tool_results": [],
    }
    if error:
        execution["runtime_error"] = error
    return {"test_case_id": case["id"], "execution": execution}
