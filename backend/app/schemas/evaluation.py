from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RubricScores(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    adherence_score: float = Field(ge=0, le=1)
    consistency_score: float = Field(ge=0, le=1)
    grounding_score: float = Field(ge=0, le=1)
    adherence_explanation: str = Field(min_length=1)
    consistency_explanation: str = Field(min_length=1)
    grounding_explanation: str = Field(min_length=1)

    @field_validator(
        "adherence_explanation",
        "consistency_explanation",
        "grounding_explanation",
    )
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Explanations cannot be blank")
        return value


class EvaluationCaseResponse(RubricScores):
    id: str
    test_case_id: str
    category: str


class TestSuiteEvaluationResponse(BaseModel):
    id: str
    test_suite_id: str
    trace_id: str
    status: Literal["queued", "running", "completed", "failed"]
    judge_model: str
    rubric_version: str
    classification_snapshot: dict[str, object]
    error: str | None
    created_at: datetime
    updated_at: datetime
    results: list[EvaluationCaseResponse] = Field(default_factory=list)
