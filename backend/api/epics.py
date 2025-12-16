"""
Epic endpoints - управление эпиками (группировка историй)
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db
from models import User, Project, Epic, UserStory, UserTask, Activity
from schemas import (
    EpicResponse,
    EpicCreate,
    EpicUpdate,
    EpicWithStoriesResponse,
    EpicGenerateRequest,
    EpicGenerateResponse,
    StoryResponse
)
from services.epic_service import group_stories_into_epics, create_epics_from_grouping
from dependencies import get_current_active_user
from config import settings

router = APIRouter(prefix="", tags=["epics"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def get_redis_client():
    """Получает Redis клиент или возвращает None если недоступен"""
    try:
        import redis
        if settings.REDIS_URL:
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()  # Проверка соединения
            return redis_client
    except Exception:
        pass
    return None


def get_project_for_user(project_id: int, user_id: int, db: Session) -> Project:
    """Получает проект пользователя или выбрасывает 404"""
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .filter(Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_epic_for_user(epic_id: int, user_id: int, db: Session) -> Epic:
    """Получает эпик пользователя или выбрасывает 404"""
    epic = (
        db.query(Epic)
        .join(Project)
        .filter(Epic.id == epic_id)
        .filter(Project.user_id == user_id)
        .first()
    )
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")
    return epic


def get_story_for_user(story_id: int, user_id: int, db: Session) -> UserStory:
    """Получает историю пользователя или выбрасывает 404"""
    story = (
        db.query(UserStory)
        .join(UserTask)
        .join(Activity)
        .join(Project)
        .filter(UserStory.id == story_id)
        .filter(Project.user_id == user_id)
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/project/{project_id}/epics/generate", response_model=EpicGenerateResponse)
@limiter.limit("10/hour")
def generate_epics(
    project_id: int,
    req: EpicGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Генерирует эпики для проекта через AI группировку историй.
    
    Rate limit: 10 запросов в час
    """
    # Получаем проект
    project = get_project_for_user(project_id, current_user.id, db)
    
    # Валидация min/max
    if req.min_epics > req.max_epics:
        raise HTTPException(
            status_code=400,
            detail="min_epics must be <= max_epics"
        )
    
    # Получаем все истории проекта
    stories = (
        db.query(UserStory)
        .join(UserTask)
        .join(Activity)
        .filter(Activity.project_id == project_id)
        .order_by(UserStory.id)
        .all()
    )
    
    if not stories:
        raise HTTPException(
            status_code=400,
            detail="Project has no stories. Generate a map first."
        )
    
    # Проверка достаточности историй
    if len(stories) < req.min_epics:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stories ({len(stories)}) for {req.min_epics} epics. Minimum {req.min_epics} stories required."
        )
    
    # Получаем Redis клиент
    redis_client = get_redis_client()
    
    try:
        # Группируем истории в эпики
        logger.info(f"Generating epics for project {project_id} with {len(stories)} stories")
        epics_data = group_stories_into_epics(
            stories=stories,
            project=project,
            min_epics=req.min_epics,
            max_epics=req.max_epics,
            redis_client=redis_client,
            use_cache=True
        )
        
        # Создаем эпики в БД
        created_epics = create_epics_from_grouping(
            db=db,
            project=project,
            epics_data=epics_data
        )
        
        # Подсчитываем статистику
        total_stories_grouped = sum(len(epic_data.get("story_ids", [])) for epic_data in epics_data)
        ungrouped_count = len(stories) - total_stories_grouped
        
        # Формируем ответ
        epic_responses = [
            EpicResponse(
                id=epic.id,
                project_id=epic.project_id,
                title=epic.title,
                description=epic.description,
                confidence_score=epic.confidence_score,
                position=epic.position,
                created_at=epic.created_at,
                updated_at=epic.updated_at,
                stories_count=len(epic.stories)
            )
            for epic in created_epics
        ]
        
        return EpicGenerateResponse(
            success=True,
            message=f"Successfully generated {len(created_epics)} epics",
            epics=epic_responses,
            total_stories_grouped=total_stories_grouped,
            ungrouped_stories_count=ungrouped_count
        )
        
    except Exception as e:
        logger.error(f"Error generating epics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate epics: {str(e)}"
        )


@router.get("/project/{project_id}/epics", response_model=List[EpicWithStoriesResponse])
def get_project_epics(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получает все эпики проекта с историями"""
    # Получаем проект
    project = get_project_for_user(project_id, current_user.id, db)
    
    # Получаем все эпики проекта
    epics = (
        db.query(Epic)
        .filter(Epic.project_id == project_id)
        .order_by(Epic.position)
        .options(joinedload(Epic.stories))
        .all()
    )
    
    # Формируем ответ
    result = []
    for epic in epics:
        stories_data = [
            StoryResponse(
                id=story.id,
                title=story.title,
                description=story.description,
                priority=story.priority,
                acceptance_criteria=story.acceptance_criteria or [],
                release_id=story.release_id,
                epic_id=story.epic_id,
                position=story.position,
                status=story.status or "todo"
            )
            for story in epic.stories
        ]
        
        result.append(EpicWithStoriesResponse(
            id=epic.id,
            project_id=epic.project_id,
            title=epic.title,
            description=epic.description,
            confidence_score=epic.confidence_score,
            position=epic.position,
            created_at=epic.created_at,
            updated_at=epic.updated_at,
            stories=stories_data
        ))
    
    return result


@router.put("/epic/{epic_id}", response_model=EpicResponse)
def update_epic(
    epic_id: int,
    epic_update: EpicUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Редактирует эпик (title, description, position)"""
    epic = get_epic_for_user(epic_id, current_user.id, db)
    
    # Обновляем поля
    if epic_update.title is not None:
        epic.title = epic_update.title
    if epic_update.description is not None:
        epic.description = epic_update.description
    if epic_update.position is not None:
        epic.position = epic_update.position
    
    db.commit()
    db.refresh(epic)
    
    return EpicResponse(
        id=epic.id,
        project_id=epic.project_id,
        title=epic.title,
        description=epic.description,
        confidence_score=epic.confidence_score,
        position=epic.position,
        created_at=epic.created_at,
        updated_at=epic.updated_at,
        stories_count=len(epic.stories)
    )


@router.post("/epic/{epic_id}/stories/{story_id}")
def add_story_to_epic(
    epic_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Добавляет историю в эпик"""
    epic = get_epic_for_user(epic_id, current_user.id, db)
    story = get_story_for_user(story_id, current_user.id, db)
    
    # Проверяем, что история из того же проекта
    if story.task.activity.project_id != epic.project_id:
        raise HTTPException(
            status_code=400,
            detail="Story and epic must belong to the same project"
        )
    
    # Проверка на дубликат
    if story.epic_id is not None and story.epic_id != epic_id:
        raise HTTPException(
            status_code=400,
            detail=f"Story {story_id} already belongs to epic {story.epic_id}"
        )
    
    # Добавляем историю в эпик
    story.epic_id = epic.id
    db.commit()
    
    return {"success": True, "message": f"Story {story_id} added to epic {epic_id}"}


@router.delete("/epic/{epic_id}/stories/{story_id}")
def remove_story_from_epic(
    epic_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Убирает историю из эпика"""
    epic = get_epic_for_user(epic_id, current_user.id, db)
    story = get_story_for_user(story_id, current_user.id, db)
    
    # Проверяем, что история действительно в этом эпике
    if story.epic_id != epic.id:
        raise HTTPException(
            status_code=400,
            detail="Story is not in this epic"
        )
    
    # Убираем историю из эпика
    story.epic_id = None
    db.commit()
    
    return {"success": True, "message": f"Story {story_id} removed from epic {epic_id}"}


@router.post("/epic/{epic_id}/accept")
def accept_epic(
    epic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Принимает группировку эпика (сохраняет текущее состояние).
    По сути, это просто подтверждение - эпик уже создан в БД.
    Можно использовать для логирования или будущих функций.
    """
    epic = get_epic_for_user(epic_id, current_user.id, db)
    
    # Эпик уже сохранен, просто возвращаем успех
    logger.info(f"User {current_user.id} accepted epic {epic_id}")
    
    return {
        "success": True,
        "message": f"Epic {epic_id} accepted",
        "epic_id": epic.id,
        "stories_count": len(epic.stories)
    }


@router.post("/epic/{epic_id}/reject")
def reject_epic(
    epic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Отклоняет эпик - убирает все истории из эпика и удаляет сам эпик.
    Истории остаются в проекте, но без привязки к эпику.
    """
    epic = get_epic_for_user(epic_id, current_user.id, db)
    
    # Убираем все истории из эпика
    for story in epic.stories:
        story.epic_id = None
    
    # Удаляем эпик
    db.delete(epic)
    db.commit()
    
    logger.info(f"User {current_user.id} rejected epic {epic_id}")
    
    return {
        "success": True,
        "message": f"Epic {epic_id} rejected and removed",
        "stories_unassigned": len(epic.stories)
    }

