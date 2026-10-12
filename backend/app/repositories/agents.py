from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agent


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict[str, Any]) -> Agent:
        prompt = data["prompt"]
        agent = Agent(
            id=f"agt_{uuid4().hex}",
            name=data["name"],
            description=data.get("description"),
            system_prompt=prompt["system"],
            developer_prompt=prompt.get("developer"),
            model_config_json=data.get("model"),
            tools=data.get("tools", []),
            metadata_json=data.get("metadata", {}),
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get(self, agent_id: str) -> Agent | None:
        return self.db.scalar(
            select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None))
        )

    def list(self) -> tuple[list[Agent], int]:
        query = (
            select(Agent)
            .where(Agent.deleted_at.is_(None))
            .order_by(Agent.created_at.desc(), Agent.id)
        )
        items = list(self.db.scalars(query).all())
        return items, len(items)

    def update(self, agent: Agent, fields: dict[str, Any]) -> Agent:
        if "name" in fields:
            agent.name = fields["name"]
        if "description" in fields:
            agent.description = fields["description"]
        if "prompt" in fields:
            agent.system_prompt = fields["prompt"]["system"]
            agent.developer_prompt = fields["prompt"].get("developer")
        if "model" in fields:
            agent.model_config_json = fields["model"]
        if "tools" in fields:
            agent.tools = fields["tools"]
        if "metadata" in fields:
            agent.metadata_json = fields["metadata"]
        agent.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def delete(self, agent: Agent) -> None:
        agent.deleted_at = datetime.now(timezone.utc)
        agent.updated_at = datetime.now(timezone.utc)
        self.db.commit()
