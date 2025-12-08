"""
Project models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.database import Base


class Project(Base):
    """Модель проекта User Story Map"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, index=True)
    raw_requirements = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    wireframe_markdown = Column(Text, nullable=True)
    wireframe_generated_at = Column(DateTime(timezone=True), nullable=True)
    wireframe_status = Column(String, default="idle", server_default="idle")
    wireframe_error = Column(Text, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    activities = relationship(
        "Activity",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Activity.position"
    )
    releases = relationship(
        "Release",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Release.position"
    )


class Activity(Base):
    """Модель Activity (высокоуровневая активность пользователя)"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String)
    position = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="activities")
    tasks = relationship(
        "UserTask",
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="UserTask.position"
    )
    
    __table_args__ = (
        Index('idx_activity_project_position', 'project_id', 'position'),
    )


class UserTask(Base):
    """Модель User Task (конкретный шаг пользователя)"""
    __tablename__ = "user_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    title = Column(String)
    position = Column(Integer, default=0)
    
    # Relationships
    activity = relationship("Activity", back_populates="tasks")
    stories = relationship(
        "UserStory",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="UserStory.position"
    )
    
    __table_args__ = (
        Index('idx_task_activity_position', 'activity_id', 'position'),
    )


class Release(Base):
    """Модель релиза (MVP, Release 1, Later)"""
    __tablename__ = "releases"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String)
    position = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="releases")
    stories = relationship("UserStory", back_populates="release")
    
    __table_args__ = (
        Index('idx_release_project_position', 'project_id', 'position'),
    )

