"""add share_token to projects

Revision ID: f7a8b9c0d1e2
Revises: 6870130f1b69
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7a8b9c0d1e2'
down_revision = '6870130f1b69'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку share_token в таблицу projects
    op.add_column(
        'projects',
        sa.Column('share_token', sa.String(), nullable=True)
    )
    
    # Создаем уникальный индекс для share_token
    op.create_index('idx_project_share_token', 'projects', ['share_token'], unique=True)


def downgrade():
    op.drop_index('idx_project_share_token', table_name='projects')
    op.drop_column('projects', 'share_token')

