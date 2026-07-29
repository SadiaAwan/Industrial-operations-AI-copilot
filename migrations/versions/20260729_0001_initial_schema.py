"""Create the initial operational data schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260729_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "machines",
        sa.Column("machine_id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("machine_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "machine_id ~ '^[A-Z][A-Z0-9]*-[0-9]{3,6}$'",
            name="ck_machines_machine_id_format",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive','maintenance','decommissioned')",
            name="ck_machines_status",
        ),
    )
    op.create_index("ix_machines_type_status", "machines", ["machine_type", "status"])

    op.create_table(
        "sensor_readings",
        sa.Column("reading_id", sa.String(100), primary_key=True),
        sa.Column(
            "machine_id",
            sa.String(32),
            sa.ForeignKey("machines.machine_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sensor_type", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("value = value", name="ck_sensor_value_not_nan"),
        sa.UniqueConstraint(
            "machine_id", "sensor_type", "recorded_at", name="uq_sensor_measurement"
        ),
    )
    op.create_index(
        "ix_sensor_readings_machine_type_time",
        "sensor_readings",
        ["machine_id", "sensor_type", "recorded_at"],
    )

    for table_name, id_name, id_length, columns in (
        (
            "maintenance_records",
            "record_id",
            64,
            [
                sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("maintenance_type", sa.String(100), nullable=False),
                sa.Column("description", sa.Text(), nullable=False),
                sa.Column("technician_id", sa.String(64)),
            ],
        ),
        (
            "incidents",
            "incident_id",
            64,
            [
                sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
                sa.Column("severity", sa.String(16), nullable=False),
                sa.Column("summary", sa.Text(), nullable=False),
                sa.Column("root_cause", sa.Text()),
                sa.Column("resolution", sa.Text()),
            ],
        ),
    ):
        constraints: list[sa.SchemaItem] = []
        if table_name == "incidents":
            constraints.append(
                sa.CheckConstraint(
                    "severity IN ('normal','low','medium','high','critical')",
                    name="ck_incidents_severity",
                )
            )
        op.create_table(
            table_name,
            sa.Column(id_name, sa.String(id_length), primary_key=True),
            sa.Column(
                "machine_id",
                sa.String(32),
                sa.ForeignKey("machines.machine_id", ondelete="RESTRICT"),
                nullable=False,
            ),
            *columns,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            *constraints,
        )
    op.create_index(
        "ix_maintenance_machine_performed",
        "maintenance_records",
        ["machine_id", "performed_at"],
    )
    op.create_index(
        "ix_incidents_machine_occurred", "incidents", ["machine_id", "occurred_at"]
    )

    op.create_table(
        "work_orders",
        sa.Column("work_order_id", sa.String(64), primary_key=True),
        sa.Column(
            "machine_id",
            sa.String(32),
            sa.ForeignKey("machines.machine_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("proposed_checks", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "priority IN ('normal','low','medium','high','critical')",
            name="ck_work_orders_priority",
        ),
        sa.CheckConstraint(
            "status IN ('draft','pending_approval','approved','rejected','open',"
            "'in_progress','completed','cancelled')",
            name="ck_work_orders_status",
        ),
    )
    op.create_index(
        "ix_work_orders_machine_status", "work_orders", ["machine_id", "status"]
    )

    op.create_table(
        "agent_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column(
            "machine_id",
            sa.String(32),
            sa.ForeignKey("machines.machine_id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("pending_action_ids", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','waiting_for_approval','completed','failed')",
            name="ck_agent_sessions_status",
        ),
    )
    op.create_index(
        "ix_agent_sessions_machine_status", "agent_sessions", ["machine_id", "status"]
    )

    op.create_table(
        "agent_feedback",
        sa.Column("feedback_id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("agent_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("agent_version", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rating IN ('helpful','not_helpful')", name="ck_agent_feedback_rating"
        ),
    )
    op.create_index(
        "ix_agent_feedback_session_request",
        "agent_feedback",
        ["session_id", "request_id"],
    )

    op.create_table(
        "approval_actions",
        sa.Column("action_id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("agent_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(128), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.String(100)),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','expired')",
            name="ck_approval_actions_status",
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_approval_expiry"),
        sa.CheckConstraint(
            "(status IN ('approved','rejected') AND decided_at IS NOT NULL AND "
            "decided_by IS NOT NULL) OR (status IN ('pending','expired') AND "
            "decided_at IS NULL AND decided_by IS NULL)",
            name="ck_approval_decision_metadata",
        ),
    )
    op.create_index(
        "ix_approval_session_status", "approval_actions", ["session_id", "status"]
    )


def downgrade() -> None:
    for table in (
        "approval_actions",
        "agent_feedback",
        "agent_sessions",
        "work_orders",
        "incidents",
        "maintenance_records",
        "sensor_readings",
        "machines",
    ):
        op.drop_table(table)
