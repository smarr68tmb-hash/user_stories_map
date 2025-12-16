"""
Epic schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class EpicCreate(BaseModel):
    """Схема для создания Epic"""
    project_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    position: int = Field(default=0, ge=0)


class EpicUpdate(BaseModel):
    """Схема для обновления Epic"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    position: Optional[int] = Field(None, ge=0)


class EpicResponse(BaseModel):
    """Схема ответа с информацией об Epic"""
    id: int
    project_id: int
    title: str
    description: Optional[str]
    confidence_score: float
    position: int
    created_at: datetime
    updated_at: datetime
    stories_count: Optional[int] = None  # Количество историй в эпике
    
    class Config:
        from_attributes = True


class EpicWithStoriesResponse(BaseModel):
    """Схема ответа с Epic и списком историй"""
    id: int
    project_id: int
    title: str
    description: Optional[str]
    confidence_score: float
    position: int
    created_at: datetime
    updated_at: datetime
    stories: List[dict] = []  # Список историй в эпике
    
    class Config:
        from_attributes = True


class EpicGenerateRequest(BaseModel):
    """Схема для запроса генерации эпиков"""
    min_epics: int = Field(default=3, ge=1, le=10)
    max_epics: int = Field(default=7, ge=1, le=10)


class EpicGenerateResponse(BaseModel):
    """Схема ответа на генерацию эпиков"""
    success: bool
    message: str
    epics: List[EpicResponse]
    total_stories_grouped: int
    ungrouped_stories_count: int

