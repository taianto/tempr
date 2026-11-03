from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.trace import TestSuiteTraceCreate, TestSuiteTraceResponse
from app.services.traces import (
    TestSuiteTraceService,
    TestSuiteTraceServiceError,
    test_suite_trace_response,
)

router = APIRouter(prefix="/test-suites", tags=["test suite traces"])


def _raise_http_error(exc: TestSuiteTraceServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/{test_suite_id}/trace",
    response_model=TestSuiteTraceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trace(
    test_suite_id: str,
    payload: TestSuiteTraceCreate,
    response: Response,
    service: Annotated[TestSuiteTraceService, Depends(TestSuiteTraceService)],
) -> TestSuiteTraceResponse:
    try:
        record = service.create(test_suite_id, payload.trace)
    except TestSuiteTraceServiceError as exc:
        _raise_http_error(exc)
    response.headers["Location"] = f"/api/v1/test-suites/{test_suite_id}/trace"
    return TestSuiteTraceResponse(**test_suite_trace_response(record))


@router.get("/{test_suite_id}/trace", response_model=TestSuiteTraceResponse)
def get_trace(
    test_suite_id: str,
    service: Annotated[TestSuiteTraceService, Depends(TestSuiteTraceService)],
) -> TestSuiteTraceResponse:
    try:
        record = service.get(test_suite_id)
    except TestSuiteTraceServiceError as exc:
        _raise_http_error(exc)
    return TestSuiteTraceResponse(**test_suite_trace_response(record))


@router.delete("/{test_suite_id}/trace", status_code=status.HTTP_204_NO_CONTENT)
def delete_trace(
    test_suite_id: str,
    service: Annotated[TestSuiteTraceService, Depends(TestSuiteTraceService)],
) -> Response:
    try:
        service.delete(test_suite_id)
    except TestSuiteTraceServiceError as exc:
        _raise_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
