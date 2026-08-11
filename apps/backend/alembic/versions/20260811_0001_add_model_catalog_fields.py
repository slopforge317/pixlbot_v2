"""Add stable model catalog fields.

Revision ID: 20260811_0001
Revises: 20260805_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260811_0001"
down_revision: str | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("slug", sa.String(length=100)))
    op.execute(
        """
        UPDATE providers
        SET slug = CASE title
            WHEN 'Nano Banana 2' THEN 'nano-banana-2'
            WHEN 'Nano Banana Pro' THEN 'nano-banana-pro'
            WHEN 'Seedream 5 Lite' THEN 'seedream-5-lite'
            WHEN 'Seedream 4.5' THEN 'seedream-4-5'
            WHEN 'GPT Image 1.5' THEN 'gpt-image-1-5'
            WHEN 'Sora 2 Pro' THEN 'sora-2-pro'
            WHEN 'Kling 2.6' THEN 'kling-2-6'
            ELSE 'provider-' || id::text
        END
        """
    )
    op.alter_column("providers", "slug", nullable=False)
    op.create_unique_constraint("uq_providers_slug", "providers", ["slug"])

    op.add_column(
        "ai_models",
        sa.Column(
            "input_mode",
            sa.String(length=20),
            server_default="text_only",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE ai_models
        SET input_mode = CASE
            WHEN api_model_id IN ('nano-banana-2', 'nano-banana-pro')
                THEN 'image_optional'
            WHEN api_model_id LIKE '%image-to-image%'
                OR api_model_id LIKE '%image-to-video%'
                OR api_model_id = 'seedream/4.5-edit'
                THEN 'image_required'
            ELSE 'text_only'
        END
        """
    )
    op.create_check_constraint(
        "ck_ai_models_input_mode",
        "ai_models",
        "input_mode IN ('text_only', 'image_required', 'image_optional')",
    )

    op.execute("UPDATE providers SET active = false WHERE gen_type <> 'image'")
    op.execute(
        """
        UPDATE ai_models
        SET active = false
        WHERE provider_id IN (
            SELECT id FROM providers WHERE gen_type <> 'image'
        )
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_ai_models_input_mode", "ai_models", type_="check")
    op.drop_column("ai_models", "input_mode")
    op.drop_constraint("uq_providers_slug", "providers", type_="unique")
    op.drop_column("providers", "slug")
