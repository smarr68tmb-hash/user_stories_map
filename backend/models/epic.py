"""
Epic model
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from utils.database import Base


class Epic(Base):
    """Модель Epic (группа связанных пользовательских историй)"""
    __tablename__ = "epics"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0)  # 0.0-1.0, уверенность AI в группировке
    position = Column(Integer, default=0)  # порядок отображения
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="epics")
    stories = relationship(
        "UserStory",
        back_populates="epic",
        cascade="all, delete-orphan",
        order_by="UserStory.position"
    )
    
    __table_args__ = (
        Index('idx_epic_project_position', 'project_id', 'position'),
        Index('idx_epic_confidence', 'project_id', 'confidence_score'),
    )

