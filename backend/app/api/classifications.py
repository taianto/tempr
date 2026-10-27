from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.classification import ClassificationCreate, ClassificationResponse
from app.services.classification import (
    ClassificationService,
    ClassificationServiceError,
)

router = APIRouter(prefix="/classifications", tags=["classifications"])


@router.get("/{classification_id}", response_model=ClassificationResponse)
def get_classification(
    classification_id: str,
    service: Annotated[ClassificationService, Depends(ClassificationService)],
) -> ClassificationResponse:
    try:
        return ClassificationResponse.from_record(service.get(classification_id))
    except ClassificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("", response_model=ClassificationResponse)
def classify_version(
    payload: ClassificationCreate,
    service: Annotated[ClassificationService, Depends(ClassificationService)],
    refresh: Annotated[bool, Query()] = False,
) -> ClassificationResponse:
    try:
        record = service.classify(payload.version_id, refresh)
        return ClassificationResponse.from_record(record)
    except ClassificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
