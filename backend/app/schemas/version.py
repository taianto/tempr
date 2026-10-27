from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import AgentVersion
from app.schemas.classification import ClassificationResponse
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


class InitialVersion(VersionCreate):
    version: str = Field(default="1.0", min_length=1, max_length=64)


class VersionCreateRequest(VersionCreate):
    agent_id: str


class AgentVersionSummary(BaseModel):
    id: str
    version: str
    created_at: datetime
    classification_id: str | None

    @classmethod
    def from_record(cls, version: AgentVersion) -> "AgentVersionSummary":
        return cls(
            id=version.id,
            version=version.version,
            created_at=version.created_at,
            classification_id=version.classification_id,
        )


class AgentVersionResponse(AgentVersionSummary):
    model_config = ConfigDict(populate_by_name=True)
    agent_id: str
    schema_: AgentSchema = Field(alias="schema")
    classification: ClassificationResponse | None

    @classmethod
    def from_record(cls, version: AgentVersion) -> "AgentVersionResponse":
        return cls(
            **AgentVersionSummary.from_record(version).model_dump(),
            agent_id=version.agent_id,
            schema_=AgentSchema(
                description=version.description,
                prompt=PromptConfig(
                    system=version.system_prompt, developer=version.developer_prompt
                ),
                model=version.model_config_json,
                tools=version.tools,
                metadata=version.metadata_json,
            ),
            classification=(
                ClassificationResponse.from_record(version.classification)
                if version.classification is not None
                else None
            ),
        )


class AgentVersionListResponse(BaseModel):
    items: list[AgentVersionSummary]
    total: int
