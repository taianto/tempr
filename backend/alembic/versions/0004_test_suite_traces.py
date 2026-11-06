"""Store one execution trace per test suite."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_test_suite_traces"
down_revision: str | None = "0003_test_suites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "test_suite_id",
            sa.String(40),
            sa.ForeignKey("test_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trace_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("test_suite_id", name="uq_traces_test_suite_id"),
    )


def downgrade() -> None:
    op.drop_table("traces")
