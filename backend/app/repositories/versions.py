from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.models import Agent, AgentVersion


def _id() -> str:
    return f"agv_{uuid4().hex}"


class VersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def build(agent_id: str, data: dict[str, Any]) -> AgentVersion:
        schema = data["schema"]
        prompt = schema["prompt"]
        return AgentVersion(
            id=_id(),
            agent_id=agent_id,
            version=data["version"],
            description=schema.get("description"),
            system_prompt=prompt["system"],
            developer_prompt=prompt.get("developer"),
            model_config_json=schema.get("model"),
            tools=schema.get("tools", []),
            metadata_json=schema.get("metadata", {}),
        )

    def create(self, agent_id: str, data: dict[str, Any]) -> AgentVersion | None:
        agent = self.db.scalar(
            select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )
        if agent is None:
            return None
        version = self.build(agent_id, data)
        self.db.add(version)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        return self.get(version.id)

    def list_for_agent(self, agent_id: str) -> list[AgentVersion]:
        return list(
            self.db.scalars(
                select(AgentVersion)
                .join(Agent)
                .where(AgentVersion.agent_id == agent_id, Agent.deleted_at.is_(None))
                .options(joinedload(AgentVersion.classification))
                .order_by(AgentVersion.created_at.desc(), AgentVersion.id.desc())
            ).all()
        )

    def get(self, version_id: str) -> AgentVersion | None:
        return self.db.scalar(
            select(AgentVersion)
            .join(Agent)
            .where(AgentVersion.id == version_id, Agent.deleted_at.is_(None))
            .options(
                joinedload(AgentVersion.classification), joinedload(AgentVersion.agent)
            )
        )
