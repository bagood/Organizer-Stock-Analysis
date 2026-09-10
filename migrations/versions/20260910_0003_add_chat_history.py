"""Add daily chat conversations and messages."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0003"
down_revision = "20260908_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "chat_usage_date",
        server_default=sa.text("((CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Jakarta')::date)"),
    )
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Asia/Jakarta",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "business_date", name="uq_chat_conversations_user_date"
        ),
    )
    op.create_index(
        "ix_chat_conversations_user_id", "chat_conversations", ["user_id"], unique=False
    )
    op.create_index(
        "ix_chat_conversations_expires_at",
        "chat_conversations",
        ["expires_at"],
        unique=False,
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("client_message_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(content)) > 0", name="ck_chat_messages_content_nonempty"
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name="ck_chat_messages_role"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_chat_messages_conversation_client_message_id",
        "chat_messages",
        ["conversation_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )
    op.create_index(
        "uq_chat_messages_conversation_sequence",
        "chat_messages",
        ["conversation_id", "sequence_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_chat_messages_conversation_sequence", table_name="chat_messages"
    )
    op.drop_index(
        "uq_chat_messages_conversation_client_message_id", table_name="chat_messages"
    )
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_conversations_expires_at", table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_user_id", table_name="chat_conversations")
    op.drop_table("chat_conversations")
    op.alter_column(
        "users",
        "chat_usage_date",
        server_default=sa.text("((CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date)"),
    )
