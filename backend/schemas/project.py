"""
Project schemas
"""
from typing import Optional, List
from pydantic import BaseModel
from .story import StoryResponse


class RequirementsInput(BaseModel):
    """Схема входных требований для генерации карты"""
    text: str


class TaskResponse(BaseModel):
    """Схема ответа с информацией о задаче"""
    id: int
    title: str
    position: int
    stories: List[StoryResponse]
    
    class Config:
        from_attributes = True


class ActivityResponse(BaseModel):
    """Схема ответа с информацией об активности"""
    id: int
    title: str
    position: int
    tasks: List[TaskResponse]
    
    class Config:
        from_attributes = True


class ReleaseResponse(BaseModel):
    """Схема ответа с информацией о релизе"""
    id: int
    title: str
    position: int
    
    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    """Схема ответа с полной информацией о проекте"""
    id: int
    name: str
    raw_requirements: Optional[str]
    activities: List[ActivityResponse]
    releases: List[ReleaseResponse]
    
    class Config:
        from_attributes = True

