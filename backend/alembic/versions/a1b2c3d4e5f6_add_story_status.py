"""add story status

Revision ID: a1b2c3d4e5f6
Revises: 87751350a263
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '87751350a263'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем колонку status с значением по умолчанию 'todo'
    op.add_column(
        'user_stories',
        sa.Column('status', sa.String(), nullable=True, server_default='todo')
    )
    
    # Обновляем существующие записи
    op.execute("UPDATE user_stories SET status = 'todo' WHERE status IS NULL")
    
    # Создаем индекс для быстрого поиска по статусу
    op.create_index('idx_story_status', 'user_stories', ['status'])


def downgrade():
    op.drop_index('idx_story_status', table_name='user_stories')
    op.drop_column('user_stories', 'status')

