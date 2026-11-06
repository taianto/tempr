from datetime import datetime

from pydantic import BaseModel, ConfigDict, JsonValue


class TestSuiteTraceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace: JsonValue


class TestSuiteTraceResponse(BaseModel):
    id: str
    test_suite_id: str
    trace: JsonValue
    created_at: datetime
