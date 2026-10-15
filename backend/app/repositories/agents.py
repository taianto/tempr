from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.models import Agent, AgentVersion


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _version_values(schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "description": schema.get("description"),
            "system_prompt": schema["prompt"]["system"],
            "developer_prompt": schema["prompt"].get("developer"),
            "model_config_json": schema.get("model"),
            "tools": schema.get("tools", []),
            "metadata_json": schema.get("metadata", {}),
        }

    def create(self, data: dict[str, Any]) -> Agent:
        initial = data["initial_version"]
        agent = Agent(id=_id("agt"), name=data["name"])
        version = AgentVersion(
            id=_id("agv"),
            version=initial["version"],
            **self._version_values(initial["schema"]),
        )
        agent.versions.append(version)
        self.db.add(agent)
        self.db.commit()
        return self.get(agent.id)  # type: ignore[return-value]

    def get(self, agent_id: str) -> Agent | None:
        stmt = (
            select(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .options(joinedload(Agent.versions).joinedload(AgentVersion.classification))
        )
        agent = self.db.execute(stmt).unique().scalar_one_or_none()
        if agent is not None:
            agent.versions.sort(key=lambda item: (item.created_at, item.id), reverse=True)
        return agent

    def list(self) -> tuple[list[Agent], int]:
        stmt = (
            select(Agent)
            .where(Agent.deleted_at.is_(None))
            .options(joinedload(Agent.versions).joinedload(AgentVersion.classification))
            .order_by(Agent.created_at.desc(), Agent.id)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        for agent in items:
            agent.versions.sort(key=lambda item: (item.created_at, item.id), reverse=True)
        return items, len(items)

    def versions(self, agent_id: str) -> list[AgentVersion]:
        return list(self.db.scalars(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .options(joinedload(AgentVersion.classification))
            .order_by(AgentVersion.created_at.desc(), AgentVersion.id.desc())
        ).all())

    def get_version(self, agent_id: str, version_id: str) -> AgentVersion | None:
        return self.db.scalar(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id, AgentVersion.id == version_id)
            .options(joinedload(AgentVersion.classification))
        )

    def create_version(self, agent: Agent, data: dict[str, Any]) -> AgentVersion:
        version = AgentVersion(
            id=_id("agv"), agent_id=agent.id, version=data["version"],
            **self._version_values(data["schema"]),
        )
        self.db.add(version)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        return self.get_version(agent.id, version.id)  # type: ignore[return-value]

    def update_name(self, agent: Agent, name: str) -> Agent:
        agent.name = name
        agent.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return self.get(agent.id)  # type: ignore[return-value]

    def soft_delete(self, agent: Agent) -> None:
        agent.deleted_at = datetime.now(timezone.utc)
        agent.updated_at = agent.deleted_at
        self.db.commit()
