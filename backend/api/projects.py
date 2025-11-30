"""
Project endpoints - генерация и управление проектами
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db
from models import User, Project, Activity, UserTask, Release, UserStory
from schemas import (
    RequirementsInput, 
    EnhancementRequest,
    EnhancementResponse,
    ProjectResponse, 
    ActivityResponse, 
    TaskResponse, 
    StoryResponse, 
    ReleaseResponse
)
from services.ai_service import generate_ai_map, enhance_requirements
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def get_redis_client():
    """Получает Redis клиент или возвращает None если недоступен"""
    try:
        import redis
        from config import settings
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        return redis_client
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return None


@router.post("/enhance-requirements", response_model=EnhancementResponse)
@limiter.limit("30/hour")
def enhance_requirements_endpoint(
    req: EnhancementRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Stage 1: Улучшает требования пользователя перед генерацией карты
    
    Используется для:
    - Показа улучшений пользователю перед генерацией
    - Добавления недостающих стандартных деталей
    - Структурирования неформального текста
    
    Rate limit: 30 запросов в час
    """
    
    # Валидация входных данных
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Requirements text cannot be empty")
    
    try:
        redis_client = get_redis_client()
        result = enhance_requirements(req.text, redis_client=redis_client)
        
        logger.info(f"Requirements enhanced for user {current_user.id}. Confidence: {result.get('confidence', 'N/A')}")
        
        return EnhancementResponse(
            original_text=result.get("original_text", req.text),
            enhanced_text=result.get("enhanced_text", req.text),
            added_aspects=result.get("added_aspects", []),
            missing_info=result.get("missing_info", []),
            detected_product_type=result.get("detected_product_type", "unknown"),
            detected_roles=result.get("detected_roles", []),
            confidence=result.get("confidence", 1.0),
            fallback=result.get("fallback", False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred"
        logger.error(f"Unexpected error in enhance_requirements: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to enhance requirements: {error_msg}")


@router.post("/generate-map")
@limiter.limit("10/hour")
def generate_map(
    req: RequirementsInput,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Генерирует карту пользовательских историй из текста требований
    
    Two-Stage Processing:
    - Stage 1 (Enhancement): Улучшение требований через gpt-4o-mini (если не skip_enhancement)
    - Stage 2 (Generation): Генерация карты через gpt-4o
    
    Rate limit: 10 запросов в час
    """
    
    # Валидация входных данных
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Requirements text cannot be empty")
    
    # Получаем Redis клиент
    redis_client = get_redis_client()
    
    # Текст для генерации (может быть улучшен на Stage 1)
    generation_text = req.text
    enhancement_data = None
    
    # Stage 1: Enhancement (если не пропущен)
    if not req.skip_enhancement:
        try:
            logger.info(f"Stage 1: Enhancing requirements for user {current_user.id}")
            enhancement_data = enhance_requirements(req.text, redis_client=redis_client)
            
            # Используем улучшенный текст если confidence достаточно высокий
            if (req.use_enhanced_text and 
                enhancement_data.get("confidence", 0) >= 0.7 and 
                not enhancement_data.get("fallback", False)):
                generation_text = enhancement_data.get("enhanced_text", req.text)
                logger.info(f"Using enhanced requirements. Confidence: {enhancement_data.get('confidence')}")
            else:
                logger.info(f"Using original requirements. Confidence: {enhancement_data.get('confidence', 'N/A')}")
                
        except Exception as e:
            # Если enhancement упал - продолжаем с оригинальным текстом
            logger.warning(f"Enhancement failed, using original text: {e}")
            generation_text = req.text
    else:
        logger.info(f"Stage 1 skipped (skip_enhancement=True)")
    
    # Stage 2: Generation
    try:
        logger.info(f"Stage 2: Generating map for user {current_user.id}")
        ai_data = generate_ai_map(generation_text, redis_client=redis_client)
    except HTTPException as e:
        # Сохраняем оригинальное сообщение об ошибке
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred during map generation"
        logger.error(f"Unexpected error in generate_map: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate map: {error_msg}")
    
    # Валидация структуры данных от AI
    if not ai_data or not isinstance(ai_data, dict):
        logger.error(f"Invalid AI response structure: {type(ai_data)}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Expected a dictionary with 'productName' and 'map' fields."
        )
    
    if "map" not in ai_data or not isinstance(ai_data.get("map"), list):
        logger.error(f"Invalid AI response: missing or invalid 'map' field")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Missing or invalid 'map' field."
        )
    
    # 2. Создаем проект (привязываем к текущему пользователю)
    try:
        project = Project(
            name=ai_data.get("productName", "New Project"),
            raw_requirements=req.text,
            user_id=current_user.id
        )
        db.add(project)
        db.flush()
        
        # 3. Создаем стандартные релизы
        mvp_release = Release(project_id=project.id, title="MVP", position=0)
        release1 = Release(project_id=project.id, title="Release 1", position=1)
        later_release = Release(project_id=project.id, title="Later", position=2)
        db.add_all([mvp_release, release1, later_release])
        db.flush()
        
        # 4. Сохраняем структуру карты
        for act_idx, activity_item in enumerate(ai_data.get("map", [])):
            if not isinstance(activity_item, dict):
                logger.warning(f"Skipping invalid activity item at index {act_idx}: {type(activity_item)}")
                continue
                
            activity = Activity(
                project_id=project.id,
                title=activity_item.get("activity", ""),
                position=act_idx
            )
            db.add(activity)
            db.flush()
            
            tasks = activity_item.get("tasks", [])
            if not isinstance(tasks, list):
                logger.warning(f"Invalid tasks format for activity {act_idx}")
                continue
                
            for task_idx, task_item in enumerate(tasks):
                if not isinstance(task_item, dict):
                    logger.warning(f"Skipping invalid task item at activity {act_idx}, task {task_idx}")
                    continue
                    
                task = UserTask(
                    activity_id=activity.id,
                    title=task_item.get("taskTitle", ""),
                    position=task_idx
                )
                db.add(task)
                db.flush()
                
                stories = task_item.get("stories", [])
                if not isinstance(stories, list):
                    logger.warning(f"Invalid stories format for task {task_idx}")
                    continue
                    
                for story_idx, story_item in enumerate(stories):
                    if not isinstance(story_item, dict):
                        logger.warning(f"Skipping invalid story item at activity {act_idx}, task {task_idx}, story {story_idx}")
                        continue
                    
                    # Определяем релиз по приоритету
                    priority = story_item.get("priority", "Later").upper()
                    if "MVP" in priority:
                        target_release = mvp_release
                    elif "RELEASE" in priority or "1" in priority:
                        target_release = release1
                    else:
                        target_release = later_release
                    
                    story = UserStory(
                        task_id=task.id,
                        release_id=target_release.id,
                        title=story_item.get("title", ""),
                        description=story_item.get("description", ""),
                        priority=story_item.get("priority", "Later"),
                        acceptance_criteria=story_item.get("acceptanceCriteria", []),
                        position=story_idx
                    )
                    db.add(story)
        
        db.commit()
        db.refresh(project)
    except Exception as e:
        db.rollback()
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: Database error occurred"
        logger.error(f"Database error while saving project: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save project to database: {error_msg}"
        )
    
    return {
        "status": "success",
        "project_id": project.id,
        "project_name": project.name
    }


@router.get("/project/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Возвращает полную структуру проекта для отрисовки на фронтенде"""
    # Исправление N+1 проблемы через eager loading
    project = db.query(Project)\
        .options(
            joinedload(Project.activities)
            .subqueryload(Activity.tasks)
            .subqueryload(UserTask.stories),
            joinedload(Project.releases)
        )\
        .filter(Project.id == project_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Формируем ответ в нужном формате
    activities_data = []
    for activity in project.activities:
        tasks_data = []
        for task in activity.tasks:
            stories_data = []
            for story in task.stories:
                stories_data.append(StoryResponse(
                    id=story.id,
                    title=story.title,
                    description=story.description,
                    priority=story.priority,
                    acceptance_criteria=story.acceptance_criteria or [],
                    release_id=story.release_id,
                    position=story.position,
                    status=story.status or "todo"
                ))
            tasks_data.append(TaskResponse(
                id=task.id,
                title=task.title,
                position=task.position,
                stories=stories_data
            ))
        activities_data.append(ActivityResponse(
            id=activity.id,
            title=activity.title,
            position=activity.position,
            tasks=tasks_data
        ))
    
    releases_data = [
        ReleaseResponse(
            id=release.id,
            title=release.title,
            position=release.position
        )
        for release in project.releases
    ]
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        raw_requirements=project.raw_requirements,
        activities=activities_data,
        releases=releases_data
    )


@router.get("/projects")
def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Возвращает список проектов пользователя с пагинацией"""
    projects = db.query(Project)\
        .filter(Project.user_id == current_user.id)\
        .order_by(Project.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    total = db.query(Project).filter(Project.user_id == current_user.id).count()
    
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "created_at": p.created_at.isoformat()
            }
            for p in projects
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

