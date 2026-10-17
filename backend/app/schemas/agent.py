from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.classification import Classification as ClassificationScores
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


class AgentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str | None = None
    prompt: PromptConfig
    model: ModelConfig | None = None
    tools: list[ToolDefinition] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(default="1.0", min_length=1, max_length=64)
    schema_: AgentSchema = Field(alias="schema")

    @field_validator("version")
    @classmethod
    def trim_version(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Version label cannot be blank")
        return value


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    initial_version: VersionInput


class AgentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)


class VersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=64)
    schema_: AgentSchema = Field(alias="schema")

    @field_validator("version")
    @classmethod
    def trim_version(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Version label cannot be blank")
        return value


class ClassificationResponse(BaseModel):
    id: str
    scores: ClassificationScores
    classifier_model: str
    created_at: datetime
    updated_at: datetime


class AgentVersionSummary(BaseModel):
    id: str
    version: str
    created_at: datetime
    classification_id: str | None


class AgentVersionResponse(AgentVersionSummary):
    model_config = ConfigDict(populate_by_name=True)
    agent_id: str
    schema_: AgentSchema = Field(alias="schema")
    classification: ClassificationResponse | None


class AgentResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    latest_version: AgentVersionResponse


class AgentListItem(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    latest_version: AgentVersionSummary


class AgentListResponse(BaseModel):
    items: list[AgentListItem]
    total: int


class AgentVersionListResponse(BaseModel):
    items: list[AgentVersionSummary]
    total: int
