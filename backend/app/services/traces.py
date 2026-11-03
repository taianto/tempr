from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import TestSuiteTrace
from app.repositories.traces import TestSuiteTraceRepository


class TestSuiteTraceServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class TestSuiteTraceService:
    def __init__(self, db: Annotated[Session, Depends(get_db)]) -> None:
        self.repository = TestSuiteTraceRepository(db)

    def get(self, test_suite_id: str) -> TestSuiteTrace:
        record = self.repository.get(test_suite_id)
        if record is None:
            raise TestSuiteTraceServiceError(404, "Test suite trace not found")
        return record

    def create(self, test_suite_id: str, trace_json: Any) -> TestSuiteTrace:
        record, error = self.repository.create(test_suite_id, trace_json)
        if record is not None:
            return record
        if error is not None:
            raise TestSuiteTraceServiceError(409, error)
        raise TestSuiteTraceServiceError(404, "Test suite not found")

    def delete(self, test_suite_id: str) -> None:
        if not self.repository.delete(test_suite_id):
            raise TestSuiteTraceServiceError(404, "Test suite trace not found")


def test_suite_trace_response(record: TestSuiteTrace) -> dict[str, Any]:
    return {
        "id": record.id,
        "test_suite_id": record.test_suite_id,
        "trace": record.trace_json,
        "created_at": record.created_at,
    }
