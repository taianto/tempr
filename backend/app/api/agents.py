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
from app.services.versions import VersionService

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
    summaries = VersionService(db).evaluation_summaries(
        [agent.versions[0].id for agent in agents if agent.versions]
    )
    return AgentListResponse(
        items=[
            AgentListItem.from_record(
                agent, summaries.get(agent.versions[0].id) if agent.versions else None
            )
            for agent in agents
        ],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> AgentResponse:
    agent = AgentService(db).get_agent(agent_id)
    summaries = VersionService(db).evaluation_summaries([agent.versions[0].id])
    return AgentResponse.from_record(agent, summaries.get(agent.versions[0].id))


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str, payload: AgentUpdate, db: Annotated[Session, Depends(get_db)]
) -> AgentResponse:
    fields = payload.model_dump(exclude_unset=True)
    agent = AgentService(db).update_agent(agent_id, fields)
    summaries = VersionService(db).evaluation_summaries([agent.versions[0].id])
    return AgentResponse.from_record(agent, summaries.get(agent.versions[0].id))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    AgentService(db).delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
