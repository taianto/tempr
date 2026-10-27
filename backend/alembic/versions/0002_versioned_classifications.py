"""Persist agent schemas and classifications by immutable version."""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision: str = "0002_versioned_classifications"
down_revision: str | None = "0001_create_agents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCORES = (
    "happy_path",
    "boundary_probe",
    "missing_information",
    "ambiguous_input",
    "prompt_injection",
    "policy_bypass",
    "sensitive_data_request",
    "hallucination_probe",
)


def upgrade() -> None:
    op.create_table(
        "classifications",
        sa.Column("id", sa.String(40), primary_key=True),
        *(sa.Column(name, sa.Numeric(5, 4), nullable=False) for name in SCORES),
        sa.Column("classifier_model", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "agent_versions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "agent_id",
            sa.String(40),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("developer_prompt", sa.Text(), nullable=True),
        sa.Column("model_config", sa.JSON(), nullable=True),
        sa.Column("tools", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "classification_id",
            sa.String(40),
            sa.ForeignKey("classifications.id", ondelete="RESTRICT"),
            nullable=True,
            unique=True,
        ),
        sa.UniqueConstraint(
            "agent_id", "version", name="uq_agent_versions_agent_version"
        ),
    )
    op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])
    bind = op.get_bind()
    agents = sa.table(
        "agents",
        sa.column("id", sa.String),
        sa.column("description", sa.Text),
        sa.column("system_prompt", sa.Text),
        sa.column("developer_prompt", sa.Text),
        sa.column("model_config", sa.JSON),
        sa.column("tools", sa.JSON),
        sa.column("metadata", sa.JSON),
        sa.column("updated_at", sa.DateTime),
    )
    versions = sa.table(
        "agent_versions",
        sa.column("id", sa.String),
        sa.column("agent_id", sa.String),
        sa.column("version", sa.String),
        sa.column("description", sa.Text),
        sa.column("system_prompt", sa.Text),
        sa.column("developer_prompt", sa.Text),
        sa.column("model_config", sa.JSON),
        sa.column("tools", sa.JSON),
        sa.column("metadata", sa.JSON),
        sa.column("created_at", sa.DateTime),
    )
    rows = bind.execute(sa.select(agents)).mappings().all()
    for row in rows:
        bind.execute(
            versions.insert().values(
                id=f"agv_{uuid5(NAMESPACE_URL, row['id']).hex}",
                agent_id=row["id"],
                version="1.0",
                description=row["description"],
                system_prompt=row["system_prompt"],
                developer_prompt=row["developer_prompt"],
                model_config=row["model_config"],
                tools=row["tools"],
                metadata=row["metadata"],
                created_at=row["updated_at"],
            )
        )
    with op.batch_alter_table("agents", recreate="always") as batch:
        batch.drop_column("description")
        batch.drop_column("system_prompt")
        batch.drop_column("developer_prompt")
        batch.drop_column("model_config")
        batch.drop_column("tools")
        batch.drop_column("metadata")
    if bind.dialect.name == "sqlite":
        violations = bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                f"Foreign key violations after migration: {violations!r}"
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT count(*) FROM classifications")):
        raise RuntimeError("Cannot downgrade while persisted classifications exist")
    multiple = bind.scalar(
        sa.text(
            "SELECT count(*) FROM (SELECT agent_id FROM agent_versions GROUP BY agent_id HAVING count(*) > 1)"
        )
    )
    if multiple:
        raise RuntimeError("Cannot downgrade agents with multiple versions")
    for name, type_ in (
        ("description", sa.Text()),
        ("system_prompt", sa.Text()),
        ("developer_prompt", sa.Text()),
        ("model_config", sa.JSON()),
        ("tools", sa.JSON()),
        ("metadata", sa.JSON()),
    ):
        op.add_column("agents", sa.Column(name, type_, nullable=True))
    op.execute(
        sa.text("""
        UPDATE agents SET
          description=(SELECT description FROM agent_versions WHERE agent_id=agents.id),
          system_prompt=(SELECT system_prompt FROM agent_versions WHERE agent_id=agents.id),
          developer_prompt=(SELECT developer_prompt FROM agent_versions WHERE agent_id=agents.id),
          model_config=(SELECT model_config FROM agent_versions WHERE agent_id=agents.id),
          tools=(SELECT tools FROM agent_versions WHERE agent_id=agents.id),
          metadata=(SELECT metadata FROM agent_versions WHERE agent_id=agents.id)
    """)
    )
    op.alter_column("agents", "system_prompt", nullable=False)
    op.alter_column("agents", "tools", nullable=False)
    op.alter_column("agents", "metadata", nullable=False)
    op.drop_index("ix_agent_versions_agent_id", table_name="agent_versions")
    op.drop_table("agent_versions")
    op.drop_table("classifications")
