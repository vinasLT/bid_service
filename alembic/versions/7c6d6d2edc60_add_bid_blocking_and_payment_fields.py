"""Add bid blocking/payment fields and on-approval status

Revision ID: 7c6d6d2edc60
Revises: 90e96cf4902f
Create Date: 2025-11-12 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c6d6d2edc60'
down_revision: Union[str, Sequence[str], None] = '90e96cf4902f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # Clean up any previous failed batch tables
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_bid")

    # Extend bidstatus enum with ON_APPROVAL
    if dialect == "postgresql":
        op.execute("ALTER TYPE bidstatus ADD VALUE IF NOT EXISTS 'ON_APPROVAL'")
    elif dialect == "sqlite":
        with op.batch_alter_table("bid") as batch_op:
            batch_op.alter_column(
                "bid_status",
                existing_type=sa.Enum("WAITING_AUCTION_RESULT", "WON", "LOST", name="bidstatus"),
                type_=sa.Enum("WAITING_AUCTION_RESULT", "WON", "LOST", "ON_APPROVAL", name="bidstatus"),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "bid",
            "bid_status",
            existing_type=sa.Enum("WAITING_AUCTION_RESULT", "WON", "LOST", name="bidstatus"),
            type_=sa.Enum("WAITING_AUCTION_RESULT", "WON", "LOST", "ON_APPROVAL", name="bidstatus"),
            existing_nullable=False,
        )

    payment_status_enum = sa.Enum("NOT_REQUIRED", "PENDING", "PAID", name="paymentstatus")
    payment_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "bid",
        sa.Column("payment_status", payment_status_enum, nullable=False, server_default="NOT_REQUIRED"),
    )
    op.add_column(
        "bid",
        sa.Column("account_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    if dialect != "sqlite":
        # Drop server defaults to avoid locking them in (unsupported on SQLite)
        op.alter_column("bid", "payment_status", server_default=None)
        op.alter_column("bid", "account_blocked", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("bid", "account_blocked")
    op.drop_column("bid", "payment_status")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS paymentstatus")

    # Note: removing ON_APPROVAL from bidstatus is not supported in-place on PostgreSQL; the value will remain.
