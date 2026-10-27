from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.version import (
    AgentVersionListResponse,
    AgentVersionResponse,
    AgentVersionSummary,
    VersionCreateRequest,
)
from app.services.versions import VersionService

router = APIRouter(prefix="/versions", tags=["versions"])


@router.post(
    "", response_model=AgentVersionResponse, status_code=status.HTTP_201_CREATED
)
def create_version(
    payload: VersionCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> AgentVersionResponse:
    data = payload.model_dump(by_alias=True, exclude={"agent_id"})
    version = VersionService(db).create(payload.agent_id, data)
    return AgentVersionResponse.from_record(version)


@router.get("", response_model=AgentVersionListResponse)
def list_versions(
    db: Annotated[Session, Depends(get_db)], agent_id: Annotated[str, Query()]
) -> AgentVersionListResponse:
    versions = VersionService(db).list_for_agent(agent_id)
    items = [AgentVersionSummary.from_record(version) for version in versions]
    return AgentVersionListResponse(items=items, total=len(items))


@router.get("/{version_id}", response_model=AgentVersionResponse)
def get_version(
    version_id: str, db: Annotated[Session, Depends(get_db)]
) -> AgentVersionResponse:
    return AgentVersionResponse.from_record(VersionService(db).get(version_id))
