from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.agent import (
    AgentCreate,
    AgentListItem,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    PromptConfig,
)
from app.schemas.classification import Classification
from app.services.agents import AgentService
from app.services.classification import (
    ClassificationService,
    ClassificationServiceError,
    get_classification_service,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        prompt=PromptConfig(
            system=agent.system_prompt, developer=agent.developer_prompt
        ),
        model=agent.model_config_json,
        tools=agent.tools,
        metadata=agent.metadata_json,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    return _response(AgentService(db).create_agent(payload.model_dump()))


@router.get("", response_model=AgentListResponse)
def list_agents(db: Annotated[Session, Depends(get_db)]) -> AgentListResponse:
    agents, total = AgentService(db).list_agents()
    items = [
        AgentListItem(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
        for agent in agents
    ]
    return AgentListResponse(items=items, total=total)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    return _response(AgentService(db).get_agent(agent_id))


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str, payload: AgentUpdate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    fields = payload.model_dump(exclude_unset=True)
    if payload.prompt is not None and "prompt" in fields:
        fields["prompt"] = payload.prompt.model_dump()
    if payload.model is not None and "model" in fields:
        fields["model"] = payload.model.model_dump()
    if payload.tools is not None and "tools" in fields:
        fields["tools"] = [tool.model_dump() for tool in payload.tools]
    return _response(AgentService(db).update_agent(agent_id, fields))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str, db: Annotated[Session, Depends(get_db)]
) -> Response:
    AgentService(db).delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/classify", response_model=Classification)
def classify_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[
        ClassificationService, Depends(get_classification_service)
    ],
) -> Classification:
    agent = AgentService(db).get_agent(agent_id)
    try:
        return Classification(**service.classify(agent))
    except ClassificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
