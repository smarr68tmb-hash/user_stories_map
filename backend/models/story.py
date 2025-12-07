"""
User Story model
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from utils.database import Base


# Допустимые статусы для истории
STORY_STATUSES = ['todo', 'in_progress', 'done', 'blocked']


class UserStory(Base):
    """Модель пользовательской истории"""
    __tablename__ = "user_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("user_tasks.id"), nullable=False)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    title = Column(String)
    description = Column(Text)
    priority = Column(String)
    acceptance_criteria = Column(JSON)
    position = Column(Integer, default=0)
    status = Column(String, default='todo')  # todo, in_progress, done, blocked
    
    # Relationships
    task = relationship("UserTask", back_populates="stories")
    release = relationship("Release", back_populates="stories")
    
    __table_args__ = (
        Index('idx_story_task_release', 'task_id', 'release_id'),
        Index('idx_story_position', 'task_id', 'release_id', 'position'),
        Index('idx_story_status', 'status'),
    )

