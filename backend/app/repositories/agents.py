from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Agent, AgentVersion


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, name: str) -> Agent:
        return Agent(id=_id("agt"), name=name)

    def add(self, agent: Agent) -> None:
        self.db.add(agent)
        self.db.flush()

    def get(self, agent_id: str) -> Agent | None:
        stmt = (
            select(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .options(joinedload(Agent.versions).joinedload(AgentVersion.classification))
        )
        agent = self.db.execute(stmt).unique().scalar_one_or_none()
        if agent is not None:
            agent.versions.sort(
                key=lambda item: (item.created_at, item.id), reverse=True
            )
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
            agent.versions.sort(
                key=lambda item: (item.created_at, item.id), reverse=True
            )
        return items, len(items)

    def update_name(self, agent: Agent, name: str) -> Agent:
        agent.name = name
        agent.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.get(agent.id)  # type: ignore[return-value]

    def soft_delete(self, agent: Agent) -> None:
        agent.deleted_at = datetime.now(UTC)
        agent.updated_at = agent.deleted_at
        self.db.commit()
