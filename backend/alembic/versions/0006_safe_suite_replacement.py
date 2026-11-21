"""Allow a completed suite and one generation attempt per version."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_safe_suite_replacement"
down_revision: str | None = "0005_rubric_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("test_suites", recreate="always") as batch:
        batch.drop_constraint("uq_test_suites_version_id", type_="unique")
    op.create_index(
        "uq_test_suites_completed_version_id",
        "test_suites",
        ["version_id"],
        unique=True,
        sqlite_where=sa.text("status = 'completed'"),
        postgresql_where=sa.text("status = 'completed'"),
    )
    op.create_index(
        "uq_test_suites_attempt_version_id",
        "test_suites",
        ["version_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'running', 'failed')"),
        postgresql_where=sa.text("status IN ('queued', 'running', 'failed')"),
    )


def downgrade() -> None:
    op.drop_index("uq_test_suites_attempt_version_id", table_name="test_suites")
    op.drop_index("uq_test_suites_completed_version_id", table_name="test_suites")
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM test_suites WHERE status != 'completed' AND version_id IN "
            "(SELECT version_id FROM test_suites WHERE status = 'completed')"
        )
    )
    with op.batch_alter_table("test_suites", recreate="always") as batch:
        batch.create_unique_constraint("uq_test_suites_version_id", ["version_id"])
