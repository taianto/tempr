from typing import Any
from uuid import uuid4

from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Agent,
    AgentVersion,
    Evaluation,
    TestSuite,
    TestSuiteEvaluation,
    TestSuiteTrace,
    utc_now,
)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class EvaluationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _active_agent_id(self, test_suite_id: str) -> str | None:
        return self.db.scalar(
            select(Agent.id)
            .join(AgentVersion, AgentVersion.agent_id == Agent.id)
            .join(TestSuite, TestSuite.version_id == AgentVersion.id)
            .where(TestSuite.id == test_suite_id, Agent.deleted_at.is_(None))
        )

    def get(self, test_suite_id: str) -> TestSuiteEvaluation | None:
        record = self.db.scalar(
            select(TestSuiteEvaluation)
            .join(TestSuite, TestSuite.id == TestSuiteEvaluation.test_suite_id)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                TestSuiteEvaluation.test_suite_id == test_suite_id,
                Agent.deleted_at.is_(None),
            )
        )
        if record is not None:
            record.evaluations.sort(key=lambda result: result.test_case_id)
        return record

    def enqueue(
        self,
        test_suite_id: str,
        judge_model: str,
        rubric_version: str,
        refresh: bool,
        configured: bool,
    ) -> tuple[TestSuiteEvaluation | None, str | None, bool]:
        agent_id = self._active_agent_id(test_suite_id)
        if agent_id is None:
            return None, "Test suite not found", False

        locked = self.db.scalar(
            update(Agent)
            .where(Agent.id == agent_id, Agent.deleted_at.is_(None))
            .values(name=Agent.name, updated_at=Agent.updated_at)
            .returning(Agent.id)
        )
        if locked is None:
            self.db.rollback()
            return None, "Test suite not found", False

        source = self.db.execute(
            select(TestSuite, TestSuiteTrace, AgentVersion)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .outerjoin(TestSuiteTrace, TestSuiteTrace.test_suite_id == TestSuite.id)
            .where(TestSuite.id == test_suite_id, Agent.deleted_at.is_(None))
        ).one_or_none()
        if source is None:
            self.db.rollback()
            return None, "Test suite not found", False
        suite, trace, version = source
        if suite.status != "completed" or not suite.result_json:
            self.db.rollback()
            return None, "Test suite generation must complete before evaluation", False
        if trace is None:
            self.db.rollback()
            return None, "A trace is required before evaluation", False

        existing = self.db.scalar(
            select(TestSuiteEvaluation).where(
                TestSuiteEvaluation.test_suite_id == test_suite_id
            )
        )
        if existing is not None and not refresh:
            self.db.commit()
            return existing, None, False

        items = suite.result_json.get("items", [])
        trace_data = trace.trace_json
        error = self._validate_cases(items, trace_data)
        if error is not None:
            self.db.rollback()
            return None, error, False

        if not configured:
            self.db.rollback()
            return (
                None,
                "Evaluation is not configured: please set up LLM API key",
                False,
            )

        if existing is not None:
            self.db.delete(existing)
            self.db.flush()

        request = suite.request_json
        classification_snapshot = {
            "id": request.get("classification_id"),
            "updated_at": request.get("classification_updated_at"),
            "model": request.get("classification_model"),
            "scores": request.get("classification_scores", {}),
        }
        executions = {
            execution["test_case_id"]: execution["execution"]
            for execution in trace_data["executions"]
        }
        cases = [
            {
                **item,
                "execution": executions[item["id"]],
            }
            for item in items
        ]
        context = {
            "agent": {
                "description": version.description,
                "system_prompt": version.system_prompt,
                "developer_prompt": version.developer_prompt,
                "model": version.model_config_json,
                "tools": version.tools,
                "metadata": version.metadata_json,
            },
            "cases": cases,
        }
        record = TestSuiteEvaluation(
            id=_id("evj"),
            test_suite_id=test_suite_id,
            trace_id=trace.id,
            status="queued",
            judge_model=judge_model,
            rubric_version=rubric_version,
            classification_snapshot=classification_snapshot,
            request_json=context,
        )
        self.db.add(record)
        try:
            self.db.commit()
            self.db.refresh(record)
            return record, None, True
        except IntegrityError:
            self.db.rollback()
            record = self.db.scalar(
                select(TestSuiteEvaluation).where(
                    TestSuiteEvaluation.test_suite_id == test_suite_id
                )
            )
            if record is not None:
                return record, None, False
            return None, "An evaluation request conflicted with another request", False

    @staticmethod
    def _validate_cases(items: list[dict[str, Any]], trace: Any) -> str | None:
        if not isinstance(trace, dict) or not isinstance(trace.get("executions"), list):
            return "Trace must contain an executions list"
        if (
            not isinstance(items, list)
            or not items
            or not all(isinstance(item, dict) for item in items)
        ):
            return "Test suite cases do not have valid IDs"
        case_ids = [item.get("id") for item in items]
        if any(
            not isinstance(case_id, str) or not case_id for case_id in case_ids
        ) or len(set(case_ids)) != len(case_ids):
            return "Test suite cases do not have valid IDs"
        expected = set(case_ids)
        supplied: dict[str, Any] = {}
        for entry in trace["executions"]:
            if not isinstance(entry, dict):
                return "Each execution must be an object"
            case_id = entry.get("test_case_id")
            execution = entry.get("execution")
            if (
                not isinstance(case_id, str)
                or not isinstance(execution, dict)
                or not execution
            ):
                return "Each execution needs a test_case_id and a nonempty execution object"
            if case_id in supplied:
                return "Each test case can have only one execution"
            if case_id not in expected:
                return "Trace contains an unknown test_case_id"
            supplied[case_id] = execution
        if supplied.keys() != expected:
            return "Trace must contain exactly one execution for every test case"
        return None

    def claim(self, evaluation_id: str) -> dict[str, Any] | None:
        request = self.db.scalar(
            select(TestSuiteEvaluation.request_json)
            .join(TestSuite, TestSuite.id == TestSuiteEvaluation.test_suite_id)
            .join(AgentVersion, AgentVersion.id == TestSuite.version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .where(
                TestSuiteEvaluation.id == evaluation_id,
                TestSuiteEvaluation.status == "queued",
                Agent.deleted_at.is_(None),
            )
        )
        if request is None:
            self.db.rollback()
            return None
        claimed = self.db.execute(
            update(TestSuiteEvaluation)
            .where(
                TestSuiteEvaluation.id == evaluation_id,
                TestSuiteEvaluation.status == "queued",
            )
            .values(status="running", error=None, updated_at=utc_now())
            .returning(TestSuiteEvaluation.id)
        )
        claimed_id = claimed.scalar_one_or_none()
        self.db.commit()
        if claimed_id is None:
            return None
        return dict(request)

    def complete(self, evaluation_id: str, results: list[dict[str, Any]]) -> bool:
        active_agent = exists(
            select(Agent.id)
            .join(AgentVersion, AgentVersion.agent_id == Agent.id)
            .join(TestSuite, TestSuite.version_id == AgentVersion.id)
            .where(
                TestSuite.id == TestSuiteEvaluation.test_suite_id,
                Agent.deleted_at.is_(None),
            )
        )
        record = self.db.scalar(
            select(TestSuiteEvaluation).where(
                TestSuiteEvaluation.id == evaluation_id,
                TestSuiteEvaluation.status == "running",
                active_agent,
            )
        )
        if record is None:
            self.db.rollback()
            return False
        self.db.add_all(
            [
                Evaluation(id=_id("eva"), evaluation_id=evaluation_id, **result)
                for result in results
            ]
        )
        record.status = "completed"
        record.updated_at = utc_now()
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def fail(self, evaluation_id: str, detail: str) -> None:
        self.db.execute(
            update(TestSuiteEvaluation)
            .where(
                TestSuiteEvaluation.id == evaluation_id,
                TestSuiteEvaluation.status == "running",
            )
            .values(status="failed", error=detail, updated_at=utc_now())
        )
        self.db.commit()
