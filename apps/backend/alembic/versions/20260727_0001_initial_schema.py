"""Create the initial pixlbot schema.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260727_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_packages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("credit_amount", sa.Integer(), nullable=False),
        sa.Column("fiat_price", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "funnel_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "trigger_event",
            sa.Enum(
                "user_registered",
                "first_generation_done",
                name="funneltriggerevent",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("delay_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "condition",
            sa.Enum(
                "no_generation_done",
                "no_deposit",
                name="funnelcondition",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("button_text", sa.String(length=255), nullable=True),
        sa.Column("button_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("gen_type", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("utm_source", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_users_telegram_user_id"),
        "users",
        ["telegram_user_id"],
        unique=True,
    )
    op.create_table(
        "ai_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("api_model_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("variant_keys", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_model_id"),
    )
    op.create_index(
        op.f("ix_ai_models_provider_id"),
        "ai_models",
        ["provider_id"],
        unique=False,
    )
    op.create_table(
        "payments",
        sa.Column("payment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "success",
                "failed",
                name="paymentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("amount_currency", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("yookassa_payment_id", sa.String(length=50), nullable=True),
        sa.Column("credit_package_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["credit_package_id"], ["credit_packages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("payment_id"),
    )
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_payments_yookassa_payment_id"),
        "payments",
        ["yookassa_payment_id"],
        unique=True,
    )
    op.create_table(
        "scheduled_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("funnel_step_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "sent",
                "skipped",
                "cancelled",
                name="scheduledmessagestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["funnel_step_id"], ["funnel_steps.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "funnel_step_id",
            name="uq_scheduled_message_user_step",
        ),
    )
    op.create_index(
        op.f("ix_scheduled_messages_user_id"),
        "scheduled_messages",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "pricing_variants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("variant_values", sa.JSON(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["ai_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pricing_variants_model_id"),
        "pricing_variants",
        ["model_id"],
        unique=False,
    )
    op.create_table(
        "generations_job",
        sa.Column("job_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("pricing_variant_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queue",
                "processing",
                "done",
                "error",
                name="jobstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("provider_task_id", sa.String(length=255), nullable=True),
        sa.Column("provider_complete_time", sa.DateTime(), nullable=True),
        sa.Column("provider_consume_credit", sa.Integer(), nullable=False),
        sa.Column("cost_credit", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("generation_params", sa.JSON(), nullable=False),
        sa.Column("references_meta", sa.JSON(), nullable=True),
        sa.Column("success_url_asset", sa.String(length=1024), nullable=True),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pricing_variant_id"], ["pricing_variants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        op.f("ix_generations_job_pricing_variant_id"),
        "generations_job",
        ["pricing_variant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generations_job_status"),
        "generations_job",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generations_job_user_id"),
        "generations_job",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "transactions",
        sa.Column("tx_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "deposit",
                "withdrawal",
                "refund",
                "manual",
                "bonus",
                name="transactiontype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("amount_credits", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("credit_package_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["credit_package_id"], ["credit_packages.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["generations_job.job_id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.payment_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("tx_id"),
    )
    op.create_index(
        op.f("ix_transactions_user_id"),
        "transactions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_generations_job_user_id"), table_name="generations_job")
    op.drop_index(op.f("ix_generations_job_status"), table_name="generations_job")
    op.drop_index(
        op.f("ix_generations_job_pricing_variant_id"),
        table_name="generations_job",
    )
    op.drop_table("generations_job")
    op.drop_index(op.f("ix_pricing_variants_model_id"), table_name="pricing_variants")
    op.drop_table("pricing_variants")
    op.drop_index(
        op.f("ix_scheduled_messages_user_id"),
        table_name="scheduled_messages",
    )
    op.drop_table("scheduled_messages")
    op.drop_index(op.f("ix_payments_yookassa_payment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_ai_models_provider_id"), table_name="ai_models")
    op.drop_table("ai_models")
    op.drop_index(op.f("ix_users_telegram_user_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("providers")
    op.drop_table("funnel_steps")
    op.drop_table("credit_packages")
