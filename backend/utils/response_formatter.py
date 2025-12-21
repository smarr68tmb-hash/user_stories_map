"""
Response Formatter - централизованное форматирование ответов API

Упрощает создание ответов для API endpoints, аналогично организации тестов в классы.
"""
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from models import UserStory, UserTask, Activity, Project, Release

from schemas import (
    StoryResponse,
    TaskResponse,
    ActivityResponse,
    ProjectResponse,
    ReleaseResponse
)


class ResponseFormatter:
    """
    Класс для форматирования ответов API.
    
    Аналогично TestValidationLogic в тестах - группирует связанные функции форматирования.
    """
    
    @staticmethod
    def format_story(story: "UserStory") -> StoryResponse:
        """
        Форматирует историю в StoryResponse.
        
        Args:
            story: UserStory объект
            
        Returns:
            StoryResponse: Отформатированный ответ
        """
        return StoryResponse(
            id=story.id,
            title=story.title,
            description=story.description,
            priority=story.priority,
            acceptance_criteria=story.acceptance_criteria or [],
            release_id=story.release_id,
            epic_id=getattr(story, 'epic_id', None),
            position=story.position,
            status=story.status or "todo"
        )
    
    @staticmethod
    def format_stories(stories: List["UserStory"]) -> List[StoryResponse]:
        """
        Форматирует список историй в StoryResponse.
        
        Args:
            stories: Список UserStory объектов
            
        Returns:
            List[StoryResponse]: Список отформатированных ответов
        """
        return [ResponseFormatter.format_story(story) for story in stories]
    
    @staticmethod
    def format_task(task: "UserTask", include_stories: bool = True) -> TaskResponse:
        """
        Форматирует задачу в TaskResponse.
        
        Args:
            task: UserTask объект
            include_stories: Включать ли истории в ответ
            
        Returns:
            TaskResponse: Отформатированный ответ
        """
        stories_data = []
        if include_stories:
            stories_data = ResponseFormatter.format_stories(task.stories)
        
        return TaskResponse(
            id=task.id,
            title=task.title,
            position=task.position,
            stories=stories_data
        )
    
    @staticmethod
    def format_tasks(tasks: List["UserTask"], include_stories: bool = True) -> List[TaskResponse]:
        """
        Форматирует список задач в TaskResponse.
        
        Args:
            tasks: Список UserTask объектов
            include_stories: Включать ли истории в ответ
            
        Returns:
            List[TaskResponse]: Список отформатированных ответов
        """
        return [ResponseFormatter.format_task(task, include_stories) for task in tasks]
    
    @staticmethod
    def format_activity(activity: "Activity", include_tasks: bool = True) -> ActivityResponse:
        """
        Форматирует активность в ActivityResponse.
        
        Args:
            activity: Activity объект
            include_tasks: Включать ли задачи в ответ
            
        Returns:
            ActivityResponse: Отформатированный ответ
        """
        tasks_data = []
        if include_tasks:
            tasks_data = ResponseFormatter.format_tasks(activity.tasks, include_stories=True)
        
        return ActivityResponse(
            id=activity.id,
            title=activity.title,
            position=activity.position,
            tasks=tasks_data
        )
    
    @staticmethod
    def format_activities(activities: List["Activity"], include_tasks: bool = True) -> List[ActivityResponse]:
        """
        Форматирует список активностей в ActivityResponse.
        
        Args:
            activities: Список Activity объектов
            include_tasks: Включать ли задачи в ответ
            
        Returns:
            List[ActivityResponse]: Список отформатированных ответов
        """
        return [ResponseFormatter.format_activity(activity, include_tasks) for activity in activities]
    
    @staticmethod
    def format_release(release: "Release") -> ReleaseResponse:
        """
        Форматирует релиз в ReleaseResponse.
        
        Args:
            release: Release объект
            
        Returns:
            ReleaseResponse: Отформатированный ответ
        """
        return ReleaseResponse(
            id=release.id,
            title=release.title,
            position=release.position
        )
    
    @staticmethod
    def format_releases(releases: List["Release"]) -> List[ReleaseResponse]:
        """
        Форматирует список релизов в ReleaseResponse.
        
        Args:
            releases: Список Release объектов
            
        Returns:
            List[ReleaseResponse]: Список отформатированных ответов
        """
        return [ResponseFormatter.format_release(release) for release in releases]
    
    @staticmethod
    def format_project(project: "Project") -> ProjectResponse:
        """
        Форматирует проект в ProjectResponse с полной структурой.
        
        Args:
            project: Project объект с загруженными отношениями
            
        Returns:
            ProjectResponse: Отформатированный ответ
        """
        activities_data = ResponseFormatter.format_activities(project.activities, include_tasks=True)
        releases_data = ResponseFormatter.format_releases(project.releases)
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            raw_requirements=project.raw_requirements,
            activities=activities_data,
            releases=releases_data,
            wireframe_markdown=getattr(project, 'wireframe_markdown', None),
            wireframe_generated_at=getattr(project, 'wireframe_generated_at', None),
            wireframe_status=getattr(project, 'wireframe_status', None),
            wireframe_error=getattr(project, 'wireframe_error', None),
        )

