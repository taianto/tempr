from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AgentVersion
from app.repositories.agents import AgentRepository
from app.repositories.versions import VersionRepository


class VersionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.agents = AgentRepository(db)
        self.repository = VersionRepository(db)

    def create(self, agent_id: str, data: dict[str, Any]) -> AgentVersion:
        if self.agents.get(agent_id) is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        try:
            version = self.repository.create(agent_id, data)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=409, detail="Version label already exists for this agent"
            ) from exc
        if version is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return version

    def list_for_agent(self, agent_id: str) -> list[AgentVersion]:
        if self.agents.get(agent_id) is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return self.repository.list_for_agent(agent_id)

    def get(self, version_id: str) -> AgentVersion:
        version = self.repository.get(version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="Agent version not found")
        return version
