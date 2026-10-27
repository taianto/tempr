from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.agent import (
    AgentCreate,
    AgentListItem,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from app.services.agents import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    return AgentResponse.from_record(
        AgentService(db).create_agent(payload.model_dump(by_alias=True))
    )


@router.get("", response_model=AgentListResponse)
def list_agents(db: Annotated[Session, Depends(get_db)]) -> AgentListResponse:
    agents, total = AgentService(db).list_agents()
    return AgentListResponse(
        items=[AgentListItem.from_record(agent) for agent in agents],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> AgentResponse:
    return AgentResponse.from_record(AgentService(db).get_agent(agent_id))


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str, payload: AgentUpdate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    fields = payload.model_dump(exclude_unset=True)
    return AgentResponse.from_record(AgentService(db).update_agent(agent_id, fields))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    AgentService(db).delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
