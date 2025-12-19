"""
Resource Access Validator - централизованная проверка доступа к ресурсам

Упрощает проверку прав доступа в API endpoints, аналогично организации тестов в классы.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Project, Epic, UserStory, Activity, UserTask


class ResourceAccessValidator:
    """
    Класс для проверки доступа к ресурсам пользователя.
    
    Аналогично TestHelperFunctions в тестах - группирует связанные функции.
    """
    
    def __init__(self, db: Session, user_id: int):
        """
        Args:
            db: Database session
            user_id: ID текущего пользователя
        """
        self.db = db
        self.user_id = user_id
    
    def get_project(self, project_id: int) -> Project:
        """
        Получает проект пользователя или выбрасывает 404.
        
        Args:
            project_id: ID проекта
            
        Returns:
            Project: Проект пользователя
            
        Raises:
            HTTPException: 404 если проект не найден или нет доступа
        """
        project = (
            self.db.query(Project)
            .filter(Project.id == project_id)
            .filter(Project.user_id == self.user_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    
    def get_epic(self, epic_id: int) -> Epic:
        """
        Получает эпик пользователя или выбрасывает 404.
        
        Args:
            epic_id: ID эпика
            
        Returns:
            Epic: Эпик пользователя
            
        Raises:
            HTTPException: 404 если эпик не найден или нет доступа
        """
        epic = (
            self.db.query(Epic)
            .join(Project)
            .filter(Epic.id == epic_id)
            .filter(Project.user_id == self.user_id)
            .first()
        )
        if not epic:
            raise HTTPException(status_code=404, detail="Epic not found")
        return epic
    
    def get_story(self, story_id: int) -> UserStory:
        """
        Получает историю пользователя или выбрасывает 404.
        
        Args:
            story_id: ID истории
            
        Returns:
            UserStory: История пользователя
            
        Raises:
            HTTPException: 404 если история не найдена или нет доступа
        """
        story = (
            self.db.query(UserStory)
            .join(UserTask)
            .join(Activity)
            .join(Project)
            .filter(UserStory.id == story_id)
            .filter(Project.user_id == self.user_id)
            .first()
        )
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        return story
    
    def get_activity(self, activity_id: int) -> Activity:
        """
        Получает активность пользователя или выбрасывает 404.
        
        Args:
            activity_id: ID активности
            
        Returns:
            Activity: Активность пользователя
            
        Raises:
            HTTPException: 404 если активность не найдена или нет доступа
        """
        activity = (
            self.db.query(Activity)
            .join(Project)
            .filter(Activity.id == activity_id)
            .filter(Project.user_id == self.user_id)
            .first()
        )
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        return activity
    
    def get_task(self, task_id: int) -> UserTask:
        """
        Получает задачу пользователя или выбрасывает 404.
        
        Args:
            task_id: ID задачи
            
        Returns:
            UserTask: Задача пользователя
            
        Raises:
            HTTPException: 404 если задача не найдена или нет доступа
        """
        task = (
            self.db.query(UserTask)
            .join(Activity)
            .join(Project)
            .filter(UserTask.id == task_id)
            .filter(Project.user_id == self.user_id)
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    
    def verify_same_project(self, story: UserStory, epic: Epic) -> None:
        """
        Проверяет, что история и эпик принадлежат одному проекту.
        
        Args:
            story: История
            epic: Эпик
            
        Raises:
            HTTPException: 400 если проекты не совпадают
        """
        if story.task.activity.project_id != epic.project_id:
            raise HTTPException(
                status_code=400,
                detail="Story and epic must belong to the same project"
            )

