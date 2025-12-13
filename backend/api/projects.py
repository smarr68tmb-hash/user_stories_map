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
    ReleaseResponse,
    ActivityCreate,
    ActivityUpdate,
    TaskCreate,
    TaskUpdate,
    TaskMove,
    ProjectUpdate
)
from services.ai_service import generate_ai_map, enhance_requirements
from services.agent_service import generate_map_with_agent
from dependencies import get_current_active_user, get_current_user_optional

router = APIRouter(prefix="", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Lazy import для wireframe сервисов (чтобы не ломать импорт если Redis недоступен)
WIREFRAME_AVAILABLE = False
enqueue_wireframe_job = None
QueueAdapter = None

try:
    from services.wireframe_service import enqueue_wireframe_job
    from services.queue_provider import QueueAdapter
    WIREFRAME_AVAILABLE = True
    logger.info("✅ Wireframe services loaded successfully")
except ImportError as e:
    logger.warning(f"Wireframe services not available (ImportError): {e}")
except Exception as e:
    logger.warning(f"Wireframe services not available: {type(e).__name__}: {e}", exc_info=True)


def format_project_response(project: Project) -> ProjectResponse:
    """
    Форматирует проект в ProjectResponse (DRY принцип)

    Args:
        project: Project объект с загруженными отношениями (activities, tasks, stories, releases)

    Returns:
        ProjectResponse с полной структурой проекта
    """
    activities_data = []
    for activity in project.activities:
        tasks_data = []
        for task in activity.tasks:
            stories_data = [
                StoryResponse(
                    id=story.id,
                    title=story.title,
                    description=story.description,
                    priority=story.priority,
                    acceptance_criteria=story.acceptance_criteria or [],
                    release_id=story.release_id,
                    position=story.position,
                    status=story.status or "todo"
                )
                for story in task.stories
            ]
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
        releases=releases_data,
        wireframe_markdown=project.wireframe_markdown,
        wireframe_generated_at=project.wireframe_generated_at,
        wireframe_status=project.wireframe_status,
        wireframe_error=project.wireframe_error,
    )


def get_redis_client():
    """Получает Redis клиент или возвращает None если недоступен"""
    try:
        import redis
        from config import settings
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        return redis_client
    except Exception as e:
        # В production это критичная проблема - логируем как error
        if settings.ENVIRONMENT == "production":
            logger.error(f"❌ Redis unavailable in production: {e}. Caching disabled!")
            # В production можно отправить alert в Sentry
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"Redis connection failed: {e}",
                    level="error"
                )
            except ImportError:
                pass
        else:
            logger.warning(f"⚠️ Redis not available in development: {e}. Caching disabled.")
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

        # Используем агента если параметр use_agent=True
        if req.use_agent:
            logger.info("🤖 Using AI Agent for generation")
            ai_data = generate_map_with_agent(
                generation_text,
                redis_client=redis_client,
                use_cache=True,
                enable_validation=True,
                enable_fix=True
            )
        else:
            logger.info("📝 Using standard generation")
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
    
    # Формируем ответ
    response = {
        "status": "success",
        "project_id": project.id,
        "project_name": project.name
    }

    # Добавляем метаданные агента если использовался агент
    if req.use_agent and "metadata" in ai_data:
        response["agent_metadata"] = ai_data["metadata"]

    return response


@router.post("/generate-map/demo")
@limiter.limit("3/hour")
def generate_map_demo(
    req: RequirementsInput,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Demo-режим: генерация карты БЕЗ регистрации (один раз).

    Отличия от обычного /generate-map:
    - Не требует аутентификации (current_user может быть None)
    - Строгий rate limit: 3 запроса в час с IP
    - Возвращает карту напрямую (не сохраняет в БД)
    - Нет возможности редактировать результат

    Rate limit: 3 запроса в час с IP (для защиты от злоупотреблений)
    """

    # Валидация входных данных
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Requirements text cannot be empty")

    # Получаем Redis клиент
    redis_client = get_redis_client()

    # Текст для генерации
    generation_text = req.text

    # Для demo пропускаем enhancement (экономим время и токены)
    logger.info(f"Demo mode: Generating map without enhancement (IP: {request.client.host})")

    # Генерация карты
    try:
        # Всегда используем стандартную генерацию (не агента) для demo
        ai_data = generate_ai_map(generation_text, redis_client=redis_client)
    except HTTPException as e:
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred during map generation"
        logger.error(f"Unexpected error in generate_map_demo: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate map: {error_msg}")

    # Валидация структуры данных от AI
    if not ai_data or not isinstance(ai_data, dict):
        logger.error(f"Invalid AI response structure: {type(ai_data)}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service."
        )

    if "map" not in ai_data or not isinstance(ai_data.get("map"), list):
        logger.error(f"Invalid AI response: missing or invalid 'map' field")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service."
        )

    # Для demo возвращаем карту напрямую (БЕЗ сохранения в БД)
    # Добавляем стандартные релизы в ответ
    demo_response = {
        "status": "demo",
        "project_name": ai_data.get("productName", "Demo Project"),
        "map": ai_data.get("map", []),
        "releases": [
            {"id": -1, "title": "MVP", "position": 0},
            {"id": -2, "title": "Release 1", "position": 1},
            {"id": -3, "title": "Later", "position": 2}
        ],
        "demo_mode": True,
        "message": "Это демо-карта. Зарегистрируйтесь чтобы сохранить и редактировать проект."
    }

    logger.info(f"Demo map generated successfully (IP: {request.client.host})")
    return demo_response


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

    return format_project_response(project)


@router.post("/project/{project_id}/wireframe/generate")
@limiter.limit("20/hour")
def generate_project_wireframe(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Ставит задачу генерации markdown wireframe для всей карты проекта."""
    if not WIREFRAME_AVAILABLE or not enqueue_wireframe_job:
        raise HTTPException(
            status_code=503,
            detail="Wireframe generation service is not available. Redis queue may be unavailable."
        )
    
    project = (
        db.query(Project)
        .options(
            joinedload(Project.activities).subqueryload(Activity.tasks).subqueryload(UserTask.stories)
        )
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.activities:
        raise HTTPException(status_code=400, detail="Project has no activities to generate wireframe")

    try:
        job_id = enqueue_wireframe_job(project_id, current_user.id)
        project.wireframe_status = "pending"
        project.wireframe_error = None
        db.commit()
        return {"status": "queued", "job_id": job_id}
    except HTTPException as e:
        db.rollback()
        # Если Redis недоступен, пробуем синхронную генерацию
        if e.status_code == 503 and "Redis" in str(e.detail):
            logger.warning("Redis unavailable, falling back to synchronous wireframe generation")
            try:
                from services.wireframe_service import process_wireframe_job
                # Генерируем синхронно
                project.wireframe_status = "generating"
                project.wireframe_error = None
                db.commit()
                
                markdown = process_wireframe_job(project_id, current_user.id)
                project.wireframe_status = "success"
                project.wireframe_error = None
                db.commit()
                return {"status": "completed", "message": "Wireframe generated synchronously (Redis unavailable)"}
            except Exception as sync_error:
                db.rollback()
                error_msg = str(sync_error) if str(sync_error) else repr(sync_error)
                project.wireframe_status = "error"
                project.wireframe_error = f"Synchronous generation failed: {error_msg}"
                db.commit()
                logger.error(f"Synchronous wireframe generation failed: {error_msg}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Wireframe generation failed: {error_msg}"
                )
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"Failed to enqueue wireframe job: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to enqueue wireframe generation job: {error_msg}")


@router.get("/project/{project_id}/wireframe")
def get_project_wireframe(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Возвращает текущий wireframe markdown и статус."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "markdown": project.wireframe_markdown,
        "status": project.wireframe_status,
        "generated_at": project.wireframe_generated_at,
        "error": project.wireframe_error,
    }


@router.get("/project/{project_id}/wireframe/status")
def get_project_wireframe_status(
    project_id: int,
    job_id: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Возвращает статус wireframe и (опционально) статус задачи очереди."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    queue_status = None
    if job_id and WIREFRAME_AVAILABLE and QueueAdapter:
        try:
            adapter = QueueAdapter(driver="redis")
            job = adapter.get_job(job_id)
            if job:
                queue_status = job.get_status(refresh=True)
        except Exception as e:  # pragma: no cover - только логирование статуса очереди
            logger.warning(f"Failed to fetch queue status for job {job_id}: {e}")

    return {
        "status": project.wireframe_status,
        "generated_at": project.wireframe_generated_at,
        "error": project.wireframe_error,
        "job_status": queue_status,
    }


@router.put("/project/{project_id}", response_model=ProjectResponse)
@limiter.limit("30/minute")
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновляет название проекта"""
    # Проверяем существование проекта и владельца
    project = db.query(Project)\
        .filter(Project.id == project_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Обновляем название, если указано
    if project_update.name is not None:
        new_name = project_update.name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="Project name cannot be empty")
        if len(new_name) > 255:
            raise HTTPException(status_code=400, detail="Project name cannot exceed 255 characters")
        project.name = new_name
    
    db.commit()
    db.refresh(project)
    
    # Повторно загружаем проект с eager loading, чтобы избежать N+1 запросов,
    # аналогично get_project
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

    # Проверяем, что проект все еще существует после повторного запроса
    # (может быть удален или права доступа изменены между обновлением и запросом)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    return format_project_response(project)


@router.get("/projects")
def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Возвращает список проектов пользователя с пагинацией"""
    logger.info(f"list_projects called for user {current_user.id}, skip={skip}, limit={limit}")
    try:
        logger.debug("Querying projects from database...")
        # Загружаем только нужные поля для списка (без wireframe полей, чтобы не ломать если миграция не применена)
        projects = db.query(
            Project.id,
            Project.user_id,
            Project.name,
            Project.created_at
        )\
            .filter(Project.user_id == current_user.id)\
            .order_by(Project.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        logger.debug(f"Found {len(projects)} projects, querying total count...")
        total = db.query(Project.id).filter(Project.user_id == current_user.id).count()
        
        logger.debug(f"Total projects: {total}, preparing response...")
        items = []
        for p in projects:
            try:
                # p теперь кортеж (id, user_id, name, created_at) из-за query с конкретными полями
                project_id, _, project_name, created_at = p
                items.append({
                    "id": project_id,
                    "name": project_name,
                    "created_at": created_at.isoformat() if created_at else None
                })
            except Exception as item_error:
                logger.error(f"Error serializing project: {item_error}", exc_info=True)
                # Пропускаем проблемный проект, но продолжаем обработку
                continue
        
        logger.info(f"Successfully prepared {len(items)} items for user {current_user.id}")
        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else repr(e)
        logger.error(
            f"Error listing projects for user {current_user.id}: {error_type}: {error_msg}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {error_type}: {error_msg}"
        )


@router.delete("/project/{project_id}")
@limiter.limit("30/minute")
def delete_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаляет проект и все связанные данные (activities, tasks, stories, releases)"""
    # Проверяем существование проекта и владельца
    project = db.query(Project)\
        .filter(Project.id == project_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    project_name = project.name
    
    # Удаляем проект (каскадное удаление activities, releases, tasks и stories происходит автоматически)
    db.delete(project)
    db.commit()
    
    logger.info(f"Project {project_id} ({project_name}) deleted by user {current_user.id}")
    
    return {"status": "success", "message": f"Project '{project_name}' deleted successfully"}


# ========== ACTIVITY ENDPOINTS ==========

@router.post("/activity", response_model=ActivityResponse)
@limiter.limit("30/minute")
def create_activity(
    activity: ActivityCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создает новую Activity в проекте"""
    # Проверяем существование проекта и владельца
    project = db.query(Project)\
        .filter(Project.id == activity.project_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Проверяем уникальность названия Activity в рамках проекта
    existing_activity = db.query(Activity)\
        .filter(Activity.project_id == activity.project_id)\
        .filter(Activity.title == activity.title.strip())\
        .first()
    
    if existing_activity:
        raise HTTPException(
            status_code=400, 
            detail=f"Activity with title '{activity.title}' already exists in this project"
        )
    
    # Определяем позицию (в конец списка, если не указана)
    if activity.position is None:
        max_position = db.query(Activity)\
            .filter(Activity.project_id == activity.project_id)\
            .count()
        position = max_position
    else:
        position = activity.position
        # Сдвигаем существующие активности
        activities_to_shift = db.query(Activity)\
            .filter(Activity.project_id == activity.project_id)\
            .filter(Activity.position >= position)\
            .all()
        for act in activities_to_shift:
            act.position += 1
    
    new_activity = Activity(
        project_id=activity.project_id,
        title=activity.title.strip(),
        position=position
    )
    
    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)
    
    # Возвращаем ActivityResponse с пустым списком tasks
    return ActivityResponse(
        id=new_activity.id,
        title=new_activity.title,
        position=new_activity.position,
        tasks=[]
    )


@router.put("/activity/{activity_id}", response_model=ActivityResponse)
@limiter.limit("30/minute")
def update_activity(
    activity_id: int,
    activity_update: ActivityUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновляет существующую Activity (переименование)"""
    # Проверяем владельца проекта
    activity = db.query(Activity)\
        .join(Project)\
        .filter(Activity.id == activity_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found or access denied")
    
    # Если обновляется название, проверяем уникальность
    if activity_update.title is not None:
        new_title = activity_update.title.strip()
        if new_title != activity.title:
            existing_activity = db.query(Activity)\
                .filter(Activity.project_id == activity.project_id)\
                .filter(Activity.title == new_title)\
                .filter(Activity.id != activity_id)\
                .first()
            
            if existing_activity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Activity with title '{new_title}' already exists in this project"
                )
            activity.title = new_title
    
    # Обновляем позицию, если указана
    if activity_update.position is not None and activity_update.position != activity.position:
        old_position = activity.position
        new_position = activity_update.position
        
        if new_position < old_position:
            # Сдвигаем активности вправо
            activities_to_shift = db.query(Activity)\
                .filter(Activity.project_id == activity.project_id)\
                .filter(Activity.position >= new_position)\
                .filter(Activity.position < old_position)\
                .filter(Activity.id != activity_id)\
                .all()
            for act in activities_to_shift:
                act.position += 1
        else:
            # Сдвигаем активности влево
            activities_to_shift = db.query(Activity)\
                .filter(Activity.project_id == activity.project_id)\
                .filter(Activity.position > old_position)\
                .filter(Activity.position <= new_position)\
                .filter(Activity.id != activity_id)\
                .all()
            for act in activities_to_shift:
                act.position -= 1
        
        activity.position = new_position
    
    db.commit()
    db.refresh(activity)
    
    # Формируем ответ с tasks
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
    
    return ActivityResponse(
        id=activity.id,
        title=activity.title,
        position=activity.position,
        tasks=tasks_data
    )


@router.delete("/activity/{activity_id}")
@limiter.limit("30/minute")
def delete_activity(
    activity_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаляет Activity и все связанные Tasks (каскадное удаление)"""
    # Проверяем владельца проекта
    activity = db.query(Activity)\
        .join(Project)\
        .filter(Activity.id == activity_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found or access denied")
    
    project_id = activity.project_id
    position = activity.position
    
    # Удаляем активность (каскадное удаление tasks и stories происходит автоматически)
    db.delete(activity)
    db.commit()
    
    # Обновляем позиции остальных активностей
    activities_to_update = db.query(Activity)\
        .filter(Activity.project_id == project_id)\
        .filter(Activity.position > position)\
        .all()
    
    for act in activities_to_update:
        act.position -= 1
    
    db.commit()
    
    return {"status": "success", "message": "Activity deleted"}


# ========== TASK ENDPOINTS ==========

@router.post("/task", response_model=TaskResponse)
@limiter.limit("30/minute")
def create_task(
    task: TaskCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создает новую Task в Activity"""
    # Проверяем существование Activity и владельца проекта
    activity = db.query(Activity)\
        .join(Project)\
        .filter(Activity.id == task.activity_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found or access denied")
    
    # Валидация: проверяем, что название не пустое
    task_title = task.title.strip()
    if not task_title:
        raise HTTPException(
            status_code=400,
            detail="Поле названия шага должно быть заполнено"
        )
    
    # Проверяем дубликаты названий в рамках активности
    existing_task = db.query(UserTask)\
        .filter(UserTask.activity_id == task.activity_id)\
        .filter(UserTask.title == task_title)\
        .first()
    
    if existing_task:
        raise HTTPException(
            status_code=400,
            detail="Шаг с таким названием уже существует"
        )
    
    # Определяем позицию (в конец списка, если не указана)
    if task.position is None:
        max_position = db.query(UserTask)\
            .filter(UserTask.activity_id == task.activity_id)\
            .count()
        position = max_position
    else:
        position = task.position
        # Сдвигаем существующие задачи
        tasks_to_shift = db.query(UserTask)\
            .filter(UserTask.activity_id == task.activity_id)\
            .filter(UserTask.position >= position)\
            .all()
        for t in tasks_to_shift:
            t.position += 1
    
    new_task = UserTask(
        activity_id=task.activity_id,
        title=task_title,
        position=position
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Возвращаем TaskResponse с пустым списком stories
    return TaskResponse(
        id=new_task.id,
        title=new_task.title,
        position=new_task.position,
        stories=[]
    )


@router.put("/task/{task_id}", response_model=TaskResponse)
@limiter.limit("30/minute")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновляет существующую Task (переименование)"""
    # Проверяем владельца проекта
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    # Обновляем название, если указано
    if task_update.title is not None:
        new_title = task_update.title.strip()
        # Валидация: проверяем, что название не пустое
        if not new_title:
            raise HTTPException(
                status_code=400,
                detail="Поле названия шага должно быть заполнено"
            )
        
        # Проверяем дубликаты названий в рамках активности (исключая текущий task)
        if new_title != task.title:
            existing_task = db.query(UserTask)\
                .filter(UserTask.activity_id == task.activity_id)\
                .filter(UserTask.title == new_title)\
                .filter(UserTask.id != task_id)\
                .first()
            
            if existing_task:
                raise HTTPException(
                    status_code=400,
                    detail="Шаг с таким названием уже существует"
                )
        
        task.title = new_title
    
    # Обновляем позицию, если указана
    if task_update.position is not None and task_update.position != task.position:
        old_position = task.position
        new_position = task_update.position
        
        if new_position < old_position:
            # Сдвигаем задачи вправо
            tasks_to_shift = db.query(UserTask)\
                .filter(UserTask.activity_id == task.activity_id)\
                .filter(UserTask.position >= new_position)\
                .filter(UserTask.position < old_position)\
                .filter(UserTask.id != task_id)\
                .all()
            for t in tasks_to_shift:
                t.position += 1
        else:
            # Сдвигаем задачи влево
            tasks_to_shift = db.query(UserTask)\
                .filter(UserTask.activity_id == task.activity_id)\
                .filter(UserTask.position > old_position)\
                .filter(UserTask.position <= new_position)\
                .filter(UserTask.id != task_id)\
                .all()
            for t in tasks_to_shift:
                t.position -= 1
        
        task.position = new_position
    
    db.commit()
    db.refresh(task)
    
    # Формируем ответ с stories
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
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        position=task.position,
        stories=stories_data
    )


@router.delete("/task/{task_id}")
@limiter.limit("30/minute")
def delete_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаляет Task и все связанные Stories (каскадное удаление)"""
    # Проверяем владельца проекта
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    activity_id = task.activity_id
    position = task.position
    
    # Удаляем задачу (каскадное удаление stories происходит автоматически)
    db.delete(task)
    db.commit()
    
    # Обновляем позиции остальных задач
    tasks_to_update = db.query(UserTask)\
        .filter(UserTask.activity_id == activity_id)\
        .filter(UserTask.position > position)\
        .all()
    
    for t in tasks_to_update:
        t.position -= 1
    
    db.commit()
    
    return {"status": "success", "message": "Task deleted"}


@router.patch("/task/{task_id}/move", response_model=TaskResponse)
@limiter.limit("30/minute")
def move_task(
    task_id: int,
    move: TaskMove,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Перемещает Task в другую позицию внутри Activity (drag & drop)"""
    # Проверяем владельца проекта
    task = db.query(UserTask)\
        .join(Activity)\
        .join(Project)\
        .filter(UserTask.id == task_id)\
        .filter(Project.user_id == current_user.id)\
        .first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")
    
    old_position = task.position
    new_position = move.position

    # Нормализуем позицию в допустимый диапазон [0, max_position]
    tasks_count = db.query(UserTask)\
        .filter(UserTask.activity_id == task.activity_id)\
        .count()
    max_position = max(tasks_count - 1, 0)
    if new_position < 0:
        new_position = 0
    elif new_position > max_position:
        new_position = max_position
    
    # Если позиция не изменилась, ничего не делаем
    if old_position == new_position:
        db.refresh(task)
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
        return TaskResponse(
            id=task.id,
            title=task.title,
            position=task.position,
            stories=stories_data
        )
    
    # Обновляем позиции других задач
    if new_position < old_position:
        # Сдвигаем задачи вправо
        tasks_to_shift = db.query(UserTask)\
            .filter(UserTask.activity_id == task.activity_id)\
            .filter(UserTask.position >= new_position)\
            .filter(UserTask.position < old_position)\
            .filter(UserTask.id != task_id)\
            .all()
        for t in tasks_to_shift:
            t.position += 1
    else:
        # Сдвигаем задачи влево
        tasks_to_shift = db.query(UserTask)\
            .filter(UserTask.activity_id == task.activity_id)\
            .filter(UserTask.position > old_position)\
            .filter(UserTask.position <= new_position)\
            .filter(UserTask.id != task_id)\
            .all()
        for t in tasks_to_shift:
            t.position -= 1
    
    # Обновляем позицию текущей задачи
    task.position = new_position
    
    db.commit()
    db.refresh(task)
    
    # Формируем ответ с stories
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
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        position=task.position,
        stories=stories_data
    )

