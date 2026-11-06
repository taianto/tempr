from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from app.schemas.evaluation import TestSuiteEvaluationResponse
from app.services.evaluation_worker import run_evaluation
from app.services.evaluations import (
    EvaluationService,
    EvaluationServiceError,
    evaluation_response,
)

router = APIRouter(prefix="/test-suites", tags=["test suite evaluations"])


@router.post(
    "/{test_suite_id}/evaluation",
    response_model=TestSuiteEvaluationResponse,
)
def create_evaluation(
    test_suite_id: str,
    background_tasks: BackgroundTasks,
    response: Response,
    service: Annotated[EvaluationService, Depends(EvaluationService)],
    refresh: bool = False,
) -> TestSuiteEvaluationResponse:
    try:
        record, created = service.enqueue(test_suite_id, refresh)
    except EvaluationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if created:
        background_tasks.add_task(run_evaluation, record.id)
        response.status_code = status.HTTP_202_ACCEPTED
        response.headers["Location"] = f"/api/v1/test-suites/{test_suite_id}/evaluation"
    elif record.status in ("queued", "running"):
        response.status_code = status.HTTP_202_ACCEPTED
    return TestSuiteEvaluationResponse(**evaluation_response(record))


@router.get(
    "/{test_suite_id}/evaluation",
    response_model=TestSuiteEvaluationResponse,
)
def get_evaluation(
    test_suite_id: str,
    service: Annotated[EvaluationService, Depends(EvaluationService)],
) -> TestSuiteEvaluationResponse:
    try:
        record = service.get(test_suite_id)
    except EvaluationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TestSuiteEvaluationResponse(**evaluation_response(record))
