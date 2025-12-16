"""add_epics_table

Revision ID: 6870130f1b69
Revises: merge_heads_001
Create Date: 2025-12-16 21:34:01.471033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6870130f1b69'
down_revision: Union[str, None] = 'merge_heads_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу epics
    op.create_table(
        'epics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('position', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индексы для epics
    op.create_index('ix_epics_id', 'epics', ['id'], unique=False)
    op.create_index('ix_epics_project_id', 'epics', ['project_id'], unique=False)
    op.create_index('idx_epic_project_position', 'epics', ['project_id', 'position'], unique=False)
    op.create_index('idx_epic_confidence', 'epics', ['project_id', 'confidence_score'], unique=False)
    
    # Добавляем колонку epic_id в user_stories
    op.add_column(
        'user_stories',
        sa.Column('epic_id', sa.Integer(), nullable=True)
    )
    
    # Создаем внешний ключ для epic_id
    op.create_foreign_key(
        'fk_user_stories_epic_id',
        'user_stories',
        'epics',
        ['epic_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Создаем индекс для epic_id
    op.create_index('ix_user_stories_epic_id', 'user_stories', ['epic_id'], unique=False)
    op.create_index('idx_story_epic', 'user_stories', ['epic_id'], unique=False)


def downgrade() -> None:
    # Удаляем индексы и колонку epic_id из user_stories
    op.drop_index('idx_story_epic', table_name='user_stories')
    op.drop_index('ix_user_stories_epic_id', table_name='user_stories')
    op.drop_constraint('fk_user_stories_epic_id', 'user_stories', type_='foreignkey')
    op.drop_column('user_stories', 'epic_id')
    
    # Удаляем индексы и таблицу epics
    op.drop_index('idx_epic_confidence', table_name='epics')
    op.drop_index('idx_epic_project_position', table_name='epics')
    op.drop_index('ix_epics_project_id', table_name='epics')
    op.drop_index('ix_epics_id', table_name='epics')
    op.drop_table('epics')

