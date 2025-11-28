"""
Схемы для анализа User Story Map
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class IssueSeverity(str, Enum):
    """Уровень серьезности проблемы"""
    ERROR = "error"      # Критическая проблема
    WARNING = "warning"  # Предупреждение
    INFO = "info"        # Информация/рекомендация


class IssueType(str, Enum):
    """Тип проблемы валидации"""
    EMPTY_CELL = "empty_cell"                    # Пустая ячейка
    MISSING_DESCRIPTION = "missing_description"  # Нет описания
    MISSING_CRITERIA = "missing_criteria"        # Нет acceptance criteria
    EMPTY_ACTIVITY = "empty_activity"            # Activity без tasks
    EMPTY_TASK = "empty_task"                    # Task без stories
    SHORT_TITLE = "short_title"                  # Слишком короткое название
    DUPLICATE_TITLE = "duplicate_title"          # Дублирующееся название
    UNBALANCED_RELEASES = "unbalanced_releases"  # Несбалансированные релизы


class ValidationIssue(BaseModel):
    """Проблема, найденная при валидации"""
    type: IssueType
    severity: IssueSeverity
    message: str
    location: Optional[dict] = None  # {task_id, release_id, activity_id, story_id}
    story_ids: Optional[List[int]] = None  # Для групповых проблем


class ValidationResult(BaseModel):
    """Результат валидации карты"""
    is_valid: bool = Field(description="Карта валидна (нет ошибок)")
    score: int = Field(ge=0, le=100, description="Оценка качества карты 0-100")
    issues: List[ValidationIssue] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


# === Similarity Analysis ===

class SimilarStory(BaseModel):
    """История с оценкой схожести"""
    id: int
    title: str
    description: Optional[str] = None
    similarity: float = Field(ge=0.0, le=1.0, description="Коэффициент схожести 0-1")
    task_title: Optional[str] = None
    activity_title: Optional[str] = None


class SimilarityGroup(BaseModel):
    """Группа похожих историй"""
    stories: List[SimilarStory]
    group_type: str = Field(description="duplicate или similar")
    recommendation: str


class ConflictType(str, Enum):
    """Тип конфликта"""
    CONTRADICTION = "contradiction"  # Прямое противоречие
    OVERLAP = "overlap"              # Пересечение функциональности
    DEPENDENCY = "dependency"        # Неявная зависимость


class StoryConflict(BaseModel):
    """Конфликт между историями"""
    story1: SimilarStory
    story2: SimilarStory
    conflict_type: ConflictType
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность в конфликте")
    explanation: str
    recommendation: str


class SimilarityResult(BaseModel):
    """Результат анализа схожести"""
    similar_groups: List[SimilarityGroup] = Field(default_factory=list)
    potential_conflicts: List[StoryConflict] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


# === Full Analysis ===

class FullAnalysisResult(BaseModel):
    """Полный отчет анализа проекта"""
    project_id: int
    project_name: str
    validation: ValidationResult
    similarity: SimilarityResult
    overall_score: int = Field(ge=0, le=100, description="Общая оценка качества")
    summary: str = Field(description="Краткое резюме анализа")


# === Request schemas ===

class AnalysisRequest(BaseModel):
    """Запрос на анализ"""
    include_ai_conflicts: bool = Field(
        default=False, 
        description="Использовать AI для поиска конфликтов (медленнее, но точнее)"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.5,
        le=1.0,
        description="Порог схожести для группировки (0.5-1.0)"
    )
    duplicate_threshold: float = Field(
        default=0.9,
        ge=0.8,
        le=1.0,
        description="Порог для определения дубликатов (0.8-1.0)"
    )

