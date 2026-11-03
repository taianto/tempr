from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Agent,
    AgentVersion,
    TestSuite,
    TestSuiteTrace,
)


def _id() -> str:
    return f"trc_{uuid4().hex}"


class TestSuiteTraceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _active_suite_agent_id(self, test_suite_id: str) -> str | None:
        return self.db.scalar(
            select(Agent.id)
            .join(AgentVersion, AgentVersion.agent_id == Agent.id)
            .join(TestSuite, TestSuite.version_id == AgentVersion.id)
            .where(TestSuite.id == test_suite_id, Agent.deleted_at.is_(None))
        )

    def _lock_agent(self, agent_id: str) -> bool:
        # Match suite replacement's per-agent serialization for trace writes.
        locked = self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .values(name=Agent.name, updated_at=Agent.updated_at)
            .returning(Agent.id)
        ).scalar_one_or_none()
        return locked is not None

    def get(self, test_suite_id: str) -> TestSuiteTrace | None:
        return self.db.scalar(
            select(TestSuiteTrace)
            .join(TestSuite, TestSuite.id == TestSuiteTrace.test_suite_id)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                TestSuiteTrace.test_suite_id == test_suite_id,
                Agent.deleted_at.is_(None),
            )
        )

    def create(
        self, test_suite_id: str, trace_json: Any
    ) -> tuple[TestSuiteTrace | None, str | None]:
        agent_id = self._active_suite_agent_id(test_suite_id)
        if agent_id is None:
            return None, None
        if not self._lock_agent(agent_id):
            self.db.rollback()
            return None, None

        suite = self.db.scalar(
            select(TestSuite)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                TestSuite.id == test_suite_id,
                Agent.deleted_at.is_(None),
            )
        )
        if suite is None:
            self.db.rollback()
            return None, None
        if suite.status != "completed":
            self.db.rollback()
            return None, "Test suite generation must complete before adding a trace"
        if (
            self.db.scalar(
                select(TestSuiteTrace.id).where(
                    TestSuiteTrace.test_suite_id == test_suite_id
                )
            )
            is not None
        ):
            self.db.rollback()
            return None, "A trace already exists for this test suite"

        record = TestSuiteTrace(
            id=_id(), test_suite_id=test_suite_id, trace_json=trace_json
        )
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return None, "A trace already exists for this test suite"
        self.db.refresh(record)
        return record, None

    def delete(self, test_suite_id: str) -> bool:
        agent_id = self._active_suite_agent_id(test_suite_id)
        if agent_id is None or not self._lock_agent(agent_id):
            self.db.rollback()
            return False
        record = self.db.scalar(
            select(TestSuiteTrace)
            .join(TestSuite, TestSuite.id == TestSuiteTrace.test_suite_id)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                TestSuiteTrace.test_suite_id == test_suite_id,
                Agent.deleted_at.is_(None),
            )
        )
        if record is None:
            self.db.rollback()
            return False
        self.db.delete(record)
        self.db.commit()
        return True
