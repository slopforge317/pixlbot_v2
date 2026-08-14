"""Add Telegram Payments fields and deposit idempotency.

Revision ID: 20260814_0001
Revises: 20260811_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260814_0001"
down_revision: str | None = "20260811_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("credits_amount", sa.Integer(), nullable=True))
    op.add_column(
        "payments",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="RUB",
            nullable=False,
        ),
    )
    op.add_column(
        "payments", sa.Column("invoice_payload", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "payments",
        sa.Column("telegram_payment_charge_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("provider_payment_charge_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "payments", sa.Column("customer_email", sa.String(length=320), nullable=True)
    )
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(), nullable=True))

    op.create_index(
        "ix_payments_invoice_payload",
        "payments",
        ["invoice_payload"],
        unique=True,
    )
    op.create_index(
        "ix_payments_telegram_payment_charge_id",
        "payments",
        ["telegram_payment_charge_id"],
        unique=True,
    )
    op.create_index(
        "ix_payments_provider_payment_charge_id",
        "payments",
        ["provider_payment_charge_id"],
        unique=True,
    )
    op.create_unique_constraint(
        "uq_transactions_payment_id",
        "transactions",
        ["payment_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transactions_payment_id",
        "transactions",
        type_="unique",
    )
    op.drop_index(
        "ix_payments_provider_payment_charge_id",
        table_name="payments",
    )
    op.drop_index(
        "ix_payments_telegram_payment_charge_id",
        table_name="payments",
    )
    op.drop_index("ix_payments_invoice_payload", table_name="payments")
    op.drop_column("payments", "paid_at")
    op.drop_column("payments", "customer_email")
    op.drop_column("payments", "provider_payment_charge_id")
    op.drop_column("payments", "telegram_payment_charge_id")
    op.drop_column("payments", "invoice_payload")
    op.drop_column("payments", "currency")
    op.drop_column("payments", "credits_amount")
