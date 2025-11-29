"""
User Story schemas
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, field_validator


# Допустимые статусы
StoryStatus = Literal['todo', 'in_progress', 'done']


class StoryCreate(BaseModel):
    """Схема для создания пользовательской истории"""
    task_id: int
    release_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "Later"
    acceptance_criteria: Optional[List[str]] = []
    status: Optional[StoryStatus] = "todo"


class StoryUpdate(BaseModel):
    """Схема для обновления пользовательской истории"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    release_id: Optional[int] = None
    status: Optional[StoryStatus] = None


class StoryStatusUpdate(BaseModel):
    """Схема для быстрого обновления статуса истории"""
    status: StoryStatus


class StoryMove(BaseModel):
    """Схема для перемещения истории (drag & drop)"""
    task_id: int
    release_id: Optional[int] = None
    position: int


class StoryResponse(BaseModel):
    """Схема ответа с информацией об истории"""
    id: int
    title: str
    description: Optional[str]
    priority: Optional[str]
    acceptance_criteria: Optional[List[str]]
    release_id: Optional[int]
    position: int
    status: Optional[str] = "todo"
    
    class Config:
        from_attributes = True


class AIImproveRequest(BaseModel):
    """Схема для запроса AI улучшения истории"""
    prompt: str  # Свободный текстовый запрос пользователя
    action: Optional[str] = None  # Quick action: 'details', 'criteria', 'split', 'edge_cases'


class AIImproveResponse(BaseModel):
    """Схема ответа с улучшенной историей"""
    success: bool
    message: str
    improved_story: Optional[StoryResponse] = None
    additional_stories: Optional[List[dict]] = None  # Для случая разделения на несколько историй
    suggestion: Optional[str] = None  # Дополнительные предложения от AI


class AIBulkImproveRequest(BaseModel):
    """Схема для массового улучшения историй"""
    story_ids: List[int]
    prompt: str
    action: Optional[str] = None


class AIBulkImproveResponse(BaseModel):
    """Схема ответа для массового улучшения"""
    success: bool
    message: str
    improved_count: int
    failed_count: int
    details: List[dict]

