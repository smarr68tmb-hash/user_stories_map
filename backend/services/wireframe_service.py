"""
Wireframe generation service (project-wide markdown wireframes).

Features:
- Собирает snapshot всей карты проекта (activities → tasks → stories)
- Делает асинхронную постановку задачи в очередь (RQ/Redis по умолчанию)
- Генерирует markdown wireframe через AI и сохраняет в Project

Дизайн с учётом будущего перехода на RabbitMQ: используется QueueAdapter,
который можно реализовать под другой драйвер без изменений API слоёв.
"""
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from config import settings
from utils.database import SessionLocal
from models import Project, Activity, UserTask, UserStory, Release
from services.ai_service import generate_markdown_wireframe
from services.queue_provider import QueueAdapter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------
def _story_payload(story: UserStory) -> Dict[str, Any]:
    return {
        "id": story.id,
        "title": story.title or "",
        "description": story.description or "",
        "priority": story.priority or "",
        "status": story.status or "todo",
        "acceptance_criteria": story.acceptance_criteria or [],
    }


def _task_payload(task: UserTask) -> Dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title or "",
        "stories": [_story_payload(s) for s in task.stories],
    }


def _activity_payload(activity: Activity) -> Dict[str, Any]:
    return {
        "id": activity.id,
        "title": activity.title or "",
        "tasks": [_task_payload(t) for t in activity.tasks],
    }


def build_project_snapshot(project: Project) -> Dict[str, Any]:
    """Собирает компактный snapshot проекта для промпта."""
    return {
        "id": project.id,
        "name": project.name or f"Project {project.id}",
        "releases": [{"id": r.id, "title": r.title or ""} for r in project.releases],
        "activities": [_activity_payload(a) for a in project.activities],
    }


# ---------------------------------------------------------------------------
# Queue and job processing
# ---------------------------------------------------------------------------
def enqueue_wireframe_job(project_id: int, user_id: int) -> str:
    """
    Создаёт задачу генерации wireframe.
    Возвращает job_id из выбранного адаптера очереди.
    """
    try:
        adapter = QueueAdapter(driver="redis")
        job = adapter.enqueue(process_wireframe_job, project_id, user_id)
        return job.id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enqueue wireframe job: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to enqueue wireframe job: {str(e)}. Redis may be unavailable."
        )


def process_wireframe_job(project_id: int, user_id: int) -> Optional[str]:
    """
    Запускается воркером (RQ). Генерирует markdown wireframe и сохраняет в БД.
    Возвращает markdown текст при успехе.
    """
    db: Session = SessionLocal()
    try:
        project: Project = (
            db.query(Project)
            .options(
                joinedload(Project.activities)
                .subqueryload(Activity.tasks)
                .subqueryload(UserTask.stories),
                joinedload(Project.releases),
            )
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")

        snapshot = build_project_snapshot(project)
        logger.info(f"Generating wireframe for project {project_id} (activities={len(snapshot.get('activities', []))})")

        markdown = generate_markdown_wireframe(snapshot)

        project.wireframe_markdown = markdown
        project.wireframe_generated_at = datetime.utcnow()
        project.wireframe_status = "success"
        project.wireframe_error = None
        db.commit()

        return markdown
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - сохраняем ошибку в БД и прокидываем
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"Wireframe job failed: {error_msg}", exc_info=True)
        try:
            project = (
                db.query(Project)
                .filter(Project.id == project_id, Project.user_id == user_id)
                .first()
            )
            if project:
                project.wireframe_status = "error"
                project.wireframe_error = error_msg
                db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()

