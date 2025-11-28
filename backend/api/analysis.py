"""
Analysis endpoints - анализ схожести и валидация карты
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db
from models import User, Project, Activity, UserTask
from schemas import (
    ValidationResult,
    SimilarityResult,
    FullAnalysisResult,
    AnalysisRequest
)
from services import (
    validate_project_map,
    get_validation_summary,
    analyze_similarity,
    get_similarity_summary
)
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["analysis"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def get_project_with_stories(project_id: int, user_id: int, db: Session) -> Project:
    """Получает проект с полной загрузкой всех связей"""
    project = db.query(Project)\
        .options(
            joinedload(Project.activities)
            .subqueryload(Activity.tasks)
            .subqueryload(UserTask.stories),
            joinedload(Project.releases)
        )\
        .filter(Project.id == project_id)\
        .filter(Project.user_id == user_id)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.get("/project/{project_id}/validate", response_model=ValidationResult)
@limiter.limit("30/minute")
def validate_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Валидирует структуру User Story Map проекта
    
    Проверяет:
    - Наличие обязательных элементов (Activities, Tasks, Stories)
    - Пустые ячейки и несвязанные элементы
    - Полноту описания историй
    - Баланс между релизами
    - Дублирующиеся названия
    
    Returns:
        ValidationResult: Результат валидации с оценкой и рекомендациями
    """
    logger.info(f"Validating project {project_id} for user {current_user.id}")
    
    project = get_project_with_stories(project_id, current_user.id, db)
    
    try:
        result = validate_project_map(project, db)
        logger.info(f"Validation completed: score={result.score}, issues={len(result.issues)}")
        return result
    except Exception as e:
        logger.error(f"Validation error for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/project/{project_id}/analyze/similarity", response_model=SimilarityResult)
@limiter.limit("20/minute")
def analyze_project_similarity(
    project_id: int,
    request: Request,
    similarity_threshold: float = 0.7,
    duplicate_threshold: float = 0.9,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Анализирует схожесть историй в проекте
    
    Использует TF-IDF + Cosine Similarity для поиска:
    - Дубликатов (схожесть >= duplicate_threshold)
    - Похожих историй (схожесть >= similarity_threshold)
    
    Args:
        similarity_threshold: Порог для группировки похожих (0.5-1.0, default: 0.7)
        duplicate_threshold: Порог для определения дубликатов (0.8-1.0, default: 0.9)
    
    Returns:
        SimilarityResult: Группы похожих историй и статистика
    """
    # Валидация параметров
    if similarity_threshold < 0.5 or similarity_threshold > 1.0:
        raise HTTPException(status_code=400, detail="similarity_threshold must be between 0.5 and 1.0")
    
    if duplicate_threshold < 0.8 or duplicate_threshold > 1.0:
        raise HTTPException(status_code=400, detail="duplicate_threshold must be between 0.8 and 1.0")
    
    if duplicate_threshold < similarity_threshold:
        raise HTTPException(
            status_code=400, 
            detail="duplicate_threshold must be >= similarity_threshold"
        )
    
    logger.info(
        f"Analyzing similarity for project {project_id} "
        f"(sim={similarity_threshold}, dup={duplicate_threshold})"
    )
    
    project = get_project_with_stories(project_id, current_user.id, db)
    
    try:
        result = analyze_similarity(project, similarity_threshold, duplicate_threshold)
        logger.info(
            f"Similarity analysis completed: "
            f"{result.stats.get('similar_groups_found', 0)} groups found"
        )
        return result
    except Exception as e:
        logger.error(f"Similarity analysis error for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/project/{project_id}/analyze/full", response_model=FullAnalysisResult)
@limiter.limit("10/minute")
def full_project_analysis(
    project_id: int,
    request: Request,
    analysis_request: AnalysisRequest = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Выполняет полный анализ проекта
    
    Включает:
    - Валидацию структуры карты
    - Анализ схожести историй
    - Генерацию общей оценки и резюме
    
    Args:
        analysis_request: Параметры анализа (пороги схожести, AI конфликты)
    
    Returns:
        FullAnalysisResult: Полный отчет с валидацией, схожестью и резюме
    """
    # Дефолтные параметры
    if analysis_request is None:
        analysis_request = AnalysisRequest()
    
    logger.info(f"Running full analysis for project {project_id}")
    
    project = get_project_with_stories(project_id, current_user.id, db)
    
    try:
        # Валидация
        validation_result = validate_project_map(project, db)
        
        # Анализ схожести
        similarity_result = analyze_similarity(
            project,
            similarity_threshold=analysis_request.similarity_threshold,
            duplicate_threshold=analysis_request.duplicate_threshold
        )
        
        # TODO: AI анализ конфликтов (если include_ai_conflicts=True)
        # Пока просто пропускаем
        
        # Расчет общей оценки
        overall_score = calculate_overall_score(validation_result, similarity_result)
        
        # Генерация резюме
        summary = generate_analysis_summary(
            project.name,
            validation_result,
            similarity_result,
            overall_score
        )
        
        logger.info(f"Full analysis completed: overall_score={overall_score}")
        
        return FullAnalysisResult(
            project_id=project.id,
            project_name=project.name,
            validation=validation_result,
            similarity=similarity_result,
            overall_score=overall_score,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Full analysis error for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def calculate_overall_score(
    validation: ValidationResult,
    similarity: SimilarityResult
) -> int:
    """Рассчитывает общую оценку качества проекта"""
    
    # Базовая оценка от валидации (70% веса)
    validation_weight = 0.7
    
    # Штраф за дубликаты (30% веса)
    similarity_weight = 0.3
    
    # Штраф за дубликаты: -10 баллов за каждый дубликат
    duplicates = similarity.stats.get("duplicates_found", 0)
    similarity_penalty = min(duplicates * 10, 30)  # Максимум -30 баллов
    
    similarity_score = 100 - similarity_penalty
    
    overall = int(
        validation.score * validation_weight +
        similarity_score * similarity_weight
    )
    
    return max(0, min(100, overall))


def generate_analysis_summary(
    project_name: str,
    validation: ValidationResult,
    similarity: SimilarityResult,
    overall_score: int
) -> str:
    """Генерирует текстовое резюме анализа"""
    
    # Определяем качество
    if overall_score >= 90:
        quality = "отличное"
        emoji = "🌟"
    elif overall_score >= 70:
        quality = "хорошее"
        emoji = "✅"
    elif overall_score >= 50:
        quality = "удовлетворительное"
        emoji = "⚠️"
    else:
        quality = "требует улучшения"
        emoji = "❌"
    
    parts = [f"{emoji} Проект '{project_name}': качество {quality} ({overall_score}/100)."]
    
    # Статистика
    total_stories = validation.stats.get("total_stories", 0)
    parts.append(f"Всего историй: {total_stories}.")
    
    # Проблемы валидации
    error_count = sum(1 for i in validation.issues if i.severity.value == "error")
    warning_count = sum(1 for i in validation.issues if i.severity.value == "warning")
    
    if error_count > 0:
        parts.append(f"Критических проблем: {error_count}.")
    if warning_count > 0:
        parts.append(f"Предупреждений: {warning_count}.")
    
    # Дубликаты
    duplicates = similarity.stats.get("duplicates_found", 0)
    if duplicates > 0:
        parts.append(f"Найдено потенциальных дубликатов: {duplicates}.")
    
    similar_groups = similarity.stats.get("similar_groups_found", 0) - duplicates
    if similar_groups > 0:
        parts.append(f"Групп похожих историй: {similar_groups}.")
    
    return " ".join(parts)

