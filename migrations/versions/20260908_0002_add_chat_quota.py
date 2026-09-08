"""Add daily chat usage tracking to users."""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0002"
down_revision = "20260906_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("chat_usage_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "chat_usage_date",
            sa.Date(),
            server_default=sa.text("((CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date)"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users_chat_usage_count_nonnegative",
        "users",
        "chat_usage_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_chat_usage_count_nonnegative", "users", type_="check")
    op.drop_column("users", "chat_usage_date")
    op.drop_column("users", "chat_usage_count")
