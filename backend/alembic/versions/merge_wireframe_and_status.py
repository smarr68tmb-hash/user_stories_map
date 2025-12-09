"""merge wireframe and story status migrations

Revision ID: merge_heads_001
Revises: 8f2e3b9f61d5, a1b2c3d4e5f6
Create Date: 2025-12-09 06:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "merge_heads_001"
down_revision: Union[str, None] = ("8f2e3b9f61d5", "a1b2c3d4e5f6")  # type: ignore
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge migration - no changes needed, just merges two branches
    pass


def downgrade() -> None:
    # Merge migration - no changes needed
    pass

