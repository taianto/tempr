from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.test_categories import TestCategory


class TestSuiteGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    total_count: int = Field(default=20, ge=1, le=100)


class GeneratedTestSuiteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: TestCategory
    question: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)

    @field_validator("question", "expected_behavior")
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Generated text cannot be blank")
        return value


class GeneratedTestSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GeneratedTestSuiteItem]


class TestSuiteGenerationResponse(BaseModel):
    id: str
    version_id: str
    status: Literal["queued", "running", "completed", "failed"]
    requested_count: int
    allocation: dict[str, int]
    has_completed_suite: bool
    error: str | None
    created_at: datetime
    updated_at: datetime


class TestSuiteResponse(TestSuiteGenerationResponse):
    items: list[GeneratedTestSuiteItem] = Field(default_factory=list)
    generated_at: datetime | None = None
