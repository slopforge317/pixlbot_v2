"""Normalize legacy PostgreSQL enum columns.

Revision ID: 20260805_0001
Revises: f7d735a7befd
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0001"
down_revision: str | Sequence[str] | None = "f7d735a7befd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

funnel_trigger_event = postgresql.ENUM(
    "user_registered",
    "first_generation_done",
    name="funneltriggerevent",
    create_type=False,
)
funnel_condition = postgresql.ENUM(
    "no_generation_done",
    "no_deposit",
    name="funnelcondition",
    create_type=False,
)
scheduled_message_status = postgresql.ENUM(
    "pending",
    "sent",
    "skipped",
    "cancelled",
    name="scheduledmessagestatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE funnel_steps "
        "ALTER COLUMN trigger_event TYPE VARCHAR(21) "
        "USING trigger_event::text"
    )
    op.execute(
        "ALTER TABLE funnel_steps "
        "ALTER COLUMN condition TYPE VARCHAR(18) "
        "USING condition::text"
    )
    op.execute(
        "ALTER TABLE scheduled_messages "
        "ALTER COLUMN status TYPE VARCHAR(9) "
        "USING status::text"
    )

    bind = op.get_bind()
    scheduled_message_status.drop(bind, checkfirst=False)
    funnel_condition.drop(bind, checkfirst=False)
    funnel_trigger_event.drop(bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    funnel_trigger_event.create(bind, checkfirst=False)
    funnel_condition.create(bind, checkfirst=False)
    scheduled_message_status.create(bind, checkfirst=False)

    op.execute(
        "ALTER TABLE funnel_steps "
        "ALTER COLUMN trigger_event TYPE funneltriggerevent "
        "USING trigger_event::text::funneltriggerevent"
    )
    op.execute(
        "ALTER TABLE funnel_steps "
        "ALTER COLUMN condition TYPE funnelcondition "
        "USING condition::text::funnelcondition"
    )
    op.execute(
        "ALTER TABLE scheduled_messages "
        "ALTER COLUMN status TYPE scheduledmessagestatus "
        "USING status::text::scheduledmessagestatus"
    )
