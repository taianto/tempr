from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Agent, AgentVersion
from app.repositories.agents import AgentRepository


class AgentService:
    def __init__(self, db: Session) -> None:
        self.repository = AgentRepository(db)

    def create_agent(self, data: dict[str, Any]) -> Agent:
        try:
            return self.repository.create(data)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=409, detail="Agent version already exists"
            ) from exc

    def get_agent(self, agent_id: str) -> Agent:
        agent = self.repository.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    def list_agents(self) -> tuple[list[Agent], int]:
        return self.repository.list()

    def update_agent(self, agent_id: str, fields: dict[str, Any]) -> Agent:
        if set(fields) != {"name"}:
            raise HTTPException(
                status_code=400, detail="Only the agent name can be updated"
            )
        return self.repository.update_name(self.get_agent(agent_id), fields["name"])

    def create_version(self, agent_id: str, data: dict[str, Any]) -> AgentVersion:
        agent = self.get_agent(agent_id)
        try:
            return self.repository.create_version(agent, data)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=409, detail="Version label already exists for this agent"
            ) from exc

    def list_versions(self, agent_id: str) -> list[AgentVersion]:
        self.get_agent(agent_id)
        return self.repository.versions(agent_id)

    def get_version(self, agent_id: str, version_id: str) -> AgentVersion:
        self.get_agent(agent_id)
        version = self.repository.get_version(agent_id, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Agent version not found")
        return version

    def delete_agent(self, agent_id: str) -> None:
        self.repository.soft_delete(self.get_agent(agent_id))
