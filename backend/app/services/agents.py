from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Agent
from app.repositories.agents import AgentRepository
from app.repositories.versions import VersionRepository


class AgentService:
    def __init__(self, db: Session) -> None:
        self.repository = AgentRepository(db)
        self.versions = VersionRepository(db)

    def create_agent(self, data: dict[str, Any]) -> Agent:
        try:
            agent = self.repository.build(data["name"])
            agent.versions.append(
                self.versions.build(agent.id, data["initial_version"])
            )
            self.repository.add(agent)
            self.repository.db.commit()
            return self.repository.get(agent.id)  # type: ignore[return-value]
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

    def delete_agent(self, agent_id: str) -> None:
        self.repository.soft_delete(self.get_agent(agent_id))
