from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Agent,
    AgentVersion,
    Evaluation,
    TestSuite,
    TestSuiteEvaluation,
)


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

    def evaluation_summaries(self, version_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load compact evaluation summaries for a batch of versions."""
        if not version_ids:
            return {}

        sources = self.db.execute(
            select(
                AgentVersion.id,
                TestSuite.result_json,
                TestSuiteEvaluation.id,
                TestSuiteEvaluation.status,
            )
            .outerjoin(TestSuite, TestSuite.version_id == AgentVersion.id)
            .outerjoin(
                TestSuiteEvaluation, TestSuiteEvaluation.test_suite_id == TestSuite.id
            )
            .where(AgentVersion.id.in_(version_ids))
        ).all()
        evaluation_sources = {
            version_id: (suite_result, evaluation_id, status)
            for version_id, suite_result, evaluation_id, status in sources
            if evaluation_id is not None
        }
        evaluation_ids = [source[1] for source in evaluation_sources.values()]
        if not evaluation_ids:
            return {}

        aggregates = self.db.execute(
            select(
                Evaluation.evaluation_id,
                func.count(Evaluation.id),
                func.avg(Evaluation.adherence_score),
                func.avg(Evaluation.consistency_score),
                func.avg(Evaluation.grounding_score),
            )
            .where(Evaluation.evaluation_id.in_(evaluation_ids))
            .group_by(Evaluation.evaluation_id)
        ).all()
        aggregate_by_id = {row[0]: row[1:] for row in aggregates}

        summaries: dict[str, dict[str, Any]] = {}
        for version_id, (
            suite_result,
            evaluation_id,
            status,
        ) in evaluation_sources.items():
            result_count, adherence, consistency, grounding = aggregate_by_id.get(
                evaluation_id, (0, None, None, None)
            )
            suite_items = (suite_result or {}).get("items", [])
            overall_score = None
            if (
                status == "completed"
                and suite_items
                and result_count == len(suite_items)
                and adherence is not None
                and consistency is not None
                and grounding is not None
            ):
                overall_score = float((adherence + consistency + grounding) / 3)
            summaries[version_id] = {
                "status": status,
                "overall_score": overall_score,
            }
        return summaries

    def get(self, version_id: str) -> AgentVersion | None:
        return self.db.scalar(
            select(AgentVersion)
            .join(Agent)
            .where(AgentVersion.id == version_id, Agent.deleted_at.is_(None))
            .options(
                joinedload(AgentVersion.classification), joinedload(AgentVersion.agent)
            )
        )
