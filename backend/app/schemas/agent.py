from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Agent
from app.schemas.version import (
    AgentVersionResponse,
    AgentVersionSummary,
    InitialVersion,
)


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    initial_version: InitialVersion


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)


class AgentResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    latest_version: AgentVersionResponse

    @classmethod
    def from_record(cls, agent: Agent) -> "AgentResponse":
        if not agent.versions:
            raise ValueError("Agent has no version")
        return cls(
            id=agent.id,
            name=agent.name,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            latest_version=AgentVersionResponse.from_record(agent.versions[0]),
        )


class AgentListItem(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    latest_version: AgentVersionSummary

    @classmethod
    def from_record(cls, agent: Agent) -> "AgentListItem":
        if not agent.versions:
            raise ValueError("Agent has no version")
        return cls(
            id=agent.id,
            name=agent.name,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            latest_version=AgentVersionSummary.from_record(agent.versions[0]),
        )


class AgentListResponse(BaseModel):
    items: list[AgentListItem]
    total: int
