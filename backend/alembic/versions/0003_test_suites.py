"""Add one background-generated test suite per agent version."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_test_suites"
down_revision: str | None = "0002_versioned_classifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "test_suites",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "version_id",
            sa.String(40),
            sa.ForeignKey("agent_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version_id", name="uq_test_suites_version_id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_test_suites_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("test_suites")
