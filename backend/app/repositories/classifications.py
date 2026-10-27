from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.db.models import Agent, AgentVersion, Classification


def _id() -> str:
    return f"cls_{uuid4().hex}"


class ClassificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(
        self,
        version_id: str,
        scores: dict[str, float],
        model: str,
        refresh: bool,
    ) -> Classification | None:
        """Save scores while serializing against soft deletion and concurrent refreshes."""
        try:
            agent_id = self.db.scalar(
                select(AgentVersion.agent_id).where(AgentVersion.id == version_id)
            )
            if agent_id is None:
                self.db.rollback()
                return None
            active = self.db.execute(
                update(Agent)
                .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
                .values(name=Agent.name, updated_at=Agent.updated_at)
                .returning(Agent.id)
            ).scalar_one_or_none()
            if active is None:
                self.db.rollback()
                return None

            version = self.db.scalar(
                select(AgentVersion)
                .where(
                    AgentVersion.id == version_id,
                    AgentVersion.agent_id == agent_id,
                )
                .options(joinedload(AgentVersion.classification))
            )
            if version is None:
                self.db.rollback()
                return None
            if version.classification is not None and not refresh:
                self.db.commit()
                return version.classification

            if version.classification is None:
                classification = Classification(
                    id=_id(), classifier_model=model, **scores
                )
                self.db.add(classification)
                self.db.flush()
                version.classification_id = classification.id
            else:
                classification = version.classification
                for key, value in scores.items():
                    setattr(classification, key, value)
                classification.classifier_model = model
                classification.updated_at = datetime.now(UTC)
            self.db.commit()
            return classification
        except Exception:
            self.db.rollback()
            raise

    def get(self, classification_id: str) -> Classification | None:
        return self.db.scalar(
            select(Classification)
            .join(AgentVersion, AgentVersion.classification_id == Classification.id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                Classification.id == classification_id,
                Agent.deleted_at.is_(None),
            )
        )
