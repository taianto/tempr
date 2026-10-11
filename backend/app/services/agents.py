from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Agent
from app.repositories.agents import AgentRepository


class AgentService:
    def __init__(self, db: Session) -> None:
        self.repository = AgentRepository(db)

    def create_agent(self, data: dict[str, Any]) -> Agent:
        return self.repository.create(data)

    def get_agent(self, agent_id: str) -> Agent:
        agent = self.repository.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    def list_agents(self) -> tuple[list[Agent], int]:
        return self.repository.list()

    def update_agent(self, agent_id: str, fields: dict[str, Any]) -> Agent:
        if not fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field must be provided")
        agent = self.get_agent(agent_id)
        for required in ("name", "prompt", "tools", "metadata"):
            if required in fields and fields[required] is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{required} cannot be null")
        return self.repository.update(agent, fields)

    def delete_agent(self, agent_id: str) -> None:
        self.repository.delete(self.get_agent(agent_id))
