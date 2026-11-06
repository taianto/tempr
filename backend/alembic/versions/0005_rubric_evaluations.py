"""Add case IDs and rubric evaluation persistence."""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0005_rubric_evaluations"
down_revision: str | None = "0004_test_suite_traces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    suites = connection.execute(
        sa.text("SELECT id, result_json FROM test_suites WHERE result_json IS NOT NULL")
    ).mappings()
    for suite in suites:
        result = suite["result_json"]
        if isinstance(result, str):
            result = json.loads(result)
        items = result.get("items", [])
        changed = False
        for item in items:
            if "id" not in item:
                item["id"] = f"tc_{uuid4().hex}"
                changed = True
        if changed:
            suites_table = sa.table(
                "test_suites",
                sa.column("id", sa.String),
                sa.column("result_json", sa.JSON),
            )
            connection.execute(
                suites_table.update()
                .where(suites_table.c.id == suite["id"])
                .values(result_json=result)
            )

    op.create_table(
        "test_suite_evaluations",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "test_suite_id",
            sa.String(40),
            sa.ForeignKey("test_suites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trace_id",
            sa.String(40),
            sa.ForeignKey("traces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("judge_model", sa.String(255), nullable=False),
        sa.Column("rubric_version", sa.String(32), nullable=False),
        sa.Column("classification_snapshot", sa.JSON(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("test_suite_id", name="uq_evaluations_test_suite_id"),
        sa.UniqueConstraint("trace_id", name="uq_evaluations_trace_id"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="ck_test_suite_evaluations_status",
        ),
    )
    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "evaluation_id",
            sa.String(40),
            sa.ForeignKey("test_suite_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_case_id", sa.String(40), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("adherence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("consistency_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("grounding_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("adherence_explanation", sa.Text(), nullable=False),
        sa.Column("consistency_explanation", sa.Text(), nullable=False),
        sa.Column("grounding_explanation", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "evaluation_id", "test_case_id", name="uq_evaluations_case"
        ),
        sa.CheckConstraint(
            "adherence_score >= 0 AND adherence_score <= 1",
            name="ck_evaluations_adherence_score",
        ),
        sa.CheckConstraint(
            "consistency_score >= 0 AND consistency_score <= 1",
            name="ck_evaluations_consistency_score",
        ),
        sa.CheckConstraint(
            "grounding_score >= 0 AND grounding_score <= 1",
            name="ck_evaluations_grounding_score",
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("test_suite_evaluations")
