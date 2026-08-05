"""Add replay-safe approval execution state.

Revision ID: 20260803_0002
Revises: 20260729_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803_0002"
down_revision: str | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "approval_actions",
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("ck_approval_actions_status", "approval_actions", type_="check")
    op.drop_constraint(
        "ck_approval_decision_metadata", "approval_actions", type_="check"
    )
    op.create_check_constraint(
        "ck_approval_actions_status",
        "approval_actions",
        "status IN ('pending','approved','rejected','expired','executed')",
    )
    op.create_check_constraint(
        "ck_approval_decision_metadata",
        "approval_actions",
        "(status IN ('approved','rejected','executed') AND "
        "decided_at IS NOT NULL AND decided_by IS NOT NULL) OR "
        "(status IN ('pending','expired') AND decided_at IS NULL AND "
        "decided_by IS NULL)",
    )
    op.create_check_constraint(
        "ck_approval_execution_metadata",
        "approval_actions",
        "(status = 'executed' AND executed_at IS NOT NULL) OR "
        "(status <> 'executed' AND executed_at IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_approval_execution_metadata", "approval_actions", type_="check"
    )
    op.drop_constraint(
        "ck_approval_decision_metadata", "approval_actions", type_="check"
    )
    op.drop_constraint("ck_approval_actions_status", "approval_actions", type_="check")
    op.execute(
        "UPDATE approval_actions SET status = 'approved' WHERE status = 'executed'"
    )
    op.create_check_constraint(
        "ck_approval_actions_status",
        "approval_actions",
        "status IN ('pending','approved','rejected','expired')",
    )
    op.create_check_constraint(
        "ck_approval_decision_metadata",
        "approval_actions",
        "(status IN ('approved','rejected') AND decided_at IS NOT NULL AND "
        "decided_by IS NOT NULL) OR (status IN ('pending','expired') AND "
        "decided_at IS NULL AND decided_by IS NULL)",
    )
    op.drop_column("approval_actions", "executed_at")
