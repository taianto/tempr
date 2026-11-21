from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Agent, AgentVersion, TestSuite, utc_now


def _id() -> str:
    return f"ts_{uuid4().hex}"


class TestSuiteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_version(self, version_id: str) -> TestSuite | None:
        return self.db.scalar(
            select(TestSuite)
            .where(TestSuite.version_id == version_id)
            .order_by(
                TestSuite.status != "completed",
                TestSuite.created_at.desc(),
                TestSuite.id.desc(),
            )
        )

    def get_completed_for_version(self, version_id: str) -> TestSuite | None:
        return self.db.scalar(
            select(TestSuite).where(
                TestSuite.version_id == version_id, TestSuite.status == "completed"
            )
        )

    def get_attempt_for_version(self, version_id: str) -> TestSuite | None:
        return self.db.scalar(
            select(TestSuite)
            .where(TestSuite.version_id == version_id, TestSuite.status != "completed")
            .order_by(TestSuite.created_at.desc(), TestSuite.id.desc())
        )

    def fail_stale_attempt(self, version_id: str, timeout_seconds: float) -> None:
        cutoff = utc_now() - timedelta(seconds=timeout_seconds)
        self.db.execute(
            update(TestSuite)
            .where(
                TestSuite.version_id == version_id,
                TestSuite.status.in_(("queued", "running")),
                TestSuite.updated_at < cutoff,
            )
            .values(
                status="failed",
                error="Generation expired before it completed. Retry generation.",
                updated_at=utc_now(),
            )
        )
        self.db.commit()

    def get(self, version_id: str) -> TestSuite | None:
        return self.get_for_version(version_id)

    def enqueue(self, version_id: str, request: dict[str, Any]) -> TestSuite | None:
        agent_id = self.db.scalar(
            select(AgentVersion.agent_id).where(AgentVersion.id == version_id)
        )
        if agent_id is None:
            return None

        # Serialize replacement against concurrent requests and soft deletion.
        active_agent = self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .values(name=Agent.name, updated_at=Agent.updated_at)
            .returning(Agent.id)
        ).scalar_one_or_none()
        if active_agent is None:
            self.db.rollback()
            return None

        attempt = self.get_attempt_for_version(version_id)
        if attempt is not None:
            if attempt.status in ("queued", "running"):
                self.db.rollback()
                raise ValueError("A test suite generation is already in progress")
            self.db.delete(attempt)
            self.db.flush()

        record = TestSuite(
            id=_id(), version_id=version_id, status="queued", request_json=request
        )
        self.db.add(record)
        try:
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError(
                "A generation request conflicted with another request; retry it"
            ) from exc

    def claim(self, record_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        row = self.db.execute(
            select(TestSuite, AgentVersion)
            .join(AgentVersion, TestSuite.version_id == AgentVersion.id)
            .join(Agent, AgentVersion.agent_id == Agent.id)
            .where(
                TestSuite.id == record_id,
                TestSuite.status == "queued",
                Agent.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            return None
        record, version = row
        claimed = self.db.execute(
            update(TestSuite)
            .where(TestSuite.id == record_id, TestSuite.status == "queued")
            .values(status="running", error=None, updated_at=utc_now())
        )
        self.db.commit()
        if claimed.rowcount != 1:
            return None
        context = {
            "description": version.description,
            "system_prompt": version.system_prompt,
            "developer_prompt": version.developer_prompt,
            "model": version.model_config_json,
            "tools": version.tools,
            "metadata": version.metadata_json,
        }
        return dict(record.request_json), context

    def fail_queued_for_deleted_agent(self, record_id: str) -> None:
        self.db.execute(
            update(TestSuite)
            .where(
                TestSuite.id == record_id,
                TestSuite.status == "queued",
                TestSuite.version_id.in_(
                    select(AgentVersion.id)
                    .join(Agent, AgentVersion.agent_id == Agent.id)
                    .where(Agent.deleted_at.is_not(None))
                ),
            )
            .values(
                status="failed",
                error="Agent was deleted before generation started",
                updated_at=utc_now(),
            )
        )
        self.db.commit()

    def complete(self, record_id: str, result: dict[str, Any]) -> bool:
        attempt = self.db.scalar(
            select(TestSuite).where(
                TestSuite.id == record_id, TestSuite.status == "running"
            )
        )
        if attempt is None:
            self.db.rollback()
            return False
        agent_id = self.db.scalar(
            select(AgentVersion.agent_id).where(AgentVersion.id == attempt.version_id)
        )
        if agent_id is None:
            self.db.rollback()
            return False
        locked = self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .values(name=Agent.name, updated_at=Agent.updated_at)
            .returning(Agent.id)
        ).scalar_one_or_none()
        if locked is None:
            self.db.rollback()
            return False
        old_suite = self.get_completed_for_version(attempt.version_id)
        if old_suite is not None:
            self.db.delete(old_suite)
            self.db.flush()
        attempt.status = "completed"
        attempt.result_json = result
        attempt.error = None
        attempt.updated_at = utc_now()
        try:
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def fail(self, record_id: str, detail: str) -> None:
        self.db.execute(
            update(TestSuite)
            .where(TestSuite.id == record_id, TestSuite.status == "running")
            .values(status="failed", error=detail, updated_at=utc_now())
        )
        self.db.commit()
