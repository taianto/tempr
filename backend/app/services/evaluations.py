from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models import TestSuiteEvaluation
from app.prompts.evaluation import RUBRIC_VERSION
from app.repositories.evaluations import EvaluationRepository


class EvaluationServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class EvaluationService:
    def __init__(
        self,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> None:
        self.settings = settings
        self.repository = EvaluationRepository(db)

    def get(self, test_suite_id: str) -> TestSuiteEvaluation:
        record = self.repository.get(test_suite_id)
        if record is None:
            raise EvaluationServiceError(404, "Test suite evaluation not found")
        return record

    def enqueue(
        self, test_suite_id: str, refresh: bool
    ) -> tuple[TestSuiteEvaluation, bool]:
        api_key = self.settings.openai_api_key
        configured = api_key is not None and bool(api_key.get_secret_value().strip())
        record, error, created = self.repository.enqueue(
            test_suite_id,
            self.settings.evaluation_model or self.settings.classification_model,
            RUBRIC_VERSION,
            refresh,
            configured,
        )
        if record is not None:
            return record, created
        if error == "Test suite not found":
            status_code = 404
        elif error in (
            "Test suite generation must complete before evaluation",
            "A trace is required before evaluation",
        ):
            status_code = 409
        elif error and error.startswith("Evaluation is not configured"):
            status_code = 503
        else:
            status_code = 422
        raise EvaluationServiceError(status_code, error or "Unable to queue evaluation")


def evaluation_response(record: TestSuiteEvaluation) -> dict[str, Any]:
    by_case = {item.test_case_id: item for item in record.evaluations}
    suite_order = [
        item["id"] for item in record.test_suite.result_json.get("items", [])
    ]
    ordered = [by_case[case_id] for case_id in suite_order if case_id in by_case]
    return {
        "id": record.id,
        "test_suite_id": record.test_suite_id,
        "trace_id": record.trace_id,
        "status": record.status,
        "judge_model": record.judge_model,
        "rubric_version": record.rubric_version,
        "classification_snapshot": record.classification_snapshot,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "results": [
            {
                "id": result.id,
                "test_case_id": result.test_case_id,
                "category": result.category,
                "adherence_score": float(result.adherence_score),
                "consistency_score": float(result.consistency_score),
                "grounding_score": float(result.grounding_score),
                "adherence_explanation": result.adherence_explanation,
                "consistency_explanation": result.consistency_explanation,
                "grounding_explanation": result.grounding_explanation,
            }
            for result in ordered
        ],
    }
