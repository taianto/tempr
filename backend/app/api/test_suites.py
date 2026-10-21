from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from app.schemas.test_suite import TestSuiteGenerationRequest, TestSuiteGenerationResponse, TestSuiteResponse
from app.services.test_suite_worker import run_test_suite_generation
from app.services.test_suites import TestSuiteService, TestSuiteServiceError, test_suite_detail_response, test_suite_response

router = APIRouter(prefix="/agents", tags=["test suites"])


@router.get(
    "/{agent_id}/versions/{version_id}/test-suites",
    response_model=TestSuiteResponse | None,
)
def get_test_suite(
    agent_id: str,
    version_id: str,
    service: Annotated[TestSuiteService, Depends(TestSuiteService)],
) -> TestSuiteResponse | None:
    try:
        record = service.get(agent_id, version_id)
    except TestSuiteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TestSuiteResponse(**test_suite_detail_response(record)) if record else None


@router.post(
    "/{agent_id}/versions/{version_id}/test-suites/generate",
    response_model=TestSuiteGenerationResponse,
)
def generate_test_suite(
    agent_id: str,
    version_id: str,
    background_tasks: BackgroundTasks,
    response: Response,
    service: Annotated[TestSuiteService, Depends(TestSuiteService)],
    payload: TestSuiteGenerationRequest = TestSuiteGenerationRequest(),
) -> TestSuiteGenerationResponse:
    try:
        record = service.generate(agent_id, version_id, payload.total_count)
    except TestSuiteServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    background_tasks.add_task(run_test_suite_generation, record.id)
    response.status_code = status.HTTP_202_ACCEPTED
    return TestSuiteGenerationResponse(**test_suite_response(record))
