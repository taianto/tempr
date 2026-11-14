from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    model: str
    system_prompt: str
    create: Callable[[], Any]
