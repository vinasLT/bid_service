from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "dadf6a610765"
down_revision: Union[str, Sequence[str], None] = "7c6d6d2edc60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bid",
        sa.Column(
            "is_buy_now",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Optional: remove DB default after backfilling existing rows
    op.alter_column("bid", "is_buy_now", server_default=None)


def downgrade() -> None:
    op.drop_column("bid", "is_buy_now")
