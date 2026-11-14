from typing import Any


def configuration(
    name: str, description: str, model_name: str, prompt: str, tools: list[Any]
) -> dict[str, Any]:
    definitions = []
    for tool in tools:
        schema = tool.args_schema.model_json_schema()
        schema.pop("title", None)
        definitions.append(
            {"name": tool.name, "description": tool.description, "input_schema": schema}
        )
    return {
        "description": description,
        "prompt": {"system": prompt},
        "model": {"provider": "openai", "name": model_name, "parameters": {}},
        "tools": definitions,
        "metadata": {"example": name},
    }
