from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Agent, AgentVersion, Classification
from app.schemas.agent import (
    AgentCreate,
    AgentListItem,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AgentVersionListResponse,
    AgentVersionResponse,
    AgentVersionSummary,
    ClassificationResponse,
    PromptConfig,
    AgentSchema,
    VersionCreate,
)
from app.schemas.classification import Classification as ClassificationScores
from app.services.agents import AgentService
from app.services.classification import (
    ClassificationService,
    ClassificationServiceError,
)

router = APIRouter(prefix="/agents", tags=["agents"])
SCORE_FIELDS = tuple(ClassificationScores.model_fields)


def _classification(
    classification: Classification | None,
) -> ClassificationResponse | None:
    if classification is None:
        return None
    return ClassificationResponse(
        id=classification.id,
        scores={key: float(getattr(classification, key)) for key in SCORE_FIELDS},
        classifier_model=classification.classifier_model,
        created_at=classification.created_at,
        updated_at=classification.updated_at,
    )


def _summary(version: AgentVersion) -> AgentVersionSummary:
    return AgentVersionSummary(
        id=version.id,
        version=version.version,
        created_at=version.created_at,
        classification_id=version.classification_id,
    )


def _version_response(version: AgentVersion) -> AgentVersionResponse:
    return AgentVersionResponse(
        **_summary(version).model_dump(),
        agent_id=version.agent_id,
        schema_=AgentSchema(
            description=version.description,
            prompt=PromptConfig(
                system=version.system_prompt, developer=version.developer_prompt
            ),
            model=version.model_config_json,
            tools=version.tools,
            metadata=version.metadata_json,
        ),
        classification=_classification(version.classification),
    )


def _response(agent: Agent) -> AgentResponse:
    if not agent.versions:
        raise HTTPException(status_code=500, detail="Agent has no version")
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        latest_version=_version_response(agent.versions[0]),
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    return _response(AgentService(db).create_agent(payload.model_dump(by_alias=True)))


@router.get("", response_model=AgentListResponse)
def list_agents(db: Annotated[Session, Depends(get_db)]) -> AgentListResponse:
    agents, total = AgentService(db).list_agents()
    return AgentListResponse(
        items=[
            AgentListItem(
                id=agent.id,
                name=agent.name,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                latest_version=_summary(agent.versions[0]),
            )
            for agent in agents
        ],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> AgentResponse:
    return _response(AgentService(db).get_agent(agent_id))


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str, payload: AgentUpdate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    fields = payload.model_dump(exclude_unset=True)
    return _response(AgentService(db).update_agent(agent_id, fields))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    AgentService(db).delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{agent_id}/versions",
    response_model=AgentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    agent_id: str, payload: VersionCreate, db: Annotated[Session, Depends(get_db)]
) -> AgentVersionResponse:
    return _version_response(
        AgentService(db).create_version(agent_id, payload.model_dump(by_alias=True))
    )


@router.get("/{agent_id}/versions", response_model=AgentVersionListResponse)
def list_versions(
    agent_id: str, db: Annotated[Session, Depends(get_db)]
) -> AgentVersionListResponse:
    versions = AgentService(db).list_versions(agent_id)
    summaries = [_summary(version) for version in versions]
    return AgentVersionListResponse(items=summaries, total=len(summaries))


@router.get("/{agent_id}/versions/{version_id}", response_model=AgentVersionResponse)
def get_version(
    agent_id: str, version_id: str, db: Annotated[Session, Depends(get_db)]
) -> AgentVersionResponse:
    return _version_response(AgentService(db).get_version(agent_id, version_id))


@router.get(
    "/{agent_id}/versions/{version_id}/classification",
    response_model=ClassificationResponse,
)
def get_classification(
    agent_id: str, version_id: str, db: Annotated[Session, Depends(get_db)]
) -> ClassificationResponse:
    version = AgentService(db).get_version(agent_id, version_id)
    result = _classification(version.classification)
    if result is None:
        raise HTTPException(status_code=404, detail="Classification not found")
    return result


@router.post(
    "/{agent_id}/versions/{version_id}/classify", response_model=ClassificationResponse
)
def classify_version(
    agent_id: str,
    version_id: str,
    service: Annotated[ClassificationService, Depends(ClassificationService)],
    refresh: Annotated[bool, Query()] = False,
) -> ClassificationResponse:
    try:
        return _classification(service.classify(agent_id, version_id, refresh))  # type: ignore[return-value]
    except ClassificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
