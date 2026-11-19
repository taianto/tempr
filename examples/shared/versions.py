from typing import Any

from tempr.client import TemprAPIError


def create_next_version(
    client: Any, name: str, description: str, schema: dict
) -> tuple[str, dict]:
    agents = client.list_agents().get("items", [])
    matches = [agent for agent in agents if agent["name"] == name]
    if len(matches) > 1:
        raise TemprAPIError(
            f"Multiple agents named {name!r}; rename or remove duplicates"
        )
    if not matches:
        created = client.create_agent(name, "0.1", schema)
        return created["id"], created["latest_version"]
    agent_id = matches[0]["id"]
    versions = client.list_versions(agent_id).get("items", [])
    tenths = []
    for item in versions:
        parts = item["version"].split(".")
        if (
            len(parts) != 2
            or not all(part.isdigit() for part in parts)
            or int(parts[1]) > 9
        ):
            raise TemprAPIError(f"Unsupported version label {item['version']!r}")
        tenths.append(int(parts[0]) * 10 + int(parts[1]))
    next_tenth = max(tenths, default=0) + 1
    label = f"{next_tenth // 10}.{next_tenth % 10}"
    return agent_id, client.create_version(agent_id, label, schema)
