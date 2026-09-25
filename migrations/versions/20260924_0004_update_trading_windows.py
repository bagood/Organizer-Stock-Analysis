"""Replace trading-window ranges with fixed durations."""

from alembic import op

revision = "20260924_0004"
down_revision = "20260910_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE trading_window RENAME VALUE '5-10dd' TO '5dd'")
    op.execute("ALTER TYPE trading_window RENAME VALUE '10-20dd' TO '10dd'")


def downgrade() -> None:
    op.execute("ALTER TYPE trading_window RENAME VALUE '5dd' TO '5-10dd'")
    op.execute("ALTER TYPE trading_window RENAME VALUE '10dd' TO '10-20dd'")
