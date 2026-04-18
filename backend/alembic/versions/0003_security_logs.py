"""创建安全日志表

Revision ID: 0003_security_logs
Revises: 0002_system_settings
Create Date: 2026-01-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_security_logs"
down_revision: str | None = "0002_system_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建安全事件类型枚举
    security_event_type = sa.Enum(
        "login_failed",
        "login_anomaly",
        "request_error",
        "request_blocked",
        "service_error",
        "service_recovered",
        "daily_report",
        "config_changed",
        name="securityeventtype",
    )

    # 创建安全严重程度枚举
    security_severity = sa.Enum(
        "info",
        "warning",
        "error",
        "critical",
        name="securityseverity",
    )

    # 创建安全日志表
    op.create_table(
        "security_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", security_event_type, nullable=False),
        sa.Column("severity", security_severity, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username", sa.String(50), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 创建索引
    op.create_index("ix_security_logs_event_type", "security_logs", ["event_type"])
    op.create_index("ix_security_logs_severity", "security_logs", ["severity"])
    op.create_index("ix_security_logs_user_id", "security_logs", ["user_id"])
    op.create_index("ix_security_logs_created_at", "security_logs", ["created_at"])
    op.create_index("ix_security_logs_archived", "security_logs", ["archived"])
    op.create_index(
        "ix_security_logs_date_type", "security_logs", ["created_at", "event_type"]
    )
    op.create_index(
        "ix_security_logs_archived_date", "security_logs", ["archived", "created_at"]
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_security_logs_archived_date", table_name="security_logs")
    op.drop_index("ix_security_logs_date_type", table_name="security_logs")
    op.drop_index("ix_security_logs_archived", table_name="security_logs")
    op.drop_index("ix_security_logs_created_at", table_name="security_logs")
    op.drop_index("ix_security_logs_user_id", table_name="security_logs")
    op.drop_index("ix_security_logs_severity", table_name="security_logs")
    op.drop_index("ix_security_logs_event_type", table_name="security_logs")

    # 删除表
    op.drop_table("security_logs")

    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS securityseverity")
    op.execute("DROP TYPE IF EXISTS securityeventtype")
