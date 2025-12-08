"""add wireframe fields to projects

Revision ID: 8f2e3b9f61d5
Revises: 87751350a263
Create Date: 2025-12-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f2e3b9f61d5"
down_revision: Union[str, None] = "87751350a263"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("wireframe_markdown", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("wireframe_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "projects",
        sa.Column("wireframe_status", sa.String(), server_default="idle", nullable=True),
    )
    op.add_column("projects", sa.Column("wireframe_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "wireframe_error")
    op.drop_column("projects", "wireframe_status")
    op.drop_column("projects", "wireframe_generated_at")
    op.drop_column("projects", "wireframe_markdown")

