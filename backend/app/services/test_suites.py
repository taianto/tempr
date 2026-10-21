from datetime import datetime
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db
from app.db.models import Classification, TestSuite
from app.domain.apportionment import hamilton_apportion
from app.domain.test_categories import TEST_CATEGORIES
from app.repositories.test_suites import TestSuiteRepository
from app.services.agents import AgentService


class TestSuiteServiceError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class TestSuiteService:
    def __init__(
        self, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
    ) -> None:
        self.db = db
        self.settings = settings
        self.repository = TestSuiteRepository(db)

    def get(self, agent_id: str, version_id: str) -> TestSuite | None:
        try:
            AgentService(self.db).get_version(agent_id, version_id)
        except HTTPException as exc:
            raise TestSuiteServiceError(exc.status_code, exc.detail) from exc
        return self.repository.get(version_id)

    def generate(
        self, agent_id: str, version_id: str, total_count: int
    ) -> TestSuite:
        version = AgentService(self.db).get_version(agent_id, version_id)
        classification = version.classification
        if classification is None:
            raise TestSuiteServiceError(409, "Classify this agent version before generating a test suite")

        api_key = self.settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise TestSuiteServiceError(503, "Test suite generation is not configured: please set up LLM API key")

        scores = {name: float(getattr(classification, name)) for name in TEST_CATEGORIES}
        try:
            allocation = hamilton_apportion(scores, total_count)
        except ValueError as exc:
            raise TestSuiteServiceError(409, "The saved classification has invalid category weights") from exc

        request = self._get_suite_metadata(classification, total_count, scores, allocation)
        try:
            record = self.repository.enqueue(version_id, request)
        except ValueError as exc:
            raise TestSuiteServiceError(409, str(exc)) from exc
        if record is None:
            raise TestSuiteServiceError(404, "Agent version not found")
        return record
    
    def _get_suite_metadata(self, classification: Classification, total_count: int, scores: dict[str, float], allocation: dict[str, int]):
        return {
            "total_count": total_count,
            "classification_id": classification.id,
            "classification_updated_at": classification.updated_at.isoformat(),
            "classification_model": classification.classifier_model,
            "classification_scores": scores,
            "allocation": allocation,
            "model": self.settings.test_generation_model or self.settings.classification_model,
        }


def test_suite_response(record: TestSuite) -> dict[str, Any]:
    request = record.request_json
    return {
        "id": record.id,
        "version_id": record.version_id,
        "status": record.status,
        "requested_count": request["total_count"],
        "allocation": request["allocation"],
        "has_completed_suite": record.result_json is not None,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def test_suite_detail_response(record: TestSuite) -> dict[str, Any]:
    result = record.result_json or {}
    return {
        **test_suite_response(record),
        "items": result.get("items", []),
        "generated_at": result.get("generated_at"),
    }


def completed_result(
    request: dict[str, Any], items: list[dict[str, Any]], generated_at: datetime
) -> dict[str, Any]:
    return {**request, "items": items, "generated_at": generated_at.isoformat()}
