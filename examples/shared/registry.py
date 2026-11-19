from task_manager.agent.agent import TaskManagerAgent
from task_manager.config import DESCRIPTION, MODEL, NAME, SYSTEM_PROMPT

from shared.agents import AgentDefinition

AGENTS = {
    "task_manager": AgentDefinition(
        name=NAME,
        description=DESCRIPTION,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        create=lambda: TaskManagerAgent(MODEL),
    )
}


def get_agent(name: str) -> AgentDefinition:
    try:
        return AGENTS[name]
    except KeyError as exc:
        available = ", ".join(sorted(AGENTS))
        raise ValueError(
            f"Unknown agent {name!r}. Available agents: {available}"
        ) from exc
