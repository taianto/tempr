from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Classification as ClassificationRecord


class Classification(BaseModel):
    """Relative test-generation priority assigned to each supported category."""

    model_config = ConfigDict(extra="forbid")

    happy_path: float = Field(ge=0, le=1)
    boundary_probe: float = Field(ge=0, le=1)
    missing_information: float = Field(ge=0, le=1)
    ambiguous_input: float = Field(ge=0, le=1)
    prompt_injection: float = Field(ge=0, le=1)
    policy_bypass: float = Field(ge=0, le=1)
    sensitive_data_request: float = Field(ge=0, le=1)
    hallucination_probe: float = Field(ge=0, le=1)


class ClassificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: str


class ClassificationResponse(BaseModel):
    id: str
    scores: Classification
    classifier_model: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: ClassificationRecord) -> "ClassificationResponse":
        scores = Classification.model_validate(
            {key: float(getattr(record, key)) for key in Classification.model_fields}
        )
        return cls(
            id=record.id,
            scores=scores,
            classifier_model=record.classifier_model,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
