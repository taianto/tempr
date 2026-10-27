from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
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
