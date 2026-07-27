"""initial_schema

Revision ID: 0472b5a82e80
Revises:
Create Date: 2026-03-17 11:44:46.637605

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0472b5a82e80"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
