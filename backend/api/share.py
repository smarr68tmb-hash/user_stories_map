"""
Share endpoints - публичный доступ к проектам через share token
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db
from utils import ResponseFormatter
from models import Project, Activity, UserTask
from schemas import ShareProjectResponse

router = APIRouter(prefix="", tags=["share"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.get("/share/{share_token}", response_model=ShareProjectResponse)
@limiter.limit("100/hour")
def get_shared_project(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Получает проект по share token (публичный доступ, view-only)
    
    Не требует аутентификации - доступен всем, кто знает токен.
    """
    # Ищем проект по share_token
    project = db.query(Project)\
        .filter(Project.share_token == share_token)\
        .first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or share link is invalid")
    
    # Загружаем проект с отношениями (eager loading для избежания N+1)
    project = db.query(Project)\
        .options(
            joinedload(Project.activities)
            .subqueryload(Activity.tasks)
            .subqueryload(UserTask.stories),
            joinedload(Project.releases)
        )\
        .filter(Project.id == project.id)\
        .first()
    
    # Форматируем ответ (только чтение, без возможности редактирования)
    formatter = ResponseFormatter()
    project_data = formatter.format_project(project)
    
    logger.info(f"Shared project {project.id} accessed via token {share_token[:8]}...")
    
    return ShareProjectResponse(
        id=project_data.id,
        name=project_data.name,
        activities=project_data.activities,
        releases=project_data.releases,
        shared=True,
        view_only=True
    )

