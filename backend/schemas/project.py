"""
Project schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from .story import StoryResponse


class RequirementsInput(BaseModel):
    """Схема входных требований для генерации карты"""
    text: str
    skip_enhancement: bool = Field(
        default=False, 
        description="Пропустить этап улучшения требований (Stage 1)"
    )
    use_enhanced_text: bool = Field(
        default=True,
        description="Использовать улучшенный текст для генерации (если был enhancement)"
    )


class EnhancementRequest(BaseModel):
    """Схема запроса на улучшение требований (Stage 1)"""
    text: str


class EnhancementResponse(BaseModel):
    """Схема ответа с улучшенными требованиями"""
    original_text: str
    enhanced_text: str
    added_aspects: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    detected_product_type: str = "unknown"
    detected_roles: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    fallback: bool = Field(default=False, description="True если AI вернул ошибку и используется оригинал")


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


class ActivityCreate(BaseModel):
    """Схема для создания Activity"""
    project_id: int
    title: str
    position: Optional[int] = None


class ActivityUpdate(BaseModel):
    """Схема для обновления Activity"""
    title: Optional[str] = None
    position: Optional[int] = None


class TaskCreate(BaseModel):
    """Схема для создания Task"""
    activity_id: int
    title: str
    position: Optional[int] = None


class TaskUpdate(BaseModel):
    """Схема для обновления Task"""
    title: Optional[str] = None
    position: Optional[int] = None


class ProjectUpdate(BaseModel):
    """Схема для обновления проекта"""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Название проекта (максимум 255 символов)"
    )

