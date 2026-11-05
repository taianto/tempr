from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC timestamps and restore timezone information on SQLite reads."""

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    def process_result_value(
        self, value: datetime | None, dialect: Any
    ) -> datetime | None:
        if value is None:
            return None
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    versions: Mapped[list["AgentVersion"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    developer_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        "model_config", JSON, nullable=True
    )
    tools: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    classification_id: Mapped[str | None] = mapped_column(
        ForeignKey("classifications.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    agent: Mapped[Agent] = relationship(back_populates="versions")
    classification: Mapped["Classification | None"] = relationship(
        foreign_keys=[classification_id], lazy="joined"
    )
    test_suite: Mapped["TestSuite | None"] = relationship(
        back_populates="version", cascade="all, delete-orphan", uselist=False
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    happy_path: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    boundary_probe: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    missing_information: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    ambiguous_input: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    prompt_injection: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    policy_bypass: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    sensitive_data_request: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    hallucination_probe: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    classifier_model: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )


class TestSuite(Base):
    """Generation job and generated suite for one agent version."""

    __tablename__ = "test_suites"
    __table_args__ = (
        UniqueConstraint("version_id", name="uq_test_suites_version_id"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_test_suites_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("agent_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )
    version: Mapped[AgentVersion] = relationship(back_populates="test_suite")
    trace: Mapped["TestSuiteTrace | None"] = relationship(
        back_populates="test_suite", cascade="all, delete-orphan", uselist=False
    )
    evaluation: Mapped["TestSuiteEvaluation | None"] = relationship(
        back_populates="test_suite", cascade="all, delete-orphan", uselist=False
    )


class TestSuiteTrace(Base):
    __tablename__ = "traces"
    __table_args__ = (
        UniqueConstraint("test_suite_id", name="uq_traces_test_suite_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    test_suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    trace_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    test_suite: Mapped[TestSuite] = relationship(back_populates="trace")
    evaluation: Mapped["TestSuiteEvaluation | None"] = relationship(
        back_populates="trace", cascade="all, delete-orphan", uselist=False
    )


class TestSuiteEvaluation(Base):
    __tablename__ = "test_suite_evaluations"
    __table_args__ = (
        UniqueConstraint("test_suite_id", name="uq_evaluations_test_suite_id"),
        UniqueConstraint("trace_id", name="uq_evaluations_trace_id"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_test_suite_evaluations_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    test_suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    trace_id: Mapped[str] = mapped_column(
        ForeignKey("traces.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    judge_model: Mapped[str] = mapped_column(String(255), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now
    )
    test_suite: Mapped[TestSuite] = relationship(back_populates="evaluation")
    trace: Mapped[TestSuiteTrace] = relationship(back_populates="evaluation")
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "test_case_id", name="uq_evaluations_case"),
        CheckConstraint(
            "adherence_score >= 0 AND adherence_score <= 1",
            name="ck_evaluations_adherence_score",
        ),
        CheckConstraint(
            "consistency_score >= 0 AND consistency_score <= 1",
            name="ck_evaluations_consistency_score",
        ),
        CheckConstraint(
            "grounding_score >= 0 AND grounding_score <= 1",
            name="ck_evaluations_grounding_score",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(
        ForeignKey("test_suite_evaluations.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    adherence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    consistency_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    grounding_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    adherence_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    consistency_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation: Mapped[TestSuiteEvaluation] = relationship(back_populates="evaluations")
