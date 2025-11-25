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
from schemas import RequirementsInput, ProjectResponse, ActivityResponse, TaskResponse, StoryResponse, ReleaseResponse
from services.ai_service import generate_ai_map
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["projects"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/generate-map")
@limiter.limit("10/hour")
def generate_map(
    req: RequirementsInput,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Генерирует карту пользовательских историй из текста требований"""
    
    # Валидация входных данных
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Requirements text cannot be empty")
    
    # 1. Получаем данные от AI
    try:
        # Попробуем использовать Redis если доступен
        redis_client = None
        try:
            import redis
            from config import settings
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            redis_client = None
        
        ai_data = generate_ai_map(req.text, redis_client=redis_client)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_map: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate map")
    
    # 2. Создаем проект (привязываем к текущему пользователю)
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
        activity = Activity(
            project_id=project.id,
            title=activity_item.get("activity", ""),
            position=act_idx
        )
        db.add(activity)
        db.flush()
        
        for task_idx, task_item in enumerate(activity_item.get("tasks", [])):
            task = UserTask(
                activity_id=activity.id,
                title=task_item.get("taskTitle", ""),
                position=task_idx
            )
            db.add(task)
            db.flush()
            
            for story_idx, story_item in enumerate(task_item.get("stories", [])):
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
                    position=story.position
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

