"""
User Story CRUD endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db
from models import User, UserStory, UserTask, Activity, Project, Release
from schemas import (
    StoryCreate, 
    StoryUpdate, 
    StoryMove, 
    StoryResponse,
    AIImproveRequest,
    AIImproveResponse,
    AIBulkImproveRequest,
    AIBulkImproveResponse
)
from dependencies import get_current_active_user
from services import ai_improve_story_content
from config import settings

router = APIRouter(prefix="", tags=["stories"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/story", response_model=StoryResponse)
@limiter.limit("30/minute")
def create_story(
    story: StoryCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создает новую пользовательскую историю"""
    # Проверяем существование task и владельца проекта
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == story.task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Если release_id указан, проверяем его существование и владельца
    if story.release_id:
        release = db.query(Release)\
            .join(Project)\
            .filter(Release.id == story.release_id)\
            .filter(Project.user_id == current_user.id)\
            .first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found or access denied")
    
    # Определяем позицию (в конец списка)
    max_position = db.query(UserStory)\
        .filter(UserStory.task_id == story.task_id)\
        .filter(UserStory.release_id == story.release_id)\
        .count()
    
    new_story = UserStory(
        task_id=story.task_id,
        release_id=story.release_id,
        title=story.title,
        description=story.description,
        priority=story.priority or "Later",
        acceptance_criteria=story.acceptance_criteria or [],
        position=max_position
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return StoryResponse(
        id=new_story.id,
        title=new_story.title,
        description=new_story.description,
        priority=new_story.priority,
        acceptance_criteria=new_story.acceptance_criteria or [],
        release_id=new_story.release_id,
        position=new_story.position
    )


@router.put("/story/{story_id}", response_model=StoryResponse)
@limiter.limit("30/minute")
def update_story(
    story_id: int,
    story_update: StoryUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновляет существующую пользовательскую историю"""
    # Проверяем владельца проекта
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
    # Обновляем только переданные поля
    if story_update.title is not None:
        story.title = story_update.title
    if story_update.description is not None:
        story.description = story_update.description
    if story_update.priority is not None:
        story.priority = story_update.priority
    if story_update.acceptance_criteria is not None:
        story.acceptance_criteria = story_update.acceptance_criteria
    if story_update.release_id is not None:
        # Проверяем существование release
        if story_update.release_id:
            release = db.query(Release).filter(Release.id == story_update.release_id).first()
            if not release:
                raise HTTPException(status_code=404, detail="Release not found")
        story.release_id = story_update.release_id
    
    db.commit()
    db.refresh(story)
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        priority=story.priority,
        acceptance_criteria=story.acceptance_criteria or [],
        release_id=story.release_id,
        position=story.position
    )


@router.delete("/story/{story_id}")
@limiter.limit("30/minute")
def delete_story(
    story_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаляет пользовательскую историю"""
    # Проверяем владельца проекта
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
    task_id = story.task_id
    release_id = story.release_id
    position = story.position
    
    db.delete(story)
    db.commit()
    
    # Обновляем позиции остальных историй
    stories_to_update = db.query(UserStory)\
        .filter(UserStory.task_id == task_id)\
        .filter(UserStory.release_id == release_id)\
        .filter(UserStory.position > position)\
        .all()
    
    for s in stories_to_update:
        s.position -= 1
    
    db.commit()
    
    return {"status": "success", "message": "Story deleted"}


@router.patch("/story/{story_id}/move")
@limiter.limit("30/minute")
def move_story(
    story_id: int,
    move: StoryMove,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Перемещает пользовательскую историю в другую ячейку"""
    # Проверяем владельца проекта для исходной истории
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
    # Проверяем существование task и владельца для целевой ячейки
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == move.task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Если release_id указан, проверяем его существование
    if move.release_id:
        release = db.query(Release).filter(Release.id == move.release_id).first()
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
    
    old_task_id = story.task_id
    old_release_id = story.release_id
    old_position = story.position
    
    # Если перемещаем в другую ячейку, обновляем позиции в старой ячейке
    if old_task_id != move.task_id or old_release_id != move.release_id:
        # Уменьшаем позиции в старой ячейке
        stories_to_update = db.query(UserStory)\
            .filter(UserStory.task_id == old_task_id)\
            .filter(UserStory.release_id == old_release_id)\
            .filter(UserStory.position > old_position)\
            .all()
        
        for s in stories_to_update:
            s.position -= 1
        
        # Увеличиваем позиции в новой ячейке после целевой позиции
        stories_to_shift = db.query(UserStory)\
            .filter(UserStory.task_id == move.task_id)\
            .filter(UserStory.release_id == move.release_id)\
            .filter(UserStory.position >= move.position)\
            .all()
        
        for s in stories_to_shift:
            s.position += 1
    
    # Обновляем историю
    story.task_id = move.task_id
    story.release_id = move.release_id
    story.position = move.position
    
    db.commit()
    db.refresh(story)
    
    return StoryResponse(
        id=story.id,
        title=story.title,
        description=story.description,
        priority=story.priority,
        acceptance_criteria=story.acceptance_criteria or [],
        release_id=story.release_id,
        position=story.position
    )


@router.post("/story/{story_id}/ai-improve", response_model=AIImproveResponse)
@limiter.limit("20/hour")  # Rate limit: 20 запросов в час
def ai_improve_story(
    story_id: int,
    improve_request: AIImproveRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Улучшает пользовательскую историю через AI
    
    Quick actions:
    - 'details': Добавить больше деталей
    - 'criteria': Улучшить acceptance criteria
    - 'split': Разделить на несколько историй
    - 'edge_cases': Добавить edge cases
    """
    # Проверяем владельца проекта
    story = db.query(UserStory)\
        .join(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserStory.id == story_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or access denied")
    
    # Инициализация Redis (опционально)
    redis_client = None
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        redis_client = None
    
    # Подготовка данных истории
    story_data = {
        'title': story.title,
        'description': story.description or '',
        'priority': story.priority or 'Later',
        'acceptance_criteria': story.acceptance_criteria or []
    }
    
    try:
        # Вызов AI сервиса
        ai_result = ai_improve_story_content(
            story_data=story_data,
            user_prompt=improve_request.prompt,
            action=improve_request.action,
            redis_client=redis_client
        )
        
        # Обработка результата
        if ai_result.get('action') == 'split':
            # Случай разделения на несколько историй
            return AIImproveResponse(
                success=True,
                message="История разделена на несколько частей",
                improved_story=None,
                additional_stories=ai_result.get('stories', []),
                suggestion=ai_result.get('suggestion', '')
            )
        else:
            # Случай улучшения текущей истории
            # Обновляем историю в БД
            story.title = ai_result.get('title', story.title)
            story.description = ai_result.get('description', story.description)
            story.priority = ai_result.get('priority', story.priority)
            story.acceptance_criteria = ai_result.get('acceptance_criteria', story.acceptance_criteria)
            
            db.commit()
            db.refresh(story)
            
            return AIImproveResponse(
                success=True,
                message="История успешно улучшена",
                improved_story=StoryResponse(
                    id=story.id,
                    title=story.title,
                    description=story.description,
                    priority=story.priority,
                    acceptance_criteria=story.acceptance_criteria or [],
                    release_id=story.release_id,
                    position=story.position
                ),
                additional_stories=None,
                suggestion=ai_result.get('suggestion', '')
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error improving story: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to improve story: {str(e)}"
        )


@router.post("/stories/ai-bulk-improve", response_model=AIBulkImproveResponse)
@limiter.limit("10/hour")  # Rate limit: 10 запросов в час для массовых операций
def ai_bulk_improve_stories(
    bulk_request: AIBulkImproveRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Массовое улучшение нескольких историй через AI
    """
    if not bulk_request.story_ids:
        raise HTTPException(status_code=400, detail="No story IDs provided")
    
    if len(bulk_request.story_ids) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 stories can be improved at once"
        )
    
    # Инициализация Redis
    redis_client = None
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        redis_client = None
    
    improved_count = 0
    failed_count = 0
    details = []
    
    for story_id in bulk_request.story_ids:
        try:
            # Проверяем владельца проекта для каждой истории
            story = db.query(UserStory)\
                .join(UserTask)\
                .join(Activity)\
                .join(Project)\
                .filter(UserStory.id == story_id)\
                .filter(Project.user_id == current_user.id)\
                .first()
            
            if not story:
                details.append({
                    'story_id': story_id,
                    'success': False,
                    'error': 'Story not found or access denied'
                })
                failed_count += 1
                continue
            
            # Подготовка данных истории
            story_data = {
                'title': story.title,
                'description': story.description or '',
                'priority': story.priority or 'Later',
                'acceptance_criteria': story.acceptance_criteria or []
            }
            
            # Вызов AI сервиса
            ai_result = ai_improve_story_content(
                story_data=story_data,
                user_prompt=bulk_request.prompt,
                action=bulk_request.action,
                redis_client=redis_client
            )
            
            # Обновляем историю (пропускаем split для bulk операций)
            if ai_result.get('action') != 'split':
                story.title = ai_result.get('title', story.title)
                story.description = ai_result.get('description', story.description)
                story.priority = ai_result.get('priority', story.priority)
                story.acceptance_criteria = ai_result.get('acceptance_criteria', story.acceptance_criteria)
                
                db.commit()
                
                details.append({
                    'story_id': story_id,
                    'success': True,
                    'title': story.title
                })
                improved_count += 1
            else:
                details.append({
                    'story_id': story_id,
                    'success': False,
                    'error': 'Split action is not supported in bulk operations'
                })
                failed_count += 1
        
        except Exception as e:
            logger.error(f"Error improving story {story_id}: {e}")
            details.append({
                'story_id': story_id,
                'success': False,
                'error': str(e)
            })
            failed_count += 1
    
    return AIBulkImproveResponse(
        success=improved_count > 0,
        message=f"Улучшено {improved_count} из {len(bulk_request.story_ids)} историй",
        improved_count=improved_count,
        failed_count=failed_count,
        details=details
    )

