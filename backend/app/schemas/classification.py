from pydantic import BaseModel, ConfigDict, Field


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
