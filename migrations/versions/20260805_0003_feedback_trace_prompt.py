"""Link feedback to traces and immutable prompt artifacts.

Revision ID: 20260805_0003
Revises: 20260803_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0003"
down_revision: str | None = "20260803_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_feedback", sa.Column("trace_id", sa.String(128), nullable=True)
    )
    op.add_column(
        "agent_feedback", sa.Column("prompt_sha256", sa.String(64), nullable=True)
    )
    op.execute(
        "UPDATE agent_feedback SET trace_id = 'legacy:' || request_id, "
        "prompt_sha256 = repeat('0', 64)"
    )
    op.alter_column("agent_feedback", "trace_id", nullable=False)
    op.alter_column("agent_feedback", "prompt_sha256", nullable=False)
    op.create_index(
        "ix_agent_feedback_trace_id", "agent_feedback", ["trace_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_agent_feedback_trace_id", table_name="agent_feedback")
    op.drop_column("agent_feedback", "prompt_sha256")
    op.drop_column("agent_feedback", "trace_id")
