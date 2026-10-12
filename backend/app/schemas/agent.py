from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tool import ToolDefinition


class PromptConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str = Field(min_length=1)
    developer: str | None = None


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    prompt: PromptConfig
    model: ModelConfig | None = None
    tools: list[ToolDefinition] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    prompt: PromptConfig | None = None
    model: ModelConfig | None = None
    tools: list[ToolDefinition] | None = None
    metadata: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    prompt: PromptConfig
    model: ModelConfig | None
    tools: list[ToolDefinition]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentListItem(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentListItem]
    total: int
